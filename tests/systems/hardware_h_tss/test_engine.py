"""Test suite for H-TSS engine: Hardware Pointer Tagging & Buffer Overflow Detection."""

import pytest
import threading
from fault_keeper.systems.hardware_h_tss.engine import (
    H_TSSConfig,
    TaggedPointer,
    PointerTagger,
    BufferOverflowDetector,
    HardwarePointerTagging,
)


class TestPointerTagger:
    """Tests for PointerTagger."""

    def test_tag_pointer(self):
        """Test pointer tagging."""
        tagger = PointerTagger(tag_bits=4)
        ptr = tagger.tag_pointer(0x1008, thread_id=123)

        assert isinstance(ptr, TaggedPointer)
        assert ptr.address == 0x1008
        assert ptr.tag == (0x1008 & 0xF)
        assert ptr.is_valid is True
        assert ptr.thread_id == 123

    def test_validate_and_untag(self):
        """Test pointer validation and untagging."""
        tagger = PointerTagger()
        ptr = tagger.tag_pointer(0x2000, thread_id=1)

        # Validate while valid
        validated = tagger.validate_pointer(0x2000)
        assert validated is not None
        assert validated.is_valid is True

        # Untag pointer
        success = tagger.untag_pointer(0x2000)
        assert success is True

        # Validate after untagging
        validated_after = tagger.validate_pointer(0x2000)
        assert validated_after is not None
        assert validated_after.is_valid is False

    def test_check_uaf(self):
        """Test use-after-free detection on tagged pointers."""
        tagger = PointerTagger()
        tagger.tag_pointer(0x3000, thread_id=1)
        assert tagger.check_uaf(0x3000) is False

        tagger.untag_pointer(0x3000)
        assert tagger.check_uaf(0x3000) is True

    def test_get_active_pointers(self):
        """Test retrieving list of active pointers."""
        tagger = PointerTagger()
        tagger.tag_pointer(0x100, 1)
        tagger.tag_pointer(0x200, 1)
        assert len(tagger.get_active_pointers()) == 2

        tagger.untag_pointer(0x100)
        active = tagger.get_active_pointers()
        assert len(active) == 1
        assert active[0].address == 0x200


class TestBufferOverflowDetector:
    """Tests for BufferOverflowDetector."""

    def test_check_overflow(self):
        """Test overflow detection boundary conditions."""
        detector = BufferOverflowDetector(buffer_size_limit=1024)

        # In bounds
        assert detector.check_overflow(offset=500, size=500) is False
        assert detector.overflow_count == 0

        # Out of bounds
        assert detector.check_overflow(offset=1000, size=50) is True
        assert detector.overflow_count == 1

    def test_get_overflow_stats(self):
        """Test overflow statistics reporting."""
        detector = BufferOverflowDetector(buffer_size_limit=100)
        detector.check_overflow(offset=80, size=30)
        stats = detector.get_overflow_stats()

        assert stats["overflow_count"] == 1
        assert len(stats["overflow_history"]) == 1
        assert stats["overflow_history"][0]["offset"] == 80


class TestHardwarePointerTagging:
    """Tests for HardwarePointerTagging orchestrator."""

    def test_allocate_and_access(self):
        """Test valid pointer allocation and access."""
        hpt = HardwarePointerTagging()
        ptr = hpt.allocate_tagged(address=0x1000, size=64)

        assert ptr is not None
        assert 0x1000 in hpt.active_pointers
        assert hpt.access_pointer(0x1000) is True

    def test_buffer_overflow_raises_error(self):
        """Test that allocation exceeding buffer limit raises ValueError."""
        config = H_TSSConfig(buffer_size_limit=512)
        hpt = HardwarePointerTagging(config)

        with pytest.raises(ValueError, match="Buffer overflow detected"):
            hpt.allocate_tagged(address=500, size=50)

    def test_free_and_uaf_abort(self):
        """Test freeing pointer and subsequent UAF abort trigger."""
        config = H_TSSConfig(tag_mismatch_action="abort", validate_on_access=True)
        hpt = HardwarePointerTagging(config)

        hpt.allocate_tagged(0x5000, 32)
        freed = hpt.free_pointer(0x5000)
        assert freed is True
        assert hpt.check_uaf(0x5000) is True

        with pytest.raises(RuntimeError, match="Use-after-free detected!"):
            hpt.access_pointer(0x5000)

    def test_get_stats(self):
        """Test statistics reporting."""
        hpt = HardwarePointerTagging()
        hpt.allocate_tagged(0x1000, 16)
        stats = hpt.get_stats()

        assert stats["active_pointers"] == 1
        assert stats["tagged_pointers_count"] == 1
        assert "overflow_stats" in stats
