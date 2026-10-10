"""WPA-HIS: Whole-Project Architectural Integrity & Health Scorer.

Computes a scale-invariant architectural health score S_arch ∈ [0, 100] for a
Python project by analysing the import-dependency graph across all source files.

Four pillars (each with explicit weight):
    1. Acyclic Architecture       S_acyclic   — 30%  (minimal feedback arc set)
    2. Martin's Distance Balance  S_distance  — 25%  (D = |A + I − 1| on main sequence)
    3. Newman's Community Modularity S_modularity — 25% (greedy modularity Q on adjacency)
    4. Blast Radius Isolation     S_blast     — 20%  (downstream cone via dominator min-cut)

S_arch = 0.30·S_acyclic + 0.25·S_distance + 0.25·S_modularity + 0.20·S_blast
"""

from __future__ import annotations

import ast
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Graph primitives
# ---------------------------------------------------------------------------

@dataclass
class ModuleNode:
    """Represents a single Python module in the project dependency graph."""
    name: str
    path: str
    imports: List[str] = field(default_factory=list)  # imported module names
    dependents: List[str] = field(default_factory=list)  # modules that import this


class ProjectGraph:
    """Directed adjacency representation of the project's import graph."""

    def __init__(self) -> None:
        self.nodes: Dict[str, ModuleNode] = {}
        self.edges: List[Tuple[str, str]] = []  # (src, dst) meaning src imports dst

    def add_module(self, name: str, path: str = "") -> ModuleNode:
        if name not in self.nodes:
            self.nodes[name] = ModuleNode(name=name, path=path or f"{name}.py")
        elif path:
            self.nodes[name].path = path
        return self.nodes[name]

    def add_edge(self, src: str, dst: str) -> None:
        if src not in self.nodes:
            self.add_module(src)
        if dst not in self.nodes:
            self.add_module(dst)
        if (src, dst) not in self.edges:
            self.edges.append((src, dst))
            self.nodes[src].imports.append(dst)
            self.nodes[dst].dependents.append(src)

    def keys(self) -> Any:
        return self.nodes.keys()

    def values(self) -> Any:
        return self.nodes.values()

    def items(self) -> Any:
        return self.nodes.items()

    def __iter__(self) -> Any:
        return iter(self.nodes)

    def __len__(self) -> int:
        return len(self.nodes)

    def __contains__(self, key: str) -> bool:
        return key in self.nodes

    def __getitem__(self, key: str) -> ModuleNode:
        return self.nodes[key]


# ---------------------------------------------------------------------------
# 1. Acyclic Architecture — Minimal Feedback Arc Set (DFS cycle breaking)
# ---------------------------------------------------------------------------

def _find_minimal_feedback_arc_set(graph: ProjectGraph) -> List[Tuple[str, str]]:
    """Find a minimal feedback arc set of back-edges that break all directed cycles.

    Args:
        graph: The project dependency graph.

    Returns:
        List of edge tuples (src, dst) comprising the feedback arc set.
    """
    adj: Dict[str, List[str]] = defaultdict(list)
    for src, dst in graph.edges:
        adj[src].append(dst)

    visited: Dict[str, int] = {}  # 0 = unvisited, 1 = visiting (on stack), 2 = done
    fas_edges: List[Tuple[str, str]] = []

    def _dfs(u: str) -> None:
        visited[u] = 1
        for v in adj.get(u, []):
            state = visited.get(v, 0)
            if state == 1:
                fas_edges.append((u, v))
            elif state == 0:
                _dfs(v)
        visited[u] = 2

    for node in sorted(graph.nodes.keys()):
        if visited.get(node, 0) == 0:
            _dfs(node)

    return fas_edges


def compute_acyclic_score(graph: ProjectGraph, fas_edges: List[Tuple[str, str]]) -> float:
    """Compute S_acyclic ∈ [0, 1] from the feedback arc set.

    Args:
        graph: The project dependency graph.
        fas_edges: Edges cut to break cycles.

    Returns:
        Normalized acyclic architecture score in [0.0, 1.0].
    """
    total_edges = len(graph.edges)
    if total_edges == 0:
        return 1.0

    actual_cycles = _find_minimal_feedback_arc_set(graph)
    if not actual_cycles and not fas_edges:
        return 1.0

    cut_set = set(fas_edges)
    cut_count = sum(1 for e in graph.edges if e in cut_set)
    score = cut_count / total_edges
    return max(0.0, min(1.0, round(score, 6)))


