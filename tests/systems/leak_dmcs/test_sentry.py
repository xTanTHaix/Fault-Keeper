"""Test suite for DMCS sentry: LeakSentryMonitor & DMCS_Sentry."""

import pytest
from fault_keeper.systems.leak_dmcs.sentry import (
    DMCS_Sentry,
    LeakSentryMonitor,
    LeakRecoveryEvent,
)
from fault_keeper.systems.leak_dmcs.config import DMCSConfig


class TestLeakSentryMonitor:
    """Tests for LeakSentryMonitor."""

    def test_init(self):
        """Test monitor initialization."""
        monitor = LeakSentryMonitor()
        assert monitor.total_reclaimed_blocks == 0
        assert monitor.total_reclaimed_bytes == 0
        assert len(monitor.events) == 0

    def test_record_recovery(self):
        """Test recording leak recovery events."""
        monitor = LeakSentryMonitor()
        monitor.record_recovery(
            blocks_reclaimed=4,
            bytes_reclaimed=4096,
            cut_weight=1.5,
            duration_us=25.0,
        )

        assert monitor.total_reclaimed_blocks == 4
        assert monitor.total_reclaimed_bytes == 4096
        assert len(monitor.events) == 1
        assert monitor.get_avg_recovery_time_us() == pytest.approx(25.0)

    def test_get_stats(self):
        """Test monitor stats summary."""
        monitor = LeakSentryMonitor()
        monitor.record_recovery(2, 2048, 1.0, 10.0)
        stats = monitor.get_stats()

        assert stats["total_events"] == 1
        assert stats["total_reclaimed_blocks"] == 2
        assert stats["total_reclaimed_bytes"] == 2048


class TestDMCS_Sentry:
    """Tests for DMCS_Sentry orchestrator."""

    def test_init(self):
        """Test sentry initialization."""
        sentry = DMCS_Sentry()
        assert sentry.dmcs is not None
        assert sentry.reclamation_monitor is not None
        assert sentry.is_monitoring is False

    def test_monitor_lifecycle(self):
        """Test starting and stopping monitor."""
        sentry = DMCS_Sentry()
        sentry.monitor()
        assert sentry.is_monitoring is True
        sentry.stop()
        assert sentry.is_monitoring is False

    def test_allocate_and_diagnose_reclaim(self):
        """Test allocating, creating a cycle, and reclaiming via sentry."""
        config = DMCSConfig(leak_scan_interval_ms=0.0, min_cut_threshold=0.8)
        sentry = DMCS_Sentry(config)
        sentry.monitor()

        # Allocate root and two cyclic orphaned blocks
        sentry.allocate(address=0x1000, size=2048, thread_id=1)
        sentry.allocate(address=0x2000, size=512, thread_id=1)
        sentry.allocate(address=0x3000, size=512, thread_id=1)

        # Form detached cycle 0x2000 <-> 0x3000
        sentry.add_reference(0x2000, 0x3000)
        sentry.add_reference(0x3000, 0x2000)

        # Diagnose and reclaim
        blocks_reclaimed, bytes_reclaimed = sentry.diagnose_and_reclaim()
        assert blocks_reclaimed > 0
        assert bytes_reclaimed > 0

        # Verify sentry monitor telemetry recorded the event
        mon_stats = sentry.reclamation_monitor.get_stats()
        assert mon_stats["total_events"] >= 1
        assert mon_stats["total_reclaimed_blocks"] == blocks_reclaimed

    def test_get_full_stats(self):
        """Test telemetry reporting."""
        sentry = DMCS_Sentry()
        stats = sentry.get_full_stats()
        assert "dmcs_stats" in stats
        assert "monitor_stats" in stats
        assert "is_monitoring" in stats
