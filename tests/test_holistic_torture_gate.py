"""Holistic Torture & Heavy Stress Phase-Gate Suite.

Comprehensive end-to-end multi-threaded, high-concurrency, and large-scale
stress testing across all core subsystems:
1. Havender Canonical Lock Ordering (Tx-DLO) under high-concurrency contention.
2. ZSC-THP Zero-Stall Arena & HEH-DR Hazard-Epoch Memory Reclamation torture.
3. CDC-ABS Structural Subtyping Covariance on large-scale API surfaces.
4. FT-DSO Gray Code Binary Search minimal toxic pair isolation.
5. Topological Simplicial Concurrency Arbiter (TSCA) Betti number invariance.
6. MCP 2.0 Omni-Facade high-frequency concurrent request burst.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import random
import sys
import threading
import time
from typing import Any, Dict, List, Mapping, Sequence, Set, Tuple

import pytest

# Ensure repository root and src/ are in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Core imports
from fault_keeper.daily.txdlo import (
    LockResource,
    TransactionDeadlockOracle,
    TransactionFlow,
    build_wait_for_graph,
    compute_lock_contention_entropy,
    normalize_batch_keys,
    verify_havender_lock_ordering,
)
from fault_keeper.daily.ftdso import (
    FlakyTestDeterministicSieve,
    isolate_minimal_toxic_pair,
    verify_order_invariance,
)
from fault_keeper.daily.cdcabs import (
    CrossBoundaryContractSentry,
    analyse_cross_boundary,
    compute_inhabitation_quotient,
    is_structural_subtype,
)
from fault_keeper.systems.thp_zsc.engine import (
    DualPoolHybridAllocator,
    ZSC_ThP,
)
from fault_keeper.systems.memory_heh_dr.engine import (
    EpochBasedRetirement,
    HazardPointerSystem,
    LockFreeAllocator,
)
from fault_keeper.systems.concurrency_tsc.engine import (
    HomologyEngine,
    SimplicialComplex,
    TSCAEngine,
)
from fault_keeper.core.mcp.server import MCPDispatcher
from fault_keeper.mcp.omni_facade import MCPOmniFacade


# ===========================================================================
# 1. Havender Canonical Lock Ordering & WFG Torture (Tx-DLO)
# ===========================================================================

class TestTxDLOHavenderTorture:
    """Stress testing transaction lock ordering under high contention."""

    def test_high_concurrency_havender_lock_sorting_torture(self) -> None:
        """16 threads sort random batches of keys concurrently with strict monotonicity."""
        num_workers = 16
        keys_per_worker = 100
        table_ranks = {
            "users": 1,
            "accounts": 2,
            "orders": 3,
            "ledger": 4,
            "inventory": 5,
        }

        def worker_sort(seed: int) -> List[LockResource]:
            rng = random.Random(seed)
            tables = list(table_ranks.keys())
            resources = [
                LockResource(
                    table=rng.choice(tables),
                    primary_key=rng.randint(1, 500),
                    table_rank=table_ranks[rng.choice(tables)],
                )
                for _ in range(keys_per_worker)
            ]
            # Normalise and sort via Havender canonical order (deduplicates and sorts)
            sorted_resources = normalize_batch_keys(resources)
            assert len(sorted_resources) == len(set(resources))

            # Verify Havender total ordering: (rank, table, pkey) is monotonically non-decreasing
            for i in range(len(sorted_resources) - 1):
                r1 = sorted_resources[i]
                r2 = sorted_resources[i + 1]
                assert r1.sort_key() <= r2.sort_key(), (
                    f"Violation of Havender total order: {r1} > {r2}"
                )
            return sorted_resources

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker_sort, i) for i in range(32)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 32

    def test_wfg_cycle_detection_and_havender_resolution_torture(self) -> None:
        """Construct circular transaction dependencies, detect cycle, and resolve via Havender."""
        num_transactions = 10
        # Circular chain: T_i locks R_i then R_{(i+1)%N}
        cyclic_txs = []
        for i in range(num_transactions):
            r_curr = LockResource(table=f"tbl_{i}", primary_key=1, table_rank=i + 1)
            r_next = LockResource(
                table=f"tbl_{(i + 1) % num_transactions}",
                primary_key=1,
                table_rank=((i + 1) % num_transactions) + 1,
            )
            cyclic_txs.append(
                TransactionFlow(
                    tx_id=f"tx_{i}",
                    locks=[r_curr, r_next],
                )
            )

        # 1. Cycle detection in WFG
        wfg_report = build_wait_for_graph(cyclic_txs)
        assert wfg_report.is_deadlock_free is False
        assert wfg_report.h1_betti_number >= 1

        # 2. Re-order each transaction's locks according to Havender total order
        resolved_txs = []
        for tx in cyclic_txs:
            sorted_locks = sorted(tx.locks, key=lambda r: r.sort_key())
            resolved_txs.append(TransactionFlow(tx_id=tx.tx_id, locks=sorted_locks))

        # 3. Check Havender verification report
        havender_report = verify_havender_lock_ordering(resolved_txs)
        assert havender_report.is_canonical is True
        assert len(havender_report.violations) == 0

    def test_lock_contention_entropy_under_heavy_concurrency(self) -> None:
        """Lock contention entropy accurately quantifies resource hotspot skew."""
        flows = []
        # Highly skewed access pattern on hot key 'account:100'
        for i in range(100):
            if i % 3 == 0:
                locks = [LockResource(table="account", primary_key=100, table_rank=1)]
            else:
                locks = [LockResource(table="account", primary_key=i, table_rank=1)]
            flows.append(TransactionFlow(tx_id=f"tx_{i}", locks=locks))

        entropy_report = compute_lock_contention_entropy(flows)
        assert entropy_report.h_contention > 0.0
        assert entropy_report.hotspot_resource == "account:100"


# ===========================================================================
# 2. Systems Low-Level Memory & Reclamation Torture (ZSC-THP & HEH-DR)
# ===========================================================================

class TestSystemsMemoryTorture:
    """Stress testing low-level zero-stall memory and lock-free reclamation."""

    def test_zsc_thp_multi_threaded_allocation_stress(self) -> None:
        """Allocate and track 2MB THP and 4KB blocks across concurrent threads."""
        allocator = ZSC_ThP()
        num_threads = 8
        ops_per_thread = 20

        def alloc_worker(worker_id: int) -> int:
            allocated = 0
            for i in range(ops_per_thread):
                size = 1024 * 1024 * 2 if i % 2 == 0 else 4096
                is_crit = (i % 2 == 0)
                ptr = allocator.allocate(size=size, is_critical=is_crit)
                if ptr is not None:
                    allocated += 1
            return allocated

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(alloc_worker, i) for i in range(num_threads)]
            counts = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert sum(counts) == num_threads * ops_per_thread

        # Background compaction siphon trigger
        allocator.trigger_background_compaction()
        efficiency = allocator.get_allocation_efficiency()
        assert 0.0 <= efficiency <= 1.0

    def test_heh_dr_hazard_epoch_reclamation_torture(self) -> None:
        """Concurrent epoch advancements and hazard pointer protection."""
        allocator = LockFreeAllocator()
        hp_sys = HazardPointerSystem()
        ebr = EpochBasedRetirement()
        num_threads = 6

        def worker_epoch_advance(thread_id: int) -> None:
            for i in range(25):
                slot_id = f"worker_{thread_id}_{i}"
                ptr = allocator.allocate(value=128)
                hp_sys.register_protected(slot_id, ptr)

                # Advance global epoch safely
                ebr.advance_epoch()
                ebr.retire_object(ptr, thread_id=f"thread_{thread_id}")

                # Unprotect slot
                hp_sys.unregister_protected(slot_id)
                time.sleep(0.0005)

        threads = [
            threading.Thread(target=worker_epoch_advance, args=(i,))
            for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Reclaim safe nodes
        active_guards = hp_sys.get_active_protectors()
        assert isinstance(active_guards, set)
        reclaimed = allocator.reclaim_safe()
        assert isinstance(reclaimed, list)


# ===========================================================================
# 3. Structural Subtyping Covariance Torture (CDC-ABS)
# ===========================================================================

class TestCDCCovarianceLargeSurfaceTorture:
    """Stress testing cross-boundary subtyping covariance on large schemas."""

    def test_structural_subtyping_primitive_lattice(self) -> None:
        """Verify subtyping lattice tau_new <=_sub tau_client across primitive and union types."""
        # int <=_sub float
        assert is_structural_subtype("int", "float") is True
        # int <=_sub int
        assert is_structural_subtype("int", "int") is True
        # Union widening: int <=_sub Union[int, str]
        assert is_structural_subtype("int", "Union[int, str]") is True
        # Incompatible types: str is not subtype of int
        assert is_structural_subtype("str", "int") is False

    def test_large_cross_boundary_ast_contract_torture(self) -> None:
        """Verify cross-boundary API contract analysis with compliant subtyping and breaking changes."""
        # Server code offering endpoints
        server_code = """
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class UserDTO(BaseModel):
    user_id: int
    name: str
    email: Optional[str]
    score: int

