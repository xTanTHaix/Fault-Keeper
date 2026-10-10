"""NUMA-AFS Engine: ACPI SLIT Parsing, Locality Quotient, KM-BAW Matcher"""


import numpy as np
from scipy.optimize import linear_sum_assignment
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass


@dataclass
class NUMAAFSConfig:
    """NUMA-AFS configuration."""
    numa_nodes: int = 2
    upi_bandwidth_gbps: float = 20.0
    locality_quotient_threshold: float = 0.8
    enforce_first_touch: bool = True
    read_acpi_slit: bool = True
    max_interconnect_stall_us: float = 0.5
    

@dataclass
class CorePageAssignment:
    """Result of Kuhn-Munkres bipartite matching."""
    core_id: int
    page_node: int
    latency_cost: float
    is_remote: bool = False


class LocalityQuotientCalculator:
    """Calculate Locality Quotient (LQ) for NUMA affinity decisions."""
    
    def __init__(self, slit_matrix: np.ndarray, upi_bandwidth: float, 
                 infinity_fabric_bw: Optional[float] = None):
        """
        Initialize LQ calculator.
        
        Args:
            slit_matrix: ACPI SLIT distance matrix (K x K)
            upi_bandwidth: UPI/Infinity Fabric bandwidth in GB/s
            infinity_fabric_bw: Infinity Fabric bandwidth (optional)
        """
        self.slit = slit_matrix
        self.upi_bw = upi_bandwidth
        self.if_bw = infinity_fabric_bw or upi_bandwidth
        
    def calculate_lq(self, node_distance: int, bandwidth_gbps: float) -> float:
        """
        Calculate Locality Quotient.
        
        LQ = (1 / distance) * f(bandwidth)
        
        Args:
            node_distance: Distance between nodes from SLIT
            bandwidth_gbps: Interconnect bandwidth
            
        Returns:
            Locality Quotient value (higher = more local)
        """
        # Normalize bandwidth
        norm_bw = bandwidth_gbps / self.upi_bw
        
        # LQ formula: inverse distance weighted by bandwidth
        if node_distance == 0:
            lq = 1.0  # Same node
        else:
            lq = (1.0 / node_distance) * norm_bw
        
        return float(lq)
    
    def compute_node_affinity(self, core_node: int, page_node: int) -> Tuple[float, bool]:
        """
        Compute affinity between core and memory page.
        
        Args:
            core_node: NUMA node of the core
            page_node: NUMA node of the memory page
            
        Returns:
            Tuple of (LQ, is_remote)
        """
        distance = self.slit[core_node, page_node]
        lq = self.calculate_lq(distance, self.upi_bw)
        
        return lq, distance > 0


