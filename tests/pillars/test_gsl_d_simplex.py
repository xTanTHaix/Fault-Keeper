"""Tests for CSS Layout Simplex Solver."""

from __future__ import annotations

import pytest

from fault_keeper.workflow.gsl_d_simplex import (
    CSSLayoutSimplexSolver,
    LayoutConstraint,
    solve_layout,
)


@pytest.fixture
def solver():
    """Create CSS layout simplex solver instance."""
    return CSSLayoutSimplexSolver()


class TestCSSLayoutSimplexSolver:
    """Tests for CSSLayoutSimplexSolver class."""

    def test_init(self, solver):
        """Test initializing solver."""
        assert isinstance(solver, CSSLayoutSimplexSolver)

    def test_solve_simple(self, solver):
        """Test solving simple layout."""
        constraints = [
            {"type": "width", "value": 100},
            {"type": "height", "value": 200},
        ]
        result = solver.solve(constraints)

        assert result is not None


class TestLayoutConstraint:
    """Tests for LayoutConstraint dataclass."""

    def test_create_constraint(self):
        """Test creating layout constraint."""
        constraint = LayoutConstraint(
            type="flex",
            value=1,
            element="container",
        )

        assert constraint.type == "flex"


class TestSolveLayout:
    """Tests for solve_layout function."""

    def test_solve_valid(self):
        """Test solving valid layout."""
        constraints = [
            {"type": "min_width", "value": 300},
            {"type": "max_height", "value": 400},
        ]
        result = solve_layout(constraints)

        assert result is not None


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_constraints(self, solver):
        """Test with empty constraints."""
        result = solver.solve([])

        assert result is not None

    def test_single_constraint(self, solver):
        """Test with single constraint."""
        result = solver.solve([{"type": "width", "value": 100}])

        assert result is not None


class TestPerformance:
    """Tests for performance."""

    def test_solve_performance(self, solver):
        """Test solving performance."""
        import time

        constraints = [
            {"type": f"constraint_{i}", "value": 100}
            for i in range(20)
        ]

        start_time = time.perf_counter()
        for _ in range(10):
            solver.solve(constraints)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should be fast (< 50ms)
        assert elapsed_ms < 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])