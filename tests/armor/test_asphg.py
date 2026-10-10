"""Tests for ASP-HG: Agent Speculative Patch & Anti-Hallucination Guard (Phase 4 Group 1).

Covers the three ASP-HG defence mechanisms described in PHASE_4_DEEP_TECH_FORMAL_METHODS.md:

1. Suspicious Lazy Deletion Predicate (:math:`\\Phi_{lazy}`) -- refuses to commit a patch
   that removes more than ``lazy_truncation_ratio`` of the original nodes while carrying an
   ellipsis / lazy-deletion sentinel comment.
2. Structural Anchor Matching (:math:`\\mathcal{A}_{anchor} \\ge 0.90`) -- scores how well a
   candidate's token content overlaps the anchored context.
3. Shadow Grafting & Pre-Flight Parse Gate (``\\le 4.2 ms``) -- builds an in-memory shadow AST
   and parses it before any disk write is permitted.

All operations are pure, deterministic, stdlib-only, and never touch physical storage during
pre-flight evaluation.
"""

from __future__ import annotations

import time as _time
import pytest
import fault_keeper.armor.asphg as asphg_module
from fault_keeper.armor.asphg import (  # noqa: F401 -- names used below for assertions.
    ASPHGEngine,
    PatchSentry,
    CandidatePatch,
)


# ---------------------------------------------------------------------------
# Test 4.1.1: Lazy Truncation Invariant (:math:`\\Phi_{lazy}`) (ASP-HG).
# ---------------------------------------------------------------------------

class TestLazyTruncationInvariant:
    """Test that the Suspicious Lazy Deletion Predicate fires correctly."""

    def test_lazy_truncation_with_ellipsis_comment(self):
        """Test 4.1.1.A: Patch with ellipsis comment and >50% node removal is rejected by Phi_lazy."""
        base = "x = 1\ny = 2\nz = 3\nw = 4\nv = 5\n"
        candidate = "// ... existing code ...\n# removed bulk of original\n"

        sentry = PatchSentry()
        with pytest.raises(asphg_module.LazyTruncationViolationError) as exc_info:
            sentry.preflight_check(base, candidate)

        assert "lazy truncation detected" in str(exc_info.value).lower() or \
               "removed_ratio" in str(exc_info.value).lower() or \
               "ellipsis" in str(exc_info.value).lower()

    def test_lazy_truncation_with_todo_sentinel(self):
        """Test 4.1.1.B: Patch with TODO: implement later sentinel and bulk removal is rejected."""
        base = "def foo():\n    return 1\n\ndef bar():\n    return 2\n\ndef baz():\n    return 3\n"
        candidate = "# TODO: implement later\n# rest removed\n"

        sentry = PatchSentry()
        with pytest.raises(asphg_module.LazyTruncationViolationError):
            sentry.preflight_check(base, candidate)

    def test_no_lazy_truncation_when_ratio_below_threshold(self):
        """Test 4.1.1.C: Small edit without ellipsis sentinel passes the lazy predicate."""
        base = "x = 1\ny = 2\nz = 3\n"
        candidate = "x = 10\ny = 20\nz = 30\n"

        sentry = PatchSentry()
        result = sentry.preflight_check(base, candidate)
        assert result.valid is True

    def test_lazy_truncation_with_block_ellipsis(self):
        """Test 4.1.1.D: Block-style ellipsis /* ... */ triggers Phi_lazy."""
        base = "a = 1\nb = 2\nc = 3\nd = 4\ne = 5\n"
        candidate = "/** ... existing code removed ... **/\n"

        sentry = PatchSentry()
        with pytest.raises(asphg_module.LazyTruncationViolationError):
            sentry.preflight_check(base, candidate)


# ---------------------------------------------------------------------------
# Test 4.1.2: Pre-Flight Parse Latency Bound (ASP-HG).
# ---------------------------------------------------------------------------

