"""AC-SBE Engine: Auto-Cooperative Single-Threaded Blocking Event-Loop Yield Injector.

Statically analyzes Python AST for CPU-bound blocking loops within async functions,
computes complexity metrics and execution weight, and transforms AST by injecting
deterministic cooperative preemption points (`await asyncio.sleep(0)`).
"""

from __future__ import annotations

import ast
from typing import List, Optional, Set, Tuple

from .config import ACSBEConfig


class LoopCostEstimator:
    """Estimates the execution weight and computational complexity of an AST loop node."""

    def __init__(self) -> None:
        pass

    def estimate_cost(self, node: ast.AST) -> float:
        """Compute heuristic complexity score based on AST operation weights."""
        score = 0.0
        for child in ast.walk(node):
            if isinstance(child, (ast.For, ast.While)):
                score += 10.0
            elif isinstance(child, ast.Call):
                score += 5.0
            elif isinstance(child, ast.BinOp):
                score += 1.0
            elif isinstance(child, (ast.Subscript, ast.Attribute)):
                score += 1.5
            elif isinstance(child, ast.Compare):
                score += 1.0
            elif isinstance(child, ast.ListComp):
                score += 8.0
        return score


class BlockingLoopDetector:
    """Detects CPU-bound synchronous loops in async coroutines lacking yield/await points."""

    def __init__(self, cost_estimator: Optional[LoopCostEstimator] = None) -> None:
        self.cost_estimator = cost_estimator or LoopCostEstimator()

    def detect_blocking_loops(self, tree: ast.AST) -> List[ast.AST]:
        """Scan AST for loops in async functions that contain no await/yield points."""
        blocking_loops: List[ast.AST] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                for sub in ast.walk(node):
                    if sub is not node and isinstance(sub, (ast.For, ast.While)):
                        if not self._has_cooperative_yield(sub):
                            blocking_loops.append(sub)

        return blocking_loops

    def _has_cooperative_yield(self, loop_node: ast.AST) -> bool:
        """Check if loop body already contains an await or yield expression."""
        for child in ast.walk(loop_node):
            if isinstance(child, (ast.Await, ast.Yield, ast.YieldFrom)):
                return True
        return False


class AutoYieldTransformer(ast.NodeTransformer):
    """AST Transformer that injects deterministic `await asyncio.sleep(0)` into blocking loops."""

    def __init__(self, cadence: int = 100) -> None:
        super().__init__()
        self.cadence = cadence
        self._in_async = False
        self.injected_count = 0

    def transform(self, tree: ast.AST) -> ast.AST:
        """Transform AST by injecting cooperative preemption into blocking async loops."""
        self.injected_count = 0
        transformed = self.visit(tree)
        ast.fix_missing_locations(transformed)
        return transformed

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        """Track entry and exit of async coroutines."""
        prev = self._in_async
        self._in_async = True
        self.generic_visit(node)
        self._in_async = prev
        return node

    def visit_For(self, node: ast.For) -> ast.For:
        """Inspect and transform For loops."""
        self.generic_visit(node)
        if self._in_async and not self._contains_await(node):
            yield_expr = self._create_yield_call()
            node.body.append(yield_expr)
            self.injected_count += 1
        return node

    def visit_While(self, node: ast.While) -> ast.While:
        """Inspect and transform While loops."""
        self.generic_visit(node)
        if self._in_async and not self._contains_await(node):
            yield_expr = self._create_yield_call()
            node.body.append(yield_expr)
            self.injected_count += 1
        return node

    def _contains_await(self, node: ast.AST) -> bool:
        """Check if AST subtree already contains an await expression."""
        for child in ast.walk(node):
            if isinstance(child, (ast.Await, ast.Yield)):
                return True
        return False

    def _create_yield_call(self) -> ast.Expr:
        """Construct `await asyncio.sleep(0)` AST statement."""
        call_node = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="asyncio", ctx=ast.Load()),
                attr="sleep",
                ctx=ast.Load(),
            ),
            args=[ast.Constant(value=0)],
            keywords=[],
        )
        await_node = ast.Await(value=call_node)
        return ast.Expr(value=await_node)


__all__ = [
    "LoopCostEstimator",
    "BlockingLoopDetector",
    "AutoYieldTransformer",
]
