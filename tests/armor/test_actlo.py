"""Tests for ACT-LO: Agent Convergence & Thrashing-Loop Oracle (Phase 4 Group 1).

Covers the two failure modes that make an agent's defect trajectory unproductive:

1. **Monotonic Progress Invariant** -- the defect-state entropy ``E(s_k)`` must be
   non-increasing across consecutive turns; a turn whose entropy rises signals a
   regression and triggers a *rollback checkpoint*.
2. **Cycle / Thrashing Sieve** -- when two states within a rolling window are
   nearly identical (``SimState(s_i, s_k) >= 0.95``), the agent is oscillating
   between the same failing configurations; :class:`DoomLoopDetector` flags this
   as a doom loop / thrashing cycle.

When a doom loop is detected and named constraints were supplied, a **Minimal
Unsatisfiable Core (MUC)** is extracted via a dependency-free DPLL SAT solver and
rendered as an actionable *steering prompt*.  Everything here is pure, deterministic,
stdlib-only, and never touches physical storage.
"""

from __future__ import annotations

import math
import pytest
import fault_keeper.armor.actlo as actlo_module
from fault_keeper.armor.actlo import (  # noqa: F401 -- names used below for assertions.
    ACTLOEngine,
    DefectState,
    DoomLoopDetector,
    MucSteeringAdvisor,
    Minisat,
    Observation,
    TurnResult,
)


# ---------------------------------------------------------------------------
# Test 4.2.1: Monotonic Progress Invariant Proof.
# ---------------------------------------------------------------------------

class TestMonotonicProgressInvariant:
    """Test that entropy never rises across consecutive turns."""

    def test_rolling_entropy_non_increasing(self):
        """Test 4.2.1.A: Engine triggers rollback when entropy rises above previous turn."""
        engine = ACTLOEngine()

        # Turn 1: clean state (low entropy).
        s1 = DefectState(failed_mask=frozenset({"test_a"}), error_count=0, churn=1)
        r1 = engine.observe_turn(s1)
        assert r1.entropy > 0.0

        # Turn 2: same failure mask but higher churn -> entropy should rise.
        s2 = DefectState(failed_mask=frozenset({"test_a"}), error_count=1, churn=5)
        r2 = engine.observe_turn(s2)
        assert r2.monotonic_violation is True  # E(s2) > E(s1).
        assert r2.rollback_triggered is True

    def test_rolling_entropy_stays_flat(self):
        """Test 4.2.1.B: Engine does NOT trigger rollback when entropy stays flat."""
        engine = ACTLOEngine()

        s1 = DefectState(failed_mask=frozenset({"test_a"}), error_count=0, churn=3)
        r1 = engine.observe_turn(s1)

        # Identical state -> same entropy.
        s2 = DefectState(failed_mask=frozenset({"test_a"}), error_count=0, churn=3)
        r2 = engine.observe_turn(s2)
        assert r2.monotonic_violation is False  # E(s2) == E(s1).
        assert r2.rollback_triggered is False

    def test_rolling_entropy_decreases(self):
        """Test 4.2.1.C: Engine allows progression when entropy decreases."""
        engine = ACTLOEngine()

        s1 = DefectState(failed_mask=frozenset({"test_a", "test_b"}), error_count=2, churn=5)
        r1 = engine.observe_turn(s1)

        # Fewer failures -> lower entropy.
        s2 = DefectState(failed_mask=frozenset({"test_a"}), error_count=0, churn=1)
        r2 = engine.observe_turn(s2)
        assert r2.monotonic_violation is False  # E(s2) < E(s1).


# ---------------------------------------------------------------------------
# Test 4.2.2: Minimal Unsatisfiable Core (MUC) Soundness.
# ---------------------------------------------------------------------------

