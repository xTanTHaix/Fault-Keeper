"""Tests for Timezone Drift & DST Trap Detector."""

from __future__ import annotations

import datetime
import zoneinfo

import pytest

from fault_keeper.num.tc_gtc_timezone import (
    TimezoneDriftDetector,
    DSTTrapDetector,
    TimezoneConfig,
    detect_timezone_drift,
    detect_dst_traps,
    normalize_timestamp,
    validate_timezone_config,
)


@pytest.fixture
def drift_detector():
    """Create timezone drift detector."""
    return TimezoneDriftDetector()


@pytest.fixture
def dst_detector():
    """Create DST trap detector."""
    return DSTTrapDetector()


@pytest.fixture
def utc_config():
    """UTC timezone configuration."""
    return TimezoneConfig(
        name="UTC",
        offset_hours=0,
        is_dst=False,
        tz_name="UTC",
    )


@pytest.fixture
def bangkok_config():
    """Bangkok timezone configuration."""
    return TimezoneConfig(
        name="Asia/Bangkok",
        offset_hours=7,
        is_dst=False,
        tz_name="ICT",
    )


class TestTimezoneConfig:
    """Tests for TimezoneConfig dataclass."""

    def test_create_utc(self):
        """Test creating UTC config."""
        config = TimezoneConfig(
            name="UTC",
            offset_hours=0,
            is_dst=False,
            tz_name="UTC",
        )

        assert config.name == "UTC"
        assert config.offset_hours == 0

    def test_create_bangkok(self):
        """Test creating Bangkok config."""
        config = TimezoneConfig(
            name="Asia/Bangkok",
            offset_hours=7,
            is_dst=False,
            tz_name="ICT",
        )

        assert config.name == "Asia/Bangkok"


class TestDetectTimezoneDrift:
    """Tests for detect_timezone_drift function."""

    def test_detect_no_drift(self):
        """Test detecting no drift."""
        result = detect_timezone_drift(
            expected_offset=7,
            actual_offset=7,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

        assert result["has_drift"] is False

    def test_detect_drift(self):
        """Test detecting timezone drift."""
        result = detect_timezone_drift(
            expected_offset=7,
            actual_offset=8,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

        assert result["has_drift"] is True


class TestDetectDstTraps:
    """Tests for detect_dst_traps function."""

    def test_detect_no_dst_trap(self):
        """Test detecting no DST trap."""
        result = detect_dst_traps(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            expected_offset=7,
        )

        assert result["has_dst_trap"] is False

    def test_detect_dst_trap(self):
        """Test detecting DST trap."""
        # Simulate DST transition
        result = detect_dst_traps(
            timestamp=datetime.datetime(2023, 3, 12, 2, 0, 0),
            expected_offset=7,
        )

        assert result["has_dst_trap"] is True


class TestNormalizeTimestamp:
    """Tests for normalize_timestamp function."""

    def test_normalize_utc(self):
        """Test normalizing UTC timestamp."""
        ts = datetime.datetime.now(datetime.timezone.utc)
        result = normalize_timestamp(ts, target_tz="UTC")

        assert result.tzinfo is not None

    def test_normalize_to_bangkok(self):
        """Test normalizing to Bangkok timezone."""
        ts = datetime.datetime.now(datetime.timezone.utc)
        result = normalize_timestamp(ts, target_tz="Asia/Bangkok")

        assert result.tzinfo is not None


class TestValidateTimezoneConfig:
    """Tests for validate_timezone_config function."""

    def test_valid_config(self):
        """Test validating valid config."""
        config = TimezoneConfig(
            name="Asia/Bangkok",
            offset_hours=7,
            is_dst=False,
            tz_name="ICT",
        )

        result = validate_timezone_config(config)

        assert result["valid"] is True

    def test_invalid_offset(self):
        """Test validating invalid offset."""
        config = TimezoneConfig(
            name="InvalidTZ",
            offset_hours=999,
            is_dst=False,
            tz_name="Invalid",
        )

        result = validate_timezone_config(config)

        assert result["valid"] is False


class TestTimezoneDriftDetector:
    """Tests for TimezoneDriftDetector class."""

    def test_init(self, drift_detector):
        """Test initializing detector."""
        assert isinstance(drift_detector, TimezoneDriftDetector)

    def test_detect_drift(self, drift_detector):
        """Test detecting timezone drift."""
        result = drift_detector.detect_drift(
            expected_offset=7,
            actual_offset=8,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

        assert result["has_drift"] is True


class TestDstTrapDetector:
    """Tests for DSTTrapDetector class."""

    def test_init(self, dst_detector):
        """Test initializing detector."""
        assert isinstance(dst_detector, DSTTrapDetector)

    def test_detect_dst_trap(self, dst_detector):
        """Test detecting DST trap."""
        result = dst_detector.detect_dst_trap(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            expected_offset=7,
        )

        assert result["has_dst_trap"] is False


class TestEdgeCases:
    """Tests for edge cases."""

    def test_none_timestamp(self):
        """Test with None timestamp."""
        try:
            result = normalize_timestamp(None, target_tz="UTC")
        except Exception:
            pass  # Expected behavior

    def test_invalid_timezone(self):
        """Test with invalid timezone."""
        ts = datetime.datetime.now(datetime.timezone.utc)
        try:
            result = normalize_timestamp(ts, target_tz="Invalid/Zone")
        except Exception:
            pass  # Expected to raise


class TestPerformance:
    """Tests for performance."""

    def test_detect_drift_performance(self, drift_detector):
        """Test drift detection performance."""
        import time

        start_time = time.perf_counter()
        for _ in range(100):
            drift_detector.detect_drift(
                expected_offset=7,
                actual_offset=7,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should be fast (< 50ms)
        assert elapsed_ms < 50


class TestDSTTransitions:
    """Tests for DST transition handling."""

    def test_spring_forward(self):
        """Test spring forward DST transition."""
        # March 12, 2023 - Spring forward in US
        ts = datetime.datetime(2023, 3, 12, 2, 0, 0)
        result = detect_dst_traps(ts, expected_offset=-5)

        assert result["has_dst_trap"] is True

    def test_fall_back(self):
        """Test fall back DST transition."""
        # November 5, 2023 - Fall back in US
        ts = datetime.datetime(2023, 11, 5, 2, 0, 0)
        result = detect_dst_traps(ts, expected_offset=-5)

        assert result["has_dst_trap"] is True


class TestOffsetCalculation:
    """Tests for offset calculation accuracy."""

    def test_utc_offset(self):
        """Test UTC offset calculation."""
        config = TimezoneConfig(
            name="UTC",
            offset_hours=0,
            is_dst=False,
            tz_name="UTC",
        )

        result = validate_timezone_config(config)
        assert result["valid"] is True


class TestTimestampConversion:
    """Tests for timestamp conversion."""

    def test_convert_utc_to_local(self):
        """Test converting UTC to local time."""
        utc_time = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        result = normalize_timestamp(utc_time, target_tz="Asia/Bangkok")

        assert result is not None


class TestClockSkew:
    """Tests for clock skew detection."""

    def test_detect_clock_skew(self):
        """Test detecting clock skew."""
        detector = TimezoneDriftDetector()

        # Simulate clock skew
        skewed_time = datetime.datetime.now(datetime.timezone.utc)
        result = detector.detect_drift(
            expected_offset=7,
            actual_offset=7 + 0.1,  # 6 minutes drift
            timestamp=skewed_time,
        )

        assert result["has_drift"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])