"""Unit and invariant tests for AC-SBE Engine."""

import ast
import pytest

try:
    from fault_keeper.systems.yield_ac_sbe.config import ACSBEConfig
    from fault_keeper.systems.yield_ac_sbe.engine import (
        AutoYieldTransformer,
        BlockingLoopDetector,
        LoopCostEstimator,
    )
except ImportError:
    from yield_ac_sbe.config import ACSBEConfig
    from yield_ac_sbe.engine import (
        AutoYieldTransformer,
        BlockingLoopDetector,
        LoopCostEstimator,
    )


class TestLoopCostEstimator:
    """Tests for AST loop complexity scoring."""

    def test_cost_estimation_scales_with_operations(self) -> None:
        simple_code = "for i in range(10): x = 1"
        heavy_code = "for i in range(10): [foo(k * 2) for k in range(100)]"

        estimator = LoopCostEstimator()
        cost_simple = estimator.estimate_cost(ast.parse(simple_code))
        cost_heavy = estimator.estimate_cost(ast.parse(heavy_code))

        assert cost_heavy > cost_simple


class TestBlockingLoopDetector:
    """Tests for detection of CPU-heavy synchronous loops in async code."""

    def test_detects_blocking_async_for(self) -> None:
        code = """
async def worker():
    for i in range(1000):
        val = i * 2
"""
        tree = ast.parse(code)
        detector = BlockingLoopDetector()
        blocking = detector.detect_blocking_loops(tree)
        assert len(blocking) == 1

    def test_ignores_loop_with_await(self) -> None:
        code = """
async def worker():
    for i in range(1000):
        await asyncio.sleep(0.01)
"""
        tree = ast.parse(code)
        detector = BlockingLoopDetector()
        blocking = detector.detect_blocking_loops(tree)
        assert len(blocking) == 0


class TestAutoYieldTransformer:
    """Tests for AST rewriting and cooperative preemption injection."""

    def test_injects_sleep_into_blocking_loop(self) -> None:
        code = """
async def worker():
    for i in range(1000):
        calc = i + 1
"""
        tree = ast.parse(code)
        transformer = AutoYieldTransformer(cadence=100)
        new_tree = transformer.transform(tree)
        unparsed = ast.unparse(new_tree)

        assert "asyncio.sleep(0)" in unparsed
        assert transformer.injected_count == 1
