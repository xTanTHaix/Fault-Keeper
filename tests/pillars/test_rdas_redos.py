"""Tests for ReDoS Detector."""

from __future__ import annotations

import re

import pytest

from fault_keeper.num.rdas_redos import (
    RegexComplexityAnalyzer,
    ReDoSPattern,
    detect_reDos,
    analyze_regex_complexity,
    optimize_regex,
    validate_input_length,
)


@pytest.fixture
def redos_analyzer():
    """Create RedoS analyzer instance."""
    return RegexComplexityAnalyzer()


@pytest.fixture
def dangerous_regex():
    """Dangerous regex pattern that causes ReDoS."""
    # Catastrophic backtracking pattern
    return r"(a+)+b+"


@pytest.fixture
def safe_regex():
    """Safe regex pattern."""
    return r"a+b+"


class TestValidateInputLength:
    """Tests for validate_input_length function."""

    def test_valid_length(self):
        """Test valid input length."""
        result = validate_input_length("test_string")

        assert result["valid"] is True

    def test_empty_string(self):
        """Test empty string validation."""
        result = validate_input_length("")

        assert result["valid"] is True

    def test_long_string(self):
        """Test long input string."""
        long_string = "a" * 10000
        result = validate_input_length(long_string)

        assert result["valid"] is False


class TestAnalyzeRegexComplexity:
    """Tests for analyze_regex_complexity function."""

    def test_simple_pattern(self):
        """Test simple regex pattern analysis."""
        pattern = r"abc"
        result = analyze_regex_complexity(pattern)

        assert result["complexity_score"] == 0.0
        assert result["is_dangerous"] is False

    def test_dangerous_pattern(self, dangerous_regex):
        """Test dangerous regex pattern analysis."""
        result = analyze_regex_complexity(dangerous_regex)

        assert result["is_dangerous"] is True
        assert result["complexity_score"] > 0.5

    def test_safe_pattern(self, safe_regex):
        """Test safe regex pattern analysis."""
        result = analyze_regex_complexity(safe_regex)

        assert result["is_dangerous"] is False


class TestDetectReDos:
    """Tests for detect_reDos function."""

    def test_detect_dangerous(self, dangerous_regex):
        """Test detecting ReDoS vulnerability."""
        result = detect_reDos(dangerous_regex)

        assert result["has_vulnerability"] is True

    def test_detect_safe(self, safe_regex):
        """Test detecting safe pattern."""
        result = detect_reDos(safe_regex)

        assert result["has_vulnerability"] is False


class TestRegexComplexityAnalyzer:
    """Tests for RegexComplexityAnalyzer class."""

    def test_init(self, redos_analyzer):
        """Test initializing analyzer."""
        assert isinstance(redos_analyzer, RegexComplexityAnalyzer)

    def test_analyze_pattern(self, redos_analyzer, dangerous_regex):
        """Test analyzing regex pattern."""
        result = redos_analyzer.analyze_pattern(dangerous_regex)

        assert result["is_dangerous"] is True

    def test_optimize_pattern(self, redos_analyzer, dangerous_regex):
        """Test optimizing regex pattern."""
        optimized = redos_analyzer.optimize_pattern(dangerous_regex)

        assert optimized is not None


class TestReDoSPattern:
    """Tests for ReDoSPattern dataclass."""

    def test_create_pattern(self):
        """Test creating RedoS pattern."""
        pattern = ReDoSPattern(
            regex=r"(a+)+b+",
            complexity_score=0.8,
            is_dangerous=True,
        )

        assert pattern.regex == r"(a+)+b+"
        assert pattern.is_dangerous is True


class TestOptimizeRegex:
    """Tests for optimize_regex function."""

    def test_optimize_simple(self):
        """Test optimizing simple regex."""
        original = r"abc"
        result = optimize_regex(original)

        assert result == original

    def test_optimize_dangerous(self, dangerous_regex):
        """Test optimizing dangerous regex."""
        optimized = optimize_regex(dangerous_regex)

        # Should return optimized version or None if not fixable
        assert optimized is not None


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_pattern(self):
        """Test empty pattern analysis."""
        result = analyze_regex_complexity("")

        assert result["is_dangerous"] is False

    def test_null_pattern(self):
        """Test None pattern handling."""
        try:
            result = analyze_regex_complexity(None)
            # Should handle gracefully
        except Exception:
            pass  # Expected to raise or return error


class TestPerformance:
    """Tests for performance."""

    def test_analyze_performance(self, redos_analyzer):
        """Test analysis performance."""
        import time

        pattern = r"(a+)+b+"

        start_time = time.perf_counter()
        for _ in range(100):
            redos_analyzer.analyze_pattern(pattern)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should be fast (< 100ms)
        assert elapsed_ms < 100


class TestPatternMatching:
    """Tests for pattern matching accuracy."""

    def test_match_dangerous_patterns(self):
        """Test matching known dangerous patterns."""
        analyzer = RegexComplexityAnalyzer()

        dangerous_patterns = [
            r"(a+)+b+",
            r"(a|aa)*a",
            r"(a+b*)*",
        ]

        for pattern in dangerous_patterns:
            result = analyze_regex_complexity(pattern)
            assert result["is_dangerous"] is True

    def test_match_safe_patterns(self):
        """Test matching known safe patterns."""
        analyzer = RegexComplexityAnalyzer()

        safe_patterns = [
            r"abc",
            r"a+b+",
            r"[a-z]+",
        ]

        for pattern in safe_patterns:
            result = analyze_regex_complexity(pattern)
            assert result["is_dangerous"] is False


class TestComplexityScoring:
    """Tests for complexity scoring."""

    def test_score_range(self):
        """Test complexity score is within valid range."""
        analyzer = RegexComplexityAnalyzer()

        result = analyzer.analyze_pattern(r"(a+)+b+")
        score = result["complexity_score"]

        assert 0.0 <= score <= 1.0


class TestMitigation:
    """Tests for mitigation strategies."""

    def test_mitigation_suggestions(self):
        """Test getting mitigation suggestions."""
        analyzer = RegexComplexityAnalyzer()

        result = analyzer.get_mitigation_strategy(r"(a+)+b+")

        assert isinstance(result, list)
        assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])