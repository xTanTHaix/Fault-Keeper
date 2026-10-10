"""TC-GTC: Timezone/GTC Trap Detector.

Detects common timezone-related bugs in Python source code:
- ``YYYY`` vs ``yyyy`` format string confusion (common when porting from Java)
- DST transition edge cases (non-existent or ambiguous local times)
- Mixing naive and aware datetime objects without explicit conversion
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TrapFinding:
    """A single detected timezone/format trap."""
    lineno: int
    col_offset: int
    category: str  # "format_string", "dst_edge_case", "naive_aware_mix"
    message: str
    severity: str  # "error", "warning"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lineno": self.lineno,
            "col_offset": self.col_offset,
            "category": self.category,
            "message": self.message,
            "severity": self.severity,
        }


# Patterns for common format-string traps
_YYYY_PATTERN = re.compile(r"%[Y]{2,}")       # %YY or more → likely wrong (should be %y for 2-digit year)
_yyyy_pattern = re.compile(r"'yyyy'|\"yyyy\"") # Java-style lowercase yyyy literal in string


def _detect_format_string_traps(tree: ast.Module) -> List[TrapFinding]:
    """Detect YYYY/yyyy format confusion and invalid strftime directives."""
    findings: List[TrapFinding] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.Constant,)):
            if not isinstance(node.value, str):
                continue
            s = node.value
            lineno = getattr(node, "lineno", 0)
            col = getattr(node, "col_offset", 0)

            # Check for Java-style yyyy literal that might be intended as format code
            if _yyyy_pattern.search(s):
                findings.append(TrapFinding(
                    lineno=lineno,
                    col_offset=col,
                    category="format_string",
                    message=(
                        f"Java-style 'yyyy' found in string at line {lineno}. "
                        f"Python strftime uses '%Y' for 4-digit year. "
                        f"If this is a literal pattern (e.g., ISO date example), "
                        f"consider quoting or escaping to avoid confusion."
                    ),
                    severity="warning",
                ))

            # Check for %YY patterns that suggest wrong year format usage
            if _YYYY_PATTERN.search(s):
                findings.append(TrapFinding(
                    lineno=lineno,
                    col_offset=col,
                    category="format_string",
                    message=(
                        f"Invalid or ambiguous strftime directive '%Y...' at line {lineno}. "
                        f"Python supports %y (2-digit year) and %Y (4-digit year). "
                        f"Ensure the format string matches Python's datetime.strftime spec."
                    ),
                    severity="error",
                ))

        elif isinstance(node, ast.Call):
            # Check strftime() calls for suspicious patterns
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "strftime":
                if node.args:
                    fmt_arg = node.args[0]
                    if isinstance(fmt_arg, ast.Constant) and isinstance(fmt_arg.value, str):
                        lineno = getattr(node, "lineno", 0)
                        col = getattr(node, "col_offset", 0)
                        # Look for %YY or similar in strftime format strings
                        if _YYYY_PATTERN.search(fmt_arg.value):
                            findings.append(TrapFinding(
                                lineno=lineno,
                                col_offset=col,
                                category="format_string",
                                message=(
                                    f"Invalid strftime directive at line {lineno}. "
                                    f"Use '%Y' for 4-digit year or '%y' for 2-digit year."
                                ),
                                severity="error",
                            ))

    return findings


def _detect_naive_aware_mixing(tree: ast.Module) -> List[TrapFinding]:
    """Detect mixing of naive and aware datetime objects without explicit conversion."""
    findings: List[TrapFinding] = []

    # Track variable names assigned from timezone-aware or naive sources
    aware_vars: set = set()
    naive_vars: set = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            # Detect assignments involving datetime constructors
            value = node.value
            is_aware_call = False
            is_naive_call = False

            if isinstance(value, ast.Call):
                func = value.func
                # aware: datetime.now(timezone=...), datetime.utcnow(), .replace(tzinfo=...)
                if (isinstance(func, ast.Attribute) and
                        func.attr in ("now", "utcnow")) or \
                   (isinstance(func, ast.Attribute) and func.attr == "replace" and
                    any(kw.arg == "tzinfo" for kw in value.keywords)):
                    is_aware_call = True
                # naive: datetime.now() without tzinfo arg (bare call to .now())
                elif isinstance(func, ast.Attribute) and func.attr == "now":
                    has_tz = any(kw.arg == "tzinfo" for kw in value.keywords)
                    if not has_tz:
                        is_naive_call = True

            if is_aware_call or is_naive_call:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        if is_aware_call:
                            aware_vars.add(var_name)
                        elif is_naive_call:
                            naive_vars.add(var_name)

        elif isinstance(node, ast.BinOp):
            # Detect arithmetic between potentially mixed variables
            for varname in aware_vars & naive_vars:
                pass  # Handled via usage analysis below

    # Check for operations between known-aware and known-naive variables
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) or isinstance(node, ast.Compare):
            for child in ast.walk(node):
                if isinstance(child, ast.Name) and child.id in aware_vars:
                    # Check if a naive variable is used in the same expression
                    expr_vars = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
                    mixed = expr_vars & naive_vars
                    if mixed:
                        findings.append(TrapFinding(
                            lineno=getattr(node, "lineno", 0),
                            col_offset=getattr(node, "col_offset", 0),
                            category="naive_aware_mix",
                            message=(
                                f"Possible mixing of aware and naive datetime objects at line "
                                f"{getattr(node, 'lineno', '?')}. Variables {mixed & aware_vars} "
                                f"(aware) used alongside {mixed - aware_vars} (naive)."
                            ),
                            severity="error",
                        ))

    return findings


def _detect_dst_edge_cases(tree: ast.Module) -> List[TrapFinding]:
    """Detect code patterns vulnerable to DST transition bugs."""
    findings: List[TrapFinding] = []

    # Patterns that indicate potential DST issues:
    # 1. Adding/subtracting timedeltas across known DST boundaries without tzinfo
    # 2. Using date arithmetic on naive datetimes in contexts suggesting timezone handling
    dst_keywords = {"dst", "daylight", "tzname", "utcoffset", "fold"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # detect .astimezone() or .replace(tzinfo=...) near timedelta operations
            if isinstance(func, ast.Attribute) and func.attr == "astimezone":
                lineno = getattr(node, "lineno", 0)
                findings.append(TrapFinding(
                    lineno=lineno,
                    col_offset=getattr(node, "col_offset", 0),
                    category="dst_edge_case",
                    message=(
                        f"astimezone() call at line {lineno}. Ensure the source datetime's "
                        f"timezone is explicitly set before conversion to avoid DST ambiguity."
                    ),
                    severity="warning",
                ))

        elif isinstance(node, ast.Attribute) and node.attr in dst_keywords:
            # Accessing .dst(), .fold etc. on a potentially naive object
            lineno = getattr(node, "lineno", 0)
            findings.append(TrapFinding(
                lineno=lineno,
                col_offset=getattr(node, "col_offset", 0),
                category="dst_edge_case",
                message=(
                    f"Accessing '{node.attr}' at line {lineno}. Verify the object has a "
                    f"tzinfo set; accessing these on naive datetimes returns None/undefined."
                ),
                severity="warning",
            ))

    return findings


def detect_traps(source: str) -> Dict[str, Any]:
    """Analyse Python source for timezone and format traps.

    Args:
        source: Raw Python source code string.

    Returns:
        Dict with keys ``findings`` (list of TrapFinding dicts), grouped by category,
        and summary counts per severity level.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {
            "findings": [],
            "error": f"Source syntax error: {e}",
            "summary": {"total": 0, "errors": 0, "warnings": 0},
        }

    format_findings = _detect_format_string_traps(tree)
    mixing_findings = _detect_naive_aware_mixing(tree)
    dst_findings = _detect_dst_edge_cases(tree)

    all_findings = format_findings + mixing_findings + dst_findings

    by_category: Dict[str, List[Dict[str, Any]]] = {
        "format_string": [f.to_dict() for f in format_findings],
        "naive_aware_mix": [f.to_dict() for f in mixing_findings],
        "dst_edge_case": [f.to_dict() for f in dst_findings],
    }

    n_errors = sum(1 for f in all_findings if f.severity == "error")
    n_warnings = sum(1 for f in all_findings if f.severity == "warning")

    return {
        "findings": [f.to_dict() for f in all_findings],
        "by_category": by_category,
        "summary": {
            "total": len(all_findings),
            "errors": n_errors,
            "warnings": n_warnings,
        },
    }
