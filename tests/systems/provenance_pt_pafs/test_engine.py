"""Unit and invariant tests for PT-PAFS Engine."""

import pytest

try:
    from fault_keeper.systems.provenance_pt_pafs.config import PTPAFSConfig
    from fault_keeper.systems.provenance_pt_pafs.engine import (
        BorrowKind,
        BorrowState,
        ProvenanceRegistry,
        TreeBorrowsStateMachine,
    )
except ImportError:
    from provenance_pt_pafs.config import PTPAFSConfig
    from provenance_pt_pafs.engine import (
        BorrowKind,
        BorrowState,
        ProvenanceRegistry,
        TreeBorrowsStateMachine,
    )


class TestTreeBorrowsStateMachine:
    """Tests for Tree Borrows operational state transitions."""

    def test_shared_borrow_transitions_to_frozen_on_read(self) -> None:
        fsm = TreeBorrowsStateMachine()
        fsm.add_borrow(tag=1, parent=None, kind=BorrowKind.MUTABLE)
        fsm.add_borrow(tag=2, parent=1, kind=BorrowKind.SHARED)

        assert fsm.get_state(2) == BorrowState.RESERVED
        ok = fsm.process_read(tag=2)
        assert ok is True
        assert fsm.get_state(2) == BorrowState.FROZEN

    def test_foreign_write_disables_shared_borrow(self) -> None:
        fsm = TreeBorrowsStateMachine()
        fsm.add_borrow(tag=1, parent=None, kind=BorrowKind.MUTABLE)
        fsm.add_borrow(tag=2, parent=1, kind=BorrowKind.SHARED)

        # Write on tag 1 is a foreign write to tag 2
        fsm.process_write(tag=1)
        assert fsm.get_state(2) == BorrowState.DISABLED

        # Subsequent read on tag 2 is illegal
        ok = fsm.process_read(tag=2)
        assert ok is False


class TestProvenanceRegistry:
    """Tests for ProvenanceRegistry address tracking."""

    def test_allocation_and_access(self) -> None:
        registry = ProvenanceRegistry()
        registry.register_allocation(address=0x5000, root_tag=10)
        registry.derive_pointer(parent_tag=10, new_tag=11, kind=BorrowKind.MUTABLE)

        # Write through tag 11 should succeed
        assert registry.check_access(tag=11, is_write=True) is True
