"""Randomized SVD: Halko-Martinsson-Tropp algorithm.

Implements randomized low-rank singular value decomposition for sparse matrices:
    A ≈ U · Σ · V^T
reducing complexity from O(mn^2) to O(mn log k).
"""

from __future__ import annotations
import math
import random
from typing import List, Optional, Tuple


def randomized_svd(
    A_csr,
    k: int = 20,
    n_iter: int = 2,
    random_seed: Optional[int] = None
) -> Tuple[List[List[float]], List[float], List[List[float]]]:
    """Compute randomized SVD decomposition: A ≈ U·Σ·V^T.
    
    Algorithm (Halko et al., SIAM Review 2011):
        1. Generate random Gaussian test matrix Ω (n_cols × (k+p))
        2. Compute Sample Matrix Y = A·Ω using SpMV
        3. Orthogonalize columns of Y to obtain Q (m × (k+p))
        4. Project A into low-rank subspace B = Q^T · A ((k+p) × n)
        5. Compute standard SVD on small matrix B
        6. Compute left singular vectors U = Q · U_small
        
    Args:
        A_csr: CSRMatrix instance with dimensions (m, n)
        k: Target rank (number of singular values/vectors)
        n_iter: Power iterations for singular value decay acceleration
        random_seed: Seed for Gaussian generator
        
    Returns:
        Tuple of (U, sigma, Vt):
            U: Left singular vectors (m × k)
            sigma: Singular values in descending order (k,)
            Vt: Right singular vectors (k × n)
    """
    if random_seed is not None:
        random.seed(random_seed)

    m = A_csr.n_rows
    n = A_csr.n_cols
    target_k = min(k, m, n)

    if target_k <= 0 or m == 0 or n == 0:
        return [], [], []

    # Oversampling parameter p
    p = min(5, min(m, n) - target_k)
    l = target_k + p

    # Step 1: Draw Gaussian random matrix Omega of size (n x l)
    # Omega_cols[j] represents the j-th test vector of length n
    Omega_cols = [[random.gauss(0.0, 1.0) for _ in range(n)] for _ in range(l)]

    # Step 2: Sample matrix Y = A * Omega
    # Y_cols[j] has length m
    Y_cols = [_spmv_vector(A_csr, Omega_cols[j]) for j in range(l)]

    # Power iterations: Y = (A * A^T)^q * Y
    for _ in range(n_iter):
        # Multiply by A^T: Z_j = A^T * Y_j (length n)
        Z_cols = [_spmv_transpose(A_csr, Y_cols[j]) for j in range(l)]
        # Multiply by A: Y_j = A * Z_j (length m)
        Y_cols = [_spmv_vector(A_csr, Z_cols[j]) for j in range(l)]

    # Step 3: QR decomposition on Y to obtain orthonormal basis Q (columns Q_cols of length m)
    Q_cols = _orthonormalize_columns(Y_cols, m)
    actual_l = len(Q_cols)
    if actual_l == 0:
        return [[0.0] * target_k for _ in range(m)], [0.0] * target_k, [[0.0] * n for _ in range(target_k)]

    # Step 4: Form small matrix B = Q^T * A of dimension (actual_l x n)
    # Row i of B is Q_cols[i]^T * A = (A^T * Q_cols[i])^T
    B = []
    for i in range(actual_l):
        row_i = _spmv_transpose(A_csr, Q_cols[i])
        B.append(row_i)

    # Step 5: SVD of small matrix B (actual_l x n)
    # Compute B * B^T of size (actual_l x actual_l)
    BBt = [[0.0] * actual_l for _ in range(actual_l)]
    for i in range(actual_l):
        for j in range(i, actual_l):
            dot = sum(B[i][c] * B[j][c] for c in range(n))
            BBt[i][j] = dot
            BBt[j][i] = dot

    # Eigendecomposition of BBt (Jacobi algorithm) to get singular values and U_small
    eigenvalues, U_small = _jacobi_eigen(BBt)

    # Singular values sigma = sqrt(max(0, eigenvalue))
    sigma_full = [math.sqrt(max(0.0, ev)) for ev in eigenvalues]

    # Sort in descending order
    idx_sorted = sorted(range(actual_l), key=lambda idx: sigma_full[idx], reverse=True)
    take_k = min(target_k, len(idx_sorted))

    sigma = [sigma_full[idx_sorted[i]] for i in range(take_k)]

    # Step 6: Form U = Q * U_small[:, idx_sorted[:take_k]] (dimension m x take_k)
    U = [[0.0] * take_k for _ in range(m)]
    for r in range(m):
        for c in range(take_k):
            orig_col = idx_sorted[c]
            U[r][c] = sum(Q_cols[i][r] * U_small[i][orig_col] for i in range(actual_l))

    # Form V^T = (1/sigma) * U_small^T * B
    Vt = [[0.0] * n for _ in range(take_k)]
    for c in range(take_k):
        s = sigma[c]
        orig_col = idx_sorted[c]
        if s > 1e-12:
            for j in range(n):
                # v_j = sum_i (U_small[i][orig_col] * B[i][j]) / s
                val = sum(U_small[i][orig_col] * B[i][j] for i in range(actual_l)) / s
                Vt[c][j] = val
        else:
            # Degenerate singular value
            for j in range(n):
                Vt[c][j] = 0.0

    return U, sigma, Vt


