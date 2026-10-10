"""Adversarial stress test harness for M1 Challenger 2.

Tests Typing, Fullstack, and Workflow modules under hostile edge cases:
1. twsa_type_lattice.py
2. zec_sw_migration.py
3. ptho.py
4. gsl_d_simplex
5. lqpc_n_plus_one.py
"""

from __future__ import annotations

import asyncio
import math
import sys
import time
from pathlib import Path

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fault_keeper.typing.twsa_type_lattice import (
    TypeLatticeGraph,
    TypeNode,
    FuzzyMatcher,
    TypeLatticeAutoComplete,
    compute_lattice_distance,
)
from fault_keeper.fullstack.zec_sw_migration import (
    MigrationPlan,
    SchemaVersion,
    execute_zero_downtime_migration,
    validate_schema_version,
)
from fault_keeper.workflow.ptho import (
    TestSuitePruner,
    TestPriority,
    ImpactGraphBuilder,
)
from fault_keeper.workflow.gsl_d_simplex import (
    CSSLayoutSimplexSolver,
    solve_layout,
)
from fault_keeper.fullstack.gsl_d_simplex import (
    SimplexSolver,
)
from fault_keeper.workflow.lqpc_n_plus_one import (
    NPlusOneQueryDetector,
    NPlusOnePattern,
    detect_n_plus_one,
)


def test_domain_1_typing():
    print("\n=== DOMAIN 1: TYPING (twsa_type_lattice) ===")
    
    # 1.1 Deeply nested lattice performance
    g = TypeLatticeGraph()
    for i in range(150):
        parents = [f"Node_{i-1}"] if i > 0 else []
        g.add_node(TypeNode(f"Node_{i}", str(i), "class", parents=parents))
        if i > 0:
            g.add_edge(f"Node_{i}", f"Node_{i-1}", "subtype")
    
    m = FuzzyMatcher(g)
    t0 = time.perf_counter()
    m.compute_distances()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    print(f"[1.1] Deeply nested lattice (150 nodes) compute_distances time: {elapsed_ms:.2f}ms (Claimed SLA: < 0.5ms)")
    assert elapsed_ms > 10.0, "Expected significant latency on N^2 BFS"

    # 1.2 Cyclic type lattice
    g_cyc = TypeLatticeGraph()
    g_cyc.add_node(TypeNode("A", "1", "class", parents=["B"]))
    g_cyc.add_node(TypeNode("B", "2", "class", parents=["C"]))
    g_cyc.add_node(TypeNode("C", "3", "class", parents=["A"]))
    g_cyc.add_edge("A", "B", "subtype")
    g_cyc.add_edge("B", "C", "subtype")
    g_cyc.add_edge("C", "A", "subtype")
    dist_ab = compute_lattice_distance("A", "B", g_cyc)
    dist_ac = compute_lattice_distance("A", "C", g_cyc)
    print(f"[1.2] Cyclic lattice distances: A->B: {dist_ab}, A->C: {dist_ac}")

    # 1.3 Disjoint type lattice distance fallback
    g_disj = TypeLatticeGraph()
    g_disj.add_node(TypeNode("CustomAlpha", "1", "class"))
    g_disj.add_node(TypeNode("CustomBeta", "2", "class"))
    dist_disj = compute_lattice_distance("CustomAlpha", "CustomBeta", g_disj)
    print(f"[1.3] Disjoint type lattice distance: {dist_disj} (Fell back to Levenshtein distance instead of inf/error)")


def test_domain_2_fullstack():
    print("\n=== DOMAIN 2: FULLSTACK (zec_sw_migration) ===")

    # 2.1 Concurrent migration ID collisions
    async def run_concurrent():
        plans = [MigrationPlan(source_schema="accounts", target_schema="accounts_v2") for _ in range(25)]
        results = await asyncio.gather(*(execute_zero_downtime_migration(p) for p in plans))
        ids = [r["migration_id"] for r in results]
        unique_ids = len(set(ids))
        print(f"[2.1] Concurrent migrations: {len(results)} tasks, unique migration_ids: {unique_ids}")
        assert unique_ids == 1, "Expected 100% ID collision due to int(timestamp) granularity"
    asyncio.run(run_concurrent())

    # 2.2 Checksum tampering
    sv = SchemaVersion("v1.0.0", [{"action": "ADD_COLUMN", "table": "users", "column": "email"}])
    sv.checksum = "TAMPERED_CHECKSUM_12345"
    res = validate_schema_version(sv)
    print(f"[2.2] Tampered checksum validation: valid={res['valid']}, errors={res['errors']}")
    assert res["valid"] is True, "validate_schema_version silently accepted tampered checksum"


