"""ZSC-THP Configuration Constants"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ZSCConfig:
    """Configuration for ZSC-THP subsystem."""
    
    # Dual-Pool Hybrid Allocation Arena parameters
    static_arena_size_mb: int = 2048  # 2GB for critical path (2MB THP pages)
    dynamic_arena_size_mb: int = 4096  # 4GB for non-critical (4KB pages)
    thp_page_size_kb: int = 2048  # 2MB for Transparent HugePages
    
    # Compaction parameters
    compaction_threshold_percent: float = 75.0  # Trigger compaction at 75% fragmentation
    background_compaction_interval_s: float = 10.0  # Background compaction interval
    madvise_collapsed_pages: int = 1024  # Pages to collapse per madvise call
    
    # Memory efficiency targets
    target_allocation_efficiency: float = 0.98  # 98% efficiency
    max_compaction_duration_ms: float = 0.0  # Zero stall target for critical path
    
    # Process madvise parameters
    process_madvise_enabled: bool = True
    madvise_flags: list = None
    
    @classmethod
    def from_env(cls) -> "ZSCConfig":
        """Load configuration from environment variables."""
        config = cls()
        
        if os.getenv("ZSC_STATIC_ARENA_MB"):
            config.static_arena_size_mb = int(os.getenv("ZSC_STATIC_ARENA_MB"))
        if os.getenv("ZSC_DYNAMIC_ARENA_MB"):
            config.dynamic_arena_size_mb = int(os.getenv("ZSC_DYNAMIC_ARENA_MB"))
        if os.getenv("ZSC_COMPACT_THRESHOLD"):
            config.compaction_threshold_percent = float(os.getenv("ZSC_COMPACT_THRESHOLD"))
        
        return config


__all__ = ["ZSCConfig"]