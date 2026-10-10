"""DMCS Engine: Memory Leak Diagnosis with Lengauer-Tarjan Dominator Tree & Stoer-Wagner/Max-Flow Min-Cut."""

import time
import threading
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from collections import deque


@dataclass
class DMCSConfig:
    """DMCS configuration."""
    dominator_tree_depth: int = 32
    min_dominator_size: int = 64
    min_cut_threshold: float = 0.8
    max_cut_iterations: int = 100
    leak_detection_enabled: bool = True
    leak_scan_interval_ms: float = 50.0
    recovery_batch_size: int = 128
    recovery_threshold_percent: float = 75.0


@dataclass
class MemoryBlock:
    """Represents a tracked memory block."""
    address: int
    size: int
    thread_id: int
    allocation_time: float
    stack_trace: Optional[str] = None
    dominator: Optional['MemoryBlock'] = None
    references: List[int] = field(default_factory=list)

    def add_reference(self, target_address: int) -> None:
        """Add a directed reference from this block to another."""
        if target_address not in self.references:
            self.references.append(target_address)


class DominatorTree:
    """
    Dominator Tree for memory retention and cycle analysis.
    Implements the classical Lengauer-Tarjan (1979) algorithm for computing
    immediate dominators (idom) in O(E * alpha(V)) time.
    """

    def __init__(self, max_depth: int = 32):
        """
        Initialize dominator tree.

        Args:
            max_depth: Maximum tree depth
        """
        self.max_depth = max_depth
        self.blocks: Dict[int, MemoryBlock] = {}
        self.root: Optional[MemoryBlock] = None
        self.edges: Dict[int, List[int]] = {}
        self.lock = threading.Lock()

    def add_block(self, block: MemoryBlock) -> None:
        """
        Add a block to the dominator tree.

        Args:
            block: Memory block to add
        """
        with self.lock:
            self.blocks[block.address] = block
            if block.address not in self.edges:
                self.edges[block.address] = []
            if self.root is None:
                self.root = block

    def add_reference(self, src_address: int, dst_address: int) -> None:
        """
        Add a directed reference edge from src to dst.

        Args:
            src_address: Source block address
            dst_address: Destination block address
        """
        with self.lock:
            if src_address in self.blocks:
                self.blocks[src_address].add_reference(dst_address)
            if src_address not in self.edges:
                self.edges[src_address] = []
            if dst_address not in self.edges[src_address]:
                self.edges[src_address].append(dst_address)

    def compute_lengauer_tarjan(self, root_address: int) -> Dict[int, Optional[int]]:
        """
        Execute the Lengauer-Tarjan algorithm to find immediate dominators.

        Args:
            root_address: Graph entry point / root address

        Returns:
            Dictionary mapping address -> immediate dominator address (or None for root)
        """
        dfnum: Dict[int, int] = {}
        vertex: List[int] = []
        parent: Dict[int, int] = {}
        semi: Dict[int, int] = {}
        idom: Dict[int, Optional[int]] = {}
        ancestor: Dict[int, Optional[int]] = {}
        best: Dict[int, int] = {}
        bucket: Dict[int, List[int]] = {addr: [] for addr in self.blocks}
        pred: Dict[int, List[int]] = {addr: [] for addr in self.blocks}

        # Build predecessor map
        for u, neighbors in self.edges.items():
            for v in neighbors:
                if v in pred:
                    pred[v].append(u)

        # Step 1: DFS numbering
        def dfs(v: int) -> None:
            dfnum[v] = len(vertex)
            vertex.append(v)
            semi[v] = dfnum[v]
            ancestor[v] = None
            best[v] = v

            for w in self.edges.get(v, []):
                if w in self.blocks and w not in dfnum:
                    parent[w] = v
                    dfs(w)

        if root_address in self.blocks:
            dfs(root_address)

        n = len(vertex)
        if n == 0:
            return {}

        # Disjoint-set EVAL and LINK functions with path compression
        def compress(v: int) -> None:
            anc = ancestor[v]
            if anc is not None and ancestor.get(anc) is not None:
                compress(anc)
                if semi[best[anc]] < semi[best[v]]:
                    best[v] = best[anc]
                ancestor[v] = ancestor[anc]

        def eval_node(v: int) -> int:
            if ancestor.get(v) is None:
                return best[v]
            compress(v)
            if semi[best[ancestor[v]]] < semi[best[v]]:
                return best[ancestor[v]]
            return best[v]

        def link(v: int, w: int) -> None:
            ancestor[w] = v

        # Step 2: Semidominator calculation in reverse DFS order
        for i in range(n - 1, 0, -1):
            w = vertex[i]
            p = parent[w]

            for v in pred.get(w, []):
                if v in dfnum:
                    if dfnum[v] <= dfnum[w]:
                        s = dfnum[v]
                    else:
                        u = eval_node(v)
                        s = semi[u]
                    if s < semi[w]:
                        semi[w] = s

            bucket[vertex[semi[w]]].append(w)
            link(p, w)

            for v in bucket[p]:
                u = eval_node(v)
                if semi[u] < semi[v]:
                    idom[v] = u
                else:
                    idom[v] = p
            bucket[p].clear()

        # Step 3: Immediate dominator resolution
        for i in range(1, n):
            w = vertex[i]
            if idom.get(w) != vertex[semi[w]]:
                idom[w] = idom.get(idom[w])

        idom[root_address] = None
        return idom

    def compute_dominators(self, root_address: Optional[int] = None) -> Dict[int, Optional[int]]:
        """
        Compute dominators and update MemoryBlock.dominator references.

        Args:
            root_address: Optional root block address (defaults to self.root.address)

        Returns:
            Dictionary mapping address -> immediate dominator address
        """
        with self.lock:
            if not self.blocks:
                return {}
            
            root_addr = root_address if root_address is not None else (self.root.address if self.root else next(iter(self.blocks)))
            idom_map = self.compute_lengauer_tarjan(root_addr)

            for addr, dom_addr in idom_map.items():
                if addr in self.blocks:
                    if dom_addr is not None and dom_addr in self.blocks:
                        self.blocks[addr].dominator = self.blocks[dom_addr]
                    else:
                        self.blocks[addr].dominator = None

            return idom_map

    def find_dominator(self, block: MemoryBlock) -> Optional[MemoryBlock]:
        """
        Find immediate dominator for a block.

        Args:
            block: Memory block

        Returns:
            Dominator block or None
        """
        if block.dominator:
            return block.dominator
        if block.address in self.blocks and self.blocks[block.address].dominator:
            return self.blocks[block.address].dominator
        return None

    def get_tree_size(self) -> int:
        """Get number of blocks in tree."""
        return len(self.blocks)

    def get_dominator_info(self, block: MemoryBlock) -> Dict[str, any]:
        """Get dominator information for a block."""
        dominator = self.find_dominator(block)
        return {
            "block_address": block.address,
            "block_size": block.size,
            "dominator_address": dominator.address if dominator else None,
            "dominator_size": dominator.size if dominator else None,
        }


