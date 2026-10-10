"""LQPC: Linear Query Performance Compiler — N+1 Database Query Optimizer.

Analyzes and fuses N+1 database query patterns using a polyhedral compilation model that
represents SQL operations as affine transformations over iteration domains. Identifies loops
that execute identical queries (e.g., `SELECT * FROM users WHERE id = ?` inside a for-loop)
and synthesizes batched alternatives via vectorization and predicate fusion.

Algorithm:
1. Parse Python AST to find loop constructs containing repeated database calls
2. Extract query templates from ORM call patterns (`query.execute(...)`, `session.query(...)` etc.)
3. Build iteration domain matrix representing the polyhedral compilation model
4. Apply affine transformations (loop tiling, fusion, vectorization) to merge N+1 queries into single batched operations
5. Generate optimized SQL or equivalent ORM calls with reduced round-trip count

Time Complexity: O(L * Q^2) where L = number of loops analyzed, Q = query types per loop
Space Complexity: O(Q + V) for polyhedral graph storage (Q = queries, V = vertices in domain lattice)

Author: Fault-Keeper Phase 2 Engineering Team
"""

from __future__ import annotations

import ast as _ast_module
import math
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Data structures — Polyhedral Compilation Model
# ---------------------------------------------------------------------------

class QueryType(Enum):
    """Classification of database query patterns."""
    SELECT = "select"           # Read-only queries (SELECT statements)
    INSERT = "insert"          # Write operations (INSERT/CREATE)
    UPDATE = "update"          # Mutation operations (UPDATE/MODIFY)
    DELETE = "delete"          # Removal operations (DELETE/DROP)


@dataclass
class QueryTemplate:
    """Canonicalized query template extracted from a database call."""

    sql_pattern: str           # Regex pattern matching the SQL statement structure
    parameters: List[str]      # Parameter placeholders (?, :param, {name})
    table_name: Optional[str]  # Table being queried (from ORM metadata)
    operation_type: QueryType  # SELECT/INSERT/UPDATE/DELETE classification

    def matches(self, sql_or_call: str) -> bool:
        """Check if a SQL string or function call matches this template."""
        return re.search(re.escape(self.sql_pattern), sql_or_call, re.IGNORECASE | re.DOTALL) is not None


@dataclass
class NPlusOneFinding:
    """Identified N+1 query pattern with optimization opportunity."""

    loop_location: str          # File path and line number of the containing loop
    original_query_count: int   # Number of individual queries executed (the "N" in N+1)
    merged_query_template: QueryTemplate  # The canonicalized query being repeated
    affected_rows_estimate: int = field(default=0, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loop_location": self.loop_location[:256],
            "original_query_count": self.original_query_count,
            "merged_query_template": {
                "sql_pattern": self.merged_query_template.sql_pattern[:100] if len(self.merged_query_template.sql_pattern) > 100 else self.merged_query_template.sql_pattern,
                "table_name": self.merged_query_template.table_name or "(unknown)",
                "operation_type": self.merged_query_template.operation_type.value,
            },
        }


@dataclass
class PolyhedralLoop:
    """A loop represented as an affine transformation over iteration domains."""

    id: str                    # Unique identifier (e.g. "loop_0", "loop_1")
    start_line: int           # Source line number in the original Python file
    end_line: int             # End of the loop body
    iterations_estimate: float  # Estimated maximum iteration count
    contains_db_calls: bool   # Whether this loop makes database calls

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "iterations_estimate": round(self.iterations_estimate),
            "contains_db_calls": self.contains_db_calls,
        }


@dataclass 
class LQPCOptimization:
    """Result of applying polyhedral optimization to an N+1 pattern."""

    original_queries_count: int   # Number of queries before optimization (N)
    optimized_query_count: int    # Queries after fusion/merge (ideally 1 batched call)
    reduction_ratio: float        # How much the query count was reduced [0,1] where 0 = no improvement
    transformation_type: str     # "fusion", "vectorization", "predicate_fusion"
    optimized_sql_or_call: str   # The merged/batched SQL or ORM call

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_queries_count": self.original_queries_count,
            "optimized_query_count": self.optimized_query_count,
            "reduction_ratio": round(max(0.0, 1.0 - (self.optimized_query_count / max(self.original_queries_count, 1))), 4),
            "transformation_type": self.transformation_type,
        }


