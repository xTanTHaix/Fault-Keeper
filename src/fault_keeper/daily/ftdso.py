"""FT-DSO: Flaky-Test Deterministic Sieve & Order-Independence Oracle.

Eliminates order-dependent test flakiness, global state pollution, and async
timing jitter using four mathematical pillars:
1. Permutation Order-Invariance Oracle: R(pi_a) == R(pi_b) across forward,
   reverse (pi_rev), and seeded Fisher-Yates shuffle (pi_shuf) schedules.
2. Gray Code Minimal Toxic Pair Sieve: O(N log N) binary search over a
   reflected binary Gray code permutation lattice to isolate <t_polluter, t_victim>.
3. Global State Leakage Sieve: Delta_leak(t_k) = ||sigma_post(t_k) - sigma_pre(t_k)|| == 0
   across environment variables, sys.modules, global singletons, and unittest.mock patches.
4. Deterministic Virtual Discrete Event-Clock Quencher: Intercepts sleep and wall-clock
   calls to advance virtual time deterministically in < 1ms.
"""

from __future__ import annotations

import ast
import asyncio
import os
import random
import sys
import threading
import time
import unittest.mock
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PermutationSchedule:
    """Deterministic test permutation schedules for order-invariance checking."""

    forward: Tuple[str, ...]
    reverse: Tuple[str, ...]
    shuffled: Tuple[str, ...]
    seed: int = 42

    def to_dict(self) -> Dict[str, Any]:
        """Serialize schedule to a JSON-compatible dictionary."""
        return {
            "forward": list(self.forward),
            "reverse": list(self.reverse),
            "shuffled": list(self.shuffled),
            "seed": self.seed,
        }


@dataclass
class OrderInvarianceReport:
    """Result of verifying test outcome invariance across permutations."""

    is_order_independent: bool
    baseline_outcomes: Dict[str, str]
    reverse_outcomes: Dict[str, str]
    shuffled_outcomes: Dict[str, str]
    divergent_tests: List[str] = field(default_factory=list)
    failing_schedule_name: Optional[str] = None
    failing_order: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize invariance report to a dictionary."""
        return {
            "is_order_independent": self.is_order_independent,
            "baseline_outcomes": dict(self.baseline_outcomes),
            "reverse_outcomes": dict(self.reverse_outcomes),
            "shuffled_outcomes": dict(self.shuffled_outcomes),
            "divergent_tests": list(self.divergent_tests),
            "failing_schedule_name": self.failing_schedule_name,
            "failing_order": list(self.failing_order),
        }


@dataclass
class ToxicPairReport:
    """Result of Gray Code Binary Search Slicing for a minimal toxic pair."""

    polluter: Optional[str]
    victim: Optional[str]
    runs_executed: int
    elapsed_ms: float
    gray_code_trace: List[int] = field(default_factory=list)
    reproducible: bool = False
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize toxic pair isolation report to a dictionary."""
        return {
            "polluter": self.polluter,
            "victim": self.victim,
            "runs_executed": self.runs_executed,
            "elapsed_ms": round(self.elapsed_ms, 4),
            "gray_code_trace": list(self.gray_code_trace),
            "reproducible": self.reproducible,
            "reason": self.reason,
        }


@dataclass
class StateSnapshot:
    """Point-in-time snapshot of the process and module state lattice sigma."""

    env_vars: Dict[str, str]
    module_keys: Set[str]
    global_vars: Dict[str, str]
    active_patches: List[str]
    thread_count: int


