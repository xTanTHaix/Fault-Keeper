"""Unit and invariant tests for SC-BBW Engine."""

import pytest
import numpy as np

try:
    from fault_keeper.systems.compile_sc_bbw.config import SCBBWConfig
    from fault_keeper.systems.compile_sc_bbw.engine import (
        BasicBlock,
        ControlFlowGraph,
        GraphLaplacianCalculator,
        SpectralSequencer,
    )
except ImportError:
    from compile_sc_bbw.config import SCBBWConfig
    from compile_sc_bbw.engine import (
        BasicBlock,
        ControlFlowGraph,
        GraphLaplacianCalculator,
        SpectralSequencer,
    )


class TestControlFlowGraph:
    """Tests for CFG construction and edge weights."""

    def test_cfg_add_blocks_and_edges(self) -> None:
        cfg = ControlFlowGraph()
        cfg.add_block(BasicBlock(0, size_bytes=64, exec_count=50))
        cfg.add_block(BasicBlock(1, size_bytes=64, exec_count=50))
        cfg.add_edge(0, 1, weight=25.0)

        assert cfg.num_blocks == 2
        assert cfg.block_ids == [0, 1]
        assert cfg.edges[(0, 1)] == 25.0


class TestGraphLaplacianCalculator:
    """Tests for Graph Laplacian computation and properties."""

    def test_laplacian_properties(self) -> None:
        cfg = ControlFlowGraph()
        cfg.add_edge(0, 1, weight=10.0)
        cfg.add_edge(1, 2, weight=20.0)

        calc = GraphLaplacianCalculator(cfg)
        L = calc.compute_laplacian()

        assert L.shape == (3, 3)
        # Sum of rows in Laplacian is 0
        np.testing.assert_allclose(np.sum(L, axis=1), [0, 0, 0], atol=1e-8)
        # Symmetric matrix: L == L.T
        np.testing.assert_allclose(L, L.T, atol=1e-8)


class TestSpectralSequencer:
    """Tests for Fiedler eigenvector reordering."""

    def test_reordering_line_graph(self) -> None:
        cfg = ControlFlowGraph()
        # Edge strongly connecting 0 and 2, but 1 is weakly connected
        cfg.add_edge(0, 2, weight=100.0)
        cfg.add_edge(2, 1, weight=1.0)

        seq = SpectralSequencer(cfg)
        fiedler = seq.compute_fiedler_vector()
        assert len(fiedler) == 3

        order = seq.compute_reordering()
        assert len(order) == 3
        # Blocks 0 and 2 should be adjacent in the optimal 1D layout
        idx0 = order.index(0)
        idx2 = order.index(2)
        assert abs(idx0 - idx2) == 1