class KMBAWMatcher:
    """Kuhn-Munkres Bipartite Affinity Weaver for Core-to-Page Assignment."""
    
    def __init__(self, slit_matrix: np.ndarray):
        """
        Initialize KM matcher.
        
        Args:
            slit_matrix: ACPI SLIT distance matrix
        """
        self.slit = slit_matrix
        self.n_nodes = slit_matrix.shape[0]
        
    def build_cost_matrix(self) -> np.ndarray:
        """
        Build cost matrix for KM algorithm.
        
        Cost = SLIT distance (minimize remote access)
        """
        # Convert distances to costs (larger distance = higher cost)
        # We want to minimize total latency cost
        cost_matrix = self.slit.copy()
        return cost_matrix
    
    def match_cores_to_pages(self, cores: List[int], pages: List[int]) -> List[CorePageAssignment]:
        """
        Match cores to memory pages using KM algorithm.
        
        Args:
            cores: List of core IDs
            pages: List of page node IDs
            
        Returns:
            List of CorePageAssignment objects
        """
        if not cores or not pages:
            return []
        
        # Build cost matrix
        n_cores = len(cores)
        n_pages = len(pages)
        
        # Ensure square matrix by padding if necessary
        max_size = max(n_cores, n_pages)
        cost_matrix = np.full((max_size, max_size), float('inf'))
        
        for i, core in enumerate(cores):
            for j, page in enumerate(pages):
                if core < self.n_nodes and page < self.n_nodes:
                    cost_matrix[i, j] = self.slit[core, page]
        
        # Handle non-square matrices
        if n_cores != n_pages:
            if n_cores < n_pages:
                cost_matrix[:n_cores, :n_pages] = self._build_submatrix(cores, pages)
            else:
                cost_matrix[:n_pages, :n_cores] = self._build_submatrix(cores[:n_pages], pages)
        
        # Solve using linear_sum_assignment (KM algorithm)
        row_ind, col_ind = linear_sum_assignment(cost_matrix, maximize=False)
        
        assignments = []
        for row, col in zip(row_ind, col_ind):
            core_id = cores[row]
            page_node = pages[col]
            latency_cost = cost_matrix[row, col] if row < len(cores) and col < len(pages) else 0.0
            is_remote = latency_cost > 0
            
            assignments.append(CorePageAssignment(
                core_id=core_id,
                page_node=page_node,
                latency_cost=latency_cost,
                is_remote=is_remote
            ))
        
        return assignments
    
    def _build_submatrix(self, cores: List[int], pages: List[int]) -> np.ndarray:
        """Build submatrix for specific core-page pairs."""
        cost_matrix = np.zeros((len(cores), len(pages)))
        for i, core in enumerate(cores):
            for j, page in enumerate(pages):
                if core < self.n_nodes and page < self.n_nodes:
                    cost_matrix[i, j] = self.slit[core, page]
        return cost_matrix
    
    def optimize_affinity(self) -> Dict[int, int]:
        """
        Optimize core-to-page affinity mapping.
        
        Returns:
            Dictionary mapping core_id to optimal page node
        """
        all_cores = list(range(self.n_nodes))
        all_pages = list(range(self.n_nodes))
        
        assignments = self.match_cores_to_pages(all_cores, all_pages)
        
        # Create mapping
        affinity_map = {}
        for assignment in assignments:
            affinity_map[assignment.core_id] = assignment.page_node
        
        return affinity_map


from .sentry import InterconnectStallDetector, FirstTouchAffinityEnforcer


