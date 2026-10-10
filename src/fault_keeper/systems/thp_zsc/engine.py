"""ZSC-THP Engine: Dual-Pool Hybrid Allocation Arena & Compaction Siphon"""

import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np


@dataclass
class MemoryArena:
    """Represents a memory arena."""
    name: str
    size_mb: int
    page_size_kb: int
    allocated_pages: int = 0
    is_static: bool = False
    
    @property
    def total_pages(self) -> int:
        """Get total pages in arena."""
        return self.size_mb * 1024 // self.page_size_kb
    
    @property
    def free_pages(self) -> int:
        """Get free pages in arena."""
        return self.total_pages - self.allocated_pages
    
    @property
    def utilization_percent(self) -> float:
        """Get utilization percentage."""
        if self.total_pages == 0:
            return 0.0
        return (self.allocated_pages / self.total_pages) * 100.0


class DualPoolHybridAllocator:
    """Dual-Pool Hybrid Allocation Arena (DHACS)."""
    
    def __init__(self, static_arena_size_mb: int = 2048, 
                 dynamic_arena_size_mb: int = 4096,
                 thp_page_size_kb: int = 2048):
        """
        Initialize Dual-Pool Hybrid Allocator.
        
        Args:
            static_arena_size_mb: Size of static arena in MB (for critical path)
            dynamic_arena_size_mb: Size of dynamic arena in MB (for non-critical)
            thp_page_size_kb: Page size for THP (2MB default)
        """
        self.static_arena = MemoryArena(
            name="Static Arena (THP)",
            size_mb=static_arena_size_mb,
            page_size_kb=thp_page_size_kb,
            is_static=True
        )
        
        self.dynamic_arena = MemoryArena(
            name="Dynamic Arena (4KB)",
            size_mb=dynamic_arena_size_mb,
            page_size_kb=4,  # 4KB pages for non-critical
            is_static=False
        )
        
        self.total_allocated_pages: int = 0
        self.lock = threading.Lock()
    
    def allocate_critical(self, pages_needed: int) -> Optional[int]:
        """
        Allocate pages from static THP arena (critical path).
        
        Args:
            pages_needed: Number of pages to allocate
            
        Returns:
            Virtual address or None if allocation failed
        """
        with self.lock:
            if self.static_arena.free_pages >= pages_needed:
                self.static_arena.allocated_pages += pages_needed
                self.total_allocated_pages += pages_needed
                
                # Simulate THP allocation (return virtual address)
                return f"0x{self._generate_address(self.static_arena)}"
            
            return None
    
    def allocate_non_critical(self, pages_needed: int) -> Optional[int]:
        """
        Allocate pages from dynamic arena (non-critical path).
        
        Args:
            pages_needed: Number of pages to allocate
            
        Returns:
            Virtual address or None if allocation failed
        """
        with self.lock:
            if self.dynamic_arena.free_pages >= pages_needed:
                self.dynamic_arena.allocated_pages += pages_needed
                self.total_allocated_pages += pages_needed
                
                # Simulate 4KB page allocation
                return f"0x{self._generate_address(self.dynamic_arena)}"
            
            return None
    
    def _generate_address(self, arena: MemoryArena) -> str:
        """Generate a simulated virtual address."""
        base = int(arena.size_mb * 1024 * 1024 * (1 - arena.utilization_percent / 100))
        return f"0x{base:x}"
    
    def get_allocation_stats(self) -> Dict[str, any]:
        """Get allocation statistics."""
        return {
            "static_arena": {
                "name": self.static_arena.name,
                "size_mb": self.static_arena.size_mb,
                "total_pages": self.static_arena.total_pages,
                "allocated_pages": self.static_arena.allocated_pages,
                "free_pages": self.static_arena.free_pages,
                "utilization_percent": self.static_arena.utilization_percent,
            },
            "dynamic_arena": {
                "name": self.dynamic_arena.name,
                "size_mb": self.dynamic_arena.size_mb,
                "total_pages": self.dynamic_arena.total_pages,
                "allocated_pages": self.dynamic_arena.allocated_pages,
                "free_pages": self.dynamic_arena.free_pages,
                "utilization_percent": self.dynamic_arena.utilization_percent,
            },
            "total_allocated_pages": self.total_allocated_pages,
        }
    
    def get_allocation_efficiency(self) -> float:
        """Get overall allocation efficiency."""
        if self.total_allocated_pages == 0:
            return 1.0
        
        # Efficiency = (THP pages used) / (Total pages allocated)
        efficiency = self.static_arena.allocated_pages / self.total_allocated_pages
        return float(min(max(efficiency, 0.0), 1.0))


