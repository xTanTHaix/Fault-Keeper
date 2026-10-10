"""Tests for Fast Test Suite Selection (Test Pruner)."""

from __future__ import annotations

import pytest

from fault_keeper.workflow.ptho import (
    TestSuitePruner,
    TestPriority,
    prune_test_suite,
)


@pytest.fixture
def pruner():
    """Create test suite pruner instance."""
    return TestSuitePruner()


class TestTestSuitePruner:
    """Tests for TestSuitePruner class."""

    def test_init(self, pruner):
        """Test initializing pruner."""
        assert isinstance(pruner, TestSuitePruner)

    def test_prune_simple(self, pruner):
        """Test pruning simple test suite."""
        tests = ["test_a.py", "test_b.py", "test_c.py"]
        result = pruner.prune(tests, max_tests=2)

        assert len(result) <= 2

    def test_prune_by_priority(self, pruner):
        """Test pruning by priority."""
        tests = [
            {"name": "fast_test", "priority": TestPriority.HIGH},
            {"name": "slow_test", "priority": TestPriority.LOW},
        ]
        result = pruner.prune_by_priority(tests, max_tests=1)

        assert len(result) == 1


class TestTestPriority:
    """Tests for TestPriority enum."""

    def test_high_priority(self):
        """Test high priority value."""
        assert TestPriority.HIGH.value > TestPriority.LOW.value


class TestPruneTestSuite:
    """Tests for prune_test_suite function."""

    def test_prune_valid(self):
        """Test pruning valid test suite."""
        tests = ["test_1.py", "test_2.py"]
        result = prune_test_suite(tests, max_tests=1)

        assert len(result) == 1


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_list(self):
        """Test with empty list."""
        result = prune_test_suite([], max_tests=5)

        assert result == []

    def test_none_max_tests(self):
        """Test with None max tests."""
        tests = ["test_a.py"]
        result = prune_test_suite(tests, max_tests=None)

        assert len(result) == 1


class TestPerformance:
    """Tests for performance."""

    def test_prune_performance(self, pruner):
        """Test pruning performance."""
        import time

        tests = [f"test_{i}.py" for i in range(100)]

        start_time = time.perf_counter()
        for _ in range(10):
            pruner.prune(tests, max_tests=10)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should be fast (< 50ms)
        assert elapsed_ms < 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])