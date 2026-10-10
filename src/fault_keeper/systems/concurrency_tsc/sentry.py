"""TSCA Sentry: Runtime Concurrency Deadlock Monitor & Simplicial Homology Auditor."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .config import TSCAConfig
from .engine import SimplicialComplex, HomologyEngine, TSCAEngine


@dataclass
class DeadlockAlert:
    """Represents a topological deadlock alert triggered by beta_1 >= 1."""

    timestamp: float
    betti_1: int
    cycle_nodes: List[int]
    message: str


class TSCASentry:
    """Sentry monitoring thread-resource acquisition topology and homological cycles."""

    def __init__(self, config: Optional[TSCAConfig] = None) -> None:
        self.config = config or TSCAConfig()
        self.engine = TSCAEngine(self.config)
        self.lock = threading.Lock()
        self.alerts: List[DeadlockAlert] = []
        self._held_resources: Dict[int, int] = {}  # resource_id -> thread_id
        self._waiting_threads: Dict[int, int] = {}  # thread_id -> resource_id

    def record_acquisition(self, thread_id: int, resource_id: int) -> None:
        """Record thread acquiring ownership of a resource."""
        with self.lock:
            self._held_resources[resource_id] = thread_id
            if thread_id in self._waiting_threads and self._waiting_threads[thread_id] == resource_id:
                del self._waiting_threads[thread_id]
            self.engine.register_transition(thread_id, resource_id)

    def record_wait(self, thread_id: int, resource_id: int) -> Optional[DeadlockAlert]:
        """Record thread waiting for a resource; verify topological safety."""
        with self.lock:
            self._waiting_threads[thread_id] = resource_id
            self.engine.register_transition(thread_id, resource_id)
            holder = self._held_resources.get(resource_id)

            analysis = self.engine.analyze_topology()
            beta_1 = int(analysis["first_betti_number"])
            if beta_1 >= self.config.deadlock_cycle_threshold:
                alert = DeadlockAlert(
                    timestamp=time.time(),
                    betti_1=beta_1,
                    cycle_nodes=[thread_id, resource_id, holder] if holder else [thread_id, resource_id],
                    message=f"Deadlock cycle detected via Simplicial Homology: beta_1={beta_1}",
                )
                self.alerts.append(alert)
                return alert
            return None

    def record_release(self, thread_id: int, resource_id: int) -> None:
        """Record thread releasing a resource."""
        with self.lock:
            if self._held_resources.get(resource_id) == thread_id:
                del self._held_resources[resource_id]

    def audit_concurrency_invariants(self) -> Dict[str, object]:
        """Audit current topological concurrency state against mathematical invariants."""
        with self.lock:
            analysis = self.engine.analyze_topology()
            return {
                "active_alerts": len(self.alerts),
                "is_deadlock_free": analysis["is_deadlock_free"],
                "first_betti_number": analysis["first_betti_number"],
                "total_transitions": analysis["num_edges"],
            }


__all__ = ["DeadlockAlert", "TSCASentry"]
