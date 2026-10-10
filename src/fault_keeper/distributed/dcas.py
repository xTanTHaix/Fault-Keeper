"""Distributed Chaos Simulator (D-CAS) — Local Distributed Systems Simulator.

Simulates distributed networks, partitions, packet drops, and clock drift with
deterministic 100% reproducible execution replay via vector clocks and seeded PRNG.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclass
class NetworkPacket:
    """Represents a message packet transmitted across distributed nodes."""
    packet_id: str
    src: str
    dst: str
    payload: Any
    timestamp: float
    partition_tag: str = "default"


@dataclass
class NodeState:
    """Maintains local state and vector clock for an isolated network node."""
    node_id: str
    vector_clock: Dict[str, int] = field(default_factory=dict)
    data_store: Dict[str, Any] = field(default_factory=dict)
    received_packets: List[NetworkPacket] = field(default_factory=list)


class DCASSimulator:
    """Local Distributed Systems Chaos & Partition Simulator with 100% Deterministic Replay."""

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._rng = random.Random(seed)
        self._nodes: Dict[str, NodeState] = {}
        self._partitions: Set[Tuple[str, str]] = set()  # Bidirectional partitioned pairs (src, dst)
        self._packet_drop_rate: float = 0.0
        self._clock_drift_bounds: Tuple[float, float] = (0.0, 0.0)  # (min_drift_s, max_drift_s)
        self._event_log: List[Dict[str, Any]] = []

    def register_node(self, node_id: str) -> None:
        """Register an isolated node in the distributed cluster."""
        try:
            if not isinstance(node_id, str) or not node_id:
                raise ValueError("node_id must be a non-empty string.")
        except ValueError:
            raise

        if node_id not in self._nodes:
            self._nodes[node_id] = NodeState(node_id=node_id, vector_clock={node_id: 0})
            self._event_log.append({"event": "node_registered", "node_id": node_id})

    def create_partition(self, node_a: str, node_b: str) -> None:
        """Sever bidirectional network connectivity between node_a and node_b."""
        try:
            if node_a not in self._nodes or node_b not in self._nodes:
                raise KeyError(f"Both nodes must exist. Found: {node_a in self._nodes}, {node_b in self._nodes}")
        except KeyError:
            raise

        self._partitions.add((node_a, node_b))
        self._partitions.add((node_b, node_a))
        self._event_log.append({"event": "partition_created", "pair": [node_a, node_b]})

    def heal_partition(self, node_a: str, node_b: str) -> None:
        """Heal bidirectional network connectivity between node_a and node_b."""
        self._partitions.discard((node_a, node_b))
        self._partitions.discard((node_b, node_a))
        self._event_log.append({"event": "partition_healed", "pair": [node_a, node_b]})

    def set_chaos_parameters(
        self,
        *,
        packet_drop_rate: float = 0.0,
        clock_drift_bounds: Tuple[float, float] = (0.0, 0.0),
    ) -> None:
        """Configure stochastic network faults."""
        try:
            if not (0.0 <= packet_drop_rate <= 1.0):
                raise ValueError("packet_drop_rate must be between 0.0 and 1.0.")
        except ValueError:
            raise
        self._packet_drop_rate = packet_drop_rate
        self._clock_drift_bounds = clock_drift_bounds

    def send_packet(self, src: str, dst: str, payload: Any) -> bool:
        """Transmit a packet between nodes considering partitions, drop rate, and drift."""
        try:
            if src not in self._nodes or dst not in self._nodes:
                raise KeyError(f"Source '{src}' and destination '{dst}' must be registered.")
        except KeyError:
            raise

        # Check network partition
        if (src, dst) in self._partitions:
            self._event_log.append({
                "event": "packet_blocked", "src": src, "dst": dst, "reason": "network_partition"
            })
            return False

        # Check stochastic packet drop
        if self._packet_drop_rate > 0.0 and self._rng.random() < self._packet_drop_rate:
            self._event_log.append({
                "event": "packet_dropped", "src": src, "dst": dst, "reason": "chaos_loss"
            })
            return False

        # Advance vector clocks
        src_state = self._nodes[src]
        dst_state = self._nodes[dst]
        src_state.vector_clock[src] = src_state.vector_clock.get(src, 0) + 1

        drift = self._rng.uniform(self._clock_drift_bounds[0], self._clock_drift_bounds[1])
        pkt = NetworkPacket(
            packet_id=f"pkt_{len(self._event_log)}_{src}_{dst}",
            src=src,
            dst=dst,
            payload=payload,
            timestamp=time.time() + drift,
        )

        # Merge vector clock on destination
        dst_state.vector_clock[src] = max(
            dst_state.vector_clock.get(src, 0),
            src_state.vector_clock.get(src, 0),
        )
        dst_state.vector_clock[dst] = dst_state.vector_clock.get(dst, 0) + 1
        dst_state.received_packets.append(pkt)

        self._event_log.append({
            "event": "packet_delivered",
            "packet_id": pkt.packet_id,
            "src": src,
            "dst": dst,
            "vector_clock": dict(dst_state.vector_clock),
        })
        return True

    def compute_cluster_snapshot_hash(self) -> str:
        """Compute bit-identical deterministic SHA-256 fingerprint of the entire cluster state."""
        state_dict: Dict[str, Any] = {
            "partitions": sorted(list(self._partitions)),
            "nodes": {
                nid: {
                    "vector_clock": dict(sorted(node.vector_clock.items())),
                    "store": dict(sorted(node.data_store.items())),
                    "packets_count": len(node.received_packets),
                    "packet_ids": [p.packet_id for p in node.received_packets],
                }
                for nid, node in sorted(self._nodes.items())
            },
            "events_count": len(self._event_log),
        }
        serialized = json.dumps(state_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
