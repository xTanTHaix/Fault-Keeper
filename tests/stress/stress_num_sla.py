"""Empirical Stress Test Harness for Fault-Keeper Num & SLA Modules.

Adversarial stress-testing:
- tc_gtc_timezone.py
- rdas_redos.py
- token_bucket.py
- cas_i_op_cache.py
"""

from __future__ import annotations

import asyncio
import datetime
import math
import os
import re
import sys
import time
from typing import Any, Dict, List
import zoneinfo

sys.path.insert(0, os.path.abspath("src"))

from fault_keeper.num.cas_i_op_cache import (
    CacheStampedeXFetch,
    DistributedCacheCoordinator,
    StampedePrevention,
    XFetchAlgorithm,
    prevent_cache_stampede,
    xfetch_operation,
)
from fault_keeper.num.rdas_redos import (
    PerformanceBasedReDoSDetector,
    RegexComplexityAnalyzer,
    analyze_regex_complexity,
    optimize_regex,
    validate_input_length,
)
from fault_keeper.num.tc_gtc_timezone import (
    DSTTrapDetector,
    TimezoneConfig,
    TimezoneDriftDetector,
    detect_dst_traps,
    detect_timezone_drift,
    get_dst_transition_times,
    normalize_timestamp,
    validate_timezone_config,
)
from fault_keeper.sla.token_bucket import (
    RateLimitingStrategies,
    TokenBucketSimulator,
    consume_tokens,
    simulate_rate_limited_queue,
)


def run_timezone_tests() -> List[Dict[str, Any]]:
    """Adversarial stress tests for tc_gtc_timezone."""
    results = []

    # 1.1 Mixed type crash in TimezoneDriftDetector
    detector = TimezoneDriftDetector()
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        detector.detect_drift(now, 7.0)
        results.append({
            "test": "timezone_mixed_type_dt_float",
            "status": "PASS",
            "finding": "Handled datetime and float mixed types",
        })
    except TypeError as e:
        results.append({
            "test": "timezone_mixed_type_dt_float",
            "status": "FAIL_CRASH",
            "finding": f"TypeError on mixed datetime/float: {e}",
        })

    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        detector.detect_drift(7.0, now)
        results.append({
            "test": "timezone_mixed_type_float_dt",
            "status": "PASS",
            "finding": "Handled float and datetime mixed types",
        })
    except TypeError as e:
        results.append({
            "test": "timezone_mixed_type_float_dt",
            "status": "FAIL_CRASH",
            "finding": f"TypeError on mixed float/datetime: {e}",
        })

    # 1.2 get_dst_transition_times sampling defect
    ny_transitions = get_dst_transition_times("America/New_York", 2023)
    if ny_transitions == (None, None):
        results.append({
            "test": "timezone_get_dst_transition_times_ny",
            "status": "FAIL_ALGORITHM",
            "finding": "get_dst_transition_times returned (None, None) for America/New_York 2023 due to only testing day 15/16",
        })
    else:
        results.append({
            "test": "timezone_get_dst_transition_times_ny",
            "status": "PASS",
            "finding": f"Returned {ny_transitions}",
        })

    # 1.3 Southern hemisphere DST trap detection
    sydney_fall_back = datetime.datetime(2023, 4, 2, 2, 30, tzinfo=zoneinfo.ZoneInfo("Australia/Sydney"))
    trap_res = detect_dst_traps(sydney_fall_back)
    if not trap_res.get("has_dst_trap"):
        results.append({
            "test": "timezone_southern_hemisphere_dst_trap",
            "status": "FAIL_LOGIC",
            "finding": "detect_dst_traps missed Australia/Sydney fall-back on 2023-04-02 (hardcoded northern hemisphere months)",
        })
    else:
        results.append({
            "test": "timezone_southern_hemisphere_dst_trap",
            "status": "PASS",
            "finding": "Correctly detected Sydney DST transition",
        })

    # 1.4 Year 9999 timestamp overflow on positive offset normalization
    try:
        max_dt = datetime.datetime(9999, 12, 31, 23, 0, 0, tzinfo=datetime.timezone.utc)
        # Asia/Tokyo is UTC+9 -> year 10000 overflow
        normalize_timestamp(max_dt, "Asia/Tokyo")
        results.append({
            "test": "timezone_year_9999_overflow",
            "status": "PASS",
            "finding": "Normalized without overflow",
        })
    except OverflowError as e:
        results.append({
            "test": "timezone_year_9999_overflow",
            "status": "FAIL_OVERFLOW",
            "finding": f"OverflowError when normalizing boundary timestamp: {e}",
        })

    return results