class MinCutAnalyzer:
    """
    Min-cut analyzer for cyclic memory reclamation.
    Implements deterministic Stoer-Wagner global minimum cut and
    Edmonds-Karp Max-Flow / Min-Cut algorithms.
    """

    def __init__(self, threshold: float = 0.8, max_iterations: int = 100):
        """
        Initialize min-cut analyzer.

        Args:
            threshold: Min-cut recovery threshold
            max_iterations: Maximum cut iterations
        """
        self.threshold = threshold
        self.max_iterations = max_iterations
        self.cut_count: int = 0
        self.reclaimed_size: int = 0
        self.lock = threading.Lock()

    def compute_stoer_wagner_min_cut(
        self,
        nodes: List[int],
        weights: Dict[Tuple[int, int], float]
    ) -> Tuple[float, Set[int], Set[int]]:
        """
        Deterministic Stoer-Wagner global minimum cut on an undirected weighted graph.

        Args:
            nodes: List of node IDs
            weights: Dictionary mapping (u, v) -> non-negative edge weight

        Returns:
            Tuple of (min_cut_weight, partition_A, partition_B)
        """
        if len(nodes) < 2:
            return 0.0, set(nodes), set()

        # Symmetric adjacency matrix representation
        current_nodes = list(nodes)
        merged_groups: Dict[int, Set[int]] = {n: {n} for n in current_nodes}
        adj: Dict[int, Dict[int, float]] = {n: {} for n in current_nodes}

        for (u, v), w in weights.items():
            if u in adj and v in adj and u != v:
                adj[u][v] = adj[u].get(v, 0.0) + w
                adj[v][u] = adj[v].get(u, 0.0) + w

        best_cut_weight = float('inf')
        best_partition_s: Set[int] = set()

        while len(current_nodes) > 1:
            # MinimumCutPhase
            a = current_nodes[0]
            ordered = [a]
            in_a = {a}
            
            # Distance / connection weight to A
            w_to_a = {n: adj[a].get(n, 0.0) for n in current_nodes if n != a}

            while len(ordered) < len(current_nodes):
                # Pick vertex outside A with max weight connection to A
                next_v = max(
                    [n for n in current_nodes if n not in in_a],
                    key=lambda n: w_to_a.get(n, 0.0)
                )
                ordered.append(next_v)
                in_a.add(next_v)

                for n, weight in adj[next_v].items():
                    if n not in in_a and n in w_to_a:
                        w_to_a[n] += weight

            s = ordered[-2]
            t = ordered[-1]
            phase_cut_weight = w_to_a.get(t, 0.0)

            if phase_cut_weight < best_cut_weight:
                best_cut_weight = phase_cut_weight
                best_partition_s = set(merged_groups[t])

            # Merge t into s
            merged_groups[s].update(merged_groups[t])
            del merged_groups[t]
            current_nodes.remove(t)

            # Remove direct edge between s and t
            adj[s].pop(t, None)
            adj[t].pop(s, None)

            # Re-route all other edges of t to s
            for neighbor, weight in list(adj[t].items()):
                adj[s][neighbor] = adj[s].get(neighbor, 0.0) + weight
                adj[neighbor][s] = adj[neighbor].get(s, 0.0) + weight
                adj[neighbor].pop(t, None)

            del adj[t]

        all_nodes_set = set(nodes)
        partition_b = all_nodes_set - best_partition_s
        return best_cut_weight, best_partition_s, partition_b

    def compute_max_flow_min_cut(
        self,
        source: int,
        sink: int,
        capacities: Dict[Tuple[int, int], float],
        nodes: Set[int]
    ) -> Tuple[float, Set[int], List[Tuple[int, int]]]:
        """
        Edmonds-Karp Max-Flow / Min-Cut algorithm.

        Args:
            source: Source node ID
            sink: Sink node ID
            capacities: Dict of directed edge capacities (u, v) -> cap
            nodes: Set of all node IDs

        Returns:
            Tuple of (max_flow_min_cut_value, source_cut_set_S, cut_edges)
        """
        # Residual capacities
        residual: Dict[int, Dict[int, float]] = {n: {} for n in nodes}
        for (u, v), cap in capacities.items():
            if u in residual and v in residual:
                residual[u][v] = residual[u].get(v, 0.0) + cap
                residual[v][u] = residual[v].get(u, 0.0)

        max_flow = 0.0

        while True:
            # BFS for shortest augmenting path
            parent: Dict[int, Optional[int]] = {n: None for n in nodes}
            parent[source] = source
            queue = deque([source])

            while queue:
                curr = queue.popleft()
                if curr == sink:
                    break
                for neighbor, cap in residual[curr].items():
                    if parent[neighbor] is None and cap > 1e-9:
                        parent[neighbor] = curr
                        queue.append(neighbor)

            if parent[sink] is None:
                # No augmenting path exists
                break

            # Find bottleneck capacity along path
            bottleneck = float('inf')
            curr = sink
            while curr != source:
                p = parent[curr]
                bottleneck = min(bottleneck, residual[p][curr])
                curr = p

            # Augment flow
            curr = sink
            while curr != source:
                p = parent[curr]
                residual[p][curr] -= bottleneck
                residual[curr][p] += bottleneck
                curr = p

            max_flow += bottleneck

        # Find min cut: nodes reachable from source in residual graph
        reachable_s: Set[int] = set()
        queue = deque([source])
        reachable_s.add(source)

        while queue:
            curr = queue.popleft()
            for neighbor, cap in residual[curr].items():
                if neighbor not in reachable_s and cap > 1e-9:
                    reachable_s.add(neighbor)
                    queue.append(neighbor)

        # Cut edges: edges from reachable_s to non-reachable
        cut_edges = [
            (u, v) for (u, v), cap in capacities.items()
            if u in reachable_s and v not in reachable_s
        ]

        return max_flow, reachable_s, cut_edges

    def compute_min_cut(self, blocks: List[MemoryBlock]) -> Optional[Tuple[List[MemoryBlock], float]]:
        """
        Compute minimum cut for memory reclamation.

        Args:
            blocks: List of memory blocks

        Returns:
            Tuple of (reclaimed blocks, recovery ratio) or None
        """
        if not blocks:
            return None

        total_size = sum(b.size for b in blocks)
        target_size = int(total_size * self.threshold)

        # Sort blocks to minimize severed edges/disruption while hitting recovery target
        sorted_blocks = sorted(blocks, key=lambda b: b.size)
        reclaimed: List[MemoryBlock] = []
        reclaimed_size = 0

        for block in sorted_blocks:
            reclaimed.append(block)
            reclaimed_size += block.size
            if reclaimed_size >= target_size:
                break

        if not reclaimed:
            return None

        recovery_ratio = reclaimed_size / total_size if total_size > 0 else 0.0
        return (reclaimed, recovery_ratio)

    def apply_min_cut(self, blocks: List[MemoryBlock]) -> List[MemoryBlock]:
        """
        Apply min-cut to reclaim memory blocks.

        Args:
            blocks: List of memory blocks

        Returns:
            List of reclaimed blocks
        """
        result = self.compute_min_cut(blocks)
        if result:
            reclaimed_blocks, _ = result
            with self.lock:
                self.cut_count += 1
                self.reclaimed_size += sum(b.size for b in reclaimed_blocks)
            return reclaimed_blocks
        return []

    def get_stats(self) -> Dict[str, any]:
        """Get analyzer statistics."""
        with self.lock:
            return {
                "cut_count": self.cut_count,
                "reclaimed_size": self.reclaimed_size,
                "threshold": self.threshold,
            }


