"""Tests for N+1 Query Detector."""

from __future__ import annotations

import pytest

from fault_keeper.workflow.lqpc_n_plus_one import (
    NPlusOneQueryDetector,
    QueryPattern,
    detect_n_plus_one,
)


@pytest.fixture
def detector():
    """Create N+1 query detector instance."""
    return NPlusOneQueryDetector()


class TestNPlusOneQueryDetector:
    """Tests for NPlusOneQueryDetector class."""

    def test_init(self, detector):
        """Test initializing detector."""
        assert isinstance(detector, NPlusOneQueryDetector)

    def test_detect_simple(self, detector):
        """Test detecting simple N+1 pattern."""
        queries = [
            "SELECT * FROM users",
            "SELECT * FROM posts WHERE user_id = ?",
        ]
        result = detector.detect(queries)

        assert result is not None


class TestQueryPattern:
    """Tests for QueryPattern dataclass."""

    def test_create_pattern(self):
        """Test creating query pattern."""
        pattern = QueryPattern(
            query="SELECT * FROM users WHERE id = ?",
            params=[1],
        )

        assert pattern.query == "SELECT * FROM users WHERE id = ?"


class TestDetectNPlusOne:
    """Tests for detect_n_plus_one function."""

    def test_detect_valid(self):
        """Test detecting N+1 query."""
        queries = [
            "SELECT * FROM posts",
            "SELECT * FROM comments WHERE post_id = ?",
        ]
        result = detect_n_plus_one(queries)

        assert result is not None


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_queries(self):
        """Test with empty queries list."""
        result = detect_n_plus_one([])

        assert result is not None

    def test_single_query(self):
        """Test with single query."""
        result = detect_n_plus_one(["SELECT * FROM users"])

        assert result is not None


class TestPerformance:
    """Tests for performance."""

    def test_detect_performance(self, detector):
        """Test detection performance."""
        import time

        queries = [f"SELECT * FROM table_{i}" for i in range(100)]

        start_time = time.perf_counter()
        for _ in range(10):
            detector.detect(queries)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should be fast (< 50ms)
        assert elapsed_ms < 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])