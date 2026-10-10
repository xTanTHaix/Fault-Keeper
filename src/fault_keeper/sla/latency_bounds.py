"""Multi-hop Latency Bound Computation for Microservice Chains.

Computes worst-case latency bounds across distributed microservice chains using ball arithmetic.

Core functionality:
- Model microservice chain as sequence of hops
- Compute worst-case latency bounds using interval arithmetic
- Account for jitter and variability in each hop
- Aggregate end-to-end latency guarantees
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data Structures for Latency Analysis
# ---------------------------------------------------------------------------

@dataclass
class ServiceHop:
    """Represents a microservice hop in the chain."""
    name: str
    median_ms: float  # Median latency in milliseconds
    jitter_ms: float  # Jitter (variability) in milliseconds
    p50_ms: Optional[float] = None  # 50th percentile
    p95_ms: Optional[float] = None  # 95th percentile
    p99_ms: Optional[float] = None  # 99th percentile
    error_rate: float = 0.0  # Error rate

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "median_ms": round(self.median_ms, 4),
            "jitter_ms": round(self.jitter_ms, 4),
            "p50_ms": round(self.p50_ms, 4) if self.p50_ms else None,
            "p95_ms": round(self.p95_ms, 4) if self.p95_ms else None,
            "p99_ms": round(self.p99_ms, 4) if self.p99_ms else None,
            "error_rate": round(self.error_rate, 6),
        }


@dataclass
class LatencyBound:
    """Represents computed latency bound."""
    hop_name: str
    lower_bound_ms: float
    upper_bound_ms: float
    confidence_level: float
    computation_method: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hop_name": self.hop_name,
            "lower_bound_ms": round(self.lower_bound_ms, 4),
            "upper_bound_ms": round(self.upper_bound_ms, 4),
            "confidence_level": self.confidence_level,
            "computation_method": self.computation_method,
        }


@dataclass
class ChainLatencyResult:
    """Result of end-to-end latency bound computation."""
    chain_name: str
    hops: List[ServiceHop]
    total_median_ms: float
    total_jitter_ms: float
    lower_bound_ms: float
    upper_bound_ms: float
    worst_case_latency_ms: float
    meets_sla: bool
    sla_target_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_name": self.chain_name,
            "hops": [h.to_dict() for h in self.hops],
            "total_median_ms": round(self.total_median_ms, 4),
            "total_jitter_ms": round(self.total_jitter_ms, 4),
            "lower_bound_ms": round(self.lower_bound_ms, 4),
            "upper_bound_ms": round(self.upper_bound_ms, 4),
            "worst_case_latency_ms": round(self.worst_case_latency_ms, 4),
            "meets_sla": self.meets_sla,
            "sla_target_ms": round(self.sla_target_ms, 4) if self.sla_target_ms else None,
        }


# ---------------------------------------------------------------------------
# Ball Arithmetic for Latency Computation
# ---------------------------------------------------------------------------

class BallArithmetic:
    """Ball arithmetic for interval-based latency computation."""

    def __init__(self) -> None:
        """Initialize ball arithmetic."""
        pass

    @staticmethod
    def add_ball(
        a_mid: float,
        a_rad: float,
        b_mid: float,
        b_rad: float,
    ) -> Tuple[float, float]:
        """Add two balls (intervals).

        Args:
            a_mid: Midpoint of first ball.
            a_rad: Radius of first ball.
            b_mid: Midpoint of second ball.
            b_rad: Radius of second ball.

        Returns:
            Tuple of (midpoint, radius) for result ball.
        """
        result_mid = a_mid + b_mid
        result_rad = a_rad + b_rad
        return result_mid, result_rad

    @staticmethod
    def multiply_ball(
        a_mid: float,
        a_rad: float,
        b_mid: float,
        b_rad: float,
    ) -> Tuple[float, float]:
        """Multiply two balls (intervals).

        Args:
            a_mid: Midpoint of first ball.
            a_rad: Radius of first ball.
            b_mid: Midpoint of second ball.
            b_rad: Radius of second ball.

        Returns:
            Tuple of (midpoint, radius) for result ball.
        """
        # For latency, we use addition (latencies accumulate)
        return BallArithmetic.add_ball(a_mid, a_rad, b_mid, b_rad)

    @staticmethod
    def divide_ball(
        a_mid: float,
        a_rad: float,
        b_mid: float,
        b_rad: float,
    ) -> Tuple[float, float]:
        """Divide two balls (intervals).

        Args:
            a_mid: Midpoint of first ball.
            a_rad: Radius of first ball.
            b_mid: Midpoint of second ball.
            b_rad: Radius of second ball.

        Returns:
            Tuple of (midpoint, radius) for result ball.
        """
        # Avoid division by zero
        if abs(b_mid) < 1e-9:
            return float('inf'), float('inf')

        result_mid = a_mid / b_mid
        # Simplified error propagation
        result_rad = (a_rad / abs(b_mid)) + (abs(a_mid) * b_rad / (b_mid ** 2))
        return result_mid, result_rad


# ---------------------------------------------------------------------------
# Latency Bound Computation Engine
# ---------------------------------------------------------------------------

class LatencyBoundComputation:
    """Computes latency bounds for microservice chains."""

    def __init__(self) -> None:
        """Initialize computation engine."""
        self.ball_arithmetic = BallArithmetic()

    def compute_hop_bounds(
        self,
        hop: ServiceHop,
        confidence_level: float = 0.95,
    ) -> List[LatencyBound]:
        """Compute latency bounds for single hop.

        Args:
            hop: Service hop to analyze.
            confidence_level: Confidence level (0-1).

        Returns:
            List of latency bounds.
        """
        # Convert median and jitter to interval
        median = hop.median_ms
        jitter = hop.jitter_ms

        # Compute bounds based on confidence level
        z_score = self._get_z_score(confidence_level)

        lower_bound = median - (z_score * jitter)
        upper_bound = median + (z_score * jitter)

        return [
            LatencyBound(
                hop_name=hop.name,
                lower_bound_ms=max(0, lower_bound),  # Ensure non-negative
                upper_bound_ms=upper_bound,
                confidence_level=confidence_level,
                computation_method="ball_arithmetic",
            ),
        ]

    def _get_z_score(self, confidence_level: float) -> float:
        """Get z-score for confidence level.

        Args:
            confidence_level: Confidence level (0-1).

        Returns:
            Z-score corresponding to confidence level.
        """
        # Simplified mapping (actual implementation would use inverse CDF)
        if confidence_level == 0.95:
            return 1.645
        elif confidence_level == 0.99:
            return 2.326
        elif confidence_level == 0.999:
            return 3.090
        else:
            # Linear interpolation
            return 1.645 + (confidence_level - 0.95) * (3.090 - 1.645) / 0.049

    def compute_chain_bounds(
        self,
        hops: List[Any],
        confidence_level: float = 0.95,
    ) -> ChainLatencyResult:
        """Compute end-to-end latency bounds for chain.

        Args:
            hops: List of service hops (ServiceHop instances or dicts).
            confidence_level: Confidence level.

        Returns:
            Chain latency result.
        """
        normalized_hops: List[ServiceHop] = []
        for h in hops:
            if isinstance(h, ServiceHop):
                normalized_hops.append(h)
            elif isinstance(h, dict):
                normalized_hops.append(
                    ServiceHop(
                        name=str(h.get("name", "hop")),
                        median_ms=float(h.get("median_ms", 0.0)),
                        jitter_ms=float(h.get("jitter_ms", 0.0)),
                        p50_ms=h.get("p50_ms"),
                        p95_ms=h.get("p95_ms"),
                        p99_ms=h.get("p99_ms"),
                        error_rate=float(h.get("error_rate", 0.0)),
                    )
                )

        total_mid = 0.0
        total_rad = 0.0

        for hop in normalized_hops:
            mid, rad = self.ball_arithmetic.add_ball(
                hop.median_ms,
                hop.jitter_ms,
                0.0,
                0.0,
            )
            total_mid += mid
            total_rad += rad

        worst_case_latency = total_mid + 2 * total_rad

        z_score = self._get_z_score(confidence_level)
        lower_bound = total_mid - (z_score * total_rad)
        upper_bound = total_mid + (z_score * total_rad)

        return ChainLatencyResult(
            chain_name="microservice_chain",
            hops=normalized_hops,
            total_median_ms=total_mid,
            total_jitter_ms=total_rad,
            lower_bound_ms=max(0.0, lower_bound),
            upper_bound_ms=upper_bound,
            worst_case_latency_ms=worst_case_latency,
            meets_sla=False,
            sla_target_ms=None,
        )

    def analyze_chain_performance(
        self,
        chain_name: str,
        hops: List[Any],
        sla_target_ms: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Analyze chain performance against SLA.

        Args:
            chain_name: Name of service chain.
            hops: List of service hops.
            sla_target_ms: Target SLA latency in milliseconds.

        Returns:
            Performance analysis results.
        """
        result = self.compute_chain_bounds(hops)

        if sla_target_ms is not None:
            result.meets_sla = result.worst_case_latency_ms <= sla_target_ms
            result.sla_target_ms = sla_target_ms

        return {
            "success": True,
            "chain_name": chain_name,
            "hops_count": len(result.hops),
            "total_median_ms": round(result.total_median_ms, 4),
            "total_jitter_ms": round(result.total_jitter_ms, 4),
            "lower_bound_ms": round(result.lower_bound_ms, 4),
            "upper_bound_ms": round(result.upper_bound_ms, 4),
            "worst_case_latency_ms": round(result.worst_case_latency_ms, 4),
            "meets_sla": result.meets_sla,
            "sla_target_ms": round(sla_target_ms, 4) if sla_target_ms is not None else None,
        }


