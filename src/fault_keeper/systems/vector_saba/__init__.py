"""SABA: SIMD Auto-Vectorization Barrier Analyzer & Transformation Synthesizer."""

from .config import SABAConfig
from .engine import (
    DependencyType,
    LoopCarriedDependencyAnalyzer,
    PointerAliasingDetector,
    VectorLoopSynthesizer,
)
from .sentry import (
    SABASentry,
    VectorizationInhibitorEvent,
)

__version__ = "0.8.0"
__all__ = [
    "SABAConfig",
    "DependencyType",
    "LoopCarriedDependencyAnalyzer",
    "PointerAliasingDetector",
    "VectorLoopSynthesizer",
    "SABASentry",
    "VectorizationInhibitorEvent",
]
