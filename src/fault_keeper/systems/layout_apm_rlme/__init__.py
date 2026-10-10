"""APM-RLME: Zero-Stall Memory Layout Transposition Module."""

from .config import APM_RLMEConfig
from .engine import (
    AoSSoATransposer,
    ZeroStallContainer,
    SIMDTransposer,
)
from .sentry import APM_RLME_Sentry, TranspositionEvent, LayoutMonitor

APM_RLME = ZeroStallContainer

__all__ = [
    "APM_RLMEConfig",
    "APM_RLME",
    "AoSSoATransposer",
    "ZeroStallContainer",
    "SIMDTransposer",
    "APM_RLME_Sentry",
    "TranspositionEvent",
    "LayoutMonitor",
]