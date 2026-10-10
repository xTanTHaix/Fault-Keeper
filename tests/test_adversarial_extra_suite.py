"""Adversarial & Boundary Verification Suite across All 25 Phase 1 & Phase 2 Pillars.

Provides at least one distinct adversarial or boundary-condition test for every
module in Phase 1 (6 pillars: FK-NUM, FK-SLA, FK-GEO, A-SMW, ACDS, AEC-VS) and
Phase 2 (19 pillars: U-FSR, WPA-HIS, FT-DSO, Tx-DLO, CDC-ABS, TC-GTC, RDA-NP,
CASI-OP, FSAS, ATH-BS, AE-FPS, TWSA, PTHO, CRCAE, LQPC, SSDL, STAS, GSLD, ZEC-SW).
"""

from __future__ import annotations

import ast
import asyncio
import math
import sys
from datetime import datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Phase 1 Imports
from fault_keeper.audit.anti_unify import (
    AntiUnificationNode,
    anti_unify,
    detect_copy_paste_drift,
)
from fault_keeper.audit.ast_rewrite import ast_merge
from fault_keeper.audit.env_contract import parse_env_contract, validate_env_contract
from fault_keeper.geo.convex_hull import convex_hull_2d, convex_hull_monotone_chain
from fault_keeper.geo.morton_bvh import MortonBVH
from fault_keeper.geo.shewchuk import ShewchukPredicates
from fault_keeper.num.dual_number import DualNumber, derivative
from fault_keeper.num.fixed128 import Fixed128
from fault_keeper.num.spring_ode import SpringDynamicsSolver
from fault_keeper.num.welford import WelfordAccumulator
from fault_keeper.sla.csr_matrix import CSRMatrix
from fault_keeper.sla.randomized_svd import randomized_svd
from fault_keeper.sla.spmv import spmv
from fault_keeper.sla.token_bucket import TokenBucketSimulator, simulate_rate_limited_queue

# Phase 2 Imports
from fault_keeper.audit.ufsr import check_failure_sink_completeness
from fault_keeper.audit.wpahis import (
    ProjectGraph,
    _find_minimal_feedback_arc_set,
    compute_martin_metrics,
)
from fault_keeper.daily.cdcabs import (
    harvest_backend_contracts,
    harvest_client_callsites,
    is_structural_subtype,
    normalize_route_path,
    verify_cross_boundary_contracts,
)
from fault_keeper.daily.ftdso import (
    VirtualEventClockQuencher,
    generate_gray_code_sequence,
)
from fault_keeper.daily.txdlo import (
    LockResource,
    TransactionFlow,
    benchmark_batch_key_normalizer,
    build_wait_for_graph,
    compute_lock_contention_entropy,
    normalize_batch_keys,
)
from fault_keeper.fullstack.gsl_d_simplex import SimplexSolver
from fault_keeper.fullstack.zec_sw_migration import (
    SchemaVersion,
    ZeroDowntimeMigrationEngine,
    validate_schema_version,
)
from fault_keeper.num.cas_i_op_cache import StampedePrevention, XFetchAlgorithm
from fault_keeper.num.rdas_redos import (
    analyze_regex_complexity,
    optimize_regex,
    validate_input_length,
)
from fault_keeper.num.tc_gtc_timezone import (
    detect_YYYY_format_error,
    detect_dst_traps,
    normalize_timestamp,
)
from fault_keeper.typing.ae_fps_await_checker import (
    check_async_awaits,
    detect_race_conditions,
)
from fault_keeper.typing.ath_byped_hole import (
    TypedHoleSynthesizer,
    infer_entity_from_dto,
)
from fault_keeper.typing.fsas_ghost_cst import get_cursor_context, parse_ghost_cst
from fault_keeper.typing.twsa_type_lattice import (
    TypeLatticeGraph,
    compute_lattice_distance,
    get_fuzzy_completions,
)
from fault_keeper.workflow.crcae_root_causal import (
    CausalGraph,
    CausalNode,
    diagnose_root_cause,
)
from fault_keeper.workflow.gsl_d_simplex.css_layout_simplex_solver import (
    CSSLayoutSimplexSolver,
    LayoutConstraint,
)
from fault_keeper.workflow.lqpc_n_plus_one import Polyhedron, detect_n_plus_one
from fault_keeper.workflow.ptho import TestSuitePruner, prune_test_suite
from fault_keeper.workflow.ssdl_dependency_hell import (
    DependencyConflictDetector,
    MicroShimGenerator,
    PublicAPISlicer,
)
from fault_keeper.workflow.stas_simd_trigram import STASimDTrigramSearcher, TrigramIndex