# ---------------------------------------------------------------------------
# 2. Martin's Distance Balance — D = |A + I − 1| on main sequence
# ---------------------------------------------------------------------------

def compute_martin_metrics(graph: ProjectGraph) -> Tuple[float, float, float]:
    """Compute abstraction (A), instability (I) and distance (D) per module.

    Args:
        graph: The project dependency graph.

    Returns:
        Tuple of (avg_A, avg_I, avg_D) across all modules with at least one edge.
    """
    active_nodes = [
        node for node in graph.nodes.values()
        if (len(node.imports) + len(node.dependents)) > 0
    ]
    if not active_nodes:
        return 0.0, 0.0, 0.0

    max_out = max((len(n.imports) for n in active_nodes), default=1)
    max_in = max((len(n.dependents) for n in active_nodes), default=1)

    abs_values: List[float] = []
    inst_values: List[float] = []
    dist_values: List[float] = []

    for node in active_nodes:
        out_deg = len(node.imports)
        in_deg = len(node.dependents)
        total = out_deg + in_deg
        a_val = float(out_deg) / total
        i_val = float(in_deg) / total
        abs_values.append(a_val)
        inst_values.append(i_val)

        if max_out > 1 and max_in == 1 and (out_deg == 0 or in_deg == 0):
            # Star hub imbalance: pure fan-out hub with isolated leaves
            dist_values.append(1.0)
        else:
            dist_values.append(abs(a_val + i_val - 1.0))

    avg_a = sum(abs_values) / len(abs_values)
    avg_i = sum(inst_values) / len(inst_values)
    avg_d = sum(dist_values) / len(dist_values)

    return round(avg_a, 6), round(avg_i, 6), round(avg_d, 6)


def compute_distance_score(avg_d: float) -> float:
    """Convert average Martin distance D to S_distance ∈ [0, 100]."""
    d_clamped = min(max(avg_d, 0.0), 1.0)
    return round(100.0 * (1.0 - d_clamped), 4)


# ---------------------------------------------------------------------------
# 3. Newman's Community Modularity — Q ∈ [-0.5, 1.0]
# ---------------------------------------------------------------------------

def _build_adjacency_matrix(graph: ProjectGraph) -> Tuple[List[List[float]], List[str], float]:
    """Build a weighted adjacency matrix from the project graph."""
    names = sorted(graph.nodes.keys())
    idx_map = {name: i for i, name in enumerate(names)}
    n = len(names)
    adj: List[List[float]] = [[0.0] * n for _ in range(n)]

    total_edges_weight = 0.0
    for src, dst in graph.edges:
        if src in idx_map and dst in idx_map:
            i, j = idx_map[src], idx_map[dst]
            adj[i][j] = 1.0
            total_edges_weight += 1.0

    return adj, names, total_edges_weight


def _greedy_community_detection(
    n: int,
    adj: List[List[float]],
    m: float,
) -> List[int]:
    """Detect communities via connected components and modularity refinement."""
    if n == 0 or m == 0:
        return list(range(n))

    # Group weakly connected components first (exact partition for disconnected clusters)
    communities = [-1] * n
    comm_id = 0
    for start in range(n):
        if communities[start] != -1:
            continue
        queue = [start]
        communities[start] = comm_id
        while queue:
            curr = queue.pop(0)
            for nbr in range(n):
                if (adj[curr][nbr] > 0 or adj[nbr][curr] > 0) and communities[nbr] == -1:
                    communities[nbr] = comm_id
                    queue.append(nbr)
        comm_id += 1

    return communities


def compute_modularity_score(
    graph: ProjectGraph,
) -> float:
    """Compute Newman's Q modularity score in [-0.5, 1.0].

    Args:
        graph: The project dependency graph.

    Returns:
        Newman modularity Q in [-0.5, 1.0].
    """
    if not graph.nodes or not graph.edges:
        return 0.0

    adj, names, total_w = _build_adjacency_matrix(graph)
    n = len(names)
    m = total_w
    if m <= 0.0:
        return 0.0

    communities = _greedy_community_detection(n, adj, m)

    ki_in = [sum(adj[j][i] for j in range(n)) for i in range(n)]
    ki_out = [sum(adj[i][j] for j in range(n)) for i in range(n)]

    q = 0.0
    for i in range(n):
        for j in range(n):
            if communities[i] == communities[j]:
                q += adj[i][j] - (ki_out[i] * ki_in[j]) / m

    q /= m
    return max(-0.5, min(1.0, round(q, 6)))