@app.get("/api/v1/users/{user_id}", response_model=UserDTO)
def get_user(user_id: int) -> UserDTO:
    return UserDTO()
"""
        # Client code calling the endpoints with compliant field requirements
        client_code = """
import axios from 'axios';

interface UserResponse {
    user_id: number;
    name: string;
}

async function fetchUser(userId: string) {
    const res = await axios.get<UserResponse>(`/api/v1/users/${userId}`);
    const uid = res.user_id;
    const n = res.name;
    return { uid, n };
}
"""
        # 1. Compliant analysis
        report = analyse_cross_boundary(
            backend_source=server_code,
            client_source=client_code,
            backend_file="backend/user.py",
            client_file="frontend/user.ts",
        )
        assert report.phi_break is False
        assert len(report.violations) == 0

        # 2. Breaking change: delete required field `user_id` on server
        breaking_server = server_code.replace("user_id: int", "uid: int")
        breaking_report = analyse_cross_boundary(
            backend_source=breaking_server,
            client_source=client_code,
            old_backend_source=server_code,
            backend_file="backend/user.py",
            client_file="frontend/user.ts",
        )
        assert breaking_report.phi_break is True
        assert len(breaking_report.violations) >= 1
        assert any("user_id" in b.field_name for b in breaking_report.violations)


# ===========================================================================
# 4. Gray Code Minimal Toxic Pair Sieve (FT-DSO)
# ===========================================================================

class TestFTDSOGrayCodeIsolationTorture:
    """Stress testing Gray Code minimal toxic pair slicing under order dependencies."""

    def test_gray_code_slicing_isolates_toxic_pair_heavy(self) -> None:
        """Isolate toxic polluter-victim pair among 30 test cases in O(N log N)."""
        all_tests = [f"test_unit_{i:02d}" for i in range(30)]
        toxic_polluter = "test_unit_08"
        toxic_victim = "test_unit_21"

        def test_runner(order: Sequence[str]) -> Dict[str, str]:
            polluted = False
            outcomes: Dict[str, str] = {}
            for tid in order:
                if tid == toxic_polluter:
                    polluted = True
                    outcomes[tid] = "PASS"
                elif tid == toxic_victim and polluted:
                    outcomes[tid] = "FAIL"  # Victim fails when polluter ran before it
                else:
                    outcomes[tid] = "PASS"
            return outcomes

        # Verify order invariance catches the flakiness
        invariance = verify_order_invariance(all_tests, test_runner, seed=42)
        assert invariance.is_order_independent is False
        assert toxic_victim in invariance.divergent_tests

        # Gray Code toxic pair isolation
        sieve = FlakyTestDeterministicSieve(seed=42)
        audit = sieve.audit_suite(
            all_tests,
            test_runner,
            source_code=f"def {toxic_victim}():\n    assert True\n",
        )
        assert len(audit.toxic_pairs) == 1
        pair = audit.toxic_pairs[0]
        assert pair.polluter == toxic_polluter
        assert pair.victim == toxic_victim
        assert pair.reproducible is True


# ===========================================================================
# 5. Topological Simplicial Concurrency Arbiter (TSCA)
# ===========================================================================

class TestTSCASimplicialHomologyTorture:
    """Stress testing wait-free simplicial complex homology computation."""

    def test_simplicial_complex_betti_invariance(self) -> None:
        """Verify 1st Betti number is exactly 0 for acyclic trees, >= 1 for cycles."""
        complex_k = SimplicialComplex()

        # Build an acyclic tree of state transitions: 0-1, 1-2, 2-3, 3-4, 4-5
        for i in range(5):
            complex_k.add_edge(i, i + 1)

        engine = HomologyEngine(complex_k)
        # Betti-1 must be exactly 0 (no topological cycles)
        assert engine.compute_first_betti() == 0
        assert engine.is_deadlock_free() is True

        # Close the cycle: add edge 5-0 to form an uncontractible 1-cycle
        complex_k.add_edge(5, 0)
        assert engine.compute_first_betti() >= 1
        assert engine.is_deadlock_free() is False

        # Fill with 2-simplices (triangles) to render cycles contractible
        # Triangles: (0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 5)
        complex_k.add_face(0, 1, 2)
        complex_k.add_face(0, 2, 3)
        complex_k.add_face(0, 3, 4)
        complex_k.add_face(0, 4, 5)

        # Now all 1-cycles are boundaries of 2-simplices => Betti-1 drops to 0!
        assert engine.compute_first_betti() == 0
        assert engine.is_deadlock_free() is True


# ===========================================================================
# 6. MCP 2.0 Omni-Protocol Rapid Concurrency Burst
# ===========================================================================

class TestMCPOmniProtocolBurstTorture:
    """Stress testing MCP 2.0 JSON-RPC dispatcher under rapid thread burst."""

    def test_rapid_concurrent_tool_dispatch_burst(self) -> None:
        """Execute 100 concurrent requests across all 5 Omni-Tools."""
        dispatcher = MCPDispatcher()
        num_threads = 10
        reqs_per_thread = 10

        def send_tool_call(thread_id: int, req_idx: int) -> Dict[str, Any]:
            req_id = thread_id * 1000 + req_idx
            tools = ["fk_audit", "fk_diagnose", "fk_patch", "fk_verify", "fk_discover"]
            tool_name = tools[req_idx % len(tools)]

            if tool_name == "fk_audit":
                params = {"name": "fk_audit", "arguments": {"target": "src/fault_keeper"}}
            elif tool_name == "fk_diagnose":
                params = {"name": "fk_diagnose", "arguments": {"target": "src/fault_keeper", "symptom": "deadlock"}}
            elif tool_name == "fk_patch":
                params = {"name": "fk_patch", "arguments": {"target": "src/fault_keeper", "dry_run": True}}
            elif tool_name == "fk_verify":
                params = {"name": "fk_verify", "arguments": {"target": "src/fault_keeper", "contract": {}}}
            else:
                params = {"name": "fk_discover", "arguments": {"domains": ["deadlock"]}}

            req = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "tools/call",
                "params": params,
            }
            res = dispatcher.handle_request(req)
            assert res is not None
            assert res.get("id") == req_id
            assert "result" in res
            return res

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(send_tool_call, tid, rid)
                for tid in range(num_threads)
                for rid in range(reqs_per_thread)
            ]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(responses) == num_threads * reqs_per_thread

    def test_mcp_virtual_resource_concurrent_rw_torture(self) -> None:
        """Simultaneous register and read operations on virtual resources."""
        facade = MCPOmniFacade()
        num_ops = 50

        def rw_worker(idx: int) -> None:
            filename = f"module_{idx}.py"
            payload = f"def function_{idx}(): pass"
            facade.resource_provider.register_ast(filename, payload)
            read_back = facade.resource_provider.read_ast(filename)
            assert read_back == payload

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(rw_worker, i) for i in range(num_ops)]
            for f in concurrent.futures.as_completed(futures):
                f.result()
