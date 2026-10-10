"""H-TSS: Hardware Pointer Tagging & Spatial Safety Sentry"""

from .config import H_TSSConfig
from .engine import (
    PointerTagger,
    BufferOverflowDetector,
    HardwarePointerTagging,
    TaggedPointer,
)
from .sentry import (
    H_TSS_Sentry,
    UAFEvent,
    UAFMonitor,
)

H_TSS = HardwarePointerTagging

__version__ = "0.8.0"
__all__ = [
    "H_TSSConfig",
    "H_TSS",
    "PointerTagger",
    "BufferOverflowDetector",
    "HardwarePointerTagging",
    "TaggedPointer",
    "H_TSS_Sentry",
    "UAFEvent",
    "UAFMonitor",
]