@dataclass
class StateLeakageReport:
    """Result of evaluating Delta_leak(t_k) = ||sigma_post - sigma_pre||."""

    test_id: str
    delta_leak: int
    is_clean: bool
    leaked_env_vars: List[str] = field(default_factory=list)
    leaked_globals: List[str] = field(default_factory=list)
    leaked_modules: List[str] = field(default_factory=list)
    unreset_mocks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state leakage report to a dictionary."""
        return {
            "test_id": self.test_id,
            "delta_leak": self.delta_leak,
            "is_clean": self.is_clean,
            "leaked_env_vars": list(self.leaked_env_vars),
            "leaked_globals": list(self.leaked_globals),
            "leaked_modules": list(self.leaked_modules),
            "unreset_mocks": list(self.unreset_mocks),
        }


@dataclass
class VirtualClockQuenchReport:
    """Metrics from quenching physical sleep/time calls into discrete ticks."""

    virtual_elapsed_sec: float
    wall_clock_ms: float
    intercepted_calls: List[Dict[str, Any]] = field(default_factory=list)
    ast_sleep_callsites: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize virtual clock quench report to a dictionary."""
        return {
            "virtual_elapsed_sec": round(self.virtual_elapsed_sec, 6),
            "wall_clock_ms": round(self.wall_clock_ms, 4),
            "intercepted_calls": list(self.intercepted_calls),
            "ast_sleep_callsites": list(self.ast_sleep_callsites),
        }


@dataclass
class DeflakingPatch:
    """Prescriptive remediation patch and quarantine marker for a flaky test."""

    test_id: str
    polluter_id: Optional[str]
    quarantine_decorator: str
    reset_statements: List[str]
    patched_source: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize de-flaking patch to a dictionary."""
        return {
            "test_id": self.test_id,
            "polluter_id": self.polluter_id,
            "quarantine_decorator": self.quarantine_decorator,
            "reset_statements": list(self.reset_statements),
            "patched_source": self.patched_source,
        }


@dataclass
class FTDSOAuditReport:
    """Comprehensive audit report produced by the FT-DSO engine."""

    order_invariance: OrderInvarianceReport
    toxic_pairs: List[ToxicPairReport]
    leakage_reports: List[StateLeakageReport]
    clock_quench: VirtualClockQuenchReport
    patches: List[DeflakingPatch]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize full FT-DSO report to a dictionary."""
        return {
            "order_invariance": self.order_invariance.to_dict(),
            "toxic_pairs": [tp.to_dict() for tp in self.toxic_pairs],
            "leakage_reports": [lr.to_dict() for lr in self.leakage_reports],
            "clock_quench": self.clock_quench.to_dict(),
            "patches": [p.to_dict() for p in self.patches],
        }


# ---------------------------------------------------------------------------
# 1. Permutation Schedule Generator & Order-Invariance Oracle
# ---------------------------------------------------------------------------

def generate_permutation_schedules(
    test_ids: Sequence[str],
    seed: int = 42,
) -> PermutationSchedule:
    """Generate forward, reverse, and deterministic shuffled test schedules.

    Ensures that for N > 1, the shuffled schedule differs from both forward and
    reverse orders when possible so hidden state coupling is maximally exposed.

    Args:
        test_ids: Ordered sequence of unique test identifiers.
        seed: Deterministic PRNG seed for reproducible shuffling.

    Returns:
        A PermutationSchedule instance containing pi_fwd, pi_rev, and pi_shuf.
    """
    forward = tuple(test_ids)
    reverse = tuple(reversed(forward))
    if len(forward) <= 1:
        return PermutationSchedule(
            forward=forward,
            reverse=reverse,
            shuffled=forward,
            seed=seed,
        )

    rng = random.Random(seed)
    shuffled_list = list(forward)
    rng.shuffle(shuffled_list)

    # If the PRNG happened to produce an identical permutation on small N,
    # rotate by one position to guarantee an distinct interleaved probe.
    if tuple(shuffled_list) == forward and len(shuffled_list) > 1:
        shuffled_list = shuffled_list[1:] + shuffled_list[:1]

    return PermutationSchedule(
        forward=forward,
        reverse=reverse,
        shuffled=tuple(shuffled_list),
        seed=seed,
    )


