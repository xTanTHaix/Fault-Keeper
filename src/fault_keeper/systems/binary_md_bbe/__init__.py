"""MD-BBE: Monomorphization Deduplication & Binary Bloat Equivalence Eliminator."""

from .config import MDBBEConfig
from .engine import (
    ABITypeDescriptor,
    GenericInstance,
    PolymorphicThunkDeduplicator,
    StructuralABIEquivalenceScanner,
)
from .sentry import (
    DeduplicationReport,
    MDBBESentry,
)

__version__ = "0.8.0"
__all__ = [
    "MDBBEConfig",
    "ABITypeDescriptor",
    "GenericInstance",
    "PolymorphicThunkDeduplicator",
    "StructuralABIEquivalenceScanner",
    "MDBBESentry",
    "DeduplicationReport",
]
