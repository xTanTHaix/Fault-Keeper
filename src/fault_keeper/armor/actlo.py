"""ACT-LO: Agent Convergence & Thrashing-Loop Oracle (Phase 4 Group 1).

This module models an autonomous coding agent's *defect trajectory* and detects
the two failure modes that make such a loop unproductive:

1. **Monotonic Progress Invariant** -- the defect-state entropy ``E(s_k)`` must be
   non-increasing across consecutive turns; a turn whose entropy rises signals a
   regression and triggers a *rollback checkpoint* (the agent rejects the change
   that increased its error profile).  :func:`defect_entropy` implements Shannon
   entropy over the ``(failed-tests, errors, churn)`` defect distribution.
2. **Cycle / Thrashing Sieve** -- when two states within a rolling window are
   nearly identical (``SimState(s_i, s_k) >= STATE_SIMILARITY_THRESHOLD``), the agent
   is oscillating between the same failing configurations; :class:`DoomLoopDetector`
   flags this as a doom loop / thrashing cycle.

When a doom loop is detected the engine can also extract a **Minimal Unsatisfiable
Core (MUC)** from the candidate constraint clauses via a small, dependency-free DPLL
SAT solver (:mod:`fault_keeper.armor.actlo.Minisat`) and render it as a *steering
prompt* that names exactly the conflicting assertions to relax.  Everything here is
pure, deterministic, stdlib-only, and never touches physical storage.
"""

from __future__ import annotations

import math
from collections import OrderedDict
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Guard thresholds (spec constants from PHASE_4_DEEP_TECH_FORMAL_METHODS.md).
# ---------------------------------------------------------------------------

STATE_SIMILARITY_THRESHOLD = 0.95   # SimState >= this flags a doom-loop / thrash cycle.
DEFAULT_WINDOW_SIZE = 16            # rolling history of states kept for the sieve.
MONOTONIC_EPSILON = 1e-9            # numerical tolerance on E(s_{k+1}) <= E(s_k).

# MUC extraction safety bound.
MUC_MAX_CLAUSES = 64   # maximum clauses considered for UNSAT-core minimization.

# A defect state is a triple: < failed-test mask, hash-diff (churn), error count >.
FeatureVector = Tuple[float, float, float]


@dataclass(frozen=True)
class DefectState:
    """Snapshot of an agent's defect condition at one turn ``k``.

    Attributes:
        failed_mask: Identifiers of the tests currently failing after this turn.
        error_count: Number of non-test error signals (exceptions, invariant hits).
        churn: Magnitude of code change versus the previous accepted patch
            (structural hash delta); zero for a no-op turn.
    """

    failed_mask: frozenset[str] = field(default_factory=frozenset)
    error_count: int = 0
    churn: Optional[int] = None


def defect_entropy(state: DefectState) -> float:
    """Return the Shannon entropy (bits) of a defect state's distribution.

    The three defect signals ``(failed-tests, errors, churn)`` form a count vector;
    normalising it to a probability distribution and summing ``-p * log2(p)`` yields
    an entropy that grows when the profile spreads across categories and collapses to
    zero when every signal concentrates in one category (a clean or single-failure
    state).  A rising value therefore marks a regression of the agent's condition.
    """
    counts = [len(state.failed_mask), max(state.error_count, 0), max(state.churn or 0, 0)]
    total = sum(counts)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in counts:
        if count > 0:
            probability = count / total
            entropy -= probability * math.log2(probability)
    return entropy


def _feature_vector(state: DefectState) -> Optional[FeatureVector]:
    """Return the L2-normalised ``(mask, errors, churn)`` feature vector of ``state``.

    Returns ``None`` when every component is zero so callers can treat a clean state
    as its own (trivially self-similar) signature rather than a degenerate direction.
    """
    raw = [float(len(state.failed_mask)), float(max(state.error_count, 0)), float(max(state.churn or 0, 0))]
    norm = math.sqrt(sum(component * component for component in raw))
    if norm == 0.0:
        return None
    return tuple(component / norm for component in raw)


def _mask_jaccard(a: DefectState, b: DefectState) -> float:
    """Jaccard overlap of the failing-test masks of two states (1.0 when both empty)."""
    set_a = set(a.failed_mask)
    set_b = set(b.failed_mask)
    if not set_a and not set_b:
        return 1.0
    union_size = len(set_a | set_b)
    if union_size == 0:
        return 0.0
    return len(set_a & set_b) / union_size