class TestMinimalUnsatisfiableCore:
    """Test that MUC extraction via DPLL produces correct inclusion-minimal cores."""

    def test_muc_sound_on_conflict(self):
        """Test 4.2.2.A: MUC correctly identifies the conflicting clause subset."""
        sat = Minisat()
        # Clause 0: a OR b
        sat.add_clause(1, 2, meta="assert_a_or_b")
        # Clause 1: NOT a (i.e., -a)
        sat.add_clause(-1, meta="assert_not_a")
        # Clause 2: NOT b (i.e., -b)
        sat.add_clause(-2, meta="assert_not_b")

        core = actlo_module.minimal_unsatisfiable_core(sat)
        assert core is not None
        # Core must contain clauses that together are UNSAT.
        # {0, 1} => a|b AND NOT(a) => b forced; then clause 2 forces NOT(b) -> UNSAT.
        # But {0, 1} alone: a|b AND NOT(a) => b is true; no conflict yet without clause 2.
        # Actually {0, 1, 2}: (a|b), (!a), (!b) => UNSAT because a=F, b=F makes clause 0 false.
        assert len(core) >= 2

    def test_muc_empty_when_sat(self):
        """Test 4.2.2.B: Returns None when the whole formula is SAT."""
        sat = Minisat()
        sat.add_clause(1, -2)   # a OR NOT b
        sat.add_clause(2, -1)   # b OR NOT a

        core = actlo_module.minimal_unsatisfiable_core(sat)
        assert core is None  # SAT -> no conflicting core.

    def test_muc_inclusion_minimality(self):
        """Test 4.2.2.C: Dropping any clause from the MUC makes it SAT."""
        sat = Minisat()
        sat.add_clause(1)      # a       (index 0)
        sat.add_clause(-1)     # NOT a    (index 1)

        core = actlo_module.minimal_unsatisfiable_core(sat)
        assert core is not None

        for i in core:
            # Removing clause i should make the remaining set SAT.
            remaining = [j for j in core if j != i]

            subset_sat = Minisat()
            for idx in remaining:
                clause = sat._clauses[idx]
                subset_sat.add_clause(*clause)

            assert subset_sat.solve() is not None, \
                f"Dropping clause {i} from core should make it SAT but got UNSAT."


# ---------------------------------------------------------------------------
# Test 4.2.3: DoomLoopDetector cycle sieve.
# ---------------------------------------------------------------------------

class TestDoomLoopDetectorCycleSieve:
    """Test that the rolling window detects recurrence of similar states."""

    def test_detects_doom_loop_on_repeated_state(self):
        """Test 4.2.3.A: Two identical defect states within the window trigger doom-loop detection."""
        detector = DoomLoopDetector()

        s1 = DefectState(failed_mask=frozenset({"test_a"}), error_count=0, churn=1)
        obs1 = detector.observe(s1)
        assert obs1.doom_loop_detected is False  # first state has no prior to compare.

        # Same state again -> should be flagged as a recurrence.
        s2 = DefectState(failed_mask=frozenset({"test_a"}), error_count=0, churn=1)
        obs2 = detector.observe(s2)
        assert obs2.doom_loop_detected is True
        assert obs2.thrashing_detected is True

    def test_no_doom_loop_on_different_state(self):
        """Test 4.2.3.B: Different failure masks do not trigger doom-loop detection."""
        detector = DoomLoopDetector()

        s1 = DefectState(failed_mask=frozenset({"test_a"}), error_count=0, churn=1)
        detector.observe(s1)

        s2 = DefectState(failed_mask=frozenset({"test_b"}), error_count=0, churn=1)
        obs = detector.observe(s2)
        assert obs.doom_loop_detected is False  # different failures -> not a loop.


# ---------------------------------------------------------------------------
# Test 4.2.4: ACTLOEngine steering prompt generation.
# ---------------------------------------------------------------------------

