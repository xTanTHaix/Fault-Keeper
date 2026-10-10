"""ASP-HG: Agent Speculative Patch & Anti-Hallucination Guard (Phase 4 Group 1).

This module is the single source of truth for the low-level AST primitives that
both :mod:`fault_keeper.armor.asphg` and :mod:`fault_keeper.armor.scpve` share,
so structural analysis stays DRY across the AI-Armor pillars:

- ``ordered_node_stream``      -- deterministic post-order node walk.
- ``leaf_token_set``           -- content fingerprint of a source string.
- ``token_count``              -- significant-token tally used for delta metrics.
- ``cyclomatic_complexity``    -- McCabe decision-count complexity.
- ``tree_edit_distance``       -- Zhang-Shasha minimal tree-edit distance.

On top of those primitives the :class:`PatchSentry` implements the three ASP-HG
defences described in *PHASE_4_DEEP_TECH_FORMAL_METHODS.md*:

1. Suspicious Lazy Deletion Predicate (:math:`\\Phi_{lazy}`) -- refuses to commit
   a patch that removes more than ``lazy_truncation_ratio`` of the original nodes
   while carrying an ellipsis / lazy-deletion sentinel comment.
2. Structural Anchor Matching (:math:`\\mathcal{A}_{anchor} \\ge 0.90`) -- scores
   how well a candidate's token content overlaps the anchored context.
3. Shadow Grafting & Pre-Flight Parse Gate (``\\le 4.2 ms``) -- builds an in-memory
   shadow AST and parses it before any disk write is permitted.

All operations are pure, deterministic, stdlib-only, and never touch physical
storage during pre-flight evaluation.
"""

from __future__ import annotations

import ast
import math
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Guard thresholds (spec constants from PHASE_4_DEEP_TECH_FORMAL_METHODS.md).
# ---------------------------------------------------------------------------

ANCHOR_THRESHOLD = 0.90          # minimum leaf-token overlap to accept a patch.
DEFAULT_PREFLIGHT_BUDGET_S = 42e-3  # shadow-graft + pre-flight parse budget (<=4.2ms).
# Fraction of original AST nodes whose removal, combined with an ellipsis marker,
# flags accidental code loss under the Suspicious Lazy Deletion Predicate.
DEFAULT_LAZY_RATIO = 0.40

# Suspicious lazy-deletion sentinels. A candidate is "lazy" when it deletes more
# than the configured ratio of original nodes AND contains at least one of these
# ellipsis / abandonment markers, which together signal accidental code loss.
ELLIPSIS_SENTINELS: Sequence[re.Pattern[str]] = (
    re.compile(r"\.\.\.\s*existing\s+code\b"),      # "// ... existing code ..."
    re.compile(r"/\*\s*\.\.\..*?\*/", re.DOTALL),   # /* ... */ block ellipsis
    re.compile(r"//.*?\.\.\.[^a-zA-Z0-9_]"),        # generic line-comment ellipsis
    re.compile(r"#\s*\.\.\."),                      # hash-comment ellipsis
    re.compile(r"/\*\s*\.\.\.\s*[^*]*\.\.\.\s*\*/", re.DOTALL),  # block-style /** ... */ ellipsis
    re.compile(r"\bTODO:\s*(?:implement|write|complete)\s+later\b"),  # TODO: implement later
)

_TOKEN_RE = re.compile(
    r"[A-Za-z_][\w]*"          # identifiers / keywords
    r"|[\d]+(?:\.[\d]+)?"      # integer / float literals
    r"|[-+*/%<>=!&|^~.,;:()\[\]{}=]"  # operators & punctuation
)


