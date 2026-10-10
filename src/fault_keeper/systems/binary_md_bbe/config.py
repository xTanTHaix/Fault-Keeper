"""MD-BBE (Monomorphization Deduplication & Binary Bloat Equivalence Eliminator) Configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class MDBBEConfig:
    """Configuration parameters for MD-BBE Monomorphization Deduplication Engine."""

    # Target binary reduction savings threshold (40% to 70%)
    target_reduction_ratio: float = 0.50

    # Minimum function body size in bytes to justify thunk creation
    min_function_size_bytes: int = 64

    # Estimated thunk wrapper overhead in bytes
    thunk_overhead_bytes: int = 16

    # Strict calling convention ABI alignment check
    strict_calling_convention: bool = True

    @classmethod
    def from_env(cls) -> "MDBBEConfig":
        """Load configuration from environment variables."""
        cfg = cls()
        if os.getenv("MDBBE_TARGET_REDUCTION_RATIO"):
            cfg.target_reduction_ratio = float(os.environ["MDBBE_TARGET_REDUCTION_RATIO"])
        if os.getenv("MDBBE_MIN_FUNCTION_SIZE"):
            cfg.min_function_size_bytes = int(os.environ["MDBBE_MIN_FUNCTION_SIZE"])
        return cfg


__all__ = ["MDBBEConfig"]
