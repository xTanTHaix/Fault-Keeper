"""SABA (SIMD Auto-Vectorization Barrier Analyzer) Configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class SABAConfig:
    """Configuration parameters for SABA Auto-Vectorization Barrier Analyzer."""

    # Target SIMD vector width in bits (e.g., 128 for NEON/SSE, 256 for AVX2, 512 for AVX-512)
    vector_width_bits: int = 512

    # Default element size in bytes (e.g. 4 for float32/int32, 8 for float64/int64)
    element_size_bytes: int = 8

    # Unroll factor for vector loop body
    unroll_factor: int = 4

    # Strict pointer aliasing check enabled
    strict_noalias: bool = True

    @classmethod
    def from_env(cls) -> "SABAConfig":
        """Load configuration from environment variables."""
        cfg = cls()
        if os.getenv("SABA_VECTOR_WIDTH_BITS"):
            cfg.vector_width_bits = int(os.environ["SABA_VECTOR_WIDTH_BITS"])
        if os.getenv("SABA_UNROLL_FACTOR"):
            cfg.unroll_factor = int(os.environ["SABA_UNROLL_FACTOR"])
        return cfg


__all__ = ["SABAConfig"]
