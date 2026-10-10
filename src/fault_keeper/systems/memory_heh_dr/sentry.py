"""HEH-DR Sentry: Memory Reclamation Monitor"""

import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

from .engine import (
    HEH_DRConfig,
    HazardPointerSystem,
    EpochBasedRetirement,
    LockFreeNode,
    LockFreeAllocator,
)


@dataclass
class ReclamationEvent:
    """Represents a memory reclamation event."""
    timestamp: float
    epoch: int
    objects_reclaimed: int
    hazard_pointer_count: int


class MemoryReclamationMonitor:
    """Monitor for memory reclamation events."""
    
    def __init__(self):
        """Initialize reclamation monitor."""
        self.events: List[ReclamationEvent] = []
        self.lock = threading.Lock()
        self.total_reclaimed: int = 0
        self.reclamation_history: List[float] = []
    
    def record_reclamation(self, epoch: int, objects_count: int) -> None:
        """
        Record a reclamation event.
        
        Args:
            epoch: Current epoch number
            objects_count: Number of objects reclaimed
        """
        with self.lock:
            event = ReclamationEvent(
                timestamp=time.time(),
                epoch=epoch,
                objects_reclaimed=objects_count,
                hazard_pointer_count=0,
            )
            self.events.append(event)
            self.total_reclaimed += objects_count
            self.reclamation_history.append(time.time())
    
    def get_reclamation_rate(self, window_seconds: float = 10.0) -> float:
        """
        Get reclamation rate in objects/second.
        
        Args:
            window_seconds: Time window in seconds
            
        Returns:
            Reclamation rate
        """
        if not self.reclamation_history:
            return 0.0
        
        if len(self.reclamation_history) < 2:
            return 0.0
        
        # Calculate time span
        time_span = self.reclamation_history[-1] - self.reclamation_history[0]
        
        if time_span <= 0:
            return 0.0
        
        return self.total_reclaimed / time_span
    
    def get_stats(self) -> Dict[str, any]:
        """Get monitor statistics."""
        return {
            "total_reclaimed": self.total_reclaimed,
            "event_count": len(self.events),
            "reclamation_rate": self.get_reclamation_rate(),
        }


class HEH_DR_Sentry:
    """Main HEH-DR sentry orchestrator."""
    
    def __init__(self, config: Optional[HEH_DRConfig] = None):
        """
        Initialize HEH-DR sentry.
        
        Args:
            config: HEH-DR configuration (optional)
        """
        self.config = config or HEH_DRConfig()
        self.allocator = LockFreeAllocator(self.config)
        self.reclamation_monitor = MemoryReclamationMonitor()
        self.active_allocators: List[LockFreeAllocator] = []
        self.is_running: bool = False
    
    def monitor(self) -> None:
        """Start memory reclamation monitoring."""
        self.is_running = True
    
    def stop(self) -> None:
        """Stop memory reclamation monitoring."""
        self.is_running = False
    
    def allocate(self, value: int) -> Optional[LockFreeNode]:
        """
        Allocate a new node.
        
        Args:
            value: Value to store
            
        Returns:
            New node or None
        """
        node = self.allocator.allocate(value)
        if node:
            self.active_allocators.append(self.allocator)
        return node
    
    def retire(self, node: LockFreeNode) -> bool:
        """
        Retire a node.
        
        Args:
            node: Node to retire
            
        Returns:
            True if retirement successful
        """
        if node is None:
            return False
        
        retired = self.allocator.retire(node)
        
        if retired:
            # Simulate reclamation after some time
            def _reclaim_later():
                time.sleep(0.01)  # Small delay
                reclaimed = self.allocator.reclaim_safe()
                if reclaimed:
                    self.reclamation_monitor.record_reclamation(
                        self.allocator.epoch_retirement.current_epoch,
                        len(reclaimed)
                    )
            
            threading.Thread(target=_reclaim_later, daemon=True).start()
        
        return retired
    
    def trigger_reclamation(self) -> int:
        """
        Trigger immediate reclamation.
        
        Returns:
            Number of objects reclaimed
        """
        reclaimed = self.allocator.reclaim_safe()
        self.reclamation_monitor.record_reclamation(
            self.allocator.epoch_retirement.current_epoch,
            len(reclaimed)
        )
        return len(reclaimed)
    
    def get_stats(self) -> Dict[str, any]:
        """Get combined statistics."""
        return {
            "allocator_stats": self.allocator.get_stats(),
            "monitor_stats": self.reclamation_monitor.get_stats(),
            "active_allocators": len(self.active_allocators),
        }
    
    @property
    def hazard_system(self) -> HazardPointerSystem:
        """Hazard pointer system property."""
        return self.allocator.hazard_system
    
    @property
    def epoch_retirement(self) -> EpochBasedRetirement:
        """Epoch retirement property."""
        return self.allocator.epoch_retirement


__all__ = [
    "HEH_DR_Sentry",
    "ReclamationEvent",
    "MemoryReclamationMonitor",
]