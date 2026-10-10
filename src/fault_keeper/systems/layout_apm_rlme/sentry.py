"""APM-RLME Sentry: Zero-Stall Layout Monitor"""

import time
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass
import numpy as np

from .config import APM_RLMEConfig
from .engine import AoSSoATransposer, ZeroStallContainer, SIMDTransposer


@dataclass
class TranspositionEvent:
    """Represents a layout transposition event."""
    timestamp: float
    from_layout: str
    to_layout: str
    duration_us: float


class LayoutMonitor:
    """Monitor for memory layout changes."""
    
    def __init__(self):
        """Initialize layout monitor."""
        self.events: List[TranspositionEvent] = []
        self.lock = threading.Lock()
        self.total_transpositions: int = 0
        self.last_transposition_time: float = 0.0
    
    def record_transposition(self, from_layout: str, to_layout: str, duration_us: float) -> None:
        """
        Record a transposition event.
        
        Args:
            from_layout: Source layout
            to_layout: Target layout
            duration_us: Duration in microseconds
        """
        with self.lock:
            event = TranspositionEvent(
                timestamp=time.time(),
                from_layout=from_layout,
                to_layout=to_layout,
                duration_us=duration_us,
            )
            self.events.append(event)
            self.total_transpositions += 1
            self.last_transposition_time = time.time()
    
    def get_avg_transposition_time(self) -> float:
        """
        Get average transposition time.
        
        Returns:
            Average time in microseconds
        """
        if not self.events:
            return 0.0
        
        total_time = sum(e.duration_us for e in self.events)
        return total_time / len(self.events)
    
    def get_stats(self) -> Dict[str, any]:
        """Get monitor statistics."""
        return {
            "total_transpositions": self.total_transpositions,
            "avg_transposition_time_us": self.get_avg_transposition_time(),
            "event_count": len(self.events),
        }


class APM_RLME_Sentry:
    """Main APM-RLME sentry orchestrator."""
    
    def __init__(self, config: Optional[APM_RLMEConfig] = None):
        """
        Initialize APM-RLME sentry.
        
        Args:
            config: APM-RLME configuration (optional)
        """
        self.config = config or APM_RLMEConfig()
        self._transposer = AoSSoATransposer()
        self.container = ZeroStallContainer(self.config)
        self._simd_transposer = SIMDTransposer(self.config.simd_width)
        self.monitor = LayoutMonitor()
        self.active_data: Optional[np.ndarray] = None
    
    def process_data(self, data: np.ndarray, is_read: bool) -> np.ndarray:
        """
        Process data with automatic layout switching.
        
        Args:
            data: Input data
            is_read: True for read access
            
        Returns:
            Processed data
        """
        # Record access pattern
        self.container.record_access(is_read)
        
        # Check if transposition is needed
        if self.container.should_transpose():
            target = "SoA" if is_read else "AoS"
            self.container.switch_layout(target)
            
            # Perform transposition
            start_t = time.perf_counter()
            transposed = self._transposer.transpose(data, target == "SoA")
            duration_us = max(0.1, (time.perf_counter() - start_t) * 1_000_000)
            
            # Record event
            self.monitor.record_transposition(
                "AoS" if target == "SoA" else "SoA",
                target,
                duration_us
            )
            
            self.active_data = transposed
            return transposed
        
        # If current container layout is SoA and 2D data is AoS (rows > cols), enforce layout
        if self.container.current_layout == "SoA" and isinstance(data, np.ndarray) and data.ndim == 2 and data.shape[0] > data.shape[1]:
            return self._transposer.transpose(data, True)
        elif self.container.current_layout == "AoS" and isinstance(data, np.ndarray) and data.ndim == 2 and data.shape[0] < data.shape[1]:
            return self._transposer.transpose(data, False)
        
        return data
    
    def get_container_stats(self) -> Dict[str, any]:
        """Get container statistics."""
        return self.container.get_layout_stats()
    
    def get_monitor_stats(self) -> Dict[str, any]:
        """Get monitor statistics."""
        return self.monitor.get_stats()
    
    def get_full_stats(self) -> Dict[str, any]:
        """Get full statistics."""
        return {
            "container_stats": self.get_container_stats(),
            "monitor_stats": self.get_monitor_stats(),
            "simd_info": self._simd_transposer.get_simd_info(),
        }
    
    @property
    def transposer(self) -> AoSSoATransposer:
        """Transposer property."""
        return self._transposer
    
    @property
    def simd_transposer(self) -> SIMDTransposer:
        """SIMD transposer property."""
        return self._simd_transposer


__all__ = [
    "APM_RLME_Sentry",
    "TranspositionEvent",
    "LayoutMonitor",
]