def run_redos_tests() -> List[Dict[str, Any]]:
    """Adversarial stress tests for rdas_redos."""
    results = []
    analyzer = RegexComplexityAnalyzer()

    # 2.1 Bounded nested quantifier detection (a+){2,}
    res_bounded = analyzer.analyze_pattern(r"(a+){2,}")
    if not res_bounded["is_dangerous"]:
        results.append({
            "test": "redos_bounded_nested_quantifier",
            "status": "FAIL_DETECTION",
            "finding": "RegexComplexityAnalyzer failed to flag (a+){2,} as dangerous",
        })
    else:
        results.append({
            "test": "redos_bounded_nested_quantifier",
            "status": "PASS",
            "finding": "Flagged (a+){2,} as dangerous",
        })

    # 2.2 Ineffective optimization on alternations (a|aa)*
    opt_alt = analyzer.optimize_pattern(r"(a|aa)*")
    if opt_alt == r"(a|aa)*":
        results.append({
            "test": "redos_optimize_alternation_noop",
            "status": "FAIL_OPTIMIZATION",
            "finding": "optimize_pattern returned dangerous (a|aa)* completely unchanged",
        })
    else:
        results.append({
            "test": "redos_optimize_alternation_noop",
            "status": "PASS",
            "finding": f"Optimized to {opt_alt}",
        })

    # 2.3 Semantic corruption in optimize_pattern on (a+b*)*
    opt_multi = analyzer.optimize_pattern(r"(a+b*)*")
    if opt_multi == r"(?:a+b*)":
        results.append({
            "test": "redos_optimize_strips_quantifier",
            "status": "FAIL_SEMANTICS",
            "finding": "optimize_pattern stripped outer * quantifier entirely, turning zero-or-more into exactly-once",
        })
    else:
        results.append({
            "test": "redos_optimize_strips_quantifier",
            "status": "PASS",
            "finding": f"Optimized to {opt_multi}",
        })

    # 2.4 Lack of real execution timeout in PerformanceBasedReDoSDetector
    perf_detector = PerformanceBasedReDoSDetector(timeout_ms=5.0)
    # 23 'a's with trailing '!'
    start_t = time.perf_counter()
    perf_res = perf_detector.test_pattern_performance(r"(a+)+$", "a" * 23 + "!")
    elapsed_ms = (time.perf_counter() - start_t) * 1000
    if elapsed_ms > 200.0:  # Much greater than timeout_ms=5.0
        results.append({
            "test": "redos_performance_timeout_unheeded",
            "status": "FAIL_TIMEOUT",
            "finding": f"test_pattern_performance blocked thread for {elapsed_ms:.1f}ms despite timeout_ms=5.0 (no thread abort)",
        })
    else:
        results.append({
            "test": "redos_performance_timeout_unheeded",
            "status": "PASS",
            "finding": f"Completed within {elapsed_ms:.1f}ms",
        })

    # 2.5 Hardcoded malicious input generator
    mal = perf_detector.generate_malicious_input(r"(b+)+$")
    test_b = perf_detector.test_pattern_performance(r"(b+)+$", mal)
    if not test_b.get("is_vulnerable"):
        results.append({
            "test": "redos_malicious_input_hardcoded_a",
            "status": "FAIL_GENERATOR",
            "finding": "generate_malicious_input generates hardcoded 'a'*50, failing to trigger ReDoS for non-'a' patterns like (b+)+$",
        })
    else:
        results.append({
            "test": "redos_malicious_input_hardcoded_a",
            "status": "PASS",
            "finding": "Triggered ReDoS successfully",
        })

    return results