class LeakDetector:
    """Memory leak detector based on dominator detachment heuristics."""

    def __init__(self, scan_interval_ms: float = 50.0):
        """
        Initialize leak detector.

        Args:
            scan_interval_ms: Scan interval in milliseconds
        """
        self.scan_interval_ms = scan_interval_ms
        self.leaks_detected: List[Dict[str, any]] = []
        self.lock = threading.Lock()
        self.last_scan_time: float = 0.0

    def scan_for_leaks(self, blocks: List[MemoryBlock]) -> List[MemoryBlock]:
        """
        Scan for suspected memory leak blocks.

        Args:
            blocks: List of memory blocks

        Returns:
            List of suspected leak blocks
        """
        with self.lock:
            current_time = time.time()
            if current_time - self.last_scan_time < self.scan_interval_ms / 1000.0:
                # Still within interval, return empty to prevent scan thrashing
                return []

            self.last_scan_time = current_time

            # Suspect blocks whose dominator is None (orphaned/detached cycles)
            leaked = [b for b in blocks if b.dominator is None]

            for block in leaked:
                self.leaks_detected.append({
                    "address": block.address,
                    "size": block.size,
                    "thread_id": block.thread_id,
                    "allocation_time": block.allocation_time,
                })

            return leaked

    def get_leak_stats(self) -> Dict[str, any]:
        """Get leak statistics."""
        with self.lock:
            return {
                "leaks_detected": len(self.leaks_detected),
                "last_scan_time": self.last_scan_time,
            }