def state_similarity(a: DefectState, b: DefectState) -> float:
    """Return how similar two defect states are in ``[0.0, 1.0]``.

    Combines the cosine similarity of their normalised feature vectors with the
    Jaccard overlap of their failing-test masks so that both *magnitude* drift and
    *membership* churn contribute to a doom-loop verdict.  Identical states score 1.0.
    """
    vec_a = _feature_vector(a)
    vec_b = _feature_vector(b)
    if vec_a is None and vec_b is None:
        return 1.0
    if vec_a is None or vec_b is None:
        return 0.0
    dot = sum(x * y for x, y in zip(vec_a, vec_b))
    cosine = dot / math.sqrt(sum(x * x for x in vec_a) * sum(y * y for y in vec_b))
    combined = 0.6 * cosine + 0.4 * _mask_jaccard(a, b)
    return max(0.0, min(1.0, combined))


# ---------------------------------------------------------------------------
# Minimal Unsatisfiable Core via a dependency-free DPLL SAT solver (no Z3).
# ---------------------------------------------------------------------------

Literal = int          # positive var id == literal true; negative var id == literal false.
Clause = frozenset[Literal]


@dataclass(frozen=True)
class ConstraintClause:
    """A named boolean clause over literals, used to model agent assertions."""

    name: str
    literals: Tuple[int, ...]

    def as_clause(self) -> Clause:
        """Return the clause as a frozenset of literal ints for the solver."""
        return frozenset(literal for literal in self.literals if literal != 0)


class Minisat:
    """A small, deterministic DPLL SAT solver sufficient for MUC extraction.

    Clauses are stored as ``frozenset[int]`` literals (positive var id true, negative
    false).  The solver performs unit propagation followed by branching on the lowest
    unassigned variable; it is intentionally compact rather than a full CDCL engine
    and is bounded to small clause counts so MUC extraction cannot run away.
    """

    def __init__(self) -> None:
        self._clauses: List[Clause] = []
        self._vars: frozenset[int] = frozenset()

    def add_clause(self, *literals: Literal, meta: Optional[str] = None) -> "Minisat":
        """Register a clause and return ``self`` for fluent chaining."""
        clause = frozenset(literal for literal in literals if literal != 0)
        self._clauses.append(clause)
        self._vars |= {abs(literal) for literal in clause}
        return self

    def solve(self) -> Optional[Dict[int, bool]]:
        """Return a satisfying assignment, or ``None`` when the formula is UNSAT."""
        import sys
        if [] in self._clauses:
            return None
        model = self._propagate({})
        if model is None:
            return None
        unassigned = sorted(var for var in self._vars if var not in model)
        if not unassigned:
            return dict(model)

        def branch(assignment: Dict[int, bool]) -> Optional[Dict[int, bool]]:
            assignment = self._propagate(assignment)
            if assignment is None:
                return None
            unassigned = sorted(var for var in self._vars if var not in assignment)
            if not unassigned:
                return dict(assignment)
            variable = unassigned[0]
            for value in (True, False):
                trial = dict(assignment)
                trial[variable] = value
                result = branch(trial)
                if result is not None:
                    return result
            return None

        return branch(model)

    def _propagate(self, assignment: Dict[int, bool]) -> Optional[Dict[int, bool]]:
        """Unit-propagate ``assignment``; return it when consistent, else ``None``."""
        changed = True
        iterations = 0
        max_iterations = 1000  # safety bound to prevent infinite loops
        while changed and iterations < max_iterations:
            iterations += 1
            changed = False
            for clause in self._clauses:
                unassigned = [literal for literal in clause if abs(literal) not in assignment]
                satisfied = any(_literal_satisfied(literal, assignment) for literal in clause)
                if satisfied:
                    continue
                if not unassigned:
                    return None  # all literals assigned but the clause is false -> UNSAT.
                if len(unassigned) == 1:
                    literal = unassigned[0]
                    assignment[literal] = True
                    changed = True
        return assignment


def _clauses_iter(assignment: Dict[int, bool]) -> Sequence[Clause]:
    """Yield clauses (kept for API compatibility; use solver._clauses directly)."""
    return tuple()


def _literal_satisfied(literal: Literal, assignment: Dict[int, bool]) -> bool:
    """Return whether ``assignment`` satisfies a single literal (positive == var true)."""
    value = assignment.get(abs(literal))
    if value is None:
        return False
    return (literal > 0) and value or (literal < 0) and not value


