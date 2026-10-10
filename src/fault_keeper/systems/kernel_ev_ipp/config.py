"""EV-IPP (eBPF Verifier In-IDE Register Bounds & Truncated Number Abstract Domain) Configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class EVIPPConfig:
    """Configuration parameters for EV-IPP eBPF verifier abstract simulator."""

    # Maximum simulated instruction steps before aborting (path explosion guard)
    max_insn_limit: int = 1000000

    # Stack size limit in bytes (standard eBPF is 512 bytes)
    max_stack_size: int = 512

    # Enable 32-bit sub-register bounds tracking
    track_alu32_bounds: bool = True

    # Strict pointer provenance enforcement
    strict_pointer_check: bool = True

    @classmethod
    def from_env(cls) -> "EVIPPConfig":
        """Load configuration from environment variables."""
        cfg = cls()
        if os.getenv("EVIPP_MAX_INSN_LIMIT"):
            cfg.max_insn_limit = int(os.environ["EVIPP_MAX_INSN_LIMIT"])
        if os.getenv("EVIPP_MAX_STACK_SIZE"):
            cfg.max_stack_size = int(os.environ["EVIPP_MAX_STACK_SIZE"])
        return cfg


__all__ = ["EVIPPConfig"]
