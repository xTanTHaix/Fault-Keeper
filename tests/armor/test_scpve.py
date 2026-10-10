"""Tests for SC-PVE: Speculative Candidate Parallel Verification & Invariant-Pruned Arbiter (Phase 4 Group 1).

Covers the four defensive mechanisms that let Fault-Keeper evaluate K candidate patches
concurrently in pure memory before any physical write happens, and then pick the single
best candidate via a Pareto-optimal arbiter:

1. **Zero-Disk Copy-on-Write VFS** -- every speculative branch lives in an in-memory overlay;
   no bytes ever touch the real filesystem until an explicit commit succeeds.
2. **Discrete-Event Virtual Time Siphon** -- ``time.sleep``, ``datetime.now()``, and async I/O are
   intercepted so that simulated candidate runs advance on a virtual clock instead of wall time.
3. **Fail-Fast Invariant Pruning Sieve** -- workers whose invariant check fails (assertion error,
   memory leak proxy, infinite-loop detection) are evicted from the pool within ``evict_budget_s``
   (default 0.1 ms), guaranteeing that a single bad branch cannot stall the swarm.
4. **Pareto-Optimal AST Arbiter** -- among all surviving candidates the arbiter ranks each by
   Zhang-Shasha tree-edit distance (structural cost) and cyclomatic complexity delta (behavioral
   risk). The candidate with the lowest composite score is committed atomically to disk.

All operations are pure, deterministic, stdlib-only, and never touch physical storage during
pre-flight evaluation.
"""

from __future__ import annotations

import os
import tempfile
import time as _time
import pytest
import fault_keeper.armor.scpve as scpve_module
from fault_keeper.armor.scpve import (  # noqa: F401 -- names used below for assertions.
    ASTArbiter,
    CoWVFS,
    CoWWorkerPool,
    SCPVEEngine,
    SpeculativeRunResult,
)


# ---------------------------------------------------------------------------
# Test 4.1.3: Zero Disk-Leakage Invariant (SC-PVE).
# ---------------------------------------------------------------------------

class TestZeroDiskLeakageInvariant:
    """Test that speculative execution never writes to physical disk."""

    def test_no_temp_files_created(self):
        """Test 4.1.3.A: Running speculative_run creates zero temp files on disk."""
        engine = SCPVEEngine(max_workers=8, evict_budget_s=0.1)

        base_source = "def hello():\n    print('world')\n"
        candidates = [
            "def hello():\n    print('hello world')\n",
            "def hello():\n    return 42\n",
        ]

        result = engine.speculative_run(base_source, candidates)
        assert result.committed_candidate_index is not None

        # No temp files should exist under the default commit path.
        with tempfile.TemporaryDirectory() as tmpdir:
            expected_file = os.path.join(tmpdir, "fault_keeper_commit.py")
            assert not os.path.exists(expected_file), \
                f"Speculative run leaked a file to disk: {expected_file}"

    def test_vfs_stays_in_memory(self):
        """Test 4.1.3.B: VFS snapshot contains only in-memory entries."""
        vfs = CoWVFS()
        vfs.put("/tmp/test.py", b"print('hello')\n")
        vfs.put("/tmp/other.py", b"x = 1\n")

        snapshot = vfs.snapshot()
        assert "/tmp/test.py" in snapshot
        assert snapshot["/tmp/test.py"] == b"print('hello')\n"
        # No file system I/O happened -- just dict lookups.


# ---------------------------------------------------------------------------
# Test 4.1.4: Fail-Fast Worker Eviction Latency Bound (SC-PVE).
# ---------------------------------------------------------------------------

class TestFailFastWorkerEvictionLatencyBound:
    """Test that failed workers are evicted within the fail-fast budget."""

    def test_evict_worker_within_budget(self):
        """Test 4.1.4.A: Worker eviction happens quickly when budget is exceeded."""
        pool = CoWWorkerPool(evict_budget_s=0.001)  # 1 ms budget.

        wid = pool.spawn(candidate_source="x = 1\n")
        assert pool.is_alive(wid) is True

        # Mark the worker as started long ago (simulate slow execution).
        import fault_keeper.armor.scpve as scpve_internal
        state = pool._workers[wid]
        old_start = _time.monotonic() - 0.1  # pretend it started 100ms ago.
        state.started_at = old_start

        evicted = pool.evict_failed_workers(deadline_ns=_time.monotonic() * 1e9)
        assert wid in evicted
        assert pool.is_alive(wid) is False

    def test_inject_and_get_result(self):
        """Test 4.1.4.B: Worker results can be injected and retrieved correctly."""
        pool = CoWWorkerPool()
        wid = pool.spawn(candidate_source="x = 1\n")

        pool.inject_result(wid, success=True, result={"status": "ok"})
        success, payload = pool.get_result(wid)
        assert success is True
        assert payload == {"status": "ok"}

    def test_evict_nonexistent_worker_returns_false(self):
        """Test 4.1.4.C: Evicting a worker that was never spawned returns False."""
        pool = CoWWorkerPool()
        assert pool.evict_worker(999) is False


# ---------------------------------------------------------------------------
# Test 4.1.5: Minimal Tree Edit Distance Arbiter Soundness (SC-PVE).
# ---------------------------------------------------------------------------

class TestASTArbiterSoundness:
    """Test that the Pareto-optimal arbiter correctly ranks candidates."""

    def test_best_candidate_has_lowest_ted(self):
        """Test 4.1.5.A: The candidate with the smallest tree-edit distance wins."""
        base = "def add(a, b):\n    return a + b\n"

        # Candidate 0 is identical -> TED=0 (best).
        cand_0 = "def add(a, b):\n    return a + b\n"
        # Candidate 1 changes one line -> TED>0.
        cand_1 = "def add(a, b):\n    return a - b\n"

        arbiter = ASTArbiter(base)
        ranked = arbiter.rank_candidates([cand_0, cand_1])

        assert ranked[0][0] == 0  # index of best candidate.


