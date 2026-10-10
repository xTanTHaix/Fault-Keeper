"""SC-BBW (Spectral Graph Laplacian Basic-Block Reordering Weaver) Configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class SCBBWConfig:
    """Configuration parameters for SC-BBW Spectral Graph Laplacian Reordering."""

    # L1 Instruction cache line size in bytes (standard 64 bytes)
    cache_line_size_bytes: int = 64

    # Default fallthrough execution bias weight
    fallthrough_weight: float = 100.0

    # Minimum execution count to consider block in hot trace
    hot_threshold_count: int = 10

    # Tolerance for spectral eigensolver convergence
    spectral_tolerance: float = 1e-6

    @classmethod
    def from_env(cls) -> "SCBBWConfig":
        """Load configuration from environment variables."""
        cfg = cls()
        if os.getenv("SCBBW_CACHE_LINE_SIZE"):
            cfg.cache_line_size_bytes = int(os.environ["SCBBW_CACHE_LINE_SIZE"])
        if os.getenv("SCBBW_HOT_THRESHOLD"):
            cfg.hot_threshold_count = int(os.environ["SCBBW_HOT_THRESHOLD"])
        return cfg


__all__ = ["SCBBWConfig"]
