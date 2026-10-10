"""Tests for Multi-hop Latency Bound Computation."""

from __future__ import annotations

import pytest

from fault_keeper.sla.latency_bounds import (
    ChainLatencyResult,
    LatencyBoundComputation,
    MultiHopLatencyAnalyzer,
    ServiceHop,
    compute_latency_bounds,
    create_service_hop,
    analyze_chain_performance,
    benchmark_chain,
)


@pytest.fixture
def computation_engine():
    """Create latency computation engine."""
    return LatencyBoundComputation()


@pytest.fixture
def analyzer():
    """Create latency analyzer."""
    return MultiHopLatencyAnalyzer()


@pytest.fixture
def sample_hops():
    """Sample service hops for testing."""
    return [
        {
            "name": "api_gateway",
            "median_ms": 10.0,
            "jitter_ms": 5.0,
            "p95_ms": 25.0,
            "p99_ms": 50.0,
        },
        {
            "name": "user_service",
            "median_ms": 20.0,
            "jitter_ms": 10.0,
            "p95_ms": 40.0,
            "p99_ms": 80.0,
        },
        {
            "name": "database",
            "median_ms": 5.0,
            "jitter_ms": 2.0,
            "p95_ms": 15.0,
            "p99_ms": 30.0,
        },
    ]


class TestServiceHop:
    """Tests for ServiceHop dataclass."""

    def test_create_hop(self):
        """Test creating service hop."""
        hop = create_service_hop(
            name="test_service",
            median_ms=15.0,
            jitter_ms=8.0,
            p95_ms=35.0,
            p99_ms=60.0,
        )

        assert hop["name"] == "test_service"
        assert hop["median_ms"] == 15.0
        assert hop["jitter_ms"] == 8.0


class TestLatencyBoundComputation:
    """Tests for LatencyBoundComputation class."""

    def test_compute_chain_bounds(self, computation_engine, sample_hops):
        """Test computing chain bounds."""
        result = computation_engine.compute_chain_bounds(sample_hops)

        assert isinstance(result, ChainLatencyResult)
        assert len(result.hops) == len(sample_hops)
        assert result.total_median_ms > 0

    def test_compute_single_hop(self, computation_engine):
        """Test computing bounds for single hop."""
        hop = ServiceHop(
            name="single",
            median_ms=10.0,
            jitter_ms=5.0,
        )

        bounds = computation_engine.compute_hop_bounds(hop)

        assert len(bounds) > 0


class TestMultiHopLatencyAnalyzer:
    """Tests for MultiHopLatencyAnalyzer class."""

    def test_create_chain(self, analyzer, sample_hops):
        """Test creating service chain."""
        hops = analyzer.create_chain("test_chain", sample_hops)

        assert len(hops) == len(sample_hops)
        assert all(isinstance(hop, ServiceHop) for hop in hops)

    def test_compute_end_to_end_latency(self, analyzer, sample_hops):
        """Test computing end-to-end latency."""
        result = analyzer.compute_end_to_end_latency("test_chain", sample_hops)

        assert isinstance(result, ChainLatencyResult)
        assert result.total_median_ms > 0
        assert result.worst_case_latency_ms > result.total_median_ms

    def test_analyze_chain_performance(self, analyzer, sample_hops):
        """Test analyzing chain performance against SLA."""
        result = analyzer.analyze_chain_performance(
            "test_chain",
            sample_hops,
            sla_target_ms=100.0,
        )

        assert "chain_name" in result
        assert "worst_case_latency_ms" in result
        assert "meets_sla" in result


class TestComputeLatencyBounds:
    """Tests for compute_latency_bounds function."""

    def test_compute_bounds(self, sample_hops):
        """Test computing latency bounds."""
        result = compute_latency_bounds(sample_hops)

        assert result["success"] is True
        assert "total_median_ms" in result
        assert "upper_bound_ms" in result


class TestAnalyzeChainPerformance:
    """Tests for analyze_chain_performance function."""

    def test_analyze_with_sla(self, sample_hops):
        """Test analyzing performance with SLA target."""
        result = analyze_chain_performance(
            "test_chain",
            sample_hops,
            sla_target_ms=100.0,
        )

        assert result["success"] is True
        assert "meets_sla" in result


class TestBenchmarkChain:
    """Tests for benchmark_chain function."""

    def test_benchmark(self, sample_hops):
        """Test benchmarking chain performance."""
        result = benchmark_chain("test_chain", sample_hops, iterations=10)

        assert result["success"] is True
        assert "mean_latency_ms" in result
        assert "median_latency_ms" in result


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_hops_list(self):
        """Test with empty hops list."""
        result = compute_latency_bounds([])

        assert result["success"] is True

    def test_single_hop(self):
        """Test with single hop."""
        single_hop = [
            {
                "name": "single_service",
                "median_ms": 10.0,
                "jitter_ms": 5.0,
            },
        ]

        result = compute_latency_bounds(single_hop)

        assert result["success"] is True


class TestPerformance:
    """Tests for performance."""

    def test_compute_bounds_performance(self, sample_hops):
        """Test bounds computation performance."""
        import time

        start_time = time.perf_counter()
        for _ in range(10):
            compute_latency_bounds(sample_hops)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should be fast (< 100ms)
        assert elapsed_ms < 100


class TestLatencyAggregation:
    """Tests for latency aggregation."""

    def test_aggregate_medians(self, sample_hops):
        """Test median latency aggregation."""
        analyzer = MultiHopLatencyAnalyzer()
        result = analyzer.compute_end_to_end_latency("test", sample_hops)

        # Total median should be approximately sum of individual medians
        expected_median = sum(h["median_ms"] for h in sample_hops)
        assert abs(result.total_median_ms - expected_median) < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])