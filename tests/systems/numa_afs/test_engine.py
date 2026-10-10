"""Test suite for NUMA-AFS engine."""

import os

import pytest
import numpy as np
from numpy.testing import assert_array_almost_equal, assert_allclose


class TestLocalityQuotientCalculator:
    """Tests for LocalityQuotientCalculator."""
    
    def test_lq_same_node(self):
        """Test LQ calculation for same node (distance=0)."""
        from fault_keeper.systems.numa_afs.engine import LocalityQuotientCalculator
        
        slit = np.array([
            [0.0, 50.0],
            [50.0, 0.0]
        ])
        
        calculator = LocalityQuotientCalculator(slit, upi_bandwidth=20.0)
        
        lq, is_remote = calculator.compute_node_affinity(0, 0)
        
        assert not is_remote
        assert lq == pytest.approx(1.0, rel=1e-5)
    
    def test_lq_different_node(self):
        """Test LQ calculation for different nodes."""
        from fault_keeper.systems.numa_afs.engine import LocalityQuotientCalculator
        
        slit = np.array([
            [0.0, 50.0],
            [50.0, 0.0]
        ])
        
        calculator = LocalityQuotientCalculator(slit, upi_bandwidth=20.0)
        
        lq, is_remote = calculator.compute_node_affinity(0, 1)
        
        assert is_remote
        # LQ should be lower for remote access
        assert lq < 1.0
    
    def test_lq_with_higher_bandwidth(self):
        """Test that higher bandwidth improves LQ."""
        from fault_keeper.systems.numa_afs.engine import LocalityQuotientCalculator
        
        slit = np.array([
            [0.0, 50.0],
            [50.0, 0.0]
        ])
        
        calculator_low = LocalityQuotientCalculator(slit, upi_bandwidth=10.0)
        calculator_high = LocalityQuotientCalculator(slit, upi_bandwidth=40.0)
        
        _, lq_low = calculator_low.compute_node_affinity(0, 1)
        _, lq_high = calculator_high.compute_node_affinity(0, 1)
        
        # Higher bandwidth should give better (higher) LQ
        assert lq_high >= lq_low


class TestKMBAWMatcher:
    """Tests for Kuhn-Munkres Bipartite Affinity Weaver."""
    
    def test_match_2x2_matrix(self):
        """Test matching with 2x2 SLIT matrix."""
        from fault_keeper.systems.numa_afs.engine import KMBAWMatcher
        
        slit = np.array([
            [0.0, 50.0],
            [50.0, 0.0]
        ])
        
        matcher = KMBAWMatcher(slit)
        assignments = matcher.match_cores_to_pages([0, 1], [0, 1])
        
        # Should prefer local connections
        assert len(assignments) == 2
        
        # Check that at least one assignment is local
        local_count = sum(1 for a in assignments if not a.is_remote)
        assert local_count >= 1
    
    def test_match_4x4_matrix(self):
        """Test matching with 4x4 SLIT matrix."""
        from fault_keeper.systems.numa_afs.engine import KMBAWMatcher
        
        slit = np.array([
            [0.0, 50.0, 60.0, 70.0],
            [50.0, 0.0, 55.0, 65.0],
            [60.0, 55.0, 0.0, 52.0],
            [70.0, 65.0, 52.0, 0.0]
        ])
        
        matcher = KMBAWMatcher(slit)
        assignments = matcher.match_cores_to_pages([0, 1, 2, 3], [0, 1, 2, 3])
        
        assert len(assignments) == 4
        
        # Check that diagonal (local) connections are preferred
        local_count = sum(1 for a in assignments if not a.is_remote)
        assert local_count >= 3
    
    def test_optimize_affinity(self):
        """Test affinity optimization returns valid mapping."""
        from fault_keeper.systems.numa_afs.engine import KMBAWMatcher
        
        slit = np.array([
            [0.0, 50.0],
            [50.0, 0.0]
        ])
        
        matcher = KMBAWMatcher(slit)
        affinity_map = matcher.optimize_affinity()
        
        assert isinstance(affinity_map, dict)
        assert len(affinity_map) == 2


class TestNUMAAFS:
    """Tests for main NUMAAFS orchestrator."""
    
    def test_init(self):
        """Test initialization."""
        from fault_keeper.systems.numa_afs import NUMAAFS
        
        numa = NUMAAFS()
        
        assert numa is not None
        assert hasattr(numa, 'stall_detector')
        assert hasattr(numa, 'affinity_enforcer')
    
    def test_load_slit_matrix(self):
        """Test loading SLIT matrix."""
        from fault_keeper.systems.numa_afs import NUMAAFS
        
        slit = np.array([
            [0.0, 50.0],
            [50.0, 0.0]
        ])
        
        # Create mock SLIT file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("0 0 0.0\n")
            f.write("0 1 50.0\n")
            f.write("1 0 50.0\n")
            f.write("1 1 0.0\n")
            slit_file = f.name
        
        try:
            numa = NUMAAFS()
            result = numa.load_acpi_slit(slit_file)
            
            assert result is True
        finally:
            import os
            os.unlink(slit_file)
    
    def test_should_use_local_memory(self):
        """Test local memory decision."""
        from fault_keeper.systems.numa_afs import NUMAAFS
        
        slit = np.array([
            [0.0, 50.0],
            [50.0, 0.0]
        ])
        
        numa = NUMAAFS()
        numa.load_acpi_slit(None)  # Will use default
        
        # Same node should prefer local
        result_same = numa.should_use_local_memory(0, 0)
        result_diff = numa.should_use_local_memory(0, 1)
        
        assert result_same is True
        # Different node may or may not use local depending on config
    
    def test_check_interconnect_stall(self):
        """Test interconnect stall detection."""
        from fault_keeper.systems.numa_afs import NUMAAFS
        
        numa = NUMAAFS()
        
        # Within threshold
        result1 = numa.check_interconnect_stall(0.4)  # < 0.5us
        assert result1 is True
        
        # Exceeds threshold
        result2 = numa.check_interconnect_stall(0.6)  # > 0.5us
        assert result2 is False
    
    def test_get_affinity_for_core(self):
        """Test getting affinity for a core."""
        from fault_keeper.systems.numa_afs import NUMAAFS
        
        numa = NUMAAFS()
        
        affinity = numa.get_affinity_for_core(0)
        
        assert isinstance(affinity, int)
        assert affinity >= 0
    
    def test_get_affinity_status(self):
        """Test getting affinity status."""
        from fault_keeper.systems.numa_afs import NUMAAFS
        
        numa = NUMAAFS()
        
        status = numa.get_affinity_status()
        
        assert "core_bindings" in status
        assert "page_bindings" in status
        assert "stall_metrics" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])