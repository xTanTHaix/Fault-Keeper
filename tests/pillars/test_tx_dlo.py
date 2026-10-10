"""Tx-DLO: Transaction Deadlock & Lock-Ordering Strict Oracle — 1:1 Invariant Tests.

Verifies:
- Test 2.4.1: Wait-For Directed Graph Acyclicity (H_1(WFG) == 0 via Tarjan's SCC)
- Test 2.4.2: Havender Total Lock Ordering Verification (<_lock, Pr(Deadlock) == 0.0)
- Test 2.4.3: Dynamic Primary Key Sorting Latency Overhead (500 keys in <= 0.05ms)
- High-Concurrency Transfer Torture Test & Lock Contention Entropy H_contention.
"""

from __future__ import annotations

import math
import os
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from fault_keeper.daily.txdlo import (
    LockResource,
    TransactionDeadlockOracle,
    TransactionFlow,
    benchmark_batch_key_normalizer,
    build_wait_for_graph,
    compute_lock_contention_entropy,
    normalize_batch_keys,
    slice_ast_transactions,
    verify_havender_lock_ordering,
)


# ---------------------------------------------------------------------------
# Test 2.4.1 — Wait-For Directed Graph Acyclicity (H_1(WFG) == 0)
# ---------------------------------------------------------------------------

def test_2_4_1_wait_for_graph_detects_two_transaction_cycle() -> None:
    """Tarjan's SCC detects cycle C = {T_1, T_2} when T_1 locks A->B and T_2 locks B->A."""
    t1 = TransactionFlow(
        tx_id="T_1",
        locks=[
            LockResource(table="accounts", primary_key=1, table_rank=1),
            LockResource(table="accounts", primary_key=2, table_rank=1),
        ],
    )
    t2 = TransactionFlow(
        tx_id="T_2",
        locks=[
            LockResource(table="accounts", primary_key=2, table_rank=1),
            LockResource(table="accounts", primary_key=1, table_rank=1),
        ],
    )

    report = build_wait_for_graph([t1, t2])
    assert report.is_deadlock_free is False
    assert report.h1_betti_number >= 1
    assert len(report.cycles) == 1
    assert set(report.cycles[0]) == {"T_1", "T_2"}


def test_2_4_1_wait_for_graph_detects_three_way_ring_and_validates_dag() -> None:
    """Tarjan's SCC isolates 3-node deadlock ring T_1 -> T_2 -> T_3 -> T_1 and confirms H_1 == 0 on DAGs."""
    r_a = LockResource(table="orders", primary_key=10, table_rank=1)
    r_b = LockResource(table="inventory", primary_key=20, table_rank=2)
    r_c = LockResource(table="ledgers", primary_key=30, table_rank=3)

    ring_flows = [
        TransactionFlow(tx_id="T_1", locks=[r_a, r_b]),
        TransactionFlow(tx_id="T_2", locks=[r_b, r_c]),
        TransactionFlow(tx_id="T_3", locks=[r_c, r_a]),
    ]
    ring_wfg = build_wait_for_graph(ring_flows)
    assert ring_wfg.is_deadlock_free is False
    assert ring_wfg.h1_betti_number >= 1
    assert len(ring_wfg.cycles) == 1
    assert set(ring_wfg.cycles[0]) == {"T_1", "T_2", "T_3"}

    # Canonical DAG ordering: all transactions lock r_a -> r_b -> r_c
    dag_flows = [
        TransactionFlow(tx_id="T_1", locks=[r_a, r_b, r_c]),
        TransactionFlow(tx_id="T_2", locks=[r_a, r_b, r_c]),
        TransactionFlow(tx_id="T_3", locks=[r_b, r_c]),
    ]
    dag_wfg = build_wait_for_graph(dag_flows)
    assert dag_wfg.is_deadlock_free is True
    assert dag_wfg.h1_betti_number == 0
    assert dag_wfg.cycles == []


# ---------------------------------------------------------------------------
# Test 2.4.2 — Havender Total Lock Ordering Verification (<_lock)
# ---------------------------------------------------------------------------

