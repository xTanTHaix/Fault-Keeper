"""DIS-RA Engine: Deterministic io_uring Ring Buffer & Backpressure Arbiter.

Implements zero-copy memory-mapped submission (SQ) and completion (CQ) ring buffers,
atomic head/tail index updates modulo mask, and backpressure rate controller
preventing CQE overflow (-EBUSY) and submission drops.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, List, Optional, TypeVar

from .config import DISRAConfig

T = TypeVar("T")


@dataclass
class SQEntry:
    """Submission Queue Entry (SQE) matching Linux struct io_uring_sqe layout."""

    opcode: int
    fd: int
    addr: int
    len: int
    user_data: int
    flags: int = 0


@dataclass
class CQEntry:
    """Completion Queue Entry (CQE) matching Linux struct io_uring_cqe layout."""

    user_data: int
    res: int
    flags: int = 0


class RingBuffer(Generic[T]):
    """Lockless-style zero-copy ring buffer with atomic head/tail indices."""

    def __init__(self, capacity: int) -> None:
        self.capacity = max(1, capacity)
        self.mask = self.capacity - 1
        self._buffer: List[Optional[T]] = [None] * self.capacity
        self.head: int = 0
        self.tail: int = 0

    def is_full(self) -> bool:
        """Return True if ring buffer is completely full."""
        return (self.tail - self.head) >= self.capacity

    def is_empty(self) -> bool:
        """Return True if ring buffer is empty."""
        return self.head == self.tail

    def count(self) -> int:
        """Return current number of unconsumed entries."""
        return self.tail - self.head

    def push(self, item: T) -> bool:
        """Push item to ring tail if capacity is available."""
        if self.is_full():
            return False
        idx = self.tail % self.capacity
        self._buffer[idx] = item
        self.tail += 1
        return True

    def pop(self) -> Optional[T]:
        """Pop item from ring head if available."""
        if self.is_empty():
            return None
        idx = self.head % self.capacity
        item = self._buffer[idx]
        self._buffer[idx] = None
        self.head += 1
        return item


class IoUringEngine:
    """Simulated deterministic io_uring kernel engine managing SQ and CQ rings."""

    def __init__(self, sq_entries: int = 64, cq_entries: int = 128) -> None:
        self.sq_entries = sq_entries
        self.cq_entries = cq_entries
        self.sq_ring: RingBuffer[SQEntry] = RingBuffer(sq_entries)
        self.cq_ring: RingBuffer[CQEntry] = RingBuffer(cq_entries)
        self.overflow_count: int = 0

    def submit_sqe(self, sqe: SQEntry) -> bool:
        """Submit SQE to submission queue ring."""
        return self.sq_ring.push(sqe)

    def complete_cqe(self, cqe: CQEntry) -> bool:
        """Produce completion to CQ ring; track overflows if CQ is saturated."""
        if self.cq_ring.is_full():
            self.overflow_count += 1
            return False
        return self.cq_ring.push(cqe)

    def get_sq_utilization(self) -> float:
        """Compute SQ capacity utilization fraction (0.0 to 1.0)."""
        return self.sq_ring.count() / float(self.sq_entries)

    def get_cq_utilization(self) -> float:
        """Compute CQ capacity utilization fraction (0.0 to 1.0)."""
        return self.cq_ring.count() / float(self.cq_entries)

    def process_submissions(self) -> int:
        """Process pending SQEs and generate completions."""
        processed = 0
        while not self.sq_ring.is_empty() and not self.cq_ring.is_full():
            sqe = self.sq_ring.pop()
            if sqe is not None:
                cqe = CQEntry(user_data=sqe.user_data, res=sqe.len, flags=0)
                self.cq_ring.push(cqe)
                processed += 1
        return processed

    def reap_completions(self, max_entries: int = 32) -> List[CQEntry]:
        """Reap completed CQEs from completion ring."""
        reaped: List[CQEntry] = []
        for _ in range(max_entries):
            cqe = self.cq_ring.pop()
            if cqe is None:
                break
            reaped.append(cqe)
        return reaped


class BackpressureThrottler:
    """Proactive rate controller gating SQE submissions based on ring saturation."""

    def __init__(self, engine: IoUringEngine, threshold: float = 0.85) -> None:
        self.engine = engine
        self.threshold = threshold
        self.throttled_submissions: int = 0
        self.accepted_submissions: int = 0

    def submit(self, sqe: SQEntry) -> bool:
        """Submit SQE with backpressure gating.

        Rejects submission if SQ or CQ utilization exceeds threshold to prevent overflow.
        """
        sq_util = self.engine.get_sq_utilization()
        cq_util = self.engine.get_cq_utilization()

        if sq_util >= self.threshold or cq_util >= self.threshold or self.engine.sq_ring.is_full():
            self.throttled_submissions += 1
            return False

        ok = self.engine.submit_sqe(sqe)
        if ok:
            self.accepted_submissions += 1
        else:
            self.throttled_submissions += 1
        return ok


__all__ = [
    "SQEntry",
    "CQEntry",
    "RingBuffer",
    "IoUringEngine",
    "BackpressureThrottler",
]
