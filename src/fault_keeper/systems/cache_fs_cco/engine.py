"""FS-CCO Engine: Cache Line Alignment & False Sharing Prevention"""

import struct
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import sys


@dataclass
class StructField:
    """Represents a struct field."""
    name: str
    size: int
    offset: int
    align: int
    
    def __repr__(self) -> str:
        return f"{self.name}: {self.size}B at {self.offset} (align={self.align})"


@dataclass
class StructLayout:
    """Represents an optimized struct layout."""
    name: str
    fields: List[StructField]
    total_size: int
    cache_line_aligned: bool
    false_sharing_risk: float
    
    def __repr__(self) -> str:
        return f"{self.name}: {self.total_size}B, aligned={self.cache_line_aligned}, risk={self.false_sharing_risk:.2%}"


class StructLayoutAnalyzer:
    """Analyze and optimize struct layouts for cache line alignment."""
    
    def __init__(self, cache_line_size: int = 64):
        """
        Initialize analyzer.
        
        Args:
            cache_line_size: Cache line size in bytes (default: 64)
        """
        self.cache_line_size = cache_line_size
    
    def analyze_struct(self, name: str, fields: List[Dict]) -> StructLayout:
        """
        Analyze struct layout and compute alignment.
        
        Args:
            name: Struct name
            fields: List of field definitions with name, size, offset, align
            
        Returns:
            StructLayout object
        """
        # Parse fields
        parsed_fields = [StructField(**f) for f in fields]
        
        # Calculate total size with padding
        total_size = 0
        current_offset = 0
        
        for field in parsed_fields:
            # Align field to cache line boundary if needed
            aligned_offset = (current_offset + field.align - 1) // field.align * field.align
            
            # Add padding if needed
            padding = aligned_offset - current_offset
            total_size += padding
            
            field.offset = aligned_offset
            current_offset = aligned_offset + field.size
        
        # Round up to cache line boundary
        total_size = ((total_size + self.cache_line_size - 1) // self.cache_line_size) * self.cache_line_size
        
        # Check false sharing risk
        false_sharing_risk = self._calculate_false_sharing_risk(parsed_fields, total_size)
        
        return StructLayout(
            name=name,
            fields=parsed_fields,
            total_size=total_size,
            cache_line_aligned=(total_size % self.cache_line_size == 0),
            false_sharing_risk=false_sharing_risk,
        )
    
    def _calculate_false_sharing_risk(self, fields: List[StructField], size: int) -> float:
        """Calculate false sharing risk."""
        if not fields:
            return 0.0
        
        # Risk increases with fields in same cache line
        fields_per_line = size // self.cache_line_size
        
        if fields_per_line <= 1:
            return 0.0  # No false sharing risk
        
        # Higher risk with more fields per cache line
        risk = min((fields_per_line - 1) / fields_per_line, 1.0)
        
        return risk
    
    def optimize_layout(self, name: str, fields: List[Dict]) -> StructLayout:
        """Optimize struct layout for minimal false sharing."""
        # Sort fields by size (largest first) to reduce padding
        sorted_fields = sorted(fields, key=lambda f: f.get('size', 0), reverse=True)
        
        return self.analyze_struct(name, sorted_fields)


from .sentry import CacheLineSentry, FalseSharingDetector


class FS_CCO:
    """False Sharing Cache-Line Optimizer."""
    
    def __init__(self, cache_line_size: int = 64):
        """
        Initialize FS-CCO.
        
        Args:
            cache_line_size: Cache line size in bytes (default: 64)
        """
        self.cache_line_size = cache_line_size
        self.analyzer = StructLayoutAnalyzer(cache_line_size=cache_line_size)
        self.sentry = CacheLineSentry(cache_line_size=cache_line_size)
        self.detector = FalseSharingDetector(cache_line_size=cache_line_size)
        self.optimized_layouts: Dict[str, StructLayout] = {}
        self.detected_issues: List[Dict] = []
    
    def record_cache_event(self, cache_line_id: int, field_name: str, 
                          event_type: str = "write") -> None:
        """Record a cache line event."""
        if event_type == "write":
            self.sentry.record_write(cache_line_id, field_name)
        elif event_type == "invalidation":
            self.sentry.record_invalidation(cache_line_id, [field_name])
        else:
            self.sentry.record_write(cache_line_id, field_name)
    
    def detect_false_sharing(self, struct_name: str, fields: List[Dict]) -> List[Dict]:
        """Detect false sharing issues in struct fields."""
        issues = self.detector.analyze_struct(struct_name, fields)
        self.detected_issues.extend(issues)
        return issues
    
    def get_metrics(self) -> Dict[str, any]:
        """Get combined metrics."""
        return {
            "cache_line_sentry": self.sentry.get_metrics(),
            "false_sharing_detector": self.detector.get_issue_summary(),
        }
    
    def analyze_and_optimize(self, struct_name: str, fields: List[Dict]) -> StructLayout:
        """
        Analyze and optimize struct layout.
        
        Args:
            struct_name: Name of the struct
            fields: List of field definitions
            
        Returns:
            Optimized StructLayout
        """
        layout = self.analyzer.optimize_layout(struct_name, fields)
        self.optimized_layouts[struct_name] = layout
        
        return layout
    
    def get_optimized_layout(self, struct_name: str) -> Optional[StructLayout]:
        """Get optimized layout for a struct."""
        return self.optimized_layouts.get(struct_name)
    
    def calculate_cache_line_offsets(self, struct_name: str) -> Dict[str, int]:
        """
        Calculate cache line offsets for each field.
        
        Args:
            struct_name: Name of the struct
            
        Returns:
            Dictionary mapping field names to cache line numbers
        """
        layout = self.get_optimized_layout(struct_name)
        
        if not layout:
            return {}
        
        offsets = {}
        current_line = 0
        
        for field in layout.fields:
            cache_line = field.offset // self.cache_line_size
            offsets[field.name] = cache_line
            
            # Check if field spans multiple cache lines
            if field.offset + field.size > (cache_line + 1) * self.cache_line_size:
                current_line += 1
        
        return offsets
    
    def get_layout_info(self, struct_name: str) -> Optional[Dict[str, any]]:
        """Get detailed layout information."""
        layout = self.get_optimized_layout(struct_name)
        
        if not layout:
            return None
        
        field_info = [
            {
                "name": f.name,
                "size": f.size,
                "offset": f.offset,
                "cache_line": f.offset // self.cache_line_size,
            }
            for f in layout.fields
        ]
        
        return {
            "struct_name": struct_name,
            "total_size": layout.total_size,
            "cache_line_aligned": layout.cache_line_aligned,
            "false_sharing_risk": layout.false_sharing_risk,
            "fields": field_info,
        }
    
    def check_false_sharing(self, struct_name: str) -> Tuple[bool, float]:
        """
        Check for false sharing risk in a struct.
        
        Args:
            struct_name: Name of the struct
        
        Returns:
            Tuple of (has_risk, risk_score)
        """
        layout = self.get_optimized_layout(struct_name)
        
        if not layout:
            return False, 0.0
        
        # Check if any cache line has multiple writable fields
        fields_per_line: Dict[int, List[str]] = {}
        
        for field in layout.fields:
            cache_line = field.offset // self.cache_line_size
            
            if cache_line not in fields_per_line:
                fields_per_line[cache_line] = []
            
            fields_per_line[cache_line].append(field.name)
        
        # Calculate risk based on fields per cache line
        max_fields_in_line = max(len(fields) for fields in fields_per_line.values()) if fields_per_line else 0
        
        has_risk = max_fields_in_line > 1
        risk_score = min((max_fields_in_line - 1) / max_fields_in_line, 1.0) if max_fields_in_line > 0 else 0.0
        
        return has_risk, float(risk_score)


def align_to_cache_line(address: int, cache_line_size: int = 64) -> int:
    """Align address to cache line boundary."""
    return (address + cache_line_size - 1) // cache_line_size * cache_line_size


def align_struct_size(size: int, alignment: int) -> int:
    """Align struct size to given alignment."""
    return (size + alignment - 1) // alignment * alignment


def calculate_padding_needed(current_offset: int, target_alignment: int) -> int:
    """Calculate padding needed to reach next alignment boundary."""
    next_boundary = ((current_offset + target_alignment - 1) // target_alignment) * target_alignment
    return max(0, next_boundary - current_offset)


def detect_false_sharing(fields: List[Dict]) -> Dict[str, int]:
    """Detect potential false sharing in struct fields."""
    cache_lines: Dict[int, List[str]] = {}
    
    for field in fields:
        offset = field.get('offset', 0)
        size = field.get('size', 0)
        
        start_line = offset // 64
        end_line = (offset + size - 1) // 64
        
        for line in range(start_line, end_line + 1):
            if line not in cache_lines:
                cache_lines[line] = []
            cache_lines[line].append(field['name'])
    
    return cache_lines


def calculate_stride_alignment(struct_size: int, element_size: int) -> int:
    """Calculate stride alignment for array elements."""
    return element_size


def merge_into_same_cache_line(fields: List[Dict]) -> bool:
    """Merge fields into same cache line if possible."""
    total_size = sum(f.get('size', 0) for f in fields)
    
    # Can fit in one cache line if total <= 64
    return total_size <= 64


def calculate_padding_waste(fields: List[Dict]) -> int:
    """Calculate total padding waste in struct."""
    current_offset = 0
    waste = 0
    
    for field in fields:
        size = field.get('size', 0)
        align = field.get('align', size)
        
        # Calculate next aligned offset
        next_boundary = ((current_offset + align - 1) // align) * align
        padding = max(0, next_boundary - current_offset)
        waste += padding
        
        current_offset = next_boundary + size
    
    return waste


__all__ = [
    "FS_CCO",
    "StructLayout",
    "StructField",
    "StructLayoutAnalyzer",
    "align_to_cache_line",
    "align_struct_size",
    "calculate_padding_needed",
    "detect_false_sharing",
    "calculate_stride_alignment",
    "merge_into_same_cache_line",
    "calculate_padding_waste",
]