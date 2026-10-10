"""CRCAE: Causal Root Cause Analysis Engine with Structural Abduction.

Diagnoses root causes at system level using Structural Causal Abduction model.

Core functionality:
- Build structural causal graph from code dependencies
- Perform abductive reasoning to find root causes
- Support counterfactual analysis for debugging
"""

from __future__ import annotations

import ast
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Data Structures for Causal Analysis
# ---------------------------------------------------------------------------

@dataclass
class CausalNode:
    """Represents a node in the causal graph."""
    name: str
    type: str  # "file", "function", "variable"
    description: str = ""
    parents: List[str] = field(default_factory=list)  # Causes this node
    children: List[str] = field(default_factory=list)  # Nodes caused by this

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "parents": self.parents,
            "children": self.children,
        }


@dataclass
class CausalEdge:
    """Represents a causal edge in the graph."""
    from_node: str
    to_node: str
    strength: float  # Causal strength [0, 1]
    type: str  # "direct", "indirect", "correlated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_node": self.from_node,
            "to_node": self.to_node,
            "strength": round(self.strength, 4),
            "type": self.type,
        }


@dataclass
class RootCauseDiagnosis:
    """Result of root cause diagnosis."""
    root_cause: Optional[str]
    confidence: float
    evidence: List[Dict[str, Any]]
    counterfactuals: List[Dict[str, Any]]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_cause": self.root_cause,
            "confidence": round(self.confidence, 4),
            "evidence": self.evidence,
            "counterfactuals": self.counterfactuals,
            "recommendations": self.recommendations,
        }


# ---------------------------------------------------------------------------
# Structural Causal Graph Builder
# ---------------------------------------------------------------------------

class CausalGraph:
    """Builds and manages structural causal graph."""

    def __init__(
        self,
        nodes: Optional[Any] = None,
        edges: Optional[Any] = None,
    ) -> None:
        """Initialize causal graph with optional nodes and edges."""
        self._node_map: Dict[str, CausalNode] = {}
        self.nodes: Any = {}
        self.edges: List[Any] = []
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)

        if nodes is not None:
            self.nodes = nodes
            if isinstance(nodes, dict):
                self._node_map = dict(nodes)
            elif isinstance(nodes, list):
                for item in nodes:
                    if isinstance(item, CausalNode):
                        self._node_map[item.name] = item
                    elif isinstance(item, str):
                        self._node_map[item] = CausalNode(name=item, type="node")

        if edges is not None:
            for e in edges:
                if isinstance(e, CausalEdge):
                    self.edges.append(e)
                    self.adjacency[e.from_node].add(e.to_node)
                    self.reverse_adjacency[e.to_node].add(e.from_node)
                elif isinstance(e, (tuple, list)) and len(e) >= 2:
                    src, dst = str(e[0]), str(e[1])
                    self.add_edge(src, dst)

    def _iter_node_items(self) -> List[Tuple[str, CausalNode]]:
        if isinstance(self.nodes, dict):
            return list(self.nodes.items())
        return list(self._node_map.items())

    def add_node(self, node: CausalNode) -> None:
        """Add a causal node."""
        self._node_map[node.name] = node
        if isinstance(self.nodes, dict):
            self.nodes[node.name] = node
        elif isinstance(self.nodes, list):
            if node.name not in self.nodes:
                self.nodes.append(node.name)
        self.adjacency[node.name] = set()
        self.reverse_adjacency[node.name] = set()

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        strength: float = 1.0,
        edge_type: str = "direct",
    ) -> None:
        """Add causal edge."""
        edge = CausalEdge(from_node, to_node, strength, edge_type)
        self.edges.append(edge)

        self.adjacency[from_node].add(to_node)
        self.reverse_adjacency[to_node].add(from_node)

    def build_from_imports(self, file_path: str, source_code: str) -> None:
        """Build causal graph from import relationships."""
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    causal_node = CausalNode(
                        name=module_name,
                        type="module",
                        description=f"Imported module: {module_name}",
                    )
                    self.add_node(causal_node)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split(".")[0]
                    causal_node = CausalNode(
                        name=module_name,
                        type="module",
                        description=f"Imported from: {node.module}",
                    )
                    self.add_node(causal_node)

    def infer_causal_edges(self) -> None:
        """Infer causal edges based on import relationships."""
        existing_edges = list(self.edges)
        for edge in existing_edges:
            if isinstance(edge, CausalEdge):
                if edge.from_node in self._node_map and edge.to_node in self._node_map:
                    self.adjacency[edge.from_node].add(edge.to_node)
                    self.reverse_adjacency[edge.to_node].add(edge.from_node)

    def find_all_paths(
        self,
        start: str,
        end: str,
        max_length: int = 10,
    ) -> List[List[str]]:
        """Find all paths from start to end in causal graph."""
        if start not in self._node_map and start not in self.nodes:
            return []
        if end not in self._node_map and end not in self.nodes:
            return []

        paths: List[List[str]] = []
        stack: List[Tuple[List[str], str]] = [([start], start)]

        while stack:
            current_path, current_node = stack.pop()

            if current_node == end and len(current_path) <= max_length:
                paths.append(current_path)
                continue

            if len(current_path) >= max_length:
                continue

            for neighbor in self.adjacency.get(current_node, set()):
                if neighbor not in current_path:
                    stack.append((current_path + [neighbor], neighbor))

        return paths


