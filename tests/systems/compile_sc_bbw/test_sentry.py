"""Unit tests for SC-BBW Sentry."""

import pytest

try:
    from fault_keeper.systems.compile_sc_bbw.config import SCBBWConfig
    from fault_keeper.systems.compile_sc_bbw.engine import ControlFlowGraph
    from fault_keeper.systems.compile_sc_bbw.sentry import SCBBWSentry
except ImportError:
    from compile_sc_bbw.config import SCBBWConfig
    from compile_sc_bbw.engine import ControlFlowGraph
    from compile_sc_bbw.sentry import SCBBWSentry


class TestSCBBWSentry:
    """Tests for SCBBWSentry layout optimization and metrics."""

    def test_sentry_cfg_optimization(self) -> None:
        sentry = SCBBWSentry()
        cfg = ControlFlowGraph()
        # Non-optimal initial order: 0 connects heavily to 2, 1 is in between
        cfg.add_edge(0, 2, weight=50.0)
        cfg.add_edge(2, 1, weight=5.0)

        metric = sentry.optimize_cfg(cfg)
        assert len(metric.reordered_sequence) == 3
        assert metric.optimized_penalty <= metric.original_penalty