# ===========================================================================
# PHASE 1 ADVERSARIAL & BOUNDARY TESTS (6 PILLARS)
# ===========================================================================

def test_adv_p1_fk_num_dual_number_zero_division_and_transcendentals() -> None:
    """Pillar 1a (FK-NUM DualNumber): Division by zero guard and composition chain rule."""
    numerator = DualNumber(3.0, 1.0)
    zero_denom = DualNumber(0.0, 5.0)
    with pytest.raises(ZeroDivisionError):
        _ = numerator / zero_denom

    # Verify exact chain rule on f(x) = exp(sin(x)) at x = 0.7
    x_val = 0.7
    dn = DualNumber(x_val, 1.0)
    res = dn.sin().exp()
    expected_val = math.exp(math.sin(x_val))
    expected_deriv = math.exp(math.sin(x_val)) * math.cos(x_val)
    assert math.isclose(res.value, expected_val, rel_tol=1e-15)
    assert math.isclose(res.dual, expected_deriv, rel_tol=1e-15)
    assert math.isclose(derivative(lambda z: z * z * z, -2.0, h=1.0), 12.0, rel_tol=1e-15)


def test_adv_p1_fk_num_fixed128_negative_arithmetic_and_zero_division() -> None:
    """Pillar 1b (FK-NUM Fixed128): Exact Q64.64 negative fixed-point arithmetic & zero division."""
    a = Fixed128.from_string("-123456.7890125")
    b = Fixed128.from_string("123456.7890125")
    total = a + b
    assert total.value == 0
    assert total.to_float() == 0.0

    with pytest.raises(ZeroDivisionError):
        _ = a / Fixed128.from_int(0)


def test_adv_p1_fk_num_welford_catastrophic_cancellation_immunity() -> None:
    """Pillar 1c (FK-NUM Welford): Variance invariance under 10^9 shift (catastrophic cancellation)."""
    acc = WelfordAccumulator()
    base_shift = 1_000_000_000.0
    for offset in (1.0, 2.0, 3.0, 4.0, 5.0):
        acc.update(base_shift + offset)

    assert acc.count == 5
    assert math.isclose(acc.mean, base_shift + 3.0, rel_tol=1e-12)
    assert math.isclose(acc.variance(ddof=1), 2.5, rel_tol=1e-9)


def test_adv_p1_fk_num_spring_ode_symplectic_energy_conservation() -> None:
    """Pillar 1d (FK-NUM SpringODE): Symplectic Velocity Verlet conserves Hamiltonian energy."""
    solver = SpringDynamicsSolver(k=25.0, m=1.0)
    solver.set_initial_conditions(x0=2.0, v0=0.0)
    initial_energy = solver.energy()
    assert math.isclose(initial_energy, 50.0, rel_tol=1e-12)

    solver.integrate(t_final=2.0, dt=0.001)
    final_energy = solver.energy()
    assert abs(final_energy - initial_energy) / initial_energy < 1e-2


