"""Unit tests for CAM-RO Sentry."""

import pytest

try:
    from fault_keeper.systems.ordering_cam_ro.config import CAMROConfig
    from fault_keeper.systems.ordering_cam_ro.engine import MemoryOrder
    from fault_keeper.systems.ordering_cam_ro.sentry import CAMROSentry
except ImportError:
    from ordering_cam_ro.config import CAMROConfig
    from ordering_cam_ro.engine import MemoryOrder
    from ordering_cam_ro.sentry import CAMROSentry


class TestCAMROSentry:
    """Tests for CAMROSentry runtime auditing."""

    def test_sentry_trace_records_and_audits(self) -> None:
        sentry = CAMROSentry()
        sentry.record_operation(thread_id=1, op_type="write", address=0x100, value=42)
        sentry.record_operation(thread_id=1, op_type="read", address=0x200, value=0)

        fences = sentry.audit_trace()
        assert len(fences) >= 1
        summary = sentry.get_audit_summary()
        assert summary["total_operations"] == 2
        assert summary["total_violations"] >= 1
