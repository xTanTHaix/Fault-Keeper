"""DMCS Sentry: Dominator Tree & Min-Cut Leak Reclamation Monitor."""

import time
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .config import DMCSConfig
from .engine import (
    MemoryBlock,
    DominatorTree,
    MinCutAnalyzer,
    LeakDetector,
    DMCS,
)


@dataclass
class LeakRecoveryEvent:
    """Represents a cyclic memory leak reclamation event."""
    timestamp: float
    blocks_reclaimed: int
    bytes_reclaimed: int
    cut_weight: float
    duration_us: float


class LeakSentryMonitor:
    """Monitor for memory reclamation and cycle break events."""

    def __init__(self):
        """Initialize reclamation monitor."""
        self.events: List[LeakRecoveryEvent] = []
        self.total_reclaimed_bytes: int = 0
        self.total_reclaimed_blocks: int = 0
        self.lock = threading.RLock()

    def record_recovery(
        self,
        blocks_reclaimed: int,
        bytes_reclaimed: int,
        cut_weight: float = 0.0,
        duration_us: float = 0.0,
    ) -> None:
        """
        Record a memory recovery event.

        Args:
            blocks_reclaimed: Number of blocks reclaimed
            bytes_reclaimed: Total bytes recovered
            cut_weight: Min-cut objective value / edge weight
            duration_us: Execution duration in microseconds
        """
        with self.lock:
            event = LeakRecoveryEvent(
                timestamp=time.time(),
                blocks_reclaimed=blocks_reclaimed,
                bytes_reclaimed=bytes_reclaimed,
                cut_weight=cut_weight,
                duration_us=duration_us,
            )
            self.events.append(event)
            self.total_reclaimed_blocks += blocks_reclaimed
            self.total_reclaimed_bytes += bytes_reclaimed

    def get_avg_recovery_time_us(self) -> float:
        """Get average recovery duration in microseconds."""
        with self.lock:
            if not self.events:
                return 0.0
            return sum(e.duration_us for e in self.events) / len(self.events)

    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        with self.lock:
            return {
                "total_events": len(self.events),
                "total_reclaimed_blocks": self.total_reclaimed_blocks,
                "total_reclaimed_bytes": self.total_reclaimed_bytes,
                "avg_recovery_time_us": self.get_avg_recovery_time_us(),
            }


class DMCS_Sentry:
    """Main DMCS Sentry orchestrator for proactive leak monitoring."""

    def __init__(self, config: Optional[DMCSConfig] = None):
        """
        Initialize DMCS Sentry.

        Args:
            config: DMCS configuration (optional)
        """
        self.config = config or DMCSConfig()
        self.dmcs = DMCS(self.config)
        self.reclamation_monitor = LeakSentryMonitor()
        self.is_monitoring: bool = False
        self.lock = threading.RLock()

    def monitor(self) -> None:
        """Start memory reclamation monitoring."""
        self.is_monitoring = True

    def stop(self) -> None:
        """Stop memory reclamation monitoring."""
        self.is_monitoring = False

    def allocate(self, address: int, size: int, thread_id: int = 1) -> MemoryBlock:
        """
        Allocate a memory block through DMCS.

        Args:
            address: Memory address
            size: Block size in bytes
            thread_id: Allocating thread ID

        Returns:
            Tracked MemoryBlock
        """
        return self.dmcs.allocate(address, size, thread_id)

    def add_reference(self, src_address: int, dst_address: int) -> None:
        """
        Add a reference between blocks.

        Args:
            src_address: Source pointer
            dst_address: Target pointer
        """
        self.dmcs.add_reference(src_address, dst_address)

    def diagnose_and_reclaim(self) -> Tuple[int, int]:
        """
        Run dominator analysis, diagnose leaks, and execute min-cut reclamation.

        Returns:
            Tuple of (blocks_reclaimed, bytes_reclaimed)
        """
        start_t = time.perf_counter()
        
        # Check suspected leaks
        leaked = self.dmcs.diagnose_leaks()
        if not leaked:
            return 0, 0

        bytes_to_reclaim = sum(b.size for b in leaked)
        reclaimed_blocks = self.dmcs.min_cut.apply_min_cut(leaked)

        with self.dmcs.lock:
            for block in reclaimed_blocks:
                if block in self.dmcs.blocks:
                    self.dmcs.blocks.remove(block)

        reclaimed_count = len(reclaimed_blocks)
        duration_us = max(0.1, (time.perf_counter() - start_t) * 1_000_000)

        # Record in sentry monitor
        self.reclamation_monitor.record_recovery(
            blocks_reclaimed=reclaimed_count,
            bytes_reclaimed=bytes_to_reclaim,
            cut_weight=float(reclaimed_count),
            duration_us=duration_us,
        )

        return reclaimed_count, bytes_to_reclaim

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            "dmcs_stats": self.dmcs.get_recovery_stats(),
            "monitor_stats": self.reclamation_monitor.get_stats(),
            "is_monitoring": self.is_monitoring,
        }

    def get_full_stats(self) -> Dict[str, Any]:
        """Get full telemetry statistics."""
        return self.get_stats()


__all__ = [
    "DMCS_Sentry",
    "LeakRecoveryEvent",
    "LeakSentryMonitor",
]