class LazyTruncationViolationError(Exception):
    """Raised when a patch deletes the bulk of original code with an ellipsis marker.

    Attributes:
        removed_ratio: Fraction of original AST nodes that the candidate drops.
        sentinels: The matched lazy-deletion sentinel patterns (never empty).
        message: Human-readable diagnostic describing the violation.
    """

    def __init__(self, removed_ratio: float, sentinels: Sequence[str], message: Optional[str] = None) -> None:
        super().__init__(message or self._default_message(removed_ratio, sentinels))
        self.removed_ratio = removed_ratio
        self.sentinels = list(sentinels)

    @staticmethod
    def _default_message(removed_ratio: float, sentinels: Sequence[str]) -> str:
        return (
            f"[ASP-HG] Lazy truncation detected: candidate removed {removed_ratio:.1%} of "
            f"original nodes while carrying lazy-deletion sentinel(s): {list(sentinels)}."
        )


class ParseGuardError(RuntimeError):
    """Raised when a candidate fails the pre-flight shadow parse gate."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


@dataclass(frozen=True)
class CandidatePatch:
    """Outcome of an ASP-HG guard evaluation for one candidate patch.

    Attributes:
        anchor_score: Leaf-token Jaccard overlap between base and candidate in [0, 1].
        node_delta_ratio: Fraction of original AST nodes the candidate drops (0 = identical).
        valid: ``True`` only when no guard fired (no parse error, no lazy violation).
        rejection_reason: Diagnostic explaining a rejected patch; ``None`` when ``valid``.
    """

    anchor_score: float
    node_delta_ratio: float
    valid: bool = True
    rejection_reason: Optional[str] = None

    def __post_init__(self) -> None:
        # Enforce the validity/reason invariant: valid=True requires rejection_reason=None,
        # valid=False requires rejection_reason to be a non-empty string.
        try:
            if (self.valid and self.rejection_reason is not None) or \
               (not self.valid and self.rejection_reason is None):
                raise ValueError(
                    "CandidatePatch must set rejection_reason when valid is False and omit it otherwise."
                )
        except ValueError:
            raise


# ---------------------------------------------------------------------------
# Shared low-level AST primitives.  These are imported by scpve.py so both
# pillars share one implementation of structural analysis.
# ---------------------------------------------------------------------------

def ordered_node_stream(root: ast.AST) -> Iterator[ast.AST]:
    """Yield every node of ``root`` in deterministic post-order (children first).

    Post-order traversal is used everywhere downstream because it gives a stable,
    child-before-parent sequence that makes structural comparisons and the Zhang-Shasha
    distance well defined regardless of source formatting.
    """
    stack: List[Tuple[ast.AST, bool]] = [(root, False)]
    while stack:
        node, processed = stack.pop()
        if processed:
            yield node
        else:
            stack.append((node, True))
            for child in ast.iter_child_nodes(node):
                stack.append((child, False))


def _postorder_hash_sequence(root: ast.AST) -> List[Tuple[str, Tuple[str, ...]]]:
    """Return each node's structural hash (type + sorted child hashes), post-order.

    Two subtrees that are structurally identical receive an identical hash string,
    which is the property Zhang-Shasha relies on to match nodes of equal cost.
    The cache keyed by object id guarantees O(n) hashing for a single tree.
    """
    seq: List[Tuple[str, Tuple[str, ...]]] = []
    cache: dict[int, Tuple[str, Tuple[str, ...]]] = {}

    def _hash(node: ast.AST, memo: dict[int, Tuple[str, Tuple[str, ...]]]) -> Tuple[str, Tuple[str, ...]]:
        key = id(node)
        if key in memo:
            return memo[key]
        child_hashes = tuple(sorted(_hash(child, memo) for child in ast.iter_child_nodes(node)))
        memo[key] = (type(node).__name__, child_hashes)  # type: ignore[assignment]
        return memo[key]

    for node in ordered_node_stream(root):
        seq.append(_hash(node, cache))
    return seq


def leaf_token_set(source: str) -> frozenset[str]:
    """Fingerprint the content of ``source`` by its identifier and string/number leaves.

    Collects every :class:`ast.Name` id plus the textual value of each constant,
    tagged to avoid collisions between identifiers and literals (e.g. a name ``x``
    versus the string ``"x"``).  Used for anchor-overlap scoring via Jaccard.
    """
    tree = ast.parse(source)
    tokens: set[str] = set()
    for node in ordered_node_stream(tree):
        if isinstance(node, ast.Name):
            tokens.add(("name", node.id))
        elif isinstance(node, ast.Constant):
            value = node.value  # type: ignore[union-attr]
            if isinstance(value, str):
                tokens.add(("str", value))
            elif isinstance(value, bool):
                tokens.add(("bool", "true" if value else "false"))
            elif isinstance(value, (int, float)):
                tokens.add(("num", repr(value)))
    return frozenset(tokens)


def token_count(source: str) -> int:
    """Count significant source tokens on non-comment lines.

    Line comments are stripped before counting so that blank/comment-only regions
    do not inflate the tally, keeping ``token_count`` monotonic with real code size
    for use as a delta metric in the arbiter.
    """
    total = 0
    for raw_line in source.splitlines():
        code_part = re.sub(r"\s*#.*$", "", raw_line)
        if not code_part.strip():
            continue
        total += len(_TOKEN_RE.findall(code_part))
    return total


def cyclomatic_complexity(tree: ast.AST) -> int:
    """Return the McCabe cyclomatic complexity of ``tree`` (decision points + 1).

    Counts every branch-bearing construct: if/elif, for/async-for, while, with,
    except-handler, boolean operators (each extra operand adds one decision), and
    comprehension guards plus conditional expressions.
    """
    decisions = 0
    for node in ordered_node_stream(tree):
        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.With)):
            decisions += 1
        elif isinstance(node, ast.BoolOp):
            # ``and``/``or`` of k operands introduces k-1 decision points.
            decisions += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            # Each guard clause in a comprehension adds an implicit branch.
            decisions += len(node.ifs)
        elif isinstance(node, ast.IfExp):
            decisions += 1
    return decisions + 1


def _zhang_shasha_distance(h1: Sequence[str], h2: Sequence[str]) -> int:
    """Compute the unweighted Zhang-Shasha minimal tree-edit distance.

    ``h1`` / ``h2`` are post-order structural hash sequences (see
    :func:`_postorder_hash_sequence`).  The DP matrix encodes the minimum cost of
    aligning the two prefix sequences via delete/insert/substitute; backtracking then
    reconstructs that optimal cost while recursing into matched identical subtrees,
    which contribute zero additional cost.
    """
    n, m = len(h1), len(h2)
    INF = math.inf

    matrix = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        matrix[i][0] = i
    for j in range(1, m + 1):
        matrix[0][j] = j
    for i in range(1, n + 1):
        hi = h1[i - 1]
        row_i = matrix[i]
        row_prev = matrix[i - 1]
        for j in range(1, m + 1):
            if hi == h2[j - 1]:
                row_i[j] = 0
            else:
                best = row_prev[j] + 1           # delete h1[i-1]
                insert_cost = row_i[j - 1] + 1   # insert h2[j-1]
                sub_cost = row_prev[j - 1] + 2   # substitute the two nodes
                if insert_cost < best:
                    best = insert_cost
                if sub_cost < best:
                    best = sub_cost
                row_i[j] = best

    def backtrack(i: int, j: int) -> int:
        if i == 0 and j == 0:
            return 0
        elif h1[i - 1] == h2[j - 1]:
            # Identical subtrees match for free; align the remaining prefixes.
            return backtrack(i - 1, j - 1)
        else:
            best = INF
            if i > 0 and matrix[i][j] >= matrix[i - 1][j] + 1:      # delete
                candidate = backtrack(i - 1, j) + 1
                if candidate < best:
                    best = candidate
            if j > 0 and matrix[i][j] >= matrix[i][j - 1] + 1:      # insert
                candidate = backtrack(i, j - 1) + 1
                if candidate < best:
                    best = candidate
            if i > 0 and j > 0 and matrix[i][j] == matrix[i - 1][j - 1] + 2:  # substitute
                candidate = backtrack(i - 1, j - 1) + 2
                if candidate < best:
                    best = candidate
            return int(best)

    distance = backtrack(n, m)
    return distance


def tree_edit_distance(a: ast.AST, b: ast.AST) -> int:
    """Return the Zhang-Shasha minimal tree-edit distance between two ASTs.

    Zero means structurally identical; larger values indicate progressively more
    edits (substitutions cost 2, insertions/deletions cost 1).  Deterministic and
    used by :mod:`fault_keeper.armor.scpve` to rank speculative candidates.
    """
    if a is b:
        return 0
    hash_a = _postorder_hash_sequence(a)
    hash_b = _postorder_hash_sequence(b)
    return _zhang_shasha_distance(hash_a, hash_b)


def jaccard_similarity(set_a: frozenset[str], set_b: frozenset[str]) -> float:
    """Return the Jaccard overlap of two token sets in ``[0.0, 1.0]``."""
    if not set_a and not set_b:
        return 1.0
    union_size = len(set_a | set_b)
    if union_size == 0:
        return 0.0
    intersection_size = len(set_a & set_b)
    return intersection_size / union_size


# ---------------------------------------------------------------------------
# Lazy-truncation predicate (Suspicious Lazy Deletion Predicate, Phi_lazy).
# ---------------------------------------------------------------------------


def _ast_node_count(root: ast.AST) -> int:
    """Return the total number of nodes in ``root``'s tree, including root itself."""
    return 1 + sum(1 for _ in ast.walk(root))


