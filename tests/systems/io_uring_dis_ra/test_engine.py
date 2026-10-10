"""Unit and invariant tests for DIS-RA Engine."""

import pytest

try:
    from fault_keeper.systems.io_uring_dis_ra.config import DISRAConfig
    from fault_keeper.systems.io_uring_dis_ra.engine import (
        BackpressureThrottler,
        CQEntry,
        IoUringEngine,
        RingBuffer,
        SQEntry,
    )
except ImportError:
    from io_uring_dis_ra.config import DISRAConfig
    from io_uring_dis_ra.engine import (
        BackpressureThrottler,
        CQEntry,
        IoUringEngine,
        RingBuffer,
        SQEntry,
    )


class TestRingBuffer:
    """Tests for zero-copy lockless ring buffer."""

    def test_push_pop_ordering(self) -> None:
        rb: RingBuffer[int] = RingBuffer(capacity=4)
        assert rb.is_empty() is True
        assert rb.push(10) is True
        assert rb.push(20) is True
        assert rb.count() == 2

        assert rb.pop() == 10
        assert rb.pop() == 20
        assert rb.is_empty() is True

    def test_full_capacity_rejection(self) -> None:
        rb: RingBuffer[int] = RingBuffer(capacity=2)
        assert rb.push(1) is True
        assert rb.push(2) is True
        assert rb.is_full() is True
        assert rb.push(3) is False


class TestIoUringEngine:
    """Tests for simulated io_uring lifecycle."""

    def test_submission_and_completion(self) -> None:
        engine = IoUringEngine(sq_entries=16, cq_entries=32)
        sqe = SQEntry(opcode=0, fd=3, addr=0x1000, len=512, user_data=99)
        assert engine.submit_sqe(sqe) is True
        assert engine.get_sq_utilization() > 0.0

        processed = engine.process_submissions()
        assert processed == 1
        assert engine.get_sq_utilization() == 0.0
        assert engine.get_cq_utilization() > 0.0

        completions = engine.reap_completions()
        assert len(completions) == 1
        assert completions[0].user_data == 99
        assert completions[0].res == 512


class TestBackpressureThrottler:
    """Tests for rate throttling and overflow avoidance."""

    def test_throttling_activates_at_threshold(self) -> None:
        engine = IoUringEngine(sq_entries=10, cq_entries=20)
        # Threshold at 80% (8 entries)
        throttler = BackpressureThrottler(engine=engine, threshold=0.80)

        for i in range(8):
            sqe = SQEntry(opcode=0, fd=1, addr=0, len=1, user_data=i)
            assert throttler.submit(sqe) is True

        # 9th submission reaches 80% utilization -> rejected!
        sqe_excess = SQEntry(opcode=0, fd=1, addr=0, len=1, user_data=999)
        assert throttler.submit(sqe_excess) is False
        assert throttler.throttled_submissions >= 1
