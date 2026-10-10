"""ACDS: Anti-Unification Copy-Paste Bug Detector."""

from __future__ import annotations
import ast
import re
from typing import Set, Dict, Any


class AntiUnificationNode:
    """Generalized term from anti-unification."""
    
    def __init__(self, name: str = "", kind: str = "var", children: list = None):
        self.name = name
        self.kind = kind  # "var", "const", "binop", "func"
        self.children = children or []
        self.generic = False  # True if generalized (has holes)

    def __repr__(self) -> str:
        if self.generic:
            return f"Gen({self.name})"
        return f"{self.kind}({self.name})"


def anti_unify(t1: AntiUnificationNode, t2: AntiUnificationNode) -> AntiUnificationNode:
    """Compute anti-unification of two terms.
    
    Returns the most general term that is a specialization of both inputs.
    """
    if t1.kind != t2.kind:
        # Different kinds - create generalized node
        return AntiUnificationNode(
            name=f"{{t1={t1.name}, t2={t2.name}}}",
            kind="gen",
            children=[t1, t2],
            generic=True
        )
    
    if t1.kind == "var":
        # Variable - check if same or different
        if t1.name == t2.name:
            return t1
        else:
            # Different variables - generalize to hole
            return AntiUnificationNode(
                name="?",
                kind="hole",
                generic=True
            )
    
    if t1.kind in ("const", "binop", "func"):
        # Structural comparison
        if len(t1.children) != len(t2.children):
            return AntiUnificationNode(
                name=f"{{children_mismatch}}",
                kind="gen",
                generic=True
            )
        
        # Recursively anti-unify children
        generalized_children = [
            anti_unify(c1, c2) for c1, c2 in zip(t1.children, t2.children)
        ]
        
        result = AntiUnificationNode(
            name=t1.name,
            kind=t1.kind,
            children=generalized_children
        )
        
        # Mark as generic if any child is generic
        result.generic = any(child.generic for child in generalized_children)
        
        return result
    
    return t1


def detect_copy_paste_drift(code: str) -> list[dict]:
    """
    Detect copy-paste bugs using anti-unification.
    
    Parses code, identifies duplicated blocks, and checks for incomplete
    substitutions (variables that should change but don't).
    
    Args:
        code: Source code to analyze
        
    Returns:
        List of detected drifts with line numbers and variable names
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [{"error": str(e)}]
    
    # Find duplicated code blocks
    drifts = []
    
    # Simple heuristic: look for repeated function bodies
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    
    for i, func1 in enumerate(functions):
        for j, func2 in enumerate(functions[i+1:], i+1):
            # Compare function bodies
            body1 = get_function_body_vars(func1)
            body2 = get_function_body_vars(func2)
            
            # Find variables that appear same in both
            common_vars = set(body1.keys()) & set(body2.keys())
            
            # Check for incomplete substitution
            for var in common_vars:
                if not is_substituted(func1, func2, var):
                    drifts.append({
                        "type": "incomplete_substitution",
                        "variable": var,
                        "function1": func1.name,
                        "function2": func2.name,
                        "line1": func1.lineno,
                        "line2": func2.lineno
                    })
    
    return drifts


def get_function_body_vars(func: ast.FunctionDef) -> dict[str, str]:
    """Extract variables from function body."""
    vars = {}
    for node in ast.walk(func):
        if isinstance(node, ast.Name):
            vars[node.id] = node.id
    return vars


def is_substituted(func1: ast.FunctionDef, func2: ast.FunctionDef, var: str) -> bool:
    """Check if variable was properly substituted."""
    # Simple heuristic: check if variable appears with different values
    lines1 = get_lines_for_function(func1)
    lines2 = get_lines_for_function(func2)
    
    if not lines1 or not lines2:
        return False
    
    # Check for pattern like "x = 1" vs "x = 2"
    pattern1 = f"{var} = [0-9]+"
    pattern2 = f"{var} = [0-9]+"
    
    count1 = sum(1 for line in lines1 if re.match(pattern1, line))
    count2 = sum(1 for line in lines2 if re.match(pattern2, line))
    
    return count1 != count2


def get_lines_for_function(func: ast.FunctionDef) -> list[str]:
    """Get source code lines for function body."""
    start = func.lineno - 1
    end = func.end_lineno if hasattr(func, 'end_lineno') else start + 20
    return []  # Placeholder


if __name__ == "__main__":
    # Test copy-paste detection
    code = """
def calculate(a, b):
    result = a + b
    return result

def calculate2(a, b):
    result = a + b  # Forgot to change 'b' to 'c'
    return result
"""
    
    drifts = detect_copy_paste_drift(code)
    print(f"Detected {len(drifts)} copy-paste drifts")