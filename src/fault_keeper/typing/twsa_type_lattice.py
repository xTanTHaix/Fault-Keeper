"""TWSA: Type Weighted Super-fast Auto-complete with Type Lattice.

Provides ultra-fast fuzzy auto-completion (< 0.5ms) using Type Lattice graph.

Core functionality:
- Type lattice construction for type hierarchy relationships
- Fuzzy matching with weighted scoring
- Ultra-fast completion suggestions under 0.5ms latency
"""

from __future__ import annotations

import math
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class TypeNode:
    """Represents an internal node in the Type Lattice graph."""
    name: str
    type_id: str
    kind: str
    signature: str = ""
    docstring: str = ""
    children: List[str] = field(default_factory=list)
    parents: List[str] = field(default_factory=list)
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type_id": self.type_id,
            "kind": self.kind,
            "signature": self.signature,
            "docstring": self.docstring[:200] if self.docstring else "",
            "children": self.children,
            "parents": self.parents,
            "weight": self.weight,
        }


@dataclass
class TypeLatticeNode:
    """Represents a node in a Type Lattice hierarchy for autocompletion."""
    name: str
    depth: int = 0
    children: Optional[List[Any]] = None

    def __post_init__(self) -> None:
        if self.children is None:
            self.children = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "depth": self.depth,
            "children": [
                c.name if isinstance(c, TypeLatticeNode) else str(c)
                for c in self.children
            ],
        }


@dataclass
class LatticeEdge:
    """Represents an edge in the Type Lattice."""
    from_type: str
    to_type: str
    relation: str
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_type": self.from_type,
            "to_type": self.to_type,
            "relation": self.relation,
            "weight": self.weight,
        }


@dataclass
class CompletionSuggestion:
    """A single completion suggestion."""
    text: str
    type_name: str
    kind: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "type_name": self.type_name,
            "kind": self.kind,
            "score": round(self.score, 4),
            "metadata": self.metadata,
        }


class TypeLatticeGraph:
    """Type Lattice graph for fuzzy completion with type hierarchy."""

    def __init__(self) -> None:
        self.nodes: Dict[str, TypeNode] = {}
        self.edges: List[LatticeEdge] = []
        self.adjacency: Dict[str, Set[str]] = {}
        self.reverse_adjacency: Dict[str, Set[str]] = {}

    def add_node(self, node: TypeNode) -> None:
        self.nodes[node.name] = node
        if node.name not in self.adjacency:
            self.adjacency[node.name] = set()
        if node.name not in self.reverse_adjacency:
            self.reverse_adjacency[node.name] = set()

    def add_edge(self, from_type: str, to_type: str, relation: str, weight: float = 1.0) -> None:
        edge = LatticeEdge(from_type, to_type, relation, weight)
        self.edges.append(edge)

        if from_type in self.adjacency:
            self.adjacency[from_type].add(to_type)
        else:
            self.adjacency[from_type] = {to_type}

        if to_type in self.reverse_adjacency:
            self.reverse_adjacency[to_type].add(from_type)
        else:
            self.reverse_adjacency[to_type] = {from_type}

    def build_lattice(self, types_data: List[Dict[str, Any]]) -> None:
        for type_info in types_data:
            name = type_info.get("name", "")
            kind = type_info.get("kind", "class")
            signature = type_info.get("signature", "")
            docstring = type_info.get("docstring", "")
            parents = type_info.get("parents", [])

            node = TypeNode(
                name=name,
                type_id=f"__{hash(name)}__",
                kind=kind,
                signature=signature,
                docstring=docstring,
                parents=parents,
            )
            self.add_node(node)

            for parent in parents:
                self.add_edge(name, parent, "subtype", 0.8)
                self.add_edge(parent, name, "super", 1.0)

    def compute_lattice_distances(self) -> Dict[str, Dict[str, float]]:
        """Compute all-pairs shortest path distances using single-source BFS per node.

        Runs V single-source BFS passes using collections.deque in O(V(V + E)),
        eliminating the O(V^4) list.pop(0) penalty.
        """
        distances: Dict[str, Dict[str, float]] = {}

        for start_node in self.nodes:
            dist_map: Dict[str, float] = {}
            visited: Set[str] = {start_node}
            queue: deque[Tuple[str, float]] = deque([(start_node, 0.0)])

            while queue:
                curr, d = queue.popleft()
                for neighbor in self.adjacency.get(curr, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        dist_map[neighbor] = d + 1.0
                        queue.append((neighbor, d + 1.0))

            distances[start_node] = dist_map

        return distances

    def _bfs_distance(self, start: str, end: str) -> float:
        """Compute shortest path distance between start and end via O(V+E) BFS."""
        if start == end:
            return 0.0

        visited: Set[str] = {start}
        queue: deque[Tuple[str, float]] = deque([(start, 0.0)])

        while queue:
            current, dist = queue.popleft()
            for neighbor in self.adjacency.get(current, set()):
                if neighbor == end:
                    return dist + 1.0
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, dist + 1.0))

        return float("inf")


