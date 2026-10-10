"""ath_byped_hole - Type hole analysis for TypedHole integration.

This module provides type hole detection and constraint solving capabilities
for the TypedHole synthesis system.

Author: Fault-Keeper Team
License: MIT
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
import ast


@dataclass
class TypeHole:
    """Represents a type hole in source code."""
    
    name: str
    position: tuple[int, int]  # (line, column)
    context: str = ""
    constraints: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "position": self.position,
            "context": self.context,
            "constraints": self.constraints,
        }


@dataclass
class TypeConstraint:
    """Represents a type constraint between entities."""

    lhs: str = ""
    rhs: str = ""
    operator: str = "="
    position: Optional[tuple[int, int]] = None
    variable: str = ""
    expected_type: str = ""
    inferred_type: str = ""

    def __post_init__(self) -> None:
        if self.variable and not self.lhs:
            self.lhs = self.variable
        elif self.lhs and not self.variable:
            self.variable = self.lhs
        if self.expected_type and not self.rhs:
            self.rhs = self.expected_type
        elif self.rhs and not self.expected_type:
            self.expected_type = self.rhs
        if not self.inferred_type and self.expected_type:
            self.inferred_type = self.expected_type

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "lhs": self.lhs,
            "rhs": self.rhs,
            "operator": self.operator,
            "position": self.position,
            "variable": self.variable,
            "expected_type": self.expected_type,
            "inferred_type": self.inferred_type,
        }


@dataclass
class SynthesisResult:
    """Result of type synthesis operation."""

    success: bool
    entity_schema: Dict[str, str] = field(default_factory=dict)
    substitutions: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "entity_schema": self.entity_schema,
            "substitutions": self.substitutions,
            "errors": self.errors,
        }


class TypedHoleSynthesizer:
    """Synthesizes types from source code and type hole queries.

    This class handles the core logic for:
    - Detecting type holes in source code
    - Generating type constraints
    - Solving constraints to infer missing types
    - Validating synthesized types
    """

    def __init__(self) -> None:
        """Initialize the synthesizer."""
        self._cached_results: Dict[str, SynthesisResult] = {}

    def synthesize(
        self,
        source: str,
        query: str = "infer_types",
    ) -> SynthesisResult:
        """Synthesize types from source code and query.

        Args:
            source: Source code containing type definitions.
            query: Query describing desired transformation with type holes.

        Returns:
            SynthesisResult with inferred types and substitutions.

        Raises:
            ValueError: If source is None.
        """
        if source is None:
            raise ValueError("Source code cannot be None")

        if not source.strip():
            return SynthesisResult(
                success=False,
                errors=["Source code cannot be empty"],
            )

        if not query or not query.strip():
            query = "infer_types"

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return SynthesisResult(
                success=False,
                errors=[f"Syntax error in source: {e}"],
            )

        holes = self._detect_type_holes(tree, query)
        constraints = self._generate_constraints(holes, source)
        substitutions = self._solve_constraints(constraints)
        entity_schema = self._build_entity_schema(source, holes, substitutions)

        return SynthesisResult(
            success=True,
            entity_schema=entity_schema,
            substitutions=substitutions,
        )

    def _detect_type_holes(
        self,
        tree: ast.AST,
        query: str,
    ) -> List[TypeHole]:
        """Detect type holes in AST nodes."""
        holes: List[TypeHole] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                ann_str = ast.unparse(node.annotation) if hasattr(ast, "unparse") else "Any"
                holes.append(
                    TypeHole(
                        name=node.target.id,
                        position=(getattr(node, "lineno", 1), getattr(node, "col_offset", 0)),
                        context=ann_str,
                        constraints=[f"{node.target.id}: {ann_str}"],
                    )
                )
            elif isinstance(node, ast.FunctionDef):
                ret_str = (
                    ast.unparse(node.returns)
                    if node.returns is not None and hasattr(ast, "unparse")
                    else "Any"
                )
                holes.append(
                    TypeHole(
                        name=node.name,
                        position=(getattr(node, "lineno", 1), getattr(node, "col_offset", 0)),
                        context=ret_str,
                        constraints=[f"{node.name} -> {ret_str}"],
                    )
                )

        return holes

    def _generate_constraints(
        self,
        holes: List[TypeHole],
        source: str,
    ) -> List[TypeConstraint]:
        """Generate type constraints from detected holes."""
        constraints: List[TypeConstraint] = []
        for hole in holes:
            constraint = TypeConstraint(
                lhs=hole.name,
                rhs=hole.context or "Any",
                position=hole.position,
                variable=hole.name,
                expected_type=hole.context or "Any",
                inferred_type=hole.context or "Any",
            )
            constraints.append(constraint)

        return constraints

    def _solve_constraints(
        self,
        constraints: List[TypeConstraint],
    ) -> Dict[str, str]:
        """Solve type constraints to infer substitutions."""
        substitutions: Dict[str, str] = {}
        for c in constraints:
            key = c.variable or c.lhs
            val = c.inferred_type or c.rhs or "Any"
            if key:
                substitutions[key] = val
        return substitutions

    def _build_entity_schema(
        self,
        source: str,
        holes: List[TypeHole],
        substitutions: Dict[str, str],
    ) -> Dict[str, str]:
        """Build entity schema from source and substitutions."""
        schema: Dict[str, str] = dict(substitutions)
        for hole in holes:
            if hole.name not in schema and hole.context:
                schema[hole.name] = hole.context
        return schema


def transform_dto_to_entity(
    dto_schema: Dict[str, str],
    query: Optional[str] = None,
) -> SynthesisResult:
    """Transform DTO schema to entity schema.
    
    This function converts a data transfer object (DTO) schema representation
    into an entity schema suitable for database operations.
    
    Args:
        dto_schema: Dictionary mapping field names to their types in DTO format.
        query: Optional query string providing additional context.
        
    Returns:
        SynthesisResult containing the transformed entity schema.
        
    Example:
        dto = {"id": "int", "name": "str", "email": "str"}
        result = transform_dto_to_entity(dto)
        if result.success:
            print(f"Entity schema: {result.entity_schema}")
    """
    synthesizer = TypedHoleSynthesizer()
    
    # Build source code from DTO schema
    fields = []
    for field_name, field_type in dto_schema.items():
        fields.append(f'    "{field_name}": "{field_type}"')
    
    source = f"""
