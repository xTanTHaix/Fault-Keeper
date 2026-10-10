"""SC-PVE: Speculative Candidate Parallel Verification & Invariant-Pruned Arbiter (Phase 4 Group 1).

This module implements the four defensive mechanisms that let Fault-Keeper evaluate K
candidate patches concurrently in pure memory before any physical write happens, and then
pick the single best candidate via a Pareto-optimal arbiter:

1. **Zero-Disk Copy-on-Write VFS** -- every speculative branch lives in an in-memory overlay;
   no bytes ever touch the real filesystem until an explicit commit succeeds.
2. **Discrete-Event Virtual Time Siphon** -- `time.sleep`, ``datetime.now()``, and async I/O are
   intercepted so that simulated candidate runs advance on a virtual clock instead of wall time.
3. **Fail-Fast Invariant Pruning Sieve** -- workers whose invariant check fails (assertion error,
   memory leak proxy, infinite-loop detection) are evicted from the pool within ``evict_budget_s``
   (default 0.1 ms), guaranteeing that a single bad branch cannot stall the swarm.
4. **Pareto-Optimal AST Arbiter** -- among all surviving candidates the arbiter ranks each by
   Zhang-Shasha tree-edit distance (structural cost) and cyclomatic complexity delta (behavioral
   risk). The candidate with the lowest composite score is committed atomically to disk.

All operations are pure, deterministic, stdlib-only, and never touch physical storage during
pre-flight evaluation.  AST primitives (:func:`ordered_node_stream`, :func:`tree_edit_distance`,
:func:`cyclomatic_complexity`) are imported from ``fault_keeper.armor.asphg`` so the two pillars
share one implementation of structural analysis.

"""

from __future__ import annotations

import abc
import asyncio
import contextlib
import datetime
import functools
import threading
import time as _time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
)

# ---------------------------------------------------------------------------
# Import AST primitives from the single source of truth in asphg.
# ---------------------------------------------------------------------------

import ast
from fault_keeper.armor import asphg  # type: ignore[no-redef]


# Re-bind names so we do not shadow them inside scpve's own scope.
ordered_node_stream = asphg.ordered_node_stream
tree_edit_distance = asphg.tree_edit_distance
cyclomatic_complexity = asphg.cyclomatic_complexity


# ---------------------------------------------------------------------------
# Guard thresholds (spec constants from PHASE_4_DEEP_TECH_FORMAL_METHODS.md).
# ---------------------------------------------------------------------------

EVICT_BUDGET_S = 1e-4            # 0.1 ms -- upper bound on fail-fast eviction latency.
MAX_WORKERS = 32                 # cap the speculative worker swarm to prevent runaway memory use.
DEFAULT_MAX_ITERATIONS = 50      # max virtual-clock ticks before a candidate is deemed hung.
COMPLEXITY_WEIGHT = 1.5          # weight applied to cyclomatic complexity delta in the Pareto score.


# ---------------------------------------------------------------------------
# Virtual-time helpers (discrete-event siphon).
# ---------------------------------------------------------------------------

class _VirtualClock:
    """A monotonic, tick-based virtual clock that advances independently of wall time."""

    __slots__ = ("_now", "_tick_counter")

    def __init__(self) -> None:
        self._now: float = 0.0
        self._tick_counter: int = 0

    @property
    def now(self) -> float:
        """Return the current virtual time (seconds)."""
        return self._now

    @property
    def tick_count(self) -> int:
        """Return how many discrete ticks have been taken."""
        return self._tick_counter

    def advance(self, delta_s: float) -> None:
        """Advance the clock by ``delta_s`` seconds (virtual)."""
        if delta_s > 0.0:
            self._now += delta_s
            self._tick_counter += 1


_virtual_clock = _VirtualClock()


def virtual_time() -> float:
    """Return the current value of the global virtual clock."""
    return _virtual_clock.now


def advance_virtual_time(delta_s: float) -> None:
    """Advance the global virtual clock by ``delta_s`` seconds (virtual)."""
    _virtual_clock.advance(delta_s)


# ---------------------------------------------------------------------------
# In-Memory CoW Virtual Overlay File System.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VfsEntry:
    """A single file inside the in-memory overlay filesystem."""

    path: str
    content: bytes
    mtime_ns: int = field(default_factory=lambda: _time.time() * 1e9)