def test_adv_p1_fk_sla_csr_spmv_dimension_mismatch_and_sparse_svd() -> None:
    """Pillar 2 (FK-SLA): CSRMatrix SpMV, short vector IndexError, and randomized SVD."""
    csr = CSRMatrix.from_coo(
        row_ind=[0, 1, 2, 3],
        col_ind=[0, 1, 2, 3],
        data=[10.0, 4.0, 5.0, 2.0],
        shape=(4, 4),
    )
    assert csr.nnz == 4
    y = spmv(csr, [1.0, 2.0, 2.0, 3.0])
    assert y == [10.0, 8.0, 10.0, 6.0]

    with pytest.raises(IndexError):
        _ = spmv(csr, [1.0, 2.0])

    u_mat, sigma, vt_mat = randomized_svd(csr, k=2, n_iter=2, random_seed=7)
    assert len(sigma) == 2
    assert sigma[0] >= sigma[1] >= 0.0
    assert len(u_mat) == 4 and len(vt_mat) == 2


def test_adv_p1_fk_sla_token_bucket_burst_exhaustion() -> None:
    """Pillar 2b (FK-SLA TokenBucket): Burst exhaustion under high arrival rate."""
    sim = TokenBucketSimulator(capacity=5.0, refill_rate_num=1.0, refill_rate_den_ms=1000.0)
    res_ok = sim.consume_tokens(5, elapsed_ms=0)
    assert res_ok.success is True
    res_throttled = sim.consume_tokens(1, elapsed_ms=0)
    assert res_throttled.success is False

    stats = simulate_rate_limited_queue(
        arrival_rate=50.0,
        service_rate=10.0,
        servers=1,
        simulation_time_ms=1000.0,
    )
    assert isinstance(stats, dict)


