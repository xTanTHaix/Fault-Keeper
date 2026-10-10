"""PT-PAFS: Pointer Provenance & Tree Borrows Formal State Machine Verifier."""

from .config import PTPAFSConfig
from .engine import (
    BorrowKind,
    BorrowState,
    BorrowTreeNode,
    ProvenanceRegistry,
    TreeBorrowsStateMachine,
)
from .sentry import (
    PTPAFSSentry,
    UndefinedBehaviorEvent,
)

__version__ = "0.8.0"
__all__ = [
    "PTPAFSConfig",
    "BorrowKind",
    "BorrowState",
    "BorrowTreeNode",
    "ProvenanceRegistry",
    "TreeBorrowsStateMachine",
    "PTPAFSSentry",
    "UndefinedBehaviorEvent",
]