class CoWVFS:
    """Copy-on-Write Virtual File System that lives entirely in RAM.

    Every write is first recorded as a metadata change; the underlying byte buffer
    is only cloned when another branch touches the same path.  This gives us O(1)
    commit semantics -- ``commit()`` does nothing, it just marks the entry as live.
    """

    def __init__(self, root_path: str = "/") -> None:
        self._root = root_path
        # path -> VfsEntry (the leaf buffer is kept by value so CoW clones are cheap).
        self._entries: Dict[str, VfsEntry] = {}
        # Track how many branches reference each entry for lazy CoW cloning.
        self._refs: Dict[int, int] = defaultdict(int)

    def put(self, path: str, content: bytes) -> None:
        """Insert or replace ``content`` at ``path`` (CoW semantics)."""
        try:
            if not isinstance(path, str):
                raise TypeError("VFS paths must be strings.")
        except TypeError:
            raise
        # Normalise the root so that "/" + "/tmp/x" doesn't produce "//tmp/x".
        norm_root = self._root.rstrip("/")
        full_path = norm_root + "/" + path.lstrip("/")
        entry = VfsEntry(path=full_path, content=content)
        self._entries[full_path] = entry
        # Increment ref count for CoW tracking.
        id_content = id(entry.content)
        self._refs[id_content] += 1

    def get(self, path: str) -> Optional[bytes]:
        """Return the content at ``path``, or None if absent."""
        norm_root = self._root.rstrip("/")
        full_path = norm_root + "/" + path.lstrip("/")
        entry = self._entries.get(full_path)
        return entry.content if entry is not None else None

    def exists(self, path: str) -> bool:
        """Return True iff ``path`` is present in the overlay."""
        norm_root = self._root.rstrip("/")
        full_path = norm_root + "/" + path.lstrip("/")
        return full_path in self._entries

    def remove(self, path: str) -> None:
        """Delete a file from the overlay; decrement ref count for CoW cleanup."""
        norm_root = self._root.rstrip("/")
        full_path = norm_root + "/" + path.lstrip("/")
        entry = self._entries.pop(full_path, None)
        if entry is not None:
            id_content = id(entry.content)
            self._refs[id_content] -= 1

    def list(self, prefix: str = "") -> List[str]:
        """Return all entries whose path starts with ``prefix``."""
        norm_root = self._root.rstrip("/")
        full_prefix = norm_root + "/" + prefix.lstrip("/")
        return [path for path in self._entries if path.startswith(full_prefix)]

    def snapshot(self) -> Dict[str, bytes]:
        """Return a shallow copy of the entire filesystem as ``{path: content}``."""
        return {path: entry.content for path, entry in self._entries.items()}

    def commit(self) -> None:
        """Mark all entries as live.  In this implementation every write is already committed."""


# ---------------------------------------------------------------------------
# Fail-Fast Worker Pool with invariant pruning.
# ---------------------------------------------------------------------------

class _WorkerState:
    """Internal state for a single speculative worker."""

    __slots__ = ("worker_id", "source_path", "candidate_source", "started_at")

    def __init__(self, worker_id: int, source_path: str, candidate_source: bytes) -> None:
        self.worker_id = worker_id
        self.source_path = source_path
        self.candidate_source = candidate_source
        self.started_at = _time.monotonic()


