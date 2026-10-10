"""SC-BBW Sentry: Machine Code Layout Auditor & I-Cache Locality Sentinel."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import SCBBWConfig
from .engine import BasicBlock, ControlFlowGraph, SpectralSequencer


@dataclass
class ReorderMetric:
    """Diagnostic comparison metric of CFG layout before and after reordering."""

    original_penalty: float
    optimized_penalty: float
    cache_miss_reduction_percent: float
    reordered_sequence: List[int]


class SCBBWSentry:
    """Sentry auditing basic block arrangement and enforcing I-cache locality invariants."""

    def __init__(self, config: Optional[SCBBWConfig] = None) -> None:
        self.config = config or SCBBWConfig()

    def optimize_cfg(self, cfg: ControlFlowGraph) -> ReorderMetric:
        """Analyze CFG layout, compute spectral reordering, and evaluate penalty reduction."""
        sequencer = SpectralSequencer(cfg, self.config)
        reordered = sequencer.compute_reordering()

        # Compute branch distance penalty before vs after
        orig_order = cfg.block_ids
        orig_pos = {bid: i for i, bid in enumerate(orig_order)}
        new_pos = {bid: i for i, bid in enumerate(reordered)}

        orig_penalty = sum(
            weight * abs(orig_pos[src] - orig_pos[dst])
            for (src, dst), weight in cfg.edges.items()
            if src in orig_pos and dst in orig_pos
        )
        new_penalty = sum(
            weight * abs(new_pos[src] - new_pos[dst])
            for (src, dst), weight in cfg.edges.items()
            if src in new_pos and dst in new_pos
        )

        reduction = 0.0
        if orig_penalty > 0:
            reduction = max(0.0, (orig_penalty - new_penalty) / orig_penalty * 100.0)

        return ReorderMetric(
            original_penalty=orig_penalty,
            optimized_penalty=new_penalty,
            cache_miss_reduction_percent=reduction,
            reordered_sequence=reordered,
        )


__all__ = ["ReorderMetric", "SCBBWSentry"]
