"""TSCA: Topological Simplicial Concurrency Arbiter."""

from .config import TSCAConfig
from .engine import (
    BoundaryMatrixCalculator,
    HomologyEngine,
    SimplicialComplex,
    TSCAEngine,
)
from .sentry import (
    DeadlockAlert,
    TSCASentry,
)

TSCA = TSCAEngine

__version__ = "0.8.0"
__all__ = [
    "TSCAConfig",
    "TSCA",
    "SimplicialComplex",
    "BoundaryMatrixCalculator",
    "HomologyEngine",
    "TSCAEngine",
    "TSCASentry",
    "DeadlockAlert",
]
