"""Tests for Structural Causal Abduction."""

from __future__ import annotations

import pytest

from fault_keeper.workflow.crcae_root_causal import (
    RootCausalAnalyzer,
    CausalGraph,
    infer_root_cause,
)


@pytest.fixture
def analyzer():
    """Create root causal analyzer instance."""
    return RootCausalAnalyzer()


class TestRootCausalAnalyzer:
    """Tests for RootCausalAnalyzer class."""

    def test_init(self, analyzer):
        """Test initializing analyzer."""
        assert isinstance(analyzer, RootCausalAnalyzer)

    def test_analyze_simple(self, analyzer):
        """Test analyzing simple causal graph."""
        causes = ["network_error", "timeout"]
        effects = ["request_failed"]
        result = analyzer.analyze(causes, effects)

        assert result is not None


class TestCausalGraph:
    """Tests for CausalGraph dataclass."""

    def test_create_graph(self):
        """Test creating causal graph."""
        graph = CausalGraph(
            nodes=["A", "B", "C"],
            edges=[("A", "B"), ("B", "C")],
        )

        assert graph.nodes == ["A", "B", "C"]


class TestInferRootCause:
    """Tests for infer_root_cause function."""

    def test_infer_valid(self):
        """Test inferring root cause."""
        symptoms = ["error_1", "error_2"]
        result = infer_root_cause(symptoms)

        assert result is not None


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_symptoms(self):
        """Test with empty symptoms."""
        result = infer_root_cause([])

        assert result is not None

    def test_single_symptom(self):
        """Test with single symptom."""
        result = infer_root_cause(["single_error"])

        assert result is not None


class TestPerformance:
    """Tests for performance."""

    def test_analyze_performance(self, analyzer):
        """Test analysis performance."""
        import time

        causes = [f"cause_{i}" for i in range(50)]
        effects = ["effect"]

        start_time = time.perf_counter()
        for _ in range(10):
            analyzer.analyze(causes, effects)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should be fast (< 100ms)
        assert elapsed_ms < 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])