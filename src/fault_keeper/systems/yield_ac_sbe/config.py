"""AC-SBE (Auto-Cooperative Single-Threaded Blocking Event-Loop Yield Injector) Configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ACSBEConfig:
    """Configuration parameters for AC-SBE Event Loop Preemption & Yield Injector."""

    # Default iteration cadence between cooperative yields
    yield_cadence: int = 100

    # Stall detection threshold in seconds (10ms)
    stall_threshold_sec: float = 0.010

    # AST cost threshold above which loop is classified as blocking
    loop_cost_threshold: float = 10.0

    # Whether to inject asyncio.sleep(0) automatically
    auto_inject: bool = True

    @classmethod
    def from_env(cls) -> "ACSBEConfig":
        """Load configuration from environment variables."""
        cfg = cls()
        if os.getenv("ACSBE_YIELD_CADENCE"):
            cfg.yield_cadence = int(os.environ["ACSBE_YIELD_CADENCE"])
        if os.getenv("ACSBE_STALL_THRESHOLD_SEC"):
            cfg.stall_threshold_sec = float(os.environ["ACSBE_STALL_THRESHOLD_SEC"])
        return cfg


__all__ = ["ACSBEConfig"]