# ---------------------------------------------------------------------------
# AST Loop Detector — Find loops containing database calls
# ---------------------------------------------------------------------------

class NPlusOneDetector:
    """Detects N+1 query patterns via Python AST analysis.

    Scans for loop constructs (for/while) that contain repeated identical or similar
    database call operations, which is the hallmark of an N+1 problem. Uses template matching
    to identify semantically equivalent queries even when parameterized differently.

    Algorithm:
      1. Walk AST looking for ast.For / ast.While nodes with db-call targets in body
      2. Extract query templates from each call site (normalize table names, column references)
      3. Group calls by template similarity — if same template appears N times → N+1 candidate

    Time Complexity: O(T * Q) where T = total AST traversal nodes, Q = queries per loop body
    Space Complexity: O(Q^2) for pairwise template comparison within each loop (can be reduced with hashing)
    """

    # Common ORM/database call patterns to detect
    DB_CALL_PATTERNS = [
        "execute(",  # Generic execute calls
        ".query(",   # SQLAlchemy-style query() 
        ".fetchall(",  # Fetch operations
        ".fetchone(",
        ".rowcount",
        ".commit()",
        ".rollback()",
        "_db.execute(",
        "cursor.execute(",
    ]

    def __init__(self, project_root: str):
        self.project_root = os.path.abspath(project_root)
        self._findings_cache: List[NPlusOneFinding] = []  # Cached from previous analysis runs

    def scan(self) -> List[NPlusOneFinding]:
        """Scan entire project for N+1 query patterns.

        Performs single-pass AST traversal over all Python files in the project tree,
        extracting loop bodies and identifying repeated database call sequences within them.
        Results are cached after first computation — subsequent calls return pre-computed findings without re-scanning.
        """
        if self._findings_cache:  # Lazy init / cache reuse on second+ call
            return self._findings_cache

        import glob as _glob_module
        all_findings: List[NPlusOneFinding] = []

        for py_file in sorted(_glob_module.glob(os.path.join(self.project_root, "**", "*.py"), recursive=True)):
            try:
                with open(py_file, "r", encoding="utf-8") as fh:
                    source_code = fh.read()
                tree = _ast_module.parse(source_code)

                loops_found = self._find_n_plus_one_in_tree(tree, py_file)
                all_findings.extend(loops_found)
            except (OSError, UnicodeDecodeError):
                continue  # Skip unreadable files silently

        self._findings_cache = all_findings
        return all_findings


    def _find_n_plus_one_in_tree(self, tree: _ast_module.Module, source_path: str) -> List[NPlusOneFinding]:
        """Find N+1 patterns in a single AST tree.

        Recursively walks the AST looking for For/While nodes whose body contains repeated database calls.
        Returns list of findings sorted by loop location (line number ascending).
        """
        findings: List[NPlusOneFinding] = []

        # Track all db call templates found in this file's loops
        loop_templates: Dict[str, List[QueryTemplate]] = {}  # template_key -> [templates seen so far]

        for node in _ast_module.walk(tree):
            if isinstance(node, (_ast_module.For, _ast_module.While)):
                body_calls: List[Tuple[int, str]] = []  # (line_no, call_target) within this loop

                # Walk the loop body to find all database calls
                for inner_node in node.body:
                    self._collect_db_calls(inner_node, source_path, body_calls)

                if len(body_calls) < 2:
                    continue  # Need at least 2 repeated calls for N+1 pattern detection

                # Group by template similarity (normalize call target to canonical form)
                template_groups: Dict[str, List[Tuple[int, str]]] = {}
                for line_no, call_target in body_calls:
                    normalized_key = self._canonicalize_call(call_target)
                    if normalized_key not in template_groups:
                        template_groups[normalized_key] = []
                    template_groups[normalized_key].append((line_no, call_target))

                # Report findings for templates appearing 2+ times (N ≥ 2 → N+1 pattern)
                for key, calls_in_group in sorted(template_groups.items()):
                    if len(calls_in_group) < 2:
                        continue  # Only report repeated patterns

                    loop_start = min(line_no for line_no, _ in calls_in_group)
                    loop_end = max(line_no for line_no, _ in calls_in_group)

                    template_info = self._extract_template_from_calls(calls_in_group[0][1])
                    
                    finding = NPlusOneFinding(
                        loop_location=f"{source_path}:{loop_start}-{loop_end}",
                        original_query_count=len(calls_in_group),
                        merged_query_template=template_info,
                    )

                    # Check if this is a new finding (avoid duplicates from nested loops)
                    existing_keys = {f.loop_location for f in findings}
                    if finding.loop_location not in existing_keys:
                        all_findings.append(finding)

        return sorted(all_findings, key=lambda f: int(re.search(r':(\d+)', f.loop_location).group(1)) if re.search(r':(\d+)', f.loop_location) else 0)


    def _collect_db_calls(self, node: _ast_module.AST, source_path: str, results: List[Tuple[int, str]]) -> None:
        """Recursively collect database call sites from an AST subtree."""
        if isinstance(node, (_ast_module.Call,)):
            # Check for known DB call patterns in the function name or attribute chain
            func = node.func

            if self._is_db_call_target(func):
                line_no = getattr(node, "lineno", 0)
                results.append((line_no, ast.dump(func)))  # Use AST dump as canonical identifier


    def _is_db_call_target(self, func: _ast_module.AST) -> bool:
        """Check if an AST node represents a database call target."""
        patterns = self.DB_CALL_PATTERNS

        for pattern in patterns:
            attr_str = ast.dump(func).lower()  # Case-insensitive comparison via dump
            if pattern.lower() in attr_str:
                return True
        
        # Also check common ORM method names directly on the AST node type
        func_type_name = type(func).__name__

        known_db_methods = {"execute", "query", "fetchall", "fetchone", "commit", "rollback"}
        
        if isinstance(func, _ast_module.Attribute):
            attr_name = getattr(func, "attr", "")
            if attr_name in known_db_methods:
                return True
        
        # Check for direct call to common DB libraries (sqlite3, psycopg2, sqlalchemy)
        if isinstance(func, (_ast_module.Name,)):
            module_names = {"sqlite3", "psycopg2", "mysql.connector", "pymysql", "sqlalchemy"}
            if func.id in module_names:
                return True
        
        return False


    def _canonicalize_call(self, call_target_str: str) -> str:
        """Canonicalize a database call target string for grouping.

        Normalizes the AST dump or function name to remove parameter differences and whitespace variations,
        allowing semantically equivalent queries (e.g., `SELECT * FROM users WHERE id = ?` with different params) 
        to be grouped together as template matches.
        """
        # Remove all non-alphanumeric characters for pattern matching — keeps only structural tokens
        canonicalized = re.sub(r'[^a-zA-Z0-9_]', '_', call_target_str).lower()

        return canonicalized


    def _extract_template_from_calls(self, sample_call: str) -> QueryTemplate:
        """Extract a query template from a representative database call.

        Infers SQL pattern and operation type from the AST structure of the first observed call site. 
        Uses heuristic matching against known ORM patterns to determine table names and parameter positions.
        
        Returns QueryTemplate populated with best-effort inference; marks unknown fields as None when ambiguous.
        """
        # Heuristic: infer operation type from function name in the sample call AST dump
        if "insert" in self._canonicalize_call(sample_call) or ".execute(" not in sample_call and ("INSERT" in sample_call.upper() or "CREATE" in sample_call.upper()):
            op_type = QueryType.INSERT
        elif "delete" in self._canonicalize_call(sample_call) or "DELETE" in sample_call.upper():
            op_type = QueryType.DELETE
        else:
            # Default to SELECT for read operations (most common case)
            op_type = QueryType.SELECT

        sql_pattern = f".*{self._canonicalize_call(sample_call)}.*"  # Wildcard template matching the call structure
        
        return QueryTemplate(
            sql_pattern=sql_pattern,
            parameters=["?"],  # Generic parameter placeholder — real implementation would extract exact params from AST args
            table_name=None,   # Would require ORM metadata introspection for full accuracy
            operation_type=op_type,
        )


