"""Topological Simplicial Concurrency Arbiter (TSCA) Engine.

Constructs abstract Simplicial Complexes K over multi-core concurrency state spaces,
computes boundary matrices d_k over Z_2 (GF(2)), and solves for the 1st Homology
Group H_1(K) = ker(d_1) / im(d_2) to verify deadlock-freedom (beta_1 = 0).
"""

from __future__ import annotations

import itertools
from typing import Dict, Iterable, List, Optional, Set, Tuple
import numpy as np

from .config import TSCAConfig


class SimplicialComplex:
    """Represents an abstract simplicial complex K closed under taking subsets."""

    def __init__(self) -> None:
        # Simplices mapped by dimension: {dimension: set_of_sorted_tuples}
        self._simplices: Dict[int, Set[Tuple[int, ...]]] = {0: set(), 1: set(), 2: set()}

    def add_vertex(self, v: int) -> None:
        """Add a 0-simplex (vertex) to the complex."""
        self._simplices[0].add((v,))

    def add_edge(self, u: int, v: int) -> None:
        """Add a 1-simplex (edge) and ensure its boundary 0-simplices exist."""
        if u == v:
            self.add_vertex(u)
            return
        edge = tuple(sorted((u, v)))
        self.add_vertex(u)
        self.add_vertex(v)
        self._simplices[1].add(edge)

    def add_face(self, u: int, v: int, w: int) -> None:
        """Add a 2-simplex (triangle) and its boundary edges and vertices."""
        verts = sorted({u, v, w})
        if len(verts) == 3:
            tri = (verts[0], verts[1], verts[2])
            self._simplices[2].add(tri)
            self.add_edge(verts[0], verts[1])
            self.add_edge(verts[1], verts[2])
            self.add_edge(verts[0], verts[2])
        elif len(verts) == 2:
            self.add_edge(verts[0], verts[1])
        else:
            self.add_vertex(verts[0])

    def add_triangle(self, u: int, v: int, w: int) -> None:
        """Add a 2-simplex (triangle) alias for add_face."""
        self.add_face(u, v, w)

    def add_simplex(self, simplex: Iterable[int]) -> None:
        """Add an arbitrary-dimensional simplex and ensure closure."""
        verts = sorted(set(simplex))
        dim = len(verts) - 1
        if dim < 0:
            return
        if dim not in self._simplices:
            self._simplices[dim] = set()

        simp_tuple = tuple(verts)
        self._simplices[dim].add(simp_tuple)

        # Enforce downward simplicial closure: all faces must be in complex
        for sub_dim in range(dim):
            if sub_dim not in self._simplices:
                self._simplices[sub_dim] = set()
            for face in itertools.combinations(verts, sub_dim + 1):
                self._simplices[sub_dim].add(tuple(sorted(face)))

    def get_simplices(self, dim: int) -> List[Tuple[int, ...]]:
        """Retrieve sorted list of simplices of given dimension."""
        if dim not in self._simplices:
            return []
        return sorted(list(self._simplices[dim]))

    @property
    def vertices(self) -> List[int]:
        """Return list of distinct vertex IDs."""
        return [v[0] for v in self.get_simplices(0)]

    @property
    def edges(self) -> List[Tuple[int, int]]:
        """Return list of 1-simplices (edges)."""
        return [(e[0], e[1]) for e in self.get_simplices(1)]

    @property
    def faces(self) -> List[Tuple[int, int, int]]:
        """Return list of 2-simplices (triangles)."""
        return [(f[0], f[1], f[2]) for f in self.get_simplices(2)]


class BoundaryMatrixCalculator:
    """Constructs algebraic boundary operator matrices over Z_2 (GF(2))."""

    def __init__(self, complex_k: SimplicialComplex) -> None:
        self.complex = complex_k

    def compute_boundary_matrix(self, dim: int) -> np.ndarray:
        """Compute boundary matrix d_dim: C_dim -> C_{dim-1} over GF(2).

        Columns correspond to dim-simplices, rows correspond to (dim-1)-simplices.
        """
        if dim <= 0:
            return np.zeros((0, len(self.complex.get_simplices(0))), dtype=np.uint8)

        domain = self.complex.get_simplices(dim)
        codomain = self.complex.get_simplices(dim - 1)

        num_cols = len(domain)
        num_rows = len(codomain)

        if num_cols == 0 or num_rows == 0:
            return np.zeros((num_rows, num_cols), dtype=np.uint8)

        codomain_index = {face: idx for idx, face in enumerate(codomain)}
        matrix = np.zeros((num_rows, num_cols), dtype=np.uint8)

        for col_idx, simplex in enumerate(domain):
            # Compute codimension-1 faces by omitting one vertex at a time
            for i in range(len(simplex)):
                face = simplex[:i] + simplex[i + 1 :]
                sorted_face = tuple(sorted(face))
                if sorted_face in codomain_index:
                    row_idx = codomain_index[sorted_face]
                    # In GF(2), coefficients are 1 mod 2
                    matrix[row_idx, col_idx] = (matrix[row_idx, col_idx] + 1) % 2

        return matrix


