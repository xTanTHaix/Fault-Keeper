"""Unit tests for TSCA Sentry and runtime deadlock auditing."""

import pytest

try:
    from fault_keeper.systems.concurrency_tsc.config import TSCAConfig
    from fault_keeper.systems.concurrency_tsc.sentry import TSCASentry, DeadlockAlert
except ImportError:
    from concurrency_tsc.config import TSCAConfig
    from concurrency_tsc.sentry import TSCASentry, DeadlockAlert


class TestTSCASentry:
    """Tests for TSCASentry runtime deadlock detection."""

    def test_safe_linear_acquisitions(self) -> None:
        sentry = TSCASentry()
        sentry.record_acquisition(thread_id=1, resource_id=101)
        sentry.record_acquisition(thread_id=2, resource_id=102)

        audit = sentry.audit_concurrency_invariants()
        assert audit["is_deadlock_free"] is True
        assert audit["active_alerts"] == 0

    def test_circular_wait_triggers_deadlock_alert(self) -> None:
        sentry = TSCASentry()
        # Thread 1 holds Resource 101, Thread 2 holds Resource 102
        sentry.record_acquisition(thread_id=1, resource_id=101)
        sentry.record_acquisition(thread_id=2, resource_id=102)

        # Thread 1 waits for Resource 102 (held by 2) -> edge 1 -> 2
        sentry.record_wait(thread_id=1, resource_id=102)

        # Thread 2 waits for Resource 101 (held by 1) -> edge 2 -> 1 (Cycle!)
        alert = sentry.record_wait(thread_id=2, resource_id=101)

        assert alert is not None
        assert isinstance(alert, DeadlockAlert)
        assert alert.betti_1 >= 1

        audit = sentry.audit_concurrency_invariants()
        assert audit["is_deadlock_free"] is False
        assert audit["active_alerts"] >= 1
