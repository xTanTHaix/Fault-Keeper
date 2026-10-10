"""Tests for Typed-Hole Synthesis."""

from __future__ import annotations

import pytest

from fault_keeper.typing.ath_byped_hole import (
    TypedHoleSynthesizer,
    TypeConstraint,
    synthesize_type,
)


@pytest.fixture
def synthesizer():
    """Create typed-hole synthesizer instance."""
    return TypedHoleSynthesizer()


class TestTypedHoleSynthesizer:
    """Tests for TypedHoleSynthesizer class."""

    def test_init(self, synthesizer):
        """Test initializing synthesizer."""
        assert isinstance(synthesizer, TypedHoleSynthesizer)

    def test_synthesize_simple(self, synthesizer):
        """Test synthesizing simple type."""
        source = "x: int"
        result = synthesizer.synthesize(source)

        assert result is not None

    def test_synthesize_complex(self, synthesizer):
        """Test synthesizing complex type."""
        source = "def foo(x: int) -> str: ..."
        result = synthesizer.synthesize(source)

        assert result is not None


class TestTypeConstraint:
    """Tests for TypeConstraint dataclass."""

    def test_create_constraint(self):
        """Test creating type constraint."""
        constraint = TypeConstraint(
            variable="x",
            expected_type="int",
            inferred_type="int",
        )

        assert constraint.variable == "x"


class TestSynthesizeType:
    """Tests for synthesize_type function."""

    def test_synthesize_valid(self):
        """Test synthesizing valid type."""
        source = "x: int = 5"
        result = synthesize_type(source)

        assert result is not None

    def test_synthesize_invalid(self):
        """Test synthesizing invalid type."""
        source = "x: str ="
        result = synthesize_type(source)

        assert result is not None


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_source(self):
        """Test with empty source."""
        result = synthesize_type("")

        assert result is not None

    def test_none_source(self):
        """Test with None source."""
        try:
            result = synthesize_type(None)
        except Exception:
            pass  # Expected behavior


class TestPerformance:
    """Tests for performance."""

    def test_synthesize_performance(self, synthesizer):
        """Test synthesis performance."""
        import time

        source = "x: int" * 10

        start_time = time.perf_counter()
        for _ in range(10):
            synthesizer.synthesize(source)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should be fast (< 50ms)
        assert elapsed_ms < 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])