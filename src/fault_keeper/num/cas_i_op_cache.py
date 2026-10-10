"""Cache Stampede & XFetch Algorithm for Distributed Systems."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import inspect
import math
import random
import time
from typing import Any, Dict, List, Optional


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""

    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    version: int = 1
    hit_count: int = 0
    is_locked: bool = False
    lock_owner: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "version": self.version,
            "hit_count": self.hit_count,
            "is_locked": self.is_locked,
            "lock_owner": self.lock_owner,
        }


@dataclass
class StampedeEvent:
    """Represents a cache stampede event."""

    timestamp: datetime = field(default_factory=datetime.now)
    affected_keys: List[str] = field(default_factory=list)
    concurrent_requests: int = 0
    resolution_strategy: str = "none"
    resolution_result: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "affected_keys": self.affected_keys,
            "concurrent_requests": self.concurrent_requests,
            "resolution_strategy": self.resolution_strategy,
            "resolution_result": self.resolution_result,
        }


async def _invoke_fetch(fetch_func: Any, key: str) -> Any:
    """Robustly invoke fetch_func whether sync or async, 0-arg or 1-arg."""
    try:
        sig = inspect.signature(fetch_func)
        if len(sig.parameters) == 0:
            res = fetch_func()
        else:
            res = fetch_func(key)
    except (TypeError, ValueError):
        try:
            res = fetch_func(key)
        except TypeError:
            res = fetch_func()

    if asyncio.iscoroutine(res):
        return await res
    return res


class StampedePrevention:
    """Prevents cache stampedes using mutex locking and single-flight coordination."""

    def __init__(self) -> None:
        self.locks: Dict[str, asyncio.Lock] = {}
        self.warmup_queue: asyncio.Queue = asyncio.Queue()
        self.cache: Dict[str, Any] = {}
        self.cache_expiry: Dict[str, float] = {}

    async def acquire_lock(self, key: str) -> asyncio.Lock:
        """Acquire or retrieve mutex lock for cache key."""
        if key not in self.locks:
            self.locks[key] = asyncio.Lock()
        return self.locks[key]

    async def release_lock(self, key: str) -> None:
        """Release lock for cache key."""
        if key in self.locks:
            del self.locks[key]

    async def stampede_prevention(
        self,
        key: str,
        fetch_func: Any,
        ttl_seconds: int = 60,
    ) -> Optional[Any]:
        """Prevent stampede by locking on miss and fetching atomically."""
        now = time.time()
        if key in self.cache:
            if key in self.cache_expiry and now > self.cache_expiry[key]:
                del self.cache[key]
                if key in self.cache_expiry:
                    del self.cache_expiry[key]
            else:
                return self.cache[key]

        lock = await self.acquire_lock(key)
        async with lock:
            now = time.time()
            if key in self.cache:
                if key in self.cache_expiry and now > self.cache_expiry[key]:
                    del self.cache[key]
                    if key in self.cache_expiry:
                        del self.cache_expiry[key]
                else:
                    return self.cache[key]

            val = await _invoke_fetch(fetch_func, key)
            self.cache[key] = val
            if ttl_seconds is not None:
                self.cache_expiry[key] = time.time() + ttl_seconds
            return val


class XFetchAlgorithm:
    """Implements XFetch atomic fetch-and-update algorithm with probabilistic early expiration."""

    def __init__(self, beta: float = 1.0, delta: float = 0.01) -> None:
        self.version_counter = 0
        self.cache: Dict[str, Any] = {}
        self.cache_expiry: Dict[str, float] = {}
        self.cache_compute_time: Dict[str, float] = {}
        self.beta: float = beta
        self.delta: float = delta

    def should_refresh(self, key: str, beta: Optional[float] = None) -> bool:
        """Evaluate Vattani et al. XFetch probabilistic early expiration condition:
        now - (beta * delta * ln(random())) > expiry
        """
        expiry = self.cache_expiry.get(key)
        if expiry is None:
            return False
        delta = self.cache_compute_time.get(key, self.delta)
        b = beta if beta is not None else self.beta
        r = random.random()
        if r <= 0.0:
            r = 0.000001
        now = time.time()
        return (now - (b * delta * math.log(r))) > expiry

    async def xfetch(
        self,
        key: str,
        fetch_func: Any,
        update_func: Any = None,
    ) -> Dict[str, Any]:
        """Perform atomic fetch-and-update operation returning explicit value key."""
        cached_value = self.cache.get(key)
        old_value = cached_value
        is_expired = self.should_refresh(key)

        if cached_value is None or is_expired:
            t0 = time.perf_counter()
            try:
                new_value = await _invoke_fetch(fetch_func, key)
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "old_value": None,
                    "new_value": None,
                    "value": None,
                    "version": 0,
                }
            compute_delta = time.perf_counter() - t0
            self.cache_compute_time[key] = max(0.0001, compute_delta)
            self.cache_expiry[key] = time.time() + 60.0

            if update_func:
                try:
                    new_value = update_func(new_value)
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Update failed: {e}",
                        "old_value": None,
                        "new_value": new_value,
                        "value": new_value,
                        "version": 0,
                    }

            self.version_counter += 1
            version = self.version_counter
            self.cache[key] = new_value

            return {
                "success": True,
                "cache_miss": (cached_value is None),
                "old_value": old_value,
                "new_value": new_value,
                "value": new_value,
                "version": version,
            }
        else:
            self.version_counter += 1
            version = self.version_counter

            return {
                "success": True,
                "cache_miss": False,
                "old_value": old_value,
                "new_value": cached_value,
                "value": cached_value,
                "version": version,
            }


class DistributedCacheCoordinator:
    """Coordinates distributed cache operations."""

    def __init__(self) -> None:
        self.cache_entries: Dict[str, CacheEntry] = {}
        self.lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self.lock:
            if key in self.cache_entries:
                entry = self.cache_entries[key]
                if entry.expires_at and datetime.now() > entry.expires_at:
                    del self.cache_entries[key]
                    return None
                entry.hit_count += 1
                return entry.value
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        expires_at = None
        if ttl_seconds is not None:
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

        entry = CacheEntry(
            key=key,
            value=value,
            expires_at=expires_at,
        )

        async with self.lock:
            self.cache_entries[key] = entry
        return True

    async def delete(self, key: str) -> bool:
        async with self.lock:
            if key in self.cache_entries:
                del self.cache_entries[key]
                return True
            return False

    async def invalidate_pattern(self, pattern: str) -> Dict[str, Any]:
        invalidated: List[str] = []
        async with self.lock:
            for key in list(self.cache_entries.keys()):
                if key.startswith(pattern):
                    del self.cache_entries[key]
                    invalidated.append(key)

        return {
            "success": True,
            "pattern": pattern,
            "invalidated_count": len(invalidated),
            "invalidated_keys": invalidated,
        }

    async def warm_cache(
        self,
        keys: List[str],
        fetch_func: Any,
        batch_size: int = 10,
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()

        for i in range(0, len(keys), batch_size):
            batch = keys[i:i + batch_size]
            for key in batch:
                try:
                    value = await _invoke_fetch(fetch_func, key)
                    await self.set(key, value, ttl_seconds=60)
                except Exception:
                    pass

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return {
            "success": True,
            "warmed_count": len(keys),
            "elapsed_ms": round(elapsed_ms, 4),
        }

    async def monitor_cache_health(self) -> Dict[str, Any]:
        async with self.lock:
            total_entries = len(self.cache_entries)
            hit_count_sum = sum(e.hit_count for e in self.cache_entries.values())
        avg_hits = hit_count_sum / total_entries if total_entries > 0 else 0

        return {
            "total_entries": total_entries,
            "total_hits": hit_count_sum,
            "avg_hits_per_entry": round(avg_hits, 4),
            "memory_usage_kb": total_entries,
        }


class CacheStampedeXFetch:
    """Combined cache stampede prevention with XFetch algorithm."""

    def __init__(self) -> None:
        self.coordinator = DistributedCacheCoordinator()
        self.prevention = StampedePrevention()
        self.xfetch = XFetchAlgorithm()

    async def stampede_prevention(
        self,
        key: str,
        fetch_func: Any,
        ttl_seconds: int = 60,
    ) -> Optional[Any]:
        value = await self.coordinator.get(key)
        if value is not None:
            return value

        lock = await self.prevention.acquire_lock(key)
        async with lock:
            value = await self.coordinator.get(key)
            if value is not None:
                return value

            value = await _invoke_fetch(fetch_func, key)
            await self.coordinator.set(key, value, ttl_seconds=ttl_seconds)
            return value

    async def xfetch_operation(
        self,
        key: str,
        fetch_func: Any,
        update_func: Any = None,
    ) -> Dict[str, Any]:
        return await self.xfetch.xfetch(key, fetch_func, update_func)

    async def prevent_stampede_and_fetch(
        self,
        key: str,
        fetch_func: Any,
        ttl_seconds: int = 60,
    ) -> Dict[str, Any]:
        value = await self.stampede_prevention(key, fetch_func, ttl_seconds)
        return {
            "success": value is not None,
            "key": key,
            "value": value,
            "timestamp": datetime.now().isoformat(),
        }


_global_stampede_prevention = StampedePrevention()


async def prevent_cache_stampede(
    key: str,
    fetch_func: Any,
    ttl_seconds: int = 60,
) -> Optional[Any]:
    return await _global_stampede_prevention.stampede_prevention(key, fetch_func, ttl_seconds)


_global_xfetch_algorithm = XFetchAlgorithm()


async def xfetch_operation(
    key: str,
    fetch_func: Any,
    update_func: Any = None,
) -> Dict[str, Any]:
    return await _global_xfetch_algorithm.xfetch(key, fetch_func, update_func)


async def warm_cache(
    keys: List[str],
    fetch_func: Any,
    batch_size: int = 10,
) -> Dict[str, Any]:
    coordinator = DistributedCacheCoordinator()
    return await coordinator.warm_cache(keys, fetch_func, batch_size)


def monitor_cache_health() -> Dict[str, Any]:
    coordinator = DistributedCacheCoordinator()
    return asyncio.run(coordinator.monitor_cache_health())


__all__ = [
    "CacheEntry",
    "StampedeEvent",
    "StampedePrevention",
    "XFetchAlgorithm",
    "DistributedCacheCoordinator",
    "CacheStampedeXFetch",
    "prevent_cache_stampede",
    "xfetch_operation",
    "warm_cache",
    "monitor_cache_health",
]
