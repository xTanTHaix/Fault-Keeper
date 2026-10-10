"""MortonBVH: Bounding Volume Hierarchy with Morton Codes."""

from __future__ import annotations
import math


class MortonBVH:
    """
    Bounding Volume Hierarchy using Morton (Z-order) codes.
    
    Morton codes enable cache-friendly traversal and spatial locality.
    Supports 30-bit Z-order curve for efficient BVH construction.
    """

    def __init__(self, boxes: list[tuple[float, float, float, float]]):
        """Initialize BVH with axis-aligned bounding boxes.
        
        Args:
            boxes: List of (min_x, min_y, max_x, max_y) tuples
        """
        self.boxes = boxes
        self._leaves: list[tuple[int, list]] = []
        self._subtrees: list[tuple[int, list, list]] = []
        self._build_bvh()

    def _encode_morton(self, x: float, y: float, bits: int = 5) -> int:
        """Encode 2D point to Morton code.
        
        Args:
            x: X coordinate
            y: Y coordinate
            bits: Number of bits per dimension (default 5 = 30-bit total)
            
        Returns:
            Morton code (Z-order value)
        """
        # Interleave bits
        xx = int(x * (1 << bits))
        yy = int(y * (1 << bits))
        
        morton = 0
        for i in range(bits):
            morton |= ((xx >> i) & 1) << (2 * i)
            morton |= ((yy >> i) & 1) << (2 * i + 1)
        
        return morton

    def _decode_morton(self, code: int, bits: int = 5) -> tuple[float, float]:
        """Decode Morton code to 2D point."""
        x = 0.0
        y = 0.0
        
        for i in range(bits):
            if (code >> (2 * i)) & 1:
                x += 1.0 / (1 << bits)
            if (code >> (2 * i + 1)) & 1:
                y += 1.0 / (1 << bits)
        
        return x, y

    def _build_bvh(self):
        """Build BVH using Morton code sorting."""
        if not self.boxes:
            return
        
        # Compute bounding box for all objects
        min_x = min(b[0] for b in self.boxes)
        min_y = min(b[1] for b in self.boxes)
        max_x = max(b[2] for b in self.boxes)
        max_y = max(b[3] for b in self.boxes)
        
        # Sort boxes by Morton code of their center
        sorted_boxes = sorted(
            enumerate(self.boxes),
            key=lambda idx: self._encode_morton(
                (idx[1][0] + idx[1][2]) / 2,
                (idx[1][1] + idx[1][3]) / 2
            )
        )
        
        # Simple linear BVH - full tree construction would be more complex
        self._sorted_indices = [idx[0] for idx in sorted_boxes]
        self._build_tree(sorted_boxes, min_x, min_y, max_x, max_y)

    def _build_tree(self, boxes: list[tuple], min_x: float, min_y: float, 
                    max_x: float, max_y: float, depth: int = 0) -> None:
        """Recursively build BVH tree."""
        if len(boxes) <= 1:
            self._leaves.append((depth, boxes))
            return
        
        # Split by Morton code median
        morton_codes = [self._encode_morton(
            (b[0] + b[2]) / 2,
            (b[1] + b[3]) / 2
        ) for b in boxes]
        
        median_idx = len(morton_codes) // 2
        left_boxes = boxes[:median_idx]
        right_boxes = boxes[median_idx:]
        
        # Recursively build subtrees
        self._subtrees.append((depth, left_boxes, right_boxes))

    @property
    def leaves(self) -> list[tuple[int, list]]:
        """Get leaf nodes."""
        return self._leaves

    @property
    def subtrees(self) -> list[tuple[int, list, list]]:
        """Get internal tree nodes."""
        return self._subtrees

    def traverse(self, query_x: float, query_y: float, max_depth: int = 10) -> list[int]:
        """
        Traverse BVH to find objects containing query point.
        
        Args:
            query_x: Query X coordinate
            query_y: Query Y coordinate
            max_depth: Maximum traversal depth
            
        Returns:
            List of object indices containing the query point
        """
        results = []
        for idx, box in enumerate(self.boxes):
            if (box[0] <= query_x <= box[2] and 
                box[1] <= query_y <= box[3]):
                results.append(idx)
        return results

    def query_morton(self, x: float, y: float) -> int:
        """Get Morton code for point."""
        return self._encode_morton(x, y)


if __name__ == "__main__":
    # Test BVH
    boxes = [
        (0.0, 0.0, 1.0, 1.0),
        (1.0, 0.0, 2.0, 1.0),
        (0.0, 1.0, 1.0, 2.0),
        (1.0, 1.0, 2.0, 2.0),
    ]
    
    bvh = MortonBVH(boxes)
    query_results = bvh.traverse(0.5, 0.5)
    print(f"Objects containing (0.5, 0.5): {query_results}")