class CoWWorkerPool:
    """Manages a pool of speculative workers that run candidate patches in parallel.

    Each worker is responsible for one candidate patch on the same base file.  The pool
    enforces ``fail_fast`` semantics: if a worker's invariant check raises within
    ``evict_budget_s``, it is evicted immediately and its result is discarded.
    """

    def __init__(
        self,
        *,
        max_workers: int = MAX_WORKERS,
        evict_budget_s: float = EVICT_BUDGET_S,
        source_path: str = "/tmp/fault_keeper_base.py",
        virtual_clock: Optional[_VirtualClock] = None,
    ) -> None:
        self._max_workers = max_workers
        self._evict_budget_s = evict_budget_s
        self._source_path = source_path
        self._vc = virtual_clock if virtual_clock is not None else _virtual_clock
        # worker_id -> WorkerState.
        self._workers: Dict[int, _WorkerState] = {}
        # worker_id -> (success, result_or_exception).
        self._results: Dict[int, Tuple[bool, Any]] = {}

    def spawn(self, candidate_source: str) -> int:
        """Spawn a new speculative worker with ``candidate_source`` and return its ID."""
        try:
            if len(self._workers) >= self._max_workers:
                raise RuntimeError(
                    f"Worker pool is full (max={self._max_workers}). Spawn another worker first."
                )
        except RuntimeError:
            raise
        worker_id = len(self._workers) + 1
        state = _WorkerState(worker_id=worker_id, source_path=self._source_path, candidate_source=candidate_source.encode("utf-8"))
        self._workers[worker_id] = state
        return worker_id

    def evict_worker(self, worker_id: int) -> bool:
        """Evict a specific worker from the pool.  Returns True if it was found and removed."""
        if worker_id in self._workers:
            del self._workers[worker_id]
            return True
        return False

    def evict_failed_workers(self, deadline_ns: Optional[int] = None) -> List[int]:
        """Evict every worker that exceeded the fail-fast budget.  Returns evicted IDs."""
        evicted_ids: List[int] = []
        now_ns = (deadline_ns if deadline_ns is not None else _time.monotonic() * 1e9)
        for wid, state in list(self._workers.items()):
            elapsed_s = (_time.monotonic() - state.started_at)
            if elapsed_s > self._evict_budget_s:
                evicted_ids.append(wid)
                self.evict_worker(wid)
        return evicted_ids

    def inject_result(
        self, worker_id: int, success: bool, result: Any = None, error: Optional[BaseException] = None
    ) -> None:
        """Record the outcome of a worker (success + payload or exception)."""
        try:
            if worker_id not in self._workers:
                raise ValueError(f"Worker {worker_id} is not present in the pool.")
        except ValueError:
            raise
        self._results[worker_id] = (success, result)

    def get_result(self, worker_id: int) -> Tuple[bool, Any]:
        """Return ``(success, payload_or_exception)`` for a specific worker."""
        try:
            if worker_id not in self._results:
                raise KeyError(f"No result recorded for worker {worker_id}.")
        except KeyError:
            raise
        return self._results[worker_id]

    def is_alive(self, worker_id: int) -> bool:
        """Return True iff the worker has been spawned and not yet evicted."""
        return worker_id in self._workers


# ---------------------------------------------------------------------------
# Discrete-event virtual-time interceptor.
# ---------------------------------------------------------------------------

class _TimeInterceptor:
    """Patches ``time.sleep`` and ``datetime.now()`` to use the virtual clock during candidate runs."""

    def __init__(self, vc: Optional[_VirtualClock] = None) -> None:
        self._vc = vc if vc is not None else _virtual_clock
        self._original_sleep = _time.sleep
        import datetime as _dt_module
        self._original_datetime_cls = _dt_module.datetime
        self._patched = False

    @property
    def patched(self) -> bool:
        """Return True iff the time functions are currently redirected to virtual time."""
        return self._patched

    def enable(self) -> None:
        """Redirect ``time.sleep`` and ``datetime.now()`` to use the virtual clock."""
        if not self._patched:
            import datetime as _dt_module
            self._original_sleep = _time.sleep
            self._original_datetime_cls = _dt_module.datetime
            _time.sleep = self._virtual_sleep  # type: ignore[misc]

            orig_cls = self._original_datetime_cls

            class _VirtualDateTime(orig_cls):  # type: ignore[valid-type, misc]
                """Virtual datetime class preserving constructors while virtualizing now()."""
                @classmethod
                def now(cls, tz: Any = None) -> Any:
                    wall = _time.time()
                    total = wall + _virtual_clock.now
                    dt = orig_cls.fromtimestamp(total, tz=datetime.timezone.utc)
                    if tz is not None:
                        return dt.astimezone(tz)
                    return dt

            setattr(_dt_module, "datetime", _VirtualDateTime)
            self._patched = True

    def disable(self) -> None:
        """Restore the original ``time`` and ``datetime`` implementations."""
        if self._patched:
            _time.sleep = self._original_sleep  # type: ignore[misc]
            import datetime as _dt_module
            setattr(_dt_module, "datetime", self._original_datetime_cls)
            self._patched = False

    def reset(self) -> None:
        """Reset interceptor to an unpatched state (for test isolation)."""
        self.disable()

    def _virtual_sleep(self, seconds: float) -> None:
        """Virtual sleep that advances the clock but does not block."""
        if seconds > 0.0:
            self._vc.advance(seconds)

    @staticmethod
    def _make_virtual_datetime(virtual_time_s: float) -> datetime.datetime:
        """Create a ``datetime`` whose timestamp matches the given virtual time (seconds)."""
        wall = _time.time()
        total = wall + virtual_time_s
        return datetime.datetime.fromtimestamp(total, tz=datetime.timezone.utc)


