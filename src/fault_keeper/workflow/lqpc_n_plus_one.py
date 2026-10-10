"""LQPC: Little Query Pattern Compiler for N+1 Database Query Detection.

Analyzes and fuses N+1 database queries using Polyhedral Compilation Model.

Core functionality:
- Detect N+1 query patterns in ORM code
- Build polyhedral representation of query execution
- Optimize query fusion and batching
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Data Structures for Query Analysis
# ---------------------------------------------------------------------------

@dataclass
class QueryAccess:
    """Represents a database query access point."""
    location: str  # File:line
    query_type: str  # "SELECT", "INSERT", "UPDATE", "DELETE"
    model: str  # ORM model name (e.g., "User", "Order")
    context: str = ""  # Function or method context

    def to_dict(self) -> Dict[str, Any]:
        return {
            "location": self.location,
            "query_type": self.query_type,
            "model": self.model,
            "context": self.context,
        }


@dataclass
class QueryPattern:
    """Represents a SQL query pattern with parameters."""

    query: str
    params: List[Any] = field(default_factory=list)
    query_type: str = "SELECT"
    table: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "params": self.params,
            "query_type": self.query_type,
            "table": self.table,
        }


@dataclass
class NPlusOnePattern:
    """Represents an N+1 query pattern."""
    model: str
    location: List[str]  # List of locations where queries occur
    loop_context: Optional[str] = None  # Loop variable or context
    estimated_queries: int = 0  # Estimated N value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "location": self.location,
            "loop_context": self.loop_context,
            "estimated_queries": self.estimated_queries,
        }


@dataclass
class Polyhedron:
    """Represents a polyhedral representation of query fusion."""
    name: str
    dimension: int
    vertices: List[Tuple[float, float, float]]
    constraints: List[str]
    optimization: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "dimension": self.dimension,
            "vertices": [list(v) for v in self.vertices],
            "constraints": self.constraints,
            "optimization": self.optimization,
        }


@dataclass
class OptimizationResult:
    """Represents query optimization result."""
    model: str
    original_queries: int
    optimized_queries: int
    strategy: str
    improvement: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "original_queries": self.original_queries,
            "optimized_queries": self.optimized_queries,
            "strategy": self.strategy,
            "improvement": round(self.improvement, 4),
        }


# ---------------------------------------------------------------------------
# N+1 Query Detector
# ---------------------------------------------------------------------------

class NPlusOneQueryDetector:
    """Detects N+1 query patterns in ORM code.

    This class analyzes Python source code to detect N+1 query patterns
    commonly found in SQLAlchemy, Django ORM, and similar databases.

    Detection strategy:
    1. Parse AST to find loop constructs (for loops, list comprehensions)
    2. Identify ORM model references inside loops
    3. Detect direct query calls (query(), get(), filter(), etc.)
    4. Build polyhedral representation for optimization
    """

    def __init__(self) -> None:
        """Initialize N+1 query detector."""
        self.query_patterns: List[NPlusOnePattern] = []
        self.polyhedrons: Dict[str, Polyhedron] = {}
        self.optimizations: List[OptimizationResult] = []

    def analyze(self, source_code: str) -> Dict[str, Any]:
        """Analyze source code for N+1 query patterns.

        Args:
            source_code: Python source code as string.

        Returns:
            Dictionary with analysis results.
        """
        self.query_patterns = []
        self.polyhedrons = {}
        self.optimizations = []

        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return {
                "success": False,
                "error": "Invalid Python syntax",
            }

        # Detect N+1 patterns
        patterns = self._detect_patterns(tree)

        # Build polyhedral representation
        polyhedrons = self._build_polyhedron(patterns)

        # Generate optimizations
        optimizations = self._optimize_queries(patterns)

        return {
            "success": True,
            "n_plus_one_patterns": [p.to_dict() for p in patterns],
            "polyhedrons": {k: v.to_dict() for k, v in polyhedrons.items()},
            "optimizations": [o.to_dict() for o in optimizations],
            "summary": {
                "n_patterns_detected": len(patterns),
                "models_affected": list(set(p.model for p in patterns)),
                "total_optimizations": len(optimizations),
            },
        }

    def detect(self, queries: Any) -> Dict[str, Any]:
        """Detect N+1 patterns from a list of SQL queries or source code.

        Args:
            queries: List of SQL strings, QueryPattern instances, dicts, or source code.

        Returns:
            Dictionary containing detected patterns, polyhedrons, optimizations, and summary.
        """
        if isinstance(queries, str):
            try:
                ast.parse(queries)
                return self.analyze(queries)
            except SyntaxError:
                query_list = [queries]
        else:
            query_list = list(queries)

        if not query_list:
            return {
                "success": True,
                "n_plus_one_patterns": [],
                "polyhedrons": {},
                "optimizations": [],
                "summary": {
                    "n_patterns_detected": 0,
                    "models_affected": [],
                    "total_optimizations": 0,
                },
            }

        patterns: List[NPlusOnePattern] = []
        template_counts: Dict[str, List[str]] = defaultdict(list)

        for q in query_list:
            raw_sql = q.query if isinstance(q, QueryPattern) else (q.get("query", "") if isinstance(q, dict) else str(q))
            canonical = re.sub(r"\s+", " ", raw_sql.strip())
            canonical_template = re.sub(r"=\s*(\?|\$|\d+|'[^']*')", "= ?", canonical)
            template_counts[canonical_template].append(raw_sql)

        for template, raw_queries in template_counts.items():
            match = re.search(r"FROM\s+([a-zA-Z0-9_]+)", template, re.IGNORECASE)
            model_name = match.group(1) if match else "Model"
            if len(raw_queries) >= 2 or ("WHERE" in template.upper() and len(query_list) > 1):
                patterns.append(NPlusOnePattern(
                    model=model_name,
                    location=[f"query:{i}" for i in range(len(raw_queries))],
                    loop_context="batch_sequence",
                    estimated_queries=len(raw_queries),
                ))

        polyhedrons = self._build_polyhedron(patterns)
        optimizations = self._optimize_queries(patterns)

        return {
            "success": True,
            "n_plus_one_patterns": [p.to_dict() for p in patterns],
            "polyhedrons": {k: v.to_dict() for k, v in polyhedrons.items()},
            "optimizations": [o.to_dict() for o in optimizations],
            "summary": {
                "n_patterns_detected": len(patterns),
                "models_affected": list(set(p.model for p in patterns)),
                "total_optimizations": len(optimizations),
            },
        }

    def _detect_patterns(self, tree: ast.AST) -> List[NPlusOnePattern]:
        """Detect N+1 query patterns in AST.

        Args:
            tree: Parsed AST tree.

        Returns:
            List of detected N+1 patterns.
        """
        patterns: List[NPlusOnePattern] = []
        loop_nodes: Dict[str, List[ast.AST]] = defaultdict(list)
        query_locations: Dict[str, Set[str]] = defaultdict(set)

        # Find all loops
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.AsyncFor)):
                loop_var = ""
                if isinstance(node.target, ast.Name):
                    loop_var = node.target.id
                elif isinstance(node.target, ast.Tuple):
                    loop_var = ", ".join(t.id for t in node.target.elts if isinstance(t, ast.Name))

                # Find query calls inside loop
                for child in ast.walk(node):
                    if self._is_query_call(child):
                        func_name = ""
                        if isinstance(child.func, ast.Attribute):
                            func_name = child.func.attr
                        elif isinstance(child.func, ast.Name):
                            func_name = child.func.id

                        query_locations[loop_var or "unknown"].add(func_name)

        # Create patterns for each model with queries in loops
        for loop_var, funcs in query_locations.items():
            for func in funcs:
                if func in ("query", "get", "filter", "first", "all", "values"):
                    pattern = NPlusOnePattern(
                        model=f"Model_{loop_var}",
                        location=[f"{loop_var}:{func}"],
                        loop_context=loop_var,
                        estimated_queries=10,  # Estimate N=10
                    )
                    patterns.append(pattern)

        return patterns

    def _is_query_call(self, node: ast.AST) -> bool:
        """Check if node is a query call.

        Args:
            node: AST node to check.

        Returns:
            True if node is a query call.
        """
        if not isinstance(node, ast.Call):
            return False

        func_name = ""
        if isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            func_name = node.func.id

        query_keywords = ("query", "get", "filter", "first", "all", "values", 
                         "select", "insert", "update", "delete")
        return func_name.lower() in query_keywords

    def _build_polyhedron(
        self,
        patterns: List[NPlusOnePattern],
    ) -> Dict[str, Polyhedron]:
        """Build polyhedral representation for query fusion.

        Args:
            patterns: List of detected N+1 patterns.

        Returns:
            Dictionary mapping model names to polyhedrons.
        """
        polyhedrons: Dict[str, Polyhedron] = {}

        for pattern in patterns:
            # Create vertices based on estimated queries
            n = pattern.estimated_queries
            vertices = [
                (0.0, 0.0, 0.0),  # Origin
                (1.0, 0.0, 0.0),  # X axis
                (0.0, 1.0, 0.0),  # Y axis
                (1.0 / n, 1.0 / n, 0.0),  # Fusion point
            ]

            polyhedron = Polyhedron(
                name=f"fusion_{pattern.model}",
                dimension=3,
                vertices=vertices,
                constraints=[
                    f"x >= 0",
                    f"y >= 0",
                    f"x + y <= {2.0 / n}",
                    f"z = 0",
                ],
                optimization="eager_loading",
            )
            polyhedrons[pattern.model] = polyhedron

        return polyhedrons

    def _optimize_queries(
        self,
        patterns: List[NPlusOnePattern],
    ) -> List[OptimizationResult]:
        """Generate query fusion optimizations.

        Args:
            patterns: List of detected N+1 patterns.

        Returns:
            List of optimization results.
        """
        optimizations: List[OptimizationResult] = []

        for pattern in patterns:
            n = pattern.estimated_queries
            improvement = 1 - (1 / n) if n > 1 else 0.0

            optimization = OptimizationResult(
                model=pattern.model,
                original_queries=n,
                optimized_queries=1,
                strategy="eager_loading",
                improvement=improvement,
            )
            optimizations.append(optimization)

        return optimizations


# ---------------------------------------------------------------------------
# Public API Functions
# ---------------------------------------------------------------------------

def detect_n_plus_one(source_or_queries: Any) -> Optional[Dict[str, Any]]:
    """Detect N+1 query patterns in Python source code or list of SQL queries.

    Args:
        source_or_queries: Python source code string, or list of SQL queries / QueryPatterns.

    Returns:
        Analysis result dictionary or None if analysis fails.
    """
    detector = NPlusOneQueryDetector()
    if isinstance(source_or_queries, list):
        return detector.detect(source_or_queries)
    if isinstance(source_or_queries, str):
        try:
            ast.parse(source_or_queries)
            return detector.analyze(source_or_queries)
        except SyntaxError:
            return detector.detect([source_or_queries])
    return detector.detect([])


def generate_query_fusion_plan(
    source: str,
) -> Optional[Dict[str, Any]]:
    """Generate query fusion plan for optimized execution.

    Args:
        source: Source code as string.

    Returns:
        Query fusion plan or None if analysis fails.
    """
    result = detect_n_plus_one(source)

    if not result.get("success"):
        return None

    # Generate fusion plan
    fusion_plan = {
        "models": [],
        "fusion_strategy": "eager_loading" if result["summary"]["n_patterns_detected"] > 0 else "none",
        "estimated_improvement": 0.0,
    }

    for pattern in result["n_plus_one_patterns"]:
        model = pattern.model
        fusion_plan["models"].append({
            "model": model,
            "current_queries": pattern.estimated_queries,
            "optimized_queries": 1,
            "improvement": round(1 - 1/pattern.estimated_queries, 4) if pattern.estimated_queries > 1 else 0.0,
        })

    total_improvement = sum(m["improvement"] for m in fusion_plan["models"])
    fusion_plan["estimated_improvement"] = round(total_improvement, 4)

    return fusion_plan


__all__ = [
    "QueryAccess",
    "QueryPattern",
    "NPlusOnePattern",
    "Polyhedron",
    "OptimizationResult",
    "NPlusOneQueryDetector",
    "detect_n_plus_one",
    "generate_query_fusion_plan",
]
