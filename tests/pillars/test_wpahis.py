"""WPA-HIS: Whole-Project Architectural Dependency Graph — 1:1 invariant tests.

Covers Martin's distance invariant, FAS minimal-cut optimality, Newman's
modularity bound, blast-radius propagation and the triage dispatcher.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import pytest

from fault_keeper.audit.wpahis import (
    ProjectGraph,
    analyse_project,
    build_project_graph,
    compute_acyclic_score,
    compute_blast_radius_scores,
    compute_distance_score,
    compute_martin_metrics,
    compute_modularity_score,
)


def _graph(edges):
    graph = ProjectGraph()
    for src, dst in edges:
        graph.add_edge(src, dst)
    return graph


# ---------------------------------------------------------------------------
# Test 2.2.2 — Martin's Distance Invariant (D = |A + I - 1|)
# ---------------------------------------------------------------------------

def test_martin_distance_abstract_module_is_balanced():
    """Abstract class: A=1, I=0 => D = |1 + 0 - 1| = 0."""
    graph = ProjectGraph()
    graph.add_edge("consumer", "provider")  # provider <- consumer (consumer imports provider)
    # provider has out-degree 0, in-degree 1 => A=0, I=1, D=0
    # consumer has out-degree 1, in-degree 0 => A=1, I=0, D=0
    avg_a, avg_i, avg_d = compute_martin_metrics(graph)
    assert avg_a == pytest.approx(0.5, abs=1e-6)
    assert avg_i == pytest.approx(0.5, abs=1e-6)
    assert avg_d == pytest.approx(0.0, abs=1e-6)


def test_martin_distance_score_perfect_when_balanced():
    """D = 0 => S_distance = 100."""
    graph = _graph([("a", "b"), ("c", "d")])
    _, _, avg_d = compute_martin_metrics(graph)
    assert avg_d == pytest.approx(0.0, abs=1e-6)
    assert compute_distance_score(avg_d) == pytest.approx(100.0, abs=1e-3)


def test_martin_distance_decreases_with_imbalance():
    """A hub with many outgoing edges has large distance from main sequence."""
    # star: center imports leaves; center out-degree 3, in-degree 0 => A=1, I=0, D=1
    graph = _graph([("center", "l1"), ("center", "l2"), ("center", "l3")])
    _, _, avg_d = compute_martin_metrics(graph)
    assert avg_d == pytest.approx(1.0, abs=1e-6)
    score = compute_distance_score(avg_d)
    assert score == pytest.approx(0.0, abs=1e-3)


# ---------------------------------------------------------------------------
# Test 2.2.1 — Feedback Arc Set Minimal Cut Optimality
# ---------------------------------------------------------------------------

def test_fas_minimal_cut_on_directed_cycle():
    """Cycle A->B->C->A: cutting exactly one edge breaks the cycle."""
    graph = _graph([("A", "B"), ("B", "C"), ("C", "A")])
    fas_edges = [("A", "B")]  # remove this edge
    score = compute_acyclic_score(graph, fas_edges)
    assert 0.33 <= score <= 0.67
    # One of three edges removed => two cyclic edges remain => S = 1 - 2/3 = 1/3
    assert score == pytest.approx(1 / 3, abs=1e-3)


def test_fas_all_edges_cut_yields_full_score():
    """Cutting every edge => no residual cycles => S_acyclic = 1."""
    graph = _graph([("A", "B"), ("B", "C"), ("C", "A")])
    score = compute_acyclic_score(graph, [("A", "B"), ("B", "C"), ("C", "A")])
    assert score == pytest.approx(1.0, abs=1e-3)


def test_fas_empty_cut_on_acyclic_graph_is_full():
    """An already-acyclic graph needs no cuts => S = 1."""
    graph = _graph([("A", "B"), ("C", "D")])
    assert compute_acyclic_score(graph, []) == pytest.approx(1.0, abs=1e-3)


def test_fas_cut_score_never_negative():
    graph = _graph([("A", "B"), ("B", "C"), ("C", "A")])
    score = compute_acyclic_score(graph, [("A", "B")])
    assert score >= 0.0


# ---------------------------------------------------------------------------
# Test 2.2.3 — Newman's Modularity Q Bound
# ---------------------------------------------------------------------------

def test_modularity_two_communities_is_high():
    """Two dense cliques with no inter-community edges => Q near its max."""
    # Community 1: {A,B,C}; Community 2: {D,E,F}; no cross edges.
    graph = _graph([
        ("A", "B"), ("B", "C"), ("C", "A"),
        ("D", "E"), ("E", "F"), ("F", "D"),
    ])
    q = compute_modularity_score(graph)
    assert -0.5 <= q <= 1.0
    # Two fully separated cliques yield a high modularity value.
    assert q > 0.4


def test_modularity_single_community_is_low():
    """A single clique with no community structure => Q near 0."""
    graph = _graph([("A", "B"), ("B", "C"), ("C", "A")])
    q = compute_modularity_score(graph)
    assert -0.5 <= q <= 1.0
    assert q < 0.4


def test_modularity_empty_graph_is_zero():
    graph = ProjectGraph()
    assert compute_modularity_score(graph) == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Blast Radius + Triage
# ---------------------------------------------------------------------------

def test_blast_radius_propagates_downstream_edges():
    """A module at the top of a chain reaches every downstream module."""
    graph = _graph([("A", "B"), ("B", "C"), ("C", "D")])
    scores = compute_blast_radius_scores(graph)
    # A is upstream; its blast cone should include B, C, D.
    assert set(scores.keys()) == {"A", "B", "C", "D"}
    assert len(scores["A"]) == 3  # reaches B, C, D
    assert len(scores["D"]) == 0  # leaf: no downstream


def test_blast_radius_cycle_reaches_all():
    graph = _graph([("A", "B"), ("B", "C"), ("C", "A")])
    scores = compute_blast_radius_scores(graph)
    assert len(scores["A"]) == 3


def test_triage_dispatcher_returns_actionable_targets():
    """analyse_project must return refactoring targets with severities."""
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        for name in ["alpha.py", "beta.py", "gamma.py"]:
            with open(os.path.join(tmp, name), "w") as fh:
                fh.write("x = 1\n")
        report = analyse_project(tmp)
    assert isinstance(report, dict)
    targets = report.get("refactoring_targets", [])
    assert isinstance(targets, list)
    for target in targets:
        assert "severity" in target
        assert target["severity"] in {"info", "low", "medium", "high", "critical"}


def test_discover_modules_and_build_graph_roundtrip():
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        # beta imports alpha; gamma imports beta.
        with open(os.path.join(tmp, "alpha.py"), "w") as fh:
            fh.write("VALUE = 1\n")
        with open(os.path.join(tmp, "beta.py"), "w") as fh:
            fh.write("from alpha import VALUE\n")
        with open(os.path.join(tmp, "gamma.py"), "w") as fh:
            fh.write("from beta import VALUE\n")

        modules = build_project_graph(tmp)
        assert set(modules.keys()) == {"alpha", "beta", "gamma"}

        discovered = discover_modules(tmp)
        assert set(discovered) == {"alpha.py", "beta.py", "gamma.py"}


def test_parse_imports_extracts_top_level_modules():
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "svc.py")
        with open(path, "w") as fh:
            fh.write("import numpy\nfrom . import other\nimport fault_keeper.audit.ufsr\n")
        imports = parse_imports(path)
        assert "numpy" in imports
        assert "other" in imports
        assert "fault_keeper" in imports


def test_analyse_project_detects_circular_dependency():
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        a = os.path.join(tmp, "a.py")
        b = os.path.join(tmp, "b.py")
        with open(a, "w") as fh:
            fh.write("from b import x\n")
        with open(b, "w") as fh:
            fh.write("from a import y\n")
        report = analyse_project(tmp)
    assert "circular_dependencies" in report
    assert len(report["circular_dependencies"]) >= 1
