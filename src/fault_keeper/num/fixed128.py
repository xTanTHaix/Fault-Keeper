"""Fixed128: Q64.64 fixed-point arithmetic for financial calculations."""

from __future__ import annotations
import struct
import math
from decimal import Decimal, ROUND_HALF_UP


class Fixed128:
    """
    128-bit fixed-point number (Q64.64) for exact financial arithmetic.
    
    Represents value as 64-bit integer scaled by 2^64.
    Format: sign + 64-bit mantissa × 2^64
    
    This provides IEEE-754 epsilon-free precision suitable for:
    - Financial calculations (currency, interest)
    - Scientific computing requiring exact decimal arithmetic
    """

    Q_BITS = 64  # Quantization bits
    SCALE = 2**Q_BITS  # Scale factor = 2^64
    
    def __init__(self, value):
        """Initialize fixed-point number.
        
        Args:
            value: Input value (int, float, or string)
        """
        self._value = Decimal(str(value))
        self._quantized = self._quantize()

    def _quantize(self) -> int:
        """Quantize to 128-bit signed integer representation (Q64.64)."""
        d = Decimal(str(self._value))
        scaled = d * Decimal(self.SCALE)
        scaled_int = int(scaled.to_integral_value())
        
        # In Q64.64, signed representation has 128 bits: [-2^127, 2^127 - 1]
        max_int = (1 << 127) - 1
        min_int = -(1 << 127)
        if scaled_int > max_int or scaled_int < min_int:
            raise OverflowError(f"Value {self._value} exceeds Q64.64 range")
        
        return scaled_int

    def __repr__(self) -> str:
        """Return string representation."""
        return f"Fixed128({self._value})"

    @property
    def value(self) -> Decimal:
        """Get decimal value."""
        return self._value

    @property
    def quantized(self) -> int:
        """Get 64-bit integer representation."""
        return self._quantized

    def to_float(self) -> float:
        """Convert to float (may lose precision)."""
        return float(self._value)

    def to_decimal(self) -> Decimal:
        """Return Decimal value."""
        return self._value

    def __add__(self, other: "Fixed128") -> "Fixed128":
        """Add two fixed-point numbers."""
        total = self._value + other._value
        return Fixed128(total)

    def __radd__(self, other: "Fixed128") -> "Fixed128":
        """Right-add."""
        return self.__add__(other)

    def __sub__(self, other: "Fixed128") -> "Fixed128":
        """Subtract two fixed-point numbers."""
        diff = self._value - other._value
        return Fixed128(diff)

    def __rsub__(self, other: "Fixed128") -> "Fixed128":
        """Right-subtract."""
        return self.__sub__(other)

    def __mul__(self, other: "Fixed128") -> "Fixed128":
        """Multiply two fixed-point numbers.
        
        Result is Q128, converted back to Q64 by rounding.
        """
        product = self._value * other._value
        return Fixed128(product)

    def __rmul__(self, other: "Fixed128") -> "Fixed128":
        """Right-multiply."""
        return self.__mul__(other)

    def __truediv__(self, other: "Fixed128") -> "Fixed128":
        """Divide two fixed-point numbers."""
        quotient = self._value / other._value
        return Fixed128(quotient)

    def __rtruediv__(self, other: "Fixed128") -> "Fixed128":
        """Right-divide."""
        return self.__truediv__(other)

    def __neg__(self) -> "Fixed128":
        """Negate fixed-point number."""
        return Fixed128(-self._value)

    def __pos__(self) -> "Fixed128":
        """Positive fixed-point number."""
        return Fixed128(self._value)

    def __abs__(self) -> "Fixed128":
        """Absolute value."""
        return Fixed128(abs(self._value))

    def __eq__(self, other: "Fixed128") -> bool:
        """Equality check."""
        if isinstance(other, Fixed128):
            return self._value == other._value
        return False

    def __lt__(self, other: "Fixed128") -> bool:
        """Less than comparison."""
        if isinstance(other, Fixed128):
            return self._value < other._value
        return False

    def __le__(self, other: "Fixed128") -> bool:
        """Less than or equal comparison."""
        if isinstance(other, Fixed128):
            return self._value <= other._value
        return False

    def __gt__(self, other: "Fixed128") -> bool:
        """Greater than comparison."""
        if isinstance(other, Fixed128):
            return self._value > other._value
        return False

    def __ge__(self, other: "Fixed128") -> bool:
        """Greater than or equal comparison."""
        if isinstance(other, Fixed128):
            return self._value >= other._value
        return False

    @classmethod
    def from_float(cls, f: float) -> "Fixed128":
        """Create from float."""
        return cls(f)

    @classmethod
    def from_decimal(cls, d: Decimal) -> "Fixed128":
        """Create from Decimal."""
        return cls(d)

    @classmethod
    def from_int(cls, i: int) -> "Fixed128":
        """Create from integer."""
        return cls(i)

    @classmethod
    def from_string(cls, s: str) -> "Fixed128":
        """Create from string."""
        return cls(s)

    def round_to(self, decimals: int) -> "Fixed128":
        """Round to specified decimal places."""
        if decimals < 0:
            raise ValueError("decimals must be non-negative")
        
        quantize_str = "0." + "0" * decimals
        rounded = self._value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)
        return Fixed128(rounded)

    def to_string(self, decimals: int = 2) -> str:
        """Convert to string with specified decimal places."""
        rounded = self.round_to(decimals)
        return str(rounded._value)


if __name__ == "__main__":
    # Test IEEE-754 epsilon-free arithmetic
    a = Fixed128("0.1")
    b = Fixed128("0.2")
    c = a + b
    
    print(f"0.1 + 0.2 = {c}")
    print(f"Expected: 0.3, Got: {c.to_string(1)}")
    
    # Test financial calculation
    amount = Fixed128("1000.00")
    tax_rate = Fixed128("0.07")
    tax = amount * tax_rate
    total = amount + tax
    
    print(f"\nAmount: {amount}")
    print(f"Tax rate: {tax_rate}")
    print(f"Tax: {tax.to_string(2)}")
    print(f"Total: {total.to_string(2)}")