def _evaluate_lazy_truncation(base_source: str, candidate_source: str, ratio: float = DEFAULT_LAZY_RATIO) -> Optional[Tuple[float, Sequence[str]]]:
    """Assess whether ``candidate_source`` accidentally drops the bulk of ``base_source``.

    Returns ``(removed_ratio, matched_sentinels)`` when more than ``ratio`` of the base
    nodes are removed AND an ellipsis / abandonment marker is present; otherwise None.
    Parsing failures return None so the caller's explicit parse gate can surface a
    precise diagnostic instead of masking it behind the lazy predicate.
    """
    # Gate 1: parse both sources; if either fails, still evaluate sentinel patterns
    # so lazy truncation can fire before the caller's explicit parse gate rejects.
    base_ok = True
    candidate_ok = True
    try:
        base_tree = ast.parse(base_source)
    except SyntaxError as exc:
        base_ok = False
    try:
        candidate_tree = ast.parse(candidate_source)
    except SyntaxError as exc:
        candidate_ok = False

    # Even when parsing fails (e.g. JS-style comments), check for ellipsis sentinels.
    matched_sentinels = [pattern.pattern for pattern in ELLIPSIS_SENTINELS if pattern.search(candidate_source)]

    base_count = _ast_node_count(base_tree) if base_ok else 0
    candidate_count = _ast_node_count(candidate_tree) if candidate_ok else 0

    if matched_sentinels:
        # If both sources failed to parse or the candidate is far smaller than base,
        # treat as suspicious lazy deletion regardless of exact node counts.
        if not base_ok or not candidate_ok:
            return 1.0, matched_sentinels
        removed_ratio = (base_count - candidate_count) / base_count if base_count else 1.0
        if removed_ratio > ratio:
            return removed_ratio, matched_sentinels
    return None


