"""SABA Engine: SIMD Auto-Vectorization Barrier Analyzer & Transformation Synthesizer.

Analyzes loop-carried dependencies, computes distance vectors d, detects pointer
aliasing hazards, and synthesizes strip-mined vector loops for AVX-512 / ARM Neon.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Tuple

from .config import SABAConfig


class DependencyType(str, Enum):
    """Loop-carried data dependency hazard types."""

    NONE = "none"
    RAW = "raw"  # Flow dependency: Read-After-Write (true dependency)
    WAR = "war"  # Anti dependency: Write-After-Read
    WAW = "waw"  # Output dependency: Write-After-Write


class LoopCarriedDependencyAnalyzer:
    """Computes loop-carried data dependencies and distance vectors."""

    def __init__(self) -> None:
        pass

    def analyze_distance(self, write_offset: int, read_offset: int) -> DependencyType:
        """Analyze loop-carried dependence between a write at index (i + write_offset)

        and a read at index (i + read_offset).
        If read depends on previous or future write across loop iterations:
        - read_offset > write_offset: Read-After-Write (RAW) hazard across iterations.
        - read_offset < write_offset: Write-After-Read (WAR) hazard.
        - read_offset == write_offset: No loop-carried hazard (intra-iteration dependency).
        """
        dist = read_offset - write_offset
        if dist > 0:
            return DependencyType.RAW
        elif dist < 0:
            return DependencyType.WAR
        return DependencyType.NONE

    def compute_distance_vector(self, loop_writes: List[int], loop_reads: List[int]) -> List[int]:
        """Compute multidimensional distance vector d = read_idx - write_idx."""
        return [r - w for w, r in zip(loop_writes, loop_reads)]

    def is_vectorizable(self, write_offset: int, read_offset: int, vector_width: int) -> bool:
        """Evaluate if loop iteration dependency distance allows vectorization of width V."""
        hazard = self.analyze_distance(write_offset, read_offset)
        dist = abs(read_offset - write_offset)
        if hazard == DependencyType.RAW and 0 < dist < vector_width:
            return False  # RAW loop-carried dependency inside vector chunk
        return True


class PointerAliasingDetector:
    """Detects pointer aliasing and memory range overlap inhibiting SIMD execution."""

    def __init__(self) -> None:
        pass

    def check_aliasing(self, ptr1: int, size1: int, ptr2: int, size2: int) -> bool:
        """Return True if memory range [ptr1, ptr1 + size1) overlaps [ptr2, ptr2 + size2)."""
        end1 = ptr1 + size1
        end2 = ptr2 + size2
        # Intervals overlap if neither is completely before the other
        overlaps = not (end1 <= ptr2 or end2 <= ptr1)
        return overlaps


class VectorLoopSynthesizer:
    """Synthesizes strip-mined vector loops and scalar cleanup epilogues."""

    def __init__(self, config: Optional[SABAConfig] = None) -> None:
        self.config = config or SABAConfig()

    def synthesize_vector_loop(
        self,
        loop_bound: int,
        simd_elements: Optional[int] = None,
        unroll_factor: Optional[int] = None,
    ) -> Dict[str, object]:
        """Synthesize strip-mined vector loop execution schedule.

        Returns vector loop bounds and scalar epilogue parameters.
        """
        elements = simd_elements or (self.config.vector_width_bits // (self.config.element_size_bytes * 8))
        unroll = unroll_factor or self.config.unroll_factor

        step = elements * unroll
        if step <= 0:
            step = 1

        vector_trips = loop_bound // step
        vector_elements_processed = vector_trips * step
        scalar_epilogue_count = loop_bound - vector_elements_processed

        return {
            "total_iterations": loop_bound,
            "simd_width_elements": elements,
            "unroll_factor": unroll,
            "vector_step": step,
            "vector_trips": vector_trips,
            "vector_elements_processed": vector_elements_processed,
            "scalar_epilogue_count": scalar_epilogue_count,
            "speedup_potential": round(elements * 0.85, 2),
        }


__all__ = [
    "DependencyType",
    "LoopCarriedDependencyAnalyzer",
    "PointerAliasingDetector",
    "VectorLoopSynthesizer",
]
