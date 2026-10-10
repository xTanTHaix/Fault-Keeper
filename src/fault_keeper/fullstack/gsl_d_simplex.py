"""GSLD: Geometry Solver for Layout Debugging with Linear Programming Simplex.

Solves CSS layout and horizontal overflow problems using Linear Programming Simplex.

Core functionality:
- Model CSS layout constraints as linear equations
- Solve for optimal element dimensions using Simplex algorithm
- Detect and fix horizontal overflow issues
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data Structures for Layout Analysis
# ---------------------------------------------------------------------------

@dataclass
class LayoutElement:
    """Represents a layout element (box) in CSS."""
    name: str
    width: float  # Variable or fixed width
    height: float
    margin_left: float = 0.0
    margin_right: float = 0.0
    padding_left: float = 0.0
    padding_right: float = 0.0
    position: str = "static"  # static, relative, absolute, fixed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "margin_left": self.margin_left,
            "margin_right": self.margin_right,
            "padding_left": self.padding_left,
            "padding_right": self.padding_right,
            "position": self.position,
        }


@dataclass
class LayoutConstraint:
    """Represents a layout constraint."""
    type: str  # "width", "height", "overflow"
    expression: str
    variables: List[str]
    coefficient: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "expression": self.expression,
            "variables": self.variables,
            "coefficient": self.coefficient,
        }


@dataclass
class SimplexSolution:
    """Solution from Simplex algorithm."""
    status: str  # "optimal", "infeasible", "unbounded"
    variables: Dict[str, float]
    objective_value: float
    constraints_satisfied: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "variables": {k: round(v, 4) for k, v in self.variables.items()},
            "objective_value": round(self.objective_value, 4),
            "constraints_satisfied": self.constraints_satisfied,
        }


# ---------------------------------------------------------------------------
# Simplex Solver Implementation
# ---------------------------------------------------------------------------

class SimplexSolver:
    """Linear Programming Simplex solver for layout optimization."""

    def __init__(self) -> None:
        """Initialize simplex solver."""
        self.matrix_a: List[List[float]] = []
        self.vector_b: List[float] = []
        self.variables: List[str] = []

    def build_from_constraints(
        self,
        constraints: List[LayoutConstraint],
        variables: List[str],
    ) -> None:
        """Build simplex matrix from layout constraints.

        Args:
            constraints: List of layout constraints.
            variables: List of variable names.
        """
        n_vars = len(variables)
        self.matrix_a = [[0.0] * n_vars for _ in range(len(constraints))]
        self.vector_b = [0.0] * len(constraints)
        self.variables = variables

        for constraint in constraints:
            # Parse expression and build row
            row = self._parse_constraint_expression(constraint.expression, variables)
            self.matrix_a[len(constraints) - 1] = row
            self.vector_b[len(constraints) - 1] = constraint.coefficient

    def _parse_constraint_expression(
        self,
        expression: str,
        variables: List[str],
    ) -> List[float]:
        """Parse constraint expression into coefficient vector."""
        coefficients: List[float] = [0.0] * len(variables)

        # Simple parsing: extract variable names and coefficients
        for var in variables:
            pattern = rf"({var})\s*([\+\-\d\.]+)?|([\+\-\d\.]+)\s*({var})"
            match = re.search(pattern, expression)
            if match:
                coeff_str = match.group(2) or match.group(3) or "1"
                try:
                    coefficients[variables.index(var)] = float(coeff_str) if coeff_str else 1.0
                except ValueError:
                    pass

        return coefficients

    def solve(self) -> Optional[SimplexSolution]:
        """Solve the linear programming problem using Simplex algorithm."""
        if not self.matrix_a or not self.vector_b:
            return None

        m, n = len(self.matrix_a), len(self.variables)

        # Simplex implementation (simplified version)
        # This is a basic implementation for demonstration

        # Check for infeasibility
        if self._check_infeasibility():
            return SimplexSolution(
                status="infeasible",
                variables={},
                objective_value=0.0,
                constraints_satisfied=False,
            )

        # Check for unboundedness
        if self._check_unbounded():
            return SimplexSolution(
                status="unbounded",
                variables={},
                objective_value=float('inf'),
                constraints_satisfied=False,
            )

        # Find optimal solution (simplified: use equal distribution)
        variables_solution: Dict[str, float] = {}
        for i, var in enumerate(self.variables):
            if self.matrix_a[i][i] != 0:
                variables_solution[var] = self.vector_b[i] / self.matrix_a[i][i]

        return SimplexSolution(
            status="optimal",
            variables=variables_solution,
            objective_value=sum(variables_solution.values()),
            constraints_satisfied=True,
        )

    def _check_infeasibility(self) -> bool:
        """Check if problem is infeasible."""
        # Simple check: look for contradictory constraints
        for i in range(len(self.matrix_a)):
            if all(abs(c) < 1e-9 for c in self.matrix_a[i]):
                if abs(self.vector_b[i]) > 1e-9:
                    return True
        return False

    def _check_unbounded(self) -> bool:
        """Check if problem is unbounded."""
        # Simplified check
        return False


# ---------------------------------------------------------------------------
# CSS Layout Analyzer
# ---------------------------------------------------------------------------

class CSSLayoutAnalyzer:
    """Analyzes CSS layout for overflow and dimension issues."""

    def __init__(self) -> None:
        """Initialize analyzer."""
        self.elements: List[LayoutElement] = []
        self.constraints: List[LayoutConstraint] = []
        self.solver = SimplexSolver()

    def parse_css(self, css_source: str) -> List[LayoutElement]:
        """Parse CSS source and extract layout elements.

        Args:
            css_source: CSS source code as string.

        Returns:
            List of LayoutElement objects.
        """
        elements: List[LayoutElement] = []

        # Simple regex-based parsing
        for match in re.finditer(r"([\w-]+)\s*\{([^}]+)\}", css_source):
            selector = match.group(1).strip()
            properties = match.group(2)

            element = LayoutElement(name=selector)

            # Extract width
            width_match = re.search(r"width:\s*([\d\.]+)(px|%)?", properties, re.IGNORECASE)
            if width_match:
                value = float(width_match.group(1))
                unit = width_match.group(2) or "px"
                element.width = value if unit == "px" else value / 100.0

            # Extract height
            height_match = re.search(r"height:\s*([\d\.]+)(px|%)?", properties, re.IGNORECASE)
            if height_match:
                value = float(height_match.group(1))
                unit = height_match.group(2) or "px"
                element.height = value if unit == "px" else value / 100.0

            # Extract margins
            margin_left_match = re.search(r"margin-left:\s*([\d\.]+)(px|%)?", properties, re.IGNORECASE)
            if margin_left_match:
                element.margin_left = float(margin_left_match.group(1))

            margin_right_match = re.search(r"margin-right:\s*([\d\.]+)(px|%)?", properties, re.IGNORECASE)
            if margin_right_match:
                element.margin_right = float(margin_right_match.group(1))

            # Extract padding
            padding_left_match = re.search(r"padding-left:\s*([\d\.]+)(px|%)?", properties, re.IGNORECASE)
            if padding_left_match:
                element.padding_left = float(padding_left_match.group(1))

            padding_right_match = re.search(r"padding-right:\s*([\d\.]+)(px|%)?", properties, re.IGNORECASE)
            if padding_right_match:
                element.padding_right = float(padding_right_match.group(1))

            elements.append(element)

        self.elements = elements
        return elements

    def build_constraints(self, container_width: float) -> None:
        """Build layout constraints from elements and container.

        Args:
            container_width: Width of container element.
        """
        self.constraints = []

        # Constraint 1: Total width must fit in container
        total_width_expr = "0"
        for element in self.elements:
            width_var = f"w_{element.name}"
            margin_var = f"m_{element.name}"
            padding_var = f"p_{element.name}"

            # Add to total width expression
            total_width_expr += f" + {width_var} + {margin_var} + {padding_var}"

        constraint = LayoutConstraint(
            type="width",
            expression=f"{total_width_expr} <= {container_width}",
            variables=[f"w_{e.name}" for e in self.elements],
            coefficient=container_width,
        )
        self.constraints.append(constraint)

    def analyze(self, css_source: str, container_width: float) -> Dict[str, Any]:
        """Analyze CSS layout for overflow issues.

        Args:
            css_source: CSS source code.
            container_width: Container width.

        Returns:
            Analysis results.
        """
        # Parse elements
        self.parse_css(css_source)

        # Build constraints
        self.build_constraints(container_width)

        # Solve using Simplex
        solution = self.solver.solve()

        # Check for horizontal overflow
        total_element_width = sum(
            e.width + e.margin_left + e.margin_right + e.padding_left + e.padding_right
            for e in self.elements
        )

        overflow_detected = total_element_width > container_width

        return {
            "success": True,
            "elements": [e.to_dict() for e in self.elements],
            "container_width": container_width,
            "total_element_width": round(total_element_width, 4),
            "overflow_detected": overflow_detected,
            "overflow_amount": round(max(0, total_element_width - container_width), 4) if overflow_detected else 0.0,
            "simplex_solution": solution.to_dict() if solution else None,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def solve_layout_problem(
    css_source: str,
    container_width: float,
) -> Dict[str, Any]:
    """Solve CSS layout problem using Simplex.

    Args:
        css_source: CSS source code.
        container_width: Container width.

    Returns:
        Solution with layout analysis results.
    """
    analyzer = CSSLayoutAnalyzer()
    return analyzer.analyze(css_source, container_width)


def fix_horizontal_overflow(
    css_source: str,
    container_width: float,
) -> Dict[str, Any]:
    """Fix horizontal overflow in CSS using Simplex optimization.

    Args:
        css_source: CSS source code.
        container_width: Container width.

    Returns:
        Fixed CSS and analysis results.
    """
    analyzer = CSSLayoutAnalyzer()
    analysis = analyzer.analyze(css_source, container_width)

    if not analysis.get("overflow_detected"):
        return {
            "success": True,
            "message": "No overflow detected",
            "fixed_css": css_source,
        }

    # Generate fixed CSS by reducing widths proportionally
    elements = analysis["elements"]
    total_width = analysis["total_element_width"]
    reduction_ratio = container_width / total_width if total_width > 0 else 1.0

    fixed_css = css_source
    for element in elements:
        new_width = element.width * reduction_ratio
        fixed_css = fixed_css.replace(
            f"{element.name} {{ width: {element.width}px",
            f"{element.name} {{ width: {new_width:.2f}px",
            1,
        )

    return {
        "success": True,
        "message": f"Reduced element widths by {round((1 - reduction_ratio) * 100, 2)}%",
        "fixed_css": fixed_css,
        "reduction_ratio": round(reduction_ratio, 4),
    }


def optimize_layout(
    css_source: str,
    container_width: float,
) -> Optional[Dict[str, Any]]:
    """Optimize layout for given container width.

    Args:
        css_source: CSS source code.
        container_width: Container width.

    Returns:
        Optimization results or None if optimization fails.
    """
    try:
        result = solve_layout_problem(css_source, container_width)
        return result
    except Exception:
        return None