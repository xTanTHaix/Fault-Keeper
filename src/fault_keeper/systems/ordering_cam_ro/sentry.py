"""CAM-RO Sentry: Memory Ordering Invariant Auditor & Barrier Verification Sentinel."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import CAMROConfig
from .engine import ArchitectureModel, FenceSynthesizer, LitmusTest, MemoryOperation, MemoryOrder


@dataclass
class OrderingViolationEvent:
    """Represents a detected memory ordering violation or missing barrier."""

    timestamp: float
    thread_id: int
    architecture: str
    expected_barrier: str
    description: str


class CAMROSentry:
    """Sentry monitoring memory ordering invariants across hardware architectures."""

    def __init__(self, config: Optional[CAMROConfig] = None) -> None:
        self.config = config or CAMROConfig()
        arch_enum = getattr(ArchitectureModel, self.config.default_architecture, ArchitectureModel.ARMV8_WEAK)
        self.synthesizer = FenceSynthesizer(target_architecture=arch_enum)
        self.recorded_ops: List[MemoryOperation] = []
        self.violations: List[OrderingViolationEvent] = []
        self.lock = threading.Lock()

    def record_operation(
        self,
        thread_id: int,
        op_type: str,
        address: int,
        value: int = 0,
        order: MemoryOrder = MemoryOrder.RELAXED,
    ) -> None:
        """Record a thread memory operation into the active audit window."""
        with self.lock:
            op = MemoryOperation(
                thread_id=thread_id,
                op_type=op_type,
                address=address,
                value=value,
                order=order,
            )
            self.recorded_ops.append(op)

    def audit_trace(self) -> List[str]:
        """Audit the recorded memory operations and return required synthesized fences."""
        with self.lock:
            fences = self.synthesizer.synthesize_fences(self.recorded_ops)
            if fences:
                self.violations.append(
                    OrderingViolationEvent(
                        timestamp=time.time(),
                        thread_id=-1,
                        architecture=self.synthesizer.target_architecture.value,
                        expected_barrier=", ".join(fences),
                        description="Relaxed memory operations require barrier insertion",
                    )
                )
            return fences

    def get_audit_summary(self) -> Dict[str, object]:
        """Return diagnostic metrics of memory ordering surveillance."""
        with self.lock:
            return {
                "total_operations": len(self.recorded_ops),
                "total_violations": len(self.violations),
                "target_architecture": self.synthesizer.target_architecture.value,
                "is_barrier_compliant": len(self.violations) == 0,
            }


__all__ = ["OrderingViolationEvent", "CAMROSentry"]
