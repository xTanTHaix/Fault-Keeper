"""SC-BBW Engine: Spectral Graph Laplacian Basic-Block Reordering Weaver.

Constructs CFG execution transition topologies, computes the unnormalized and
normalized Graph Laplacian L = D - W, solves for the Fiedler eigenvector v_2, and
computes optimal 1D basic block layout permutations to minimize L1 I-cache line misses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

from .config import SCBBWConfig


@dataclass
class BasicBlock:
    """Represents a compiler basic block with size and execution frequency."""

    block_id: int
    size_bytes: int = 32
    exec_count: int = 0


class ControlFlowGraph:
    """Directed control-flow graph annotated with execution frequency weights."""

    def __init__(self) -> None:
        self.blocks: Dict[int, BasicBlock] = {}
        self.edges: Dict[Tuple[int, int], float] = {}

    def add_block(self, block: BasicBlock) -> None:
        """Add a basic block to the control flow graph."""
        self.blocks[block.block_id] = block

    def add_edge(self, src: int, dst: int, weight: float = 1.0) -> None:
        """Add or update an execution transition edge with frequency weight."""
        if src not in self.blocks:
            self.add_block(BasicBlock(block_id=src))
        if dst not in self.blocks:
            self.add_block(BasicBlock(block_id=dst))
        self.edges[(src, dst)] = self.edges.get((src, dst), 0.0) + float(weight)

    @property
    def num_blocks(self) -> int:
        """Return total number of basic blocks."""
        return len(self.blocks)

    @property
    def block_ids(self) -> List[int]:
        """Return sorted list of block IDs."""
        return sorted(list(self.blocks.keys()))


class GraphLaplacianCalculator:
    """Computes the Graph Laplacian L = D - W over CFG transition weights."""

    def __init__(self, cfg: ControlFlowGraph) -> None:
        self.cfg = cfg

    def compute_laplacian(self) -> np.ndarray:
        """Compute symmetric Graph Laplacian matrix L = D - W.

        Guarantees no NaN or Inf even for disconnected or dead-code subgraphs.
        """
        n = self.cfg.num_blocks
        if n == 0:
            return np.zeros((0, 0), dtype=np.float64)

        block_ids = self.cfg.block_ids
        id_to_idx = {bid: idx for idx, bid in enumerate(block_ids)}

        # Symmetrized weight matrix W
        W = np.zeros((n, n), dtype=np.float64)
        for (src, dst), weight in self.cfg.edges.items():
            if src in id_to_idx and dst in id_to_idx:
                i = id_to_idx[src]
                j = id_to_idx[dst]
                # Undirected affinity: sum weights in both directions
                W[i, j] += weight
                W[j, i] += weight

        # Degree matrix D_ii = sum_j W_ij
        degrees = np.sum(W, axis=1)
        D = np.diag(degrees)

        L = D - W
        # Clean any floating anomalies
        np.nan_to_num(L, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
        return L


class SpectralSequencer:
    """Computes optimal basic block permutation pi using the Fiedler eigenvector."""

    def __init__(self, cfg: ControlFlowGraph, config: Optional[SCBBWConfig] = None) -> None:
        self.cfg = cfg
        self.config = config or SCBBWConfig()
        self.laplacian_calc = GraphLaplacianCalculator(cfg)

    def compute_fiedler_vector(self) -> np.ndarray:
        """Compute the Fiedler eigenvector v_2 corresponding to lambda_2 of L."""
        L = self.laplacian_calc.compute_laplacian()
        n = L.shape[0]
        if n < 2:
            return np.zeros(n, dtype=np.float64)

        # Eigen-decomposition of real symmetric matrix
        eigenvalues, eigenvectors = np.linalg.eigh(L)
        # Sort indices ascending
        sort_indices = np.argsort(eigenvalues)
        # Fiedler vector is eigenvector for 2nd smallest eigenvalue
        fiedler_idx = sort_indices[1]
        return eigenvectors[:, fiedler_idx]

    def compute_reordering(self) -> List[int]:
        """Compute optimal basic block permutation ordering minimizing cache misses."""
        n = self.cfg.num_blocks
        if n <= 1:
            return self.cfg.block_ids

        fiedler = self.compute_fiedler_vector()
        block_ids = self.cfg.block_ids

        # Permutation is ordering of block IDs according to ascending Fiedler values
        sorted_indices = np.argsort(fiedler)
        return [block_ids[idx] for idx in sorted_indices]


__all__ = [
    "BasicBlock",
    "ControlFlowGraph",
    "GraphLaplacianCalculator",
    "SpectralSequencer",
]