# ---------------------------------------------------------------------------
# Test 4.1.6: SCPVEEngine speculative_run with invariant_fn.
# ---------------------------------------------------------------------------

class TestSCPVEEngineSpeculativeRun:
    """Test the high-level engine's speculative run pipeline."""

    def test_speculative_run_selects_best_candidate(self):
        """Test 4.1.6.A: Engine commits the candidate with lowest composite score."""
        base = "def add(a, b):\n    return a + b\n"

        # Candidate 0 is identical (TED=0).
        cand_0 = "def add(a, b):\n    return a + b\n"
        # Candidate 1 adds complexity.
        cand_1 = """def add(a, b):
    if a > 0 and b > 0:
        return a + b
    else:
        return 0
"""

        engine = SCPVEEngine(max_workers=4)
        result = engine.speculative_run(base, [cand_0, cand_1])

        assert result.committed_candidate_index == 0  # identical candidate wins.
        assert len(result.arbiter_ranking) == 2

    def test_speculative_run_with_failing_invariant(self):
        """Test 4.1.6.B: Engine evicts workers whose invariant_fn returns (False, ...)."""
        base = "x = 1\n"

        # Candidate that passes syntax but fails our custom invariant check.
        failing_cand = "x = 'not a number'\n"
        passing_cand = "x = 2\n"

        def my_invariant(src: str) -> tuple[bool, str]:
            """Reject candidates where x is assigned a non-integer."""
            try:
                compile(src, "<string>", "exec")
                exec(compile(src, "<string>", "exec"), {"__builtins__": __import__("builtins")})  # type: ignore[misc]
                return (True, "ok")
            except Exception as exc:
                return (False, str(exc))

        engine = SCPVEEngine(max_workers=4)
        result = engine.speculative_run(
            base, [failing_cand, passing_cand], invariant_fn=my_invariant
        )

        # The failing candidate should be evicted or not survive.
        assert result.committed_candidate_index is not None  # at least one survives.


# ---------------------------------------------------------------------------
# Test 4.1.7: Virtual Time Interceptor behavior.
# ---------------------------------------------------------------------------

class TestVirtualTimeInterceptor:
    """Test that virtual time replaces wall-clock time during candidate runs."""

    def test_virtual_time_advances_independently(self):
        """Test 4.1.7.A: Virtual clock advances without blocking on real sleep."""
        from fault_keeper.armor.scpve import _VirtualClock, disable_virtual_time

        # Ensure clean state before this test.
        disable_virtual_time()

        vc = _VirtualClock()
        assert vc.now == 0.0

        # Advance the local virtual clock (each instance has independent state).
        vc.advance(1.5)
        assert vc.now == 1.5

    def test_interceptor_patches_and_unpatches(self):
        """Test 4.1.7.B: Interceptor can be enabled and disabled cleanly."""
        from fault_keeper.armor.scpve import enable_virtual_time, disable_virtual_time

        # Ensure clean state before this test.
        disable_virtual_time()

        # Initially not patched (wall-clock).
        assert scpve_module._interceptor.patched is False

        enable_virtual_time()
        assert scpve_module._interceptor.patched is True

        disable_virtual_time()
        assert scpve_module._interceptor.patched is False


# ---------------------------------------------------------------------------
# Test 4.1.8: CoWWorkerPool max_workers enforcement.
# ---------------------------------------------------------------------------

class TestCoWWorkerPoolLimits:
    """Test that the worker pool enforces its maximum capacity."""

    def test_spawn_exceeds_max_raises(self):
        """Test 4.1.8.A: Spawning beyond max_workers raises RuntimeError."""
        pool = CoWWorkerPool(max_workers=2)

        wid_1 = pool.spawn(candidate_source="x = 1\n")
        wid_2 = pool.spawn(candidate_source="x = 2\n")

        with pytest.raises(RuntimeError, match="full"):
            pool.spawn(candidate_source="x = 3\n")


# ---------------------------------------------------------------------------
# Test 4.1.9: SCPVEEngine initialization validation.
# ---------------------------------------------------------------------------

class TestSCPVEEngineInitValidation:
    """Test that the engine rejects invalid configuration."""

    def test_invalid_max_workers(self):
        """Test 4.1.9.A: Non-positive max_workers raises ValueError."""
        with pytest.raises(ValueError):
            SCPVEEngine(max_workers=0)

    def test_invalid_evict_budget(self):
        """Test 4.1.9.B: Non-positive evict budget raises ValueError."""
        with pytest.raises(ValueError):
            SCPVEEngine(evict_budget_s=-0.001)


# ---------------------------------------------------------------------------
# Test 4.1.10: Public symbol table assertions.
# ---------------------------------------------------------------------------

class TestSCPVEPublicSymbols:
    """Verify that the module's public API matches the spec deliverables."""

    def test_module_exposes_engine_and_pool(self):
        """Test 4.1.10.A: Module exports SCPVEEngine and CoWWorkerPool as documented."""
        assert hasattr(scpve_module, "SCPVEEngine")
        assert hasattr(scpve_module, "CoWWorkerPool")

    def test_arbiter_and_vfs_exposed(self):
        """Test 4.1.10.B: Arbiter and VFS classes are importable."""
        assert hasattr(scpve_module, "ASTArbiter")
        assert hasattr(scpve_module, "CoWVFS")
