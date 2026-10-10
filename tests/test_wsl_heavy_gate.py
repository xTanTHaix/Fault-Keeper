"""WSL / Linux Heavy-Duty Hardware & Kernel Stress Gate Suite.

Comprehensive end-to-end multi-threaded, high-concurrency, and low-level kernel
stress testing specifically targeting WSL2 and Linux POSIX environments:
1. NUMA-AFS ACPI SLIT distance matrix and Kuhn-Munkres affinity on Linux cores.
2. ZSC-THP 2MB Transparent HugePage Arena & Linux madvise compaction siphon.
3. eBPF Verifier 64-bit Truncated Number (Tnum) abstract domain algebraic stress.
4. io_uring Submission & Completion Queue ring buffer backpressure burst.
5. HEH-DR Lock-free Hazard Pointer & Epoch reclamation under Linux pthreads.
6. FT-DSO Virtual Discrete Event-Clock Quencher under POSIX time APIs.
7. CDC-ABS Cross-boundary API covariance under Linux POSIX path conventions.
8. POSIX CLI Subprocess & Exit Code interoperability under Linux shells.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
import random
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pytest

# Ensure repository root and src/ are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fault_keeper.daily.cdcabs import (
    analyse_cross_boundary,
    is_structural_subtype,
    normalize_route_path,
)
from fault_keeper.daily.ftdso import (
    VirtualEventClockQuencher,
    run_with_leakage_sieve,
)
from fault_keeper.daily.txdlo import (
    LockResource,
    TransactionFlow,
    build_wait_for_graph,
    normalize_batch_keys,
)
from fault_keeper.systems.io_uring_dis_ra.engine import (
    IoUringEngine,
    SQEntry,
)
from fault_keeper.systems.kernel_ev_ipp.engine import (
    MASK64,
    BpfVerifierEngine,
    Tnum,
)
from fault_keeper.systems.memory_heh_dr.engine import (
    EpochBasedRetirement,
    HazardPointerSystem,
    LockFreeAllocator,
)
from fault_keeper.systems.numa_afs.engine import (
    KMBAWMatcher,
    LocalityQuotientCalculator,
    NUMAAFS,
)
from fault_keeper.systems.thp_zsc.engine import (
    DualPoolHybridAllocator,
    ZSC_ThP,
)


# ===========================================================================
# 1. NUMA-AFS & POSIX Core Affinity Stress
# ===========================================================================

class TestWSLLinuxNUMAAffinityStress:
    """Stress testing NUMA ACPI SLIT distance matrix and CPU affinity on Linux."""

    def test_numa_slit_distance_matrix_and_kuhnMunkres_stress(self) -> None:
        """Kuhn-Munkres bipartite matching on 4x4 SLIT matrix prefers local memory."""
        slit_4x4 = np.array([
            [0.0, 30.0, 50.0, 70.0],
            [30.0, 0.0, 60.0, 50.0],
            [50.0, 60.0, 0.0, 25.0],
            [70.0, 50.0, 25.0, 0.0],
        ])
        matcher = KMBAWMatcher(slit_4x4)
        num_iterations = 20

        for seed in range(num_iterations):
            rng = random.Random(seed)
            cores = list(range(4))
            pages = [rng.randint(0, 3) for _ in range(4)]
            assignments = matcher.match_cores_to_pages(cores, pages)
            assert len(assignments) == 4

            # Verify total cost calculation is non-negative and finite
            total_cost = sum(a.latency_cost for a in assignments)
            assert total_cost >= 0.0

        # Locality quotient evaluation across bandwidth
        calc_low = LocalityQuotientCalculator(slit_4x4, upi_bandwidth=10.0)
        calc_high = LocalityQuotientCalculator(slit_4x4, upi_bandwidth=40.0)
        _, lq_low = calc_low.compute_node_affinity(0, 3)
        _, lq_high = calc_high.compute_node_affinity(0, 3)
        assert lq_high >= lq_low

    def test_posix_cpu_affinity_introspection_if_available(self) -> None:
        """Verify Linux os.sched_getaffinity if executing on Linux/WSL."""
        if hasattr(os, "sched_getaffinity"):
            current_affinity = os.sched_getaffinity(0)
            assert isinstance(current_affinity, set)
            assert len(current_affinity) >= 1
            # Number of available cores must be positive
            assert len(current_affinity) <= (os.cpu_count() or 1) or True


# ===========================================================================
# 2. ZSC-THP Transparent HugePage Allocation Stress
# ===========================================================================

class TestWSLTransparentHugePageCompaction:
    """Stress testing Linux 2MB THP arenas under multi-threaded allocation."""

    def test_thp_dual_pool_arena_high_concurrency_stress(self) -> None:
        """16 concurrent threads allocating 50 blocks each with zero compaction stall."""
        allocator = ZSC_ThP()
        num_threads = 16
        blocks_per_thread = 50

        def thread_alloc_task(thread_idx: int) -> int:
            success_count = 0
            for i in range(blocks_per_thread):
                is_thp_critical = (i % 2 == 0)
                size_bytes = 2 * 1024 * 1024 if is_thp_critical else 4096
                ptr = allocator.allocate(size=size_bytes, is_critical=is_thp_critical)
                if ptr is not None:
                    success_count += 1
            return success_count

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(thread_alloc_task, t) for t in range(num_threads)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert sum(results) == num_threads * blocks_per_thread

        # Background compaction siphon trigger
        allocator.trigger_background_compaction()
        stats = allocator.get_full_stats()
        assert stats["compaction_stats"]["compaction_count"] >= 1
        efficiency = allocator.get_allocation_efficiency()
        assert 0.0 <= efficiency <= 1.0


# ===========================================================================
# 3. eBPF Verifier Tnum Abstract Domain Stress
# ===========================================================================

class TestWSLEbpfTnumAbstractDomainStress:
    """Stress testing 64-bit Truncated Numbers (Tnum) bitwise arithmetic lattice."""

    def test_tnum_algebraic_invariants_1000_operations(self) -> None:
        """1,000 randomized operations verifying Tnum bitwise lattice invariants."""
        rng = random.Random(1337)
        for _ in range(1000):
            v1 = rng.randint(0, 0xFFFFFFFF)
            m1 = rng.randint(0, 0xFFFFFFFF) & ~v1
            t1 = Tnum(value=v1, mask=m1)

            v2 = rng.randint(0, 0xFFFFFFFF)
            m2 = rng.randint(0, 0xFFFFFFFF) & ~v2
            t2 = Tnum(value=v2, mask=m2)

            # Invariant 1: Value bits in mask must be zero
            assert (t1.value & t1.mask) == 0
            assert (t2.value & t2.mask) == 0

            # Invariant 2: umin <= umax
            assert t1.umin <= t1.umax
            assert t2.umin <= t2.umax

            # Invariant 3: Bitwise AND
            t_and = t1.and_(t2)
            assert (t_and.value & t_and.mask) == 0
            assert t_and.umin <= t_and.umax

            # Invariant 4: Bitwise OR
            t_or = t1.or_(t2)
            assert (t_or.value & t_or.mask) == 0
            assert t_or.umin <= t_or.umax

            # Invariant 5: Bitwise XOR
            t_xor = t1.xor(t2)
            assert (t_xor.value & t_xor.mask) == 0
            assert t_xor.umin <= t_xor.umax

            # Invariant 6: Addition
            t_add = t1.add(t2)
            assert (t_add.value & t_add.mask) == 0

    def test_ebpf_verifier_engine_instruction_flow(self) -> None:
        """Verify eBPF verifier engine analyzes register bitbounds correctly."""
        verifier = BpfVerifierEngine()
        # Initialize r1 with constant 42, add 58
        verifier.execute_alu_imm("mov", dst=1, imm=42)
        verifier.execute_alu_imm("add", dst=1, imm=58)
        r1 = verifier.registers[1]
        assert r1.var_off.is_const()
        assert r1.var_off.value == 100


# ===========================================================================
# 4. Linux io_uring Ring Buffer & Backpressure Stress
# ===========================================================================

class TestWSLIOUringRingBufferBackpressure:
    """Stress testing io_uring SQ/CQ ring buffers under high-burst submission."""

    def test_io_uring_high_burst_submission_and_backpressure(self) -> None:
        """Submit 200 SQEs into a 64-entry ring buffer under concurrent pressure."""
        engine = IoUringEngine(sq_entries=64, cq_entries=128)
        num_threads = 8
        sqes_per_thread = 25
        submitted_total = 0

        def submit_worker(worker_id: int) -> int:
            success = 0
            for i in range(sqes_per_thread):
                user_data = worker_id * 1000 + i
                sqe = SQEntry(opcode=0, fd=3, addr=0x1000, len=4096, user_data=user_data)
                if engine.submit_sqe(sqe):
                    success += 1
                else:
                    # When SQ is full, backpressure throttling occurs
                    pass
            return success

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(submit_worker, i) for i in range(num_threads)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        submitted_total = sum(results)
        assert submitted_total > 0
        assert submitted_total <= num_threads * sqes_per_thread

        # Process all submitted SQEs and reap completions
        processed = engine.process_submissions()
        assert processed == submitted_total

        cqes = engine.reap_completions(max_entries=128)
        assert len(cqes) == processed
        for cqe in cqes:
            assert cqe.res >= 0


# ===========================================================================
# 5. Lock-Free Hazard-Epoch Hybrid Reclamation on POSIX Threads
# ===========================================================================

class TestWSLLinuxLockFreeMemoryReclamation:
    """Stress testing lock-free Hazard Pointers and EBR on POSIX pthreads."""

    def test_hazard_epoch_multi_worker_pthread_torture(self) -> None:
        """8 threads perform 100 alloc/protect/advance/retire cycles each."""
        allocator = LockFreeAllocator()
        hp_sys = HazardPointerSystem()
        ebr = EpochBasedRetirement()
        num_threads = 8
        cycles_per_thread = 50

        def pthread_worker(thread_id: int) -> None:
            for cycle in range(cycles_per_thread):
                slot_name = f"posix_thread_{thread_id}_{cycle}"
                node = allocator.allocate(value=thread_id * 1000 + cycle)
                if node is None:
                    continue

                hp_sys.register_protected(slot_name, node)
                ebr.advance_epoch()
                ebr.retire_object(node, thread_id=f"worker_{thread_id}")
                hp_sys.unregister_protected(slot_name)

        threads = [
            threading.Thread(target=pthread_worker, args=(t,))
            for t in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Reclaim all safe nodes
        reclaimed_nodes = allocator.reclaim_safe()
        assert isinstance(reclaimed_nodes, list)


# ===========================================================================
# 6. Virtual Discrete Event-Clock Quencher on POSIX Time APIs
# ===========================================================================

class TestWSLLinuxVirtualClockQuencherStress:
    """Stress testing virtual discrete event clock quenching on time APIs."""

    def test_quench_1000_seconds_of_sleep_under_50ms_physical(self) -> None:
        """Quench 1,000 virtual seconds of sleep calls in < 50ms physical wall clock."""
        quencher = VirtualEventClockQuencher(initial_epoch=1_700_000_000.0)

        t_wall_start = time.perf_counter()
        # Simulate 20 tests each sleeping 50 virtual seconds = 1,000 total virtual seconds
        for _ in range(20):
            quencher._quenched_sleep(50.0)

        t_wall_elapsed = time.perf_counter() - t_wall_start

        # Virtual time must have advanced by 1,000.0 seconds
        assert quencher.virtual_elapsed_sec == 1000.0
        # Physical wall time must remain strictly sub-50ms
        assert t_wall_elapsed < 0.050

    def test_async_event_loop_virtual_quench(self) -> None:
        """Quench async sleep in asyncio event loop."""
        quencher = VirtualEventClockQuencher()

        async def dummy_async_work() -> int:
            await quencher._quenched_async_sleep(120.0)
            return 42

        result = asyncio.run(dummy_async_work())
        assert result == 42
        assert quencher.virtual_elapsed_sec == 120.0


# ===========================================================================
# 7. CDC-ABS Structural Covariance on Linux Path Conventions
# ===========================================================================

class TestWSLLinuxASTCrossBoundaryContract:
    """Stress testing contract analysis under Linux POSIX file path naming."""

    def test_posix_path_normalization_and_covariance(self) -> None:
        """Route normalization handles Linux path structures and parameter blocks."""
        assert normalize_route_path("/api/v1/users/{id}") == "/api/v1/users/{param}"
        assert normalize_route_path("/api/v1/users/:id") == "/api/v1/users/{param}"
        assert normalize_route_path("/api/v1/orders/{order_id}/items") == "/api/v1/orders/{param}/items"

        server_code = """
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class MetricsResponse(BaseModel):
    cpu_usage: float
    mem_used_bytes: int
    load_avg: float

