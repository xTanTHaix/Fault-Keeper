"""Unit tests for DIS-RA Sentry."""

import pytest

try:
    from fault_keeper.systems.io_uring_dis_ra.config import DISRAConfig
    from fault_keeper.systems.io_uring_dis_ra.sentry import DISRASentry
except ImportError:
    from io_uring_dis_ra.config import DISRAConfig
    from io_uring_dis_ra.sentry import DISRASentry


class TestDISRASentry:
    """Tests for DISRASentry ring surveillance."""

    def test_sentry_backpressure_throttling(self) -> None:
        cfg = DISRAConfig(default_sq_entries=10, backpressure_threshold=0.50)
        sentry = DISRASentry(cfg)

        for i in range(5):
            assert sentry.submit_operation(0, 1, 0, 100, i) is True

        # 6th operation throttles due to 50% threshold
        accepted = sentry.submit_operation(0, 1, 0, 100, 99)
        assert accepted is False
        assert len(sentry.events) >= 1

        summary = sentry.get_audit_summary()
        assert summary["is_zero_overflow"] is True
        assert summary["throttled_count"] >= 1