class THPCompactionSiphon:
    """Background Page Compaction Siphon via process_madvise."""
    
    def __init__(self, arena: DualPoolHybridAllocator,
                 madvise_collapsed_pages: int = 1024):
        """
        Initialize compaction siphon.
        
        Args:
            arena: Memory arena to compact
            madvise_collapsed_pages: Number of pages to collapse per operation
        """
        self.arena = arena
        self.madvise_collapsed_pages = madvise_collapsed_pages
        self.compaction_count: int = 0
        self.last_compaction_time: float = 0.0
        self.lock = threading.Lock()
    
    def run_background_compaction(self) -> bool:
        """
        Run background compaction via process_madvise.
        
        Returns:
            True if compaction completed successfully
        """
        start_time = time.time()
        
        try:
            # Simulate MADV_COLLAPSE operation
            pages_collapsed = self.madvise_collapsed_pages
            
            with self.lock:
                self.compaction_count += 1
                self.last_compaction_time = time.time()
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Critical path should have zero stall
            is_critical_path = duration_ms < 1.0  # < 1ms
            
            return is_critical_path
            
        except Exception as e:
            print(f"Compaction error: {e}")
            return False
    
    def compact_specific_pages(self, pages: List[int]) -> int:
        """
        Compact specific pages.
        
        Args:
            pages: List of page addresses to compact
            
        Returns:
            Number of pages compacted
        """
        if not pages:
            return 0
        
        with self.lock:
            # Simulate compaction
            compacted_count = min(len(pages), self.madvise_collapsed_pages)
            
            self.compaction_count += 1
        
        return compacted_count
    
    def get_compaction_stats(self) -> Dict[str, any]:
        """Get compaction statistics."""
        return {
            "compaction_count": self.compaction_count,
            "last_compaction_time": self.last_compaction_time,
            "avg_compaction_interval_s": 0.0 if self.compaction_count < 2 else \
                (time.time() - self.last_compaction_time) / self.compaction_count,
        }


class ZSC_ThP:
    """Main ZSC-THP orchestrator."""
    
    def __init__(self):
        """Initialize ZSC-THP."""
        self.allocator = DualPoolHybridAllocator()
        self.siphon = THPCompactionSiphon(self.allocator)
        self.critical_allocations: List[str] = []
        self.non_critical_allocations: List[str] = []
        self.is_compacting: bool = False
    
    def allocate(self, size: int, is_critical: bool = False) -> Optional[str]:
        """
        Allocate memory of given size.
        
        Args:
            size: Size in bytes or MB
            is_critical: Whether allocation is for critical path
            
        Returns:
            Virtual address or None if failed
        """
        size_mb = max(1, size // (1024 * 1024)) if size >= 1024 * 1024 else max(1, size // 1024) if size >= 1024 else max(1, size)
        return self.allocate_memory(size_mb, is_critical)
    
    def allocate_memory(self, size_mb: int, is_critical: bool = False) -> Optional[str]:
        """
        Allocate memory from appropriate arena.
        
        Args:
            size_mb: Size to allocate in MB
            is_critical: Whether allocation is for critical path
            
        Returns:
            Virtual address or None if failed
        """
        # Convert MB to pages
        thp_page_size_kb = 2048  # 2MB THP
        pages_needed = max(1, (size_mb * 1024) // thp_page_size_kb)
        
        if is_critical:
            addr = self.allocator.allocate_critical(pages_needed)
            if addr:
                self.critical_allocations.append(addr)
            return addr
        else:
            addr = self.allocator.allocate_non_critical(pages_needed)
            if addr:
                self.non_critical_allocations.append(addr)
            return addr
    
    def trigger_background_compaction(self) -> bool:
        """Trigger background compaction."""
        self.is_compacting = True
        return self.siphon.run_background_compaction()
    
    def check_fragmentation(self) -> Tuple[bool, float]:
        """
        Check memory fragmentation level.
        
        Returns:
            Tuple of (is_fragmented, fragmentation_percent)
        """
        stats = self.allocator.get_allocation_stats()
        
        # Calculate fragmentation based on free pages distribution
        static_free = stats["static_arena"]["free_pages"]
        dynamic_free = stats["dynamic_arena"]["free_pages"]
        
        total_free = static_free + dynamic_free
        total_pages = stats["static_arena"]["total_pages"] + stats["dynamic_arena"]["total_pages"]
        
        if total_pages == 0:
            return False, 0.0
        
        fragmentation = (total_pages - total_free) / total_pages * 100.0
        is_fragmented = fragmentation > 75.0  # 75% threshold
        
        return is_fragmented, fragmentation
    
    def get_allocation_efficiency(self) -> float:
        """Get overall allocation efficiency."""
        return self.allocator.get_allocation_efficiency()
    
    def get_full_stats(self) -> Dict[str, any]:
        """Get full statistics."""
        return {
            "allocation_stats": self.allocator.get_allocation_stats(),
            "compaction_stats": self.siphon.get_compaction_stats(),
            "critical_allocations_count": len(self.critical_allocations),
            "non_critical_allocations_count": len(self.non_critical_allocations),
            "allocation_efficiency": self.get_allocation_efficiency(),
        }


__all__ = [
    "ZSC_ThP",
    "DualPoolHybridAllocator",
    "THPCompactionSiphon",
    "MemoryArena",
]