"""Test suite for FS-CCO sentry."""

import pytest
from fault_keeper.systems.cache_fs_cco.sentry import (
    CacheLineSentry,
    FalseSharingDetector,
    CacheLineEvent,
)
from fault_keeper.systems.cache_fs_cco.engine import FS_CCO


class TestCacheLineSentry:
    """Tests for CacheLineSentry."""
    
    def test_init(self):
        """Test initialization."""
        sentry = CacheLineSentry(cache_line_size=64)
        
        assert sentry is not None
    
    def test_record_write(self):
        """Test recording write event."""
        sentry = CacheLineSentry()
        
        sentry.record_write(0, "field_a")
        
        assert len(sentry.events) == 1
    
    def test_record_invalidation(self):
        """Test recording invalidation event."""
        sentry = CacheLineSentry()
        
        sentry.record_invalidation(0, ["field_a", "field_b"])
        
        assert len(sentry.events) == 1
    
    def test_detect_conflict(self):
        """Test conflict detection."""
        sentry = CacheLineSentry()
        
        result = sentry.detect_conflict(-1, "writer", "reader")
        
        assert isinstance(result, bool)
    
    def test_get_conflict_rate(self):
        """Test getting conflict rate."""
        sentry = CacheLineSentry()
        
        sentry.record_write(0, "a")
        sentry.record_invalidation(0, ["b"])
        
        rate = sentry.get_conflict_rate()
        
        assert 0.0 <= rate <= 1.0
    
    def test_get_metrics(self):
        """Test getting metrics."""
        sentry = CacheLineSentry()
        
        for _ in range(10):
            sentry.record_write(0, "field")
        
        metrics = sentry.get_metrics()
        
        assert "total_events" in metrics
        assert "conflict_count" in metrics


class TestFalseSharingDetector:
    """Tests for FalseSharingDetector."""
    
    def test_init(self):
        """Test initialization."""
        detector = FalseSharingDetector(cache_line_size=64)
        
        assert detector is not None
    
    def test_analyze_struct(self):
        """Test struct analysis."""
        detector = FalseSharingDetector()
        
        fields = [
            {"name": "a", "size": 4, "offset": 0, "align": 4},
            {"name": "b", "size": 8, "offset": 8, "align": 8},
        ]
        
        issues = detector.analyze_struct("TestStruct", fields)
        
        assert isinstance(issues, list)
    
    def test_get_issue_summary(self):
        """Test getting issue summary."""
        detector = FalseSharingDetector()
        
        detector.analyze_struct("Struct1", [
            {"name": "a", "size": 4, "offset": 0, "align": 4},
            {"name": "b", "size": 8, "offset": 8, "align": 8},
        ])
        
        summary = detector.get_issue_summary()
        
        assert "total_issues" in summary
        assert "high_risk_count" in summary


class TestFS_CCO:
    """Tests for main FS-CCO with sentry."""
    
    def test_init(self):
        """Test initialization."""
        fsc = FS_CCO(cache_line_size=64)
        
        assert fsc is not None
    
    def test_record_cache_event(self):
        """Test recording cache event."""
        fsc = FS_CCO()
        
        fsc.record_cache_event(0, "field_a", "write")
    
    def test_detect_false_sharing(self):
        """Test false sharing detection."""
        fsc = FS_CCO()
        
        fields = [
            {"name": "a", "size": 4, "offset": 0, "align": 4},
        ]
        
        issues = fsc.detect_false_sharing("Struct1", fields)
        
        assert isinstance(issues, list)
    
    def test_get_metrics(self):
        """Test getting metrics."""
        fsc = FS_CCO()
        
        metrics = fsc.get_metrics()
        
        assert "cache_line_sentry" in metrics
        assert "false_sharing_detector" in metrics


if __name__ == "__main__":
    pytest.main([__file__, "-v"])