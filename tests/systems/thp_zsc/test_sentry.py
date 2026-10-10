"""Test suite for ZSC-THP sentry."""

import pytest
from fault_keeper.systems.thp_zsc.engine import (
    ZSC_ThP,
    DualPoolHybridAllocator,
    THPCompactionSiphon,
)
from fault_keeper.systems.thp_zsc.sentry import (
    KernelCompactionMonitor,
    THPArenaSentry,
    CompactionEvent,
)


class TestKernelCompactionMonitor:
    """Tests for KernelCompactionMonitor."""
    
    def test_init(self):
        """Test initialization."""
        monitor = KernelCompactionMonitor()
        
        assert monitor is not None
        assert len(monitor.events) == 0
    
    def test_record_compaction_begin(self):
        """Test recording compaction begin."""
        monitor = KernelCompactionMonitor()
        
        monitor.record_compaction_begin()
        
        # Should have recorded the event
        assert monitor.last_event_time > 0
    
    def test_record_compaction_end(self):
        """Test recording compaction end."""
        monitor = KernelCompactionMonitor()
        
        monitor.record_compaction_begin()
        monitor.record_compaction_end()
        
        # Should have recorded the event
        assert monitor.last_event_time > 0
    
    def test_get_compaction_stats(self):
        """Test getting compaction statistics."""
        monitor = KernelCompactionMonitor()
        
        monitor.record_compaction_begin()
        monitor.record_compaction_end()
        
        stats = monitor.get_compaction_stats()
        
        assert stats is not None


class TestTHPArenaSentry:
    """Tests for THPArenaSentry."""
    
    def test_init(self):
        """Test sentry initialization."""
        sentry = THPArenaSentry()
        
        assert sentry is not None
    
    def test_monitor(self):
        """Test monitoring."""
        sentry = THPArenaSentry()
        
        sentry.monitor()
        
        assert sentry.is_running


class TestZSC_ThP:
    """Tests for ZSC-ThP."""
    
    def test_init(self):
        """Test ZSC-ThP initialization."""
        zsc = ZSC_ThP()
        
        assert zsc is not None
    
    def test_allocate_and_monitor(self):
        """Test allocating and monitoring."""
        zsc = ZSC_ThP()
        
        ptr = zsc.allocate(1024)
        
        assert ptr is not None
    
    def test_trigger_background_compaction(self):
        """Test triggering background compaction."""
        zsc = ZSC_ThP()
        
        zsc.trigger_background_compaction()
        
        assert zsc.is_compacting
    
    def test_check_fragmentation(self):
        """Test checking fragmentation."""
        zsc = ZSC_ThP()
        
        frag = zsc.check_fragmentation()
        
        assert frag is not None
    
    def test_get_full_stats(self):
        """Test getting full statistics."""
        zsc = ZSC_ThP()
        
        stats = zsc.get_full_stats()
        
        assert stats is not None