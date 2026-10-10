"""Test suite for NUMA-AFS sentry."""

import pytest


class TestInterconnectStallDetector:
    """Tests for InterconnectStallDetector."""
    
    def test_record_operation_within_threshold(self):
        """Test recording operation within threshold."""
        from fault_keeper.systems.numa_afs.sentry import InterconnectStallDetector
        
        detector = InterconnectStallDetector(max_stall_us=0.5)
        
        result = detector.record_operation(0.4)  # < 0.5us
        
        assert result is True
    
    def test_record_operation_exceeds_threshold(self):
        """Test recording operation exceeding threshold."""
        from fault_keeper.systems.numa_afs.sentry import InterconnectStallDetector
        
        detector = InterconnectStallDetector(max_stall_us=0.5)
        
        result = detector.record_operation(0.6)  # > 0.5us
        
        assert result is False
    
    def test_get_stall_ratio(self):
        """Test getting stall ratio."""
        from fault_keeper.systems.numa_afs.sentry import InterconnectStallDetector
        
        detector = InterconnectStallDetector(max_stall_us=0.5)
        
        detector.record_operation(0.4)  # OK
        detector.record_operation(0.6)  # Stall
        
        ratio = detector.get_stall_ratio()
        
        assert 0 <= ratio <= 1


class TestFirstTouchAffinityEnforcer:
    """Tests for FirstTouchAffinityEnforcer."""
    
    def test_init(self):
        """Test enforcer initialization."""
        from fault_keeper.systems.numa_afs.sentry import FirstTouchAffinityEnforcer
        
        enforcer = FirstTouchAffinityEnforcer(numa_nodes=2)
        
        assert enforcer is not None
    
    def test_set_cpu_affinity(self):
        """Test setting CPU affinity."""
        from fault_keeper.systems.numa_afs.sentry import FirstTouchAffinityEnforcer
        
        enforcer = FirstTouchAffinityEnforcer()
        
        enforcer.set_cpu_affinity(0, [0, 1, 2])
        
        assert enforcer.cpu_affinity[0] == [0, 1, 2]
    
    def test_set_memory_affinity(self):
        """Test setting memory affinity."""
        from fault_keeper.systems.numa_afs.sentry import FirstTouchAffinityEnforcer
        
        enforcer = FirstTouchAffinityEnforcer()
        
        enforcer.set_memory_affinity(0, [0x1000, 0x2000])
        
        assert enforcer.memory_affinity[0] == [0x1000, 0x2000]
    
    def test_get_cpu_topology(self):
        """Test getting CPU topology."""
        from fault_keeper.systems.numa_afs.sentry import FirstTouchAffinityEnforcer
        
        enforcer = FirstTouchAffinityEnforcer(numa_nodes=2)
        
        topology = enforcer.get_cpu_topology()
        
        assert topology is not None


class TestNUMAAFS:
    """Tests for NUMA-AFS."""
    
    def test_init(self):
        """Test NUMA-AFS initialization."""
        from fault_keeper.systems.numa_afs.engine import NUMAAFS
        
        afs = NUMAAFS()
        
        assert afs is not None
    
    def test_bind_thread_to_core(self):
        """Test binding thread to core."""
        from fault_keeper.systems.numa_afs.engine import NUMAAFS
        
        afs = NUMAAFS()
        
        result = afs.bind_thread_to_core(1, 0)
        
        assert result is True
    
    def test_bind_memory_to_node(self):
        """Test binding memory to NUMA node."""
        from fault_keeper.systems.numa_afs.engine import NUMAAFS
        
        afs = NUMAAFS()
        
        result = afs.bind_memory_to_node(0x1000, 0)
        
        assert result is True
    
    def test_check_and_rebind_if_stalled(self):
        """Test checking and rebinding if stalled."""
        from fault_keeper.systems.numa_afs.engine import NUMAAFS
        
        afs = NUMAAFS()
        
        result = afs.check_and_rebind_if_stalled()
        
        assert result is not None
    
    def test_get_affinity_status(self):
        """Test getting affinity status."""
        from fault_keeper.systems.numa_afs.engine import NUMAAFS
        
        afs = NUMAAFS()
        
        status = afs.get_affinity_status()
        
        assert status is not None