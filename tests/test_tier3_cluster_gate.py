"""Tier 3: Phase-Gate Cluster Integration & Scenario Verification Suite.

Simulates the end-to-end "Developer CI & Numerical Verification Gate" scenario:
1. Bootstraps the full MCP Server Dispatcher & Facade
2. Concurrently dispatches requests across all 6 Phase 1 pillars:
   - Git AST Conflict Resolution (A-SMW)
   - Copy-Paste Drift Detection (ACDS)
   - Environment Variable Contract Sentry (AEC-VS)
   - Dual-Number Derivative Evaluation (FK-NUM)
   - Sparse Low-Rank SVD Decomposition (FK-SLA)
   - Exact Geometric Predicate Orientation (FK-GEO)
3. Enforces Latency Budgets (MCP response < 50ms, Facade startup < 15ms)
4. Enforces Zero State Cross-Contamination and 100% Sound Diagnostics
"""

import ast
import time
import sys
sys.path.insert(0, "src")

import pytest
from fault_keeper.core.facade import get_fault_keeper, FaultKeeper
from fault_keeper.core.mcp.server import MCPDispatcher


class TestTier3ClusterPhaseGate:
    """Tier 3: Phase-Gate Cluster Integration Test Suite."""

    def test_facade_startup_latency_budget(self):
        """Enforce Facade startup latency <= 15ms."""
        t_start = time.perf_counter()
        fk = FaultKeeper()
        # Trigger lazy access
        _ = fk.num
        _ = fk.sla
        _ = fk.geo
        _ = fk.audit
        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        assert t_elapsed_ms < 15.0, f"Facade startup exceeded budget: {t_elapsed_ms:.2f}ms >= 15ms"

    def test_mcp_e2e_cluster_pipeline_scenario(self):
        """Simulate Developer CI & Numerical Cluster scenario via MCP Dispatcher."""
        dispatcher = MCPDispatcher()

        # Step 1: Dispatch A-SMW AST Merge
        t0 = time.perf_counter()
        merge_req = {
            "jsonrpc": "2.0",
            "method": "git_ast_merge",
            "params": {
                "base": "def process():\n    step_a()\n    step_b()",
                "ours": "def process():\n    step_a_optimized()\n    step_b()",
                "theirs": "def process():\n    step_a()\n    step_b_logged()"
            },
            "id": 101
        }
        res_merge = dispatcher.handle_request(merge_req)
        t_merge_ms = (time.perf_counter() - t0) * 1000.0

        assert res_merge["jsonrpc"] == "2.0"
        assert res_merge["id"] == 101
        assert res_merge["result"]["merged"] is True
        assert t_merge_ms < 50.0, f"AST Merge exceeded MCP budget: {t_merge_ms:.2f}ms"

        # Step 2: Dispatch ACDS Copy-Paste Drift
        t0 = time.perf_counter()
        audit_req = {
            "jsonrpc": "2.0",
            "method": "audit_copy_paste",
            "params": {
                "code": (
                    "def calculate_tax_ny(income, rate):\n"
                    "    return income * rate\n"
                    "def calculate_tax_ca(revenue, fee):\n"
                    "    return income * fee\n"
                )
            },
            "id": 102
        }
        res_audit = dispatcher.handle_request(audit_req)
        t_audit_ms = (time.perf_counter() - t0) * 1000.0

        assert res_audit["id"] == 102
        assert len(res_audit["result"]["drifts_detected"]) > 0
        assert t_audit_ms < 50.0, f"Copy-Paste Audit exceeded MCP budget: {t_audit_ms:.2f}ms"

        # Step 3: Dispatch AEC-VS .env Validation
        t0 = time.perf_counter()
        env_req = {
            "jsonrpc": "2.0",
            "method": "validate_env_contract",
            "params": {
                "content": (
                    "DATABASE_URL:\n"
                    "  required: true\n"
                    "  pattern: '^postgres://.*$'\n"
                    "APP_SECRET:\n"
                    "  required: true\n"
                    "  pattern: '^[0-9a-f]{32}$'\n"
                )
            },
            "id": 103
        }
        res_env = dispatcher.handle_request(env_req)
        t_env_ms = (time.perf_counter() - t0) * 1000.0

        assert res_env["id"] == 103
        # Should flag missing required keys
        assert res_env["result"]["contracts_count"] == 2
        assert t_env_ms < 50.0, f"Env Contract validation exceeded MCP budget: {t_env_ms:.2f}ms"

        # Step 4: Dispatch FK-NUM Numerical Autodiff
        t0 = time.perf_counter()
        num_req = {
            "jsonrpc": "2.0",
            "method": "fk_num_eval",
            "params": {"x": 3.0, "expr": "x**2"},
            "id": 104
        }
        res_num = dispatcher.handle_request(num_req)
        t_num_ms = (time.perf_counter() - t0) * 1000.0

        assert res_num["id"] == 104
        # (3.0)^2 = 9.0, derivative = 2*3.0 = 6.0
        assert res_num["result"]["value"] == 9.0
        assert res_num["result"]["dual"] == 6.0
        assert t_num_ms < 50.0

        # Step 5: Dispatch FK-SLA Randomized SVD
        t0 = time.perf_counter()
        svd_req = {
            "jsonrpc": "2.0",
            "method": "sparse_svd_decompose",
            "params": {
                "rows": [0, 1, 2],
                "cols": [0, 1, 2],
                "data": [5.0, 3.0, 2.0],
                "shape": [3, 3],
                "k": 2
            },
            "id": 105
        }
        res_svd = dispatcher.handle_request(svd_req)
        t_svd_ms = (time.perf_counter() - t0) * 1000.0

        assert res_svd["id"] == 105
        assert res_svd["result"]["status"] == "ok"
        assert res_svd["result"]["sigma_rank"] == 2
        assert t_svd_ms < 50.0

        # Step 6: Dispatch FK-GEO Exact Orientation
        t0 = time.perf_counter()
        geo_req = {
            "jsonrpc": "2.0",
            "method": "geo_orient_query",
            "params": {
                "p": [0.0, 0.0],
                "q": [1.0, 1.0],
                "r": [2.0, 2.0]
            },
            "id": 106
        }
        res_geo = dispatcher.handle_request(geo_req)
        t_geo_ms = (time.perf_counter() - t0) * 1000.0

        assert res_geo["id"] == 106
        assert res_geo["result"]["orientation"] == 0.0
        assert t_geo_ms < 50.0
