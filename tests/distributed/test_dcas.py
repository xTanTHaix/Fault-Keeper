"""Tier 1 Math & Invariant Tests for DCAS (Distributed Chaos Simulator)."""

import pytest
from fault_keeper.distributed.dcas import DCASSimulator, NetworkPacket, NodeState


class TestDCASSimulator:
    def test_node_registration_and_validation(self):
        sim = DCASSimulator(seed=123)
        sim.register_node("node-1")
        sim.register_node("node-2")

        with pytest.raises(ValueError):
            sim.register_node("")

    def test_partition_blocks_traffic(self):
        sim = DCASSimulator(seed=42)
        sim.register_node("A")
        sim.register_node("B")

        # Prior to partition: delivery succeeds
        assert sim.send_packet("A", "B", {"op": "write", "v": 1}) is True

        # Create partition between A and B
        sim.create_partition("A", "B")
        assert sim.send_packet("A", "B", {"op": "write", "v": 2}) is False
        assert sim.send_packet("B", "A", {"op": "ack"}) is False

        # Heal partition
        sim.heal_partition("A", "B")
        assert sim.send_packet("A", "B", {"op": "write", "v": 3}) is True

    def test_test_4_4_2_deterministic_replay_bit_identical_hash(self):
        """Test 4.4.2: Deterministic Replay Bit-Identical Hash across 5 identical chaos runs."""
        hashes = []
        for _ in range(5):
            sim = DCASSimulator(seed=999)
            sim.register_node("alpha")
            sim.register_node("beta")
            sim.register_node("gamma")
            sim.set_chaos_parameters(packet_drop_rate=0.2, clock_drift_bounds=(0.001, 0.05))

            # Transmit packets
            sim.send_packet("alpha", "beta", {"msg": "hello"})
            sim.create_partition("beta", "gamma")
            sim.send_packet("beta", "gamma", {"msg": "blocked"})
            sim.send_packet("alpha", "gamma", {"msg": "ok"})
            sim.heal_partition("beta", "gamma")
            sim.send_packet("beta", "gamma", {"msg": "restored"})

            fp = sim.compute_cluster_snapshot_hash()
            hashes.append(fp)

        # All 5 deterministic hashes must be 100% bit-identical
        assert len(set(hashes)) == 1
        assert len(hashes[0]) == 64