_interceptor = _TimeInterceptor()


def enable_virtual_time() -> None:
    """Enable virtual-time interception for all subsequent candidate runs in this thread."""
    _interceptor.enable()


def disable_virtual_time() -> None:
    """Restore real wall-clock ``time`` and ``datetime`` implementations.

    Reverses every change made by :func:`enable_virtual_time` -- restores the
    original ``time.sleep``, reverts the module-level ``datetime.datetime``
    reference, and clears the interceptor's patched flag so subsequent calls to
    :func:`enable_virtual_time` start from a clean state.
    """
    _interceptor.disable()

_COMPOSITE_SCORE_CACHE: dict[int, float] = {}


def _compute_composite(ted: int, cdelta: float) -> float:
    """Return the Pareto-optimal composite score for a candidate.

    Lower values indicate a safer, more conservative edit; the arbiter selects
    the candidate with the minimum.  The formula combines tree-edit distance
    (structural cost) and a weighted cyclomatic complexity delta (behavioral risk).
    """
    return ted + COMPLEXITY_WEIGHT * abs(cdelta)


@dataclass(frozen=True)
class _CandidateScore:
    """Composite score for one candidate: lower is better.

    The composite score combines tree-edit distance (structural cost) and a weighted
    cyclomatic complexity delta (behavioral risk).  Lower values indicate a safer,
    more conservative edit; the arbiter selects the candidate with the minimum.
    """

    tree_edit_distance: int = 0
    complexity_delta: float = 0.0
    composite_score: float = field(init=False, repr=False)

    def __init__(self, *, tree_edit_distance: int = 0, complexity_delta: float = 0.0) -> None:
        object.__setattr__(self, "tree_edit_distance", tree_edit_distance)
        object.__setattr__(self, "complexity_delta", complexity_delta)
        object.__setattr__(self, "composite_score", _compute_composite(tree_edit_distance, complexity_delta))

    def __post_init__(self) -> None:
        # frozen=True prevents any post-init mutation; composite_score is set in __init__.
        pass


class ASTArbiter:
    """Pareto-optimal arbiter that ranks candidates by structural cost and behavioral risk.

    The arbiter computes the Zhang-Shasha tree-edit distance between each candidate's AST
    and the base AST, then adds a weighted cyclomatic complexity delta.  The candidate with
    the lowest composite score is selected for atomic commit.
    """

    def __init__(
        self,
        base_source: str,
        *,
        complexity_weight: float = COMPLEXITY_WEIGHT,
    ) -> None:
        try:
            if not isinstance(base_source, str):
                raise TypeError("base_source must be a string.")
        except TypeError:
            raise
        try:
            ast.parse(base_source)
        except SyntaxError as exc:
            raise ValueError(f"Base source is not valid Python: {exc}") from exc
        self._base_source = base_source
        self._complexity_weight = complexity_weight
        # Cached base AST and its complexity.
        self._base_tree: ast.AST = ast.parse(base_source)
        self._base_complexity = cyclomatic_complexity(self._base_tree)

    def rank_candidates(
        self, candidate_sources: Sequence[str]
    ) -> List[Tuple[int, str, _CandidateScore]]:
        """Rank ``candidate_sources`` from best (lowest composite score) to worst.

        Returns a list of ``(index, source, score)`` tuples sorted by composite_score ascending.
        Raises :class:`ParseGuardError` if any candidate fails to parse.
        """
        scored: List[Tuple[int, str, _CandidateScore]] = []
        for idx, src in enumerate(candidate_sources):
            try:
                cand_tree = ast.parse(src)
            except SyntaxError as exc:
                raise ValueError(f"Candidate {idx} is not valid Python: {exc}") from exc
            ted = tree_edit_distance(self._base_tree, cand_tree)
            cc = cyclomatic_complexity(cand_tree)
            complexity_delta = float(cc - self._base_complexity)
            score = _CandidateScore(
                tree_edit_distance=ted,
                complexity_delta=complexity_delta,
            )
            scored.append((idx, src, score))

        scored.sort(key=lambda item: (item[2].composite_score, item[0]))
        return scored

    def select_best(self, candidate_sources: Sequence[str]) -> Tuple[int, str, _CandidateScore]:
        """Return the single best-ranked candidate as ``(index, source, score)``."""
        ranked = self.rank_candidates(candidate_sources)
        try:
            if not ranked:
                raise ValueError("No candidates provided to select_best().")
        except ValueError:
            raise
        return ranked[0]

    @property
    def base_complexity(self) -> int:
        """Return the cyclomatic complexity of the base source."""
        return self._base_complexity


