"""Unit tests for SABA Sentry."""

import pytest

try:
    from fault_keeper.systems.vector_saba.config import SABAConfig
    from fault_keeper.systems.vector_saba.sentry import SABASentry
except ImportError:
    from vector_saba.config import SABAConfig
    from vector_saba.sentry import SABASentry


class TestSABASentry:
    """Tests for SABASentry loop inspection."""

    def test_inspect_clean_vectorizable_loop(self) -> None:
        sentry = SABASentry()
        res = sentry.inspect_loop(
            loop_id="loop_matmul_inner",
            write_offset=0,
            read_offset=0,
            ptr_a=0x1000,
            size_a=256,
            ptr_b=0x2000,
            size_b=256,
        )
        assert res["can_vectorize"] is True
        assert len(res["inhibitors"]) == 0

    def test_inspect_inhibited_by_aliasing(self) -> None:
        sentry = SABASentry()
        res = sentry.inspect_loop(
            loop_id="loop_copy_overlap",
            write_offset=0,
            read_offset=0,
            ptr_a=0x1000,
            size_a=128,
            ptr_b=0x1040,
            size_b=128,
        )
        assert res["can_vectorize"] is False
        assert res["aliasing_detected"] is True
        assert sentry.get_audit_summary()["is_clean"] is False
