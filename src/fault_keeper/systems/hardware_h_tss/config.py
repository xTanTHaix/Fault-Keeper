"""H-TSS Configuration Constants"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class H_TSSConfig:
    """Configuration for H-TSS (Hardware Pointer Tagging)."""
    
    # Pointer tagging parameters
    tag_bits: int = 4  # Bits for pointer tag
    tag_mask: int = 0xF  # Tag mask (2^tag_bits - 1)
    
    # Buffer overflow detection
    buffer_size_limit: int = 1024 * 1024  # 1MB limit
    overflow_threshold_percent: float = 95.0  # Alert at 95% buffer usage
    
    # Use-After-Free detection
    uaf_detection_enabled: bool = True
    uaf_check_interval_ms: float = 10.0
    
    # Tag validation
    validate_on_access: bool = True
    tag_mismatch_action: str = "abort"  # abort, log, ignore
    
    @classmethod
    def from_env(cls) -> "H_TSSConfig":
        """Load configuration from environment variables."""
        config = cls()
        
        if os.getenv("H_TSS_TAG_BITS"):
            config.tag_bits = int(os.getenv("H_TSS_TAG_BITS"))
        
        return config


__all__ = ["H_TSSConfig"]