def run_token_bucket_tests() -> List[Dict[str, Any]]:
    """Adversarial stress tests for token_bucket."""
    results = []
    sim = TokenBucketSimulator(capacity=100.0)
    state = sim.init(capacity=100.0)

    # 3.1 Negative token consumption vulnerability (token injection)
    res_neg = sim.consume(state, -200.0)
    if res_neg["success"] and state.tokens > 100.0:
        results.append({
            "test": "token_bucket_negative_consumption_injection",
            "status": "FAIL_SECURITY",
            "finding": f"consume accepted negative tokens (-200), inflating bucket tokens to {state.tokens} (capacity: 100)",
        })
    else:
        results.append({
            "test": "token_bucket_negative_consumption_injection",
            "status": "PASS",
            "finding": "Rejected negative tokens or capped at capacity",
        })

    # 3.2 Sub-interval refill truncation loss
    sim2 = TokenBucketSimulator(capacity=100.0, refill_rate_num=10.0, refill_rate_den_ms=1000.0)
    sim2.bucket.tokens = 0
    # 5 calls of 800ms each = 4000ms total (should give 40 tokens)
    for _ in range(5):
        sim2.consume_tokens(0, elapsed_ms=800)
    if sim2.bucket.tokens == 0:
        results.append({
            "test": "token_bucket_rational_truncation_leak",
            "status": "FAIL_PRECISION",
            "finding": "Integer division (800 // 1000) dropped all refill tokens over 4000ms elapsed time",
        })
    else:
        results.append({
            "test": "token_bucket_rational_truncation_leak",
            "status": "PASS",
            "finding": f"Refilled {sim2.bucket.tokens} tokens",
        })

    # 3.3 Broken standalone consume_tokens due to ephemeral RateLimitingStrategies
    standalone_res = consume_tokens("test_bucket", 1)
    if not standalone_res["success"] and "Unknown bucket" in standalone_res.get("error", ""):
        results.append({
            "test": "token_bucket_standalone_consume_stateless",
            "status": "FAIL_ARCHITECTURE",
            "finding": "consume_tokens() instantiates a local empty RateLimitingStrategies() on each call, rendering it non-functional",
        })
    else:
        results.append({
            "test": "token_bucket_standalone_consume_stateless",
            "status": "PASS",
            "finding": "consume_tokens succeeded",
        })

    # 3.4 Zero arrival and service rate anomaly in queue simulation
    q_res = simulate_rate_limited_queue(arrival_rate=0.0, service_rate=0.0)
    if q_res["queue_length"] > 0.0:
        results.append({
            "test": "token_bucket_zero_rate_queue_anomaly",
            "status": "FAIL_LOGIC",
            "finding": f"simulate_rate_limited_queue(0, 0) reported non-empty queue length {q_res['queue_length']} for zero traffic",
        })
    else:
        results.append({
            "test": "token_bucket_zero_rate_queue_anomaly",
            "status": "PASS",
            "finding": f"Reported queue length {q_res['queue_length']}",
        })

    return results


