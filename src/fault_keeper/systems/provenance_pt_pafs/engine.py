"""PT-PAFS Engine: Pointer Provenance & Tree Borrows Formal State Machine Verifier.

Implements the formal Tree Borrows operational memory model for unsafe Rust/C,
tracking pointer provenance hierarchies, permissions (Reserved, Active, Frozen, Disabled),
and verifying strict aliasing and undefined behavior invariants.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

from .config import PTPAFSConfig


class BorrowKind(str, Enum):
    """Classification of pointer borrow permission types."""

    MUTABLE = "mutable"
    SHARED = "shared"


class BorrowState(str, Enum):
    """Formal Tree Borrows state machine permission states."""

    RESERVED = "reserved"
    ACTIVE = "active"
    FROZEN = "frozen"
    DISABLED = "disabled"


@dataclass
class BorrowTreeNode:
    """Represents an atomic borrow tag node in the provenance tree."""

    tag: int
    parent: Optional[int]
    kind: BorrowKind
    state: BorrowState = BorrowState.RESERVED
    children: List[int] = field(default_factory=list)


class TreeBorrowsStateMachine:
    """Formal Tree Borrows State Machine tracking permissions across a pointer tree."""

    def __init__(self, config: Optional[PTPAFSConfig] = None) -> None:
        self.config = config or PTPAFSConfig()
        self.nodes: Dict[int, BorrowTreeNode] = {}
        self.violations: List[str] = []

    def add_borrow(self, tag: int, parent: Optional[int], kind: BorrowKind) -> BorrowTreeNode:
        """Add a borrow tag to the provenance hierarchy."""
        initial_state = BorrowState.RESERVED
        node = BorrowTreeNode(
            tag=tag,
            parent=parent,
            kind=kind,
            state=initial_state,
        )
        self.nodes[tag] = node
        if parent is not None and parent in self.nodes:
            self.nodes[parent].children.append(tag)
        return node

    def get_state(self, tag: int) -> BorrowState:
        """Retrieve current borrow state of a tag."""
        if tag not in self.nodes:
            return BorrowState.DISABLED
        return self.nodes[tag].state

    def _get_ancestors(self, tag: int) -> Set[int]:
        """Compute set of ancestor tags up to tree root."""
        ancestors: Set[int] = set()
        curr = self.nodes.get(tag)
        while curr and curr.parent is not None:
            ancestors.add(curr.parent)
            curr = self.nodes.get(curr.parent)
        return ancestors

    def _get_descendants(self, tag: int) -> Set[int]:
        """Compute set of all descendant tags in subtree."""
        descendants: Set[int] = set()
        stack = list(self.nodes[tag].children) if tag in self.nodes else []
        while stack:
            curr = stack.pop()
            descendants.add(curr)
            if curr in self.nodes:
                stack.extend(self.nodes[curr].children)
        return descendants

    def process_read(self, tag: int) -> bool:
        """Apply read event on pointer with given tag."""
        if tag not in self.nodes:
            self.violations.append(f"Use of unregistered tag {tag}")
            return False

        node = self.nodes[tag]
        if node.state == BorrowState.DISABLED:
            self.violations.append(f"Read access on Disabled borrow tag {tag}")
            return False

        # Accessing tag transitions
        if node.state == BorrowState.RESERVED:
            if node.kind == BorrowKind.SHARED:
                node.state = BorrowState.FROZEN

        # Foreign read on other active mutable nodes transitions them to Frozen
        ancestors = self._get_ancestors(tag)
        for other_tag, other_node in self.nodes.items():
            if other_tag != tag and other_tag not in ancestors:
                if other_node.state == BorrowState.ACTIVE:
                    other_node.state = BorrowState.FROZEN

        return True

    def process_write(self, tag: int) -> bool:
        """Apply write event on pointer with given tag."""
        if tag not in self.nodes:
            self.violations.append(f"Write to unregistered tag {tag}")
            return False

        node = self.nodes[tag]
        if node.state in (BorrowState.FROZEN, BorrowState.DISABLED):
            self.violations.append(f"Write access on {node.state.value} borrow tag {tag}")
            return False

        # Active write transition
        node.state = BorrowState.ACTIVE

        # All other tags that are not the current tag experience a foreign write
        # In Tree Borrows, foreign write invalidates/disables other branches and non-descendant nodes
        for other_tag, other_node in self.nodes.items():
            if other_tag != tag:
                # Any node not performing the write gets disabled by foreign write
                other_node.state = BorrowState.DISABLED

        return True


class ProvenanceRegistry:
    """Tracks physical memory addresses to their active provenance borrow trees."""

    def __init__(self) -> None:
        self._address_to_root: Dict[int, int] = {}
        self._fsm = TreeBorrowsStateMachine()

    def register_allocation(self, address: int, root_tag: int, kind: BorrowKind = BorrowKind.MUTABLE) -> None:
        """Register physical address allocation with root borrow tag."""
        self._address_to_root[address] = root_tag
        self._fsm.add_borrow(tag=root_tag, parent=None, kind=kind)

    def derive_pointer(self, parent_tag: int, new_tag: int, kind: BorrowKind) -> None:
        """Derive a new pointer tag from an existing parent tag."""
        self._fsm.add_borrow(tag=new_tag, parent=parent_tag, kind=kind)

    def check_access(self, tag: int, is_write: bool) -> bool:
        """Validate access against Tree Borrows state machine rules."""
        if is_write:
            return self._fsm.process_write(tag)
        return self._fsm.process_read(tag)


__all__ = [
    "BorrowKind",
    "BorrowState",
    "BorrowTreeNode",
    "TreeBorrowsStateMachine",
    "ProvenanceRegistry",
]
