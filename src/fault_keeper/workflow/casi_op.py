"""CASI-OP: Cache Atomicity & Stamping Invalidation Optimizer — Operational Protection.

Ensures correct cache invalidation ordering relative to database operations and
implements the XFetch algorithm to prevent cache stampede on cache misses under
high concurrency.
"""

from __future__ import annotations

import ast
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CacheInvalidationFinding:
    """A single cache invalidation ordering finding."""
    lineno: int
    category: str  # "ordering", "missing_invalidation", "stampede_risk"
    message: str
    severity: str  # "error", "warning"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lineno": self.lineno,
            "category": self.category,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass
class XFetchConfig:
    """Configuration for the XFetch cache stampede prevention algorithm."""
    base_delay_ms: float = 10.0       # Initial jitter delay in milliseconds
    max_delay_ms: float = 500.0       # Maximum backoff cap
    beta: float = 2.0                 # Exponential growth factor for jitter
    early_recompute_threshold: float = 0.7  # Fraction of TTL at which to start recomputation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_delay_ms": self.base_delay_ms,
            "max_delay_ms": self.max_delay_ms,
            "beta": self.beta,
            "early_recompute_threshold": self.early_recompute_threshold,
        }


# ---------------------------------------------------------------------------
# Cache invalidation ordering analysis
# ---------------------------------------------------------------------------