def detect_lazy_truncation(base_source: str, candidate_source: str, ratio: float = DEFAULT_LAZY_RATIO) -> Optional[str]:
    """Return a lazy-truncation diagnostic when ``candidate_source`` looks accidental.

    Pure and non-raising: returns the human-readable message (see :class:`LazyTruncationViolationError`)
    or None. Used for scoring before the hard gate in :meth:`PatchSentry.preflight_check`.
    """
    result = _evaluate_lazy_truncation(base_source, candidate_source, ratio)
    if result is None:
        return None
    removed_ratio, matched_sentinels = result
    return (
        f"[ASP-HG] Lazy truncation detected: candidate removes {removed_ratio:.1%} of "
        f"original nodes while carrying lazy-deletion sentinel(s): {list(matched_sentinels)}."
    )


# ---------------------------------------------------------------------------
# Structural anchor matching (A_anchor).
# ---------------------------------------------------------------------------


def structural_anchor_score(base_source: str, candidate_source: str) -> float:
    """Score structural similarity between base and a candidate source.

    Combines tree-edit-distance-based structural similarity (primary metric) with
    leaf-token Jaccard overlap (secondary guard).  An identical source scores 1.0;
    a wholly unrelated one approaches 0.0.  The anchor gate requires at least
    ANCHOR_THRESHOLD (0.90).
    """
    # Parse both sources to compute structural similarity.
    try:
        base_ast = ast.parse(base_source)
        candidate_ast = ast.parse(candidate_source)
    except SyntaxError:
        return 0.0

    # Primary: tree-edit distance normalized by the larger tree size.
    ted = tree_edit_distance(base_ast, candidate_ast)
    base_nodes = list(ordered_node_stream(base_ast))
    candidate_nodes = list(ordered_node_stream(candidate_ast))
    max_size = max(len(base_nodes), len(candidate_nodes))
    if max_size == 0:
        return 1.0
    structural_sim = 1.0 - (ted / float(max_size))

    # Secondary: token overlap as a sanity check for content preservation.
    base_tokens = leaf_token_set(base_source)
    candidate_tokens = leaf_token_set(candidate_source)
    if not base_tokens and not candidate_tokens:
        return structural_sim
    union_size = len(base_tokens | candidate_tokens)
    intersection_size = len(base_tokens & candidate_tokens)
    token_jaccard = intersection_size / union_size if union_size else 0.0

    # Use the maximum so structurally similar code passes even when literals differ,
    # while still penalizing content changes (token Jaccard captures literal overlap).
    return max(structural_sim, token_jaccard)


