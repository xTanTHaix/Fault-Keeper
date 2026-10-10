"""HEH-DR Configuration Constants"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class HEH_DRConfig:
    """Configuration for HEH-DR (Lock-Free Memory Reclamation)."""
    
    # Hazard pointer parameters
    hazard_pointer_slots: int = 16
    hazard_pointer_interval_ms: float = 100.0
    
    # Epoch-based reclamation
    epoch_advance_threshold: float = 0.8  # Advance epoch at 80% utilization
    epoch_min_objects: int = 100  # Min objects before advancing epoch
    
    # EBR (Epoch-Based Reclamation)
    ebr_window_size: int = 1024
    ebr_retire_interval_ms: float = 50.0
    
    # Thread retirement
    high_frequency_retirement: bool = False
    retire_batch_size: int = 64
    
    @classmethod
    def from_env(cls) -> "HEH_DRConfig":
        """Load configuration from environment variables."""
        config = cls()
        
        if os.getenv("HEH_DR_HAZARD_SLOTS"):
            config.hazard_pointer_slots = int(os.getenv("HEH_DR_HAZARD_SLOTS"))
        
        return config


__all__ = ["HEH_DRConfig"]