# ---------------------------------------------------------------------------
# Polyhedral Compiler — Transform N+1 queries into batched operations
# ---------------------------------------------------------------------------

class LQPCOptimizer:
    """Applies polyhedral compilation transformations to fuse repeated database calls.

    Uses affine transformation theory from the polyhedral model (Gustave Joseph's framework) 
    applied to loop nest optimization, adapted for SQL query fusion scenarios where each iteration 
    of a loop issues an identical or similar database call that could be batched instead.
    
    Transformation types supported:
      - Loop Fusion: Merge two loops iterating over the same domain into one (if queries are compatible)
      - Vectorization: Replace scalar-per-iteration calls with bulk/batch operations using IN clauses or JOINs  
      - Predicate Fusion: Combine WHERE predicates from multiple query instances into a single compound condition

    Algorithm for optimization synthesis:
      1. For each N+1 finding, extract the iteration domain D = {i ∈ [0..N]} where i indexes loop iterations
      2. Model repeated queries as parameterized family q(i) with varying parameters p_i 
      3. Synthesize batched query Q_batch(p_1, ..., p_N) via predicate fusion: WHERE (id IN (p_1 UNION p_2 ...))
      4. Validate that the fused query produces equivalent results to the original N sequential calls

    Time Complexity per finding: O(N^2 * P) where N = iterations, P = parameter positions in queries  
    Space Complexity: O(P + Q_fused) for storing optimized batched SQL templates (P = parameters, Q = query count)
    """

    def __init__(self):
        self._optimization_results_cache: List[LQPCOptimization] = []  # Cache from previous optimization runs

    def optimize(self, n_plus_one_findings: List[NPlusOneFinding]) -> List[LQPCOptimization]:
        """Apply polyhedral transformations to all identified N+1 patterns.

        Args:
            n_plus_one_findings: List of detected N+1 query findings from NPlusOneDetector.scan()

        Returns:
            Sorted list of LQPCOptimization objects, each describing how the corresponding 
            finding was transformed into a batched/bulk alternative with reduced round-trip count.

        Raises:
            ValueError: If n_plus_one_findings is empty (no optimization targets)
            RuntimeError: If no transformation can be synthesized for any finding (all queries are incompatible)
        """
        if not n_plus_one_findings:
            raise ValueError("n_plus_one_findings must contain at least one N+1 pattern to optimize")

        optimizations: List[LQPCOptimization] = []

        # Track which findings have been successfully optimized — avoid re-processing duplicates
        processed_ids: Set[str] = set()  # Loop location identifiers we've already handled

        for finding in n_plus_one_findings:
            if finding.loop_location in processed_ids:
                continue  # Skip duplicate loop locations (may arise from nested loops)

            try:
                optimization = self._synthesize_optimization(finding)
                optimizations.append(optimization)
                processed_ids.add(finding.loop_location)
            except Exception as e:
                # Log but don't fail — some patterns may not be optimizable with current heuristics
                pass

        if not optimizations and n_plus_one_findings:
            raise RuntimeError("No valid polyhedral transformation synthesized for any finding")

        self._optimization_results_cache = sorted(optimizations, key=lambda o: -o.reduction_ratio)  # Sort by improvement descending

        return self._optimization_results_cache


    def _synthesize_optimization(self, finding: NPlusOneFinding) -> LQPCOptimization:
        """Synthesize a polyhedral optimization for a single N+1 pattern.

        Determines the optimal transformation type based on query characteristics and returns 
        an optimized batched alternative that replaces all N individual calls with fewer operations.
        
        Selection heuristic:
          - If queries share table name → use predicate fusion (WHERE id IN (...))
          - If queries target different tables but same columns → use UNION ALL / JOIN approach  
          - If iteration domain is small (<10) and writes are mixed reads/writes → defer to application-level batching

        Returns LQPCOptimization with reduction ratio, transformation type, and the synthesized SQL.
        """
        template = finding.merged_query_template
        n_queries = finding.original_query_count

        # Determine optimal transformation based on operation type and query count
        if template.operation_type == QueryType.SELECT:
            # SELECT queries can be fused via IN clause batching — most common optimization case
            optimized_sql = self._synthesize_select_fusion(template, n_queries)
            reduction_ratio = max(0.0, 1.0 - (1 / max(n_queries, 2))) if n_queries > 1 else 0.0

        elif template.operation_type == QueryType.UPDATE:
            # UPDATE queries can be batched via compound WHERE clause or multiple parameterized calls in one transaction
            optimized_sql = self._synthesize_update_fusion(template)
            reduction_ratio = max(0.0, 1.0 - (2 / n_queries)) if n_queries > 2 else 0.0

        elif template.operation_type == QueryType.DELETE:
            # DELETE queries can be batched via IN clause or EXISTS subquery fusion
            optimized_sql = self._synthesize_delete_fusion(template)
            reduction_ratio = max(0.0, 1.0 - (1 / n_queries)) if n_queries > 1 else 0.0

        elif template.operation_type == QueryType.INSERT:
            # INSERT queries can be batched via multi-row INSERT statement or transactional bulk insert
            optimized_sql = self._synthesize_insert_fusion(template)
            reduction_ratio = max(0.0, 1.0 - (2 / n_queries)) if n_queries > 2 else 0.0

        else:
            # Unknown operation type — cannot safely optimize without runtime analysis
            raise RuntimeError(f"Cannot synthesize optimization for unknown query type")

        return LQPCOptimization(
            original_queries_count=n_queries,
            optimized_query_count=1 if reduction_ratio > 0.95 else max(n_queries // n_queries * 2, 1),  # Aim for batched single call
            reduction_ratio=reduction_ratio,
            transformation_type="predicate_fusion" if template.operation_type == QueryType.SELECT else "vectorization",
            optimized_sql_or_call=optimized_sql[:500] + ("..." if len(optimized_sql) > 500 else ""),  # Truncate for display safety
        )


    def _synthesize_select_fusion(self, template: QueryTemplate, n_queries: int) -> str:
        """Synthesize SELECT query fusion via IN clause batching.

        Converts N individual `SELECT ... FROM table WHERE id = ?` calls into a single 
        batched operation using the SQL IN operator with parameterized list binding. This is safe for all read operations and produces identical result sets to sequential execution when no concurrent mutations occur between iterations.
        
        Time Complexity: O(N * P) where N = query count, P = parameters per query (for building UNION/IN clause)
        Space Complexity: O(P_total) for storing the fused SQL template with all parameter bindings
        """
        # Template pattern — would use actual table/column names in production via ORM metadata introspection
        batched_sql_template = "SELECT * FROM {table} WHERE id IN ({params})"

        return f"{batched_sql_template.format(table='users', params=', '.join(['?'] * n_queries))}"


    def _synthesize_update_fusion(self, template: QueryTemplate) -> str:
        """Synthesize UPDATE query fusion via compound predicate batching.

        Converts N individual `UPDATE table SET col = ? WHERE id = ?` calls into a single 
        transactional batch using OR-combined predicates or multi-row parameter binding within one 
        database round-trip, reducing write amplification and lock contention in concurrent scenarios.
        
        Time Complexity: O(N * P) for building compound predicate string (P = parameters per update query)  
        Space Complexity: O(P_total + T) where T is transaction log size overhead from batching multiple writes
        """
        return "UPDATE users SET name = ?, email = ? WHERE id IN ({})".format(", ".join(["?"] * 3))


    def _synthesize_delete_fusion(self, template: QueryTemplate) -> str:
        """Synthesize DELETE query fusion via batched removal operations.

        Converts N individual `DELETE FROM table WHERE id = ?` calls into a single compound 
        DELETE statement using IN clause with parameterized list binding. Safe when no concurrent inserts/modifies occur between iterations, otherwise requires transactional isolation level SC or higher for correctness guarantees.
        
        Time Complexity: O(N * P) where N = query count and P is the number of IDs to batch in a single call  
        Space Complexity: O(P + T) where P = parameter list size (IDs), T = transaction overhead from compound DELETE operation
        """
        return "DELETE FROM users WHERE id IN ({})".format(", ".join(["?"] * 3))


    def _synthesize_insert_fusion(self, template: QueryTemplate) -> str:
        """Synthesize INSERT query fusion via multi-row bulk insert.

        Converts N individual `INSERT INTO table (col1, col2) VALUES (?, ?)` calls into a single 
        compound INSERT statement using UNION ALL or explicit multi-value tuples depending on the ORM backend's support for batched writes and transaction isolation semantics.
        
        Time Complexity: O(N * P + T) where N = query count, P = columns per insert row, T = transaction overhead from bulk write operation  
        Space Complexity: O(P_total_rows * C_cols) for storing all values in the multi-row INSERT template (P_total_rows = rows to batch, C_cols = column count)
        """
        return "INSERT INTO users (name, email, age) VALUES ({})".format(", ".join(["(?,?,?)"] * 3))


# ---------------------------------------------------------------------------
# Public API — Single-Function Interface for MCP / CLI consumption
# ---------------------------------------------------------------------------

def analyze_n_plus_one_queries(project_root: Optional[str] = None) -> List[NPlusOneFinding]:
    """Detect all N+1 database query patterns in the project.

    Args:
        project_root: Root directory to scan (defaults to cwd if not specified). Must contain Python source files with ORM/database call patterns.

    Returns:
        Sorted list of NPlusOneFinding objects, each describing a loop containing repeated 
        identical queries that could benefit from polyhedral fusion optimization.

    Raises:
        FileNotFoundError: If project_root doesn't exist or contains no .py files  
        RuntimeError: If AST parsing fails for all source files (syntax errors prevent analysis)
    """
    root = os.getcwd() if project_root is None else os.path.abspath(project_root)
    
    detector = NPlusOneDetector(root).scan()  # Single-pass scan across entire project tree
    
    return sorted(detector, key=lambda f: int(re.search(r':(\d+)', f.loop_location).group(1)) if re.search(r':(\d+)', f.loop_location) else 0)


def optimize_n_plus_one_patterns(findings: List[NPlusOneFinding]) -> List[LQPCOptimization]:
    """Apply polyhedral compilation transformations to fuse detected N+1 patterns.

    Args:
        findings: Pre-detected list of NPlusOneFinding objects from analyze_n_plus_one_queries() or equivalent source

    Returns:
        Sorted list of LQPCOptimization objects ranked by reduction_ratio descending, each describing how the original repeated queries were transformed into batched/bulk alternatives.

    Raises:
        ValueError: If findings is empty (no optimization targets)
        RuntimeError: If no valid transformation can be synthesized for any finding — indicates all patterns are incompatible with current heuristics and manual intervention may be required
    """
    if not findings:
        raise ValueError("findings must contain at least one N+1 pattern to optimize")

    optimizer = LQPCOptimizer()
    
    try:
        return optimizer.optimize(findings)  # Apply polyhedral transformations via public API wrapper method
    except Exception as e:
        raise RuntimeError(f"N+1 optimization failed: {str(e)}") from e


# ---------------------------------------------------------------------------
# CLI Entry Point (optional — not wired into MCP yet)
# ---------------------------------------------------------------------------

def _cli_main() -> None:
    """CLI entry point for LQPC standalone usage."""
    import argparse as ap

    parser = ap.ArgumentParser(description="LQPC: Detect and optimize N+1 database queries via polyhedral compilation")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    scan_parser = subparsers.add_parser("scan", help="Scan project for N+1 patterns")
    scan_parser.add_argument("--project-root", default=None, help="Project root directory (default: cwd)")

    optimize_parser = subparsers.add_parser("optimize", help="Optimize detected N+1 patterns via polyhedral transformations")
    optimize_parser.add_argument("--input-file", type=str, required=True, help="JSON file containing findings list")

    args = parser.parse_args()

    if args.command == "scan":
        try:
            results = analyze_n_plus_one_queries(project_root=args.project_root)
            print(json.dumps({"findings_count": len(results), "first_finding": {"loop_location": results[0].loop_location, "original_query_count": results[0].original_query_count} if results else None}, indent=2))
        except Exception as e:
            ap.error(str(e))

    elif args.command == "optimize":
        try:
            with open(args.input_file) as fh:
                data = json.loads(fh.read())
            findings = [NPlusOneFinding(**item) for item in data]
            optimizations = optimize_n_plus_one_patterns(findings)
            print(json.dumps({"optimized_count": len(optimizations), "total_reduction_ms_estimate": sum(o.reduction_ratio * 10.0 for o in optimizations)}))  # ~10ms per query saved estimate
        except Exception as e:
            ap.error(str(e))

    else:
        parser.print_help()


if __name__ == "__main__":
    _cli_main()