# ---------------------------------------------------------------------------
# Multi-hop Latency Analyzer
# ---------------------------------------------------------------------------

class MultiHopLatencyAnalyzer:
    """Analyzes multi-hop microservice latency chains."""

    def __init__(self) -> None:
        """Initialize analyzer."""
        self.computation = LatencyBoundComputation()

    def create_chain(
        self,
        chain_name: str,
        hops_data: List[Any],
    ) -> List[ServiceHop]:
        """Create service chain from hop data.

        Args:
            chain_name: Name of service chain.
            hops_data: List of hop dictionaries or ServiceHop objects.

        Returns:
            List of ServiceHop objects.
        """
        hops: List[ServiceHop] = []

        for hop_data in hops_data:
            if isinstance(hop_data, ServiceHop):
                hops.append(hop_data)
            elif isinstance(hop_data, dict):
                hop = ServiceHop(
                    name=hop_data["name"],
                    median_ms=hop_data["median_ms"],
                    jitter_ms=hop_data["jitter_ms"],
                    p50_ms=hop_data.get("p50_ms"),
                    p95_ms=hop_data.get("p95_ms"),
                    p99_ms=hop_data.get("p99_ms"),
                    error_rate=hop_data.get("error_rate", 0.0),
                )
                hops.append(hop)

        return hops

    def compute_end_to_end_latency(
        self,
        chain_name: str,
        hops_data: List[Any],
        confidence_level: float = 0.95,
    ) -> ChainLatencyResult:
        """Compute end-to-end latency for chain.

        Args:
            chain_name: Name of service chain.
            hops_data: List of hop data dictionaries.
            confidence_level: Confidence level.

        Returns:
            Chain latency result.
        """
        hops = self.create_chain(chain_name, hops_data)
        return self.computation.compute_chain_bounds(hops, confidence_level)

    def analyze_chain_performance(
        self,
        chain_name: str,
        hops_data: List[Any],
        sla_target_ms: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Analyze chain performance against SLA target."""
        hops = self.create_chain(chain_name, hops_data)
        return self.computation.analyze_chain_performance(chain_name, hops, sla_target_ms)

    def benchmark_chain(
        self,
        chain_name: str,
        hops_data: List[Dict[str, Any]],
        iterations: int = 100,
    ) -> Dict[str, Any]:
        """Benchmark service chain performance.

        Args:
            chain_name: Name of service chain.
            hops_data: List of hop data.
            iterations: Number of benchmark iterations.

        Returns:
            Benchmark results.
        """
        import random
        import statistics

        latencies: List[float] = []

        for _ in range(max(1, iterations)):
            total_latency = 0.0
            for hop_data in hops_data:
                if isinstance(hop_data, ServiceHop):
                    median = hop_data.median_ms
                    jitter = hop_data.jitter_ms
                else:
                    median = float(hop_data["median_ms"])
                    jitter = float(hop_data["jitter_ms"])
                latency = random.triangular(max(0.0, median - jitter), median + jitter, median)
                total_latency += latency

            latencies.append(total_latency)

        return {
            "success": True,
            "chain_name": chain_name,
            "iterations": iterations,
            "mean_latency_ms": round(statistics.mean(latencies), 4),
            "median_latency_ms": round(statistics.median(latencies), 4),
            "p95_latency_ms": round(statistics.quantiles(latencies, n=20)[17], 4) if len(latencies) >= 20 else None,
            "p99_latency_ms": round(statistics.quantiles(latencies, n=100)[98], 4) if len(latencies) >= 100 else None,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_latency_bounds(
    hops: List[Dict[str, Any]],
    confidence_level: float = 0.95,
) -> Dict[str, Any]:
    """Compute latency bounds for microservice chain.

    Args:
        hops: List of hop data dictionaries.
        confidence_level: Confidence level.

    Returns:
        Computation results with latency bounds.
    """
    analyzer = MultiHopLatencyAnalyzer()
    result = analyzer.compute_end_to_end_latency("chain", hops, confidence_level)

    return {
        "success": True,
        "chain_name": result.chain_name,
        "hops_count": len(result.hops),
        "total_median_ms": round(result.total_median_ms, 4),
        "total_jitter_ms": round(result.total_jitter_ms, 4),
        "lower_bound_ms": round(result.lower_bound_ms, 4),
        "upper_bound_ms": round(result.upper_bound_ms, 4),
        "worst_case_latency_ms": round(result.worst_case_latency_ms, 4),
    }


def analyze_chain_performance(
    chain_name: str,
    hops: List[Dict[str, Any]],
    sla_target_ms: Optional[float] = None,
) -> Dict[str, Any]:
    """Analyze service chain performance against SLA.

    Args:
        chain_name: Name of service chain.
        hops: List of hop data.
        sla_target_ms: Target SLA latency.

    Returns:
        Performance analysis results.
    """
    analyzer = MultiHopLatencyAnalyzer()
    return analyzer.analyze_chain_performance(chain_name, hops, sla_target_ms)


def benchmark_chain(
    chain_name: str,
    hops: List[Dict[str, Any]],
    iterations: int = 100,
) -> Dict[str, Any]:
    """Benchmark service chain performance.

    Args:
        chain_name: Name of service chain.
        hops: List of hop data.
        iterations: Number of benchmark iterations.

    Returns:
        Benchmark results.
    """
    analyzer = MultiHopLatencyAnalyzer()
    return analyzer.benchmark_chain(chain_name, hops, iterations)


def create_service_hop(
    name: str,
    median_ms: float,
    jitter_ms: float,
    **kwargs,
) -> Dict[str, Any]:
    """Create service hop data.

    Args:
        name: Service name.
        median_ms: Median latency.
        jitter_ms: Jitter.
        **kwargs: Optional percentiles and error rate.

    Returns:
        Hop data dictionary.
    """
    return {
        "name": name,
        "median_ms": median_ms,
        "jitter_ms": jitter_ms,
        "p50_ms": kwargs.get("p50_ms"),
        "p95_ms": kwargs.get("p95_ms"),
        "p99_ms": kwargs.get("p99_ms"),
        "error_rate": kwargs.get("error_rate", 0.0),
    }