def _spmv_vector(A_csr, x: List[float]) -> List[float]:
    """Matrix-vector product y = A * x."""
    m = A_csr.n_rows
    y = [0.0] * m
    for i in range(m):
        start = A_csr.row_ptr[i]
        end = A_csr.row_ptr[i + 1]
        y[i] = sum(A_csr.values[j] * x[A_csr.columns[j]] for j in range(start, end))
    return y


def _spmv_transpose(A_csr, y: List[float]) -> List[float]:
    """Matrix-transpose vector product x = A^T * y."""
    n = A_csr.n_cols
    x = [0.0] * n
    for i in range(A_csr.n_rows):
        start = A_csr.row_ptr[i]
        end = A_csr.row_ptr[i + 1]
        y_val = y[i]
        for j in range(start, end):
            col = A_csr.columns[j]
            x[col] += A_csr.values[j] * y_val
    return x


def _orthonormalize_columns(cols: List[List[float]], length: int) -> List[List[float]]:
    """Modified Gram-Schmidt orthogonalization on column vectors."""
    ortho: List[List[float]] = []
    for col in cols:
        v = list(col)
        for q in ortho:
            dot = sum(v[i] * q[i] for i in range(length))
            for i in range(length):
                v[i] -= dot * q[i]
        norm = math.sqrt(sum(v[i] ** 2 for i in range(length)))
        if norm > 1e-10:
            for i in range(length):
                v[i] /= norm
            ortho.append(v)
    return ortho


def _jacobi_eigen(A: List[List[float]], max_iter: int = 50) -> Tuple[List[float], List[List[float]]]:
    """Jacobi eigenvalue algorithm for symmetric positive semi-definite matrix."""
    n = len(A)
    # V is eigenvector matrix (initially identity)
    V = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    D = [[A[i][j] for j in range(n)] for i in range(n)]

    for _ in range(max_iter):
        # Find maximum off-diagonal element
        max_val = 0.0
        p, q = 0, 1
        for i in range(n):
            for j in range(i + 1, n):
                if abs(D[i][j]) > max_val:
                    max_val = abs(D[i][j])
                    p, q = i, j

        if max_val < 1e-12:
            break

        # Compute Jacobi rotation angle
        diff = D[q][q] - D[p][p]
        if abs(D[p][q]) < 1e-15:
            t = 0.0
        else:
            phi = diff / (2.0 * D[p][q])
            t = 1.0 / (abs(phi) + math.sqrt(phi * phi + 1.0))
            if phi < 0.0:
                t = -t

        c = 1.0 / math.sqrt(t * t + 1.0)
        s = t * c

        # Apply rotation to D
        d_pp = D[p][p]
        d_qq = D[q][q]
        d_pq = D[p][q]

        D[p][p] = c * c * d_pp - 2.0 * s * c * d_pq + s * s * d_qq
        D[q][q] = s * s * d_pp + 2.0 * s * c * d_pq + c * c * d_qq
        D[p][q] = 0.0
        D[q][p] = 0.0

        for r in range(n):
            if r != p and r != q:
                d_rp = D[r][p]
                d_rq = D[r][q]
                D[r][p] = c * d_rp - s * d_rq
                D[p][r] = D[r][p]
                D[r][q] = s * d_rp + c * d_rq
                D[q][r] = D[r][q]

        # Accumulate eigenvectors in V
        for r in range(n):
            v_rp = V[r][p]
            v_rq = V[r][q]
            V[r][p] = c * v_rp - s * v_rq
            V[r][q] = s * v_rp + c * v_rq

    eigenvalues = [D[i][i] for i in range(n)]
    return eigenvalues, V