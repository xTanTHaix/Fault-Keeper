"""SC-BBW: Spectral Graph Laplacian Basic-Block Reordering Weaver."""

from .config import SCBBWConfig
from .engine import (
    BasicBlock,
    ControlFlowGraph,
    GraphLaplacianCalculator,
    SpectralSequencer,
)
from .sentry import (
    ReorderMetric,
    SCBBWSentry,
)

__version__ = "0.8.0"
__all__ = [
    "SCBBWConfig",
    "BasicBlock",
    "ControlFlowGraph",
    "GraphLaplacianCalculator",
    "SpectralSequencer",
    "ReorderMetric",
    "SCBBWSentry",
]