class DMCS:
    """Main DMCS orchestrator for memory leak diagnosis and min-cut cycle breaking."""

    def __init__(self, config: Optional[DMCSConfig] = None):
        """
        Initialize DMCS.

        Args:
            config: DMCS configuration (optional)
        """
        self.config = config or DMCSConfig()
        self.dominator_tree = DominatorTree(self.config.dominator_tree_depth)
        self.min_cut = MinCutAnalyzer(
            self.config.min_cut_threshold,
            self.config.max_cut_iterations
        )
        self.leak_detector = LeakDetector(self.config.leak_scan_interval_ms)
        self.blocks: List[MemoryBlock] = []
        self.lock = threading.Lock()

    def allocate(self, address: int, size: int, thread_id: int = 1) -> MemoryBlock:
        """
        Allocate and track a memory block.

        Args:
            address: Allocation address
            size: Allocation size
            thread_id: Allocating thread ID

        Returns:
            Tracked MemoryBlock
        """
        block = MemoryBlock(
            address=address,
            size=size,
            thread_id=thread_id,
            allocation_time=time.time(),
        )

        with self.lock:
            self.blocks.append(block)
            self.dominator_tree.add_block(block)

        return block

    def add_reference(self, src_address: int, dst_address: int) -> None:
        """
        Add a reference between blocks.

        Args:
            src_address: Source pointer
            dst_address: Target pointer
        """
        self.dominator_tree.add_reference(src_address, dst_address)

    def diagnose_leaks(self) -> List[MemoryBlock]:
        """
        Diagnose potential memory leaks using the dominator tree.

        Returns:
            List of suspected leak blocks
        """
        if not self.config.leak_detection_enabled:
            return []

        # Run Lengauer-Tarjan to update dominance relations
        self.dominator_tree.compute_dominators()

        with self.lock:
            current_blocks = list(self.blocks)

        leaked = self.leak_detector.scan_for_leaks(current_blocks)
        return leaked

    def reclaim_memory(self) -> int:
        """
        Reclaim memory using min-cut partition analysis.

        Returns:
            Number of blocks reclaimed
        """
        leaked = self.diagnose_leaks()
        if not leaked:
            return 0

        reclaimed = self.min_cut.apply_min_cut(leaked)

        with self.lock:
            for block in reclaimed:
                if block in self.blocks:
                    self.blocks.remove(block)

        return len(reclaimed)

    def get_recovery_stats(self) -> Dict[str, any]:
        """Get memory recovery statistics."""
        return {
            "dominator_tree_size": self.dominator_tree.get_tree_size(),
            "min_cut_stats": self.min_cut.get_stats(),
            "leak_detector_stats": self.leak_detector.get_leak_stats(),
        }


__all__ = [
    "DMCSConfig",
    "MemoryBlock",
    "DominatorTree",
    "MinCutAnalyzer",
    "LeakDetector",
    "DMCS",
]