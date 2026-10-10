"""MD-BBE Sentry: Binary Bloat Monitor & Monomorphization Deduplication Sentinel."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import MDBBEConfig
from .engine import (
    ABITypeDescriptor,
    GenericInstance,
    PolymorphicThunkDeduplicator,
    StructuralABIEquivalenceScanner,
)


@dataclass
class DeduplicationReport:
    """Diagnostic report on binary code size savings achieved via ABI deduplication."""

    original_size_bytes: int
    deduplicated_size_bytes: int
    bytes_saved: int
    reduction_percentage: float
    total_generic_instances: int
    unique_abi_clusters: int


class MDBBESentry:
    """Sentry analyzing binary monomorphization bloat and enforcing size limits."""

    def __init__(self, config: Optional[MDBBEConfig] = None) -> None:
        self.config = config or MDBBEConfig()
        self.scanner = StructuralABIEquivalenceScanner()
        self.deduplicator = PolymorphicThunkDeduplicator(self.config)

    def audit_and_optimize(self, instances: List[GenericInstance]) -> DeduplicationReport:
        """Audit binary instances and compute deduplication savings."""
        orig_size = sum(inst.code_size_bytes for inst in instances)
        clusters = self.scanner.cluster_instances(instances)
        deduped, ratio = self.deduplicator.deduplicate(instances)
        new_size = sum(inst.code_size_bytes for inst in deduped)

        return DeduplicationReport(
            original_size_bytes=orig_size,
            deduplicated_size_bytes=new_size,
            bytes_saved=orig_size - new_size,
            reduction_percentage=round(ratio * 100.0, 2),
            total_generic_instances=len(instances),
            unique_abi_clusters=len(clusters),
        )


__all__ = ["DeduplicationReport", "MDBBESentry"]