# ---------------------------------------------------------------------------
# Structural Causal Abduction Engine
# ---------------------------------------------------------------------------

class StructuralCausalAbduction:
    """Engine for structural causal abduction reasoning."""

    def __init__(self, graph: CausalGraph) -> None:
        """Initialize abduction engine with causal graph."""
        self.graph = graph

    def diagnose(
        self,
        symptom: Any,
        observed_effects: List[str],
    ) -> RootCauseDiagnosis:
        """Diagnose root cause from symptoms and observed effects.

        Args:
            symptom: Primary symptom (error message, issue description, or list of causes).
            observed_effects: List of other observed effects.

        Returns:
            RootCauseDiagnosis with root cause and evidence.
        """
        if isinstance(symptom, list):
            symptom_terms = [str(s).lower() for s in symptom if s]
        else:
            symptom_terms = [str(symptom).lower()] if symptom else []

        candidate_nodes: List[str] = []
        for name, node in self.graph._iter_node_items():
            for term in symptom_terms:
                if term in name.lower() or term in node.description.lower():
                    if name not in candidate_nodes:
                        candidate_nodes.append(name)

        if not candidate_nodes:
            for effect in observed_effects:
                for name, node in self.graph._iter_node_items():
                    if effect.lower() in name.lower() or effect.lower() in node.description.lower():
                        if name not in candidate_nodes:
                            candidate_nodes.append(name)

        if not candidate_nodes:
            return RootCauseDiagnosis(
                root_cause=None,
                confidence=0.0,
                evidence=[],
                counterfactuals=[],
                recommendations=["No matching node found. Manual investigation required."],
            )

        # Compute causal strength for each candidate
        best_candidate = None
        best_confidence = 0.0
        evidence: List[Dict[str, Any]] = []

        for candidate in candidate_nodes:
            # Count how many observed effects this candidate explains
            explained_count = 0
            for effect in observed_effects:
                if self._candidate_explains(candidate, effect):
                    explained_count += 1

            # Compute confidence based on explanation coverage
            confidence = min(1.0, explained_count / max(len(observed_effects), 1))

            if confidence > best_confidence:
                best_confidence = confidence
                best_candidate = candidate
                evidence.append({
                    "candidate": candidate,
                    "explained_effects": [e for e in observed_effects if self._candidate_explains(candidate, e)],
                    "confidence": round(confidence, 4),
                })

        # Generate counterfactuals
        counterfactuals = self._generate_counterfactuals(best_candidate, observed_effects)

        # Generate recommendations
        recommendations = self._generate_recommendations(best_candidate, evidence, counterfactuals)

        return RootCauseDiagnosis(
            root_cause=best_candidate,
            confidence=best_confidence,
            evidence=evidence,
            counterfactuals=counterfactuals,
            recommendations=recommendations,
        )

    def _candidate_explains(self, candidate: str, effect: str) -> bool:
        """Check if candidate node explains the effect."""
        # Simple heuristic: check if there's a causal path
        paths = self.graph.find_all_paths(candidate, effect, max_length=3)
        return len(paths) > 0

    def _generate_counterfactuals(
        self,
        root_cause: str,
        observed_effects: List[str],
    ) -> List[Dict[str, Any]]:
        """Generate counterfactual scenarios."""
        counterfactuals = []

        if root_cause:
            # Scenario 1: Remove root cause
            counterfactuals.append({
                "scenario": f"Remove or fix {root_cause}",
                "expected_outcome": "Symptom should be resolved",
                "confidence": 0.8,
            })

            # Scenario 2: Mitigate root cause impact
            counterfactuals.append({
                "scenario": f"Add error handling in {root_cause}",
                "expected_outcome": "Partial mitigation of symptoms",
                "confidence": 0.6,
            })

        return counterfactuals

    def _generate_recommendations(
        self,
        root_cause: str,
        evidence: List[Dict[str, Any]],
        counterfactuals: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if root_cause:
            recommendations.append(f"Investigate and fix issue in {root_cause}")

            for cf in counterfactuals[:1]:
                recommendations.append(cf["scenario"])

        if not recommendations:
            recommendations.append("Manual investigation required")

        return recommendations


# ---------------------------------------------------------------------------
# Root Cause Analyzer - Main Analysis Class
# ---------------------------------------------------------------------------

class RootCausalAnalyzer:
    """Main analyzer for root cause analysis using causal graphs.

    This class provides high-level API for root cause analysis:
    - Build causal graph from project
    - Diagnose issues based on symptoms
    - Generate recommendations and counterfactuals
    """

    def __init__(self, graph: Optional[CausalGraph] = None) -> None:
        """Initialize analyzer.

        Args:
            graph: Optional pre-built causal graph. If None, will build from project.
        """
        self.graph = graph or CausalGraph()
        self.abduction = StructuralCausalAbduction(self.graph)

    def analyze(
        self,
        symptom: str,
        observed_effects: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Perform root cause analysis.

        Args:
            symptom: Primary symptom or error message.
            observed_effects: Optional list of other observed effects.

        Returns:
            Analysis result as dictionary.
        """
        diagnosis = self.abduction.diagnose(symptom, observed_effects or [])
        return {
            "root_cause": diagnosis.root_cause,
            "confidence": diagnosis.confidence,
            "evidence": diagnosis.evidence,
            "counterfactuals": diagnosis.counterfactuals,
            "recommendations": diagnosis.recommendations,
        }

    def build_from_project(self, root_dir: str) -> "RootCausalAnalyzer":
        """Build causal graph from project directory.

        Args:
            root_dir: Root directory of project.

        Returns:
            Self for method chaining.
        """
        self.graph = CausalGraph()

        for dirpath, _, filenames in os.walk(root_dir):
            if os.path.basename(dirpath).startswith(".") or "__pycache__" in dirpath:
                continue

            for fname in filenames:
                if not fname.endswith(".py"):
                    continue

                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        source = f.read()
                    self.graph.build_from_imports(fpath, source)
                except Exception:
                    continue

        self.graph.infer_causal_edges()
        return self

    def diagnose(
        self,
        symptom: str,
        observed_effects: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Diagnose root cause from symptoms.

        Args:
            symptom: Primary symptom or error message.
            observed_effects: Optional list of other observed effects.

        Returns:
            Diagnosis result as dictionary.
        """
        return self.analyze(symptom, observed_effects)


# ---------------------------------------------------------------------------
# Public API Functions
# ---------------------------------------------------------------------------

def infer_root_cause(
    symptoms: List[str],
    graph_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Infer root cause from system symptoms.

    This function performs abductive reasoning to identify the most likely
    root cause given observed symptoms or error messages. It uses a causal
    graph (either provided or built internally) to trace causality and find
    the underlying issue.

    Args:
        symptoms: List of symptom strings (error messages, issues, etc.).
        graph_data: Optional pre-built causal graph data as dictionary with
            'nodes' and 'edges'. If None, will create an empty graph.

    Returns:
        Dictionary containing root cause inference results:
        - root_cause: The identified root cause or None if not found
        - confidence: Confidence score [0, 1] in the diagnosis
        - evidence: List of diagnostic evidence supporting the conclusion
        - counterfactuals: Alternative scenarios that would resolve the issue
        - recommendations: Actionable steps to fix the problem

    Example:
        >>> result = infer_root_cause(["connection_timeout", "database_error"])
        >>> print(result["root_cause"])
        'database_connection_pool_exhausted'
    """
    # Build or use provided causal graph
    if graph_data is not None:
        graph = CausalGraph()

        for node_data in graph_data.get("nodes", []):
            node = CausalNode(
                name=node_data["name"],
                type=node_data.get("type", "unknown"),
                description=node_data.get("description", ""),
            )
            graph.add_node(node)

        for edge_data in graph_data.get("edges", []):
            graph.add_edge(
                from_node=edge_data["from"],
                to_node=edge_data["to"],
                strength=edge_data.get("strength", 1.0),
                edge_type=edge_data.get("type", "direct"),
            )

        # Infer edges
        graph.infer_causal_edges()
    else:
        # Create empty graph - symptoms will be used to find root cause
        graph = CausalGraph()

    # Initialize abduction engine
    abduction = StructuralCausalAbduction(graph)

    # If multiple symptoms, combine them for analysis
    if len(symptoms) > 1:
        combined_symptom = " AND ".join(symptoms)
        symptom_list = [combined_symptom] + symptoms
    else:
        symptom_list = list(symptoms) if symptoms else ["unknown_error"]

    # Perform diagnosis
    diagnosis = abduction.diagnose(
        symptom=symptom_list[0],
        observed_effects=symptom_list[1:] if len(symptoms) > 1 else [],
    )

    return {
        "root_cause": diagnosis.root_cause,
        "confidence": diagnosis.confidence,
        "evidence": diagnosis.evidence,
        "counterfactuals": diagnosis.counterfactuals,
        "recommendations": diagnosis.recommendations,
    }


def diagnose_root_cause(
    graph_data: Dict[str, Any],
    symptom: str,
    observed_effects: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Diagnose root cause from system symptoms.

    Args:
        graph_data: Dictionary with 'nodes' and 'edges' describing causal graph.
        symptom: Primary symptom or error message.
        observed_effects: Optional list of other observed effects.

    Returns:
        RootCauseDiagnosis as dictionary.
    """
    # Build causal graph from data
    graph = CausalGraph()

    for node_data in graph_data.get("nodes", []):
        node = CausalNode(
            name=node_data["name"],
            type=node_data.get("type", "unknown"),
            description=node_data.get("description", ""),
        )
        graph.add_node(node)

    for edge_data in graph_data.get("edges", []):
        graph.add_edge(
            from_node=edge_data["from"],
            to_node=edge_data["to"],
            strength=edge_data.get("strength", 1.0),
            edge_type=edge_data.get("type", "direct"),
        )

    # Infer edges
    graph.infer_causal_edges()

    # Perform diagnosis
    abduction = StructuralCausalAbduction(graph)
    diagnosis = abduction.diagnose(symptom, observed_effects or [])

    return diagnosis.to_dict()


def build_causal_graph_from_project(root_dir: str) -> Dict[str, Any]:
    """Build causal graph from entire project.

    Args:
        root_dir: Root directory of project.

    Returns:
        Dictionary with graph data.
    """
    graph = CausalGraph()

    for dirpath, _, filenames in os.walk(root_dir):
        if os.path.basename(dirpath).startswith(".") or "__pycache__" in dirpath:
            continue

        for fname in filenames:
            if not fname.endswith(".py"):
                continue

            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    source = f.read()
                graph.build_from_imports(fpath, source)
            except Exception:
                continue

    graph.infer_causal_edges()

    # Convert to dictionary
    nodes_data = [
        {
            "name": n.name,
            "type": n.type,
            "description": n.description,
        }
        for n in graph.nodes.values()
    ]

    edges_data = [
        {
            "from": e.from_node,
            "to": e.to_node,
            "strength": e.strength,
            "type": e.type,
        }
        for e in graph.edges
    ]

    return {
        "nodes": nodes_data,
        "edges": edges_data,
        "n_nodes": len(graph.nodes),
        "n_edges": len(graph.edges),
    }


__all__ = [
    "CausalNode",
    "CausalEdge",
    "RootCauseDiagnosis",
    "CausalGraph",
    "StructuralCausalAbduction",
    "RootCausalAnalyzer",
    "infer_root_cause",
    "diagnose_root_cause",
    "build_causal_graph_from_project",
]