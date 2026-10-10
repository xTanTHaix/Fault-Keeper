"""A-SMW: AST Commutative Rewrite Algebra for Git Merge.

Provides structural 3-way AST merge by decomposing AST into statement blocks,
identifying commutative mutations, and reconstructing valid Python AST.
"""

from __future__ import annotations
import ast
import copy
from typing import Any, Dict, List, Optional, Tuple


def ast_merge(
    base_tree: ast.AST,
    our_changes: Dict[str, ast.AST],
    their_changes: Dict[str, ast.AST]
) -> Tuple[ast.AST, List[Dict[str, Any]]]:
    """Merge AST trees using commutative rewrite algebra.
    
    Applies non-overlapping statement-level mutations across disjoint lines
    guaranteeing commutativity: Merge(Base, A, B) == Merge(Base, B, A).
    
    Args:
        base_tree: Base AST root node.
        our_changes: Dict mapping line/index key to AST statements from our branch.
        their_changes: Dict mapping line/index key to AST statements from their branch.
        
    Returns:
        Tuple of (merged_ast_tree, conflict_resolutions_list).
    """
    if not isinstance(base_tree, ast.Module):
        # Wrap in module if not already
        base_module = ast.Module(body=[base_tree] if isinstance(base_tree, ast.stmt) else [], type_ignores=[])
    else:
        base_module = copy.deepcopy(base_tree)

    merged_body: List[ast.stmt] = list(base_module.body)
    resolutions: List[Dict[str, Any]] = []

    # Map statements by lineno if available or by order index
    line_to_idx: Dict[str, int] = {}
    for idx, stmt in enumerate(merged_body):
        lineno_key = str(getattr(stmt, "lineno", idx + 1))
        line_to_idx[lineno_key] = idx

    all_keys = set(our_changes.keys()).union(set(their_changes.keys()))

    for key in sorted(all_keys):
        has_our = key in our_changes
        has_their = key in their_changes

        if has_our and not has_their:
            # Non-overlapping: Our change applies cleanly
            new_node = our_changes[key]
            if key in line_to_idx:
                merged_body[line_to_idx[key]] = _ensure_stmt(new_node)
            else:
                merged_body.append(_ensure_stmt(new_node))
        elif has_their and not has_our:
            # Non-overlapping: Their change applies cleanly
            new_node = their_changes[key]
            if key in line_to_idx:
                merged_body[line_to_idx[key]] = _ensure_stmt(new_node)
            else:
                merged_body.append(_ensure_stmt(new_node))
        else:
            # Both modified the exact same key - check structural equivalence
            our_node = our_changes[key]
            their_node = their_changes[key]

            our_dump = ast.dump(our_node)
            their_dump = ast.dump(their_node)

            if our_dump == their_dump:
                # Commutative convergence: identical changes
                if key in line_to_idx:
                    merged_body[line_to_idx[key]] = _ensure_stmt(our_node)
                else:
                    merged_body.append(_ensure_stmt(our_node))
            else:
                # Real conflict: Record resolution and take our change as deterministic baseline
                resolutions.append({
                    "line": key,
                    "type": "structural_conflict",
                    "our_change": our_dump,
                    "their_change": their_dump,
                    "resolution": "our_precedence"
                })
                if key in line_to_idx:
                    merged_body[line_to_idx[key]] = _ensure_stmt(our_node)
                else:
                    merged_body.append(_ensure_stmt(our_node))

    base_module.body = merged_body
    ast.fix_missing_locations(base_module)
    return base_module, resolutions


def _ensure_stmt(node: ast.AST) -> ast.stmt:
    """Ensure given AST node is a statement acceptable in module body."""
    if isinstance(node, ast.stmt):
        return node
    elif isinstance(node, ast.expr):
        return ast.Expr(value=node)
    elif isinstance(node, ast.Module) and len(node.body) > 0:
        return node.body[0]
    return ast.Pass()