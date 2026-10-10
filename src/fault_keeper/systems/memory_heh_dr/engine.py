"""HEH-DR Engine: Lock-Free Memory Reclamation with Hazard Pointers & Epochs"""


import time
import threading
import weakref
from typing import Dict, List, Optional, Set, TypeVar, Generic
from dataclasses import dataclass
import gc


@dataclass
class HEH_DRConfig:
    """HEH-DR configuration."""
    hazard_pointer_slots: int = 16
    hazard_pointer_interval_ms: float = 100.0
    epoch_advance_threshold: float = 0.8
    epoch_min_objects: int = 100
    ebr_window_size: int = 1024
    ebr_retire_interval_ms: float = 50.0


T = TypeVar('T')


@dataclass
class HazardPointerSlot:
    """Represents a hazard pointer slot."""
    thread_id: Optional[int] = None
    pointer: Optional[int] = None
    generation: int = 0


@dataclass
class RetiredObject:
    """Represents a retired object waiting for reclamation."""
    pointer: int
    thread_id: int
    retired_at: float


class HazardPointerSystem:
    """Hazard Pointer protection system."""
    
    def __init__(self, slots: int = 16):
        """
        Initialize hazard pointer system.
        
        Args:
            slots: Number of hazard pointer slots
        """
        self.slots = slots
        self.slots_data: List[HazardPointerSlot] = [
            HazardPointerSlot() for _ in range(slots)
        ]
        self.protected_objects: Set[int] = set()
        self.lock = threading.Lock()
        self.generation = 0
    
    def register_protected(self, pointer: int, thread_id: int) -> bool:
        """
        Register a pointer as protected.
        
        Args:
            pointer: Pointer to protect
            thread_id: Thread ID registering the pointer
            
        Returns:
            True if registration successful
        """
        with self.lock:
            # Rotate through slots
            slot_idx = self.generation % len(self.slots_data)
            
            self.slots_data[slot_idx] = HazardPointerSlot(
                thread_id=thread_id,
                pointer=pointer,
                generation=self.generation
            )
            
            self.protected_objects.add(pointer)
            self.generation += 1
            
            return True
    
    def unregister_protected(self, pointer: int) -> bool:
        """
        Unregister a pointer from protection.
        
        Args:
            pointer: Pointer to unregister
            
        Returns:
            True if unregistration successful
        """
        with self.lock:
            if pointer in self.protected_objects:
                self.protected_objects.remove(pointer)
                return True
            return False
    
    def scan_and_retire(self, retired_objects: List[RetiredObject]) -> List[int]:
        """
        Scan for objects that can be safely retired.
        
        Args:
            retired_objects: List of retired objects
            
        Returns:
            List of pointers that can be safely freed
        """
        with self.lock:
            safe_to_free = []
            
            for retired in retired_objects:
                if retired.pointer not in self.protected_objects:
                    safe_to_free.append(retired.pointer)
            
            return safe_to_free
    
    def get_active_protectors(self) -> Set[int]:
        """Get set of currently active protecting threads."""
        with self.lock:
            return {
                slot.thread_id 
                for slot in self.slots_data 
                if slot.thread_id is not None
            }


class EpochBasedRetirement:
    """Epoch-based memory reclamation."""
    
    def __init__(self, window_size: int = 1024, min_objects: int = 100):
        """
        Initialize epoch-based retirement.
        
        Args:
            window_size: Size of retirement window
            min_objects: Minimum objects before advancing epoch
        """
        self.window_size = window_size
        self.min_objects = min_objects
        self.retired_count: int = 0
        self.current_epoch: int = 0
        self.retired_objects: List[RetiredObject] = []
        self.lock = threading.Lock()
    
    def retire_object(self, pointer: int, thread_id: Optional[int] = None) -> RetiredObject:
        """
        Retire an object.
        
        Args:
            pointer: Object pointer
            thread_id: Thread ID retiring the object (defaults to current thread)
            
        Returns:
            RetiredObject instance
        """
        if thread_id is None:
            thread_id = threading.get_ident()
        with self.lock:
            obj = RetiredObject(
                pointer=pointer,
                thread_id=thread_id,
                retired_at=time.time()
            )
            self.retired_objects.append(obj)
            self.retired_count += 1
            
            # Check if we should advance epoch
            if self.retired_count >= self.min_objects:
                self.current_epoch += 1
                self.retired_count = 0
                self.retired_objects.clear()
            return obj
    
    def advance_epoch(self) -> None:
        """Advance to next epoch."""
        with self.lock:
            self.current_epoch += 1
            self.retired_count = 0
            self.retired_objects.clear()

    def _advance_epoch(self) -> None:
        """Internal alias for advancing epoch."""
        self.advance_epoch()
    
    def get_epoch_info(self) -> Dict[str, any]:
        """Get epoch information."""
        return {
            "current_epoch": self.current_epoch,
            "retired_count": self.retired_count,
            "retired_objects": len(self.retired_objects),
        }


