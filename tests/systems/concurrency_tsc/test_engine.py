"""Unit and invariant tests for TSCA Engine."""

import pytest
import numpy as np

try:
    from fault_keeper.systems.concurrency_tsc.config import TSCAConfig
    from fault_keeper.systems.concurrency_tsc.engine import (
        BoundaryMatrixCalculator,
        HomologyEngine,
        SimplicialComplex,
        TSCAEngine,
    )
except ImportError:
    from concurrency_tsc.config import TSCAConfig
    from concurrency_tsc.engine import (
        BoundaryMatrixCalculator,
        HomologyEngine,
        SimplicialComplex,
        TSCAEngine,
    )


class TestSimplicialComplex:
    """Tests for abstract simplicial complex data structure and closure properties."""

    def test_vertex_and_edge_addition(self) -> None:
        sc = SimplicialComplex()
        sc.add_vertex(10)
        sc.add_edge(10, 20)
        assert 10 in sc.vertices
        assert 20 in sc.vertices
        assert (10, 20) in sc.edges

    def test_face_addition_creates_boundary_edges(self) -> None:
        sc = SimplicialComplex()
        sc.add_face(1, 2, 3)
        assert (1, 2, 3) in sc.faces
        assert (1, 2) in sc.edges
        assert (2, 3) in sc.edges
        assert (1, 3) in sc.edges
        assert len(sc.vertices) == 3

    def test_simplex_closure(self) -> None:
        sc = SimplicialComplex()
        sc.add_simplex((4, 5, 6))
        assert (4, 5, 6) in sc.faces
        assert (4, 5) in sc.edges
        assert 4 in sc.vertices


class TestHomologyEngine:
    """Tests for homology group computation and Betti numbers over GF(2)."""

    def test_acyclic_tree_has_zero_first_betti(self) -> None:
        sc = SimplicialComplex()
        sc.add_edge(0, 1)
        sc.add_edge(1, 2)
        sc.add_edge(2, 3)

        homology = HomologyEngine(sc)
        assert homology.compute_first_betti() == 0
        assert homology.is_deadlock_free() is True

    def test_cycle_without_filling_has_first_betti_one(self) -> None:
        sc = SimplicialComplex()
        sc.add_edge(0, 1)
        sc.add_edge(1, 2)
        sc.add_edge(2, 0)

        homology = HomologyEngine(sc)
        assert homology.compute_first_betti() == 1
        assert homology.is_deadlock_free() is False

    def test_filled_triangle_becomes_contractible(self) -> None:
        sc = SimplicialComplex()
        sc.add_face(0, 1, 2)

        homology = HomologyEngine(sc)
        # With 2-simplex filled, cycle is a boundary -> beta_1 == 0
        assert homology.compute_first_betti() == 0
        assert homology.is_deadlock_free() is True

    def test_figure_eight_double_cycle(self) -> None:
        sc = SimplicialComplex()
        # First cycle: 0-1-2-0
        sc.add_edge(0, 1)
        sc.add_edge(1, 2)
        sc.add_edge(2, 0)
        # Second cycle: 2-3-4-2
        sc.add_edge(2, 3)
        sc.add_edge(3, 4)
        sc.add_edge(4, 2)

        homology = HomologyEngine(sc)
        assert homology.compute_first_betti() == 2


class TestTSCAEngine:
    """Tests for TSCAEngine orchestration and topology analysis."""

    def test_engine_topology_analysis(self) -> None:
        engine = TSCAEngine()
        engine.register_transition(100, 200)
        engine.register_transition(200, 300)
        analysis = engine.analyze_topology()
        assert analysis["is_deadlock_free"] is True
        assert analysis["first_betti_number"] == 0
