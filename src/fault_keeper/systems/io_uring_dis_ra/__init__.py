"""DIS-RA: Deterministic io_uring Ring Buffer & Backpressure Arbiter."""

from .config import DISRAConfig
from .engine import (
    BackpressureThrottler,
    CQEntry,
    IoUringEngine,
    RingBuffer,
    SQEntry,
)
from .sentry import (
    DISRASentry,
    RingOverflowEvent,
)

__version__ = "0.8.0"
__all__ = [
    "DISRAConfig",
    "BackpressureThrottler",
    "CQEntry",
    "IoUringEngine",
    "RingBuffer",
    "SQEntry",
    "DISRASentry",
    "RingOverflowEvent",
]
