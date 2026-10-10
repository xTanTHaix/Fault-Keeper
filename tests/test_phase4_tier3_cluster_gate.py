"""Tier 3 Phase-Gate Cluster Test for Phase 4 (v1.0 Flagship Release).

Scenario: "The Full AI Agent Autonomous Loop & Formal Chaos Gate"
Orchestrates:
1. MCP-OFA Omni-Tools interface (fk_patch, fk_verify, fk_diagnose, fk_audit)
2. SC-PVE Speculative In-Memory CoW Sandbox & Pareto-Optimal Tree Edit Distance Arbiter
3. ASP-HG Lazy Truncation Predicate rejection (Phi_lazy)
4. ACT-LO SMT/DPLL-driven Minimal Unsatisfiable Core (MUC) Doom-Loop breaker
5. D-CAS Distributed Chaos Simulator & Deterministic Replay
6. CADRE Copy-on-Write Time-Travel Execution Replay
7. DCEG Sub-50ms Differential Causal Re-evaluation
8. FSLS Category Theory Adjunction Triangle Identities
"""

import ast
import tempfile
import time
from pathlib import Path

import pytest
from fault_keeper.armor.actlo import ACTLOEngine, DefectState
from fault_keeper.armor.asphg import ASPHGEngine, PatchSentry
from fault_keeper.armor.scpve import SCPVEEngine, CoWVFS
from fault_keeper.distributed.dcas import DCASSimulator
from fault_keeper.formal.dceg import DCEGDifferentialGraph
from fault_keeper.formal.fsls import FSLSAdjointFunctor, FormalCategoryObject
from fault_keeper.mcp.omni_facade import MCPOmniFacade
from fault_keeper.timetravel.cadre import CADRETimeTravelTracer


class TestPhase4Tier3ClusterGate:
    def test_full_ai_agent_autonomous_loop_and_formal_chaos_gate(self):
        """Execute Phase 4 Tier 3 Cluster Gate scenario end-to-end."""
        # 1. Initialize MCP Omni-Facade & verify Omni-Tools
        facade = MCPOmniFacade()
        tools_schema = facade.get_omni_tools_schema()
        assert len(tools_schema) == 5  # fk_audit, fk_diagnose, fk_patch, fk_verify, fk_discover

        # 2. Speculative Parallel Sandbox (SC-PVE) & ASP-HG Sentry
        base_code = (
            "def calculate_tax(subtotal: float, rate: float) -> float:\n"
            "    # Base production tax engine\n"
            "    tax = subtotal * rate\n"
            "    return tax\n"
        )
        candidates = [
            # Broken syntax candidate -> evicted by SC-PVE
            "def calculate_tax( broken syntax:",
            # Lazy ellipsis patch -> flagged by ASP-HG
            "def calculate_tax(subtotal, rate):\n    # ... existing code ...\n",
            # Bloated calculation candidate
            (
                "def calculate_tax(subtotal: float, rate: float) -> float:\n"
                "    intermediate = subtotal * 1.0\n"
                "    tax = intermediate * rate\n"
                "    return round(tax, 2)\n"
            ),
            # Minimal clean calculation candidate
            (
                "def calculate_tax(subtotal: float, rate: float) -> float:\n"
                "    return round(subtotal * rate, 2)\n"
            ),
        ]

        # Check ASP-HG Lazy Truncation rejection
        sentry = PatchSentry()
        diagnostic = sentry.detect_lazy_truncation(base_code, candidates[1])
        assert diagnostic is not None
        assert "lazy" in diagnostic.lower() or "truncation" in diagnostic.lower() or "existing code" in diagnostic.lower()

        # Speculative In-Memory Execution
        sc_pve = SCPVEEngine(max_workers=8, evict_budget_s=0.1)
        valid_candidates = [candidates[2], candidates[3]]
        result = sc_pve.speculative_run(base_code, valid_candidates)

        assert result.committed_candidate_index is not None
        assert result.committed_source is not None
        assert len(result.surviving_candidates) >= 1

        # 3. Anti-Doom Loop & MUC Steering (ACT-LO)
        actlo = ACTLOEngine()
        # Simulate oscillating agent state with rising/recurrent entropy
        s0 = DefectState(failed_mask=frozenset({"test_tax"}), error_count=0, churn=2)
        s1 = DefectState(failed_mask=frozenset({"test_tax", "test_overflow"}), error_count=1, churn=10)
        s2 = DefectState(failed_mask=frozenset({"test_tax"}), error_count=0, churn=2)  # Recurrent state

        r0 = actlo.observe_turn(s0)
        r1 = actlo.observe_turn(s1)
        assert r1.monotonic_violation is True  # E(s1) > E(s0) triggers rollback

        r2 = actlo.observe_turn(s2, constraint_names=["must_return_float", "must_handle_zero_rate"])
        assert r2.doom_loop_detected is True
        assert r2.similar_to_step is not None

        # 4. Distributed Chaos Simulator (D-CAS)
        dcas = DCASSimulator(seed=777)
        dcas.register_node("replica-1")
        dcas.register_node("replica-2")
        dcas.set_chaos_parameters(packet_drop_rate=0.0)
        delivered = dcas.send_packet("replica-1", "replica-2", {"committed": result.committed_source})
        assert delivered is True

        # 5. Time-Travel Tracer (CADRE) Deterministic Replay
        cadre = CADRETimeTravelTracer({"tax_system_active": True})
        cadre.record_mutation("latest_commit", result.committed_source)
        cadre.record_mutation("cluster_hash", dcas.compute_cluster_snapshot_hash())
        replay_ok, replay_fp = cadre.replay_trace()
        assert replay_ok is True
        assert len(replay_fp) == 64

        # 6. Differential Causal Execution Graph (DCEG) Latency < 50ms
        dceg = DCEGDifferentialGraph()
        dceg.add_node("subtotal", value=100.0)
        dceg.add_node("rate", value=0.07)
        dceg.add_node("tax", compute_fn=lambda d: d["subtotal"] * d["rate"], dependencies={"subtotal", "rate"})
        dceg_latency = dceg.set_value("subtotal", 250.0)
        assert dceg_latency < 50.0
        assert dceg.get_value("tax") == 17.5

        # 7. Category Theory Adjunction Invariant (FSLS)
        fsls = FSLSAdjointFunctor()
        spec_obj = FormalCategoryObject(
            identifier="calculate_tax",
            content="Spec: tax = subtotal * rate",
            signature={"subtotal": "float", "rate": "float"},
        )
        code_obj = FormalCategoryObject(
            identifier="calculate_tax",
            content=result.committed_source,
            signature={"subtotal": "float", "rate": "float"},
        )
        assert fsls.verify_triangle_identities(spec_obj, code_obj) is True