def verify_order_invariance(
    test_ids: Sequence[str],
    runner: Callable[[Sequence[str]], Mapping[str, str]],
    seed: int = 42,
) -> OrderInvarianceReport:
    """Verify the Order-Independence Invariant R(pi_a) == R(pi_b).

    Executes the test suite under forward (pi_fwd), reverse (pi_rev), and
    shuffled (pi_shuf) permutations. Any discrepancy in per-test outcomes
    violates the invariance condition and triggers Toxic Pair Isolation mode.

    Args:
        test_ids: Ordered list of test identifiers.
        runner: Callable accepting a test sequence and returning a mapping of
            test_id -> outcome string ("PASS", "FAIL", "ERROR").
        seed: Random seed for the deterministic shuffle schedule.

    Returns:
        OrderInvarianceReport detailing outcome vectors and divergent tests.
    """
    schedule = generate_permutation_schedules(test_ids, seed=seed)
    if not schedule.forward:
        return OrderInvarianceReport(
            is_order_independent=True,
            baseline_outcomes={},
            reverse_outcomes={},
            shuffled_outcomes={},
        )

    baseline = dict(runner(schedule.forward))
    if len(schedule.forward) == 1:
        return OrderInvarianceReport(
            is_order_independent=True,
            baseline_outcomes=baseline,
            reverse_outcomes=dict(baseline),
            shuffled_outcomes=dict(baseline),
        )

    rev_outcomes = dict(runner(schedule.reverse))
    shuf_outcomes = dict(runner(schedule.shuffled))

    divergent: List[str] = []
    failing_schedule_name: Optional[str] = None
    failing_order: List[str] = []

    for tid in schedule.forward:
        b_res = baseline.get(tid, "PASS")
        r_res = rev_outcomes.get(tid, "PASS")
        s_res = shuf_outcomes.get(tid, "PASS")
        if not (b_res == r_res == s_res):
            divergent.append(tid)

    if divergent:
        # Select the schedule that exhibits the failure for the divergent victim
        first_div = divergent[0]
        if rev_outcomes.get(first_div) != "PASS":
            failing_schedule_name = "reverse"
            failing_order = list(schedule.reverse)
        elif shuf_outcomes.get(first_div) != "PASS":
            failing_schedule_name = "shuffled"
            failing_order = list(schedule.shuffled)
        else:
            failing_schedule_name = "forward"
            failing_order = list(schedule.forward)

    return OrderInvarianceReport(
        is_order_independent=(len(divergent) == 0),
        baseline_outcomes=baseline,
        reverse_outcomes=rev_outcomes,
        shuffled_outcomes=shuf_outcomes,
        divergent_tests=divergent,
        failing_schedule_name=failing_schedule_name,
        failing_order=failing_order,
    )


# ---------------------------------------------------------------------------
# 2. Gray Code Minimal Toxic Pair Sieve O(N log N)
# ---------------------------------------------------------------------------

def gray_code(n: int) -> int:
    """Compute the n-th reflected binary Gray code G(n) = n ^ (n >> 1).

    Adjacent Gray code integers differ by a Hamming distance of 1 bit,
    enabling minimal-perturbation traversal across binary partition lattices.

    Args:
        n: Non-negative integer index.

    Returns:
        Reflected binary Gray code integer.
    """
    if n < 0:
        raise ValueError(f"Gray code index must be non-negative, got {n}")
    return n ^ (n >> 1)


def generate_gray_code_sequence(bits: int) -> List[int]:
    """Generate the full reflected binary Gray code sequence of length 2^bits.

    Args:
        bits: Number of bits in the lattice dimension (0 <= bits <= 20).

    Returns:
        List of 2^bits integers where successive elements differ by 1 bit.
    """
    if bits < 0 or bits > 20:
        raise ValueError(f"bits must be between 0 and 20, got {bits}")
    return [gray_code(i) for i in range(1 << bits)]


