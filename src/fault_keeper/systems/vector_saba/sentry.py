"""SABA Sentry: SIMD Auto-Vectorization Barrier Monitor & Compiler Invariant Sentinel."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import SABAConfig
from .engine import (
    DependencyType,
    LoopCarriedDependencyAnalyzer,
    PointerAliasingDetector,
    VectorLoopSynthesizer,
)


@dataclass
class VectorizationInhibitorEvent:
    """Represents an identified inhibitor preventing auto-vectorization."""

    timestamp: float
    loop_id: str
    inhibitor_type: str
    details: str


class SABASentry:
    """Sentry analyzing compiler loop representations and certifying vectorizability."""

    def __init__(self, config: Optional[SABAConfig] = None) -> None:
        self.config = config or SABAConfig()
        self.dep_analyzer = LoopCarriedDependencyAnalyzer()
        self.alias_detector = PointerAliasingDetector()
        self.synthesizer = VectorLoopSynthesizer(self.config)
        self.inhibitors: List[VectorizationInhibitorEvent] = []

    def inspect_loop(
        self,
        loop_id: str,
        write_offset: int,
        read_offset: int,
        ptr_a: int,
        size_a: int,
        ptr_b: int,
        size_b: int,
    ) -> Dict[str, object]:
        """Inspect a loop for vectorization hazards (dependencies and aliasing)."""
        simd_elements = self.config.vector_width_bits // (self.config.element_size_bytes * 8)
        dep_hazard = self.dep_analyzer.analyze_distance(write_offset, read_offset)
        aliasing = self.alias_detector.check_aliasing(ptr_a, size_a, ptr_b, size_b)

        can_vectorize = True
        reasons: List[str] = []

        if dep_hazard == DependencyType.RAW:
            dist = read_offset - write_offset
            if dist < simd_elements:
                can_vectorize = False
                msg = f"Loop-carried RAW dependency distance d={dist} < SIMD width {simd_elements}"
                reasons.append(msg)
                self.inhibitors.append(
                    VectorizationInhibitorEvent(
                        timestamp=time.time(),
                        loop_id=loop_id,
                        inhibitor_type="RAW_DEPENDENCY",
                        details=msg,
                    )
                )

        if aliasing:
            can_vectorize = False
            msg = f"Pointer aliasing detected between ranges [{ptr_a:#x}, {ptr_a+size_a:#x}) and [{ptr_b:#x}, {ptr_b+size_b:#x})"
            reasons.append(msg)
            self.inhibitors.append(
                VectorizationInhibitorEvent(
                    timestamp=time.time(),
                    loop_id=loop_id,
                    inhibitor_type="POINTER_ALIASING",
                    details=msg,
                )
            )

        return {
            "loop_id": loop_id,
            "can_vectorize": can_vectorize,
            "inhibitors": reasons,
            "dependency_hazard": dep_hazard.value,
            "aliasing_detected": aliasing,
        }

    def get_audit_summary(self) -> Dict[str, object]:
        """Return diagnostic metrics of auto-vectorization barrier surveillance."""
        return {
            "total_inhibitors_found": len(self.inhibitors),
            "vector_width_bits": self.config.vector_width_bits,
            "is_clean": len(self.inhibitors) == 0,
        }


__all__ = ["VectorizationInhibitorEvent", "SABASentry"]