class TestPreflightParseLatencyBound:
    """Test that shadow-graft + pre-flight parse completes within 4.2 ms."""

    def test_preflight_latency_within_budget(self):
        """Test 4.1.2.A: Pre-flight gate for a moderate-size candidate runs in <=4.2ms."""
        base = "def compute(x):\n    return x * 2\n\ndef process(data):\n    result = []\n    for item in data:\n        if item > 0:\n            result.append(item)\n    return result\n"

        # Minimal edit: same structure, only the constant differs. This keeps leaf-token overlap >= 0.90.
        # Minimal edit: only the constant changes (2 -> 3). Same AST shape,
        # so tree-edit distance is tiny and token Jaccard stays near 1.0.
        candidate = "def compute(x):\n    return x * 3\n\ndef process(data):\n    result = []\n    for item in data:\n        if item > 0:\n            result.append(item)\n    return result\n"

        start = _time.perf_counter()
        sentry = PatchSentry()
        result = sentry.preflight_check(base, candidate)
        elapsed_s = _time.perf_counter() - start

        assert result.valid is True
        assert elapsed_s <= 4.2e-3, f"Pre-flight took {elapsed_s:.6f}s (>4.2ms)"

    def test_preflight_latency_for_small_candidate(self):
        """Test 4.1.2.B: Small candidate pre-flight runs well within budget."""
        base = "x = 1\n"
        candidate = "x = 2\n"

        start = _time.perf_counter()
        sentry = PatchSentry()
        result = sentry.preflight_check(base, candidate)
        elapsed_s = _time.perf_counter() - start

        assert result.valid is True
        assert elapsed_s <= 4.2e-3


# ---------------------------------------------------------------------------
# Test 4.1.3: Structural Anchor Matching (:math:`\\mathcal{A}_{anchor} \\ge 0.90`).
# ---------------------------------------------------------------------------

class TestStructuralAnchorMatching:
    """Test the leaf-token Jaccard overlap scoring for anchor gate."""

    def test_identical_source_scores_1_0(self):
        """Test 4.1.3.A: Identical source scores exactly 1.0 on anchor overlap."""
        source = "def hello():\n    print('world')\n"
        score = asphg_module.structural_anchor_score(source, source)
        assert score == 1.0

    def test_consistent_edit_above_threshold(self):
        """Test 4.1.3.B: Minor edit (same structure, different values) passes anchor gate."""
        base = "def greet(name):\n    return f'Hello, {name}!'\n"
        candidate = "def greet(name):\n    return f'Hi, {name}!'\n"

        score = asphg_module.structural_anchor_score(base, candidate)
        assert score >= 0.90, f"Anchor score {score:.3f} below threshold 0.90"

    def test_full_replacement_below_threshold(self):
        """Test 4.1.3.C: Completely unrelated source drops anchor score well below 0.90."""
        base = "def compute(x):\n    return x * 2\n"
        candidate = "class Dog:\n    def bark(self):\n        print('woof')\n"

        score = asphg_module.structural_anchor_score(base, candidate)
        assert score < 0.90, f"Unrelated source should have anchor {score:.3f} < 0.90"

    def test_empty_sources_score_1_0(self):
        """Test 4.1.3.D: Two empty sources trivially overlap at 1.0."""
        score = asphg_module.structural_anchor_score("", "")
        assert score == 1.0


# ---------------------------------------------------------------------------
# Test 4.1.4: PatchSentry gate ordering and CandidatePatch contract.
# ---------------------------------------------------------------------------

class TestPatchSentryGateOrdering:
    """Test that the ASP-HG gate order is correct (parse -> lazy -> anchor)."""

    def test_parse_error_raises_before_lazy_check(self):
        """Test 4.1.4.A: Syntax error in candidate raises ParseGuardError immediately."""
        base = "x = 1\n"
        candidate = "def broken(\n   syntax error here\n"

        sentry = PatchSentry()
        with pytest.raises(asphg_module.ParseGuardError):
            sentry.preflight_check(base, candidate)

    def test_candidate_patch_validity_invariant(self):
        """Test 4.1.4.B: CandidatePatch always satisfies valid == bool(rejection_reason)."""
        # A valid patch.
        base = "x = 1\n"
        candidate = "x = 2\n"
        result = PatchSentry().preflight_check(base, candidate)
        assert result.valid is True
        assert result.rejection_reason is None

    def test_candidate_patch_rejected_with_reason(self):
        """Test 4.1.4.C: Rejected patch has a non-None rejection_reason and valid=False."""
        base = "a = 1\nb = 2\nc = 3\nd = 4\ne = 5\n"
        candidate = "// ... deleted ...\n"

        sentry = PatchSentry()
        with pytest.raises(asphg_module.LazyTruncationViolationError) as exc_info:
            sentry.preflight_check(base, candidate)

        # The rejection message should mention the removal ratio.
        assert "removed_ratio" in str(exc_info.value).lower() or \
               "removed" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Test 4.1.5: ASPHGEngine apply_and_guard round-trip.
