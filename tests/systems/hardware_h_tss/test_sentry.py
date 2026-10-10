"""Test suite for H-TSS sentry: UAFMonitor & H_TSS_Sentry."""

import pytest
from fault_keeper.systems.hardware_h_tss.sentry import (
    H_TSS_Sentry,
    UAFMonitor,
    UAFEvent,
    TaggedPointer,
)
from fault_keeper.systems.hardware_h_tss.config import H_TSSConfig


class TestUAFMonitor:
    """Tests for UAF event monitor."""

    def test_init(self):
        """Test UAF monitor initialization."""
        monitor = UAFMonitor()
        assert monitor.total_uaf == 0
        assert len(monitor.events) == 0

    def test_record_uaf(self):
        """Test recording UAF occurrences."""
        monitor = UAFMonitor()
        monitor.record_uaf(address=0x2000, thread_id=42)

        assert monitor.total_uaf == 1
        assert len(monitor.events) == 1
        event = monitor.events[0]
        assert isinstance(event, UAFEvent)
        assert event.address == 0x2000
        assert event.thread_id == 42

    def test_get_stats(self):
        """Test UAF monitor statistics."""
        monitor = UAFMonitor()
        monitor.record_uaf(address=0x1000, thread_id=1)
        stats = monitor.get_stats()

        assert stats["total_uaf"] == 1
        assert stats["event_count"] == 1
        assert stats["uaf_rate"] >= 0.0


class TestH_TSS_Sentry:
    """Tests for H_TSS_Sentry orchestrator."""

    def test_init(self):
        """Test sentry initialization."""
        sentry = H_TSS_Sentry()
        assert sentry.tagger is not None
        assert sentry.overflow_detector is not None
        assert sentry.uaf_monitor is not None
        assert len(sentry.active_pointers) == 0

    def test_allocate_access_and_free(self):
        """Test pointer lifecycle: allocate -> access -> free -> illegal access."""
        sentry = H_TSS_Sentry()

        ptr = sentry.allocate(address=0x4000, size=128)
        assert isinstance(ptr, TaggedPointer)
        assert 0x4000 in sentry.active_pointers

        # Valid access
        assert sentry.access(0x4000) is True

        # Free pointer
        assert sentry.free(0x4000) is True
        assert 0x4000 not in sentry.active_pointers

        # Access freed pointer: should fail and record UAF
        assert sentry.access(0x4000) is False
        assert sentry.uaf_monitor.total_uaf == 1

    def test_check_overflow(self):
        """Test buffer overflow checking via sentry."""
        config = H_TSSConfig(buffer_size_limit=1024)
        sentry = H_TSS_Sentry(config)

        assert sentry.check_overflow(offset=500, size=200) is False
        assert sentry.check_overflow(offset=1000, size=100) is True

    def test_get_stats(self):
        """Test full sentry statistics summary."""
        sentry = H_TSS_Sentry()
        sentry.allocate(address=0x1000, size=32)
        stats = sentry.get_stats()

        assert stats["active_pointers"] == 1
        assert "uaf_monitor_stats" in stats
        assert "overflow_stats" in stats
