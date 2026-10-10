"""NUMA-AFS Configuration Constants"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class NUMAAFSConfig:
    """Configuration for NUMA-AFS subsystem."""
    
    # NUMA topology parameters
    numa_nodes: int = 2  # Number of NUMA nodes (default: 2)
    cores_per_socket: int = 32  # Cores per socket
    threads_per_core: int = 2  # Threads per core
    
    # ACPI SLIT parsing
    acpi_slit_file: Optional[str] = None
    default_slit_threshold: float = 1.0
    
    # Locality Quotient parameters
    locality_quotient_threshold: float = 1.0
    locality_weight: float = 0.8
    bandwidth_weight: float = 0.2
    
    # Kuhn-Munkres matching
    km_cost_matrix_size: int = 64  # Max cores x pages
    
    # Interconnect stall thresholds
    max_interconnect_stall_us: float = 0.5  # microseconds
    upi_bandwidth_gbps: float = 20.0  # Default UPI bandwidth
    infinity_fabric_bbw_gbps: float = 50.0  # Default Infinity Fabric
    
    # Affinity enforcement
    enforce_first_touch: bool = True
    numa_policy: str = "prefer"  # prefer, bind, interleave, loose
    
    # Runtime detection
    detect_numa_topology: bool = True
    read_acpi_slit: bool = True
    
    @classmethod
    def from_env(cls) -> "NUMAAFSConfig":
        """Load configuration from environment variables."""
        config = cls()
        
        if os.getenv("NUMA_NODES"):
            config.numa_nodes = int(os.getenv("NUMA_NODES"))
        if os.getenv("NUMAAFS_LQ_THRESHOLD"):
            config.locality_quotient_threshold = float(os.getenv("NUMAAFS_LQ_THRESHOLD"))
        if os.getenv("NUMAAFS_MAX_STALL_US"):
            config.max_interconnect_stall_us = float(os.getenv("NUMAAFS_MAX_STALL_US"))
        
        return config


__all__ = ["NUMAAFSConfig"]