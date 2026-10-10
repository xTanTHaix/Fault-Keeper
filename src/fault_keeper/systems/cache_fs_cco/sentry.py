"""FS-CCO Sentry: Cache Line Integrity & False Sharing Detection"""

import time
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class CacheLineEvent:
    """Represents a cache line event."""
    timestamp: float
    cache_line_id: int
    event_type: str  # "write", "invalidation", "conflict"
    affected_fields: List[str]


class CacheLineSentry:
    """Monitor cache line integrity and conflicts."""
    
    def __init__(self, cache_line_size: int = 64):
        """
        Initialize sentry.
        
        Args:
            cache_line_size: Cache line size in bytes
        """
        self.cache_line_size = cache_line_size
        self.events: List[CacheLineEvent] = []
        self.conflict_count: int = 0
    
    def record_write(self, cache_line_id: int, field_name: str) -> None:
        """Record a write to a cache line."""
        event = CacheLineEvent(
            timestamp=time.time(),
            cache_line_id=cache_line_id,
            event_type="write",
            affected_fields=[field_name],
        )
        
        self.events.append(event)
    
    def record_invalidation(self, cache_line_id: int, field_names: List[str]) -> None:
        """Record cache line invalidation."""
        event = CacheLineEvent(
            timestamp=time.time(),
            cache_line_id=cache_line_id,
            event_type="invalidation",
            affected_fields=field_names,
        )
        
        self.events.append(event)
    
    def detect_conflict(self, cache_line_id: int, writer_field: str, 
                       reader_field: str) -> bool:
        """
        Detect false sharing conflict.
        
        Args:
            cache_line_id: Cache line ID
            writer_field: Field being written
            reader_field: Field being read
            
        Returns:
            True if conflict detected
        """
        # Conflict if fields are in same cache line
        if cache_line_id < 0:
            # Unknown cache line - assume conflict
            self.conflict_count += 1
            return True
        
        return False
    
    def get_conflict_rate(self) -> float:
        """Get false sharing conflict rate."""
        if not self.events:
            return 0.0
        
        conflicts = sum(1 for e in self.events if e.event_type == "invalidation")
        return conflicts / len(self.events)
    
    def get_metrics(self) -> Dict[str, float]:
        """Get cache line metrics."""
        return {
            "total_events": len(self.events),
            "conflict_count": self.conflict_count,
            "conflict_rate": self.get_conflict_rate(),
            "cache_line_size": self.cache_line_size,
        }


class FalseSharingDetector:
    """Detect and report false sharing issues."""
    
    def __init__(self, cache_line_size: int = 64):
        """
        Initialize detector.
        
        Args:
            cache_line_size: Cache line size in bytes
        """
        self.cache_line_size = cache_line_size
        self.detected_issues: List[Dict] = []
    
    def analyze_struct(self, struct_name: str, fields: List[Dict]) -> List[Dict]:
        """
        Analyze struct for false sharing issues.
        
        Args:
            struct_name: Struct name
            fields: Field definitions
            
        Returns:
            List of detected issues
        """
        # Calculate field offsets
        current_offset = 0
        field_offsets = {}
        
        for field in fields:
            field_offsets[field['name']] = current_offset
            current_offset += field.get('size', 16)  # Default 16 bytes if not specified
        
        # Check for false sharing
        issues = []
        
        # Group fields by cache line
        cache_line_fields: Dict[int, List[str]] = {}
        
        for name, offset in field_offsets.items():
            line_id = offset // self.cache_line_size
            
            if line_id not in cache_line_fields:
                cache_line_fields[line_id] = []
            
            cache_line_fields[line_id].append(name)
        
        # Report issues for cache lines with multiple fields
        for line_id, field_names in cache_line_fields.items():
            if len(field_names) > 1:
                issue = {
                    "struct": struct_name,
                    "cache_line": line_id,
                    "fields": field_names,
                    "risk": "high" if len(field_names) > 2 else "medium",
                }
                issues.append(issue)
        
        return issues
    
    def get_issue_summary(self) -> Dict[str, any]:
        """Get summary of detected issues."""
        return {
            "total_issues": len(self.detected_issues),
            "high_risk_count": sum(1 for i in self.detected_issues if i.get("risk") == "high"),
            "medium_risk_count": sum(1 for i in self.detected_issues if i.get("risk") == "medium"),
        }


class FS_CCO:
    """Main FS-CCO orchestrator with sentry."""
    
    def __init__(self, cache_line_size: int = 64):
        """Initialize FS-CCO."""
        self.sentry = CacheLineSentry(cache_line_size=cache_line_size)
        self.detector = FalseSharingDetector(cache_line_size=cache_line_size)
    
    def record_cache_event(self, cache_line_id: int, field_name: str, 
                          event_type: str = "write") -> None:
        """Record a cache line event."""
        self.sentry.record_write(cache_line_id, field_name)
    
    def detect_false_sharing(self, struct_name: str, fields: List[Dict]) -> List[Dict]:
        """Detect false sharing issues."""
        issues = self.detector.analyze_struct(struct_name, fields)
        self.detected_issues.extend(issues)
        
        return issues
    
    def get_metrics(self) -> Dict[str, any]:
        """Get combined metrics."""
        return {
            "cache_line_sentry": self.sentry.get_metrics(),
            "false_sharing_detector": self.detector.get_issue_summary(),
        }


__all__ = [
    "CacheLineSentry",
    "FalseSharingDetector",
    "CacheLineEvent",
]