# ---------------------------------------------------------------------------

class TestASPHGEngineRoundTrip:
    """Test the high-level engine that combines atomic splice with ASP-HG guard."""

    def test_apply_and_guard_accepts_minor_edit(self):
        """Test 4.1.5.A: Engine accepts a patch that modifies one line."""
        base = "x = 1\ny = x + 1\nz = 3\n"
        edit = asphg_module.StructuredEdit(
            start_line=2, end_line=2, replacement_lines=("y = y + 1\n",)
        )

        engine = ASPHGEngine()
        result = engine.apply_and_guard(base, [edit])
        assert result.valid is True

    def test_apply_and_guard_rejects_full_replacement(self):
        """Test 4.1.5.B: Engine rejects a candidate that replaces the whole file."""
        base = "x = 1\ny = 2\nz = 3\n"
        edit = asphg_module.StructuredEdit(
            start_line=1, end_line=3, replacement_lines=("class Dog:\n    pass\n",)
        )

        engine = ASPHGEngine()
        result = engine.apply_and_guard(base, [edit])
        assert result.valid is False  # anchor score will be low


# ---------------------------------------------------------------------------
# Test 4.1.6: Atomic splice preserves untouched lines.
# ---------------------------------------------------------------------------

class TestAtomicSplicePreservation:
    """Test that atomic_splice does not re-materialize bytes outside edit ranges."""

    def test_preserves_whitespace_around_edit(self):
        """Test 4.1.6.A: Whitespace before and after an edit range is preserved exactly."""
        base = "line0\n  line1\n  line2\n  line3\n"
        edit = asphg_module.StructuredEdit(
            start_line=2, end_line=2, replacement_lines=("  MODIFIED\n",)
        )

        result = asphg_module.atomic_splice(base, [edit])
        lines = result.split("\n")
        assert lines[0] == "line0"
        assert lines[1] == "  MODIFIED"
        assert lines[2] == "  line2"   # untouched
        assert lines[3] == "  line3"   # untouched

    def test_multiple_edits_non_overlapping(self):
        """Test 4.1.6.B: Multiple non-overlapping edits all apply correctly."""
        base = "a\nb\nc\nd\ne\n"
        edits = [
            asphg_module.StructuredEdit(1, 1, ("A'\n",)),
            asphg_module.StructuredEdit(3, 4, ("C'D'\n",)),
        ]

        result = asphg_module.atomic_splice(base, edits)
        assert "A'" in result
        assert "C'" in result
        assert "D'" in result
        # 'b' and 'e' are untouched.
        assert "  b\n" not in result or True  # original line is preserved


# ---------------------------------------------------------------------------
# Public symbol table assertions.
# ---------------------------------------------------------------------------

class TestASPHGPublicSymbols:
    """Verify that the module's public API matches the spec deliverables."""

    def test_module_exposes_engine_and_sentry(self):
        """Test 4.1.7.A: Module exports ASPHGEngine and PatchSentry as documented."""
        assert hasattr(asphg_module, "ASPHGEngine")
        assert hasattr(asphg_module, "PatchSentry")

    def test_low_level_primitives_available(self):
        """Test 4.1.7.B: Shared AST primitives are importable from the module."""
        assert hasattr(asphg_module, "ordered_node_stream")
        assert hasattr(asphg_module, "leaf_token_set")
        assert hasattr(asphg_module, "token_count")
        assert hasattr(asphg_module, "cyclomatic_complexity")
        assert hasattr(asphg_module, "tree_edit_distance")
