"""Tier 1: 1:1 Mathematical Invariant Proofs & Algorithmic Equivalence Tests.

Verifies bit-exact mathematical properties, error bounds, and zero-drift invariants
for Phase 1 pillars: FK-NUM, FK-SLA, FK-GEO, A-SMW, ACDS, and AEC-VS.
"""

import ast
import math
import sys
sys.path.insert(0, "src")

import pytest
from fault_keeper.num import DualNumber, Fixed128, WelfordAccumulator, SpringDynamicsSolver
from fault_keeper.sla import CSRMatrix, spmv, randomized_svd
from fault_keeper.geo import ShewchukPredicates, MortonBVH, convex_hull_monotone_chain
from fault_keeper.audit import ast_merge, detect_copy_paste_drift, validate_env_contract


class TestTier1FKNumInvariants:
    """1:1 Invariant Tests for FK-NUM."""

    def test_dual_number_autodiff_analytical(self):
        """Test 1.1.1: Dual Number Autodiff vs Analytical Derivative."""
        # f(x) = 3x^3 - 2x^2 + sin(x) * exp(x)
        # f'(x) = 9x^2 - 4x + cos(x)*exp(x) + sin(x)*exp(x)
        x_val = 2.5
        dn = DualNumber(x_val, 1.0)

        # Dual number evaluation using member methods
        term1 = DualNumber(3.0) * dn.pow(3)
        term2 = DualNumber(2.0) * dn.pow(2)
        term3 = dn.sin() * dn.exp()
        f_dual = term1 - term2 + term3

        # Analytical derivative
        f_prime_analytical = 9.0 * (x_val ** 2) - 4.0 * x_val + math.cos(x_val) * math.exp(x_val) + math.sin(x_val) * math.exp(x_val)

        delta = abs(f_dual.dual - f_prime_analytical)
        assert delta < 1e-12, f"Dual autodiff drift exceeds tolerance: {delta}"

    def test_fixed128_financial_exactness(self):
        """Test 1.1.2: Fixed128 Financial Invariant (Zero IEEE-754 epsilon drift)."""
        # 0.1 + 0.2 must equal 0.3 without 0.30000000000000004 artifact
        a = Fixed128.from_float(0.1)
        b = Fixed128.from_float(0.2)
        c = a + b
        expected = Fixed128.from_float(0.3)
        assert c == expected
        assert c.to_float() == pytest.approx(0.3, abs=1e-9)

        # Accumulate 10,000 cents: 10,000 * 0.01 = 100.00
        cent = Fixed128.from_float(0.01)
        total = Fixed128.from_int(0)
        for _ in range(10000):
            total = total + cent
        assert total.to_float() == pytest.approx(100.0, abs=1e-9)

    def test_welford_numerical_stability(self):
        """Test 1.1.3: Welford O(1) Numerical Stability vs High Mean Offset."""
        # High offset data: 10^9 + [1, 2, 3, 4, 5]
        # Textbook naive variance algorithm suffers severe cancellation
        offset = 1_000_000_000.0
        samples = [1.0, 2.0, 3.0, 4.0, 5.0]
        acc = WelfordAccumulator()
        for s in samples:
            acc.update(offset + s)

        # Expected sample variance of [1, 2, 3, 4, 5] is 2.5
        assert abs(acc.mean - (offset + 3.0)) < 1e-12
        assert abs(acc.variance() - 2.5) < 1e-12

    def test_spring_dynamics_energy_conservation(self):
        """Test 1.1.4: Undamped harmonic oscillator energy conservation."""
        # m = 1.0, k = 1.0
        # Total Mechanical Energy E = 0.5 * k * x^2 + 0.5 * m * v^2 is invariant
        solver = SpringDynamicsSolver(k=1.0, m=1.0)
        solver.set_initial_conditions(x0=2.0, v0=0.0)
        initial_energy = 0.5 * solver.k * (solver.x ** 2) + 0.5 * solver.m * (solver.v ** 2)

        dt = 0.01
        for _ in range(1000):
            solver.step(dt=dt)

        final_energy = 0.5 * solver.k * (solver.x ** 2) + 0.5 * solver.m * (solver.v ** 2)
        energy_drift = abs(final_energy - initial_energy)
        # Euler-Cromer preserves energy envelope within bounded tolerance
        assert energy_drift < 0.05, f"Energy conservation drift too high: {energy_drift}"


