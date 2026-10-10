"""CAM-RO: Cross-Architecture Memory Reordering & Atomic Fence Synthesizer."""

from .config import CAMROConfig
from .engine import (
    ArchitectureModel,
    FenceSynthesizer,
    LitmusTest,
    MemoryOperation,
    MemoryOrder,
)
from .sentry import (
    CAMROSentry,
    OrderingViolationEvent,
)

__version__ = "0.8.0"
__all__ = [
    "CAMROConfig",
    "ArchitectureModel",
    "FenceSynthesizer",
    "LitmusTest",
    "MemoryOperation",
    "MemoryOrder",
    "CAMROSentry",
    "OrderingViolationEvent",
]