def minimal_unsatisfiable_core(sat: Minisat, only_indices: Optional[Sequence[int]] = None) -> Optional[List[int]]:
    """Return an inclusion-minimal UNSAT core of ``sat``'s clauses as sorted indices.

    The returned index set is unsatisfiable on its own and dropping any single clause
    makes it satisfiable -- exactly the Minimal Unsatisfiable Core used to pinpoint the
    conflicting assertions behind a doom loop.  Returns ``None`` when the whole formula
    is SAT (no conflict), or ``[]`` for an empty formula.  Bounded by :data:`MUC_MAX_CLAUSES`
    so pathological inputs cannot trigger exponential blow-up.
    """
    candidate_indices = set(only_indices) if only_indices else None

    def active_set() -> frozenset[int]:
        return {i for i in range(len(sat._clauses)) if (candidate_indices is None or i in candidate_indices)}

    def is_unsat(index_set: Sequence[int]) -> bool:
        subset = [sat._clauses[i] for i in index_set]
        probe = Minisat()
        probe._clauses = subset  # type: ignore[attr-defined]
        probe._vars = frozenset(abs(literal) for clause in subset for literal in clause)
        return probe.solve() is None

    active = active_set()
    if not active:
        return []
    if not is_unsat(list(active)):
        return None  # SAT overall -> there is no conflicting core.

    iteration = 0
    while len(active) > MUC_MAX_CLAUSES:  # safety bound
        iteration += 1
        if iteration % 100 == 0:
            print(f"MUC minimization iteration {iteration}, active clauses: {len(active)}")
            sys.stdout.flush()
        removable: List[int] = []
        for i in list(active):
            trial = [j for j in active if j != i]
            try:
                if not is_unsat(trial):
                    removable.append(i)  # dropping clause ``i`` keeps UNSAT -> safe to drop.
            except Exception as e:
                print(f"Error checking subset {trial}: {e}")
                sys.stdout.flush()
        if not removable:
            break
        active = {i for i in active if i not in set(removable)}

    return sorted(active)


class MucSteeringAdvisor:
    """Turns a Minimal Unsatisfiable Core into an actionable steering prompt."""

    @staticmethod
    def build_prompt(core_indices: Sequence[int], constraint_names: Sequence[str]) -> str:
        """Render the conflicting constraints as a focused fix instruction.

        ``core_indices`` index into ``constraint_names``; only those assertions are
        named, so the agent learns precisely which constraints to relax rather than
        guessing at any of them.
        """
        if not core_indices:
            return "No conflicting constraints identified; the constraint set is satisfiable."
        ordered = sorted(core_indices)
        names = ", ".join(constraint_names[i] for i in ordered)
        return (
            "[ACT-LO] Doom-loop steering prompt: the Minimal Unsatisfiable Core pinpoints "
            f"these conflicting assertions as {names}. Relax or reconcile exactly these "
            "constraints to break the cycle; do not change unrelated constraints."
        )


# ---------------------------------------------------------------------------
# Doom-loop / thrashing detection.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Observation:
    """Result of feeding one turn's defect state into :class:`DoomLoopDetector`."""

    step_index: int
    entropy: float
    monotonic_violation: bool = False   # E(s_k) rose above the previous turn.
    rollback_triggered: bool = False    # set together with a monotonic violation.
    doom_loop_detected: bool = False    # a near-identical prior state recurred.
    thrashing_detected: bool = False    # same as doom-loop for this oracle.
    similar_to_step: Optional[int] = None   # index of the recurrent prior state, if any.
    steering_prompt: Optional[str] = None  # populated when a MUC could be built.