def test_2_4_2_havender_total_lock_ordering_and_ast_slicing() -> None:
    """AST slicer extracts locks across tables/keys and Canonical Key Sorter enforces <_lock with Pr(Deadlock) == 0.0."""
    source = '''
def transfer_alpha(tx):
    tx.acquire_lock("wallets", 200)
    tx.acquire_lock("accounts", 100)

def transfer_beta(tx):
    tx.execute("SELECT * FROM accounts WHERE id = 50 FOR UPDATE")
    tx.execute("UPDATE accounts SET balance = 0 WHERE id = 10")
'''
    table_ranks = {"accounts": 1, "wallets": 2}
    oracle = TransactionDeadlockOracle(table_ranks=table_ranks)
    analysis = oracle.analyze_source(source, file_path="payments/service.py")

    ordering = analysis["ordering"]
    assert ordering.is_canonical is False
    assert len(ordering.violations) == 2
    assert ordering.deadlock_probability == 0.0
    assert "def transfer_alpha(tx):" in ordering.reordered_patch

    # Check that canonical schedule strictly obeys Havender's <_lock relation
    for tx_id, sched in ordering.canonical_schedule.items():
        for i in range(len(sched) - 1):
            assert sched[i] < sched[i + 1], f"Out-of-order lock in {tx_id}"

    # Verify canonicalized flows yield H_1(WFG) == 0
    canonical_flows = [
        TransactionFlow(tx_id=k, locks=v)
        for k, v in ordering.canonical_schedule.items()
    ]
    wfg_post = build_wait_for_graph(canonical_flows)
    assert wfg_post.is_deadlock_free is True
    assert wfg_post.h1_betti_number == 0


# ---------------------------------------------------------------------------
# Test 2.4.3 — Dynamic Primary Key Sorting Latency Overhead
# ---------------------------------------------------------------------------

def test_2_4_3_dynamic_primary_key_sorting_500_keys_under_0_05ms() -> None:
    """Sorting 500 unsorted primary keys in RAM completes in <= 0.05ms with exact deduplication."""
    rng = random.Random(2026)
    unsorted_keys = [rng.randint(-5000, 5000) for _ in range(500)]

    # Measure best of 5 in-memory runs to eliminate OS thread-scheduling jitter
    reports = [
        benchmark_batch_key_normalizer(unsorted_keys, budget_ms=0.05)
        for _ in range(5)
    ]
    best_report = min(reports, key=lambda r: r.latency_ms)

    assert best_report.original_count == 500
    assert best_report.sorted_keys == sorted(set(unsorted_keys))
    assert best_report.latency_ms <= 0.05, (
        f"Expected <= 0.05ms, got {best_report.latency_ms:.5f}ms"
    )
    assert best_report.within_budget is True

    # Edge cases: empty list and heterogeneous keys
    assert normalize_batch_keys([]) == []
    mixed = normalize_batch_keys(["user_b", 10, "user_a", 2, 10])
    assert mixed == [2, 10, "user_a", "user_b"]


# ---------------------------------------------------------------------------
# High-Concurrency Transfer Torture Test & Contention Entropy
# ---------------------------------------------------------------------------

def test_high_concurrency_havender_transfer_torture_zero_deadlock() -> None:
    """200 concurrent multi-account transfers using Havender canonical key sorting complete with 0 deadlocks and exact conservation of money."""
    account_ids = [101, 102, 103, 104, 105]
    locks: Dict[int, threading.Lock] = {aid: threading.Lock() for aid in account_ids}
    balances: Dict[int, int] = {aid: 10_000 for aid in account_ids}
    initial_total = sum(balances.values())

    def canonical_transfer(src_id: int, dst_id: int, amount: int) -> None:
        if src_id == dst_id:
            return
        # Havender canonical lock acquisition order via normalize_batch_keys
        first_key, second_key = normalize_batch_keys([src_id, dst_id])
        with locks[first_key]:
            with locks[second_key]:
                balances[src_id] -= amount
                balances[dst_id] += amount

    rng = random.Random(99)
    transfer_ops = [
        (rng.choice(account_ids), rng.choice(account_ids), rng.randint(1, 50))
        for _ in range(200)
    ]

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [
            pool.submit(canonical_transfer, s, d, amt)
            for s, d, amt in transfer_ops
        ]
        for fut in futures:
            fut.result(timeout=5.0)

    assert sum(balances.values()) == initial_total


def test_lock_contention_shannon_entropy_calculation() -> None:
    """Verifies H_contention = -sum p(r) log2 p(r) on uniform and skewed lock distributions."""
    # 4 resources acquired equally (2 times each => p = 0.25 => H = log2(4) = 2.0 bits)
    flows = [
        TransactionFlow(
            tx_id=f"tx_{i}",
            locks=[
                LockResource("t", 1),
                LockResource("t", 2),
                LockResource("t", 3),
                LockResource("t", 4),
            ],
        )
        for i in range(2)
    ]
    ent = compute_lock_contention_entropy(flows)
    assert ent.total_acquisitions == 8
    assert ent.h_contention == pytest.approx(math.log2(4), abs=1e-9)
    assert compute_lock_contention_entropy([]).h_contention == 0.0