def test_domain_3_workflow_ptho():
    print("\n=== DOMAIN 3: WORKFLOW (ptho) ===")

    # 3.1 Invalid priority ordering
    pruner = TestSuitePruner()
    try:
        pruner.prune_by_priority([{"name": "test_1", "priority": None}, {"name": "test_2", "priority": TestPriority.HIGH}], max_tests=2)
        print("[3.1] Priority None test unexpectedly succeeded")
    except TypeError as e:
        print(f"[3.1] Priority None test raised TypeError: {e}")

    try:
        pruner.prune_by_priority([{"test_id": "test_1", "priority": 1}], max_tests=1)
        print("[3.1] Missing 'name' test unexpectedly succeeded")
    except KeyError as e:
        print(f"[3.1] Missing 'name' key raised KeyError: {e}")

    # 3.2 ImpactGraphBuilder subpackage reverse dependency loss
    builder = ImpactGraphBuilder(".")
    builder.discover_and_build()
    affected = builder.get_affected_tests(["src/fault_keeper/typing/twsa_type_lattice.py"])
    print(f"[3.2] Affected tests for twsa_type_lattice.py: {affected} (Actual test exists: tests/pillars/test_twsa_type_lattice.py)")


def test_domain_4_workflow_simplex():
    print("\n=== DOMAIN 4: WORKFLOW/FULLSTACK (gsl_d_simplex) ===")

    # 4.1 Contradictory / Infeasible constraints in CSSLayoutSimplexSolver
    solver = CSSLayoutSimplexSolver()
    solver.add_element("ElemA", width=100.0)
    solver.add_element("ElemB", width=100.0)
    solver.add_constraint("ElemA", "ElemB", "left_of")
    solver.add_constraint("ElemB", "ElemA", "left_of")
    res = solver.solve()
    print(f"[4.1] Infeasible constraints solve: success={res['success']}, satisfied={res['n_constraints_satisfied']}, elements={res['elements']}")

    # 4.2 SimplexSolver rectangular matrix crash (more vars than constraints)
    s = SimplexSolver()
    s.matrix_a = [[1.0, 2.0, 3.0]]
    s.vector_b = [100.0]
    s.variables = ["x", "y", "z"]
    try:
        s.solve()
        print("[4.2] SimplexSolver unexpectedly succeeded on rectangular matrix")
    except IndexError as e:
        print(f"[4.2] SimplexSolver raised IndexError on rectangular matrix: {e}")


def test_domain_5_workflow_lqpc():
    print("\n=== DOMAIN 5: WORKFLOW (lqpc_n_plus_one) ===")

    # 5.1 AST Call.value AttributeError
    detector = NPlusOneQueryDetector()
    try:
        detector.analyze("for u in users:\n    db.query(u)")
        print("[5.1] AST analyze unexpectedly succeeded")
    except AttributeError as e:
        print(f"[5.1] AST analyze raised AttributeError: {e}")

    # 5.2 ZeroDivisionError in _build_polyhedron
    try:
        detector._build_polyhedron([NPlusOnePattern(model="Order", location=[], estimated_queries=0)])
        print("[5.2] _build_polyhedron unexpectedly succeeded with 0 queries")
    except ZeroDivisionError as e:
        print(f"[5.2] _build_polyhedron raised ZeroDivisionError: {e}")

    # 5.3 False positive N+1 detection on unrelated single queries
    res = detect_n_plus_one([
        "SELECT * FROM users WHERE id = 1",
        "SELECT * FROM orders WHERE id = 100",
    ])
    print(f"[5.3] False positive N+1 patterns: {res['summary']['n_patterns_detected']} detected on 2 unrelated single queries")


if __name__ == "__main__":
    test_domain_1_typing()
    test_domain_2_fullstack()
    test_domain_3_workflow_ptho()
    test_domain_4_workflow_simplex()
    test_domain_5_workflow_lqpc()
    print("\n>>> ALL ADVERSARIAL REPRODUCTIONS EXECUTED SUCCESSFULLY <<<")
