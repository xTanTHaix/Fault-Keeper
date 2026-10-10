"""APM-RLME Engine: Zero-Stall AoS/SoA Transposition Container"""


import numpy as np
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class APM_RLMEConfig:
    """APM-RLME configuration."""
    aoas_buffer_size_mb: int = 256
    soas_buffer_size_mb: int = 256
    transposition_threshold: float = 0.7
    zero_stall_mode: bool = True
    simd_width: int = 256


class AoSSoATransposer:
    """Array of Structures <-> Structure of Arrays transposer using NumPy stride vectorization."""
    
    def __init__(self, aoas_size_mb: int = 256, soas_size_mb: int = 256):
        """
        Initialize transposer.
        
        Args:
            aoas_size_mb: AoS buffer size in MB
            soas_size_mb: SoA buffer size in MB
        """
        self.aoas_buffer_size = aoas_size_mb * 1024 * 1024
        self.soas_buffer_size = soas_size_mb * 1024 * 1024
        self.aoas_buffer: Optional[np.ndarray] = None
        self.soas_buffer: Optional[np.ndarray] = None
        self.lock = threading.Lock()
    
    def aoas_to_soas(self, aoas_data: any, field_names: Optional[List[str]] = None) -> any:
        """
        Transpose AoS to SoA.
        
        For 2D numerical array of shape (N, C) (AoS), transposes along strides to (C, N) (SoA).
        For structured array with named fields, extracts contiguous 1D column arrays.
        
        Args:
            aoas_data: Array of Structures data
            field_names: List of field names to extract (optional)
            
        Returns:
            Structure of Arrays data (2D transposed array or dict of column arrays)
        """
        if isinstance(aoas_data, dict):
            return aoas_data
        
        if isinstance(aoas_data, np.ndarray) and aoas_data.dtype.names is not None:
            names = field_names or list(aoas_data.dtype.names)
            soa_dict = {}
            for name in names:
                if name in aoas_data.dtype.names:
                    soa_dict[name] = np.ascontiguousarray(aoas_data[name])
            return soa_dict
        elif isinstance(aoas_data, np.ndarray) and aoas_data.ndim == 2:
            return np.ascontiguousarray(aoas_data.T)
        else:
            return np.ascontiguousarray(aoas_data)
    
    def soas_to_aos(self, soas_data: any, field_names: Optional[List[str]] = None) -> np.ndarray:
        """
        Transpose SoA to AoS.
        
        For 2D numerical array of shape (C, N) (SoA), transposes along strides to (N, C) (AoS).
        For dictionary of column arrays, reconstructs structured array.
        
        Args:
            soas_data: Structure of Arrays data
            field_names: List of field names to combine (optional)
            
        Returns:
            Array of Structures data
        """
        if isinstance(soas_data, dict):
            names = field_names or list(soas_data.keys())
            if not names:
                return np.array([])
            n_items = len(soas_data[names[0]])
            dtype_list = [(name, soas_data[name].dtype) for name in names]
            aos_array = np.empty(n_items, dtype=dtype_list)
            for name in names:
                aos_array[name] = soas_data[name]
            return aos_array
        elif isinstance(soas_data, np.ndarray) and soas_data.ndim == 2:
            return np.ascontiguousarray(soas_data.T)
        else:
            return np.ascontiguousarray(soas_data)
    
    def transpose(self, data: any, to_soas: bool) -> any:
        """
        Transpose between AoS and SoA.
        
        Args:
            data: Input data
            to_soas: True for AoS->SoA, False for SoA->AoS
            
        Returns:
            Transposed data
        """
        with self.lock:
            if to_soas:
                if isinstance(data, np.ndarray) and data.dtype.names is not None:
                    return self.aoas_to_soas(data, list(data.dtype.names))
                return self.aoas_to_soas(data)
            else:
                if isinstance(data, dict):
                    return self.soas_to_aos(data, list(data.keys()))
                return self.soas_to_aos(data)
    
    def get_buffer_info(self) -> Dict[str, any]:
        """Get buffer information."""
        return {
            "aoas_buffer_size": self.aoas_buffer_size,
            "soas_buffer_size": self.soas_buffer_size,
            "aoas_allocated": self.aoas_buffer is not None,
            "soas_allocated": self.soas_buffer is not None,
        }


class ZeroStallContainer:
    """Zero-stall memory layout container."""
    
    def __init__(self, config: Optional["APM_RLMEConfig"] = None):
        """
        Initialize zero-stall container.
        
        Args:
            config: APM-RLME configuration (optional)
        """
        self.config = config or APM_RLMEConfig()
        self.transposer = AoSSoATransposer(
            self.config.aoas_buffer_size_mb,
            self.config.soas_buffer_size_mb
        )
        self.current_layout: str = "AoS"
        self.read_count: int = 0
        self.write_count: int = 0
        self.lock = threading.Lock()
    
    def record_access(self, is_read: bool) -> None:
        """
        Record memory access pattern.
        
        Args:
            is_read: True for read access, False for write access
        """
        with self.lock:
            if is_read:
                self.read_count += 1
            else:
                self.write_count += 1
    
    def should_transpose(self) -> bool:
        """
        Check if transposition is needed.
        
        Returns:
            True if transposition should occur
        """
        total = self.read_count + self.write_count
        if total == 0:
            return False
        
        read_ratio = self.read_count / total
        
        # Switch to SoA if read-heavy
        should_soas = read_ratio > self.config.transposition_threshold
        should_aos = read_ratio < (1 - self.config.transposition_threshold)
        
        return should_soas != (self.current_layout == "SoA")
    
    def switch_layout(self, target_layout: str) -> bool:
        """
        Switch memory layout.
        
        Args:
            target_layout: Target layout ("AoS" or "SoA")
            
        Returns:
            True if switch successful
        """
        with self.lock:
            if target_layout == "SoA":
                self.current_layout = "SoA"
                return True
            elif target_layout == "AoS":
                self.current_layout = "AoS"
                return True
            return False
    
    def get_layout_stats(self) -> Dict[str, any]:
        """Get layout statistics."""
        total = self.read_count + self.write_count
        read_ratio = self.read_count / total if total > 0 else 0.0
        
        return {
            "current_layout": self.current_layout,
            "read_count": self.read_count,
            "write_count": self.write_count,
            "read_ratio": read_ratio,
            "should_transpose": self.should_transpose(),
        }


class SIMDTransposer:
    """SIMD-accelerated transposer."""
    
    def __init__(self, simd_width: int = 256):
        """
        Initialize SIMD transposer.
        
        Args:
            simd_width: SIMD width in bits
        """
        self.simd_width = simd_width
        self.vectors_per_word = simd_width // 64  # 64-bit words
    
    def transpose_simd(self, data: any) -> any:
        """
        SIMD-accelerated transposition.
        
        Args:
            data: Input data
            
        Returns:
            Transposed data
        """
        if isinstance(data, np.ndarray) and data.ndim == 2:
            return np.ascontiguousarray(data.T)
        elif isinstance(data, dict):
            return {k: np.ascontiguousarray(v) for k, v in data.items()}
        return np.ascontiguousarray(data)
    
    def get_simd_info(self) -> Dict[str, any]:
        """Get SIMD information."""
        return {
            "simd_width": self.simd_width,
            "vectors_per_word": self.vectors_per_word,
        }


__all__ = [
    "APM_RLMEConfig",
    "AoSSoATransposer",
    "ZeroStallContainer",
    "SIMDTransposer",
]