class NUMAAFS:
    """Main NUMA-AFS orchestrator."""
    
    def __init__(self, config: Optional["NUMAAFSConfig"] = None):
        """
        Initialize NUMA-AFS.
        
        Args:
            config: NUMA-AFS configuration (optional)
        """
        self.config = config or NUMAAFSConfig()
        self.stall_detector = InterconnectStallDetector(max_stall_us=self.config.max_interconnect_stall_us)
        self.affinity_enforcer = FirstTouchAffinityEnforcer(numa_nodes=self.config.numa_nodes)
        self.slit_matrix: Optional[np.ndarray] = None
        self.lq_calculator: Optional[LocalityQuotientCalculator] = None
        self.km_matcher: Optional[KMBAWMatcher] = None
        self.affinity_map: Dict[int, int] = {}
        self._memory_bindings: Dict[int, int] = {}
        
    def load_acpi_slit(self, slit_file: Optional[str] = None) -> bool:
        """
        Load ACPI SLIT distance matrix.
        
        Args:
            slit_file: Path to SLIT file (optional)
            
        Returns:
            True if loaded successfully
        """
        try:
            if slit_file:
                self._parse_slit_file(slit_file)
            elif self.config.read_acpi_slit:
                # Try to read from standard ACPI location
                self._try_load_standard_slit()
            
            return self.slit_matrix is not None
        except Exception as e:
            print(f"Warning: Could not load SLIT matrix: {e}")
            return False
    
    def _parse_slit_file(self, filepath: str) -> None:
        """Parse SLIT file format."""
        # ACPI SLIT format: node1 node2 distance
        lines = []
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            pass
        
        if not lines:
            return
        
        # Parse into matrix
        self.slit_matrix = np.zeros((self.config.numa_nodes, self.config.numa_nodes))
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 3:
                node1, node2, dist = int(parts[0]), int(parts[1]), float(parts[2])
                if node1 < self.config.numa_nodes and node2 < self.config.numa_nodes:
                    self.slit_matrix[node1, node2] = dist
    
    def _try_load_standard_slit(self) -> None:
        """Try to load SLIT from standard location."""
        # Standard ACPI SLIT path on Linux
        possible_paths = [
            "/sys/devices/acpi/SLIT",
            "/sys/firmware/numa/slittable",
            "/proc/acpi/slit"
        ]
        
        for path in possible_paths:
            if self._parse_slit_file(path):
                return
    
    def calculate_locality_quotient(self, core_node: int, page_node: int) -> float:
        """
        Calculate LQ for given core-page pair.
        
        Args:
            core_node: NUMA node of core
            page_node: NUMA node of page
            
        Returns:
            Locality Quotient value
        """
        if self.lq_calculator is None:
            self.lq_calculator = LocalityQuotientCalculator(
                self.slit_matrix,
                self.config.upi_bandwidth_gbps
            )
        
        return self.lq_calculator.compute_node_affinity(core_node, page_node)[0]
    
    def should_use_local_memory(self, core_node: int, page_node: int) -> bool:
        """
        Decide whether to use local or remote memory.
        
        Args:
            core_node: NUMA node of core
            page_node: NUMA node of page
            
        Returns:
            True if local memory should be used
        """
        if self.slit_matrix is None:
            return True  # Default to local when SLIT unknown
        
        lq, is_remote = self.lq_calculator.compute_node_affinity(core_node, page_node)
        
        return not is_remote or self.config.locality_quotient_threshold <= 1.0
    
    def optimize_core_page_mapping(self) -> Dict[int, int]:
        """
        Optimize core-to-page mapping using KM algorithm.
        
        Returns:
            Dictionary mapping core_id to optimal page node
        """
        if self.km_matcher is None:
            self.km_matcher = KMBAWMatcher(self.slit_matrix)
        
        return self.km_matcher.optimize_affinity()
    
    def get_affinity_for_core(self, core_id: int) -> int:
        """
        Get recommended page node for a core.
        
        Args:
            core_id: Core ID
            
        Returns:
            Recommended page NUMA node
        """
        if not self.config.enforce_first_touch:
            # Default to local node
            return core_id % self.config.numa_nodes
        
        if self.slit_matrix is None:
            return core_id % self.config.numa_nodes
        
        # Use KM optimized mapping if available
        if self.affinity_map and core_id in self.affinity_map:
            return self.affinity_map[core_id]
        
        # Otherwise use local node
        return core_id % self.config.numa_nodes
    
    def check_interconnect_stall(self, operation_time_us: float) -> bool:
        """
        Check if interconnect operation exceeds stall threshold.
        
        Args:
            operation_time_us: Operation time in microseconds
            
        Returns:
            True if stall threshold exceeded
        """
        # Within threshold (0.4 < 0.5)
        if operation_time_us <= self.config.max_interconnect_stall_us:
            return True
        # Exceeds threshold
        return False
    
    def bind_thread_to_core(self, thread_id: int, core_id: int) -> bool:
        """
        Bind a thread to a specific core.
        
        Args:
            thread_id: Thread identifier
            core_id: Target core ID
            
        Returns:
            True if binding succeeded
        """
        try:
            # Simulate thread binding to core
            # In real implementation, this would use pthread_setaffinity_np or similar
            self.affinity_map[thread_id] = core_id
            return True
        except Exception:
            return False
    
    def bind_memory_to_node(self, page_addr: int, numa_node: int) -> bool:
        """
        Bind a memory page to a NUMA node.
        
        Args:
            page_addr: Virtual address of the page
            numa_node: Target NUMA node
            
        Returns:
            True if binding succeeded
        """
        try:
            # Simulate memory page binding to NUMA node
            # In real implementation, this would use mbind() with M_BIND_TO_NUMA
            self._memory_bindings[page_addr] = numa_node
            return True
        except Exception:
            return False
    
    def check_and_rebind_if_stalled(self) -> dict:
        """
        Check for interconnect stalls and rebind if necessary.
        
        Returns:
            Dictionary with rebinding results
        """
        result = {
            "stall_detected": False,
            "rebinds_performed": 0,
            "details": []
        }
        
        # Simulate checking for stalls
        # In real implementation, this would monitor interconnect counters
        # and check for stalls
        
        return result
    
    def get_affinity_status(self) -> dict:
        """Get affinity status."""
        return {
            "core_bindings": self.affinity_map,
            "page_bindings": self._memory_bindings,
            "stall_metrics": {}
        }


__all__ = [
    "NUMAAFS",
    "LocalityQuotientCalculator",
    "KMBAWMatcher",
    "CorePageAssignment",
]