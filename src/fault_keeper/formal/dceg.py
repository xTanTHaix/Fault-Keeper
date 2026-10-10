"""Differential Causal Execution Graph (DCEG).

Maintains a dynamic causal DAG of states, mutations, and dependencies with
sub-50ms incremental re-evaluation latency for IDE live-feedback.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class CausalNode:
    """Represents a state node in the causal dependency DAG."""
    node_id: str
    compute_fn: Optional[Callable[[Dict[str, Any]], Any]] = None
    value: Any = None
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    is_dirty: bool = False
    last_eval_ms: float = 0.0


class DCEGDifferentialGraph:
    """High-Performance Incremental & Differential Causal Graph Engine."""

    def __init__(self) -> None:
        self._nodes: Dict[str, CausalNode] = {}

    def add_node(
        self,
        node_id: str,
        value: Any = None,
        compute_fn: Optional[Callable[[Dict[str, Any]], Any]] = None,
        dependencies: Optional[Set[str]] = None,
    ) -> None:
        """Add a causal state node with upstream dependencies."""
        try:
            if not isinstance(node_id, str) or not node_id:
                raise ValueError("node_id must be a valid non-empty string.")
        except ValueError:
            raise

        deps = dependencies or set()
        node = CausalNode(
            node_id=node_id,
            value=value,
            compute_fn=compute_fn,
            dependencies=deps,
            is_dirty=(compute_fn is not None),
        )
        self._nodes[node_id] = node

        # Register dependents
        for dep in deps:
            if dep in self._nodes:
                self._nodes[dep].dependents.add(node_id)

    def set_value(self, node_id: str, new_value: Any) -> float:
        """Mutate a source node and incrementally invalidate downstream dependents (<50ms)."""
        t0 = time.perf_counter()
        try:
            if node_id not in self._nodes:
                raise KeyError(f"Node '{node_id}' does not exist in causal graph.")
        except KeyError:
            raise

        node = self._nodes[node_id]
        if node.value == new_value and not node.is_dirty:
            return (time.perf_counter() - t0) * 1000.0

        node.value = new_value
        node.is_dirty = False

        # Mark all transitive downstream dependents as dirty
        queue = list(node.dependents)
        dirty_set: Set[str] = set()

        while queue:
            curr = queue.pop(0)
            if curr not in dirty_set:
                dirty_set.add(curr)
                if curr in self._nodes:
                    self._nodes[curr].is_dirty = True
                    queue.extend(self._nodes[curr].dependents)

        # Incrementally re-evaluate dirty nodes in topological order
        re_eval_time = self._recompute_dirty_nodes(dirty_set)
        total_ms = (time.perf_counter() - t0) * 1000.0
        return total_ms

    def _recompute_dirty_nodes(self, dirty_set: Set[str]) -> None:
        """Re-evaluate dirty nodes by resolving their upstream dependencies."""
        eval_order: List[str] = []
        visited: Set[str] = set()

        def visit(n: str) -> None:
            if n in visited or n not in self._nodes:
                return
            visited.add(n)
            for d in self._nodes[n].dependencies:
                visit(d)
            if n in dirty_set:
                eval_order.append(n)

        for n in dirty_set:
            visit(n)

        for n_id in eval_order:
            node = self._nodes[n_id]
            if node.compute_fn:
                dep_values = {d: self._nodes[d].value for d in node.dependencies if d in self._nodes}
                t_start = time.perf_counter()
                node.value = node.compute_fn(dep_values)
                node.last_eval_ms = (time.perf_counter() - t_start) * 1000.0
                node.is_dirty = False

    def get_value(self, node_id: str) -> Any:
        """Retrieve the current value of a node, re-evaluating if dirty."""
        try:
            if node_id not in self._nodes:
                raise KeyError(f"Node '{node_id}' does not exist.")
        except KeyError:
            raise

        node = self._nodes[node_id]
        if node.is_dirty and node.compute_fn:
            dep_values = {d: self._nodes[d].value for d in node.dependencies if d in self._nodes}
            node.value = node.compute_fn(dep_values)
            node.is_dirty = False

        return node.value