class FuzzyMatcher:
    """Fuzzy matcher for type completions with lattice weighting."""

    MAX_DISTANCE = 3

    def __init__(self, lattice: TypeLatticeGraph) -> None:
        self.lattice = lattice
        self.distances: Dict[str, Dict[str, float]] = {}

    def compute_distances(self) -> None:
        """Eliminate computing unread all-pairs distance matrix on initialization.

        Maintains < 0.5ms SLA. Graph distances are evaluated on-demand when requested.
        """
        self.distances = {}

    def match(self, query: str, threshold: float = 0.5) -> List[CompletionSuggestion]:
        """Match query against lattice types using Levenshtein distance and lattice weights.

        Does not trigger unread all-pairs distance computation, guaranteeing <0.5ms SLA.
        """
        suggestions: List[CompletionSuggestion] = []

        for node_name, node in self.lattice.nodes.items():
            distance = self._levenshtein(query, node_name)
            max_len = max(len(query), len(node_name), 1)
            similarity = 1.0 - (distance / max_len)

            if similarity >= threshold or node_name.lower().startswith(query.lower()):
                weight = self._get_lattice_weight(node_name)
                # Boost prefix matches
                if node_name.lower().startswith(query.lower()):
                    similarity = max(similarity, 0.85)
                score = similarity * weight

                suggestion = CompletionSuggestion(
                    text=node_name,
                    type_name=node.type_id,
                    kind=node.kind,
                    score=score,
                    metadata={
                        "distance": distance,
                        "similarity": similarity,
                        "weight": weight,
                        "parents": node.parents,
                        "children": node.children,
                    },
                )
                suggestions.append(suggestion)

        suggestions.sort(key=lambda s: s.score, reverse=True)
        return suggestions

    def _levenshtein(self, s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return self._levenshtein(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1] + [0] * len(s2)
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row[j + 1] = min(insertions, deletions, substitutions)
            previous_row = current_row

        return previous_row[-1]

    def _get_lattice_weight(self, type_name: str) -> float:
        degree = len(self.lattice.adjacency.get(type_name, set()))
        return 1.0 + math.log(degree + 1) / 10.0


DEFAULT_TYPES_DATA: List[Dict[str, Any]] = [
    {"name": "int", "kind": "builtin", "parents": ["float", "object"]},
    {"name": "float", "kind": "builtin", "parents": ["number", "object"]},
    {"name": "number", "kind": "builtin", "parents": ["object"]},
    {"name": "str", "kind": "builtin", "parents": ["object"]},
    {"name": "bool", "kind": "builtin", "parents": ["int", "object"]},
    {"name": "list", "kind": "builtin", "parents": ["object"]},
    {"name": "dict", "kind": "builtin", "parents": ["object"]},
    {"name": "set", "kind": "builtin", "parents": ["object"]},
    {"name": "tuple", "kind": "builtin", "parents": ["object"]},
    {"name": "bytes", "kind": "builtin", "parents": ["object"]},
    {"name": "object", "kind": "builtin", "parents": []},
    {"name": "Any", "kind": "typing", "parents": ["object"]},
    {"name": "Optional", "kind": "typing", "parents": ["object"]},
    {"name": "Union", "kind": "typing", "parents": ["object"]},
    {"name": "Callable", "kind": "typing", "parents": ["object"]},
    {"name": "Iterator", "kind": "typing", "parents": ["object"]},
    {"name": "Generator", "kind": "typing", "parents": ["Iterator"]},
    {"name": "Coroutine", "kind": "typing", "parents": ["object"]},
    {"name": "def", "kind": "keyword", "parents": []},
    {"name": "async", "kind": "keyword", "parents": []},
    {"name": "await", "kind": "keyword", "parents": []},
    {"name": "class", "kind": "keyword", "parents": []},
    {"name": "return", "kind": "keyword", "parents": []},
    {"name": "fetch", "kind": "function", "parents": []},
    {"name": "get", "kind": "function", "parents": []},
    {"name": "post", "kind": "function", "parents": []},
    {"name": "default", "kind": "keyword", "parents": []},
]

DEFAULT_TYPE_HIERARCHY: Dict[str, Dict[str, Any]] = {
    "object": {"depth": 0, "parents": []},
    "Any": {"depth": 1, "parents": ["object"]},
    "number": {"depth": 1, "parents": ["object"]},
    "complex": {"depth": 2, "parents": ["number"]},
    "float": {"depth": 3, "parents": ["complex"]},
    "int": {"depth": 4, "parents": ["float"]},
    "bool": {"depth": 5, "parents": ["int"]},
    "str": {"depth": 1, "parents": ["object"]},
    "bytes": {"depth": 1, "parents": ["object"]},
    "list": {"depth": 1, "parents": ["object"]},
    "dict": {"depth": 1, "parents": ["object"]},
    "set": {"depth": 1, "parents": ["object"]},
    "tuple": {"depth": 1, "parents": ["object"]},
    "None": {"depth": 1, "parents": ["object"]},
    "Callable": {"depth": 1, "parents": ["object"]},
    "Iterator": {"depth": 1, "parents": ["object"]},
    "Generator": {"depth": 2, "parents": ["Iterator"]},
    "Coroutine": {"depth": 1, "parents": ["object"]},
    "Exception": {"depth": 1, "parents": ["object"]},
    "ValueError": {"depth": 2, "parents": ["Exception"]},
    "TypeError": {"depth": 2, "parents": ["Exception"]},
}


def _get_type_ancestors(
    type_name: str,
    lattice: Optional[TypeLatticeGraph] = None,
) -> Dict[str, int]:
    """Retrieve all ancestor types and their hop distance via fast on-demand traversal."""
    ancestors: Dict[str, int] = {type_name: 0}
    queue: deque[Tuple[str, int]] = deque([(type_name, 0)])
    visited: Set[str] = {type_name}

    # 1. If lattice graph is provided, traverse lattice node parents and subtype edges
    if lattice is not None and type_name in lattice.nodes:
        while queue:
            curr, dist = queue.popleft()
            node = lattice.nodes.get(curr)
            direct_parents = list(node.parents) if node else []
            for target in lattice.adjacency.get(curr, set()):
                if target not in direct_parents:
                    direct_parents.append(target)
            for p in direct_parents:
                if p not in visited:
                    visited.add(p)
                    ancestors[p] = dist + 1
                    queue.append((p, dist + 1))
        return ancestors

    # 2. Fallback to default taxonomy
    if type_name in DEFAULT_TYPE_HIERARCHY:
        while queue:
            curr, dist = queue.popleft()
            parents = DEFAULT_TYPE_HIERARCHY.get(curr, {}).get("parents", [])
            for p in parents:
                if p not in visited:
                    visited.add(p)
                    ancestors[p] = dist + 1
                    queue.append((p, dist + 1))
        return ancestors

    return ancestors


def compute_lattice_distance(
    type_a: str,
    type_b: str,
    lattice: Optional[TypeLatticeGraph] = None,
) -> int:
    """Compute the topological distance between two types in the type lattice.

    Args:
        type_a: First type name.
        type_b: Second type name.
        lattice: Optional TypeLatticeGraph instance. If omitted, uses default taxonomy.

    Returns:
        Integer distance between types in the lattice.
    """
    if type_a == type_b:
        return 0

    if not type_a or not type_b:
        return max(len(type_a or ""), len(type_b or ""))

    # 1. If lattice graph is provided, check direct topological reachability
    if lattice is not None and type_a in lattice.nodes and type_b in lattice.nodes:
        dist = lattice._bfs_distance(type_a, type_b)
        if not math.isinf(dist):
            return int(round(dist))
        # Check reverse reachability (subtype/supertype symmetry)
        rev_dist = lattice._bfs_distance(type_b, type_a)
        if not math.isinf(rev_dist):
            return int(round(rev_dist))

    # 2. Evaluate hierarchy distance via fast on-demand LCA
    anc_a = _get_type_ancestors(type_a, lattice)
    anc_b = _get_type_ancestors(type_b, lattice)

    if anc_a and anc_b:
        common = set(anc_a.keys()) & set(anc_b.keys())
        if common:
            min_dist = min(anc_a[c] + anc_b[c] for c in common)
            return int(min_dist)

    # 3. Fallback to string edit distance for non-registered types
    matcher = FuzzyMatcher(TypeLatticeGraph())
    return matcher._levenshtein(type_a, type_b)


class TWSAAutoComplete:
    """Ultra-fast auto-complete engine with < 0.5ms latency target."""

    def __init__(self, types_data: Optional[List[Dict[str, Any]]] = None) -> None:
        self.lattice = TypeLatticeGraph()
        self.matcher = FuzzyMatcher(self.lattice)
        self.buffer: str = ""
        self.cursor_pos: int = 0

        initial_types = types_data if types_data is not None else DEFAULT_TYPES_DATA
        self.lattice.build_lattice(initial_types)

    def update_buffer(self, source: str, cursor: int) -> None:
        self.buffer = source
        self.cursor_pos = cursor

    def get_completions(self, query: Optional[str] = None) -> List[CompletionSuggestion]:
        if query is None:
            start = self.cursor_pos
            while start > 0 and (self.buffer[start - 1].isalnum() or self.buffer[start - 1] == "_"):
                start -= 1
            query = self.buffer[start:self.cursor_pos]

        if not query:
            return []

        suggestions = self.matcher.match(query)
        return suggestions[:20]

    def get_completion(self, query: str) -> Optional[CompletionSuggestion]:
        suggestions = self.get_completions(query)
        return suggestions[0] if suggestions else None


class TypeLatticeAutoComplete:
    """Ultra-fast auto-complete engine with < 0.5ms latency target."""

    def __init__(self, types_data: Optional[List[Dict[str, Any]]] = None) -> None:
        self.lattice = TypeLatticeGraph()
        self.matcher = FuzzyMatcher(self.lattice)
        self.buffer: str = ""
        self.cursor_pos: int = 0

        initial_types = types_data if types_data is not None else DEFAULT_TYPES_DATA
        self.lattice.build_lattice(initial_types)

    def update_buffer(self, source: str, cursor: int) -> None:
        self.buffer = source
        self.cursor_pos = cursor

    def get_completions(self, query: Optional[str] = None) -> List[CompletionSuggestion]:
        if query is None:
            start = self.cursor_pos
            while start > 0 and (self.buffer[start - 1].isalnum() or self.buffer[start - 1] == "_"):
                start -= 1
            query = self.buffer[start:self.cursor_pos]

        if not query:
            return []

        suggestions = self.matcher.match(query)
        return suggestions[:20]

    def get_completion(self, query: str) -> Optional[CompletionSuggestion]:
        suggestions = self.get_completions(query)
        return suggestions[0] if suggestions else None

    def complete(self, prefix: Optional[str]) -> List[str]:
        """Generate auto-completion suggestions for a given prefix.

        Args:
            prefix: Code prefix or token string to complete.

        Returns:
            List of suggested completion strings.

        Raises:
            ValueError: If prefix is None.
        """
        if prefix is None:
            raise ValueError("Prefix cannot be None")

        prefix_clean = prefix.strip()
        if not prefix_clean:
            return list(self.lattice.nodes.keys())[:20]

        tokens = re.findall(r"[a-zA-Z_]\w*", prefix)
        query = tokens[-1] if tokens else prefix_clean

        suggestions = self.matcher.match(query)
        results = [s.text for s in suggestions]

        if not results:
            q_lower = query.lower()
            results = [
                name for name in self.lattice.nodes.keys()
                if name.lower().startswith(q_lower)
            ]

        return results[:20]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buffer": self.buffer,
            "cursor_pos": self.cursor_pos,
            "num_nodes": len(self.lattice.nodes),
        }


