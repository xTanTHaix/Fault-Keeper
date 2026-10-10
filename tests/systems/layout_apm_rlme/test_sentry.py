"""Test suite for APM-RLME sentry: LayoutMonitor & APM_RLME_Sentry."""

import pytest
import numpy as np
from fault_keeper.systems.layout_apm_rlme.sentry import (
    LayoutMonitor,
    APM_RLME_Sentry,
    TranspositionEvent,
)
from fault_keeper.systems.layout_apm_rlme.config import APM_RLMEConfig


class TestLayoutMonitor:
    """Tests for layout transition monitor."""

    def test_init(self):
        """Test monitor initialization."""
        monitor = LayoutMonitor()
        assert monitor.total_transpositions == 0
        assert len(monitor.events) == 0

    def test_record_transposition(self):
        """Test recording layout transpositions."""
        monitor = LayoutMonitor()
        monitor.record_transposition(from_layout="AoS", to_layout="SoA", duration_us=12.5)
        monitor.record_transposition(from_layout="SoA", to_layout="AoS", duration_us=17.5)

        assert monitor.total_transpositions == 2
        assert len(monitor.events) == 2
        avg_time = monitor.get_avg_transposition_time()
        assert avg_time == pytest.approx(15.0, rel=1e-3)

    def test_get_stats(self):
        """Test monitor statistics summary."""
        monitor = LayoutMonitor()
        monitor.record_transposition("AoS", "SoA", 20.0)
        stats = monitor.get_stats()
        assert stats["total_transpositions"] == 1
        assert stats["event_count"] == 1
        assert stats["avg_transposition_time_us"] == pytest.approx(20.0)


class TestAPM_RLME_Sentry:
    """Tests for APM_RLME_Sentry orchestrator."""

    def test_init(self):
        """Test sentry initialization."""
        sentry = APM_RLME_Sentry()
        assert sentry.container is not None
        assert sentry.monitor is not None
        assert sentry.transposer is not None
        assert sentry.simd_transposer is not None

    def test_process_data_and_auto_transposition(self):
        """Test data processing with automatic layout adaptation."""
        config = APM_RLMEConfig(transposition_threshold=0.6)
        sentry = APM_RLME_Sentry(config)
        
        data = np.arange(64, dtype=np.float32).reshape(16, 4)

        # Trigger read access patterns
        for _ in range(5):
            out = sentry.process_data(data, is_read=True)

        # Container should detect read-heavy pattern and switch to SoA
        assert sentry.container.current_layout == "SoA"
        # Monitor should have captured the transposition event
        assert sentry.monitor.total_transpositions >= 1
        assert out.shape == (4, 16)

    def test_get_full_stats(self):
        """Test full telemetry report generation."""
        sentry = APM_RLME_Sentry()
        stats = sentry.get_full_stats()
        assert "container_stats" in stats
        assert "monitor_stats" in stats
        assert "simd_info" in stats