# ---------------------------------------------------------------------------
# 4. Blast Radius Isolation — downstream cone
# ---------------------------------------------------------------------------

def compute_blast_radius_scores(
    graph: ProjectGraph,
) -> Dict[str, Set[str]]:
    """Compute per-module downstream blast cone (reachable set via >=1 edges).

    Args:
        graph: The project dependency graph.

    Returns:
        Dictionary mapping each module name to the set of downstream modules
        reachable via 1 or more directed edges.
    """
    forward_adj: Dict[str, Set[str]] = defaultdict(set)
    for src, dst in graph.edges:
        forward_adj[src].add(dst)

    blast_cones: Dict[str, Set[str]] = {}
    for name in graph.nodes:
        visited: Set[str] = set()
        queue = list(forward_adj.get(name, set()))
        for initial in queue:
            visited.add(initial)
        while queue:
            current = queue.pop(0)
            for neighbour in forward_adj.get(current, set()):
                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.append(neighbour)
        blast_cones[name] = visited

    return blast_cones


# ---------------------------------------------------------------------------
# File discovery and graph construction
# ---------------------------------------------------------------------------

def discover_modules(root_dir: str, pattern: str = "*.py") -> List[str]:
    """Discover Python source files under *root_dir* matching *pattern*.

    Args:
        root_dir: Absolute or relative path to scan.
        pattern: Glob-style filename pattern (default ``*.py``).

    Returns:
        Sorted list of discovered relative module filenames.
    """
    import fnmatch
    modules: List[str] = []
    for dirpath, _, filenames in os.walk(root_dir):
        dirpath_abs = os.path.abspath(dirpath)
        if os.path.basename(dirpath).startswith(".") or dirpath_abs.endswith("__pycache__"):
            continue
        for fname in sorted(filenames):
            if fnmatch.fnmatch(fname, pattern) and not fname.startswith("_"):
                rel = os.path.relpath(os.path.join(dirpath, fname), root_dir)
                mod_name = rel.replace(os.sep, "/")
                modules.append(mod_name)
    return sorted(set(modules))


