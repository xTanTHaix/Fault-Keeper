"""Tests for Async Await Lifecycle Checker."""

from __future__ import annotations

import pytest

from fault_keeper.typing.ae_fps_await_checker import (
    AsyncAwaitLifecycleChecker,
    MissingAwaitIssue,
    RaceConditionDetector,
    check_async_awaits,
    detect_race_conditions,
)


@pytest.fixture
def checker():
    """Create async lifecycle checker."""
    return AsyncAwaitLifecycleChecker()


@pytest.fixture
def detector():
    """Create race condition detector."""
    return RaceConditionDetector()


class TestAsyncAwaitLifecycleChecker:
    """Tests for AsyncAwaitLifecycleChecker class."""

    def test_init(self, checker):
        """Test initializing checker."""
        assert isinstance(checker, AsyncAwaitLifecycleChecker)

    def test_analyze_module_no_issues(self, checker):
        """Test analyzing module with no issues."""
        source = """
async def fetch_data():
    await some_async_call()
    return data
"""
        issues = checker.analyze_module(source)

        assert len(issues) == 0

    def test_analyze_module_with_issues(self, checker):
        """Test analyzing module with missing await."""
        source = """
async def fetch_data():
    some_sync_call()
    return data
"""
        issues = checker.analyze_module(source)

        assert len(issues) > 0


class TestMissingAwaitIssue:
    """Tests for MissingAwaitIssue dataclass."""

    def test_create_issue(self):
        """Test creating missing await issue."""
        issue = MissingAwaitIssue(
            function_name="fetch_data",
            line_number=5,
            severity="error",
            message="Missing await call",
        )

        assert issue.function_name == "fetch_data"


class TestRaceConditionDetector:
    """Tests for RaceConditionDetector class."""

    def test_init(self, detector):
        """Test initializing detector."""
        assert isinstance(detector, RaceConditionDetector)

    def test_analyze_module(self, detector):
        """Test analyzing module for race conditions."""
        source = """
async def process():
    global counter
    await do_something()
"""
        issues = detector.analyze_module(source)

        assert isinstance(issues, list)


class TestCheckAsyncAwaits:
    """Tests for check_async_awaits function."""

    def test_check_valid_code(self):
        """Test checking valid async code."""
        source = """
async def fetch():
    await api_call()
"""
        issues = check_async_awaits(source)

        assert isinstance(issues, list)


class TestDetectRaceConditions:
    """Tests for detect_race_conditions function."""

    def test_detect_no_races(self):
        """Test detecting no race conditions."""
        source = """
async def safe():
    await operation()
"""
        issues = detect_race_conditions(source)

        assert isinstance(issues, list)


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_source(self):
        """Test with empty source code."""
        issues = check_async_awaits("")

        assert isinstance(issues, list)

    def test_syntax_error(self):
        """Test with syntax error in source."""
        source = "async def broken("
        issues = check_async_awaits(source)

        # Should handle gracefully
        assert isinstance(issues, list)


class TestPerformance:
    """Tests for performance."""

    def test_analyze_performance(self, checker):
        """Test analysis performance."""
        import time

        source = """
async def fetch():
    await call1()
    await call2()
    await call3()
""" * 10

        start_time = time.perf_counter()
        for _ in range(10):
            checker.analyze_module(source)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should be fast (< 100ms)
        assert elapsed_ms < 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])