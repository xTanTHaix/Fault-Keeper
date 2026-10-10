"""SSDL: Service Dependency Slicing for Dependency Hell Resolution.

Resolves circular import hell via micro-shim generation using API slicing technique.

Core functionality:
- Detect circular import chains in project
- Generate micro-shims to break cycles
- Re-export symbols through proxy methods
"""

from __future__ import annotations

import ast as _ast_module
import os
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data Structures for Dependency Graph
# ---------------------------------------------------------------------------

class DependencyGraph:
    """Builds dependency graph from project."""

    def __init__(self, project_root: str) -> None:
        """Initialize dependency graph.

        Args:
            project_root: Root directory of project.
        """
        self.project_root = project_root
        self.modules: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, str]] = []

    def build(self) -> None:
        """Build dependency graph from project."""
        import os

        for root, dirs, files in os.walk(self.project_root):
            for fname in files:
                if not fname.endswith(".py"):
                    continue

                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, self.project_root)

                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        source = f.read()
                    tree = _ast_module.parse(source)

                    # Extract imports
                    for node in _ast_module.walk(tree):
                        if isinstance(node, (_ast_module.Import, _ast_module.ImportFrom)):
                            if isinstance(node, _ast_module.Import):
                                for alias in node.names:
                                    self.edges.append({
                                        "from": rel_path,
                                        "to": alias.name,
                                    })
                            elif isinstance(node, _ast_module.ImportFrom):
                                module = node.module or ""
                                self.edges.append({
                                    "from": rel_path,
                                    "to": module,
                                })
                except Exception:
                    continue


class ConflictType:
    """Enum-like class for conflict types."""

    CIRCULAR_DEPENDENCY = "circular_dependency"
    IMPORT_CYCLE = "import_cycle"
    MISSING_SYMBOL = "missing_symbol"


class DependencyConflict:
    """Represents a dependency conflict."""

    def __init__(self, affected_modules: List[str]) -> None:
        """Initialize conflict.

        Args:
            affected_modules: List of modules involved in conflict.
        """
        self.affected_modules = affected_modules


class MicroShim:
    """Represents a generated micro-shim module."""

    def __init__(self, name: str, source_module_wrapping: List[str]) -> None:
        """Initialize micro-shim.

        Args:
            name: Name of shim module (e.g., 'shim_app_services.py').
            source_module_wrapping: List of original modules whose API is being proxied.
        """
        self.name = name
        self.source_module_wrapping = source_module_wrapping


# ---------------------------------------------------------------------------
# Conflict Detector
# ---------------------------------------------------------------------------

class ConflictDetector:
    """Detects dependency conflicts in project."""

    def detect(self, graph: DependencyGraph) -> Dict[str, List[DependencyConflict]]:
        """Detect all dependency conflicts.

        Args:
            graph: Pre-built dependency graph.

        Returns:
            Dictionary mapping conflict type to list of conflicts.
        """
        conflicts_by_type: Dict[str, List[DependencyConflict]] = {}

        # Build adjacency from edges
        adj: Dict[str, set] = {}
        for edge in graph.edges:
            from_mod = edge["from"]
            to_mod = edge["to"]

            if from_mod not in adj:
                adj[from_mod] = set()
            adj[from_mod].add(to_mod)

        # Detect cycles using DFS
        visited: set = set()
        rec_stack: set = set()
        cycles: List[List[str]] = []

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in adj.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])

            path.pop()
            rec_stack.remove(node)

        for node in adj:
            if node not in visited:
                dfs(node, [])

        # Create conflicts from cycles
        for cycle in cycles:
            conflict = DependencyConflict(affected_modules=list(set(cycle)))
            conflict_type = ConflictType.CIRCULAR_DEPENDENCY
            conflicts_by_type[conflict_type] = conflicts_by_type.get(conflict_type, [])
            conflicts_by_type[conflict_type].append(conflict)

        return conflicts_by_type


# ---------------------------------------------------------------------------
# Micro-Shim Generator — Slice-based API isolation  
# ---------------------------------------------------------------------------

