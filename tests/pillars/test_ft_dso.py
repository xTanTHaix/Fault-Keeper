"""FT-DSO: Flaky-Test Deterministic Sieve & Order-Independence Oracle — 1:1 Invariant Tests.

Verifies:
- Test 2.3.1: Permutation Order Invariance Proof (I_order: R(pi_a) == R(pi_b))
- Test 2.3.2: Gray Code Minimal Toxic Pair Sieve Optimality O(N log N) (<= 15 runs, <= 2.5s)
- Test 2.3.3: Global State Leakage Zero Invariant (Delta_leak == 0)
- Edge Cases: N=1 suite, non-reproducible failure, VirtualEventClockQuencher (< 5ms),
  and prescriptive @pytest.mark.quarantine patch emission.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import unittest.mock
from typing import Dict, Sequence

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from fault_keeper.daily.ftdso import (
    FlakyTestDeterministicSieve,
    VirtualEventClockQuencher,
    capture_state_snapshot,
    compute_state_leakage,
    emit_deflaking_patch,
    generate_gray_code_sequence,
    generate_permutation_schedules,
    gray_code,
    isolate_minimal_toxic_pair,
    run_with_leakage_sieve,
    verify_order_invariance,
)


# ---------------------------------------------------------------------------
# Test 2.3.1 — Permutation Order Invariance Proof (I_order)
# ---------------------------------------------------------------------------

def test_2_3_1_permutation_order_invariance_holds_for_clean_suite() -> None:
    """20 independent tests produce identical outcome vectors across all permutations."""
    test_ids = [f"test_case_{i}" for i in range(20)]

    def clean_runner(order: Sequence[str]) -> Dict[str, str]:
        return {tid: "PASS" for tid in order}

    report = verify_order_invariance(test_ids, clean_runner, seed=42)
    assert report.is_order_independent is True
    assert report.divergent_tests == []
    assert report.baseline_outcomes == report.reverse_outcomes
    assert report.baseline_outcomes == report.shuffled_outcomes


def test_2_3_1_permutation_invariance_detects_order_dependent_flakiness() -> None:
    """When t_15 pollutes state that breaks t_3 in reverse order, invariance fails and triggers Toxic Pair mode."""
    test_ids = [f"test_unit_{i}" for i in range(20)]

    def order_sensitive_runner(order: Sequence[str]) -> Dict[str, str]:
        polluted = False
        outcomes: Dict[str, str] = {}
        for tid in order:
            if tid == "test_unit_15":
                polluted = True
                outcomes[tid] = "PASS"
            elif tid == "test_unit_3":
                outcomes[tid] = "FAIL" if polluted else "PASS"
            else:
                outcomes[tid] = "PASS"
        return outcomes

    sieve = FlakyTestDeterministicSieve(seed=42)
    invariance = sieve.verify_invariance(test_ids, order_sensitive_runner)

    # Forward order runs test_unit_3 before test_unit_15 => PASS
    # Reverse order runs test_unit_15 before test_unit_3 => FAIL
    assert invariance.is_order_independent is False
    assert "test_unit_3" in invariance.divergent_tests
    assert invariance.baseline_outcomes["test_unit_3"] == "PASS"
    assert invariance.reverse_outcomes["test_unit_3"] == "FAIL"

    # Full audit automatically switches to Toxic Pair isolation
    audit = sieve.audit_suite(
        test_ids,
        order_sensitive_runner,
        source_code="def test_unit_3():\n    assert True\n",
    )
    assert len(audit.toxic_pairs) == 1
    assert audit.toxic_pairs[0].polluter == "test_unit_15"
    assert audit.toxic_pairs[0].victim == "test_unit_3"
    assert audit.toxic_pairs[0].reproducible is True


# ---------------------------------------------------------------------------
# Test 2.3.2 — Gray Code Minimal Toxic Pair Sieve Optimality O(N log N)
# ---------------------------------------------------------------------------

def test_2_3_2_gray_code_minimal_toxic_pair_sieve_1000_tests() -> None:
    """In a 1,000-test suite where t_42 pollutes t_888, binary slicing isolates <t_42, t_888> in <= 15 runs and <= 2.5s."""
    test_ids = [f"t_{i}" for i in range(1000)]

    def thousand_test_runner(order: Sequence[str]) -> Dict[str, str]:
        dirty_singleton = False
        results: Dict[str, str] = {}
        for tid in order:
            if tid == "t_42":
                dirty_singleton = True
                results[tid] = "PASS"
            elif tid == "t_888":
                results[tid] = "FAIL" if dirty_singleton else "PASS"
            else:
                results[tid] = "PASS"
        return results

    report = isolate_minimal_toxic_pair(
        test_ids=test_ids,
        runner=thousand_test_runner,
        victim_id="t_888",
        failing_order=test_ids,
    )

    assert report.reproducible is True
    assert report.polluter == "t_42"
    assert report.victim == "t_888"
    assert report.runs_executed <= 15
    assert report.elapsed_ms <= 2500.0
    assert len(report.gray_code_trace) >= 1

    # Verify adjacent elements in the Gray code sequence have Hamming distance == 1
    seq = generate_gray_code_sequence(4)
    assert len(seq) == 16
    for idx in range(len(seq) - 1):
        xor_val = seq[idx] ^ seq[idx + 1]
        assert bin(xor_val).count("1") == 1


# ---------------------------------------------------------------------------
# Test 2.3.3 — Global State Leakage Zero Invariant (Delta_leak == 0)
# ---------------------------------------------------------------------------

class _GlobalConfigSingleton:
    cache_enabled: bool = True

    def __init__(self) -> None:
        self.cache_enabled = True
        self.active_tenant: str = "default"


def test_2_3_3_global_state_leakage_sieve_detects_singleton_env_and_mock() -> None:
    """Detects mutated global singletons, leaked environment variables, and un-reset mocks with 100% precision."""
    singleton = _GlobalConfigSingleton()
    tracked_globals = {"AUTH_SINGLETON": singleton}
    env_key = "FT_DSO_TEST_LEAK_VAR"
    os.environ.pop(env_key, None)

    def leaky_test_case() -> None:
        # 1. Mutate global singleton without restoring
        singleton.active_tenant = "polluted_tenant"
        # 2. Mutate environment variable without cleanup
        os.environ[env_key] = "dirty_value"
        # 3. Start a unittest.mock.patch without calling .stop()
        patcher = unittest.mock.patch.object(
            _GlobalConfigSingleton, "cache_enabled", False
        )
        patcher.start()

    try:
        report = run_with_leakage_sieve(
            test_id="test_leaky_singleton_and_mock",
            test_fn=leaky_test_case,
            target_namespaces=tracked_globals,
            auto_cleanup_mocks=True,
        )
    finally:
        os.environ.pop(env_key, None)
        singleton.active_tenant = "default"
        unittest.mock.patch.stopall()

    assert report.delta_leak > 0
    assert report.is_clean is False
    assert "AUTH_SINGLETON" in report.leaked_globals
    assert env_key in report.leaked_env_vars
    assert len(report.unreset_mocks) >= 1


def test_2_3_3_global_state_leakage_zero_for_well_behaved_test() -> None:
    """A test that properly restores all state satisfies Delta_leak == 0."""
    singleton = _GlobalConfigSingleton()
    tracked_globals = {"AUTH_SINGLETON": singleton}

    def clean_test_case() -> None:
        prev = singleton.active_tenant
        singleton.active_tenant = "temporary"
        singleton.active_tenant = prev

    report = run_with_leakage_sieve(
        test_id="test_clean_state",
        test_fn=clean_test_case,
        target_namespaces=tracked_globals,
    )
    assert report.delta_leak == 0
    assert report.is_clean is True
    assert report.leaked_globals == []
    assert report.leaked_env_vars == []
    assert report.unreset_mocks == []


# ---------------------------------------------------------------------------
# Edge Cases & Virtual Event-Clock Quenching
# ---------------------------------------------------------------------------

def test_virtual_event_clock_quencher_eliminates_sleep_delay() -> None:
    """Multi-second time.sleep and asyncio.sleep execute in < 10ms via virtual event-clock quenching."""
    with VirtualEventClockQuencher(initial_epoch=1_000.0) as quencher:
        t0 = time.time()
        time.sleep(5.0)
        time.sleep(2.5)
        asyncio.run(asyncio.sleep(12.5))
        t1 = time.time()

    report = quencher.build_report(
        source_code="import time\ndef slow_test():\n    time.sleep(5.0)\n"
    )
    assert (t1 - t0) == pytest.approx(20.0, abs=1e-6)
    assert report.virtual_elapsed_sec == pytest.approx(20.0, abs=1e-6)
    assert report.wall_clock_ms < 50.0
    assert len(report.intercepted_calls) == 3
    assert len(report.ast_sleep_callsites) == 1
    assert report.ast_sleep_callsites[0]["call"] == "time.sleep"
    assert report.ast_sleep_callsites[0]["lineno"] == 3


def test_edge_cases_single_test_and_deflaking_patch_emitter() -> None:
    """Single-test suites and prescriptive quarantine patch emitter behave deterministically."""
    sched = generate_permutation_schedules(["only_test"])
    assert sched.forward == ("only_test",)
    assert sched.reverse == ("only_test",)
    assert sched.shuffled == ("only_test",)

    tp_single = isolate_minimal_toxic_pair(
        ["only_test"], lambda seq: {"only_test": "PASS"}
    )
    assert tp_single.reproducible is False
    assert tp_single.polluter is None

    # Non-reproducible failure where victim passes even when paired
    tp_non_repro = isolate_minimal_toxic_pair(
        ["t1", "t2", "t3"],
        lambda seq: {t: "PASS" for t in seq},
        victim_id="t3",
    )
    assert tp_non_repro.reproducible is False

    # Prescriptive patch emission
    pre = capture_state_snapshot({"GLOB": 1})
    post = capture_state_snapshot({"GLOB": 2})
    leak = compute_state_leakage("test_victim", pre, post)
    patch = emit_deflaking_patch(
        source_code="def test_victim():\n    assert True\n",
        test_id="test_victim",
        leakage=leak,
        polluter_id="test_polluter",
    )
    assert "@pytest.mark.quarantine" in patch.patched_source
    assert "test_polluter" in patch.quarantine_decorator
    assert len(patch.reset_statements) == 1
