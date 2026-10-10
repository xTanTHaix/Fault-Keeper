"""APM-RLME Configuration Constants"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class APM_RLMEConfig:
    """Configuration for APM-RLME (Memory Layout Transposition)."""
    
    # Transposition parameters
    aoas_buffer_size_mb: int = 256  # Array of Structures buffer size
    soas_buffer_size_mb: int = 256  # Structure of Arrays buffer size
    transposition_threshold: float = 0.7  # Switch to SoA at 70% read ratio
    
    # Zero-stall parameters
    zero_stall_mode: bool = True
    async_transposition: bool = True
    
    # SIMD parameters
    simd_width: int = 256  # AVX-512 width in bits
    gather_scatter_enabled: bool = True
    
    # Performance targets
    target_transposition_time_us: float = 100.0  # Target < 100us
    max_stall_cycles: int = 1000
    
    @classmethod
    def from_env(cls) -> "APM_RLMEConfig":
        """Load configuration from environment variables."""
        config = cls()
        
        if os.getenv("APM_RLME_AOAS_SIZE_MB"):
            config.aoas_buffer_size_mb = int(os.getenv("APM_RLME_AOAS_SIZE_MB"))
        
        return config


__all__ = ["APM_RLMEConfig"]