"""FSAS: Fault-Tolerant Resilient CST Parser for In-Flight Typing.

Provides Ghost CST (Concrete Syntax Tree) support to suppress error squiggles
during active typing sessions where tokens are incomplete.

Core functionality:
- Parse incomplete Python code with resilience to unfinished tokens
- Maintain CST structure even during incremental keystrokes
- Provide incremental parse results for IDE language server integration
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Ghost CST Data Structures
# ---------------------------------------------------------------------------

@dataclass
class GhostToken:
    """Represents a token that may be incomplete (Ghost token)."""
    kind: str  # e.g., "NAME", "STRING", "NUMBER", "OP"
    value: str
    start: int
    end: int

    def is_complete(self) -> bool:
        """Check if token appears complete (not truncated)."""
        return self.end < len(self.value) * 2 or not self.value.endswith('_')


@dataclass
class CSTNode:
    """Node in the Concrete Syntax Tree."""
    kind: str = ""  # e.g., "Module", "FunctionDef", "ClassDef"
    name: Optional[str] = None
    children: List[CSTNode] = field(default_factory=list)
    line: int = 0
    column: int = 0
    type: str = ""
    value: Optional[Any] = None
    left: Optional[Any] = None
    right: Optional[Any] = None

    def __post_init__(self) -> None:
        if self.type and not self.kind:
            self.kind = self.type
        elif self.kind and not self.type:
            self.type = self.kind

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation."""
        return {
            "kind": self.kind,
            "type": self.type,
            "name": self.name,
            "value": self.value,
            "left": self.left,
            "right": self.right,
            "children": [child.to_dict() for child in self.children],
            "line": self.line,
            "column": self.column,
        }


class GhostCSTParser:
    """Parser for incomplete/in-flight Python code."""

    def __init__(self, source: str = "") -> None:
        """Initialize parser with optional source code.

        Args:
            source: Optional source code to parse initially.
        """
        self.source = source
        self.ghost_nodes: Dict[str, CSTNode] = {}
        self.parse_errors: List[str] = []

    def parse(self, source: Optional[str] = None) -> GhostCST:
        """Parse source code (complete or incomplete) into Ghost CST."""
        if source is not None:
            self.source = source
            self.parse_errors = []
        ghost_nodes: Dict[str, CSTNode] = {}

        try:
            # Try normal parsing first
            tree = ast.parse(self.source)
            
            # Convert AST to our CST representation
            def ast_to_cst(node: ast.AST, parent: Optional[CSTNode] = None) -> CSTNode:
                kind_map = {
                    "Module": "Module",
                    "FunctionDef": "function",
                    "ClassDef": "class",
                    "Import": "import",
                    "Assign": "assignment",
                    "Expr": "expression",
                }
                
                node_kind = kind_map.get(type(node).__name__, type(node).__name__)
                cst_node = CSTNode(
                    kind=node_kind,
                    name=None if not hasattr(node, 'name') else getattr(node, 'name', None),
                    line=getattr(node, 'lineno', 0),
                    column=getattr(node, 'col_offset', 0),
                )

                # Process children based on node type
                if isinstance(node, ast.FunctionDef):
                    cst_node.name = node.name
                    for child in [node.args, node.body]:
                        for subnode in ast.iter_child_nodes(child):
                            child_cst = ast_to_cst(subnode, cst_node)
                            cst_node.children.append(child_cst)

                elif isinstance(node, ast.ClassDef):
                    cst_node.name = node.name
                    for item in node.body:
                        child_cst = ast_to_cst(item, cst_node)
                        cst_node.children.append(child_cst)

                return cst_node
            
            root = ast_to_cst(tree)
            ghost_nodes["root"] = root

        except SyntaxError as e:
            # Handle incomplete syntax gracefully
            self.parse_errors.append(str(e))
            
            # Create best-effort CST from partial parse
            try:
                # Try to extract what we can
                lines = self.source.split('\n')
                for i, line in enumerate(lines[:10]):  # Limit to first 10 lines
                    stripped = line.strip()
                    if stripped and not stripped.startswith('#'):
                        tokens = re.findall(r'\b\w+\b', stripped)
                        for token in tokens:
                            node = CSTNode(
                                kind="identifier",
                                name=token,
                                line=i + 1,
                                column=len(self.source[:i]) - len(self.source[:i].rstrip()) if '\n' in self.source[:i] else 0,
                            )
                            ghost_nodes[token] = node

            except Exception:
                pass

        return GhostCST(
            source=self.source,
            nodes=ghost_nodes,
            errors=self.parse_errors,
        )


