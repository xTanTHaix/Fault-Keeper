"""H-TSS Engine: Hardware Pointer Tagging & Buffer Overflow Detection"""


import time
import threading
import struct
from typing import Dict, List, Optional, Set
from dataclasses import dataclass


@dataclass
class H_TSSConfig:
    """H-TSS configuration."""
    tag_bits: int = 4
    tag_mask: int = 0xF
    buffer_size_limit: int = 1024 * 1024
    overflow_threshold_percent: float = 95.0
    uaf_detection_enabled: bool = True
    uaf_check_interval_ms: float = 10.0
    validate_on_access: bool = True
    tag_mismatch_action: str = "abort"


@dataclass
class TaggedPointer:
    """Tagged pointer with validity metadata."""
    address: int
    tag: int
    is_valid: bool
    allocation_time: float
    thread_id: int


class PointerTagger:
    """Hardware pointer tagging simulator."""
    
    def __init__(self, tag_bits: int = 4):
        """
        Initialize pointer tagger.
        
        Args:
            tag_bits: Number of bits for tag
        """
        self.tag_bits = tag_bits
        self.tag_mask = (1 << tag_bits) - 1
        self.tagged_pointers: Dict[int, TaggedPointer] = {}
        self.lock = threading.Lock()
    
    def tag_pointer(self, address: int, thread_id: int) -> TaggedPointer:
        """
        Tag a pointer.
        
        Args:
            address: Pointer address
            thread_id: Thread ID tagging the pointer
            
        Returns:
            Tagged pointer
        """
        tag = address & self.tag_mask
        
        pointer = TaggedPointer(
            address=address,
            tag=tag,
            is_valid=True,
            allocation_time=time.time(),
            thread_id=thread_id,
        )
        
        with self.lock:
            self.tagged_pointers[address] = pointer
        
        return pointer
    
    def validate_pointer(self, address: int) -> Optional[TaggedPointer]:
        """
        Validate a pointer.
        
        Args:
            address: Pointer address to validate
            
        Returns:
            Tagged pointer or None if not found/invalid
        """
        with self.lock:
            if address in self.tagged_pointers:
                pointer = self.tagged_pointers[address]
                
                # Check if pointer is still valid
                if pointer.is_valid:
                    return pointer
                
                # Pointer was freed but tag still exists
                pointer.is_valid = False
                return pointer
            
            return None
    
    def untag_pointer(self, address: int) -> bool:
        """
        Untag a pointer (mark as invalid).
        
        Args:
            address: Pointer address to untag
            
        Returns:
            True if untagging successful
        """
        with self.lock:
            if address in self.tagged_pointers:
                self.tagged_pointers[address].is_valid = False
                return True
            return False
    
    def check_uaf(self, address: int) -> bool:
        """
        Check for use-after-free.
        
        Args:
            address: Pointer address to check
            
        Returns:
            True if UAF detected
        """
        pointer = self.validate_pointer(address)
        
        if pointer is None:
            return False  # Pointer never tagged
        
        return not pointer.is_valid
    
    def get_active_pointers(self) -> List[TaggedPointer]:
        """Get list of active (valid) pointers."""
        with self.lock:
            return [
                ptr for ptr in self.tagged_pointers.values()
                if ptr.is_valid
            ]


class BufferOverflowDetector:
    """Buffer overflow detection using tagged pointers."""
    
    def __init__(self, buffer_size_limit: int = 1024 * 1024):
        """
        Initialize buffer overflow detector.
        
        Args:
            buffer_size_limit: Maximum buffer size
        """
        self.buffer_size_limit = buffer_size_limit
        self.overflow_count: int = 0
        self.overflow_history: List[Dict] = []
        self.lock = threading.Lock()
    
    def check_overflow(self, offset: int, size: int) -> bool:
        """
        Check if write would overflow buffer.
        
        Args:
            offset: Write offset
            size: Write size
            
        Returns:
            True if overflow would occur
        """
        if offset + size > self.buffer_size_limit:
            with self.lock:
                self.overflow_count += 1
                self.overflow_history.append({
                    "offset": offset,
                    "size": size,
                    "timestamp": time.time(),
                })
            return True
        return False
    
    def get_overflow_stats(self) -> Dict[str, any]:
        """Get overflow statistics."""
        with self.lock:
            return {
                "overflow_count": self.overflow_count,
                "overflow_history": self.overflow_history[-10:],  # Last 10 events
            }


class HardwarePointerTagging:
    """Main hardware pointer tagging orchestrator."""
    
    def __init__(self, config: Optional[H_TSSConfig] = None):
        """
        Initialize hardware pointer tagging.
        
        Args:
            config: H-TSS configuration (optional)
        """
        self.config = config or H_TSSConfig()
        self.tagger = PointerTagger(self.config.tag_bits)
        self.overflow_detector = BufferOverflowDetector(self.config.buffer_size_limit)
        self.active_pointers: Set[int] = set()
        self.lock = threading.Lock()
    
    def allocate_tagged(self, address: int, size: int = 1) -> TaggedPointer:
        """
        Allocate and tag a pointer.
        
        Args:
            address: Allocation address
            size: Allocation size
            
        Returns:
            Tagged pointer
        """
        # Check for overflow
        try:
            if self.overflow_detector.check_overflow(address, size):
                raise ValueError("Buffer overflow detected")
        except ValueError:
            raise
        
        pointer = self.tagger.tag_pointer(address, threading.get_ident())
        
        with self.lock:
            self.active_pointers.add(address)
        
        return pointer
    
    def free_pointer(self, address: int) -> bool:
        """
        Free a pointer (mark as invalid).
        
        Args:
            address: Pointer address to free
            
        Returns:
            True if freeing successful
        """
        with self.lock:
            if address in self.active_pointers:
                self.tagger.untag_pointer(address)
                self.active_pointers.remove(address)
                return True
            return False
    
    def access_pointer(self, address: int) -> bool:
        """
        Access a pointer (validate tag).
        
        Args:
            address: Pointer address to access
            
        Returns:
            True if access valid
        """
        if not self.config.validate_on_access:
            return True
        
        pointer = self.tagger.validate_pointer(address)
        
        if pointer is None:
            return False
        
        if not pointer.is_valid:
            # Use-after-free detected
            if self.config.tag_mismatch_action == "abort":
                try:
                    raise RuntimeError("Use-after-free detected!")
                except RuntimeError:
                    raise
            return False
        
        return True
    
    def check_uaf(self, address: int) -> bool:
        """
        Check for use-after-free.
        
        Args:
            address: Pointer address to check
            
        Returns:
            True if UAF detected
        """
        return self.tagger.check_uaf(address)
    
    def get_stats(self) -> Dict[str, any]:
        """Get tagging statistics."""
        return {
            "active_pointers": len(self.active_pointers),
            "tagged_pointers_count": len(self.tagger.tagged_pointers),
            "overflow_stats": self.overflow_detector.get_overflow_stats(),
        }


__all__ = [
    "H_TSSConfig",
    "TaggedPointer",
    "PointerTagger",
    "BufferOverflowDetector",
    "HardwarePointerTagging",
]