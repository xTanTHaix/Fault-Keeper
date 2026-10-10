"""FS-CCO: False Sharing Cache-Line Optimizer"""

from .engine import (
    FS_CCO,
    StructLayoutAnalyzer,
)
from .sentry import (
    CacheLineSentry,
    FalseSharingDetector,
)
from .config import FS_CCO_Config

__version__ = "0.8.0"
__all__ = [
    "FS_CCO",
    "StructLayoutAnalyzer",
    "CacheLineSentry",
    "FalseSharingDetector",
    "FS_CCO_Config",
]