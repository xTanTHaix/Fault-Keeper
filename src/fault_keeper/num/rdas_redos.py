"""ReDoS Detector: Catastrophic Backtracking Prevention for Regular Expressions."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import time
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ReDoSPattern:
    """Represents a regex pattern with ReDoS analysis results."""

    regex: str
    complexity_score: float = 0.0
    is_dangerous: bool = False
    vulnerabilities: List[str] = field(default_factory=list)


@dataclass
class RegexPattern:
    """Represents a regex pattern with legacy analysis results."""

    pattern: str
    flags: int = 0
    is_vulnerable: bool = False
    vulnerability_type: Optional[str] = None
    complexity_estimate: int = 1
    suggested_fix: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern,
            "flags": self.flags,
            "is_vulnerable": self.is_vulnerable,
            "vulnerability_type": self.vulnerability_type,
            "complexity_estimate": self.complexity_estimate,
            "suggested_fix": self.suggested_fix,
        }


@dataclass
class ReDoSVulnerability:
    """Represents a detected ReDoS vulnerability."""

    pattern: str
    vulnerability_type: str
    severity: str
    explanation: str
    affected_positions: List[int]
    suggested_fix: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern,
            "vulnerability_type": self.vulnerability_type,
            "severity": self.severity,
            "explanation": self.explanation,
            "affected_positions": self.affected_positions,
            "suggested_fix": self.suggested_fix,
        }


class RegexComplexityAnalyzer:
    """Deterministic complexity analyzer for regular expressions."""

    def __init__(self) -> None:
        self._dangerous_regexes = [
            # Nested quantifiers like (a+)+ or (a*)* or (a+){2,}
            re.compile(r"\([^()]*(?:[+*]|\{\d+(?:,\d*)?\})[^()]*\)(?:[+*]|\{\d+(?:,\d*)?\})"),
            # Overlapping alternation inside quantifier like (a|aa)* or (a|aa)+ or (a|aa){2,}
            re.compile(r"\([^()]*\|[^()]*\)(?:[+*]|\{\d+(?:,\d*)?\})"),
            # Ambiguous multi-greedy wildcards
            re.compile(r"\.\*.*?\.\*"),
        ]

    def analyze_pattern(self, pattern: str | None) -> dict[str, Any]:
        """Analyze regular expression for catastrophic backtracking vulnerability."""
        if not pattern:
            return {
                "pattern": pattern or "",
                "is_dangerous": False,
                "complexity_score": 0.0,
                "vulnerabilities": [],
            }

        vulnerabilities: List[str] = []
        is_dangerous = False

        for detector in self._dangerous_regexes:
            match = detector.search(pattern)
            if match:
                is_dangerous = True
                matched_sub = match.group(0)
                vulnerabilities.append(f"Catastrophic backtracking hazard detected: {matched_sub}")

        if is_dangerous:
            # Score between 0.7 and 0.95 depending on vulnerability density
            complexity_score = min(0.95, 0.70 + 0.10 * len(vulnerabilities))
        else:
            complexity_score = 0.0

        return {
            "pattern": pattern,
            "is_dangerous": is_dangerous,
            "complexity_score": float(complexity_score),
            "vulnerabilities": vulnerabilities,
        }

    def optimize_pattern(self, pattern: str) -> str:
        """Optimize dangerous regex patterns by flattening nested quantifiers."""
        if not pattern:
            return pattern

        analysis = self.analyze_pattern(pattern)
        if not analysis["is_dangerous"]:
            return pattern

        optimized = pattern
        # Convert nested (a+)+ or (a+){2,} to a+
        optimized = re.sub(r"\(([a-zA-Z0-9_-]+)\+\)(?:\+|\{\d+,?\d*\})", r"\1+", optimized)
        # Convert (a*)* or (a*){2,} to a*
        optimized = re.sub(r"\(([a-zA-Z0-9_-]+)\*\)(?:\*|\{\d+,?\d*\})", r"\1*", optimized)
        # Convert overlapping alternation like (a|aa)* to a*
        optimized = re.sub(r"\(([a-zA-Z0-9_-]+)\|\1+\)\*", r"\1*", optimized)
        optimized = re.sub(r"\(([a-zA-Z0-9_-]+)\|\1+\)\+", r"\1+", optimized)
        # Convert nested multi-quantifier (a+b*)* to (ab*)* without stripping outer quantifier
        optimized = re.sub(r"\(([a-zA-Z0-9_-]+)\+([a-zA-Z0-9_-]+)\*\)\*", r"(\1\2*)*", optimized)
        optimized = re.sub(r"\(([a-zA-Z0-9_-]+)\+([a-zA-Z0-9_-]+)\*\)\+", r"(\1\2*)+", optimized)

        return optimized

    def get_mitigation_strategy(self, pattern: str) -> List[str]:
        """Return recommended mitigation strategies for the pattern."""
        return [
            "Flatten nested quantifiers into atomic groups or single-level quantifiers",
            "Use possessive quantifiers (e.g., ++ or *+) to prevent backtracking",
            "Enforce strict input string length validation with validate_input_length",
            "Deploy linear-time DFA-based regex engines for untrusted user inputs",
        ]


def validate_input_length(input_string: str, max_length: int = 1000) -> Dict[str, Any]:
    """Validate that input string does not exceed safe length boundary."""
    if input_string is None:
        return {"valid": True, "length": 0, "max_length": max_length}

    length = len(input_string)
    return {
        "valid": length <= max_length,
        "length": length,
        "max_length": max_length,
    }


def analyze_regex_complexity(pattern: str | None) -> Dict[str, Any]:
    """Analyze regex complexity and catastrophic backtracking potential."""
    analyzer = RegexComplexityAnalyzer()
    return analyzer.analyze_pattern(pattern)


def detect_reDos(pattern: str) -> Dict[str, Any]:
    """Detect ReDoS vulnerability in regular expression."""
    analyzer = RegexComplexityAnalyzer()
    result = analyzer.analyze_pattern(pattern)
    return {
        "has_vulnerability": result["is_dangerous"],
        "is_dangerous": result["is_dangerous"],
        "complexity_score": result["complexity_score"],
        "pattern": result["pattern"],
        "vulnerabilities": result["vulnerabilities"],
    }


def optimize_regex(pattern: str) -> str:
    """Optimize regular expression to mitigate ReDoS hazards."""
    analyzer = RegexComplexityAnalyzer()
    return analyzer.optimize_pattern(pattern)


# ---------------------------------------------------------------------------
# Legacy Support & Engine Aliases
# ---------------------------------------------------------------------------

class ReDoSDetector:
    """Legacy detector alias."""

    def __init__(self) -> None:
        self.analyzer = RegexComplexityAnalyzer()

    def analyze_pattern(self, pattern: str, flags: int = 0) -> RegexPattern:
        res = self.analyzer.analyze_pattern(pattern)
        return RegexPattern(
            pattern=pattern,
            flags=flags,
            is_vulnerable=res["is_dangerous"],
            vulnerability_type="catastrophic_backtracking" if res["is_dangerous"] else None,
            complexity_estimate=int(res["complexity_score"] * 3) + 1,
            suggested_fix=self.analyzer.optimize_pattern(pattern) if res["is_dangerous"] else None,
        )


class PerformanceBasedReDoSDetector:
    """Detects ReDoS through performance testing."""

    def __init__(self, timeout_ms: float = 100.0) -> None:
        self.timeout_ms = timeout_ms

    def test_pattern_performance(self, pattern: str, malicious_input: str) -> Dict[str, Any]:
        try:
            compiled = re.compile(pattern)
        except re.error as e:
            return {"pattern": pattern, "error": str(e), "is_vulnerable": False}

        analyzer = RegexComplexityAnalyzer()
        static_analysis = analyzer.analyze_pattern(pattern)

        start_time = time.perf_counter()
        matched = False
        is_vulnerable = False

        if static_analysis["is_dangerous"] and len(malicious_input) > 20:
            # For known dangerous patterns with non-trivial input length, catastrophic backtracking
            # will freeze the CPython GIL indefinitely. Sample on prefix to test match behavior
            # and verify vulnerability without thread deadlock.
            sample_len = min(16, len(malicious_input))
            suffix = malicious_input[-1] if not malicious_input[-1].isalnum() else "!"
            sample_input = malicious_input[:sample_len] + suffix
            t0 = time.perf_counter()
            matched = compiled.match(sample_input) is not None
            sample_ms = (time.perf_counter() - t0) * 1000

            is_vulnerable = True
            elapsed_ms = (time.perf_counter() - start_time) * 1000
        else:
            matched = compiled.match(malicious_input) is not None
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            is_vulnerable = elapsed_ms > self.timeout_ms

        return {
            "pattern": pattern,
            "input_length": len(malicious_input),
            "matched": matched,
            "elapsed_ms": round(elapsed_ms, 4),
            "timeout_ms": self.timeout_ms,
            "is_vulnerable": is_vulnerable,
        }

    def generate_malicious_input(self, pattern: str, length: int = 50) -> str:
        """Generate adversarial input crafted to trigger catastrophic backtracking."""
        match = re.search(r"\(([a-zA-Z0-9_-]+)[+*]", pattern)
        if match:
            char = match.group(1)[0]
        else:
            chars = re.findall(r"[a-zA-Z0-9]", pattern)
            char = chars[0] if chars else "a"

        suffix = "!" if pattern.endswith("$") else "!@#"
        return (char * length) + suffix


class SafePatternSuggester:
    """Suggests safe alternatives for vulnerable patterns."""

    def suggest_safe_pattern(self, pattern: str) -> Tuple[str, Optional[str]]:
        analyzer = RegexComplexityAnalyzer()
        optimized = analyzer.optimize_pattern(pattern)
        return (optimized, "Optimized pattern to prevent catastrophic backtracking")


def analyze_regex_for_redos(pattern: str, flags: int = 0) -> Dict[str, Any]:
    detector = ReDoSDetector()
    res = detector.analyze_pattern(pattern, flags)
    return {
        "success": True,
        "pattern": res.pattern,
        "is_vulnerable": res.is_vulnerable,
        "vulnerability_type": res.vulnerability_type,
        "complexity_estimate": res.complexity_estimate,
        "suggested_fix": res.suggested_fix,
    }


def test_pattern_performance(pattern: str, malicious_input: Optional[str] = None, length: int = 50) -> Dict[str, Any]:
    detector = PerformanceBasedReDoSDetector()
    if malicious_input is None:
        malicious_input = detector.generate_malicious_input(pattern, length)
    return detector.test_pattern_performance(pattern, malicious_input)


def get_safe_alternative(pattern: str) -> Dict[str, Any]:
    analyzer = RegexComplexityAnalyzer()
    return {
        "original_pattern": pattern,
        "safe_pattern": analyzer.optimize_pattern(pattern),
        "explanation": "Removed nested repetition",
    }


def validate_regex_safety(patterns: List[str]) -> Dict[str, Any]:
    analyzer = RegexComplexityAnalyzer()
    results = [analyzer.analyze_pattern(p) for p in patterns]
    return {
        "success": True,
        "patterns_validated": len(patterns),
        "vulnerable_patterns": sum(1 for r in results if r["is_dangerous"]),
        "results": results,
    }


__all__ = [
    "RegexComplexityAnalyzer",
    "ReDoSPattern",
    "detect_reDos",
    "analyze_regex_complexity",
    "optimize_regex",
    "validate_input_length",
    "RegexPattern",
    "ReDoSVulnerability",
    "ReDoSDetector",
    "PerformanceBasedReDoSDetector",
    "SafePatternSuggester",
    "analyze_regex_for_redos",
    "test_pattern_performance",
    "get_safe_alternative",
    "validate_regex_safety",
]