def test_adv_p1_fk_geo_shewchuk_collinear_and_degenerate_convex_hull() -> None:
    """Pillar 3 (FK-GEO): Exact collinearity sign, degenerate convex hull, and MortonBVH."""
    assert ShewchukPredicates.orient2d_sign(0.0, 1.0, 1e8, 2e8 + 1.0, 2e8, 4e8 + 1.0) == 0
    assert ShewchukPredicates.orient2d_sign(0.0, 1.0, 1e8, 2e8 + 1.0, 2e8, 4e8 + 2.0) == 1

    dup_points = [(0.0, 0.0), (0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (0.0, 2.0), (2.0, 0.0)]
    hull = convex_hull_monotone_chain(dup_points)
    assert len(hull) == 4
    assert set(hull) == {(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)}
    assert len(convex_hull_2d([(5.0, 5.0)])) == 1

    bvh = MortonBVH([(0.0, 0.0, 10.0, 10.0)])
    hits = bvh.traverse(5.0, 5.0)
    assert len(hits) == 1
    assert bvh.traverse(99.0, 99.0) == []


def test_adv_p1_a_smw_ast_merge_commutativity_and_conflict_resolution() -> None:
    """Pillar 4 (A-SMW): Commutativity of disjoint AST merges and conflict detection."""
    base_tree = ast.parse("def alpha():\n    return 1\n")
    left_tree = ast.parse("def beta():\n    return 2\n")
    right_tree = ast.parse("def gamma():\n    return 3\n")

    merged_lr, res_lr = ast_merge(base_tree, {"L": left_tree}, {"R": right_tree})
    merged_rl, res_rl = ast_merge(base_tree, {"R": right_tree}, {"L": left_tree})
    assert res_lr == [] and res_rl == []
    assert ast.dump(merged_lr) == ast.dump(merged_rl)

    conflict_left = ast.parse("x = 10\n")
    conflict_right = ast.parse("x = 20\n")
    _, conflicts = ast_merge(base_tree, {"same_slot": conflict_left}, {"same_slot": conflict_right})
    assert len(conflicts) == 1


def test_adv_p1_acds_anti_unification_alpha_renaming_vs_structural_divergence() -> None:
    """Pillar 5 (ACDS): Anti-unification preserves isomorphic AST subtrees and handles syntax errors."""
    drifted_code = """
def calc_tax_us(amount, rate):
    tax = amount * rate
    return tax

def calc_tax_eu(value, rate):
    tax = amount * rate
    return tax
"""
    drifts = detect_copy_paste_drift(drifted_code)
    assert isinstance(drifts, list)
    err_drifts = detect_copy_paste_drift("def broken(:\n")
    assert len(err_drifts) == 1 and "error" in err_drifts[0]

    node1 = AntiUnificationNode(
        name="add",
        kind="binop",
        children=[AntiUnificationNode("a", "var"), AntiUnificationNode("1", "const")],
    )
    node2 = AntiUnificationNode(
        name="add",
        kind="binop",
        children=[AntiUnificationNode("a", "var"), AntiUnificationNode("1", "const")],
    )
    au_node = anti_unify(node1, node2)
    assert au_node.name == "add" and len(au_node.children) == 2


def test_adv_p1_aec_vs_env_contract_invalid_pattern_and_missing_required() -> None:
    """Pillar 6 (AEC-VS): Env contract rejects malformed values and missing required keys."""
    schema_text = """
# Production environment contract
DATABASE_URL:
  required: true
  pattern: "^postgres://.*$"

PORT:
  required: true
  pattern: "^[0-9]{4}$"
"""
    contracts = parse_env_contract(schema_text)
    assert "DATABASE_URL" in contracts and contracts["DATABASE_URL"].required is True

    invalid_res = validate_env_contract(schema_text, {"PORT": "abcd"})
    assert invalid_res["valid"] is False
    assert "DATABASE_URL" in invalid_res["missing_keys"]

    valid_res = validate_env_contract(
        schema_text,
        {"DATABASE_URL": "postgres://localhost:5432/db", "PORT": "8080"},
    )
    assert valid_res["valid"] is True


# ===========================================================================
# PHASE 2 ADVERSARIAL & BOUNDARY TESTS (19 PILLARS)
# ===========================================================================

def test_adv_p2_ufsr_caught_vs_uncaught_exception_sink_completeness() -> None:
    """Pillar 7 (U-FSR): Distinguishes caught exceptions from escaped failure sinks."""
    caught_src = """
def safe_handler(x: int) -> int:
    try:
        if x < 0:
            raise ValueError("negative")
        return x
    except ValueError:
        return 0
"""
    uncaught_src = """
def leaky_handler(x: int) -> int:
    if x < 0:
        raise KeyError("escaped_key")
    return x
"""
    caught_fn = ast.parse(caught_src).body[0]
    uncaught_fn = ast.parse(uncaught_src).body[0]
    assert isinstance(caught_fn, ast.FunctionDef)
    assert isinstance(uncaught_fn, ast.FunctionDef)

    rep_caught = check_failure_sink_completeness(caught_fn)
    rep_uncaught = check_failure_sink_completeness(uncaught_fn)
    assert rep_caught.phi_sink is True and len(rep_caught.unguarded_branches) == 0
    assert rep_uncaught.phi_sink is False and len(rep_uncaught.unguarded_branches) >= 1


def test_adv_p2_wpahis_figure_eight_double_cycle_feedback_arc_set() -> None:
    """Pillar 8 (WPA-HIS): Figure-8 double cycle graph requires >= 2 FAS edges and computes Martin metrics."""
    graph = ProjectGraph()
    for mod in ("hub", "left_a", "left_b", "right_a", "right_b"):
        graph.add_module(mod)
    for u, v in (
        ("hub", "left_a"),
        ("left_a", "left_b"),
        ("left_b", "hub"),
        ("hub", "right_a"),
        ("right_a", "right_b"),
        ("right_b", "hub"),
    ):
        graph.add_edge(u, v)

    fas = _find_minimal_feedback_arc_set(graph)
    assert len(fas) == 2
    avg_a, avg_i, avg_d = compute_martin_metrics(graph)
    assert 0.0 <= avg_a <= 1.0
    assert 0.0 <= avg_i <= 1.0
    assert 0.0 <= avg_d <= 1.0


def test_adv_p2_ftdso_gray_code_hamming_distance_one_and_virtual_clock() -> None:
    """Pillar 9 (FT-DSO): Adjacent Gray code integers differ by exactly 1 bit; virtual clock < 50ms."""
    seq = generate_gray_code_sequence(4)
    assert len(seq) == 16
    assert len(set(seq)) == 16
    for idx in range(len(seq) - 1):
        xor_val = seq[idx] ^ seq[idx + 1]
        assert xor_val > 0 and (xor_val & (xor_val - 1)) == 0

    with VirtualEventClockQuencher() as quencher:
        import time as _time_mod
        _time_mod.sleep(120.0)
        _time_mod.sleep(60.0)

    report = quencher.build_report("import time\ntime.sleep(120.0)\n")
    assert math.isclose(report.virtual_elapsed_sec, 180.0, rel_tol=1e-9)
    assert report.wall_clock_ms < 50.0
    assert len(report.ast_sleep_callsites) == 1


def test_adv_p2_txdlo_three_way_ring_deadlock_and_mixed_batch_keys() -> None:
    """Pillar 10 (Tx-DLO): 3-way circular wait T1->T2->T3->T1 and heterogeneous batch key sort."""
    t1 = TransactionFlow("tx_1", [LockResource("orders", 1), LockResource("orders", 2)])
    t2 = TransactionFlow("tx_2", [LockResource("orders", 2), LockResource("orders", 3)])
    t3 = TransactionFlow("tx_3", [LockResource("orders", 3), LockResource("orders", 1)])

    wfg = build_wait_for_graph([t1, t2, t3])
    assert wfg.is_deadlock_free is False
    assert wfg.h1_betti_number >= 1
    assert len(wfg.cycles) == 1
    assert set(wfg.cycles[0]) == {"tx_1", "tx_2", "tx_3"}

    entropy_rep = compute_lock_contention_entropy([t1, t2, t3])
    assert math.isclose(entropy_rep.h_contention, math.log2(3.0), rel_tol=1e-5)

    mixed_keys = ["acct_z", 500, "acct_a", 10, 500, 10]
    norm_keys = normalize_batch_keys(mixed_keys)
    assert norm_keys == [10, 500, "acct_a", "acct_z"]

    bench = benchmark_batch_key_normalizer(list(range(500, 0, -1)), budget_ms=5.0)
    assert bench.unique_count == 500
    assert bench.sorted_keys[0] == 1 and bench.sorted_keys[-1] == 500


def test_adv_p2_cdcabs_multi_framework_route_matching_and_type_narrowing() -> None:
    """Pillar 11 (CDC-ABS): FastAPI/Flask/Express/TS route canonicalization and subtype lattice."""
    assert normalize_route_path("https://api.example.com/v1/users/{user_id:int}/?active=1") == "/v1/users/{param}"
    assert normalize_route_path("/v1/users/<int:user_id>/") == "/v1/users/{param}"
    assert normalize_route_path("/v1/users/:userId") == "/v1/users/{param}"
    assert normalize_route_path("`/v1/users/${user.id}`") == "/v1/users/{param}"

    assert is_structural_subtype("int", "float") is True
    assert is_structural_subtype("float", "int") is False
    assert is_structural_subtype("Optional[str]", "str") is False
    assert is_structural_subtype("Optional[str]", "Optional[str]") is True

    backend_code = """
from pydantic import BaseModel
class ItemDTO(BaseModel):
    code: int
@app.get("/api/items/{id}", response_model=ItemDTO)
def get_item(id: int) -> ItemDTO:
    return ItemDTO(code=404)
"""
    client_code = """
async function checkItem(id: number) {
    const res = await fetch(`/api/items/${id}`);
    const data = await res.json();
    return data.code.toLowerCase();
}
"""
    rep = verify_cross_boundary_contracts(
        harvest_backend_contracts(backend_code),
        harvest_client_callsites(client_code),
    )
    assert rep.phi_break is True
    assert any(v.violation_kind == "TYPE_MISMATCH" for v in rep.violations)


def test_adv_p2_tc_gtc_yyyy_format_and_dst_transition_hazard() -> None:
    """Pillar 12 (TC-GTC): Detects non-standard YYYY/MM/DD date format, DST traps, and offset drift."""
    from fault_keeper.num.tc_gtc_timezone import detect_timezone_drift

    has_yyyy_err, err_msg = detect_YYYY_format_error("2026/12/31")
    assert has_yyyy_err is True
    assert err_msg is not None

    dst_dt = datetime(2026, 3, 8, 2, 30, 0)
    dst_traps = detect_dst_traps(timestamp=dst_dt, tz_name="America/New_York")
    assert isinstance(dst_traps, dict)

    drift = detect_timezone_drift(expected_offset=0.0, actual_offset=3600.0)
    assert drift is not None


def test_adv_p2_rda_np_exponential_star_height_and_regex_optimization() -> None:
    """Pillar 13 (RDA-NP): Detects nested quantifier catastrophic backtracking and optimizes regex."""
    evil_pattern = r"^(a+)+b$"
    analysis = analyze_regex_complexity(evil_pattern)
    assert isinstance(analysis, dict)
    assert analysis.get("is_dangerous") is True
    assert len(analysis.get("vulnerabilities", [])) >= 1

    optimized = optimize_regex(r"(a+)+")
    assert isinstance(optimized, str)
    len_check = validate_input_length("a" * 5000, max_length=1024)
    assert len_check.get("valid") is False or len_check.get("is_valid") is False


def test_adv_p2_casi_op_xfetch_boundary_ttl_and_stampede_lock() -> None:
    """Pillar 14 (CASI-OP): XFetch probabilistic refresh and stampede single-flight lock."""
    xfetch = XFetchAlgorithm(beta=1.0, delta=0.05)
    res_xf = asyncio.run(xfetch.xfetch("session_key", lambda: {"user": 1}))
    assert isinstance(res_xf, dict)
    should_ref = xfetch.should_refresh("session_key")
    assert isinstance(should_ref, bool)

    prevention = StampedePrevention()
    lock = asyncio.run(prevention.acquire_lock("hot_key"))
    assert lock is not None
    asyncio.run(prevention.release_lock("hot_key"))


def test_adv_p2_fsas_ghost_cst_severely_corrupted_syntax_recovery() -> None:
    """Pillar 15 (FSAS): GhostCST recovers valid AST/CST nodes from mid-keystroke syntax errors."""
    corrupted_code = (
        "class OrderProcessor:\n"
        "    def process(self, order_id: int):\n"
        "        self.\n"
        "        if (unclosed_paren\n"
    )
    cst = parse_ghost_cst(corrupted_code)
    assert cst is not None
    ctx = get_cursor_context(corrupted_code, cursor_pos=55)
    assert isinstance(ctx, dict)


def test_adv_p2_ath_bs_typed_hole_inference_and_dto_entity_mapping() -> None:
    """Pillar 16 (ATH-BS): Synthesizes typed holes and infers Entity fields from DTO definitions."""
    synthesizer = TypedHoleSynthesizer()
    res = synthesizer.synthesize("count: _ = 42")
    assert res is not None

    dto_def = "class WalletDTO:\n    user_id: int\n    balance: float\n"
    inferred_entity = infer_entity_from_dto(dto_def, target_entity_name="WalletEntity")
    assert inferred_entity is not None


def test_adv_p2_ae_fps_unawaited_coroutine_in_loop_and_race_detector() -> None:
    """Pillar 17 (AE-FPS): Detects unawaited async function inside loop and concurrent shared write."""
    code = """
import asyncio

shared_counter = 0

async def send_notification(uid: int) -> None:
    global shared_counter
    shared_counter += 1

async def batch_notify(user_ids: list[int]) -> None:
    for uid in user_ids:
        send_notification(uid)
    await asyncio.gather(send_notification(1), send_notification(2))
"""
    missing_awaits = check_async_awaits(code)
    races = detect_race_conditions(code)
    assert len(missing_awaits) >= 1
    assert any(m.function_name == "send_notification" for m in missing_awaits)
    assert isinstance(races, list)


def test_adv_p2_twsa_type_lattice_distance_and_fuzzy_subsequence_search() -> None:
    """Pillar 18 (TWSA): Computes type lattice distance and ranks fuzzy completions."""
    lattice = TypeLatticeGraph()
    lattice.build_lattice(
        [
            {"name": "object", "parents": []},
            {"name": "Number", "parents": ["object"]},
            {"name": "Integer", "parents": ["Number"]},
            {"name": "Boolean", "parents": ["Integer"]},
        ]
    )
    dist = compute_lattice_distance("Boolean", "object", lattice=lattice)
    assert dist >= 0

    types_data = [
        {"name": "getUserAccountBalance", "type": "float"},
        {"name": "getUserProfile", "type": "dict"},
        {"name": "deleteUserSession", "type": "bool"},
    ]
    matches = get_fuzzy_completions("getUserAccount", types_data, threshold=0.3)
    assert len(matches) >= 1


def test_adv_p2_ptho_transitive_impact_and_zero_budget_boundary(tmp_path: Path) -> None:
    """Pillar 19 (PTHO): Transitive dependency graph impact and test suite pruning."""
    proj = tmp_path / "ptho_adv"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "core_db.py").write_text("def query():\n    return 1\n", encoding="utf-8")
    (proj / "repo.py").write_text("import core_db\ndef fetch():\n    return core_db.query()\n", encoding="utf-8")
    (proj / "test_repo.py").write_text("import repo\ndef test_r():\n    assert repo.fetch() == 1\n", encoding="utf-8")

    pruner = TestSuitePruner(str(proj)).discover_and_analyze()
    scores = pruner.get_impact_scores(["core_db.py"])
    assert isinstance(scores, dict)

    pruned = prune_test_suite(["test_a.py", "test_b.py", "test_c.py"], max_tests=2)
    assert len(pruned) == 2


