"""Convex Hull: Monotone Chain algorithm O(N log N)."""

from __future__ import annotations
import math


def cross_product(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    """Compute cross product of vectors OA and OB."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def convex_hull_monotone_chain(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """
    Compute convex hull using Monotone Chain algorithm.
    
    Time Complexity: O(N log N)
    Space Complexity: O(N)
    
    Args:
        points: List of (x, y) points
        
    Returns:
        List of points forming convex hull in counter-clockwise order
    """
    if len(points) <= 1:
        return points[:]
    
    # Sort points by x-coordinate, then y
    points.sort()
    
    # Build lower hull
    lower = []
    for p in points:
        while len(lower) >= 2 and cross_product(
            lower[-2], lower[-1], p
        ) <= 0:
            lower.pop()
        lower.append(p)
    
    # Build upper hull
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross_product(
            upper[-2], upper[-1], p
        ) <= 0:
            upper.pop()
        upper.append(p)
    
    # Concatenate lower and upper hull
    # Remove last point of each half to avoid duplication
    return lower[:-1] + upper[:-1]


def convex_hull_2d(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Convenience function for 2D convex hull."""
    return convex_hull_monotone_chain(points)


if __name__ == "__main__":
    # Test convex hull
    points = [
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
        (0.5, 0.5),  # Inside the square - should not be in hull
    ]
    
    hull = convex_hull_2d(points)
    print(f"Convex hull: {hull}")
    print(f"Hull has {len(hull)} vertices")