"""Tier 1 Math & Invariant Tests for CADRE (Time-Travel Execution Tracer)."""

import pytest
from fault_keeper.timetravel.cadre import CADRETimeTravelTracer


class TestCADRETimeTravelTracer:
    def test_basic_mutation_and_step_reverse(self):
        tracer = CADRETimeTravelTracer(initial_state={"counter": 0, "status": "init"})

        tracer.record_mutation("counter", 1)
        tracer.record_mutation("counter", 2)
        tracer.record_mutation("status", "running")

        assert tracer.current_state["counter"] == 2
        assert tracer.current_state["status"] == "running"
        assert tracer.current_step == 3

        # Step back 1 step
        last_frame = tracer.step_backward()
        assert last_frame is not None
        assert last_frame.target == "status"
        assert tracer.current_state["status"] == "init"
        assert tracer.current_step == 2

        # Step back another step
        tracer.step_backward()
        assert tracer.current_state["counter"] == 1
        assert tracer.current_step == 1

        # Step forward
        tracer.step_forward()
        assert tracer.current_state["counter"] == 2
        assert tracer.current_step == 2

    def test_instant_jump_and_checkpoint_fidelity(self):
        tracer = CADRETimeTravelTracer()
        for i in range(1, 105):
            tracer.record_mutation(f"key_{i % 10}", i)

        final_hash = tracer.compute_state_hash()

        # Jump back to step 50
        tracer.jump_to_step(50)
        assert tracer.current_step == 50

        # Jump back to step 0
        tracer.jump_to_step(0)
        assert tracer.current_step == 0
        assert tracer.current_state == {}

        # Jump forward to final step
        tracer.jump_to_step(104)
        assert tracer.current_step == 104
        assert tracer.compute_state_hash() == final_hash

    def test_test_4_4_2_replay_trace_deterministic_bit_identical(self):
        """Test 4.4.2: Deterministic bit-identical replay of time-travel execution."""
        tracer = CADRETimeTravelTracer({"env": "prod"})
        tracer.record_mutation("account_balance", 1000)
        tracer.record_mutation("account_balance", 950)
        tracer.record_mutation("status", "debited")
        tracer.record_mutation("account_balance", 1200)

        pre_replay_hash = tracer.compute_state_hash()
        success, post_replay_hash = tracer.replay_trace()

        assert success is True
        assert pre_replay_hash == post_replay_hash