def isolate_minimal_toxic_pair(
    test_ids: Sequence[str],
    runner: Callable[[Sequence[str]], Mapping[str, str]],
    victim_id: Optional[str] = None,
    failing_order: Optional[Sequence[str]] = None,
) -> ToxicPairReport:
    """Isolate the minimal toxic pair <t_polluter, t_victim> in O(N log N).

    Slices the candidate prefix preceding the victim test using binary bisection
    indexed along a reflected binary Gray code trace. For N = 1,000 tests, the
    polluter is isolated in ceil(log2(N)) + 2 <= 12 test executions.

    Args:
        test_ids: Full sequence of test identifiers in the suite.
        runner: Callable executing an ordered subset of test IDs and returning
            a dictionary mapping each executed test ID to "PASS" or "FAIL".
        victim_id: Optional known victim test ID. If omitted, discovered via
            forward/reverse/shuffled probing.
        failing_order: Optional permutation in which victim_id fails.

    Returns:
        ToxicPairReport identifying the exact polluter, victim, run count,
        wall-clock duration in milliseconds, and Gray code bisection trace.
    """
    start_ns = time.perf_counter_ns()
    runs_executed = 0
    gray_trace: List[int] = []

    if len(test_ids) <= 1:
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        return ToxicPairReport(
            polluter=None,
            victim=None,
            runs_executed=0,
            elapsed_ms=elapsed_ms,
            gray_code_trace=[],
            reproducible=False,
            reason="Suite contains fewer than 2 tests; order pollution impossible.",
        )

    active_order = list(failing_order) if failing_order is not None else list(test_ids)
    target_victim = victim_id

    # Step 1: Discover failing order and victim if not provided by caller
    if target_victim is None:
        fwd_res = dict(runner(active_order))
        runs_executed += 1
        failed_in_fwd = [t for t in active_order if fwd_res.get(t, "PASS") != "PASS"]
        if failed_in_fwd:
            target_victim = failed_in_fwd[0]
        else:
            rev_order = list(reversed(active_order))
            rev_res = dict(runner(rev_order))
            runs_executed += 1
            failed_in_rev = [t for t in rev_order if rev_res.get(t, "PASS") != "PASS"]
            if failed_in_rev:
                active_order = rev_order
                target_victim = failed_in_rev[0]

    if target_victim is None or target_victim not in active_order:
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        return ToxicPairReport(
            polluter=None,
            victim=target_victim,
            runs_executed=runs_executed,
            elapsed_ms=elapsed_ms,
            gray_code_trace=gray_trace,
            reproducible=False,
            reason="No failing victim test observed across schedules.",
        )

    # Step 2: Extract candidate prefix preceding target_victim in active_order
    victim_idx = active_order.index(target_victim)
    candidates = active_order[:victim_idx]
    if not candidates:
        # If target_victim is at index 0 of active_order, all other tests are candidates
        candidates = [t for t in active_order if t != target_victim]

    # Step 3: Binary search over the candidate prefix using Gray code step indexing
    step_idx = 1
    while len(candidates) > 1:
        g_code = gray_code(step_idx)
        gray_trace.append(g_code)
        step_idx += 1

        mid = len(candidates) // 2
        lower_half = candidates[:mid]
        upper_half = candidates[mid:]

        # Probe lower half + victim
        probe_seq = list(lower_half) + [target_victim]
        probe_res = runner(probe_seq)
        runs_executed += 1

        if probe_res.get(target_victim, "PASS") != "PASS":
            candidates = lower_half
        else:
            candidates = upper_half

    # Step 4: Verify the isolated single candidate polluter + victim pair
    candidate_polluter = candidates[0]
    verify_res = runner([candidate_polluter, target_victim])
    runs_executed += 1
    gray_trace.append(gray_code(step_idx))

    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
    if verify_res.get(target_victim, "PASS") != "PASS":
        return ToxicPairReport(
            polluter=candidate_polluter,
            victim=target_victim,
            runs_executed=runs_executed,
            elapsed_ms=elapsed_ms,
            gray_code_trace=gray_trace,
            reproducible=True,
            reason=f"Confirmed minimal toxic pair <{candidate_polluter}, {target_victim}>.",
        )

    return ToxicPairReport(
        polluter=None,
        victim=target_victim,
        runs_executed=runs_executed,
        elapsed_ms=elapsed_ms,
        gray_code_trace=gray_trace,
        reproducible=False,
        reason="Non-reproducible state pollution or multi-test interaction.",
    )


# ---------------------------------------------------------------------------
# 3. Global State Leakage Sieve (Delta_leak == 0)
# ---------------------------------------------------------------------------

