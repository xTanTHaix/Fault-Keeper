"""Test suite for ZSC-THP engine."""


import pytest


class TestMemoryArena:
    """Tests for MemoryArena class."""
    
    def test_arena_creation(self):
        """Test creating a memory arena."""
        from fault_keeper.systems.thp_zsc.engine import MemoryArena
        
        arena = MemoryArena(name="test", size_mb=1024, page_size_kb=4)
        
        assert arena.name == "test"
        assert arena.size_mb == 1024
    
    def test_arena_pages(self):
        """Test calculating arena pages."""
        from fault_keeper.systems.thp_zsc.engine import MemoryArena
        
        arena = MemoryArena(name="test", size_mb=1024, page_size_kb=4)
        
        assert arena.total_pages == 262144  # 1024 * 1024 / 4
        assert arena.allocated_pages == 0
    
    def test_arena_utilization(self):
        """Test arena utilization."""
        from fault_keeper.systems.thp_zsc.engine import MemoryArena
        
        arena = MemoryArena(name="test", size_mb=1024, page_size_kb=4)
        
        assert arena.utilization_percent == 0.0


class TestDualPoolHybridAllocator:
    """Tests for Dual-Pool Hybrid Allocator."""
    
    def test_allocator_init(self):
        """Test allocator initialization."""
        from fault_keeper.systems.thp_zsc.engine import DualPoolHybridAllocator
        
        allocator = DualPoolHybridAllocator()
        
        assert allocator is not None
    
    def test_allocate_critical(self):
        """Test critical path allocation."""
        from fault_keeper.systems.thp_zsc.engine import DualPoolHybridAllocator, MemoryArena
        
        allocator = DualPoolHybridAllocator(static_arena_size_mb=2048)
        
        # Should be able to allocate critical memory
        result = allocator.allocate_critical(1)
        
        assert result is not None
    
    def test_allocate_non_critical(self):
        """Test non-critical path allocation."""
        from fault_keeper.systems.thp_zsc.engine import DualPoolHybridAllocator, MemoryArena
        
        allocator = DualPoolHybridAllocator(dynamic_arena_size_mb=4096)
        
        # Should be able to allocate non-critical memory
        result = allocator.allocate_non_critical(1)
        
        assert result is not None
    
    def test_allocation_stats(self):
        """Test allocation statistics."""
        from fault_keeper.systems.thp_zsc.engine import DualPoolHybridAllocator
        
        allocator = DualPoolHybridAllocator()
        
        # Make some allocations
        allocator.allocate_critical(1)
        allocator.allocate_non_critical(1)
        
        stats = allocator.get_allocation_stats()
        
        assert "static_arena" in stats
        assert "dynamic_arena" in stats


class TestTHPCompactionSiphon:
    """Tests for Compaction Siphon."""
    
    def test_siphon_init(self):
        """Test siphon initialization."""
        from fault_keeper.systems.thp_zsc.engine import THPCompactionSiphon, DualPoolHybridAllocator
        
        allocator = DualPoolHybridAllocator()
        siphon = THPCompactionSiphon(allocator)
        
        assert siphon is not None
    
    def test_run_background_compaction(self):
        """Test background compaction."""
        from fault_keeper.systems.thp_zsc.engine import THPCompactionSiphon, DualPoolHybridAllocator
        
        allocator = DualPoolHybridAllocator()
        siphon = THPCompactionSiphon(allocator)
        
        result = siphon.run_background_compaction()
        
        assert isinstance(result, bool)
    
    def test_compact_specific_pages(self):
        """Test compaction of specific pages."""
        from fault_keeper.systems.thp_zsc.engine import THPCompactionSiphon, DualPoolHybridAllocator
        
        allocator = DualPoolHybridAllocator()
        siphon = THPCompactionSiphon(allocator)
        
        # Test with empty list
        result = siphon.compact_specific_pages([])
        
        assert result == 0


class TestZSC_ThP:
    """Tests for main ZSC-THP orchestrator."""
    
    def test_init(self):
        """Test initialization."""
        from fault_keeper.systems.thp_zsc import ZSC_ThP
        
        zsc = ZSC_ThP()
        
        assert zsc is not None
    
    def test_allocate_memory_critical(self):
        """Test critical memory allocation."""
        from fault_keeper.systems.thp_zsc import ZSC_ThP
        
        zsc = ZSC_ThP()
        
        result = zsc.allocate_memory(1, is_critical=True)
        
        assert isinstance(result, str)
    
    def test_allocate_memory_non_critical(self):
        """Test non-critical memory allocation."""
        from fault_keeper.systems.thp_zsc import ZSC_ThP
        
        zsc = ZSC_ThP()
        
        result = zsc.allocate_memory(1, is_critical=False)
        
        assert isinstance(result, str)
    
    def test_trigger_background_compaction(self):
        """Test background compaction."""
        from fault_keeper.systems.thp_zsc import ZSC_ThP
        
        zsc = ZSC_ThP()
        
        result = zsc.trigger_background_compaction()
        
        assert isinstance(result, bool)
    
    def test_get_allocation_efficiency(self):
        """Test allocation efficiency."""
        from fault_keeper.systems.thp_zsc import ZSC_ThP
        
        zsc = ZSC_ThP()
        
        result = zsc.get_allocation_efficiency()
        
        assert isinstance(result, float)
    
    def test_get_full_stats(self):
        """Test full statistics retrieval."""
        from fault_keeper.systems.thp_zsc import ZSC_ThP
        
        zsc = ZSC_ThP()
        
        stats = zsc.get_full_stats()
        
        assert "allocation_stats" in stats
        assert "compaction_stats" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])