class DoomLoopDetector:
    """Detects doom loops / thrashing in a stream of :class:`DefectState` snapshots."""

    def __init__(self, *, similarity_threshold: float = STATE_SIMILARITY_THRESHOLD, window_size: int = DEFAULT_WINDOW_SIZE) -> None:
        try:
            if not 0.0 <= similarity_threshold <= 1.0:
                raise ValueError("similarity_threshold must lie within [0.0, 1.0].")
            if window_size < 2:
                raise ValueError("window_size must be at least 2 to detect a recurrence.")
        except ValueError:
            raise
        self._similarity_threshold = similarity_threshold
        self._window_size = window_size
        self._seen: "OrderedDict[str, DefectState]" = OrderedDict()
        self._step_history: List[int] = []  # insertion-order step indices for prior states.

    @staticmethod
    def _signature(state: DefectState) -> str:
        """Return a canonical hash of the state so identical states share a key."""
        import hashlib

        payload = "|".join(
            [
                repr(sorted(state.failed_mask)),
                str(state.error_count),
                str(state.churn if state.churn is not None else 0),
            ]
        )
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()

    def observe(self, state: DefectState) -> Observation:
        """Record ``state``, run the cycle sieve, and return an :class:`Observation`."""
        entropy = defect_entropy(state)
        similar_to_step: Optional[int] = None
        for step_idx, prior_state in zip(self._step_history, list(self._seen.values())):
            if state_similarity(prior_state, state) >= self._similarity_threshold:
                similar_to_step = int(step_idx)
                break

        observation = Observation(
            step_index=len(self._seen),
            entropy=entropy,
            similar_to_step=similar_to_step,
            doom_loop_detected=False,
            thrashing_detected=False,
        )
        if similar_to_step is not None:
            observation = replace(observation, doom_loop_detected=True, thrashing_detected=True)

        self._step_history.append(len(self._seen))
        self._seen[DoomLoopDetector._signature(state)] = state
        excess = len(self._seen) - self._window_size
        if excess > 0:
            for _ in range(excess):
                self._seen.popitem(last=False)
                del self._step_history[_]
        return observation


# ---------------------------------------------------------------------------
# High-level engine tying monotonic progress, the cycle sieve, and MUC steering.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TurnResult:
    """Full verdict for one agent turn."""

    state: DefectState
    entropy: float
    monotonic_violation: bool
    rollback_triggered: bool
    doom_loop_detected: bool
    similar_to_step: Optional[int]
    steering_prompt: Optional[str]


class ACTLOEngine:
    """Tracks an agent's defect trajectory and steers it out of doom loops."""

    def __init__(self, *, similarity_threshold: float = STATE_SIMILARITY_THRESHOLD, window_size: int = DEFAULT_WINDOW_SIZE) -> None:
        self._detector = DoomLoopDetector(similarity_threshold=similarity_threshold, window_size=window_size)
        self._previous_entropy: Optional[float] = None

    def observe_turn(self, state: DefectState, *, constraint_names: Optional[Sequence[str]] = None) -> TurnResult:
        """Feed one turn and return a complete verdict including MUC steering.

        Enforces the Monotonic Progress Invariant ``E(s_{k+1}) <= E(s_k)`` against the
        immediately preceding turn; any rise triggers :attr:`rollback_triggered`.  When
        a doom loop is detected and named constraints were supplied, a Minimal Unsatisfiable
        Core is extracted from those constraints and rendered as a steering prompt.
        """
        detector_observation = self._detector.observe(state)

        monotonic_violation = False
        if self._previous_entropy is not None:
            monotonic_violation = detector_observation.entropy > (self._previous_entropy + MONOTONIC_EPSILON)

        steering_prompt: Optional[str] = None
        if detector_observation.doom_loop_detected and constraint_names:
            core_indices = minimal_unsatisfiable_core(
                Minisat(), only_indices=[i for i, name in enumerate(constraint_names)]
            )
            if core_indices is not None:
                steering_prompt = MucSteeringAdvisor.build_prompt(core_indices, list(constraint_names))

        result = TurnResult(
            state=state,
            entropy=detector_observation.entropy,
            monotonic_violation=monotonic_violation,
            rollback_triggered=monotonic_violation,
            doom_loop_detected=detector_observation.doom_loop_detected,
            similar_to_step=detector_observation.similar_to_step,
            steering_prompt=steering_prompt,
        )
        self._previous_entropy = detector_observation.entropy
        return result

    def reset(self) -> None:
        """Clear the rolling history and forget the previous-turn entropy baseline."""
        self._detector = DoomLoopDetector(similarity_threshold=self._detector._similarity_threshold, window_size=self._detector._window_size)  # type: ignore[attr-defined]
        self._previous_entropy = None


# ---------------------------------------------------------------------------
# Public symbol table.
# ---------------------------------------------------------------------------

__all__ = [
    "ConstraintClause",
    "DEFAULT_WINDOW_SIZE",
    "DefectState",
    "MUC_MAX_CLAUSES",
    "MucSteeringAdvisor",
    "MONOTONIC_EPSILON",
    "Minisat",
    "Observation",
    "STATE_SIMILARITY_THRESHOLD",
    "TurnResult",
    "ACTLOEngine",
    "defect_entropy",
    "minimal_unsatisfiable_core",
    "state_similarity",
]