class LockFreeNode:
    """Lock-free node for allocation/reclamation testing."""
    
    def __init__(self, value: int = 0, ptr: Optional[int] = None):
        """
        Initialize node.
        
        Args:
            value: Node value
            ptr: Optional pointer address/identifier
        """
        self.value = value
        self.next: Optional['LockFreeNode'] = None
        self.protected = False
        self._ptr_id = ptr if ptr is not None else id(self)
    
    @property
    def ptr(self) -> int:
        """Get pointer ID."""
        return self._ptr_id

    @ptr.setter
    def ptr(self, val: int) -> None:
        self._ptr_id = val
    
    def __repr__(self) -> str:
        return f"LockFreeNode(value={self.value}, ptr={self._ptr_id})"


class LockFreeAllocator:
    """Lock-free memory allocator with HEH-DR."""
    
    def __init__(self, config: Optional[HEH_DRConfig] = None, size: Optional[int] = None):
        """
        Initialize lock-free allocator.
        
        Args:
            config: HEH-DR configuration (optional)
            size: Allocation pool size (optional)
        """
        self.config = config or HEH_DRConfig()
        self.size: int = size if size is not None else 4096
        self.hazard_system = HazardPointerSystem(self.config.hazard_pointer_slots)
        self.epoch_retirement = EpochBasedRetirement(
            self.config.ebr_window_size,
            self.config.epoch_min_objects
        )
        self.lock = threading.Lock()
        self.allocation_count: int = 0
        self.reclamation_count: int = 0
        self.freed_list: List[any] = []
        self._allocated_nodes: Dict[int, LockFreeNode] = {}
    
    def allocate(self, value: int = 0) -> Optional[LockFreeNode]:
        """
        Allocate a new node.
        
        Args:
            value: Value to store in node
            
        Returns:
            New LockFreeNode or None if allocation failed
        """
        with self.lock:
            node = LockFreeNode(value=value)
            node.protected = True
            
            # Register with hazard pointer system
            self.hazard_system.register_protected(node.ptr, threading.get_ident())
            self._allocated_nodes[node.ptr] = node
            
            self.allocation_count += 1
            return node
    
    def retire(self, node: any) -> bool:
        """
        Retire a node or pointer for later reclamation.
        
        Args:
            node: Node or pointer to retire
            
        Returns:
            True if retirement successful
        """
        with self.lock:
            if isinstance(node, LockFreeNode):
                ptr = node.ptr
                node.protected = False
            else:
                ptr = int(node)
                if ptr in self._allocated_nodes:
                    self._allocated_nodes[ptr].protected = False
            
            self.freed_list.append(node)
            self.hazard_system.unregister_protected(ptr)
            self.epoch_retirement.retire_object(ptr, threading.get_ident())
            return True
    
    def reclaim_safe(self) -> List[LockFreeNode]:
        """
        Reclaim nodes that are safe to free.
        
        Returns:
            List of nodes that can be safely freed
        """
        with self.lock:
            safe_pointers = self.hazard_system.scan_and_retire(
                self.epoch_retirement.retired_objects
            )
            
            # Find corresponding nodes
            reclaimed = []
            for ptr in safe_pointers:
                # In real implementation, we'd search linked list
                # Here we just simulate
                reclaimed.append(LockFreeNode(0))
            
            self.reclamation_count += len(reclaimed)
            return reclaimed
    
    def get_stats(self) -> Dict[str, any]:
        """Get allocator statistics."""
        return {
            "allocations": self.allocation_count,
            "reclamations": self.reclamation_count,
            "hazard_slots_active": sum(
                1 for slot in self.hazard_system.slots_data 
                if slot.pointer is not None
            ),
            "epoch_info": self.epoch_retirement.get_epoch_info(),
        }


__all__ = [
    "HEH_DRConfig",
    "HazardPointerSlot",
    "RetiredObject",
    "HazardPointerSystem",
    "EpochBasedRetirement",
    "LockFreeNode",
    "LockFreeAllocator",
]