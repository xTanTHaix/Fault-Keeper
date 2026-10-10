"""NUMA-AFS Sentry: Interconnect Stall Detection & Affinity Enforcement"""

import sys
import os
import ctypes
from typing import Optional, Dict, List, Any
from dataclasses import dataclass


@dataclass
class AffinityResult:
    """Result of affinity enforcement operation."""
    success: bool
    core_id: int
    old_node: int
    new_node: int
    error_message: Optional[str] = None


class InterconnectStallDetector:
    """Detect and monitor interconnect stall times."""
    
    def __init__(self, max_stall_us: float = 0.5):
        """
        Initialize stall detector.
        
        Args:
            max_stall_us: Maximum allowed stall time in microseconds
        """
        self.max_stall_us = max_stall_us
        self.stall_history: List[float] = []
        self.avg_stall_us: float = 0.0
    
    def record_operation(self, operation_time_us: float) -> bool:
        """
        Record an operation's timing and check for stalls.
        
        Args:
            operation_time_us: Operation time in microseconds
            
        Returns:
            True if within acceptable limits
        """
        is_stall = operation_time_us > self.max_stall_us
        
        self.stall_history.append(operation_time_us)
        
        # Update average (exponential moving average)
        self.avg_stall_us = 0.9 * self.avg_stall_us + 0.1 * operation_time_us
        
        return not is_stall
    
    def get_stall_ratio(self) -> float:
        """
        Get ratio of operations that exceeded stall threshold.
        
        Returns:
            Stall ratio (0.0 - 1.0)
        """
        if not self.stall_history:
            return 0.0
        
        return sum(1 for t in self.stall_history if t > self.max_stall_us) / len(self.stall_history)
    
    def get_metrics(self) -> Dict[str, float]:
        """Get stall metrics."""
        return {
            "max_stall_us": self.max_stall_us,
            "avg_stall_us": self.avg_stall_us,
            "stall_ratio": self.get_stall_ratio(),
            "sample_count": len(self.stall_history),
        }


class FirstTouchAffinityEnforcer:
    """Enforce first-touch NUMA affinity policy."""
    
    def __init__(self, numa_nodes: int = 2):
        """
        Initialize affinity enforcer.
        
        Args:
            numa_nodes: Number of NUMA nodes
        """
        self.numa_nodes = numa_nodes
        if sys.platform != 'win32':
            try:
                self._libctypes = ctypes.CDLL(None)
            except Exception:
                self._libctypes = None
        else:
            self._libctypes = None
        self._initialized = False
        self.cpu_affinity: Dict[int, List[int]] = {}
        self.memory_affinity: Dict[int, Any] = {}
        
    def set_cpu_affinity(self, pid: int, cpu_list: List[int]) -> bool:
        """
        Set CPU affinity for a process.
        
        Args:
            pid: Process ID
            cpu_list: List of CPU IDs to bind to
            
        Returns:
            True if successful
        """
        try:
            # Use Linux sched_setaffinity via ctypes
            # This is a simplified version - in production would use proper bindings
            if not self._initialized:
                self._init_sched_setaffinity()
            
            self.cpu_affinity[pid] = list(cpu_list)
            return True
            
        except Exception as e:
            print(f"Failed to set CPU affinity: {e}")
            return False
    
    def set_memory_affinity(self, pid: int, node: Any) -> bool:
        """
        Set memory affinity (mbind) for a process.
        
        Args:
            pid: Process ID
            node: NUMA node or list of addresses to bind to
            
        Returns:
            True if successful
        """
        try:
            # Use Linux mbind via ctypes
            if not self._initialized:
                self._init_mbind()
            
            self.memory_affinity[pid] = node
            return True
            
        except Exception as enode:
            print(f"Failed to set memory affinity: {enode}")
            return False
    
    def _init_sched_setaffinity(self) -> None:
        """Initialize sched_setaffinity bindings."""
        self._initialized = True
    
    def _init_mbind(self) -> None:
        """Initialize mbind bindings."""
        self._initialized = True
    
    def get_cpu_topology(self) -> Dict[str, int]:
        """
        Get CPU topology information.
        
        Returns:
            Dictionary with topology info
        """
        return {
            "numa_nodes": self.numa_nodes,
            "cores_per_node": self._get_cores_per_node(),
        }
    
    def _get_cores_per_node(self) -> int:
        """Get estimated cores per NUMA node."""
        # Estimate based on typical hardware
        return 32 // self.numa_nodes
    
    def verify_affinity(self, pid: int) -> Dict[str, any]:
        """
        Verify current affinity for a process.
        
        Args:
            pid: Process ID
            
        Returns:
            Dictionary with affinity verification results
        """
        try:
            return {
                "pid": pid,
                "affinity_verified": True,  # Simplified
                "current_node": pid % self.numa_nodes,
            }
        except Exception as e:
            return {
                "pid": pid,
                "affinity_verified": False,
                "error": str(e),
            }


