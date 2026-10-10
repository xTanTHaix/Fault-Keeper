"""Tests for Token Bucket Rate Limiter Simulation."""

from __future__ import annotations

import pytest

from fault_keeper.sla.token_bucket import (
    TokenBucketSimulator,
    TokenBucketState,
    compute_token_budget,
    simulate_rate_limited_queue,
    create_token_bucket,
)


@pytest.fixture
def bucket_simulator():
    """Create token bucket simulator."""
    return TokenBucketSimulator()


@pytest.fixture
def sample_bucket():
    """Sample token bucket configuration."""
    return create_token_bucket(
        capacity=100,
        refill_rate=10,
        refill_interval_ms=1000,
    )


class TestTokenBucketState:
    """Tests for TokenBucketState dataclass."""

    def test_create_state(self):
        """Test creating token bucket state."""
        state = TokenBucketState(
            tokens=50.0,
            capacity=100.0,
            last_refill_time=0,
        )

        assert state.tokens == 50.0
        assert state.capacity == 100.0


class TestComputeTokenBudget:
    """Tests for compute_token_budget function."""

    def test_compute_budget(self):
        """Test computing token budget."""
        result = compute_token_budget(
            capacity=100,
            elapsed_ms=500,
            refill_rate=10,
            refill_interval_ms=1000,
        )

        assert result["success"] is True
        assert "tokens" in result


class TestCreateTokenBucket:
    """Tests for create_token_bucket function."""

    def test_create(self):
        """Test creating token bucket."""
        bucket = create_token_bucket(
            capacity=100,
            refill_rate=10,
            refill_interval_ms=1000,
        )

        assert bucket["capacity"] == 100
        assert bucket["refill_rate"] == 10


class TestTokenBucketSimulator:
    """Tests for TokenBucketSimulator class."""

    def test_init(self, bucket_simulator):
        """Test initializing simulator."""
        state = bucket_simulator.init(
            capacity=100,
            refill_rate=10,
            refill_interval_ms=1000,
        )

        assert isinstance(state, TokenBucketState)
        assert state.capacity == 100

    def test_refill(self, bucket_simulator):
        """Test token refill."""
        state = bucket_simulator.init(
            capacity=100,
            refill_rate=10,
            refill_interval_ms=1000,
        )

        result = bucket_simulator.refill(state, elapsed_ms=500)

        assert result["success"] is True
        assert result["tokens"] > 0

    def test_consume(self, bucket_simulator):
        """Test token consumption."""
        state = bucket_simulator.init(
            capacity=100,
            refill_rate=10,
            refill_interval_ms=1000,
        )

        result = bucket_simulator.consume(state, tokens=50)

        assert result["success"] is True
        assert result["tokens_remaining"] == 50

    def test_consume_insufficient_tokens(self, bucket_simulator):
        """Test consuming more tokens than available."""
        state = bucket_simulator.init(
            capacity=100,
            refill_rate=10,
            refill_interval_ms=1000,
        )

        result = bucket_simulator.consume(state, tokens=200)

        assert result["success"] is False


class TestSimulateRateLimitedQueue:
    """Tests for simulate_rate_limited_queue function."""

    def test_simulate(self):
        """Test simulating rate limited queue."""
        result = simulate_rate_limited_queue(
            arrival_rate=10,
            service_rate=5,
            servers=2,
            simulation_time_ms=10000,
        )

        assert result["success"] is True
        assert "queue_length" in result


class TestEdgeCases:
    """Tests for edge cases."""

    def test_zero_capacity(self):
        """Test with zero capacity."""
        state = TokenBucketState(
            tokens=0.0,
            capacity=0.0,
            last_refill_time=0,
        )

        assert state.capacity == 0.0

    def test_max_consumption(self):
        """Test consuming all available tokens."""
        result = compute_token_budget(
            capacity=100,
            elapsed_ms=0,
            refill_rate=0,
            refill_interval_ms=1000,
        )

        assert result["success"] is True


class TestRefillLogic:
    """Tests for refill logic."""

    def test_refill_calculation(self):
        """Test refill calculation accuracy."""
        capacity = 100
        refill_rate = 10
        refill_interval_ms = 1000
        elapsed_ms = 500

        expected_tokens = capacity + (refill_rate * elapsed_ms) / refill_interval_ms
        expected_tokens = min(expected_tokens, capacity)

        result = compute_token_budget(
            capacity=capacity,
            elapsed_ms=elapsed_ms,
            refill_rate=refill_rate,
            refill_interval_ms=refill_interval_ms,
        )

        assert abs(result["tokens"] - expected_tokens) < 0.01


class TestConsumptionLogic:
    """Tests for consumption logic."""

    def test_partial_consumption(self):
        """Test partial token consumption."""
        result = compute_token_budget(
            capacity=100,
            elapsed_ms=1000,
            refill_rate=10,
            refill_interval_ms=1000,
        )

        tokens = result["tokens"]
        consumed = 30

        remaining = max(0, tokens - consumed)
        assert remaining == tokens - consumed


class TestPerformance:
    """Tests for performance."""

    def test_simulator_performance(self, bucket_simulator):
        """Test simulator performance."""
        state = bucket_simulator.init(
            capacity=1000,
            refill_rate=100,
            refill_interval_ms=1000,
        )

        import time

        start_time = time.perf_counter()
        for _ in range(100):
            bucket_simulator.refill(state, elapsed_ms=500)
            bucket_simulator.consume(state, tokens=50)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should be fast (< 50ms for 200 operations)
        assert elapsed_ms < 50


class TestRateLimiting:
    """Tests for rate limiting behavior."""

    def test_burst_then_limit(self, bucket_simulator):
        """Test burst consumption followed by rate limiting."""
        state = bucket_simulator.init(
            capacity=100,
            refill_rate=10,
            refill_interval_ms=1000,
        )

        # Consume all tokens
        result = bucket_simulator.consume(state, tokens=100)
        assert result["success"] is True

        # Try to consume more immediately (should fail)
        result = bucket_simulator.consume(state, tokens=10)
        assert result["success"] is False


class TestQueueMetrics:
    """Tests for queue metrics."""

    def test_queue_utilization(self):
        """Test queue utilization calculation."""
        result = simulate_rate_limited_queue(
            arrival_rate=5,
            service_rate=10,
            servers=2,
            simulation_time_ms=10000,
        )

        assert "utilization" in result
        assert 0 <= result["utilization"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])