class TestTier1FKSLAInvariants:
    """1:1 Invariant Tests for FK-SLA."""

    def test_spmv_cache_line_equivalence(self):
        """Test 1.2.1: SpMV mathematical equivalence: y = A * x."""
        row_ind = [0, 0, 1, 2]
        col_ind = [0, 2, 1, 0]
        data = [2.0, 3.0, 4.0, 5.0]
        shape = (3, 3)
        A = CSRMatrix.from_coo(row_ind, col_ind, data, shape)
        x = [1.0, 2.0, 3.0]

        # Row 0: 2.0*1 + 3.0*3 = 11.0
        # Row 1: 4.0*2 = 8.0
        # Row 2: 5.0*1 = 5.0
        y = spmv(A, x)
        assert y == [11.0, 8.0, 5.0]

    def test_randomized_svd_reconstruction_bound(self):
        """Test 1.2.2: SVD Reconstruction Frobenius Error Bound."""
        row_ind = [0, 1, 2, 3]
        col_ind = [0, 1, 2, 3]
        data = [10.0, 8.0, 1.0, 0.5]
        A = CSRMatrix.from_coo(row_ind, col_ind, data, (4, 4))

        U, sigma, Vt = randomized_svd(A, k=2, n_iter=3, random_seed=42)

        # Reconstruct top-2 approximation: A_recon = U * diag(sigma) * Vt
        m, n = 4, 4
        A_recon = [[0.0] * n for _ in range(m)]
        for r in range(m):
            for c in range(n):
                A_recon[r][c] = sum(U[r][k] * sigma[k] * Vt[k][c] for k in range(len(sigma)))

        orig_norm = math.sqrt(10.0**2 + 8.0**2 + 1.0**2 + 0.5**2)
        err_sq = 0.0
        for r in range(m):
            for c in range(n):
                expected = data[r] if r == c else 0.0
                err_sq += (A_recon[r][c] - expected) ** 2
        frob_rel_error = math.sqrt(err_sq) / orig_norm
        assert frob_rel_error < 0.2


class TestTier1FKGeoInvariants:
    """1:1 Invariant Tests for FK-GEO."""

    def test_shewchuk_exact_orient2d_degenerate(self):
        """Test 1.3.1: Shewchuk Exact Orient2D on near-collinear degenerate points."""
        p = (0.0, 0.0)
        q = (1.0, 1.0)
        # Exactly collinear
        r_exact = (2.0, 2.0)
        assert ShewchukPredicates.orient2d(p, q, r_exact) == 0.0
        assert ShewchukPredicates.orient2d_sign(p[0], p[1], q[0], q[1], r_exact[0], r_exact[1]) == 0

        # Perturbed by 1e-15 (left turn / CCW)
        r_ccw = (2.0, 2.0 + 1e-15)
        sign_ccw = ShewchukPredicates.orient2d_sign(p[0], p[1], q[0], q[1], r_ccw[0], r_ccw[1])
        assert sign_ccw == 1

        # Perturbed by 1e-15 (right turn / CW)
        r_cw = (2.0, 2.0 - 1e-15)
        sign_cw = ShewchukPredicates.orient2d_sign(p[0], p[1], q[0], q[1], r_cw[0], r_cw[1])
        assert sign_cw == -1

    def test_convex_hull_monotone_chain(self):
        """Test 1.3.2: Monotone Chain Convex Hull invariant."""
        points = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0), (1.0, 1.0)]
        hull = convex_hull_monotone_chain(points)
        assert len(hull) == 4
        assert (1.0, 1.0) not in hull


class TestTier1KillerTrioInvariants:
    """1:1 Invariant Tests for A-SMW, ACDS, and AEC-VS."""

    def test_ast_merge_commutativity(self):
        """Test 1.4.1: A-SMW Commutativity Merge(Base, A, B) == Merge(Base, B, A)."""
        base = ast.parse("x = 1\ny = 2\nz = 3")
        our_change = {"1": ast.parse("x = 100").body[0]}
        their_change = {"3": ast.parse("z = 300").body[0]}

        merged_ab, conflicts_ab = ast_merge(base, our_change, their_change)
        merged_ba, conflicts_ba = ast_merge(base, their_change, our_change)

        assert len(conflicts_ab) == 0
        assert len(conflicts_ba) == 0
        assert ast.dump(merged_ab) == ast.dump(merged_ba)

    def test_acds_copy_paste_drift_detection(self):
        """Test 1.4.2: ACDS Variable Drift Bound."""
        code_with_drift = """
def calc_rect_a(width, height):
    area = width * height
    return area

def calc_rect_b(length, breadth):
    area = width * breadth
    return area
"""
        drifts = detect_copy_paste_drift(code_with_drift)
        assert len(drifts) >= 1
        assert any(d.get("drifted_var") == "width" or "calc_rect" in str(d) for d in drifts)

    def test_aec_vs_env_contract_validation(self):
        """Test 1.4.3: AEC-VS Strict Schema Validation."""
        contract_spec = """
DATABASE_URL:
  required: true
  pattern: "^postgres://.*$"

SECRET_KEY:
  required: true
  pattern: "^[a-f0-9]{32}$"
"""
        valid_env = {
            "DATABASE_URL": "postgres://user:pass@localhost:5432/db",
            "SECRET_KEY": "a" * 32
        }
        res_valid = validate_env_contract(contract_spec, valid_env)
        assert res_valid["valid"] is True
        assert len(res_valid["missing_keys"]) == 0

        invalid_env = {
            "DATABASE_URL": "mysql://localhost/db"
        }
        res_invalid = validate_env_contract(contract_spec, invalid_env)
        assert res_invalid["valid"] is False
        assert len(res_invalid["missing_keys"]) >= 1
