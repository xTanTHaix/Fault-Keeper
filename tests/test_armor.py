"""Tests for One-Line Auto Armor (@guard / @protect)."""

import asyncio
import time
import pytest
import fault_keeper as fk
from fault_keeper.core.armor import ArmorViolationError


def test_guard_sync_basic():
    """Test standard sync function decorated with @fk.guard."""
    @fk.guard
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    assert add(10, 20) == 30
    assert add.__name__ == "add"
    assert add.__doc__ == "Add two numbers."


@pytest.mark.asyncio
async def test_guard_async_basic():
    """Test async coroutine decorated with @fk.guard."""
    @fk.guard
    async def async_fetch_val(x: int) -> int:
        """Fetch async value."""
        await asyncio.sleep(0.01)
        return x * 2

    res = await async_fetch_val(21)
    assert res == 42
    assert async_fetch_val.__name__ == "async_fetch_val"


def test_guard_sync_timeout_violation():
    """Test sync function latency budget violation raises ArmorViolationError."""
    @fk.guard(timeout_s=0.05)
    def slow_task() -> str:
        time.sleep(0.08)
        return "done"

    with pytest.raises(ArmorViolationError) as exc_info:
        slow_task()

    assert "exceeding budget of 0.05s" in str(exc_info.value)


@pytest.mark.asyncio
async def test_guard_async_timeout_violation():
    """Test async coroutine latency budget violation raises ArmorViolationError."""
    @fk.guard(timeout_s=0.05)
    async def slow_async_task() -> str:
        await asyncio.sleep(0.1)
        return "done"

    with pytest.raises(ArmorViolationError) as exc_info:
        await slow_async_task()

    assert "exceeded latency budget of 0.05s" in str(exc_info.value)


def test_guard_ordered_locks_havender():
    """Test Havender lock ordering enforcement on given keys."""
    locks = [99, 12, 45, 1, 88]

    @fk.guard(ordered_locks=locks)
    def transaction_step() -> str:
        return "transacted"

    assert transaction_step() == "transacted"


def test_protect_and_armored_aliases():
    """Verify @protect and @armored aliases function identically."""
    @fk.protect
    def p_func() -> str:
        return "protected"

    @fk.armored
    def a_func() -> str:
        return "armored"

    assert p_func() == "protected"
    assert a_func() == "armored"


def test_exception_propagation():
    """Verify real application exceptions are preserved accurately."""
    @fk.guard
    def failing_func():
        raise ValueError("Invalid state payload")

    with pytest.raises(ValueError, match="Invalid state payload"):
        failing_func()
