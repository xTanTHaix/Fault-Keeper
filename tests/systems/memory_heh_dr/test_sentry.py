"""Test suite for HEH-DR sentry."""

import pytest


class TestMemoryReclamationMonitor:
    """Tests for MemoryReclamationMonitor."""
    
    def test_init(self):
        """Test monitor initialization."""
        from fault_keeper.systems.memory_heh_dr.sentry import MemoryReclamationMonitor
        
        monitor = MemoryReclamationMonitor()
        
        assert monitor is not None
    
    def test_record_reclamation(self):
        """Test recording reclamation."""
        from fault_keeper.systems.memory_heh_dr.sentry import MemoryReclamationMonitor
        
        monitor = MemoryReclamationMonitor()
        
        monitor.record_reclamation(epoch=1, objects_count=10)
        
        stats = monitor.get_stats()
        
        assert stats["total_reclaimed"] == 10
        assert stats["event_count"] == 1
    
    def test_get_reclamation_rate(self):
        """Test getting reclamation rate."""
        from fault_keeper.systems.memory_heh_dr.sentry import MemoryReclamationMonitor
        
        monitor = MemoryReclamationMonitor()
        
        # Record multiple reclamations
        for _ in range(5):
            monitor.record_reclamation(epoch=_, objects_count=10)
        
        rate = monitor.get_reclamation_rate(window_seconds=10.0)
        
        assert rate >= 0


class TestHEH_DR_Sentry:
    """Tests for HEH-DR Sentry."""
    
    def test_init(self):
        """Test HEH-DR Sentry initialization."""
        from fault_keeper.systems.memory_heh_dr.sentry import HEH_DR_Sentry
        
        sentry = HEH_DR_Sentry()
        
        assert sentry is not None
    
    def test_monitor(self):
        """Test monitoring memory reclamation."""
        from fault_keeper.systems.memory_heh_dr.sentry import HEH_DR_Sentry
        
        sentry = HEH_DR_Sentry()
        
        sentry.monitor()
        
        assert sentry.is_running