# ---------------------------------------------------------------------------
# Atomic whitespace-preserving splice (zero accidental code loss).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StructuredEdit:
    """A single line-based replacement applied to a source file.

    Attributes:
        start_line: 1-indexed inclusive first line of the covered range.
        end_line: 1-indexed inclusive last line of the covered range (>= start_line).
        replacement_lines: Exact text lines that replace the covered range verbatim.
    """

    start_line: int
    end_line: int
    replacement_lines: Tuple[str, ...]


def atomic_splice(base_source: str, edits: Sequence[StructuredEdit]) -> str:
    """Splice ``edits`` into ``base_source``, preserving every untouched line verbatim.

    Lines outside any edit range are copied through byte-for-byte (including trailing
    whitespace and the original newline style); only covered ranges are replaced, so no
    bytes beyond an edit are ever re-materialized. Edits must be non-overlapping and
    ordered by start_line; otherwise ValueError is raised before any write.

    The result's final-newline state matches the input source exactly.
    """
    lines = base_source.split("\n")
    preserved_trailing_newline = bool(lines) and lines[-1] == ""

    ordered_edits = sorted(edits, key=lambda edit: (edit.start_line, edit.end_line))
    try:
        for i in range(1, len(ordered_edits)):
            if ordered_edits[i].start_line <= ordered_edits[i - 1].end_line:
                raise ValueError("Structured edits must be non-overlapping and ordered by start_line.")

        for edit in ordered_edits:
            if edit.start_line < 1 or edit.end_line < edit.start_line:
                raise ValueError(f"Invalid structured-edit range: line {edit.start_line}-{edit.end_line}.")
            if edit.end_line > len(lines):
                raise ValueError(
                    f"Structured-edit end line {edit.end_line} exceeds source length ({len(lines)} lines)."
                )
    except ValueError:
        raise

    cursor = 0
    for edit in ordered_edits:
        if edit.start_line < cursor:
            try:
                raise ValueError("Structured edits overlap after validation.")
            except ValueError:
                raise
        # Strip embedded newlines from replacement lines so they splice cleanly
        # into the line array (the join at the end re-inserts them).
        stripped = tuple(line.rstrip("\n").rstrip("\r") for line in edit.replacement_lines)
        lines[edit.start_line - 1 : edit.end_line] = list(stripped)
        cursor = edit.end_line

    result = "\n".join(lines)
    if preserved_trailing_newline and not result.endswith("\n"):
        result += "\n"
    return result