def _serialize_state_value(
    val: Any,
    visited: Optional[set] = None,
    max_depth: int = 5,
) -> str:
    """Create a deterministic string fingerprint for a global/singleton object with cycle protection."""
    if visited is None:
        visited = set()

    if isinstance(val, (int, float, str, bool, bytes, type(None))):
        return f"{type(val).__qualname__}:{repr(val)}"

    val_id = id(val)
    if val_id in visited or max_depth <= 0:
        return f"{type(val).__qualname__}:<cycle_or_depth_limit>"
    visited.add(val_id)

    try:
        if isinstance(val, (list, tuple, set, frozenset)):
            items = ", ".join(_serialize_state_value(x, visited, max_depth - 1) for x in val)
            return f"{type(val).__qualname__}:[{items}]"
        if isinstance(val, dict):
            pairs = ", ".join(
                f"{repr(k)}:{_serialize_state_value(v, visited, max_depth - 1)}"
                for k, v in sorted(val.items(), key=lambda item: str(item[0]))
            )
            return f"dict:{{{pairs}}}"
        if hasattr(val, "__dict__"):
            attrs = {
                k: v
                for k, v in vars(val).items()
                if not k.startswith("__") and not callable(v)
            }
            if attrs:
                return f"{type(val).__qualname__}:{_serialize_state_value(attrs, visited, max_depth - 1)}"
        return f"{type(val).__qualname__}:{repr(val)}"
    finally:
        visited.remove(val_id)


def capture_state_snapshot(
    target_namespaces: Optional[Mapping[str, Any]] = None,
) -> StateSnapshot:
    """Capture a pre- or post-test snapshot of the global state lattice sigma.

    Inspects os.environ, sys.modules, active unittest.mock patches, thread count,
    and user-supplied global/singleton namespaces.

    Args:
        target_namespaces: Optional dictionary of global variables, singletons,
            or module dicts to track for mutation.

    Returns:
        StateSnapshot capturing the current state vector.
    """
    env_copy = dict(os.environ)
    mod_keys = set(sys.modules.keys())

    global_fingerprints: Dict[str, str] = {}
    if target_namespaces is not None:
        for name, obj in target_namespaces.items():
            if name.startswith("__"):
                continue
            global_fingerprints[name] = _serialize_state_value(obj)

    active_patches: List[str] = []
    raw_patches = getattr(unittest.mock._patch, "_active_patches", [])
    for p in list(raw_patches):
        target_desc = getattr(p, "attribute", None) or repr(p)
        getter = getattr(p, "getter", None)
        if callable(getter):
            try:
                target_obj = getter()
                target_name = getattr(
                    target_obj, "__name__", type(target_obj).__qualname__
                )
                target_desc = f"{target_name}.{target_desc}"
            except Exception:
                target_desc = str(target_desc)
        active_patches.append(str(target_desc))

    return StateSnapshot(
        env_vars=env_copy,
        module_keys=mod_keys,
        global_vars=global_fingerprints,
        active_patches=active_patches,
        thread_count=threading.active_count(),
    )


def compute_state_leakage(
    test_id: str,
    pre: StateSnapshot,
    post: StateSnapshot,
) -> StateLeakageReport:
    """Compute the state leakage norm Delta_leak(t_k) = ||sigma_post - sigma_pre||.

    Args:
        test_id: Identifier of the executed test.
        pre: StateSnapshot captured immediately prior to test execution.
        post: StateSnapshot captured immediately after test execution.

    Returns:
        StateLeakageReport enumerating every leaked environment variable,
        mutated global/singleton, newly imported module, and un-reset mock.
    """
    leaked_env: List[str] = []
    all_env_keys = set(pre.env_vars.keys()) | set(post.env_vars.keys())
    for k in sorted(all_env_keys):
        if pre.env_vars.get(k) != post.env_vars.get(k):
            leaked_env.append(k)

    leaked_globals: List[str] = []
    all_global_keys = set(pre.global_vars.keys()) | set(post.global_vars.keys())
    for k in sorted(all_global_keys):
        if pre.global_vars.get(k) != post.global_vars.get(k):
            leaked_globals.append(k)

    leaked_modules = sorted(post.module_keys - pre.module_keys)

    pre_patch_counts: Dict[str, int] = {}
    for p in pre.active_patches:
        pre_patch_counts[p] = pre_patch_counts.get(p, 0) + 1

    unreset_mocks: List[str] = []
    for p in post.active_patches:
        if pre_patch_counts.get(p, 0) > 0:
            pre_patch_counts[p] -= 1
        else:
            unreset_mocks.append(p)

    delta_leak = (
        len(leaked_env)
        + len(leaked_globals)
        + len(leaked_modules)
        + len(unreset_mocks)
    )

    return StateLeakageReport(
        test_id=test_id,
        delta_leak=delta_leak,
        is_clean=(delta_leak == 0),
        leaked_env_vars=leaked_env,
        leaked_globals=leaked_globals,
        leaked_modules=leaked_modules,
        unreset_mocks=unreset_mocks,
    )


