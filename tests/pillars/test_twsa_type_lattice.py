"""Tests for Type Lattice Auto-Complete."""

from __future__ import annotations

import pytest

from fault_keeper.typing.twsa_type_lattice import (
    TypeLatticeAutoComplete,
    TypeLatticeNode,
    compute_lattice_distance,
)


@pytest.fixture
def lattice():
    """Create type lattice auto-complete instance."""
    return TypeLatticeAutoComplete()


class TestTypeLatticeAutoComplete:
    """Tests for TypeLatticeAutoComplete class."""

    def test_init(self, lattice):
        """Test initializing lattice."""
        assert isinstance(lattice, TypeLatticeAutoComplete)

    def test_complete_simple(self, lattice):
        """Test simple auto-complete."""
        prefix = "def "
        suggestions = lattice.complete(prefix)

        assert isinstance(suggestions, list)

    def test_complete_complex(self, lattice):
        """Test complex auto-complete."""
        prefix = "async def fetch"
        suggestions = lattice.complete(prefix)

        assert isinstance(suggestions, list)


class TestTypeLatticeNode:
    """Tests for TypeLatticeNode dataclass."""

    def test_create_node(self):
        """Test creating lattice node."""
        node = TypeLatticeNode(
            name="int",
            depth=0,
            children=[],
        )

        assert node.name == "int"


class TestComputeLatticeDistance:
    """Tests for compute_lattice_distance function."""

    def test_compute_distance(self):
        """Test computing lattice distance."""
        result = compute_lattice_distance("int", "float")

        assert isinstance(result, (int, float))


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_prefix(self, lattice):
        """Test with empty prefix."""
        suggestions = lattice.complete("")

        assert isinstance(suggestions, list)

    def test_none_prefix(self, lattice):
        """Test with None prefix."""
        try:
            suggestions = lattice.complete(None)
        except Exception:
            pass  # Expected behavior


class TestPerformance:
    """Tests for performance."""

    def test_complete_performance(self, lattice):
        """Test auto-complete performance."""
        import time

        prefix = "def foo"

        start_time = time.perf_counter()
        for _ in range(10):
            lattice.complete(prefix)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should be fast (< 50ms)
        assert elapsed_ms < 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])