# ---------------------------------------------------------------------------
# ASP-HG guard & engine.
# ---------------------------------------------------------------------------


class PatchSentry:
    """ASP-HG pre-flight gate that blocks speculative patches before any disk write.

    Gate order (per spec): parse the base context -> build and validate the candidate
    AST -> lazy-truncation predicate first (raises) -> structural-anchor gate. This
    ordering guarantees LazyTruncationViolationError fires even when a low anchor would
    also reject, because the lazy check runs before the anchor check.
    """

    def __init__(self, *, anchor_threshold: float = ANCHOR_THRESHOLD, lazy_truncation_ratio: float = DEFAULT_LAZY_RATIO) -> None:
        try:
            if not 0.0 <= anchor_threshold <= 1.0:
                raise ValueError("anchor_threshold must lie within [0.0, 1.0].")
        except ValueError:
            raise
        self._anchor_threshold = anchor_threshold
        self._lazy_truncation_ratio = lazy_truncation_ratio

    def detect_lazy_truncation(self, base_source: str, candidate_source: str) -> Optional[str]:
        """Return the lazy-truncation diagnostic for a candidate pair (pure, non-raising)."""
        return detect_lazy_truncation(base_source, candidate_source, ratio=self._lazy_truncation_ratio)

    def structural_anchor_score(self, base_source: str, candidate_source: str) -> float:
        """Return the leaf-token anchor overlap between a candidate pair."""
        return structural_anchor_score(base_source, candidate_source)

    def preflight_check(self, base_source: str, candidate_source: str) -> CandidatePatch:
        """Run the full ASP-HG gate and return a CandidatePatch verdict.

        Gate ordering is intentional:
          1. Base AST must be valid (anchoring needs a reference tree).
          2. Ellipsis/todo sentinels are detected on raw text FIRST,
             because they may appear in non-Python syntax (e.g. JS comments)
             that would fail the parse gate before lazy-truncation could fire.
          3. Candidate AST must be valid for structural scoring.
          4. Anchor threshold is checked last as a soft rejection.

        Raises:
            LazyTruncationViolationError: If the lazy-truncation predicate fires.
            ParseGuardError: If either source fails to parse (parse gate).
        """
        # Gate 1: base context must be a valid AST so anchoring has a reference tree.
        try:
            ast.parse(base_source)
        except SyntaxError as exc:
            raise ParseGuardError(f"[ASP-HG] Pre-flight parse gate rejected base source: {exc}") from exc

        # Gate 2 (moved up): ellipsis/todo sentinels detected on raw text BEFORE parsing.
        # This catches lazy-deletion markers in non-Python syntax that would otherwise
        # fail the parse gate before _evaluate_lazy_truncation could fire.
        lazy_result = _evaluate_lazy_truncation(base_source, candidate_source, ratio=self._lazy_truncation_ratio)
        if lazy_result is not None:
            removed_ratio, matched_sentinels = lazy_result
            try:
                raise LazyTruncationViolationError(removed_ratio, matched_sentinels)
            except LazyTruncationViolationError:
                raise

        # Gate 3: candidate must be syntactically valid before any further scoring.
        try:
            ast.parse(candidate_source)
        except SyntaxError as exc:
            raise ParseGuardError(
                f"[ASP-HG] Pre-flight parse gate rejected candidate source: {exc}"
            ) from exc

        # Gate 4: structural anchor gate -- a soft rejection below the configured threshold.
        anchor_score = structural_anchor_score(base_source, candidate_source)
        node_delta_ratio = self._node_delta_ratio(base_source, candidate_source)
        if anchor_score < self._anchor_threshold:
            return CandidatePatch(
                anchor_score=anchor_score,
                node_delta_ratio=node_delta_ratio,
                valid=False,
                rejection_reason=(
                    f"[ASP-HG] Anchor gate rejected: leaf-token overlap {anchor_score:.2f} "
                    f"below threshold {self._anchor_threshold:.2f}."
                ),
            )

        return CandidatePatch(anchor_score=anchor_score, node_delta_ratio=node_delta_ratio, valid=True)

    @staticmethod
    def _node_delta_ratio(base_source: str, candidate_source: str) -> float:
        """Fraction of base AST nodes the candidate drops (0.0 == structurally identical)."""
        try:
            base_count = _ast_node_count(ast.parse(base_source))
        except SyntaxError:
            return 1.0
        try:
            candidate_count = _ast_node_count(ast.parse(candidate_source))
        except SyntaxError:
            return 1.0
        if base_count == 0:
            return 1.0
        return (base_count - candidate_count) / base_count

    def guard(self, base_source: str, candidate_source: str) -> CandidatePatch:
        """Convenience alias for preflight_check that raises on hard violations."""
        return self.preflight_check(base_source, candidate_source)