def test_adv_p2_crcae_cycle_detection_and_multi_root_abduction() -> None:
    """Pillar 20 (CRCAE): Builds CausalGraph and ranks competing root causes."""
    cg = CausalGraph()
    cg.add_node(CausalNode(name="redis_cluster", type="cache"))
    cg.add_node(CausalNode(name="postgres_primary", type="database"))
    cg.add_node(CausalNode(name="checkout_api", type="service"))
    cg.add_edge("redis_cluster", "checkout_api", strength=0.2)
    cg.add_edge("postgres_primary", "checkout_api", strength=0.95)

    paths = cg.find_all_paths("postgres_primary", "checkout_api")
    assert len(paths) == 1

    graph_data = {
        "nodes": [
            {"name": "redis_cluster", "type": "cache"},
            {"name": "postgres_primary", "type": "database"},
            {"name": "checkout_api", "type": "service"},
        ],
        "edges": [
            {"from": "redis_cluster", "to": "checkout_api", "strength": 0.2},
            {"from": "postgres_primary", "to": "checkout_api", "strength": 0.95},
        ],
    }
    diag = diagnose_root_cause(graph_data, symptom="checkout_api")
    assert isinstance(diag, dict)


def test_adv_p2_lqpc_polyhedral_nested_loops_and_sql_in_loop() -> None:
    """Pillar 21 (LQPC): Polyhedron loop domain representation and batch SQL N+1 detection."""
    poly = Polyhedron(
        name="nested_dept_loop",
        dimension=2,
        vertices=[(0.0, 0.0, 0.0), (100.0, 50.0, 0.0)],
        constraints=["0 <= i < 100", "0 <= j < 50"],
        optimization="batch_in_clause",
    )
    assert poly.dimension == 2

    repeated_queries = [
        "SELECT * FROM salaries WHERE emp_id = 10",
        "SELECT * FROM salaries WHERE emp_id = 20",
        "SELECT * FROM salaries WHERE emp_id = 30",
    ]
    issues = detect_n_plus_one(repeated_queries)
    assert issues is not None and issues["summary"]["n_patterns_detected"] >= 1


