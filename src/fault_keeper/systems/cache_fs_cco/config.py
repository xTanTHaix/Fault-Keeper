"""FS-CCO Configuration Constants"""

import os
from dataclasses import dataclass


@dataclass
class FS_CCO_Config:
    """Configuration for FS-CCO subsystem."""
    
    # Cache line parameters
    cache_line_size_bytes: int = 64  # Standard x86/ARM cache line size
    
    # Alignment and padding
    min_padding_bytes: int = 64
    max_padding_bytes: int = 128
    
    # False sharing detection thresholds
    invalidation_threshold_percent: float = 99.5  # Target reduction
    false_sharing_penalty: float = 0.01  # Performance penalty per false sharing event
    
    # Layout optimization
    auto_pad_structs: bool = True
    enforce_alignment: bool = True
    
    @classmethod
    def from_env(cls) -> "FS_CCO_Config":
        """Load configuration from environment variables."""
        config = cls()
        
        if os.getenv("CACHE_LINE_SIZE"):
            config.cache_line_size_bytes = int(os.getenv("CACHE_LINE_SIZE"))
        if os.getenv("INVALIDATION_THRESHOLD"):
            config.invalidation_threshold_percent = float(os.getenv("INVALIDATION_THRESHOLD"))
        
        return config


__all__ = ["FS_CCO_Config"]