"""PT-PAFS Sentry: Pointer Provenance & Tree Borrows Formal Invariant Sentinel."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import PTPAFSConfig
from .engine import (
    BorrowKind,
    BorrowState,
    ProvenanceRegistry,
    TreeBorrowsStateMachine,
)


@dataclass
class UndefinedBehaviorEvent:
    """Represents an undefined behavior / strict aliasing violation."""

    timestamp: float
    tag: int
    operation: str
    message: str


class PTPAFSSentry:
    """Sentry enforcing Tree Borrows provenance invariants at runtime."""

    def __init__(self, config: Optional[PTPAFSConfig] = None) -> None:
        self.config = config or PTPAFSConfig()
        self.fsm = TreeBorrowsStateMachine(self.config)
        self.ub_events: List[UndefinedBehaviorEvent] = []

    def record_borrow(self, tag: int, parent: Optional[int], kind: BorrowKind) -> None:
        """Record derivation of a new borrow tag."""
        self.fsm.add_borrow(tag=tag, parent=parent, kind=kind)

    def verify_read(self, tag: int) -> bool:
        """Verify safety of pointer read."""
        ok = self.fsm.process_read(tag)
        if not ok:
            self.ub_events.append(
                UndefinedBehaviorEvent(
                    timestamp=time.time(),
                    tag=tag,
                    operation="read",
                    message=f"Illegal read using disabled tag {tag}",
                )
            )
        return ok

    def verify_write(self, tag: int) -> bool:
        """Verify safety of pointer write."""
        ok = self.fsm.process_write(tag)
        if not ok:
            self.ub_events.append(
                UndefinedBehaviorEvent(
                    timestamp=time.time(),
                    tag=tag,
                    operation="write",
                    message=f"Illegal write using frozen/disabled tag {tag}",
                )
            )
        return ok

    def get_audit_summary(self) -> Dict[str, object]:
        """Return diagnostic metrics of Tree Borrows provenance surveillance."""
        return {
            "total_ub_events": len(self.ub_events),
            "total_nodes": len(self.fsm.nodes),
            "is_sound": len(self.ub_events) == 0,
        }


__all__ = ["UndefinedBehaviorEvent", "PTPAFSSentry"]
