"""CDC-ABS: Cross-Boundary Contract & API Breaking-Change Sentry — 1:1 Invariant Tests.

Verifies:
- Test 2.5.1: Response Subtyping Covariance Invariant (S_new <=_sub S_client => Phi_break == False)
- Test 2.5.2: Nullability Drift & Field Removal Breaking Trigger (Phi_break == True + exact line numbers)
- Test 2.5.3: Safe Dead-Field Deletion Suppression (Q_inhabit == 0 => Suppression Ratio == 1.0)
- Monorepo Pre-Commit Gate Benchmark (<= 250ms across 25 cross-boundary endpoints).
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from fault_keeper.daily.cdcabs import (
    CrossBoundaryContractSentry,
    analyse_cross_boundary,
    compute_inhabitation_quotient,
    harvest_backend_contracts,
    harvest_client_callsites,
    is_structural_subtype,
    normalize_route_path,
)


# ---------------------------------------------------------------------------
# Test 2.5.1 — Response Subtyping Covariance Invariant (S_new <=_sub S_client)
# ---------------------------------------------------------------------------

def test_2_5_1_response_subtyping_covariance_allows_field_widening() -> None:
    """Backend adding new fields or returning int for float satisfies S_new <=_sub S_client (Phi_break is False)."""
    old_backend_src = '''
class UserProfileDTO:
    id: int
    email: str
    score: float

@app.get("/api/users/{user_id}", response_model=UserProfileDTO)
def get_user(user_id: int) -> UserProfileDTO:
    return UserProfileDTO()
'''
    # S_new widens the response with `tier` and `created_at`, and narrows `score` to `int` (int <=_sub float)
    new_backend_src = '''
class UserProfileDTO:
    id: int
    email: str
    score: int
    tier: str
    created_at: int

@app.get("/api/users/{user_id}", response_model=UserProfileDTO)
def get_user(user_id: int) -> UserProfileDTO:
    return UserProfileDTO()
'''
    client_src = '''
interface UserProfile {
    id: number;
    email: string;
    score: number;
}
async function loadProfile(userId: string) {
    const res = await axios.get<UserProfile>(`/api/users/${userId}`);
    const mail = res.email.toLowerCase();
    return mail;
}
'''
    report = analyse_cross_boundary(
        backend_source=new_backend_src,
        client_source=client_src,
        old_backend_source=old_backend_src,
        backend_file="backend/users.py",
        client_file="frontend/profile.ts",
    )

    assert report.phi_break is False
    assert report.violations == []
    assert "GET /api/users/{param}" in report.matched_endpoints
    assert is_structural_subtype("int", "float") is True
    assert is_structural_subtype("str", "string") is True


# ---------------------------------------------------------------------------
# Test 2.5.2 — Nullability Drift & Field Removal Breaking Trigger (Phi_break)
# ---------------------------------------------------------------------------

def test_2_5_2_nullability_drift_and_field_removal_trigger_phi_break() -> None:
    """Backend making `email` nullable while client dereferences it directly triggers Phi_break == True with line coordinates."""
    old_backend_src = '''
class AccountDTO:
    id: int
    email: str
    username: str

@app.get("/api/accounts/{account_id}", response_model=AccountDTO)
def get_account(account_id: int) -> AccountDTO:
    return AccountDTO()
'''
    # `email` drifts from `str` to `Optional[str]` on line 4, and `username` is removed!
    new_backend_src = '''
class AccountDTO:
    id: int
    email: Optional[str]

@app.get("/api/accounts/{account_id}", response_model=AccountDTO)
def get_account(account_id: int) -> AccountDTO:
    return AccountDTO()
'''
    client_src = '''
async function fetchAccount(id: number) {
    const data = await fetch(`/api/accounts/${id}`);
    const normalizedEmail = data.email.trim();
    const handle = data.username.toUpperCase();
    return { normalizedEmail, handle };
}
'''
    report = analyse_cross_boundary(
        backend_source=new_backend_src,
        client_source=client_src,
        old_backend_source=old_backend_src,
        backend_file="backend/accounts.py",
        client_file="frontend/account_view.ts",
    )

    assert report.phi_break is True
    assert len(report.violations) == 2

    by_field = {v.field_name: v for v in report.violations}
    assert "email" in by_field
    email_v = by_field["email"]
    assert email_v.violation_kind == "NULLABILITY_DRIFT"
    assert email_v.backend_file == "backend/accounts.py"
    assert email_v.backend_lineno == 4
    assert email_v.client_file == "frontend/account_view.ts"
    assert email_v.client_lineno == 4

    assert "username" in by_field
    user_v = by_field["username"]
    assert user_v.violation_kind == "FIELD_REMOVED"
    assert user_v.client_lineno == 5


# ---------------------------------------------------------------------------
# Test 2.5.3 — Safe Dead-Field Deletion Suppression (Q_inhabit == 0)
# ---------------------------------------------------------------------------

def test_2_5_3_safe_dead_field_deletion_suppression_ratio_is_one() -> None:
    """Deleting backend fields never referenced in client AST yields Q_inhabit == 0.0 and Suppression Ratio == 1.0."""
    old_backend_src = '''
class OrderResponse:
    order_id: int
    total_cents: int
    internal_debug_trace: str
    legacy_audit_hash: str

@app.get("/api/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int) -> OrderResponse:
    return OrderResponse()
'''
    # Backend prunes both dead fields `internal_debug_trace` and `legacy_audit_hash`
    new_backend_src = '''
class OrderResponse:
    order_id: int
    total_cents: int

@app.get("/api/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int) -> OrderResponse:
    return OrderResponse()
'''
    # Client only accesses `order_id` and `total_cents`
    client_src = '''
async function renderOrder(orderId: number) {
    const data = await fetch(`/api/orders/${orderId}`);
    const id = data.order_id;
    const total = data.total_cents.toFixed(2);
    return { id, total };
}
'''
    report = analyse_cross_boundary(
        backend_source=new_backend_src,
        client_source=client_src,
        old_backend_source=old_backend_src,
    )

    assert report.phi_break is False
    assert report.violations == []
    assert report.inhabitation_quotient == pytest.approx(0.0, abs=1e-9)
    assert report.suppression_ratio == pytest.approx(1.0, abs=1e-9)
    assert set(report.suppressed_dead_fields) == {
        "internal_debug_trace",
        "legacy_audit_hash",
    }


# ---------------------------------------------------------------------------
# Monorepo Pre-Commit Gate Benchmark (<= 250ms)
# ---------------------------------------------------------------------------

def test_monorepo_pre_commit_cross_boundary_gate_benchmark_under_250ms() -> None:
    """Static cross-boundary verification of 25 endpoints and client callsites completes in <= 250ms."""
    backend_blocks = []
    client_blocks = []
    for idx in range(25):
        backend_blocks.append(
            f"class ItemDTO_{idx}:\n"
            f"    id: int\n"
            f"    title_{idx}: str\n"
            f"    unused_meta_{idx}: str\n\n"
            f"@app.get('/api/v1/items_{idx}/{{item_id}}', response_model=ItemDTO_{idx})\n"
            f"def get_item_{idx}(item_id: int) -> ItemDTO_{idx}:\n"
            f"    return ItemDTO_{idx}()\n"
        )
        client_blocks.append(
            f"async function loadItem_{idx}(id: string) {{\n"
            f"    const data = await fetch(`/api/v1/items_{idx}/${{id}}`);\n"
            f"    return data.title_{idx}.trim();\n"
            f"}}\n"
        )

    sentry = CrossBoundaryContractSentry()
    report = sentry.verify_sources(
        backend_source="\n".join(backend_blocks),
        client_source="\n".join(client_blocks),
    )

    assert report.phi_break is False
    assert len(report.matched_endpoints) == 25
    assert report.elapsed_ms <= 250.0
    assert (
        normalize_route_path("https://api.faultkeeper.dev/v1/users/${userId}?active=1")
        == "/v1/users/{param}"
    )
    q_in, sup = compute_inhabitation_quotient({"a", "b"}, {"b", "c"})
    assert q_in == pytest.approx(0.5)
    assert sup == pytest.approx(0.5)
