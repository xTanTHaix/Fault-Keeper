"""Tests for Dependency Hell Resolver."""

from __future__ import annotations

import pytest

from fault_keeper.workflow.ssdl_dependency_hell import (
    DependencyHellResolver,
    PackageConflict,
    resolve_dependencies,
)


@pytest.fixture
def resolver():
    """Create dependency hell resolver instance."""
    return DependencyHellResolver()


class TestDependencyHellResolver:
    """Tests for DependencyHellResolver class."""

    def test_init(self, resolver):
        """Test initializing resolver."""
        assert isinstance(resolver, DependencyHellResolver)

    def test_resolve_simple(self, resolver):
        """Test resolving simple dependency conflict."""
        conflicts = [
            {"package": "requests", "version_a": "2.28.0", "version_b": "2.29.0"},
        ]
        result = resolver.resolve(conflicts)

        assert result is not None


class TestPackageConflict:
    """Tests for PackageConflict dataclass."""

    def test_create_conflict(self):
        """Test creating package conflict."""
        conflict = PackageConflict(
            package="numpy",
            required_by=["package_a"],
            versions=["1.20.0", "1.24.0"],
        )

        assert conflict.package == "numpy"


class TestResolveDependencies:
    """Tests for resolve_dependencies function."""

    def test_resolve_valid(self):
        """Test resolving dependencies."""
        packages = ["requests", "numpy", "pandas"]
        result = resolve_dependencies(packages)

        assert result is not None


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_packages(self):
        """Test with empty packages list."""
        result = resolve_dependencies([])

        assert result is not None

    def test_single_package(self):
        """Test with single package."""
        result = resolve_dependencies(["requests"])

        assert result is not None


class TestPerformance:
    """Tests for performance."""

    def test_resolve_performance(self, resolver):
        """Test resolution performance."""
        import time

        conflicts = [
            {"package": f"pkg_{i}", "version_a": "1.0", "version_b": "2.0"}
            for i in range(50)
        ]

        start_time = time.perf_counter()
        for _ in range(10):
            resolver.resolve(conflicts)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should be fast (< 50ms)
        assert elapsed_ms < 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])