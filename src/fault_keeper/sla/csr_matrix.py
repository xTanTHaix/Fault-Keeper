"""CSRMatrix: Compressed Sparse Row matrix for efficient storage."""

from __future__ import annotations
import math
from typing import List, Tuple


class CSRMatrix:
    """
    Compressed Sparse Row (CSR) format for sparse matrices.
    
    Storage:
        - values: Non-zero values in row-major order
        - columns: Column index for each value
        - row_ptr: Row pointer (len = n_rows + 1)
    
    This is memory-efficient for sparse matrices and enables fast SpMV.
    """

    def __init__(self, row_ptr: List[int], values: List[float], columns: List[int]):
        """Initialize CSR matrix.
        
        Args:
            row_ptr: Row pointer array (len = n_rows + 1)
            values: Non-zero values
            columns: Column indices
        """
        self.row_ptr = row_ptr
        self.values = values
        self.columns = columns
        self.n_rows = len(row_ptr) - 1
        self.n_cols = max(columns) + 1 if columns else 0

    @classmethod
    def from_coo(
        cls,
        row_ind: List[int],
        col_ind: List[int],
        data: List[float],
        shape: Tuple[int, int]
    ) -> "CSRMatrix":
        """Convert from COO format.
        
        Args:
            row_ind: Row indices
            col_ind: Column indices
            data: Non-zero values
            shape: (n_rows, n_cols)
            
        Returns:
            CSRMatrix instance
        """
        n_rows, n_cols = shape
        
        # Initialize CSR structures
        row_ptr = [0] * (n_rows + 1)
        columns = []
        values = []
        
        # Count non-zeros per row
        row_counts = [0] * n_rows
        for r in row_ind:
            row_counts[r] += 1
        
        # Compute row pointers
        row_ptr[0] = 0
        for i in range(n_rows):
            row_ptr[i + 1] = row_ptr[i] + row_counts[i]
        
        # Fill values and columns
        col_pos = [0] * n_rows
        for r, c, v in zip(row_ind, col_ind, data):
            columns.append(c)
            values.append(v)
            col_pos[r] += 1
        
        return cls(row_ptr, values, columns)

    def to_coo(self) -> Tuple[List[int], List[int], List[float]]:
        """Convert back to COO format."""
        row_ind = []
        col_ind = []
        data = []
        
        for i in range(len(self.row_ptr) - 1):
            start = self.row_ptr[i]
            end = self.row_ptr[i + 1]
            for j in range(start, end):
                row_ind.append(i)
                col_ind.append(self.columns[j])
                data.append(self.values[j])
        
        return row_ind, col_ind, data

    def __repr__(self) -> str:
        """Return string representation."""
        nnz = len(self.values)
        return f"CSRMatrix(n_rows={self.n_rows}, n_cols={self.n_cols}, nnz={nnz})"

    @property
    def nnz(self) -> int:
        """Get number of non-zero elements."""
        return len(self.values)

    @property
    def density(self) -> float:
        """Get matrix density (nnz / (n_rows * n_cols))."""
        if self.n_rows * self.n_cols == 0:
            return 0.0
        return self.nnz / (self.n_rows * self.n_cols)

    def is_symmetric(self) -> bool:
        """Check if matrix is symmetric."""
        # Simplified check - actual implementation would compare transposed
        return True  # Placeholder


if __name__ == "__main__":
    # Test CSR creation from COO
    row_ind = [0, 0, 1, 2]
    col_ind = [1, 2, 0, 1]
    data = [1.0, 2.0, 3.0, 4.0]
    shape = (3, 3)
    
    A = CSRMatrix.from_coo(row_ind, col_ind, data, shape)
    print(A)
    print(f"Density: {A.density:.4f}")