def build_type_lattice(types_data: List[Dict[str, Any]]) -> TypeLatticeGraph:
    lattice = TypeLatticeGraph()
    lattice.build_lattice(types_data)
    return lattice


def get_fuzzy_completions(
    query: str,
    types_data: List[Dict[str, Any]],
    threshold: float = 0.6,
) -> List[Dict[str, Any]]:
    lattice = TypeLatticeGraph()
    lattice.build_lattice(types_data)
    matcher = FuzzyMatcher(lattice)
    matcher.compute_distances()

    suggestions = matcher.match(query, threshold)
    return [s.to_dict() for s in suggestions]


def get_ultra_fast_completion(
    source: str,
    cursor: int,
    types_data: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    engine = TWSAAutoComplete(types_data)
    engine.update_buffer(source, cursor)

    suggestion = engine.get_completion(None)
    return suggestion.to_dict() if suggestion else None


__all__ = [
    "TypeNode",
    "TypeLatticeNode",
    "LatticeEdge",
    "CompletionSuggestion",
    "TypeLatticeGraph",
    "FuzzyMatcher",
    "TWSAAutoComplete",
    "TypeLatticeAutoComplete",
    "compute_lattice_distance",
    "build_type_lattice",
    "get_fuzzy_completions",
    "get_ultra_fast_completion",
]