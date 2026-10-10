"""PT-PAFS (Pointer Provenance & Tree Borrows Formal State Machine Verifier) Configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class PTPAFSConfig:
    """Configuration parameters for PT-PAFS Pointer Provenance & Tree Borrows Verifier."""

    # Maximum tree depth for borrow hierarchies
    max_tree_depth: int = 64

    # Strict aliasing UB abort policy
    abort_on_ub: bool = True

    # Track full history trace per pointer tag
    enable_history_trace: bool = True

    @classmethod
    def from_env(cls) -> "PTPAFSConfig":
        """Load configuration from environment variables."""
        cfg = cls()
        if os.getenv("PTPAFS_MAX_TREE_DEPTH"):
            cfg.max_tree_depth = int(os.environ["PTPAFS_MAX_TREE_DEPTH"])
        return cfg


__all__ = ["PTPAFSConfig"]
