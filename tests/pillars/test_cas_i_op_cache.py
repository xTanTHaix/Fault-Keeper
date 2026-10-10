"""Tests for Cache Stampede & XFetch Algorithm."""

from __future__ import annotations

import asyncio

import pytest

from fault_keeper.num.cas_i_op_cache import (
    CacheEntry,
    DistributedCacheCoordinator,
    StampedePrevention,
    XFetchAlgorithm,
    prevent_cache_stampede,
    xfetch_operation,
    warm_cache,
)


@pytest.fixture
def stampede_prevention():
    """Create stampede prevention instance."""
    return StampedePrevention()


@pytest.fixture
def xfetch_algorithm():
    """Create XFetch algorithm instance."""
    return XFetchAlgorithm()


@pytest.fixture
async def cache_coordinator():
    """Create cache coordinator for testing."""
    return DistributedCacheCoordinator()


class TestStampedePrevention:
    """Tests for StampedePrevention class."""

    @pytest.mark.asyncio
    async def test_acquire_lock(self, stampede_prevention):
        """Test acquiring lock."""
        lock = await stampede_prevention.acquire_lock("test_key")

        assert lock is not None

    @pytest.mark.asyncio
    async def test_release_lock(self, stampede_prevention):
        """Test releasing lock."""
        await stampede_prevention.release_lock("test_key")

        # Should not raise exception

    @pytest.mark.asyncio
    async def test_stampede_prevention(self, stampede_prevention):
        """Test stampede prevention mechanism."""
        async def fetch_func():
            return "cached_data"

        result = await stampede_prevention.stampede_prevention(
            "test_key",
            fetch_func,
            ttl_seconds=60,
        )

        assert result is not None


class TestXFetchAlgorithm:
    """Tests for XFetchAlgorithm class."""

    @pytest.mark.asyncio
    async def test_xfetch_success(self, xfetch_algorithm):
        """Test successful XFetch operation."""
        async def fetch_func(key):
            return {"data": f"value_for_{key}"}

        result = await xfetch_algorithm.xfetch("test_key", fetch_func)

        assert result["success"] is True
        assert "value" in result

    @pytest.mark.asyncio
    async def test_xfetch_cache_miss(self, xfetch_algorithm):
        """Test XFetch operation with cache miss."""
        async def fetch_func(key):
            return {"data": f"value_for_{key}"}

        result = await xfetch_algorithm.xfetch("nonexistent_key", fetch_func)

        assert result["success"] is True


class TestDistributedCacheCoordinator:
    """Tests for DistributedCacheCoordinator class."""

    @pytest.mark.asyncio
    async def test_get(self, cache_coordinator):
        """Test getting value from cache."""
        await cache_coordinator.set("key1", "value1", ttl_seconds=60)
        result = await cache_coordinator.get("key1")

        assert result == "value1"

    @pytest.mark.asyncio
    async def test_set(self, cache_coordinator):
        """Test setting value in cache."""
        result = await cache_coordinator.set("key2", "value2", ttl_seconds=60)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete(self, cache_coordinator):
        """Test deleting value from cache."""
        await cache_coordinator.set("key3", "value3")
        result = await cache_coordinator.delete("key3")

        assert result is True

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache_coordinator):
        """Test invalidating cache by pattern."""
        await cache_coordinator.set("user:1", "data1")
        await cache_coordinator.set("user:2", "data2")

        result = await cache_coordinator.invalidate_pattern("user:")

        assert result["success"] is True
        assert result["invalidated_count"] == 2

    @pytest.mark.asyncio
    async def test_warm_cache(self, cache_coordinator):
        """Test warming cache."""
        async def fetch_func(key):
            return f"value_for_{key}"

        result = await cache_coordinator.warm_cache(
            ["key1", "key2", "key3"],
            fetch_func,
            batch_size=2,
        )

        assert result["success"] is True


class TestPreventCacheStampede:
    """Tests for prevent_cache_stampede function."""

    @pytest.mark.asyncio
    async def test_prevent_stampede(self):
        """Test preventing cache stampede."""
        async def fetch_func():
            return "data"

        result = await prevent_cache_stampede("test_key", fetch_func)

        assert result is not None


class TestXFetchOperation:
    """Tests for xfetch_operation function."""

    @pytest.mark.asyncio
    async def test_xfetch(self):
        """Test XFetch operation."""
        async def fetch_func(key):
            return {"key": key, "value": f"v{key}"}

        result = await xfetch_operation("test_key", fetch_func)

        assert result["success"] is True


class TestWarmCache:
    """Tests for warm_cache function."""

    @pytest.mark.asyncio
    async def test_warm_multiple_keys(self):
        """Test warming multiple cache keys."""
        async def fetch_func(key):
            return f"value_for_{key}"

        result = await warm_cache(
            ["key1", "key2", "key3"],
            fetch_func,
            batch_size=2,
        )

        assert result["success"] is True


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_create_entry(self):
        """Test creating cache entry."""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            version=1,
            hit_count=0,
        )

        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.version == 1


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_empty_cache_operations(self, cache_coordinator):
        """Test operations on empty cache."""
        result = await cache_coordinator.get("nonexistent_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_large_batch_warm(self, cache_coordinator):
        """Test warming large batch of keys."""
        async def fetch_func(key):
            return f"value_for_{key}"

        result = await cache_coordinator.warm_cache(
            [f"key{i}" for i in range(100)],
            fetch_func,
            batch_size=10,
        )

        assert result["success"] is True


class TestPerformance:
    """Tests for performance."""

    @pytest.mark.asyncio
    async def test_cache_get_performance(self, cache_coordinator):
        """Test cache get performance."""
        await cache_coordinator.set("perf_key", "perf_value", ttl_seconds=60)

        import time

        start_time = time.perf_counter()
        for _ in range(100):
            await cache_coordinator.get("perf_key")
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should be fast (< 100ms for 100 gets)
        assert elapsed_ms < 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])