class SSDLShimGenerator:
    """Generates micro-shims to resolve dependency conflicts via API slicing.

    For each detected circular import chain, generates a thin adapter module that wraps the original 
    problematic imports through transparent proxy methods. The shim re-exports symbols from conflicting modules 
    using conditional resolution logic — attempting direct import first and falling back gracefully if unavailable  
    
    Generated shims follow this pattern:
      ```python
      # shim_A_B.py (resolves A → B circular dependency)
      
      def _get_b_module():
          'Lazy resolve module B to avoid NameError from circular imports.'
          try: return __import__('B')   # Direct import attempt  
          except ImportError: pass       # Fall back if direct import fails due to cycle  
          
      class AAdapter:
          @staticmethod  # Static methods for easy monkey-patching and testability 
          def method_name():            # Each original API surface area gets a corresponding adapter wrapper
              return _get_b_module().original_method()   # Proxy through shim layer transparently  
      """

    def generate(self, conflicts: List[DependencyConflict], graph: DependencyGraph) -> List[MicroShim]:
        """Generate micro-shims to resolve all detected dependency conflicts.

        Args:  
            conflicts: Pre-detected list of DependencyConflict objects from ConflictDetector.detect() 
            graph: The pre-built DependencyGraph with forward and reverse edge mappings populated  

        Returns:  
            Sorted list of MicroShim objects, each describing a generated shim module that resolves one or more circular dependency chains. Shims are sorted by affected modules count descending so largest conflicts get resolved first for maximum impact on import resolution success rate across the project tree 

        Raises:
          ValueError: If conflicts is empty — no shims to generate without detected cycles  
          RuntimeError: If graph doesn't contain enough module information to synthesize shim code (missing metadata or incomplete edge data) 
        """
        if not conflicts:   # Validate input before proceeding with generation logic that requires at least one conflict cluster 
            raise ValueError("conflicts must contain at least one dependency cycle to generate shims for")

        shims_generated: List[MicroShim] = []  # Will hold all generated shim objects after synthesis  

        for conflict in conflicts:   # Iterate over each detected circular import chain and synthesize a corresponding adapter module  
            if not graph.edges or len(graph.modules) < 2:
                continue   # Skip cycles that can't be resolved without sufficient module metadata available for analysis 

            affected_modules = list(set(conflict.affected_modules))

            shim_name = f"shim_{'_'.join(affected[:3])}.py" if len(affected_modules) > 0 else "shim_unknown.py"
            
            # Build adapter methods mapping original API surface area to their resolved proxy implementation location within the generated shim module  
            adapter_methods: Dict[str, str] = {}   # Maps method names → resolution strategy (direct import or fallback path)

            for affected_module in set(affected_modules):  # Iterate over unique modules participating in this conflict cycle 
                if len(adapter_methods) > 0 and affected_module not in graph.modules:
                    continue  # Skip modules that don't exist in our dependency graph metadata — they're likely external or transient 

                try:   # Attempt to extract public API symbols from each module's source file via AST inspection  
                    with open(os.path.join(graph.project_root, affected_module), "r", encoding="utf-8") as fh:
                        _ast_module.parse(fh.read())  # Validate syntax before extracting symbol metadata  

                    for node in _ast_module.walk(tree):   # Walk the parsed AST to find all public classes and functions
                        if isinstance(node, (_ast_module.ClassDef,)):
                            adapter_methods[node.name] = f"from {affected_module} import {node.name}"  # Direct re-export from original module 

                except (OSError, UnicodeDecodeError):
                    continue   # Skip files we can't read or parse without failing the entire generation process  

        return sorted(shims_generated, key=lambda s: -len(s.affected_modules) if hasattr(s, 'affected_modules') else 0)


# ---------------------------------------------------------------------------
# Public API — Single-Function Interface for MCP / CLI consumption  
# ---------------------------------------------------------------------------

def resolve_dependency_conflicts(project_root: Optional[str] = None) -> Dict[str, Any]:
    """Resolve all dependency conflicts in the project by generating micro-shims.

    Args:  
        project_root: Root directory containing Python source files to analyze (defaults to cwd if not specified). Must contain at least one .py file with import statements for meaningful conflict detection 

    Returns:  
        Dict summarizing resolution results including total conflicts found, shims generated, and estimated migration effort in terms of code changes required. Format follows JSON-RPC response schema expected by MCP clients for consistent API contract  

    Raises:
        RuntimeError: If project_root is invalid or contains no Python files to analyze 
        ValueError: If no dependency conflicts are detected and no shims can be generated 

    Example:
        >>> result = resolve_dependency_conflicts("/path/to/project")
        >>> print(result["summary"]["conflicts_found"])
        3
        >>> print(result["summary"]["shims_generated"])
        2
    """
    if project_root is None:
        project_root = "."

    # Build dependency graph
    graph = DependencyGraph(project_root)
    graph.build()

    # Detect conflicts
    detector = ConflictDetector()
    conflicts = detector.detect(graph)

    if not conflicts:
        return {
            "success": False,
            "message": "No dependency conflicts detected",
            "summary": {
                "conflicts_found": 0,
                "shims_generated": 0,
                "estimated_effort": 0,
            },
        }

    # Generate shims
    generator = SSDLShimGenerator()
    try:
        shims = generator.generate(list(conflicts.values())[0], graph)
    except ValueError as e:
        return {
            "success": False,
            "message": str(e),
            "summary": {
                "conflicts_found": len(conflicts),
                "shims_generated": 0,
                "estimated_effort": 0,
            },
        }

    # Calculate estimated effort
    total_lines = sum(10 for _ in shims)  # Estimate 10 lines per shim
    estimated_effort = total_lines

    return {
        "success": True,
        "summary": {
            "conflicts_found": len(conflicts),
            "shims_generated": len(shims),
            "estimated_effort": estimated_effort,
        },
        "shims": [
            {
                "name": shim.name,
                "wrapping": shim.source_module_wrapping,
            }
            for shim in shims
        ],
    }


__all__ = [
    "DependencyGraph",
    "ConflictType",
    "DependencyConflict",
    "MicroShim",
    "ConflictDetector",
    "SSDLShimGenerator",
    "resolve_dependency_conflicts",
]
