"""SpMV: Sparse Matrix-Vector Multiplication."""

from __future__ import annotations
import math


def spmv(A_csr, x: list[float]) -> list[float]:
    """
    Compute y = A·x for CSR matrix A and vector x.
    
    Args:
        A_csr: CSRMatrix instance
        x: Input vector (len = n_cols)
        
    Returns:
        Output vector y (len = n_rows)
    """
    n_rows = len(A_csr.row_ptr) - 1
    y = [0.0] * n_rows
    
    for i in range(n_rows):
        start = A_csr.row_ptr[i]
        end = A_csr.row_ptr[i + 1]
        
        y[i] = sum(
            A_csr.values[j] * x[A_csr.columns[j]]
            for j in range(start, end)
        )
    
    return y


if __name__ == "__main__":
    # Test SpMV
    from fault_keeper.sla.csr_matrix import CSRMatrix
    
    row_ind = [0, 0, 1, 2]
    col_ind = [1, 2, 0, 1]
    data = [1.0, 2.0, 3.0, 4.0]
    shape = (3, 3)
    
    A = CSRMatrix.from_coo(row_ind, col_ind, data, shape)
    x = [1.0, 2.0, 3.0]
    
    y = spmv(A, x)
    print(f"A·x = {y}")