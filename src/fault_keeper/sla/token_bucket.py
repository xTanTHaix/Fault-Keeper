"""Token Bucket Rate Limiter Simulation for API Rate Limiting."""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TokenBucketState:
    """State representation for a token bucket instance."""

    tokens: float
    capacity: float
    last_refill_time: float = 0.0
    refill_rate: float = 0.0
    refill_interval_ms: float = 1000.0


@dataclass
class TokenBucket:
    """Represents a token bucket with rational arithmetic."""

    capacity: int
    tokens: int
    refill_rate_num: int
    refill_rate_den_ms: int
    created_at: float = field(default_factory=time.time)
    last_refill_time: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capacity": self.capacity,
            "tokens": self.tokens,
            "refill_rate_num": self.refill_rate_num,
            "refill_rate_den_ms": self.refill_rate_den_ms,
            "created_at": self.created_at,
            "last_refill_time": self.last_refill_time,
        }


@dataclass
class ConsumptionResult:
    """Result of token consumption operation."""

    success: bool
    tokens_consumed: int
    tokens_remaining: int
    elapsed_ms: float
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "tokens_consumed": self.tokens_consumed,
            "tokens_remaining": self.tokens_remaining,
            "elapsed_ms": round(self.elapsed_ms, 4),
            "reason": self.reason,
        }


@dataclass
class RateLimitAnalysis:
    """Analysis of rate limiting behavior."""

    bucket: TokenBucket
    elapsed_ms: float
    total_consumed: int
    refill_cycles: int
    burst_capacity_used: bool
    sustained_rate_achieved: bool
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bucket": self.bucket.to_dict(),
            "elapsed_ms": round(self.elapsed_ms, 4),
            "total_consumed": self.total_consumed,
            "refill_cycles": self.refill_cycles,
            "burst_capacity_used": self.burst_capacity_used,
            "sustained_rate_achieved": self.sustained_rate_achieved,
            "recommendations": self.recommendations,
        }


class TokenBucketSimulator:
    """Token bucket simulator supporting state-based simulation and rational arithmetic."""

    def __init__(
        self,
        capacity: float = 100.0,
        refill_rate_num: float = 10.0,
        refill_rate_den_ms: float = 1000.0,
        **kwargs: Any,
    ) -> None:
        self.bucket = TokenBucket(
            capacity=int(capacity),
            tokens=int(capacity),
            refill_rate_num=int(refill_rate_num),
            refill_rate_den_ms=int(refill_rate_den_ms),
        )
        self._accumulated_remainder_ms: int = 0

    def init(
        self,
        capacity: float = 100.0,
        refill_rate: float = 10.0,
        refill_interval_ms: float = 1000.0,
    ) -> TokenBucketState:
        """Initialize state for token bucket simulation."""
        return TokenBucketState(
            tokens=float(capacity),
            capacity=float(capacity),
            last_refill_time=time.time(),
            refill_rate=float(refill_rate),
            refill_interval_ms=float(refill_interval_ms),
        )

    def refill(self, state: TokenBucketState, elapsed_ms: float) -> Dict[str, Any]:
        """Refill tokens based on elapsed milliseconds."""
        interval = state.refill_interval_ms if state.refill_interval_ms > 0 else 1000.0
        tokens_to_add = (state.refill_rate * elapsed_ms) / interval
        state.tokens = min(state.capacity, state.tokens + tokens_to_add)
        state.last_refill_time = time.time()
        return {
            "success": True,
            "tokens": state.tokens,
            "tokens_added": tokens_to_add,
            "elapsed_ms": elapsed_ms,
        }

    def consume(self, state: TokenBucketState, tokens: float) -> Dict[str, Any]:
        """Consume tokens from state."""
        if tokens < 0:
            return {
                "success": False,
                "tokens_consumed": 0.0,
                "tokens_remaining": min(state.capacity, state.tokens),
                "reason": f"Negative token consumption rejected: {tokens}",
            }
        if state.tokens >= tokens:
            state.tokens -= tokens
            return {
                "success": True,
                "tokens_consumed": tokens,
                "tokens_remaining": state.tokens,
            }
        return {
            "success": False,
            "tokens_consumed": 0.0,
            "tokens_remaining": state.tokens,
            "reason": f"Insufficient tokens: requested {tokens}, available {state.tokens}",
        }

    # Rational arithmetic support
    def _refill_tokens(self, elapsed_ms: int) -> None:
        if elapsed_ms <= 0:
            return
        total_elapsed = elapsed_ms + self._accumulated_remainder_ms
        intervals_passed = total_elapsed // self.bucket.refill_rate_den_ms
        self._accumulated_remainder_ms = total_elapsed % self.bucket.refill_rate_den_ms
        tokens_to_add = intervals_passed * self.bucket.refill_rate_num
        self.bucket.tokens = min(self.bucket.capacity, self.bucket.tokens + tokens_to_add)
        self.bucket.last_refill_time = time.time()

    def consume_tokens(self, tokens_to_consume: int, elapsed_ms: Optional[int] = None) -> ConsumptionResult:
        if elapsed_ms is None:
            elapsed_ms = int((time.time() - self.bucket.last_refill_time) * 1000)
        self._refill_tokens(elapsed_ms)
        if self.bucket.tokens >= tokens_to_consume:
            self.bucket.tokens -= tokens_to_consume
            return ConsumptionResult(
                success=True,
                tokens_consumed=tokens_to_consume,
                tokens_remaining=self.bucket.tokens,
                elapsed_ms=elapsed_ms,
            )
        return ConsumptionResult(
            success=False,
            tokens_consumed=0,
            tokens_remaining=self.bucket.tokens,
            elapsed_ms=elapsed_ms,
            reason=f"Only {self.bucket.tokens} tokens available, requested {tokens_to_consume}",
        )

    def get_current_state(self) -> Dict[str, Any]:
        return self.bucket.to_dict()

    def calculate_refill_rate(self) -> float:
        return (self.bucket.refill_rate_num * 1000) / self.bucket.refill_rate_den_ms

    def simulate_consumption(self, consumption_pattern: List[Tuple[int, int]]) -> RateLimitAnalysis:
        total_consumed = 0
        refill_cycles = 0
        burst_capacity_used = False
        sustained_rate_achieved = True

        for elapsed_ms, tokens_to_consume in consumption_pattern:
            res = self.consume_tokens(tokens_to_consume, elapsed_ms)
            if not res.success:
                burst_capacity_used = True
                sustained_rate_achieved = False
            total_consumed += res.tokens_consumed
            intervals_passed = elapsed_ms // self.bucket.refill_rate_den_ms
            refill_cycles += intervals_passed

        recommendations: List[str] = []
        if self.bucket.tokens <= 0:
            recommendations.append("Bucket empty. Consider increasing capacity or refill rate.")
        if burst_capacity_used:
            recommendations.append("Burst capacity was exceeded.")
        if sustained_rate_achieved:
            recommendations.append("Sustained rate was maintained successfully.")
        return RateLimitAnalysis(
            bucket=self.bucket,
            elapsed_ms=consumption_pattern[-1][0] if consumption_pattern else 0,
            total_consumed=total_consumed,
            refill_cycles=refill_cycles,
            burst_capacity_used=burst_capacity_used,
            sustained_rate_achieved=sustained_rate_achieved,
            recommendations=recommendations,
        )