def run_with_leakage_sieve(
    test_id: str,
    test_fn: Callable[[], Any],
    target_namespaces: Optional[Mapping[str, Any]] = None,
    auto_cleanup_mocks: bool = False,
) -> StateLeakageReport:
    """Execute a test callable while measuring global state leakage Delta_leak.

    Args:
        test_id: Identifier of the test being audited.
        test_fn: Zero-argument callable executing the test body.
        target_namespaces: Optional mapping of global symbols/singletons to watch.
        auto_cleanup_mocks: If True, stops leaked unittest.mock patches after
            recording the leakage report so subsequent tests remain isolated.

    Returns:
        StateLeakageReport with exact names of leaked globals, env vars, and mocks.
    """
    pre = capture_state_snapshot(target_namespaces)
    try:
        test_fn()
    finally:
        post = capture_state_snapshot(target_namespaces)
        if auto_cleanup_mocks and len(post.active_patches) > len(pre.active_patches):
            unittest.mock.patch.stopall()

    return compute_state_leakage(test_id, pre, post)


# ---------------------------------------------------------------------------
# 4. Deterministic Virtual Discrete Event-Clock Quencher
# ---------------------------------------------------------------------------

class VirtualEventClockQuencher:
    """Context manager and static scanner quenching physical sleep/time delays.

    Replaces physical wall-clock sleep (`time.sleep`, `asyncio.sleep`) and
    clock queries (`time.time`, `time.monotonic`) with a deterministic
    monotonically advancing virtual clock so multi-second delays execute in < 1ms.
    """

    def __init__(self, initial_epoch: float = 1_700_000_000.0) -> None:
        self._virtual_time: float = float(initial_epoch)
        self._initial_epoch: float = float(initial_epoch)
        self._intercepted_calls: List[Dict[str, Any]] = []
        self._orig_time_sleep = time.sleep
        self._orig_time_time = time.time
        self._orig_time_monotonic = time.monotonic
        self._orig_asyncio_sleep = asyncio.sleep
        self._start_wall_ns: int = 0
        self._wall_clock_ms: float = 0.0

    @property
    def virtual_time(self) -> float:
        """Return current virtual clock timestamp in seconds."""
        return self._virtual_time

    @property
    def virtual_elapsed_sec(self) -> float:
        """Return total virtual seconds advanced since quenching started."""
        return self._virtual_time - self._initial_epoch

    def _quenched_sleep(self, seconds: float) -> None:
        """Advance virtual time instantly without blocking the OS thread."""
        dt = max(0.0, float(seconds))
        self._virtual_time += dt
        self._intercepted_calls.append({"api": "time.sleep", "seconds": dt})

    async def _quenched_async_sleep(
        self, delay: float, result: Any = None
    ) -> Any:
        """Advance virtual time on async sleep and yield once to the event loop."""
        dt = max(0.0, float(delay))
        self._virtual_time += dt
        self._intercepted_calls.append({"api": "asyncio.sleep", "seconds": dt})
        await self._orig_asyncio_sleep(0)
        return result

    def _quenched_time(self) -> float:
        """Return current deterministic virtual epoch timestamp."""
        return self._virtual_time

    def _quenched_monotonic(self) -> float:
        """Return current deterministic virtual monotonic timestamp."""
        return self._virtual_time - self._initial_epoch

    def __enter__(self) -> "VirtualEventClockQuencher":
        """Install virtual event-clock hooks."""
        self._start_wall_ns = time.perf_counter_ns()
        time.sleep = self._quenched_sleep  # type: ignore[assignment]
        time.time = self._quenched_time  # type: ignore[assignment]
        time.monotonic = self._quenched_monotonic  # type: ignore[assignment]
        asyncio.sleep = self._quenched_async_sleep  # type: ignore[assignment]
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Restore physical wall-clock functions."""
        time.sleep = self._orig_time_sleep  # type: ignore[assignment]
        time.time = self._orig_time_time  # type: ignore[assignment]
        time.monotonic = self._orig_time_monotonic  # type: ignore[assignment]
        asyncio.sleep = self._orig_asyncio_sleep  # type: ignore[assignment]
        self._wall_clock_ms = (
            time.perf_counter_ns() - self._start_wall_ns
        ) / 1_000_000.0

    @staticmethod
    def scan_ast_timing_calls(source_code: str) -> List[Dict[str, Any]]:
        """Scan Python source AST for sleep and non-deterministic clock calls.

        Args:
            source_code: Python source string to inspect.

        Returns:
            List of dictionaries with function call name and line number.
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return []

        callsites: List[Dict[str, Any]] = []
        target_names = {"sleep", "setTimeout", "setInterval"}
        target_attrs = {
            ("time", "sleep"),
            ("time", "time"),
            ("asyncio", "sleep"),
            ("Date", "now"),
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                lineno = getattr(node, "lineno", 0)
                if isinstance(node.func, ast.Name) and node.func.id in target_names:
                    callsites.append({"call": node.func.id, "lineno": lineno})
                elif isinstance(node.func, ast.Attribute):
                    val = node.func.value
                    if isinstance(val, ast.Name):
                        pair = (val.id, node.func.attr)
                        if pair in target_attrs or node.func.attr in target_names:
                            callsites.append(
                                {
                                    "call": f"{val.id}.{node.func.attr}",
                                    "lineno": lineno,
                                }
                            )
        callsites.sort(key=lambda item: int(item["lineno"]))
        return callsites

    def build_report(self, source_code: str = "") -> VirtualClockQuenchReport:
        """Construct a VirtualClockQuenchReport from recorded interceptions."""
        ast_calls = (
            self.scan_ast_timing_calls(source_code) if source_code else []
        )
        return VirtualClockQuenchReport(
            virtual_elapsed_sec=self.virtual_elapsed_sec,
            wall_clock_ms=self._wall_clock_ms,
            intercepted_calls=list(self._intercepted_calls),
            ast_sleep_callsites=ast_calls,
        )


# ---------------------------------------------------------------------------
# 5. Prescriptive De-flaking Patch & Auto-Quarantine Emitter
# ---------------------------------------------------------------------------

def emit_deflaking_patch(
    source_code: str,
    test_id: str,
    leakage: Optional[StateLeakageReport] = None,
    polluter_id: Optional[str] = None,
) -> DeflakingPatch:
    """Emit a prescriptive de-flaking patch and @pytest.mark.quarantine marker.

    Generates teardown reset statements for every leaked state resource
    (mocks, environment variables, global singletons) and injects an explicit
    quarantine decorator above the target flaky test definition.

    Args:
        source_code: Original Python test file source code.
        test_id: Name of the flaky/victim or polluting test function.
        leakage: Optional StateLeakageReport identifying leaked state symbols.
        polluter_id: Optional identifier of the upstream polluting test.

    Returns:
        DeflakingPatch containing reset statements and patched source code.
    """
    reason_parts = [f"Flaky order-dependent test '{test_id}'"]
    if polluter_id:
        reason_parts.append(f"polluted by '{polluter_id}'")
    reason_str = " ".join(reason_parts)
    decorator = f'@pytest.mark.quarantine(reason="{reason_str}")'

    reset_stmts: List[str] = []
    if leakage is not None:
        if leakage.unreset_mocks:
            reset_stmts.append("unittest.mock.patch.stopall()")
        for env_key in leakage.leaked_env_vars:
            reset_stmts.append(f"os.environ.pop({repr(env_key)}, None)")
        for glob_key in leakage.leaked_globals:
            reset_stmts.append(f"# Reset leaked global/singleton: {glob_key}")

    lines = source_code.splitlines()
    patched_lines: List[str] = []
    inserted = False

    for line in lines:
        stripped = line.lstrip()
        if not inserted and (
            stripped.startswith(f"def {test_id}(")
            or stripped.startswith(f"async def {test_id}(")
        ):
            indent = line[: len(line) - len(stripped)]
            patched_lines.append(f"{indent}{decorator}")
            inserted = True
        patched_lines.append(line)

    if not inserted:
        patched_lines.append(decorator)
        patched_lines.append(f"def {test_id}():")
        patched_lines.append("    return None")

    if reset_stmts:
        patched_lines.append("")
        patched_lines.append(f"def _ftdso_teardown_{test_id}():")
        for stmt in reset_stmts:
            patched_lines.append(f"    {stmt}")

    return DeflakingPatch(
        test_id=test_id,
        polluter_id=polluter_id,
        quarantine_decorator=decorator,
        reset_statements=reset_stmts,
        patched_source="\n".join(patched_lines) + "\n",
    )


# ---------------------------------------------------------------------------
# High-Level Orchestrator Class
# ---------------------------------------------------------------------------

class FlakyTestDeterministicSieve:
    """High-level FT-DSO engine orchestrating permutation, Gray code, and leakage sieves."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed

    def verify_invariance(
        self,
        test_ids: Sequence[str],
        runner: Callable[[Sequence[str]], Mapping[str, str]],
    ) -> OrderInvarianceReport:
        """Run forward, reverse, and shuffled schedules to check R(pi_a) == R(pi_b)."""
        return verify_order_invariance(test_ids, runner, seed=self.seed)

    def isolate_toxic_pair(
        self,
        test_ids: Sequence[str],
        runner: Callable[[Sequence[str]], Mapping[str, str]],
        victim_id: Optional[str] = None,
        failing_order: Optional[Sequence[str]] = None,
    ) -> ToxicPairReport:
        """Isolate minimal <t_polluter, t_victim> pair via Gray code binary search."""
        return isolate_minimal_toxic_pair(
            test_ids=test_ids,
            runner=runner,
            victim_id=victim_id,
            failing_order=failing_order,
        )

    def audit_suite(
        self,
        test_ids: Sequence[str],
        runner: Callable[[Sequence[str]], Mapping[str, str]],
        source_code: str = "",
        leakage_reports: Optional[List[StateLeakageReport]] = None,
    ) -> FTDSOAuditReport:
        """Perform an end-to-end FT-DSO audit over a test suite."""
        invariance = self.verify_invariance(test_ids, runner)
        toxic_pairs: List[ToxicPairReport] = []
        patches: List[DeflakingPatch] = []

        if not invariance.is_order_independent:
            for victim in invariance.divergent_tests:
                tp = self.isolate_toxic_pair(
                    test_ids=test_ids,
                    runner=runner,
                    victim_id=victim,
                    failing_order=invariance.failing_order or None,
                )
                toxic_pairs.append(tp)
                matching_leak = None
                if leakage_reports:
                    for lr in leakage_reports:
                        if lr.test_id == tp.polluter or not lr.is_clean:
                            matching_leak = lr
                            break
                patches.append(
                    emit_deflaking_patch(
                        source_code=source_code,
                        test_id=victim,
                        leakage=matching_leak,
                        polluter_id=tp.polluter,
                    )
                )

        quencher = VirtualEventClockQuencher()
        clock_report = quencher.build_report(source_code=source_code)

        return FTDSOAuditReport(
            order_invariance=invariance,
            toxic_pairs=toxic_pairs,
            leakage_reports=list(leakage_reports) if leakage_reports else [],
            clock_quench=clock_report,
            patches=patches,
        )