def _detect_invalidation_ordering_issues(tree: ast.Module) -> List[CacheInvalidationFinding]:
    """Detect incorrect cache-DB operation ordering in Python source."""
    findings: List[CacheInvalidationFinding] = []

    # Track write operations (db writes, mutations) and cache invalidations
    write_ops: List[Tuple[int, str]] = []  # (lineno, description)
    invalidate_ops: List[Tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            line_no = getattr(node, "lineno", 0)

            # Detect database write operations
            if (isinstance(func, ast.Attribute) and
                    func.attr in ("execute", "commit", "save", "insert", "update", "delete",
                                  "create", "drop")):
                write_ops.append((line_no, f"DB.{func.attr}() at line {line_no}"))

            # Detect cache invalidation / eviction operations
            if (isinstance(func, ast.Attribute) and
                    func.attr in ("invalidate", "evict", "clear", "delete", "remove",
                                  "expire", "touch", "refresh")):
                invalidate_ops.append((line_no, f"cache.{func.attr}() at line {line_no}"))

            # Detect cache set/store operations (writes that should be invalidated on DB change)
            if (isinstance(func, ast.Attribute) and
                    func.attr in ("set", "store", "put", "add", "write", "save_cache")):
                invalidate_ops.append((line_no, f"cache.{func.attr}() at line {line_no} [should check invalidation]"))

    # Check ordering: cache invalidation must happen AFTER the DB write completes
    for inv_line, inv_desc in invalidate_ops:
        # Find any DB writes that occur after this invalidation (wrong order)
        for write_line, write_desc in write_ops:
            if write_line > inv_line:
                findings.append(CacheInvalidationFinding(
                    lineno=inv_line,
                    category="ordering",
                    message=(
                        f"Cache invalidation {inv_desc} occurs BEFORE DB write {write_desc}. "
                        f"Invalidation must happen AFTER the database mutation completes to avoid "
                        f"serving stale cached data."
                    ),
                    severity="error",
                ))

    # Check for missing invalidations after writes (writes without corresponding cache clears)
    if write_ops and not invalidate_ops:
        for write_line, write_desc in write_ops:
            findings.append(CacheInvalidationFinding(
                lineno=write_line,
                category="missing_invalidation",
                message=(
                    f"Database mutation {write_desc} has no corresponding cache invalidation. "
                    f"Cache will serve stale data until TTL expiry."
                ),
                severity="error",
            ))

    return findings


# ---------------------------------------------------------------------------
# XFetch algorithm — stochastic lock for cache stampede prevention
# ---------------------------------------------------------------------------

class XFetchEngine:
    """Implements the XFetch cache stampede prevention algorithm.

    When a cache entry expires under high concurrency, multiple workers may
    simultaneously attempt to recompute it (cache stampede).  XFetch resolves this
    by assigning each worker a stochastic delay E = −β · δ · ln(u), where:
        β   — jitter scale factor (configurable)
        δ   — base delay in ms
        u   — uniform random number in (0, 1]

    Only the worker with the *shortest* delay actually performs recomputation;
    all others wait and read the result once available.
    """

    def __init__(self, config: Optional[XFetchConfig] = None) -> None:
        self.config = config or XFetchConfig()

    def assign_delay(self, worker_id: int, seed: Optional[int] = None) -> float:
        """Compute the stochastic delay for a given worker.

        Args:
            worker_id: Unique integer identifier for the worker (used as RNG seed).
            seed: Optional external random seed override.

        Returns:
            Delay in milliseconds before this worker should attempt recomputation.
        """
        rng = random.Random(seed if seed is not None else worker_id)
        u = rng.uniform(1e-9, 1.0)  # Avoid ln(0); clamp to (0, 1]

        beta = self.config.beta
        delta = self.config.base_delay_ms

        delay_ms = -beta * delta * math.log(u)
        return min(delay_ms, self.config.max_delay_ms)

    def select_winner(self, workers: List[int]) -> int:
        """Given a list of worker IDs contending for cache recompute, select the winner.

        Args:
            workers: List of worker ID integers.

        Returns:
            The worker_id with the shortest stochastic delay (the recomputation owner).
        """
        delays = {wid: self.assign_delay(wid) for wid in workers}
        return min(delays, key=delays.get)  # type: ignore[arg-type]

    def simulate_stampede(self, n_workers: int, ttl_ms: float) -> Dict[str, Any]:
        """Simulate a cache stampede scenario with *n_workers* concurrent requests.

        Args:
            n_workers: Number of simultaneous workers hitting the expired cache entry.
            ttl_ms: Time-to-live of the cached entry in milliseconds (for context).

        Returns:
            Dict summarising the simulation outcome including winner, delays, and
            whether stampede was successfully prevented.
        """
        worker_ids = list(range(1, n_workers + 1))
        delays = {wid: self.assign_delay(wid) for wid in worker_ids}
        winner_id = min(delays, key=delays.get)  # type: ignore[arg-type]

        # Stampede is prevented if the second-shortest delay exceeds TTL (winner finishes first)
        sorted_delays = sorted(delays.values())
        stampede_prevented = (len(sorted_delays) < 2 or
                              sorted_delays[1] > ttl_ms * self.config.early_recompute_threshold)

        return {
            "n_workers": n_workers,
            "ttl_ms": ttl_ms,
            "winner_id": winner_id,
            "delays_ms": {str(k): round(v, 4) for k, v in delays.items()},
            "shortest_delay_ms": round(sorted_delays[0], 4) if sorted_delays else 0.0,
            "second_shortest_delay_ms": round(sorted_delays[1], 4) if len(sorted_delays) > 1 else None,
            "stampede_prevented": stampede_prevented,
        }


# ---------------------------------------------------------------------------
# Public API — analyse_cache_source & xfetch_engine
# ---------------------------------------------------------------------------

def analyse_cache_source(source: str) -> Dict[str, Any]:
    """Analyse Python source for cache invalidation ordering issues.

    Args:
        source: Raw Python source code string.

    Returns:
        Dict with ``findings`` list and summary counts.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {
            "findings": [],
            "error": f"Source syntax error: {e}",
            "summary": {"total": 0, "errors": 0, "warnings": 0},
        }

    findings = _detect_invalidation_ordering_issues(tree)

    n_errors = sum(1 for f in findings if f.severity == "error")
    n_warnings = sum(1 for f in findings if f.severity == "warning")

    return {
        "findings": [f.to_dict() for f in findings],
        "summary": {
            "total": len(findings),
            "errors": n_errors,
            "warnings": n_warnings,
        },
    }


def create_xfetch_engine(config: Optional[XFetchConfig] = None) -> Dict[str, Any]:
    """Create and return an XFetch engine serialised as dict (for MCP dispatch).

    Args:
        config: Optional configuration override.

    Returns:
        Dict with ``engine_type`` and current config snapshot.
    """
    engine = XFetchEngine(config)
    return {
        "engine_type": "XFetch",
        "config": engine.config.to_dict(),
        "description": (
            "Stochastic lock cache stampede prevention. Workers compute delay "
            "E = -β·δ·ln(u); shortest-delay worker recomputes, others wait."
        ),
    }
