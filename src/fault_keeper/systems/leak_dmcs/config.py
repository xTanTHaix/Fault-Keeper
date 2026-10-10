"""DMCS Configuration Constants"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DMCSConfig:
    """Configuration for DMCS (Memory Leak Diagnosis)."""
    
    # Dominator tree parameters
    dominator_tree_depth: int = 32
    min_dominator_size: int = 64
    
    # Min-cut parameters
    min_cut_threshold: float = 0.8  # 80% memory recovery target
    max_cut_iterations: int = 100
    
    # Leak detection
    leak_detection_enabled: bool = True
    leak_scan_interval_ms: float = 50.0
    
    # Recovery parameters
    recovery_batch_size: int = 128
    recovery_threshold_percent: float = 75.0
    
    @classmethod
    def from_env(cls) -> "DMCSConfig":
        """Load configuration from environment variables."""
        config = cls()
        
        if os.getenv("DMCS_MIN_CUT_THRESHOLD"):
            config.min_cut_threshold = float(os.getenv("DMCS_MIN_CUT_THRESHOLD"))
        
        return config


__all__ = ["DMCSConfig"]