"""TSCA (Topological Simplicial Concurrency Arbiter) Configuration.

Provides configuration bounds and parameters for simplicial complex topology analysis,
boundary matrix calculation over GF(2), and Betti number computation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class TSCAConfig:
    """Configuration parameters for Topological Simplicial Concurrency Arbiter."""

    # Maximum simplicial dimension to evaluate (default 2 for surfaces/triangles)
    max_dimension: int = 2

    # Whether to use modulo 2 arithmetic (GF(2) / Z_2 homology)
    use_z2_field: bool = True

    # First Betti number threshold for deadlock warning (beta_1 >= 1 indicates cycle)
    deadlock_cycle_threshold: int = 1

    # Maximum number of vertices in simplicial tracking window
    max_vertices: int = 4096

    # Real-time auditing interval in seconds
    audit_interval_sec: float = 0.05

    @classmethod
    def from_env(cls) -> "TSCAConfig":
        """Load configuration overrides from environment variables."""
        cfg = cls()
        if os.getenv("TSCA_MAX_DIMENSION"):
            cfg.max_dimension = int(os.environ["TSCA_MAX_DIMENSION"])
        if os.getenv("TSCA_MAX_VERTICES"):
            cfg.max_vertices = int(os.environ["TSCA_MAX_VERTICES"])
        if os.getenv("TSCA_AUDIT_INTERVAL_SEC"):
            cfg.audit_interval_sec = float(os.environ["TSCA_AUDIT_INTERVAL_SEC"])
        return cfg


__all__ = ["TSCAConfig"]
