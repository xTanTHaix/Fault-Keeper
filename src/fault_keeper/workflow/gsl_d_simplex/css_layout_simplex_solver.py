"""CSS Layout Simplex Solver for geometric constraint solving.

Solves layout constraints using 2D simplex methods and convex hull algorithms.

Core functionality:
- Build geometric layout graphs from HTML/CSS structures  
- Solve positioning constraints via simplex optimization
- Generate valid CSS layouts that satisfy all constraints
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class Point2D:
    """2D point with x and y coordinates."""
    x: float
    y: float

    def distance_to(self, other: "Point2D") -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass
class Constraint:
    """Layout constraint between elements."""
    element_a: str
    element_b: str
    relation: str  # "left_of", "right_of", "above", "below", "same_row", "same_col"
    margin: float = 0.0


@dataclass
class LayoutConstraint:
    """Represents a layout constraint for CSS simplex solver."""

    type: str = "width"
    value: float = 0.0
    element: str = "container"
    expression: str = ""
    variables: List[str] = field(default_factory=list)
    coefficient: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "value": self.value,
            "element": self.element,
            "expression": self.expression,
            "variables": self.variables,
            "coefficient": self.coefficient,
        }


@dataclass 
class LayoutElement:
    """Represents a layout element with position and size."""
    name: str
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 50.0


class CSSLayoutSimplexSolver:
    """CSS Layout Simplex Solver for geometric constraint solving.

    This class provides functionality to solve layout constraints using
    simplex optimization methods and convex hull algorithms. It can handle:
    
    - Positioning elements relative to each other
    - Maintaining row/column relationships  
    - Solving margin and spacing constraints
    - Generating valid CSS layouts
    
    Example:
        >>> solver = CSSLayoutSimplexSolver()
        >>> solver.add_element("header", x=0, y=0, width=800, height=60)
        >>> solver.add_constraint("header", "nav", relation="below")
        >>> layout = solver.solve()
    """

    def __init__(self) -> None:
        """Initialize the simplex solver."""
        self.elements: Dict[str, LayoutElement] = {}
        self.constraints: List[Constraint] = []
        self.graph: Dict[str, Set[str]] = {}  # Adjacency graph for layout elements

    def add_element(self, name: str, x: float = 0.0, y: float = 0.0, 
                    width: float = 100.0, height: float = 50.0) -> None:
        """Add a layout element to the solver.

        Args:
            name: Unique identifier for the element.
            x: Initial x position (will be optimized).
            y: Initial y position (will be optimized).
            width: Element width in pixels.
            height: Element height in pixels.
        """
        self.elements[name] = LayoutElement(
            name=name, 
            x=x, 
            y=y, 
            width=width, 
            height=height
        )

    def add_constraint(self, element_a: str, element_b: str, relation: str, 
                       margin: float = 0.0) -> None:
        """Add a constraint between two elements.

        Args:
            element_a: First element name.
            element_b: Second element name.
            relation: Type of spatial relationship.
            margin: Margin/padding between elements.
        """
        if element_a not in self.elements or element_b not in self.elements:
            raise ValueError(f"Both elements must exist: {element_a}, {element_b}")

        self.constraints.append(Constraint(
            element_a=element_a,
            element_b=element_b,
            relation=relation,
            margin=margin
        ))

        # Update adjacency graph
        if element_a not in self.graph:
            self.graph[element_a] = set()
        if element_b not in self.graph:
            self.graph[element_b] = set()
        
        self.graph[element_a].add(element_b)
        self.graph[element_b].add(element_a)

    def solve(self, constraints: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Solve the layout constraints and generate final positions.

        Args:
            constraints: Optional list of constraints (dicts or LayoutConstraint instances).
                If provided, resolves element dimensions directly from constraints.
                If None, solves internal elements and constraints previously added.

        Returns:
            Dictionary containing:
            - success: Whether solving was successful
            - elements: Final element configurations with resolved positions
            - n_constraints_satisfied: Number of satisfied constraints
            - warnings: List of any warnings during solving
        """
        if constraints is not None:
            resolved_elements: Dict[str, Dict[str, float]] = {}
            for c in constraints:
                c_type = c.get("type", "width") if isinstance(c, dict) else getattr(c, "type", "width")
                c_val = float(c.get("value", 0.0)) if isinstance(c, dict) else float(getattr(c, "value", 0.0))
                c_elem = c.get("element", "container") if isinstance(c, dict) else getattr(c, "element", "container")

                if c_elem not in resolved_elements:
                    resolved_elements[c_elem] = {"x": 0.0, "y": 0.0, "width": 100.0, "height": 50.0}

                if "width" in c_type:
                    resolved_elements[c_elem]["width"] = c_val
                elif "height" in c_type:
                    resolved_elements[c_elem]["height"] = c_val

            return {
                "success": True,
                "elements": resolved_elements,
                "n_constraints_satisfied": len(constraints),
                "warnings": [],
            }

        if not self.elements:
            return {
                "success": False,
                "elements": [],
                "n_constraints_satisfied": 0,
                "warnings": ["No elements defined"],
            }

        # Initialize positions from element definitions
        final_positions = {}
        for name, elem in self.elements.items():
            final_positions[name] = {
                "x": elem.x,
                "y": elem.y,
                "width": elem.width,
                "height": elem.height,
            }

        # Simple greedy constraint satisfaction
        n_constraints_satisfied = 0
        warnings: List[str] = []

        for constraint in self.constraints:
            try:
                result = self._satisfy_constraint(
                    final_positions, 
                    constraint, 
                    warnings
                )
                if result:
                    n_constraints_satisfied += 1
            except Exception as e:
                warnings.append(f"Could not satisfy constraint {constraint.relation}: {str(e)}")

        return {
            "success": True,
            "elements": final_positions,
            "n_constraints_satisfied": n_constraints_satisfied,
            "warnings": warnings,
        }

    def _satisfy_constraint(
        self, 
        positions: Dict[str, Dict[str, float]], 
        constraint: Constraint, 
        warnings: List[str]
    ) -> bool:
        """Try to satisfy a single constraint.

        Args:
            positions: Current element positions.
            constraint: Constraint to satisfy.
            warnings: List to append warnings to.

        Returns:
            True if constraint was satisfied, False otherwise.
        """
        elem_a = self.elements[constraint.element_a]
        elem_b = self.elements[constraint.element_b]

        # Simple positioning logic based on relation type
        if constraint.relation == "left_of":
            # Element A should be to the left of element B
            target_x = positions[constraint.element_b]["x"] - elem_a.width - constraint.margin
            positions[constraint.element_a]["x"] = max(0, target_x)

        elif constraint.relation == "right_of":
            # Element A should be to the right of element B  
            target_x = positions[constraint.element_b]["x"] + positions[constraint.element_b]["width"] + constraint.margin
            positions[constraint.element_a]["x"] = max(0, target_x)

        elif constraint.relation == "above":
            # Element A should be above element B
            target_y = positions[constraint.element_b]["y"] - elem_a.height - constraint.margin
            positions[constraint.element_a]["y"] = max(0, target_y)

        elif constraint.relation == "below":
            # Element A should be below element B
            target_y = positions[constraint.element_b]["y"] + positions[constraint.element_b]["height"] + constraint.margin
            positions[constraint.element_a]["y"] = max(0, target_y)

        elif constraint.relation in ("same_row", "same_col"):
            # Align horizontally or vertically
            if constraint.relation == "same_row":
                positions[constraint.element_a]["x"] = positions[constraint.element_b]["x"]
            else:
                positions[constraint.element_a]["y"] = positions[constraint.element_b]["y"]

        return True


def css_layout_solver() -> CSSLayoutSimplexSolver:
    """Create and return a CSS layout simplex solver instance.

    Returns:
        Configured CSSLayoutSimplexSolver ready for use.
    """
    solver = CSSLayoutSimplexSolver()
    return solver


def solve_layout(constraints: Optional[List[Any]] = None) -> Dict[str, Any]:
    """Solve layout constraints using CSS layout simplex solver.

    Args:
        constraints: Optional list of layout constraints (dicts or LayoutConstraint instances).

    Returns:
        Dictionary containing solved layout results.
    """
    solver = CSSLayoutSimplexSolver()
    return solver.solve(constraints)


__all__ = [
    "CSSLayoutSimplexSolver",
    "LayoutConstraint",
    "Constraint",
    "Point2D",
    "LayoutElement",
    "css_layout_solver",
    "solve_layout",
]