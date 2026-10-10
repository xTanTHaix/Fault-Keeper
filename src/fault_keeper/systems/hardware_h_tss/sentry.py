"""H-TSS Sentry: Pointer Tagging Monitor"""

import time
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass

from .engine import (
    H_TSSConfig,
    PointerTagger,
    BufferOverflowDetector,
    HardwarePointerTagging,
    TaggedPointer,
)


@dataclass
class UAFEvent:
    """Represents a use-after-free event."""
    timestamp: float
    address: int
    thread_id: int
    stack_trace: Optional[str] = None


class UAFMonitor:
    """Monitor for use-after-free events."""
    
    def __init__(self):
        """Initialize UAF monitor."""
        self.events: List[UAFEvent] = []
        self.lock = threading.Lock()
        self.total_uaf: int = 0
    
    def record_uaf(self, address: int, thread_id: int) -> None:
        """
        Record a UAF event.
        
        Args:
            address: Pointer address
            thread_id: Thread ID that accessed freed pointer
        """
        with self.lock:
            event = UAFEvent(
                timestamp=time.time(),
                address=address,
                thread_id=thread_id,
                stack_trace=None,
            )
            self.events.append(event)
            self.total_uaf += 1
    
    def get_uaf_rate(self, window_seconds: float = 10.0) -> float:
        """
        Get UAF rate per second.
        
        Args:
            window_seconds: Time window in seconds
            
        Returns:
            UAF rate
        """
        if not self.events:
            return 0.0
        
        # Simple rate calculation
        return self.total_uaf / window_seconds
    
    def get_stats(self) -> Dict[str, any]:
        """Get monitor statistics."""
        return {
            "total_uaf": self.total_uaf,
            "event_count": len(self.events),
            "uaf_rate": self.get_uaf_rate(),
        }


class H_TSS_Sentry:
    """Main H-TSS sentry orchestrator."""
    
    def __init__(self, config: Optional[H_TSSConfig] = None):
        """
        Initialize H-TSS sentry.
        
        Args:
            config: H-TSS configuration (optional)
        """
        self.config = config or H_TSSConfig()
        self.tagger = PointerTagger(self.config.tag_bits)
        self.overflow_detector = BufferOverflowDetector(self.config.buffer_size_limit)
        self.uaf_monitor = UAFMonitor()
        self.active_pointers: Dict[int, TaggedPointer] = {}
        self.lock = threading.Lock()
    
    def allocate(self, address: int, size: int = 1) -> TaggedPointer:
        """
        Allocate and tag a pointer.
        
        Args:
            address: Allocation address
            size: Allocation size
            
        Returns:
            Tagged pointer
        """
        pointer = self.tagger.tag_pointer(address, threading.get_ident())
        
        with self.lock:
            self.active_pointers[address] = pointer
        
        return pointer
    
    def free(self, address: int) -> bool:
        """
        Free a pointer.
        
        Args:
            address: Pointer address to free
            
        Returns:
            True if freeing successful
        """
        with self.lock:
            if address in self.active_pointers:
                pointer = self.active_pointers.pop(address)
                self.tagger.untag_pointer(address)
                return True
            return False
    
    def access(self, address: int) -> bool:
        """
        Access a pointer.
        
        Args:
            address: Pointer address to access
            
        Returns:
            True if access valid
        """
        pointer = self.tagger.validate_pointer(address)
        
        if pointer is None:
            return False
        
        if not pointer.is_valid:
            # Record UAF event
            self.uaf_monitor.record_uaf(address, threading.get_ident())
            return False
        
        return True
    
    def check_overflow(self, offset: int, size: int) -> bool:
        """
        Check for buffer overflow.
        
        Args:
            offset: Write offset
            size: Write size
            
        Returns:
            True if overflow detected
        """
        return self.overflow_detector.check_overflow(offset, size)
    
    def get_stats(self) -> Dict[str, any]:
        """Get combined statistics."""
        return {
            "active_pointers": len(self.active_pointers),
            "uaf_monitor_stats": self.uaf_monitor.get_stats(),
            "overflow_stats": self.overflow_detector.get_overflow_stats(),
        }


__all__ = [
    "H_TSS_Sentry",
    "UAFEvent",
    "UAFMonitor",
    "TaggedPointer",
]