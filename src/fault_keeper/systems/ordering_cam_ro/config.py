"""CAM-RO (Cross-Architecture Memory Reordering & Atomic Fence Synthesizer) Configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class CAMROConfig:
    """Configuration parameters for CAM-RO Memory Ordering & Fence Synthesizer."""

    # Default target architecture
    default_architecture: str = "ARMV8_WEAK"

    # Optimization level for fence synthesis: "minimal", "conservative", "strict"
    synthesis_mode: str = "minimal"

    # Enable atomic load-acquire / store-release promotion
    enable_ldar_stlr_promotion: bool = True

    # Real-time memory model violation detection enabled
    auditor_enabled: bool = True

    @classmethod
    def from_env(cls) -> "CAMROConfig":
        """Load configuration from environment variables."""
        cfg = cls()
        if os.getenv("CAMRO_DEFAULT_ARCHITECTURE"):
            cfg.default_architecture = os.environ["CAMRO_DEFAULT_ARCHITECTURE"]
        if os.getenv("CAMRO_SYNTHESIS_MODE"):
            cfg.synthesis_mode = os.environ["CAMRO_SYNTHESIS_MODE"]
        return cfg


__all__ = ["CAMROConfig"]
