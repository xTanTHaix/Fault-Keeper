"""DIS-RA Sentry: io_uring Ring Backpressure Monitor & CQE Overflow Sentry."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import DISRAConfig
from .engine import BackpressureThrottler, CQEntry, IoUringEngine, SQEntry


@dataclass
class RingOverflowEvent:
    """Represents a dangerous queue saturation or overflow event."""

    timestamp: float
    sq_utilization: float
    cq_utilization: float
    overflow_count: int
    message: str


class DISRASentry:
    """Sentry enforcing io_uring backpressure and zero-CQE-overflow invariants."""

    def __init__(self, config: Optional[DISRAConfig] = None) -> None:
        self.config = config or DISRAConfig()
        self.engine = IoUringEngine(
            sq_entries=self.config.default_sq_entries,
            cq_entries=self.config.default_cq_entries,
        )
        self.throttler = BackpressureThrottler(
            engine=self.engine,
            threshold=self.config.backpressure_threshold,
        )
        self.events: List[RingOverflowEvent] = []

    def submit_operation(self, opcode: int, fd: int, addr: int, length: int, user_data: int) -> bool:
        """Submit an I/O request through the backpressure throttler."""
        sqe = SQEntry(opcode=opcode, fd=fd, addr=addr, len=length, user_data=user_data)
        accepted = self.throttler.submit(sqe)
        if not accepted:
            self.events.append(
                RingOverflowEvent(
                    timestamp=time.time(),
                    sq_utilization=self.engine.get_sq_utilization(),
                    cq_utilization=self.engine.get_cq_utilization(),
                    overflow_count=self.engine.overflow_count,
                    message="Submission throttled to prevent ring overflow",
                )
            )
        return accepted

    def drain(self) -> int:
        """Process pending submissions and reap completions."""
        return self.engine.process_submissions()

    def get_audit_summary(self) -> Dict[str, object]:
        """Return diagnostic metrics of io_uring ring surveillance."""
        return {
            "sq_utilization": round(self.engine.get_sq_utilization(), 4),
            "cq_utilization": round(self.engine.get_cq_utilization(), 4),
            "overflow_count": self.engine.overflow_count,
            "throttled_count": self.throttler.throttled_submissions,
            "accepted_count": self.throttler.accepted_submissions,
            "is_zero_overflow": self.engine.overflow_count == 0,
        }


__all__ = ["RingOverflowEvent", "DISRASentry"]