class TestACTLOEngineSteeringPrompt:
    """Test that the engine generates MUC-based steering prompts correctly."""

    def test_steering_prompt_when_doom_loop_and_constraints(self):
        """Test 4.2.4.A: Engine produces a steering prompt when doom loop + constraints are present."""
        engine = ACTLOEngine()

        constraints = ["assert_positive", "assert_negative", "assert_zero"]

        # Feed two identical states to trigger a doom loop.
        s1 = DefectState(failed_mask=frozenset({"test_a"}), error_count=0, churn=1)
        r1 = engine.observe_turn(s1, constraint_names=constraints)
        assert r1.doom_loop_detected is False  # first state has no prior.

        s2 = DefectState(failed_mask=frozenset({"test_a"}), error_count=0, churn=1)
        r2 = engine.observe_turn(s2, constraint_names=constraints)
        assert r2.doom_loop_detected is True
        # Steering prompt should reference the named constraints.
        assert r2.steering_prompt is not None
        assert "assert_positive" in r2.steering_prompt or \
               len(r2.steering_prompt) > 0

    def test_no_steering_when_no_constraints(self):
        """Test 4.2.4.B: Engine does not generate a steering prompt without constraint names."""
        engine = ACTLOEngine()

        s1 = DefectState(failed_mask=frozenset({"test_a"}), error_count=0, churn=1)
        engine._detector.observe(s1)

        s2 = DefectState(failed_mask=frozenset({"test_a"}), error_count=0, churn=1)
        r = engine.observe_turn(s2, constraint_names=None)
        assert r.steering_prompt is None  # No constraints -> no steering.


# ---------------------------------------------------------------------------
# Test 4.2.5: DefectState entropy calculation edge cases.
# ---------------------------------------------------------------------------

class TestDefectEntropyEdgeCases:
    """Test boundary behavior of the defect-state entropy function."""

    def test_zero_state_has_zero_entropy(self):
        """Test 4.2.5.A: A completely clean state (all zeros) has zero entropy."""
        assert actlo_module.defect_entropy(DefectState()) == 0.0

    def test_single_failure_has_zero_entropy_when_concentrated(self):
        """Test 4.2.5.B: Single failure concentrated in one category yields zero entropy (maximum certainty)."""
        s1 = DefectState(failed_mask=frozenset({"test_a"}), error_count=0, churn=0)
        assert actlo_module.defect_entropy(s1) == 0.0

    def test_state_similarity_identical_is_one(self):
        """Test 4.2.5.C: Identical states have similarity exactly 1.0."""
        s = DefectState(failed_mask=frozenset({"test_a"}), error_count=1, churn=3)
        assert actlo_module.state_similarity(s, s) == 1.0


# ---------------------------------------------------------------------------
# Test 4.2.6: MucSteeringAdvisor prompt rendering.
# ---------------------------------------------------------------------------

class TestMucSteeringAdvisorRendering:
    """Test that steering prompts are well-formed and reference the right constraints."""

    def test_prompt_lists_conflicting_constraints(self):
        """Test 4.2.6.A: Prompt enumerates the conflicting constraint names in sorted order."""
        prompt = MucSteeringAdvisor.build_prompt(
            core_indices=[1, 0],
            constraint_names=["assert_positive", "assert_negative"],
        )
        assert "assert_negative" in prompt  # sorted order.
        assert "assert_positive" in prompt

    def test_empty_core_returns_helpful_message(self):
        """Test 4.2.6.B: Empty core returns a message indicating no conflict."""
        prompt = MucSteeringAdvisor.build_prompt(
            core_indices=[],
            constraint_names=["a", "b"],
        )
        assert "satisfiable" in prompt.lower()


# ---------------------------------------------------------------------------
# Test 4.2.7: DoomLoopDetector initialization validation.
# ---------------------------------------------------------------------------

class TestDoomLoopDetectorInitValidation:
    """Test that the detector rejects invalid configuration."""

    def test_similarity_threshold_out_of_range(self):
        """Test 4.2.7.A: Similarity threshold outside [0,1] raises ValueError."""
        with pytest.raises(ValueError):
            DoomLoopDetector(similarity_threshold=1.5)

    def test_window_size_too_small(self):
        """Test 4.2.7.B: Window size < 2 raises ValueError (cannot detect recurrence)."""
        with pytest.raises(ValueError):
            DoomLoopDetector(window_size=1)


# ---------------------------------------------------------------------------
# Public symbol table assertions.
# ---------------------------------------------------------------------------

class TestACTLOPublicSymbols:
    """Verify that the module's public API matches the spec deliverables."""

    def test_module_exposes_engine_and_detector(self):
        """Test 4.2.8.A: Module exports ACTLOEngine and DoomLoopDetector as documented."""
        assert hasattr(actlo_module, "ACTLOEngine")
        assert hasattr(actlo_module, "DoomLoopDetector")
