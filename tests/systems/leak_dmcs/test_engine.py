"""Test suite for DMCS engine: Lengauer-Tarjan Dominator Tree & Stoer-Wagner/Max-Flow Min-Cut."""

import pytest
import time
from fault_keeper.systems.leak_dmcs.engine import (
    DMCSConfig,
    MemoryBlock,
    DominatorTree,
    MinCutAnalyzer,
    LeakDetector,
    DMCS,
)


class TestMemoryBlock:
    """Tests for MemoryBlock entity."""

    def test_block_creation_and_references(self):
        """Test creating memory block and tracking references."""
        block = MemoryBlock(
            address=0x1000,
            size=256,
            thread_id=1,
            allocation_time=time.time(),
        )
        assert block.address == 0x1000
        assert block.size == 256
        assert len(block.references) == 0

        block.add_reference(0x2000)
        assert 0x2000 in block.references


class TestDominatorTreeLengauerTarjan:
    """Tests for Lengauer-Tarjan Dominator Tree implementation."""

    def test_linear_dominance(self):
        """Test linear chain 1 -> 2 -> 3."""
        tree = DominatorTree()
        b1 = MemoryBlock(address=1, size=10, thread_id=1, allocation_time=0.0)
        b2 = MemoryBlock(address=2, size=10, thread_id=1, allocation_time=0.0)
        b3 = MemoryBlock(address=3, size=10, thread_id=1, allocation_time=0.0)

        tree.add_block(b1)
        tree.add_block(b2)
        tree.add_block(b3)

        tree.add_reference(1, 2)
        tree.add_reference(2, 3)

        idoms = tree.compute_dominators(root_address=1)
        assert idoms[1] is None
        assert idoms[2] == 1
        assert idoms[3] == 2
        assert b3.dominator == b2
        assert b2.dominator == b1

    def test_diamond_dominance(self):
        r"""
        Test diamond graph:
               1 (Root)
              / \
             2   3
              \ /
               4
        Both paths from 1 to 4 pass through 1, so idom(4) must be 1.
        """
        tree = DominatorTree()
        blocks = [MemoryBlock(address=i, size=100, thread_id=1, allocation_time=0.0) for i in range(1, 5)]
        for b in blocks:
            tree.add_block(b)

        tree.add_reference(1, 2)
        tree.add_reference(1, 3)
        tree.add_reference(2, 4)
        tree.add_reference(3, 4)

        idoms = tree.compute_dominators(root_address=1)
        assert idoms[4] == 1
        assert idoms[2] == 1
        assert idoms[3] == 1
        assert idoms[1] is None

    def test_dominator_info_and_size(self):
        """Test dominator query utilities."""
        tree = DominatorTree()
        b1 = MemoryBlock(address=10, size=64, thread_id=1, allocation_time=0.0)
        b2 = MemoryBlock(address=20, size=128, thread_id=1, allocation_time=0.0)
        tree.add_block(b1)
        tree.add_block(b2)
        tree.add_reference(10, 20)
        tree.compute_dominators(10)

        assert tree.get_tree_size() == 2
        info = tree.get_dominator_info(b2)
        assert info["block_address"] == 20
        assert info["dominator_address"] == 10
        assert info["dominator_size"] == 64


class TestMinCutAnalyzer:
    """Tests for Stoer-Wagner global min-cut and Edmonds-Karp max-flow min-cut."""

    def test_stoer_wagner_two_clusters_cut(self):
        """
        Test Stoer-Wagner min-cut on a barbell graph:
        Cluster 1: (1, 2) with weight 10.0
        Cluster 2: (3, 4) with weight 10.0
        Bridge edge: (2, 3) with weight 1.0
        The global minimum cut must have weight 1.0 separating {1, 2} and {3, 4}.
        """
        analyzer = MinCutAnalyzer()
        nodes = [1, 2, 3, 4]
        weights = {
            (1, 2): 10.0,
            (3, 4): 10.0,
            (2, 3): 1.0,
        }

        min_cut_w, part_a, part_b = analyzer.compute_stoer_wagner_min_cut(nodes, weights)
        assert min_cut_w == pytest.approx(1.0, rel=1e-5)
        # Partitions should separate {1, 2} and {3, 4}
        assert (part_a == {1, 2} and part_b == {3, 4}) or (part_a == {3, 4} and part_b == {1, 2})

    def test_edmonds_karp_max_flow_min_cut(self):
        """
        Test Edmonds-Karp Max-Flow Min-Cut:
        1 (src) -> 2: cap 10
        1 (src) -> 3: cap 5
        2 -> 4 (sink): cap 10
        3 -> 4 (sink): cap 5
        Total max-flow = 15. Min cut edges = [(1, 2), (1, 3)] or [(2, 4), (3, 4)].
        """
        analyzer = MinCutAnalyzer()
        nodes = {1, 2, 3, 4}
        capacities = {
            (1, 2): 10.0,
            (1, 3): 5.0,
            (2, 4): 10.0,
            (3, 4): 5.0,
        }

        cut_val, reachable_s, cut_edges = analyzer.compute_max_flow_min_cut(
            source=1,
            sink=4,
            capacities=capacities,
            nodes=nodes,
        )
        assert cut_val == pytest.approx(15.0, rel=1e-5)
        assert 1 in reachable_s
        assert 4 not in reachable_s
        assert len(cut_edges) > 0

    def test_compute_and_apply_min_cut(self):
        """Test block list min-cut selection and stats updating."""
        analyzer = MinCutAnalyzer(threshold=0.75)
        blocks = [
            MemoryBlock(address=0x10, size=100, thread_id=1, allocation_time=0.0),
            MemoryBlock(address=0x20, size=200, thread_id=1, allocation_time=0.0),
            MemoryBlock(address=0x30, size=300, thread_id=1, allocation_time=0.0),
            MemoryBlock(address=0x40, size=400, thread_id=1, allocation_time=0.0),
        ]
        # Total size = 1000, target >= 750
        reclaimed = analyzer.apply_min_cut(blocks)
        assert len(reclaimed) > 0
        reclaimed_bytes = sum(b.size for b in reclaimed)
        assert reclaimed_bytes >= 750

        stats = analyzer.get_stats()
        assert stats["cut_count"] == 1
        assert stats["reclaimed_size"] == reclaimed_bytes


class TestDMCSOrchestrator:
    """Tests for main DMCS orchestrator."""

    def test_dmcs_lifecycle(self):
        """Test DMCS block allocation, cycle diagnosis, and reclamation."""
        config = DMCSConfig(leak_scan_interval_ms=0.0, min_cut_threshold=0.8)
        dmcs = DMCS(config)

        # Allocate root block and detached cyclic blocks
        root = dmcs.allocate(address=0x1000, size=1024, thread_id=1)
        leak1 = dmcs.allocate(address=0x2000, size=512, thread_id=1)
        leak2 = dmcs.allocate(address=0x3000, size=512, thread_id=1)

        # Connect leak1 <-> leak2 in an isolated cycle disconnected from root
        dmcs.add_reference(0x2000, 0x3000)
        dmcs.add_reference(0x3000, 0x2000)

        # Diagnose leaks: leak1 and leak2 have no dominator from root
        leaked = dmcs.diagnose_leaks()
        assert len(leaked) >= 2

        # Reclaim memory
        reclaimed_count = dmcs.reclaim_memory()
        assert reclaimed_count > 0

        stats = dmcs.get_recovery_stats()
        assert stats["dominator_tree_size"] == 3
        assert "min_cut_stats" in stats
        assert "leak_detector_stats" in stats