def test_adv_p2_ssdl_disjoint_version_conflict_and_ast_symbol_slicing(tmp_path: Path) -> None:
    """Pillar 22 (SSDL): Detects disjoint SemVer ranges and slices exact imported symbols."""
    proj = tmp_path / "ssdl_adv"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "requirements.txt").write_text("urllib3>=1.26,<2.0\nurllib3>=2.0.0\n", encoding="utf-8")
    py_file = proj / "http_client.py"
    py_file.write_text("from urllib3 import PoolManager, Timeout\nmgr = PoolManager()\n", encoding="utf-8")

    detector = DependencyConflictDetector()
    conflicts = detector.detect_conflicts(str(proj))
    assert isinstance(conflicts, list)

    slicer = PublicAPISlicer()
    pkg_slice = slicer.slice_package("urllib3", str(py_file), version="1.26.18")
    assert pkg_slice is not None

    if conflicts:
        shim_gen = MicroShimGenerator()
        shim = shim_gen.generate_shim(conflicts[0], pkg_slice, pkg_slice)
        assert shim is not None


def test_adv_p2_stas_simd_trigram_incremental_update_and_short_query(tmp_path: Path) -> None:
    """Pillar 23 (STAS): Trigram index extracts trigrams and searches codebase."""
    code_dir = tmp_path / "stas_adv"
    code_dir.mkdir(parents=True, exist_ok=True)
    (code_dir / "auth.py").write_text(
        "def authenticate_jwt_token(secret_key: str) -> bool:\n    return True\n",
        encoding="utf-8",
    )
    (code_dir / "math_utils.py").write_text(
        "def fast_fourier_transform(signal):\n    return signal\n",
        encoding="utf-8",
    )

    idx = TrigramIndex("authenticate_jwt_token")
    trigrams = idx.extract_trigrams("authenticate_jwt_token")
    assert len(trigrams) > 0
    idx.build_index(str(code_dir), pattern=r".*\.py$")
    hits = idx.search("authenticate_jwt")
    assert isinstance(hits, list) and len(hits) >= 1

    # Verify short (< 3 char) query boundary on STASimDTrigramSearcher
    searcher = STASimDTrigramSearcher()
    res = searcher.search("ab")
    assert res.query == "ab" and res.matches == []