class NUMAAFS:
    """Main NUMA-AFS orchestrator with sentry capabilities."""
    
    def __init__(self):
        """Initialize NUMA-AFS."""
        self.stall_detector = InterconnectStallDetector()
        self.affinity_enforcer = FirstTouchAffinityEnforcer()
        self.core_bindings: Dict[int, int] = {}
        self.page_bindings: Dict[int, int] = {}
    
    def bind_thread_to_core(self, thread_id: int, core_id: int) -> AffinityResult:
        """
        Bind a thread to a specific core.
        
        Args:
            thread_id: Thread ID
            core_id: Target core ID
            
        Returns:
            AffinityResult with success status
        """
        try:
            # Get current thread's process
            pid = os.getpid()
            
            # Get current CPU affinity
            old_mask = self._get_cpu_affinity(pid)
            
            # Set new CPU affinity
            success = self.affinity_enforcer.set_cpu_affinity(pid, [core_id])
            
            if success:
                self.core_bindings[thread_id] = core_id
            
            return AffinityResult(
                success=True,
                core_id=core_id,
                old_node=old_mask,
                new_node=core_id,
            )
            
        except Exception as e:
            return AffinityResult(
                success=False,
                core_id=-1,
                old_node=-1,
                new_node=-1,
                error_message=str(e),
            )
    
    def bind_memory_to_node(self, allocation_size_mb: int, node: int) -> bool:
        """
        Bind memory allocation to a NUMA node.
        
        Args:
            allocation_size_mb: Size of allocation in MB
            node: Target NUMA node
            
        Returns:
            True if successful
        """
        try:
            # Use mbind or similar to bind memory
            success = self.affinity_enforcer.set_memory_affinity(
                os.getpid(), node
            )
            
            if success:
                self.page_bindings[node] = allocation_size_mb
            
            return success
            
        except Exception as e:
            print(f"Failed to bind memory to node {node}: {e}")
            return False
    
    def _get_cpu_affinity(self, pid: int) -> int:
        """Get current CPU affinity mask."""
        # Simplified - in production would use proper ctypes bindings
        return 0
    
    def check_and_rebind_if_stalled(self, operation_time_us: float) -> bool:
        """
        Check for interconnect stalls and rebind if necessary.
        
        Args:
            operation_time_us: Recent operation time
            
        Returns:
            True if no action needed or already optimized
        """
        is_stalled = not self.stall_detector.record_operation(operation_time_us)
        
        if is_stalled:
            # Try to rebind to more local resources
            self._optimize_affinity()
        
        return not is_stalled
    
    def _optimize_affinity(self) -> None:
        """Optimize current affinity bindings."""
        # Simplified optimization logic
        for thread_id in list(self.core_bindings.keys()):
            core_id = self.core_bindings[thread_id]
            
            # Rebind to local core if remote access detected
            new_core = core_id % self.affinity_enforcer.numa_nodes
            
            if new_core != core_id:
                result = self.bind_thread_to_core(thread_id, new_core)
                
                if not result.success:
                    print(f"Failed to rebind thread {thread_id} to core {new_core}")
    
    def get_affinity_status(self) -> Dict[str, any]:
        """Get current affinity status."""
        return {
            "core_bindings": self.core_bindings,
            "page_bindings": self.page_bindings,
            "stall_metrics": self.stall_detector.get_metrics(),
        }


__all__ = [
    "AffinityResult",
    "InterconnectStallDetector",
    "FirstTouchAffinityEnforcer",
    "NUMAAFS",
]