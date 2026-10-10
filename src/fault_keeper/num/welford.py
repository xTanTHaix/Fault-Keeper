"""WelfordAccumulator: Streaming variance with O(1) space."""

from __future__ import annotations
import math


class WelfordAccumulator:
    """
    Welford's online algorithm for computing mean and variance.
    
    Algorithm (O(1) Space):
        Initialize: mean = 0, M2 = 0, count = 0
        For each new value x:
            count += 1
            delta = x - mean
            mean += delta / count
            M2 += delta * (x - mean)
    
    Variance = M2 / (count - 1) for count > 1
    Standard deviation = sqrt(variance)
    
    Advantages:
        - Numerically stable (no catastrophic cancellation)
        - O(1) memory regardless of N
        - Can process data stream in real-time
    """

    def __init__(self):
        """Initialize empty accumulator."""
        self._mean = 0.0
        self._M2 = 0.0
        self._count = 0

    def update(self, x: float) -> None:
        """Update accumulator with new value.
        
        Args:
            x: New data point to incorporate
        """
        self._count += 1
        delta = x - self._mean
        self._mean += delta / self._count
        delta2 = x - self._mean
        self._M2 += delta * delta2

    def add_batch(self, values: list[float]) -> None:
        """Update with batch of values."""
        for x in values:
            self.update(x)

    @property
    def count(self) -> int:
        """Get number of samples."""
        return self._count

    @property
    def mean(self) -> float:
        """Get sample mean."""
        if self._count == 0:
            return float('nan')
        return self._mean

    @property
    def M2(self) -> float:
        """Get sum of squared differences (M2)."""
        return self._M2

    def variance(self, ddof: int = 1) -> float:
        """Get sample or population variance.
        
        Args:
            ddof: Delta degrees of freedom (default 1 for sample variance)
            
        Returns:
            Sample variance if ddof=1, population variance if ddof=0
        """
        if self._count == 0:
            return float('nan')
        
        if ddof >= self._count:
            return float('nan')
        
        return self._M2 / (self._count - ddof)

    def std(self, ddof: int = 1) -> float:
        """Get sample or population standard deviation."""
        return math.sqrt(self.variance(ddof))

    def min_max(self) -> tuple[float, float]:
        """Get minimum and maximum values.
        
        Note: This requires tracking min/max separately since Welford
        algorithm doesn't preserve this information.
        
        Returns:
            Tuple of (min, max) or (nan, nan) if no data
        """
        # For now return nan - would need separate tracking
        return float('nan'), float('nan')

    def sum(self) -> float:
        """Get sum of all values."""
        return self._mean * self._count

    def reset(self) -> None:
        """Reset accumulator to initial state."""
        self._mean = 0.0
        self._M2 = 0.0
        self._count = 0


def test_welford_numerical_stability():
    """Test Welford algorithm against catastrophic cancellation."""
    
    # Test case: Large mean offset with small epsilon
    base_mean = 1e9
    epsilon = 1e-7
    
    # Generate data: base_mean + epsilon
    values = [base_mean + epsilon] * 1000000
    
    # Run Welford
    welford = WelfordAccumulator()
    welford.add_batch(values)
    
    print(f"Welford mean: {welford.mean}")
    print(f"Expected mean: {base_mean + epsilon}")
    print(f"Difference: {abs(welford.mean - (base_mean + epsilon))}")
    
    # Compare with two-pass variance (may have cancellation issues)
    mean = sum(values) / len(values)
    two_pass_var = sum((x - mean)**2 for x in values) / (len(values) - 1)
    
    print(f"\nTwo-pass variance: {two_pass_var}")
    print(f"Welford variance: {welford.variance()}")
    print(f"Difference: {abs(two_pass_var - welford.variance())}")


if __name__ == "__main__":
    test_welford_numerical_stability()