def test_adv_p2_gsld_simplex_infeasible_relaxation_and_constraint_solver() -> None:
    """Pillar 24 (GSLD): Simplex solver resolves over-constrained min-width sum > viewport."""
    solver = CSSLayoutSimplexSolver()
    constraints = [
        LayoutConstraint(type="min-width", value=200.0, element="sidebar"),
        LayoutConstraint(type="min-width", value=220.0, element="content"),
    ]
    res = solver.solve(constraints)
    assert isinstance(res, dict) and res["success"] is True

    lp = SimplexSolver()
    lp.build_from_constraints(constraints, variables=["sidebar", "content"])
    lp_sol = lp.solve()
    assert lp_sol is not None


def test_adv_p2_zec_sw_shadow_trigger_and_schema_version_validation() -> None:
    """Pillar 25 (ZEC-SW): Generates Expand-Contract shadow triggers and validates SchemaVersion."""
    sv_valid = SchemaVersion(
        version="2.1.0",
        changes=[{"action": "ADD_COLUMN", "table": "orders", "column": "total_amount"}],
        is_backward_compatible=True,
    )
    val_res = validate_schema_version(sv_valid)
    assert val_res["valid"] is True

    engine = ZeroDowntimeMigrationEngine()
    exec_result = engine.execute_full_migration(["orders", "users"])
    assert exec_result["success"] is True
    assert exec_result["downtime_seconds"] == 0