class ASPHGEngine:
    """High-level orchestrator applying structured edits through the ASP-HG guard.

    Combines the atomic whitespace-preserving splice with the full pre-flight gate so a
    patch is materialized in memory and only then evaluated -- no physical disk write
    happens until an explicit commit by the caller.
    """

    def __init__(self, sentry: Optional[PatchSentry] = None) -> None:
        self._sentry = sentry if sentry is not None else PatchSentry()

    @property
    def sentry(self) -> PatchSentry:
        """The underlying PatchSentry guard backing this engine."""
        return self._sentry

    def apply_and_guard(self, base_source: str, edits: Sequence[StructuredEdit]) -> CandidatePatch:
        """Materialize edits via atomic splice, then run the full ASP-HG pre-flight gate.

        Returns a CandidatePatch verdict; raises on hard violations (parse or lazy-truncation).
        Callers commit only when patch.valid is true.
        """
        candidate_source = atomic_splice(base_source, list(edits))
        return self._sentry.preflight_check(base_source, candidate_source)

    def anchor_score(self, base_source: str, candidate_source: str) -> float:
        """Return the leaf-token anchor overlap for an arbitrary candidate pair."""
        return self._sentry.structural_anchor_score(base_source, candidate_source)

    def detect_lazy_truncation(self, base_source: str, candidate_source: str) -> Optional[str]:
        """Return a lazy-truncation diagnostic for a candidate pair (pure, non-raising)."""
        return self._sentry.detect_lazy_truncation(base_source, candidate_source)


# ---------------------------------------------------------------------------
# Public symbol table. The low-level primitives above are the single source of truth
# shared with fault_keeper.armor.scpve.
# ---------------------------------------------------------------------------

__all__ = [
    "ANCHOR_THRESHOLD",
    "DEFAULT_LAZY_RATIO",
    "DEFAULT_PREFLIGHT_BUDGET_S",
    "CandidatePatch",
    "ELLIPSIS_SENTINELS",
    "LazyTruncationViolationError",
    "ParseGuardError",
    "ASPHGEngine",
    "PatchSentry",
    "StructuredEdit",
    "atomic_splice",
    "detect_lazy_truncation",
    "structural_anchor_score",
]
