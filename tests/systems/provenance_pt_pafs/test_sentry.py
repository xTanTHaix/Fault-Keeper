"""Unit tests for PT-PAFS Sentry."""

import pytest

try:
    from fault_keeper.systems.provenance_pt_pafs.config import PTPAFSConfig
    from fault_keeper.systems.provenance_pt_pafs.engine import BorrowKind
    from fault_keeper.systems.provenance_pt_pafs.sentry import PTPAFSSentry
except ImportError:
    from provenance_pt_pafs.config import PTPAFSConfig
    from provenance_pt_pafs.engine import BorrowKind
    from provenance_pt_pafs.sentry import PTPAFSSentry


class TestPTPAFSSentry:
    """Tests for PTPAFSSentry UB surveillance."""

    def test_sentry_detects_illegal_write(self) -> None:
        sentry = PTPAFSSentry()
        sentry.record_borrow(tag=1, parent=None, kind=BorrowKind.SHARED)
        # Shared borrow tag cannot write directly once frozen
        sentry.verify_read(tag=1)
        ok = sentry.verify_write(tag=1)

        assert ok is False
        assert len(sentry.ub_events) == 1
        summary = sentry.get_audit_summary()
        assert summary["is_sound"] is False
