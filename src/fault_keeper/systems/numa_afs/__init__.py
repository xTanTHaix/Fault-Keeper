"""NUMA-AFS: NUMA-Aware Affinity & Interconnect-Stall Formal Sentry"""

from .engine import (
    NUMAAFS,
    LocalityQuotientCalculator,
    KMBAWMatcher,
)
from .sentry import (
    InterconnectStallDetector,
    FirstTouchAffinityEnforcer,
)
from .config import NUMAAFSConfig

__version__ = "0.8.0"
__all__ = [
    "NUMAAFS",
    "LocalityQuotientCalculator",
    "KMBAWMatcher",
    "InterconnectStallDetector",
    "FirstTouchAffinityEnforcer",
    "NUMAAFSConfig",
]