"""Tests for SIMD Trigram Searcher."""

from __future__ import annotations

import pytest

from fault_keeper.workflow.stas_simd_trigram import (
    STASimDTrigramSearcher,
    TrigramIndex,
    search_trigrams,
)


@pytest.fixture
def searcher():
    """Create SIMD trigram searcher instance."""
    return STASimDTrigramSearcher()


class TestSTASimDTrigramSearcher:
    """Tests for STASimDTrigramSearcher class."""

    def test_init(self, searcher):
        """Test initializing searcher."""
        assert isinstance(searcher, STASimDTrigramSearcher)

    def test_search_simple(self, searcher):
        """Test simple trigram search."""
        text = "hello world"
        result = searcher.search(text)

        assert result is not None


class TestTrigramIndex:
    """Tests for TrigramIndex dataclass."""

    def test_create_index(self):
        """Test creating trigram index."""
        index = TrigramIndex(
            text="hello world",
            trigrams=["hel", "ell", "llo", "lo ", "o w", " wo", "ord", "rld"],
        )

        assert index.text == "hello world"


class TestSearchTrigrams:
    """Tests for search_trigrams function."""

    def test_search_valid(self):
        """Test searching trigrams."""
        text = "hello world"
        result = search_trigrams(text)

        assert result is not None


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_text(self, searcher):
        """Test with empty text."""
        result = searcher.search("")

        assert result is not None

    def test_none_text(self, searcher):
        """Test with None text."""
        try:
            result = searcher.search(None)
        except Exception:
            pass  # Expected behavior


class TestPerformance:
    """Tests for performance."""

    def test_search_performance(self, searcher):
        """Test search performance."""
        import time

        text = "hello world" * 100

        start_time = time.perf_counter()
        for _ in range(10):
            searcher.search(text)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should be fast (< 50ms)
        assert elapsed_ms < 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])