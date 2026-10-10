"""Unit tests for AC-SBE Sentry."""

import time
import pytest

try:
    from fault_keeper.systems.yield_ac_sbe.config import ACSBEConfig
    from fault_keeper.systems.yield_ac_sbe.sentry import ACSBESentry
except ImportError:
    from yield_ac_sbe.config import ACSBEConfig
    from yield_ac_sbe.sentry import ACSBESentry


class TestACSBESentry:
    """Tests for ACSBESentry event loop auditing."""

    def test_audit_module_code(self) -> None:
        sentry = ACSBESentry()
        sample = """
async def compute(x):
    total = 0
    for i in range(x):
        total += i
    return total
"""
        res = sentry.audit_module_code(sample)
        assert res["blocking_loop_count"] == 1
        assert res["injected_yields"] == 1
        assert "asyncio.sleep(0)" in str(res["transformed_code"])

    def test_record_heartbeat_stall_detection(self) -> None:
        cfg = ACSBEConfig(stall_threshold_sec=0.01)
        sentry = ACSBESentry(cfg)
        time.sleep(0.02)
        stall = sentry.record_heartbeat()
        assert stall is not None
        assert stall.duration_sec >= 0.01