class GhostCST:
    """Ghost Concrete Syntax Tree representing parsed (possibly incomplete) code."""

    def __init__(
        self,
        source: str,
        nodes: Dict[str, CSTNode],
        errors: List[str] = None,
    ) -> None:
        """Initialize Ghost CST.

        Args:
            source: Source code string.
            nodes: Dictionary mapping node names to CSTNode objects.
            errors: List of parse errors (if any).
        """
        self.source = source
        self.nodes = nodes
        self.errors = errors or []

    @property
    def is_valid(self) -> bool:
        """Check if the parsed code appears valid."""
        return len(self.errors) == 0

    def get_root(self) -> Optional[CSTNode]:
        """Get root node of the CST."""
        return self.nodes.get("root")

    def find_node(self, kind: str, name: Optional[str] = None) -> List[CSTNode]:
        """Find nodes matching criteria.

        Args:
            kind: Node kind to match (e.g., "function", "class").
            name: Optional name filter.

        Returns:
            List of matching CSTNode objects.
        """
        results = []
        for node in self.nodes.values():
            if node.kind == kind and (name is None or node.name == name):
                results.append(node)
        return results


def parse_ghost_cst(source: str) -> GhostCST:
    """Parse source code (complete or incomplete) into Ghost CST."""
    parser = GhostCSTParser(source)
    return parser.parse()


def get_completions_at_cursor(source: str, cursor_pos: int) -> List[str]:
    """Get completion suggestions at cursor position."""
    if cursor_pos >= len(source):
        return []

    # Get word before cursor
    word_start = cursor_pos
    while word_start > 0 and (source[word_start - 1].isalnum() or source[word_start - 1] == "_"):
        word_start -= 1

    prefix = source[word_start:cursor_pos]

    if not prefix:
        # No prefix - suggest common completions
        return ["self", "data", "config", "parent", "children"]

    # Check if token is incomplete
    next_char = source[cursor_pos] if cursor_pos < len(source) else None
    is_incomplete = False

    if next_char and (next_char.isalnum() or next_char == "_"):
        is_incomplete = True

    if is_incomplete:
        # Generate completions based on prefix
        suggestions = []
        for suggestion in ["self", "data", "config", "parent", "children", "methods"]:
            if suggestion.startswith(prefix):
                suggestions.append(suggestion)

        return suggestions

    return []


def get_cursor_context(source: str, cursor_pos: int) -> Dict[str, Any]:
    """Get context information at cursor position.

    Args:
        source: Source code string.
        cursor_pos: Cursor position (character offset).

    Returns:
        Dictionary with cursor context including word, line, and token info.
    """
    if cursor_pos >= len(source):
        return {
            "word": "",
            "line": 0,
            "column": 0,
            "token_type": None,
        }

    # Get current line and column
    lines_before = source[:cursor_pos].count('\n')
    col_in_line = len(source.rsplit('\n', 1)[0]) if '\n' in source[:cursor_pos] else cursor_pos

    # Get word at cursor
    word_start = cursor_pos
    while word_start > 0 and (source[word_start - 1].isalnum() or source[word_start - 1] == "_"):
        word_start -= 1

    word_end = cursor_pos
    while word_end < len(source) and (source[word_end].isalnum() or source[word_end] == "_"):
        word_end += 1

    word = source[word_start:word_end]

    return {
        "word": word,
        "line": lines_before + 1,
        "column": col_in_line,
        "context_window": source[max(0, cursor_pos - 50):cursor_pos + 50],
    }


__all__: list[str] = [
    "GhostToken",
    "CSTNode", 
    "GhostCSTParser",
    "GhostCST",
    "parse_ghost_cst",
    "get_completions_at_cursor",
    "get_cursor_context",
]