def create_token_bucket(
    capacity: float = 100.0,
    refill_rate: float = 10.0,
    refill_interval_ms: float = 1000.0,
    tokens_per_second: float | None = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Create token bucket configuration."""
    actual_rate = tokens_per_second if tokens_per_second is not None else refill_rate
    simulator = TokenBucketSimulator(
        capacity=capacity,
        refill_rate_num=int(actual_rate * 1000),
        refill_rate_den_ms=int(refill_interval_ms),
    )
    return {
        "success": True,
        "capacity": capacity,
        "refill_rate": actual_rate,
        "refill_interval_ms": refill_interval_ms,
        "tokens": capacity,
        "bucket": simulator.get_current_state(),
        "refill_rate_tokens_per_second": (actual_rate * 1000.0) / refill_interval_ms,
    }


def compute_token_budget(
    capacity: float,
    elapsed_ms: float,
    refill_rate: float,
    refill_interval_ms: float = 1000.0,
    initial_tokens: float | None = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Compute available token budget after elapsed time."""
    interval = refill_interval_ms if refill_interval_ms > 0 else 1000.0
    tokens_added = (refill_rate * elapsed_ms) / interval
    base_tokens = initial_tokens if initial_tokens is not None else float(capacity)
    tokens = min(float(capacity), base_tokens + tokens_added)

    return {
        "success": True,
        "tokens": tokens,
        "capacity": float(capacity),
        "refill_rate": float(refill_rate),
        "refill_interval_ms": float(interval),
        "elapsed_ms": float(elapsed_ms),
    }


def simulate_rate_limited_queue(
    arrival_rate: float,
    service_rate: float,
    servers: int = 1,
    simulation_time_ms: float = 10000.0,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Simulate rate-limited queueing dynamics (M/M/c approximation)."""
    if arrival_rate <= 0.0:
        return {
            "success": True,
            "arrival_rate": float(arrival_rate),
            "service_rate": float(service_rate),
            "servers": servers,
            "simulation_time_ms": simulation_time_ms,
            "utilization": 0.0,
            "queue_length": 0.0,
        }

    total_service = float(servers * service_rate)
    if total_service <= 0.0:
        clamped_utilization = 1.0
        queue_growth_rate = float(arrival_rate)
        queue_length = queue_growth_rate * (simulation_time_ms / 1000.0)
    elif arrival_rate > total_service:
        clamped_utilization = 1.0
        queue_growth_rate = arrival_rate - total_service
        queue_length = queue_growth_rate * (simulation_time_ms / 1000.0)
    else:
        utilization = arrival_rate / total_service
        clamped_utilization = min(0.95, max(0.0, utilization))
        queue_length = (clamped_utilization ** 2) / (1.0 - clamped_utilization) if clamped_utilization < 1.0 else 0.0

    return {
        "success": True,
        "arrival_rate": arrival_rate,
        "service_rate": service_rate,
        "servers": servers,
        "simulation_time_ms": simulation_time_ms,
        "utilization": clamped_utilization,
        "queue_length": max(0.0, round(queue_length, 2)),
    }


# ---------------------------------------------------------------------------
# Rate Limiting Strategies & Public Helpers
# ---------------------------------------------------------------------------

class RateLimitingStrategies:
    """Implements rate limiting strategies."""

    def __init__(self) -> None:
        self.strategies: Dict[str, TokenBucketSimulator] = {}

    def create_bucket(self, name: str, capacity: int, refill_rate_num: int, refill_rate_den_ms: int) -> TokenBucketSimulator:
        bucket = TokenBucketSimulator(capacity=capacity, refill_rate_num=refill_rate_num, refill_rate_den_ms=refill_rate_den_ms)
        self.strategies[name] = bucket
        return bucket

    def get_bucket_state(self, bucket_name: str) -> Optional[Dict[str, Any]]:
        if bucket_name not in self.strategies:
            return None
        return self.strategies[bucket_name].get_current_state()


class BurstCapacityAnalyzer:
    """Analyzes burst capacity utilization."""

    def calculate_burst_capacity(self, capacity: int, sustained_rate_ms: int = 1000, sustained_tokens_per_interval: int = 10) -> Dict[str, Any]:
        refill_time_ms = (capacity - sustained_tokens_per_interval) * sustained_rate_ms // sustained_tokens_per_interval if sustained_tokens_per_interval > 0 else 0
        return {
            "capacity": capacity,
            "sustained_rate_ms": sustained_rate_ms,
            "sustained_tokens_per_interval": sustained_tokens_per_interval,
            "refill_time_ms": refill_time_ms,
            "burst_capacity_available": capacity - sustained_tokens_per_interval,
        }


_global_rate_limiting_strategies = RateLimitingStrategies()


def consume_tokens(bucket_name: str, tokens: int, elapsed_ms: Optional[int] = None) -> Dict[str, Any]:
    """Consume tokens from a named bucket in the shared strategy registry."""
    if bucket_name not in _global_rate_limiting_strategies.strategies:
        _global_rate_limiting_strategies.create_bucket(
            name=bucket_name,
            capacity=100,
            refill_rate_num=10,
            refill_rate_den_ms=1000,
        )

    sim = _global_rate_limiting_strategies.strategies[bucket_name]
    res = sim.consume_tokens(tokens, elapsed_ms)
    return {
        "success": res.success,
        "tokens_consumed": res.tokens_consumed,
        "tokens_remaining": res.tokens_remaining,
        "elapsed_ms": round(res.elapsed_ms, 4),
        "reason": res.reason,
    }


def analyze_burst_capacity(capacity: int, tokens_per_second: float) -> Dict[str, Any]:
    analyzer = BurstCapacityAnalyzer()
    return analyzer.calculate_burst_capacity(
        capacity=capacity,
        sustained_rate_ms=1000,
        sustained_tokens_per_interval=int(tokens_per_second * 1000),
    )


def simulate_rate_limiting(capacity: int, tokens_per_second: float, consumption_pattern: List[Tuple[int, int]]) -> Dict[str, Any]:
    simulator = TokenBucketSimulator(capacity=capacity, refill_rate_num=int(tokens_per_second * 1000), refill_rate_den_ms=1000)
    result = simulator.simulate_consumption(consumption_pattern)
    return {
        "success": True,
        "bucket_state": simulator.get_current_state(),
        "analysis": result.to_dict(),
    }


def test_rate_limiter(capacity: int, tokens_per_second: float, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    for test_case in test_cases:
        simulator = TokenBucketSimulator(capacity=capacity, refill_rate_num=int(tokens_per_second * 1000), refill_rate_den_ms=1000)
        pattern = [(test_case.get("elapsed_ms", 0), test_case.get("tokens", 1))]
        result = simulator.simulate_consumption(pattern)
        results.append({"test_case": test_case, "result": result.to_dict()})

    return {
        "success": True,
        "capacity": capacity,
        "tokens_per_second": tokens_per_second,
        "test_results": results,
    }


__all__ = [
    "TokenBucketState",
    "TokenBucketSimulator",
    "compute_token_budget",
    "simulate_rate_limited_queue",
    "create_token_bucket",
    "TokenBucket",
    "ConsumptionResult",
    "RateLimitAnalysis",
    "RateLimitingStrategies",
    "BurstCapacityAnalyzer",
    "consume_tokens",
    "analyze_burst_capacity",
    "simulate_rate_limiting",
    "test_rate_limiter",
]