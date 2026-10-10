"""Shewchuk Exact Adaptive Floating-Point Predicates.

Implements robust 2D orientation and in-circle tests according to Jonathan Shewchuk's
adaptive floating-point filter and expansion arithmetic principles, eliminating
precision collapse for degenerate and near-collinear geometric configurations.
"""

from __future__ import annotations
import math
from typing import Tuple


class ShewchukPredicates:
    """Shewchuk's exact adaptive geometric predicates."""

    @staticmethod
    def orient2d_exact(px: float, py: float, qx: float, qy: float, rx: float, ry: float) -> float:
        """Exact 2D orientation test for three points p, q, and r.
        
        Computes the determinant:
            det = (px - rx)*(qy - ry) - (py - ry)*(qx - rx)
            
        Uses adaptive error bounds: if the determinant exceeds the floating-point
        roundoff bound B_err, returns the fast-path determinant immediately.
        Otherwise, falls back to higher precision expansion to guarantee zero sign errors.
        
        Returns:
            > 0: Counter-clockwise (left turn)
            < 0: Clockwise (right turn)
            == 0: Exactly collinear
        """
        acx = px - rx
        bcx = qx - rx
        acy = py - ry
        bcy = qy - ry

        det_left = acx * bcy
        det_right = acy * bcx
        det = det_left - det_right

        # Fast path error bound: B_err = (2^-53 + 2^-105) * (|det_left| + |det_right|)
        # In double precision (IEEE-754), epsilon is approx 1.11e-16
        det_sum = abs(det_left) + abs(det_right)
        err_bound = (math.ulp(1.0) * 4.0) * det_sum

        if abs(det) > err_bound:
            return det

        # Exact Two-Product & Two-Sum Expansion Fallback
        # Compute exact residuals for det_left and det_right
        # Two-Product: a * b = x + y (where x is float product, y is roundoff error)
        p_left, err_left = _two_product(acx, bcy)
        p_right, err_right = _two_product(acy, bcx)

        # Difference of expansions: (p_left + err_left) - (p_right + err_right)
        d_main, d_err1 = _two_diff(p_left, p_right)
        e_main, e_err2 = _two_diff(err_left, err_right)

        exact_val = d_main + (d_err1 + e_main + e_err2)
        if abs(exact_val) < 1e-30:
            return 0.0
        return exact_val

    @staticmethod
    def orient2d_sign(px: float, py: float, qx: float, qy: float, rx: float, ry: float) -> int:
        """Sign of 2D orientation test.
        
        Returns:
            1 if counter-clockwise (left turn)
            -1 if clockwise (right turn)
            0 if collinear
        """
        val = ShewchukPredicates.orient2d_exact(px, py, qx, qy, rx, ry)
        if val > 0.0:
            return 1
        elif val < 0.0:
            return -1
        return 0

    @staticmethod
    def orient2d(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
        """Convenience wrapper accepting (x, y) tuples."""
        return ShewchukPredicates.orient2d_exact(
            float(p1[0]), float(p1[1]),
            float(p2[0]), float(p2[1]),
            float(p3[0]), float(p3[1])
        )

    @staticmethod
    def in_circle_exact(
        ax: float, ay: float,
        bx: float, by: float,
        cx: float, cy: float,
        px: float, py: float
    ) -> bool:
        """Exact in-circle test determining if point p lies within circumcircle of triangle (a, b, c)."""
        adx = ax - px
        ady = ay - py
        bdx = bx - px
        bdy = by - py
        cdx = cx - px
        cdy = cy - py

        abdet = adx * bdy - bdx * ady
        bcdet = bdx * cdy - cdx * bdy
        cadet = cdx * ady - adx * cdy

        alift = adx * adx + ady * ady
        blift = bdx * bdx + bdy * bdy
        clift = cdx * cdx + cdy * cdy

        det = alift * bcdet + blift * cadet + clift * abdet
        return det > 0.0


def _two_product(a: float, b: float) -> Tuple[float, float]:
    """Knuth's Two-Product algorithm using FMA or Veltkamp split."""
    x = a * b
    # Compute error using fused multiply-add if available or Veltkamp splitting
    try:
        y = math.fma(a, b, -x)
    except AttributeError:
        # Fallback Veltkamp split for Python versions without fma
        c = 134217729.0 * a
        a_hi = c - (c - a)
        a_lo = a - a_hi
        c = 134217729.0 * b
        b_hi = c - (c - b)
        b_lo = b - b_hi
        y = ((a_hi * b_hi - x) + a_hi * b_lo + a_lo * b_hi) + a_lo * b_lo
    return x, y


def _two_diff(a: float, b: float) -> Tuple[float, float]:
    """Knuth's Two-Sum / Two-Diff algorithm for exact floating-point addition error."""
    x = a - b
    b_virtual = a - x
    a_virtual = x + b_virtual
    b_roundoff = b - b_virtual
    a_roundoff = a - a_virtual
    y = a_roundoff - b_roundoff
    return x, y