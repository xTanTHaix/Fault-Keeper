"""Tests for Ghost CST Parser."""

from __future__ import annotations

import pytest

from fault_keeper.typing.fsas_ghost_cst import (
    GhostCSTParser,
    CSTNode,
    parse_ghost_cst,
)


@pytest.fixture
def parser():
    """Create Ghost CST parser instance."""
    return GhostCSTParser()


class TestGhostCSTParser:
    """Tests for GhostCSTParser class."""

    def test_init(self, parser):
        """Test initializing parser."""
        assert isinstance(parser, GhostCSTParser)

    def test_parse_simple(self, parser):
        """Test parsing simple CST."""
        source = "x = 1 + 2"
        result = parser.parse(source)

        assert result is not None

    def test_parse_complex(self, parser):
        """Test parsing complex CST."""
        source = """
def foo(x, y):
    return x + y * 2
"""
        result = parser.parse(source)

        assert result is not None


class TestCSTNode:
    """Tests for CSTNode dataclass."""

    def test_create_node(self):
        """Test creating CST node."""
        node = CSTNode(
            type="BINARY_OP",
            value="+",
            left="x",
            right="2",
            line=1,
        )

        assert node.type == "BINARY_OP"


class TestParseGhostCst:
    """Tests for parse_ghost_cst function."""

    def test_parse_valid(self):
        """Test parsing valid CST."""
        source = "a + b"
        result = parse_ghost_cst(source)

        assert result is not None

    def test_parse_invalid(self):
        """Test parsing invalid CST."""
        source = ""
        result = parse_ghost_cst(source)

        assert result is not None


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_string(self):
        """Test with empty string."""
        result = parse_ghost_cst("")

        assert result is not None

    def test_whitespace_only(self):
        """Test with whitespace only."""
        source = "   \n\t  "
        result = parse_ghost_cst(source)

        assert result is not None


class TestPerformance:
    """Tests for performance."""

    def test_parse_performance(self, parser):
        """Test parsing performance."""
        import time

        source = "x" * 1000

        start_time = time.perf_counter()
        for _ in range(10):
            parser.parse(source)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should be fast (< 50ms)
        assert elapsed_ms < 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])