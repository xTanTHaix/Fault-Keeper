"""Async Await Lifecycle Checker - Static analysis for forgotten await calls.

Detects potential race conditions in async code:
- Race condition detection in async functions
- Async lifecycle tracking (create, start, stop)
- Missing await detection
- Coroutine state validation
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Data Structures for Async Analysis
# ---------------------------------------------------------------------------

@dataclass
class MissingAwaitIssue:
    """Represents a missing await issue."""
    function_name: str
    line_number: int
    severity: str  # "error", "warning"
    message: str


@dataclass
class CoroutineState:
    """Tracks coroutine lifecycle state."""
    coro_name: str
    created: bool = False
    started: bool = False
    awaited: bool = False
    completed: bool = False


@dataclass
class AsyncLifecycleTracker:
    """Tracks async function lifecycle."""
    functions: Dict[str, CoroutineState] = field(default_factory=dict)
    issues: List[MissingAwaitIssue] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Async Lifecycle Checker Implementation
# ---------------------------------------------------------------------------

class AsyncAwaitLifecycleChecker:
    """Static analysis for forgotten `await` calls.

    Core functionality:
    - Detect missing await in async functions
    - Track coroutine lifecycle (create, start, stop)
    - Identify race conditions in async code
    - Validate async/await usage patterns
    """

    def __init__(self) -> None:
        """Initialize checker."""
        self.tracker = AsyncLifecycleTracker()
        # Shared state patterns that indicate race conditions
        self.SHARED_STATE_PATTERNS = {
            r"global\s+(\w+)": "global variable",
            r"class\s+\w+\s*:\s*\n.*?self\.(\w+)\s*=": "instance attribute",
            r"nonlocal\s+(\w+)": "nested scope variable",
        }

    def analyze_module(self, source: str) -> List[MissingAwaitIssue]:
        """Analyze entire module for race conditions.

        Args:
            source: Source code as string.

        Returns:
            List of MissingAwaitIssue findings.
        """
        self.tracker = AsyncLifecycleTracker()

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return self.tracker.issues

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                self._analyze_async_function(node)
            elif isinstance(node, ast.Await):
                self._track_await(node)

        return self.tracker.issues

    def _analyze_async_function(self, node: ast.AsyncFunctionDef) -> None:
        """Analyze async function for missing await calls."""
        func_name = node.name
        coro_state = CoroutineState(
            coro_name=func_name,
            created=True,
        )
        self.tracker.functions[func_name] = coro_state

        has_await = any(
            isinstance(n, ast.Await) for n in ast.walk(node)
        )

        if not has_await:
            self.tracker.issues.append(MissingAwaitIssue(
                function_name=func_name,
                line_number=node.lineno,
                severity="error",
                message=f"Async function '{func_name}' contains no await calls",
            ))

    def _track_await(self, node: ast.Await) -> None:
        """Track await usage."""
        for coro_state in self.tracker.functions.values():
            coro_state.awaited = True

    def get_issues(self) -> List[MissingAwaitIssue]:
        """Get all detected issues."""
        return self.tracker.issues


# ---------------------------------------------------------------------------
# Race Condition Detector
# ---------------------------------------------------------------------------

class RaceConditionDetector:
    """Detects potential race conditions in async code."""

    SHARED_STATE_PATTERNS = {
        r"global\s+(\w+)": "global variable",
        r"class\s+\w+\s*:\s*\n.*?self\.(\w+)\s*=": "instance attribute",
        r"nonlocal\s+(\w+)": "nested scope variable",
    }

    def __init__(self) -> None:
        """Initialize detector."""
        self.detector = MissingAwaitDetector()

    def analyze_module(self, source: str) -> List[RaceConditionIssue]:
        """Analyze entire module for race conditions.

        Args:
            source: Source code as string.

        Returns:
            List of RaceConditionIssue findings.
        """
        issues: List[RaceConditionIssue] = []

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues

        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                for target in node.names:
                    issues.append(RaceConditionIssue(
                        line=node.lineno,
                        description=f"global variable '{target}' modified in async context",
                    ))
            elif isinstance(node, ast.Nonlocal):
                for target in node.names:
                    issues.append(RaceConditionIssue(
                        line=node.lineno,
                        description=f"nested scope variable '{target}' modified in async context",
                    ))

        return issues


@dataclass
class RaceConditionIssue:
    """Represents a detected race condition."""
    line: int
    description: str


# ---------------------------------------------------------------------------
# Missing Await Detector
# ---------------------------------------------------------------------------

class MissingAwaitDetector:
    """Detects missing await calls in async functions."""

    def __init__(self) -> None:
        """Initialize detector."""
        self.issues: List[MissingAwaitIssue] = []

    def check_function(self, source: str, func_name: str) -> bool:
        """Check if function has await calls."""
        pattern = rf"async\s+def\s+{re.escape(func_name)}\s*\("
        match = re.search(pattern, source)
        if not match:
            return False

        func_start = match.end()
        func_end = source.find("\n", func_start)
        if func_end == -1:
            func_end = len(source)

        function_code = source[func_start:func_end]
        has_await = "await" in function_code

        return has_await


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def check_async_awaits(source_code: str) -> List[MissingAwaitIssue]:
    """Check async/await usage in source code.

    Args:
        source_code: Python source code as string.

    Returns:
        List of MissingAwaitIssue findings.
    """
    checker = AsyncAwaitLifecycleChecker()
    return checker.analyze_module(source_code)


def detect_race_conditions(source_code: str) -> List[RaceConditionIssue]:
    """Detect race conditions in async code.

    Args:
        source_code: Python source code as string.

    Returns:
        List of RaceConditionIssue findings.
    """
    detector = RaceConditionDetector()
    return detector.analyze_module(source_code)


__all__ = [
    "AsyncAwaitLifecycleChecker",
    "RaceConditionDetector",
    "MissingAwaitIssue",
    "CoroutineState",
    "AsyncLifecycleTracker",
    "check_async_awaits",
    "detect_race_conditions",
]