class Entity:
    {chr(10).join(fields)}
"""
    
    # Use query if provided, otherwise use default
    query_to_use = query or "convert DTO to entity"
    
    return synthesizer.synthesize(source, query_to_use)


def infer_entity_from_dto(
    dto_definition: str,
    target_entity_name: Optional[str] = None,
) -> SynthesisResult:
    """Infer entity schema from DTO definition string.
    
    This function parses a DTO definition (string or code snippet) and
    infers the corresponding entity schema with proper type annotations.
    
    Args:
        dto_definition: String containing DTO definition or class body.
        target_entity_name: Optional name for the target entity class.
        
    Returns:
        SynthesisResult with inferred entity schema.
        
    Example:
        dto_def = '''
        id: int
        name: str
        email: Optional[str]
        '''
        result = infer_entity_from_dto(dto_def)
        if result.success:
            print(f"Entity: {result.entity_schema}")
    """
    
    # Parse DTO definition
    try:
        tree = ast.parse(dto_definition)
    except SyntaxError as e:
        return SynthesisResult(
            success=False,
            errors=[f"Failed to parse DTO definition: {e}"],
        )
    
    # Extract field information from AST
    fields = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    field_name = target.id
                    # Try to extract type from annotation
                    if hasattr(node, 'value') and isinstance(node.value, ast.Constant):
                        fields[field_name] = str(node.value.value)
    
    # Convert to schema format
    schema = {name: typ for name, typ in fields.items()}
    
    return SynthesisResult(
        success=True,
        entity_schema=schema,
        substitutions={},
    )


def synthesize_type(
    source: str,
    query: str = "infer_types",
) -> SynthesisResult:
    """Synthesize type from source code and query.

    This is an alias for TypedHoleSynthesizer.synthesize() for convenience.

    Args:
        source: Source code containing type definitions.
        query: Query describing desired transformation with type holes.

    Returns:
        SynthesisResult with inferred types and substitutions.
    """
    synthesizer = TypedHoleSynthesizer()
    return synthesizer.synthesize(source, query)


__all__: list[str] = [
    "TypeHole",
    "TypeConstraint", 
    "SynthesisResult",
    "TypedHoleSynthesizer",
    "synthesize_type",
    "transform_dto_to_entity",
    "infer_entity_from_dto",
]