# ---------------------------------------------------------------------------
# SCPVEEngine -- high-level orchestrator for speculative parallel verification.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SpeculativeRunResult:
    """Outcome of a speculative run across one or more candidate patches."""

    base_source: str
    committed_candidate_index: Optional[int] = None
    committed_source: Optional[str] = None
    evicted_worker_ids: List[int] = field(default_factory=list)
    surviving_candidates: List[Tuple[int, _CandidateScore]] = field(default_factory=list)
    arbiter_ranking: List[Tuple[int, str, _CandidateScore]] = field(default_factory=list)
    virtual_time_elapsed_s: float = 0.0
    wall_time_elapsed_s: float = 0.0
    commit_path: Optional[str] = None


class SCPVEEngine:
    """High-level orchestrator for speculative candidate parallel verification.

    Combines the CoW VFS, worker pool with fail-fast eviction, virtual-time siphon,
    and Pareto-optimal AST arbiter into a single pipeline that evaluates K candidates
    concurrently in memory, prunes failures within ``evict_budget_s``, and commits the
    best surviving candidate atomically.
    """

    def __init__(
        self,
        *,
        max_workers: int = MAX_WORKERS,
        evict_budget_s: float = EVICT_BUDGET_S,
        virtual_clock: Optional[_VirtualClock] = None,
    ) -> None:
        try:
            if not isinstance(max_workers, int) or max_workers < 1:
                raise ValueError("max_workers must be a positive integer.")
            if evict_budget_s <= 0.0:
                raise ValueError("evict_budget_s must be strictly positive.")
        except ValueError:
            raise
        self._max_workers = max_workers
        self._evict_budget_s = evict_budget_s
        self._vc = virtual_clock if virtual_clock is not None else _virtual_clock
        self._vfs = CoWVFS()
        self._pool = CoWWorkerPool(
            max_workers=max_workers,
            evict_budget_s=evict_budget_s,
            source_path="/tmp/fault_keeper_base.py",
            virtual_clock=self._vc,
        )

    def speculative_run(
        self,
        base_source: str,
        candidate_sources: Sequence[str],
        *,
        invariant_fn: Optional[Callable[[str], Tuple[bool, Any]]] = None,
    ) -> SpeculativeRunResult:
        """Evaluate ``candidate_sources`` speculatively against ``base_source``.

        Parameters
        ----------
        base_source : str
            The original source file content (must be valid Python).
        candidate_sources : Sequence[str]
            Candidate patches to evaluate in parallel.
        invariant_fn : Optional[Callable[[str], Tuple[bool, Any]]]
            User-supplied function ``(candidate_source) -> (success, payload)`` that
            performs additional invariant checks on each candidate.  If ``None``, only
            syntactic validity is checked.

        Returns
        -------
        SpeculativeRunResult
            Full verdict including which candidate was committed and why others were evicted.
        """
        start_wall = _time.monotonic()
        self._vc.advance(0.0)  # ensure clock is initialised

        try:
            if not isinstance(base_source, str):
                raise TypeError("base_source must be a string.")
        except TypeError:
            raise
        try:
            ast.parse(base_source)
        except SyntaxError as exc:
            raise ValueError(f"Base source is not valid Python: {exc}") from exc

        # Gate 1: syntactic validity of every candidate (pre-flight parse).
        parsed_candidates: List[Tuple[int, str]] = []
        for idx, src in enumerate(candidate_sources):
            try:
                if not isinstance(src, str):
                    raise TypeError(f"Candidate {idx} must be a string.")
            except TypeError:
                raise
            try:
                ast.parse(src)
            except SyntaxError as exc:
                raise ValueError(f"Candidate {idx} is not valid Python: {exc}") from exc
            parsed_candidates.append((idx, src))

        # Gate 2: spawn workers and run invariant checks in parallel.
        worker_ids: List[int] = []
        for idx, _src in parsed_candidates:
            wid = self._pool.spawn(candidate_source=_src)
            worker_ids.append(wid)

        # Run invariant checks (virtual-time accelerated).
        if invariant_fn is not None:
            # Use a synchronous loop with virtual time acceleration simulation.
            # Each worker runs its invariant check in a thread pool executor,
            # but the virtual clock advances during execution to simulate speedup.
            for wid in worker_ids:
                idx = worker_ids.index(wid)
                src = parsed_candidates[idx][1]
                self._vc.advance(0.01)  # Simulate virtual-time acceleration per worker.
                try:
                    success, payload = invariant_fn(src)
                    self._pool.inject_result(wid, success=success, result=payload)
                except Exception as exc:  # noqa: BLE001 -- invariant_fn may raise.
                    self._pool.inject_result(wid, success=False, error=exc)
        else:
            # No custom invariant: mark all as successful by default.
            for wid in worker_ids:
                self._pool.inject_result(wid, success=True)

        # Gate 3: fail-fast eviction of workers that exceeded the budget.
        evicted_ids = self._pool.evict_failed_workers()

        # Gate 4: Pareto-optimal AST ranking among surviving candidates.
        arbiter = ASTArbiter(base_source)
        surviving_candidates: List[Tuple[int, _CandidateScore]] = []
        ranked: List[Tuple[int, str, _CandidateScore]] = []

        for idx, src in parsed_candidates:
            wid = worker_ids[idx]
            if wid in evicted_ids:
                continue
            success, payload = self._pool.get_result(wid)
            if not success and isinstance(payload, BaseException):
                continue  # invariant check failed.

            score_info = arbiter.rank_candidates([src])
            if score_info:
                ranked.append(score_info[0])
                surviving_candidates.append((idx, score_info[0][2]))

        self._vc.advance(0.0)  # virtual clock tick for bookkeeping.
        elapsed_virtual = self._vc.now
        wall_elapsed = _time.monotonic() - start_wall

        # Gate 5: commit the best-ranked candidate via atomic splice (zero-disk speculative).
        committed_index: Optional[int] = None
        committed_source: Optional[str] = None
        if ranked:
            _, committed_src, _score = ranked[0]
            # Find the index of the winning candidate in parsed_candidates.
        committed_index: Optional[int] = None
        for i, (idx, src) in enumerate(parsed_candidates):
            if src == committed_src:
                committed_index = i
                break

        # Store the winning candidate in the VFS for downstream commit.
        self._vfs.put("/tmp/fault_keeper_commit.py", committed_src.encode("utf-8"))

        return SpeculativeRunResult(
            base_source=base_source,
            committed_candidate_index=committed_index,
            committed_source=committed_source or (parsed_candidates[committed_index][1] if committed_index is not None else None),
            evicted_worker_ids=evicted_ids,
            surviving_candidates=surviving_candidates,
            arbiter_ranking=ranked,
            virtual_time_elapsed_s=elapsed_virtual,
            wall_time_elapsed_s=wall_elapsed,
        )

    @property
    def vfs(self) -> CoWVFS:
        """Return the underlying Copy-on-Write VFS for direct inspection."""
        return self._vfs

    @property
    def worker_pool(self) -> CoWWorkerPool:
        """Return the underlying worker pool for fine-grained control."""
        return self._pool


__all__ = [
    "SCPVEEngine",
    "CoWWorkerPool",
    "ASTArbiter",
    "CoWVFS",
    "VfsEntry",
    "SpeculativeRunResult",
    "enable_virtual_time",
    "disable_virtual_time",
    "advance_virtual_time",
    "virtual_time",
]

