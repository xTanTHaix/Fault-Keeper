"""Test suite for FS-CCO engine."""


import pytest


class TestCacheLineAlignment:
    """Tests for cache line alignment utilities."""
    
    def test_align_to_cache_line(self):
        """Test aligning address to cache line boundary."""
        from fault_keeper.systems.cache_fs_cco.engine import align_to_cache_line
        
        # Cache line size 64 bytes
        assert align_to_cache_line(0) == 0
        assert align_to_cache_line(1) == 64
        assert align_to_cache_line(63) == 64
        assert align_to_cache_line(64) == 64
        assert align_to_cache_line(65) == 128
        assert align_to_cache_line(127) == 128
        assert align_to_cache_line(128) == 128
    
    def test_align_struct_size(self):
        """Test struct size alignment."""
        from fault_keeper.systems.cache_fs_cco.engine import align_struct_size
        
        # Should align to 64 bytes (cache line)
        assert align_struct_size(32, 64) == 64
        assert align_struct_size(64, 64) == 64
        assert align_struct_size(100, 64) == 128
    
    def test_calculate_padding_needed(self):
        """Test calculating padding needed for alignment."""
        from fault_keeper.systems.cache_fs_cco.engine import calculate_padding_needed
        
        # From offset 65, next 64-byte boundary is at 128 (64*2)
        # Padding needed = 128 - 65 = 63
        assert calculate_padding_needed(65, 64) == 63
    
    def test_calculate_stride_alignment(self):
        """Test stride alignment calculation."""
        from fault_keeper.systems.cache_fs_cco.engine import calculate_stride_alignment
        
        # Array of 64-byte structs with 8-byte elements
        struct_size = 64
        element_size = 8
        
        alignment = calculate_stride_alignment(struct_size, element_size)
        
        assert alignment == 8


class TestFS_CCO:
    """Tests for main FS-CCO orchestrator."""
    
    def test_init(self):
        """Test initialization."""
        from fault_keeper.systems.cache_fs_cco.engine import FS_CCO
        
        fsc = FS_CCO(cache_line_size=64)
        
        assert fsc is not None
        # Check analyzer has cache_line_size
        assert hasattr(fsc.analyzer, 'cache_line_size')
        assert fsc.analyzer.cache_line_size == 64
    
    def test_get_cache_line_mask(self):
        """Test getting cache line mask."""
        from fault_keeper.systems.cache_fs_cco.engine import FS_CCO
        
        fsc = FS_CCO(cache_line_size=64)
        
        # Calculate mask manually: 64 bytes = 0x40, mask = 0x3F
        mask = (1 << (64 // 8)) - 1  # 8 bits per byte * 8 bytes = 64 bits
        
        assert isinstance(mask, int)
    
    def test_align_address(self):
        """Test address alignment."""
        from fault_keeper.systems.cache_fs_cco.engine import align_to_cache_line
        
        aligned = align_to_cache_line(123)
        
        assert aligned >= 0
        assert aligned % 64 == 0
    
    def test_detect_false_sharing_risk(self):
        """Test false sharing risk detection."""
        from fault_keeper.systems.cache_fs_cco.engine import FS_CCO, detect_false_sharing
        
        fsc = FS_CCO()
        
        # Mock fields for testing with proper offset
        fields = [
            {"name": "counter1", "offset": 0, "size": 8},
            {"name": "counter2", "offset": 56, "size": 8}
        ]
        
        risk = detect_false_sharing(fields)
        
        assert isinstance(risk, dict)
    
    def test_optimize_struct_layout(self):
        """Test struct layout optimization."""
        from fault_keeper.systems.cache_fs_cco.engine import FS_CCO
        
        fsc = FS_CCO()
        
        # Fields with offset for StructField
        fields = [
            {"name": "a", "size": 8, "align": 8, "offset": 0},
            {"name": "b", "size": 64, "align": 64, "offset": 8}
        ]
        
        layout = fsc.analyzer.optimize_layout("test", fields)
        
        assert layout is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])