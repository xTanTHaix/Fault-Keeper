"""AC-SBE Sentry: Event-Loop Heartbeat Lag Monitor & Preemption Guard."""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import ACSBEConfig
from .engine import AutoYieldTransformer, BlockingLoopDetector, LoopCostEstimator


@dataclass
class EventLoopStallEvent:
    """Represents a detected synchronous blocking stall in an event loop."""

    timestamp: float
    duration_sec: float
    coroutine_name: Optional[str]
    threshold_sec: float


class ACSBESentry:
    """Sentry monitoring async event loop latency and identifying synchronous starvation."""

    def __init__(self, config: Optional[ACSBEConfig] = None) -> None:
        self.config = config or ACSBEConfig()
        self.detector = BlockingLoopDetector()
        self.transformer = AutoYieldTransformer(cadence=self.config.yield_cadence)
        self.stalls: List[EventLoopStallEvent] = []
        self._last_heartbeat = time.time()
        self.lock = threading.Lock()

    def record_heartbeat(self) -> Optional[EventLoopStallEvent]:
        """Record event-loop tick; alert if delta exceeds stall threshold."""
        now = time.time()
        with self.lock:
            delta = now - self._last_heartbeat
            self._last_heartbeat = now
            if delta > self.config.stall_threshold_sec:
                event = EventLoopStallEvent(
                    timestamp=now,
                    duration_sec=delta,
                    coroutine_name=None,
                    threshold_sec=self.config.stall_threshold_sec,
                )
                self.stalls.append(event)
                return event
            return None

    def audit_module_code(self, source_code: str) -> Dict[str, object]:
        """Audit Python source code string for blocking loops and auto-transform."""
        import ast

        tree = ast.parse(source_code)
        blocking_nodes = self.detector.detect_blocking_loops(tree)
        transformed = self.transformer.transform(tree)
        new_code = ast.unparse(transformed)
        return {
            "blocking_loop_count": len(blocking_nodes),
            "injected_yields": self.transformer.injected_count,
            "transformed_code": new_code,
        }

    def get_stats(self) -> Dict[str, object]:
        """Return diagnostic metrics of event loop preemption surveillance."""
        with self.lock:
            return {
                "total_stalls": len(self.stalls),
                "stall_threshold_sec": self.config.stall_threshold_sec,
                "is_responsive": len(self.stalls) == 0,
            }


__all__ = ["EventLoopStallEvent", "ACSBESentry"]
