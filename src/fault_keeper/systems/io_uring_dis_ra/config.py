"""DIS-RA (Deterministic io_uring Ring Buffer & Backpressure Arbiter) Configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class DISRAConfig:
    """Configuration parameters for DIS-RA io_uring Ring Buffer & Backpressure Arbiter."""

    # Default submission queue ring size (power of 2)
    default_sq_entries: int = 64

    # Default completion queue ring size (typically 2x SQ size)
    default_cq_entries: int = 128

    # Backpressure threshold ratio (0.0 to 1.0) above which new SQEs are throttled
    backpressure_threshold: float = 0.85

    # Zero-copy polling mode enabled (IORING_SETUP_SQPOLL)
    sqpoll_enabled: bool = False

    @classmethod
    def from_env(cls) -> "DISRAConfig":
        """Load configuration from environment variables."""
        cfg = cls()
        if os.getenv("DISRA_SQ_ENTRIES"):
            cfg.default_sq_entries = int(os.environ["DISRA_SQ_ENTRIES"])
        if os.getenv("DISRA_CQ_ENTRIES"):
            cfg.default_cq_entries = int(os.environ["DISRA_CQ_ENTRIES"])
        if os.getenv("DISRA_BACKPRESSURE_THRESHOLD"):
            cfg.backpressure_threshold = float(os.environ["DISRA_BACKPRESSURE_THRESHOLD"])
        return cfg


__all__ = ["DISRAConfig"]