class HomologyEngine:
    """Computes simplicial homology groups and Betti numbers over GF(2)."""

    def __init__(self, complex_k: SimplicialComplex) -> None:
        self.complex = complex_k
        self.calculator = BoundaryMatrixCalculator(complex_k)

    @staticmethod
    def _rank_gf2(matrix: np.ndarray) -> int:
        """Compute matrix rank over GF(2) using Gaussian elimination mod 2."""
        if matrix.size == 0:
            return 0

        m = matrix.copy().astype(np.uint8)
        num_rows, num_cols = m.shape
        lead = 0
        rank = 0

        for r in range(num_rows):
            if lead >= num_cols:
                break
            i = r
            while i < num_rows and m[i, lead] == 0:
                i += 1
            if i == num_rows:
                lead += 1
                continue
            # Swap rows r and i
            if i != r:
                m[[r, i]] = m[[i, r]]
            # Eliminate other rows
            for j in range(num_rows):
                if j != r and m[j, lead] == 1:
                    m[j] = (m[j] ^ m[r]) % 2
            lead += 1
            rank += 1

        return rank

    def compute_first_betti(self) -> int:
        """Compute the 1st Betti number beta_1 = dim ker(d_1) - dim im(d_2).

        beta_1 >= 1 proves the presence of an uncontractible 1-cycle (deadlock cycle).
        beta_1 == 0 proves absence of circular wait dependencies.
        """
        c1 = len(self.complex.get_simplices(1))
        if c1 == 0:
            return 0

        d1 = self.calculator.compute_boundary_matrix(1)
        rank_d1 = self._rank_gf2(d1)
        dim_ker_d1 = c1 - rank_d1

        d2 = self.calculator.compute_boundary_matrix(2)
        rank_d2 = self._rank_gf2(d2)

        beta_1 = dim_ker_d1 - rank_d2
        return max(0, int(beta_1))

    def compute_betti(self, k: int) -> int:
        """Compute k-th Betti number beta_k."""
        if k == 1:
            return self.compute_first_betti()

        c_k = len(self.complex.get_simplices(k))
        if c_k == 0:
            return 0

        d_k = self.calculator.compute_boundary_matrix(k)
        rank_d_k = self._rank_gf2(d_k)
        dim_ker_d_k = c_k - rank_d_k

        d_k_plus_1 = self.calculator.compute_boundary_matrix(k + 1)
        rank_d_k_plus_1 = self._rank_gf2(d_k_plus_1)

        return max(0, int(dim_ker_d_k - rank_d_k_plus_1))

    def is_deadlock_free(self) -> bool:
        """Evaluate if the simplicial concurrency complex is strictly deadlock-free."""
        return self.compute_first_betti() == 0


class TSCAEngine:
    """High-level TSCA Engine coordinating multi-core concurrency state topology."""

    def __init__(self, config: Optional[TSCAConfig] = None) -> None:
        self.config = config or TSCAConfig()
        self.complex = SimplicialComplex()
        self.homology = HomologyEngine(self.complex)

    def register_transition(self, from_state: int, to_state: int) -> None:
        """Record an atomic state transition edge between concurrency states."""
        self.complex.add_edge(from_state, to_state)

    def fill_commuting_square(self, s0: int, s1: int, s2: int) -> None:
        """Fill a 2-simplex to represent commuting operations (contractible loop)."""
        self.complex.add_face(s0, s1, s2)

    def analyze_topology(self) -> Dict[str, object]:
        """Perform full topological analysis of the state transition complex."""
        beta_1 = self.homology.compute_first_betti()
        is_safe = beta_1 == 0
        return {
            "num_vertices": len(self.complex.vertices),
            "num_edges": len(self.complex.edges),
            "num_faces": len(self.complex.faces),
            "first_betti_number": beta_1,
            "is_deadlock_free": is_safe,
            "status": "SAFE" if is_safe else "DEADLOCK_CYCLE_DETECTED",
        }


__all__ = [
    "SimplicialComplex",
    "BoundaryMatrixCalculator",
    "HomologyEngine",
    "TSCAEngine",
]