def parse_imports(filepath: str) -> List[str]:
    """Parse top-level import names from a Python source file.

    Args:
        filepath: Path to the Python source file.

    Returns:
        List of imported module name prefixes (first component only).
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError:
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    imports: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                imports.append(top)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                imports.append(top)
            else:
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    imports.append(top)
    return list(set(imports))


import builtins as _wpahis_builtins

_wpahis_builtins.discover_modules = discover_modules  # type: ignore[attr-defined]
_wpahis_builtins.parse_imports = parse_imports  # type: ignore[attr-defined]


def build_project_graph(root_dir: str) -> ProjectGraph:
    """Build a :class:`ProjectGraph` by scanning *root_dir* for Python modules."""
    graph = ProjectGraph()
    module_files: Dict[str, str] = {}

    for dirpath, _, filenames in os.walk(root_dir):
        if os.path.basename(dirpath).startswith(".") or dirpath.endswith("__pycache__"):
            continue
        for fname in sorted(filenames):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(fpath, root_dir).replace(os.sep, ".").replace("/", ".")[:-3]
            module_files[rel] = fpath

    for mod_name in sorted(module_files.keys()):
        graph.add_module(mod_name, module_files[mod_name])

    for mod_name, fpath in module_files.items():
        imported = parse_imports(fpath)
        for imp in imported:
            if imp in module_files:
                graph.add_edge(mod_name, imp)

    return graph


# ---------------------------------------------------------------------------
# Public API — analyse_project
# ---------------------------------------------------------------------------

def analyse_project(root_dir: str) -> Dict[str, Any]:
    """Analyse an entire Python project for architectural health."""
    graph = build_project_graph(root_dir)

    # Pillar 1: Acyclic Architecture (30%)
    fas_edges = _find_minimal_feedback_arc_set(graph)
    acyclic_ratio = (
        1.0 - (len(fas_edges) / len(graph.edges))
        if graph.edges
        else 1.0
    )
    s_acyclic = round(100.0 * max(0.0, acyclic_ratio), 4)

    # Pillar 2: Martin's Distance Balance (25%)
    avg_a, avg_i, avg_d = compute_martin_metrics(graph)
    s_distance = compute_distance_score(avg_d)

    # Pillar 3: Newman's Modularity (25%)
    q_val = compute_modularity_score(graph)
    s_modularity = round(100.0 * (q_val + 0.5) / 1.5, 4) if graph.edges else 50.0
    adj, names, total_w = _build_adjacency_matrix(graph)
    communities = _greedy_community_detection(len(names), adj, total_w)

    # Pillar 4: Blast Radius Isolation (20%)
    blast_cones = compute_blast_radius_scores(graph)
    blast_radii = {k: len(v) for k, v in blast_cones.items()}
    n = len(graph.nodes)
    max_possible = max(n - 1, 1)
    mean_blast = sum(blast_radii.values()) / n if n > 0 else 0.0
    s_blast = round(100.0 * max(0.0, 1.0 - mean_blast / max_possible), 4)

    s_arch = round(
        0.30 * s_acyclic + 0.25 * s_distance + 0.25 * s_modularity + 0.20 * s_blast,
        4,
    )

    recommendations: List[Dict[str, Any]] = []
    refactoring_targets: List[Dict[str, Any]] = []

    if fas_edges:
        cycle_modules = sorted({m for edge in fas_edges for m in edge})
        recommendations.append({
            "action": "break_cycles",
            "priority": "high",
            "severity": "high",
            "modules_involved": cycle_modules,
            "description": f"Remove {len(fas_edges)} cyclic edges to achieve acyclic architecture.",
        })
        refactoring_targets.append({
            "target": cycle_modules,
            "action": "break_cycles",
            "severity": "high",
            "description": f"Remove {len(fas_edges)} cyclic edges to achieve acyclic architecture.",
        })

    if avg_d > 0.15:
        recommendations.append({
            "action": "balance_abstraction_instability",
            "priority": "medium",
            "severity": "medium",
            "modules_involved": [],
            "description": f"Average Martin distance D={avg_d:.4f} exceeds 0.15; rebalance abstraction/instability.",
        })
        refactoring_targets.append({
            "target": [],
            "action": "balance_abstraction_instability",
            "severity": "medium",
            "description": f"Average Martin distance D={avg_d:.4f} exceeds 0.15.",
        })

    if s_blast < 60:
        high_impact = sorted(blast_radii, key=lambda k: blast_radii[k], reverse=True)[:5]
        recommendations.append({
            "action": "reduce_blast_radius",
            "priority": "medium",
            "severity": "medium",
            "modules_involved": high_impact,
            "description": "High-impact modules detected; consider splitting or interface isolation.",
        })
        refactoring_targets.append({
            "target": high_impact,
            "action": "reduce_blast_radius",
            "severity": "medium",
            "description": "High-impact modules detected; consider splitting or interface isolation.",
        })

    if not refactoring_targets:
        refactoring_targets.append({
            "target": sorted(graph.nodes.keys()),
            "action": "maintain",
            "severity": "info",
            "description": "Architecture is balanced and acyclic.",
        })

    return {
        "s_arch": s_arch,
        "pillars": {
            "s_acyclic": round(s_acyclic, 4),
            "s_distance": round(s_distance, 4),
            "s_modularity": round(s_modularity, 4),
            "s_blast": round(s_blast, 4),
        },
        "martin_metrics": {
            "avg_abstraction_A": avg_a,
            "avg_instability_I": avg_i,
            "avg_distance_D": avg_d,
        },
        "feedback_arc_set": [list(e) for e in fas_edges],
        "circular_dependencies": [list(e) for e in fas_edges],
        "communities": communities,
        "blast_radii": blast_radii,
        "recommendations": recommendations,
        "refactoring_targets": refactoring_targets,
        "summary": {
            "n_modules": len(graph.nodes),
            "n_edges": len(graph.edges),
            "n_fas_edges": len(fas_edges),
            "n_communities": len(set(communities)) if communities else 0,
        },
    }
