"""Dual Number: Forward-mode automatic differentiation."""

from __future__ import annotations
import math
from typing import Callable, Union


class DualNumber:
    """
    Dual Number for forward-mode automatic differentiation.
    
    A dual number has the form: x + ε·ẋ where ε² = 0
    
    Attributes:
        value: The real part (x)
        dual: The dual part (ẋ, derivative)
    """

    def __init__(self, value: float = 0.0, dual: float = 0.0, *, real: Optional[float] = None):
        """Initialize dual number.
        
        Args:
            value: Real part x
            dual: Dual part ẋ (derivative), default 0.0
            real: Optional alias for value
        """
        if real is not None:
            value = real
        self.value = float(value)
        self.dual = float(dual)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"DualNumber({self.value}, {self.dual})"

    @property
    def real(self) -> float:
        """Get real part."""
        return self.value

    @property
    def deriv(self) -> float:
        """Get derivative (dual part)."""
        return self.dual

    def __add__(self, other: Union["DualNumber", float]) -> "DualNumber":
        """Add dual number or scalar."""
        if isinstance(other, DualNumber):
            return DualNumber(self.value + other.value, self.dual + other.dual)
        return DualNumber(self.value + other, self.dual)

    def __radd__(self, other: float) -> "DualNumber":
        """Right-add scalar."""
        return self.__add__(other)

    def __sub__(self, other: Union["DualNumber", float]) -> "DualNumber":
        """Subtract dual number or scalar."""
        if isinstance(other, DualNumber):
            return DualNumber(self.value - other.value, self.dual - other.dual)
        return DualNumber(self.value - other, self.dual)

    def __rsub__(self, other: float) -> "DualNumber":
        """Right-subtract scalar."""
        return DualNumber(other - self.value, -self.dual)

    def __mul__(self, other: Union["DualNumber", float]) -> "DualNumber":
        """Multiply dual number or scalar.
        
        (x + ε·ẋ) · (y + ε·ẏ) = x·y + ε·(x·ẏ + y·ẋ)
        """
        if isinstance(other, DualNumber):
            new_value = self.value * other.value
            new_dual = self.value * other.dual + other.value * self.dual
            return DualNumber(new_value, new_dual)
        return DualNumber(self.value * other, self.dual * other)

    def __rmul__(self, other: float) -> "DualNumber":
        """Right-multiply scalar."""
        return self.__mul__(other)

    def __truediv__(self, other: Union["DualNumber", float]) -> "DualNumber":
        """Divide dual number or scalar.
        
        (x + ε·ẋ) / y = (x/y) + ε·(ẋ/y)
        """
        if isinstance(other, DualNumber):
            y = other.value
            ẏ = other.dual
            new_value = self.value / y
            new_dual = (self.dual * y - self.value * ẏ) / (y * y)
            return DualNumber(new_value, new_dual)
        y = float(other)
        return DualNumber(self.value / y, self.dual / y)

    def __rtruediv__(self, other: float) -> "DualNumber":
        """Right-divide scalar."""
        x = self.value
        ẋ = self.dual
        new_value = other / x
        new_dual = (-other * ẋ) / (x * x)
        return DualNumber(new_value, new_dual)

    def __neg__(self) -> "DualNumber":
        """Negate dual number."""
        return DualNumber(-self.value, -self.dual)

    def __pos__(self) -> "DualNumber":
        """Positive dual number."""
        return DualNumber(self.value, self.dual)

    def __abs__(self) -> "DualNumber":
        """Absolute value (not differentiable at 0, but forward-mode works)."""
        sign = 1.0 if self.value > 0 else -1.0
        return DualNumber(abs(self.value), sign * self.dual)

    def sin(self) -> "DualNumber":
        """Sine: sin(x + ε·ẋ) = sin(x) + ε·cos(x)·ẋ"""
        s = math.sin(self.value)
        c = math.cos(self.value)
        return DualNumber(s, c * self.dual)

    def cos(self) -> "DualNumber":
        """Cosine: cos(x + ε·ẋ) = cos(x) - ε·sin(x)·ẋ"""
        s = math.sin(self.value)
        c = math.cos(self.value)
        return DualNumber(c, -s * self.dual)

    def tan(self) -> "DualNumber":
        """Tangent: tan(x + ε·ẋ) = tan(x) + ε·sec²(x)·ẋ"""
        s = math.sin(self.value)
        c = math.cos(self.value)
        t = s / c
        sec2 = 1.0 / (c * c)
        return DualNumber(t, sec2 * self.dual)

    def exp(self) -> "DualNumber":
        """Exponential: exp(x + ε·ẋ) = exp(x) + ε·exp(x)·ẋ"""
        e = math.exp(self.value)
        return DualNumber(e, e * self.dual)

    def log(self) -> "DualNumber":
        """Natural logarithm: log(x + ε·ẋ) = log(x) + ε·ẋ/x"""
        if self.value <= 0:
            raise ValueError("log requires positive argument")
        l = math.log(self.value)
        return DualNumber(l, self.dual / self.value)

    def sqrt(self) -> "DualNumber":
        """Square root: sqrt(x + ε·ẋ) = sqrt(x) + ε·ẋ/(2·sqrt(x))"""
        if self.value < 0:
            raise ValueError("sqrt requires non-negative argument")
        s = math.sqrt(self.value)
        return DualNumber(s, self.dual / (2 * s))

    def pow(self, n: int) -> "DualNumber":
        """Power: (x + ε·ẋ)^n = x^n + ε·n·x^(n-1)·ẋ"""
        p = self.value ** n
        derivative = n * (self.value ** (n - 1)) * self.dual
        return DualNumber(p, derivative)

    def __pow__(self, n: int) -> "DualNumber":
        """Raise to integer power."""
        return self.pow(n)

    def __call__(self, func: Callable[["DualNumber"], "DualNumber"]) -> "DualNumber":
        """Apply function f(x + ε·ẋ)."""
        return func(self)

    @classmethod
    def from_float(cls, x: float) -> "DualNumber":
        """Create dual number from float with zero derivative."""
        return cls(x, 0.0)


def derivative(f: Callable[[float], float], x: float, h: float = 1e-7) -> float:
    """Compute derivative using dual numbers.
    
    Args:
        f: Function f(x) that takes and returns float
        x: Point at which to compute derivative
        h: Dual part (default 1e-7 for numerical stability)
    
    Returns:
        Approximate derivative f'(x)
    """
    dual_x = DualNumber(x, h)
    result = f(dual_x)
    return result.deriv


if __name__ == "__main__":
    # Simple test
    x = DualNumber(2.5, 1.0)
    f = lambda x: 3*x**3 - 2*x**2 + x.sin() * x.exp()
    df = f(x)
    print(f"Function value at x=2.5: {df.value}")
    print(f"Derivative (dual part): {df.deriv}")
    
    # Verify against analytical derivative
    import math
    x_val = 2.5
    analytical = 9*x_val**2 - 4*x_val + math.cos(x_val)*math.exp(x_val) + math.sin(x_val)*math.exp(x_val)
    print(f"Analytical derivative: {analytical}")
    print(f"Difference: {abs(df.deriv - analytical)}")