async def run_cache_stampede_tests() -> List[Dict[str, Any]]:
    """Adversarial stress tests for cas_i_op_cache."""
    results = []

    # 4.1 Thundering herd failure in prevent_cache_stampede standalone API
    fetch_calls = 0

    async def mock_fetch():
        nonlocal fetch_calls
        fetch_calls += 1
        await asyncio.sleep(0.02)
        return "expensive_result"

    # Launch 20 concurrent requests to prevent_cache_stampede
    tasks = [prevent_cache_stampede("herd_key", mock_fetch) for _ in range(20)]
    await asyncio.gather(*tasks)

    if fetch_calls > 1:
        results.append({
            "test": "cache_stampede_thundering_herd_leak",
            "status": "FAIL_CONCURRENCY",
            "finding": f"prevent_cache_stampede invoked fetch 20 times for 20 concurrent requests (stateless instance creation)",
        })
    else:
        results.append({
            "test": "cache_stampede_thundering_herd_leak",
            "status": "PASS",
            "finding": "Stampede prevented: single fetch call for 20 concurrent requests",
        })

    # 4.2 Stateless xfetch_operation always missing cache
    r1 = await xfetch_operation("hot_key", lambda k: "v1")
    r2 = await xfetch_operation("hot_key", lambda k: "v2")
    if r1.get("cache_miss") and r2.get("cache_miss"):
        results.append({
            "test": "cache_xfetch_stateless_always_miss",
            "status": "FAIL_ARCHITECTURE",
            "finding": "xfetch_operation instantiates new XFetchAlgorithm() each time; consecutive calls for same key both miss",
        })
    else:
        results.append({
            "test": "cache_xfetch_stateless_always_miss",
            "status": "PASS",
            "finding": "Consecutive calls hit cache",
        })

    # 4.3 Missing XFetch probabilistic early expiration algorithm
    xf_algo = XFetchAlgorithm()
    has_probabilistic = hasattr(xf_algo, "beta") or hasattr(xf_algo, "delta") or "beta" in inspect_algo_code()
    if not has_probabilistic:
        results.append({
            "test": "cache_xfetch_algorithm_noncompliance",
            "status": "FAIL_ALGORITHM",
            "finding": "XFetchAlgorithm has no probabilistic early expiration (no beta, no log(rand()), no computation time tracking)",
        })
    else:
        results.append({
            "test": "cache_xfetch_algorithm_noncompliance",
            "status": "PASS",
            "finding": "Probabilistic early expiration implemented",
        })

    # 4.4 ttl_seconds=0 eternal caching in DistributedCacheCoordinator
    coord = DistributedCacheCoordinator()
    await coord.set("eternity_key", "eternal_val", ttl_seconds=0)
    entry = coord.cache_entries.get("eternity_key")
    if entry and entry.expires_at is None:
        results.append({
            "test": "cache_ttl_zero_eternal_bypass",
            "status": "FAIL_LOGIC",
            "finding": "Setting ttl_seconds=0 resulted in expires_at=None, caching the item forever",
        })
    else:
        results.append({
            "test": "cache_ttl_zero_eternal_bypass",
            "status": "PASS",
            "finding": "ttl_seconds=0 expired immediately or was not cached",
        })

    # 4.5 ttl_seconds ignored in StampedePrevention.stampede_prevention
    prev = StampedePrevention()
    await prev.stampede_prevention("ttl_key", lambda: "val", ttl_seconds=1)
    if "ttl_key" in prev.cache and not hasattr(prev, "cache_expiry"):
        results.append({
            "test": "cache_stampede_prevention_ignores_ttl",
            "status": "FAIL_LOGIC",
            "finding": "StampedePrevention caches items in self.cache dict indefinitely without recording or checking ttl_seconds",
        })
    else:
        results.append({
            "test": "cache_stampede_prevention_ignores_ttl",
            "status": "PASS",
            "finding": "TTL respected in StampedePrevention",
        })

    return results


def inspect_algo_code() -> str:
    import inspect
    return inspect.getsource(XFetchAlgorithm)


def main():
    print("================================================================================")
    print("FAULT-KEEPER EMPIRICAL ADVERSARIAL STRESS TEST SUITE (M1 CHALLENGER 1)")
    print("================================================================================")

    tz_results = run_timezone_tests()
    redos_results = run_redos_tests()
    tb_results = run_token_bucket_tests()
    cache_results = asyncio.run(run_cache_stampede_tests())

    all_results = tz_results + redos_results + tb_results + cache_results

    failures = [r for r in all_results if r["status"].startswith("FAIL")]
    passes = [r for r in all_results if r["status"] == "PASS"]

    print(f"\n[SUMMARY] Total Tests: {len(all_results)} | Passed: {len(passes)} | Failed/Vulnerabilities: {len(failures)}")
    print("-" * 80)
    for r in all_results:
        print(f"[{r['status']:<18}] {r['test']:<42} : {r['finding']}")
    print("-" * 80)

    if failures:
        print(f"\n[VERDICT] REQUEST_CHANGES — {len(failures)} empirical defects and vulnerabilities confirmed.")
        sys.exit(1)
    else:
        print("\n[VERDICT] APPROVE — All stress tests passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