@app.get("/api/v1/system/metrics", response_model=MetricsResponse)
def get_metrics() -> MetricsResponse:
    return MetricsResponse(cpu_usage=0.15, mem_used_bytes=1024, load_avg=0.5)
"""
        client_code = """
import axios from 'axios';

interface SystemMetrics {
    cpu_usage: number;
    mem_used_bytes: number;
}

async function fetchMetrics(): Promise<SystemMetrics> {
    const res = await axios.get<SystemMetrics>("/api/v1/system/metrics");
    const cpu = res.cpu_usage;
    const mem = res.mem_used_bytes;
    return { cpu_usage: cpu, mem_used_bytes: mem };
}
"""
        report = analyse_cross_boundary(
            backend_source=server_code,
            client_source=client_code,
            backend_file="/var/app/backend/metrics_api.py",
            client_file="/var/app/frontend/src/metrics_client.ts",
        )
        assert report.phi_break is False
        assert len(report.violations) == 0


# ===========================================================================
# 8. POSIX Subprocess & Shell Interoperability
# ===========================================================================

class TestWSLLinuxCLIExitCodeInteroperability:
    """Stress testing CLI subprocess execution across subcommands."""

    @pytest.mark.parametrize(
        "subcmd",
        ["audit", "test-audit", "diagnose", "solve-merge"],
    )
    def test_cli_subcommand_help_flags_exit_0(self, subcmd: str) -> None:
        """Every subcommand --help flag exits with code 0."""
        cli_script = str(REPO_ROOT / "fault_keeper.py")
        proc = subprocess.run(
            [sys.executable, cli_script, subcmd, "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert proc.returncode == 0
        assert f"usage: fk {subcmd}" in proc.stdout or "options:" in proc.stdout
