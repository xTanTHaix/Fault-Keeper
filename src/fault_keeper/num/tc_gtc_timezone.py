"""Timezone normalization utilities with DST and YYYY/yyyy format handling."""

from __future__ import annotations

import calendar
import dataclasses
import datetime
from typing import Any, Dict, List, Optional
import zoneinfo


@dataclasses.dataclass
class TimezoneConfig:
    """Configuration for timezone-aware timestamp handling."""

    name: str = "UTC"
    offset_hours: float = 0.0
    is_dst: bool = False
    tz_name: str = "UTC"
    tolerance_seconds: float = 1.0
    use_utc: bool = False
    warn_on_dst_transition: bool = True


class DriftResult(dict):
    """Dictionary subclass supporting backwards-compatible tuple unpacking."""

    def __iter__(self):
        return iter((
            self["has_drift"],
            self.get("drift_seconds", self.get("drift_hours", 0.0) * 3600.0),
            self.get("details"),
        ))


class ValidationResult(dict):
    """Dictionary subclass supporting backwards-compatible tuple unpacking."""

    def __iter__(self):
        return iter((self["valid"], self.get("errors", [])))


def _is_dst_transition_date(dt: datetime.datetime) -> tuple[bool, str]:
    """Check if datetime falls on a standard DST transition day."""
    if dt.tzinfo is not None:
        try:
            tz = dt.tzinfo
            d0 = datetime.datetime(dt.year, dt.month, dt.day, 0, 0, tzinfo=tz)
            d1 = datetime.datetime(dt.year, dt.month, dt.day, 23, 59, tzinfo=tz)
            dst0 = d0.dst() or datetime.timedelta(0)
            dst1 = d1.dst() or datetime.timedelta(0)
            if dst0 != dst1:
                return True, "fall_back" if dst1 < dst0 else "spring_forward"
        except (ValueError, OverflowError):
            pass

    year = dt.year
    # US Second Sunday in March (Spring forward)
    first_mar_weekday = calendar.weekday(year, 3, 1)
    first_mar_sunday = 1 + (6 - first_mar_weekday) % 7
    second_mar_sunday = first_mar_sunday + 7

    # US First Sunday in November (Fall back)
    first_nov_weekday = calendar.weekday(year, 11, 1)
    first_nov_sunday = 1 + (6 - first_nov_weekday) % 7

    # EU Last Sunday in March (Spring forward)
    last_mar_weekday = calendar.weekday(year, 3, 31)
    last_mar_sunday = 31 - (last_mar_weekday - 6) % 7

    # EU Last Sunday in October (Fall back)
    last_oct_weekday = calendar.weekday(year, 10, 31)
    last_oct_sunday = 31 - (last_oct_weekday - 6) % 7

    if dt.month == 3 and dt.day in (second_mar_sunday, last_mar_sunday):
        return True, "spring_forward"
    if (dt.month == 11 and dt.day == first_nov_sunday) or (dt.month == 10 and dt.day == last_oct_sunday):
        return True, "fall_back"

    return False, "none"


class TimezoneDriftDetector:
    """Detector for clock skew and timezone configuration drift."""

    def __init__(self, tolerance_seconds: float = 1.0) -> None:
        self.tolerance_seconds = tolerance_seconds

    def detect_drift(
        self,
        expected_offset: float | datetime.datetime,
        actual_offset: float | datetime.datetime | None = None,
        timestamp: datetime.datetime | None = None,
    ) -> DriftResult:
        """Detect drift between expected offset and actual measured offset."""
        if isinstance(expected_offset, datetime.datetime) and isinstance(actual_offset, datetime.datetime):
            exp_utc = expected_offset.astimezone(datetime.timezone.utc) if expected_offset.tzinfo else expected_offset.replace(tzinfo=datetime.timezone.utc)
            act_utc = actual_offset.astimezone(datetime.timezone.utc) if actual_offset.tzinfo else actual_offset.replace(tzinfo=datetime.timezone.utc)
            drift_seconds = (act_utc - exp_utc).total_seconds()
            drift_hours = drift_seconds / 3600.0
        else:
            def _to_offset_hours(val: Any) -> float:
                if val is None:
                    return 0.0
                if isinstance(val, (int, float)):
                    return float(val)
                if isinstance(val, datetime.datetime):
                    if val.tzinfo is not None:
                        off = val.utcoffset()
                        if off is not None:
                            return off.total_seconds() / 3600.0
                    return 0.0
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return 0.0

            exp_val = _to_offset_hours(expected_offset)
            act_val = _to_offset_hours(actual_offset)
            drift_hours = act_val - exp_val
            drift_seconds = abs(drift_hours) * 3600.0

        tolerance_hours = self.tolerance_seconds / 3600.0
        has_drift = abs(drift_hours) > tolerance_hours

        details = (
            f"Timezone drift detected: {drift_hours:+.4f} hours ({drift_seconds:.1f}s)"
            if has_drift else "No drift detected"
        )

        return DriftResult({
            "has_drift": bool(has_drift),
            "drift_hours": float(drift_hours),
            "drift_seconds": float(drift_seconds),
            "details": details,
        })


class DSTTrapDetector:
    """Detector for daylight saving time boundary traps and ambiguous periods."""

    def __init__(self) -> None:
        pass

    def detect_dst_trap(
        self,
        timestamp: datetime.datetime | None = None,
        expected_offset: float = 0.0,
    ) -> dict[str, Any]:
        """Detect if timestamp falls within a dangerous DST transition window."""
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc)

        has_trap, transition_type = _is_dst_transition_date(timestamp)

        warning = (
            f"DST transition trap detected ({transition_type})"
            if has_trap else "No DST trap"
        )

        return {
            "has_dst_trap": bool(has_trap),
            "transition_type": transition_type,
            "warning": warning,
            "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
            "expected_offset": expected_offset,
        }


def detect_timezone_drift(
    expected_offset: float | datetime.datetime | None = None,
    actual_offset: float | datetime.datetime | None = None,
    timestamp: datetime.datetime | None = None,
    config: TimezoneConfig | None = None,
    expected_time: datetime.datetime | None = None,
    actual_time: datetime.datetime | None = None,
    **kwargs: Any,
) -> DriftResult:
    """Detect timezone drift supporting both offset-based and datetime-based inputs."""
    tol = config.tolerance_seconds if config is not None else 1.0
    detector = TimezoneDriftDetector(tolerance_seconds=tol)

    if expected_time is not None and actual_time is not None:
        return detector.detect_drift(expected_time, actual_time, timestamp)

    return detector.detect_drift(expected_offset or 0.0, actual_offset or 0.0, timestamp)


def detect_dst_traps(
    timestamp: datetime.datetime | str | None = None,
    expected_offset: float = 0.0,
    tz_name: str | None = None,
    datetime_to_check: datetime.datetime | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Detect DST transition traps supporting both timestamp and timezone name inputs."""
    detector = DSTTrapDetector()

    if isinstance(timestamp, str) and tz_name is None:
        tz_name = timestamp
        timestamp = datetime_to_check

    if isinstance(timestamp, datetime.datetime):
        return detector.detect_dst_trap(timestamp, expected_offset)

    if tz_name is not None:
        try:
            tz = zoneinfo.ZoneInfo(tz_name)
            check_dt = timestamp or datetime.datetime.now(tz)
            dst_offset = check_dt.dst()
            is_dst_active_val = dst_offset is not None and dst_offset > datetime.timedelta(0)
            has_trap, transition_type = _is_dst_transition_date(check_dt)
            return {
                "timezone": tz_name,
                "datetime": check_dt.isoformat(),
                "is_dst": bool(is_dst_active_val),
                "has_dst_trap": bool(has_trap),
                "transition_type": transition_type,
                "dst_offset_seconds": dst_offset.total_seconds() if dst_offset else 0,
                "utc_offset_seconds": check_dt.utcoffset().total_seconds() if check_dt.utcoffset() else 0,
            }
        except zoneinfo.ZoneInfoNotFoundError:
            raise ValueError(f"Unknown timezone: {tz_name}")

    return detector.detect_dst_trap(datetime.datetime.now(datetime.timezone.utc), expected_offset)


def validate_timezone_config(config: TimezoneConfig) -> ValidationResult:
    """Validate timezone configuration object."""
    errors: List[str] = []

    if not config.name:
        errors.append("Timezone name cannot be empty")

    if abs(config.offset_hours) > 14:
        errors.append(f"Invalid offset hours: {config.offset_hours} (must be between -14 and 14)")

    try:
        zoneinfo.ZoneInfo(config.name)
    except Exception:
        errors.append(f"Invalid timezone: {config.name}")

    if config.tolerance_seconds < 0:
        errors.append("Tolerance seconds cannot be negative")

    is_valid = len(errors) == 0
    return ValidationResult({"valid": is_valid, "errors": errors})


def normalize_timestamp(
    timestamp: datetime.datetime | None,
    target_tz: str | None = None,
) -> datetime.datetime:
    """Normalize timestamp to UTC or specified target timezone."""
    if timestamp is None:
        raise TypeError("timestamp cannot be None")

    if target_tz is None:
        target_tz = "UTC"

    if target_tz.upper() in ("UTC", "ETC/UTC", "Z"):
        tz: datetime.tzinfo = datetime.timezone.utc
    else:
        try:
            tz = zoneinfo.ZoneInfo(target_tz)
        except Exception as e:
            raise ValueError(f"Unknown timezone: {target_tz}") from e

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)

    try:
        return timestamp.astimezone(tz)
    except OverflowError:
        if timestamp.year >= 9999:
            return datetime.datetime.max.replace(tzinfo=tz)
        return datetime.datetime.min.replace(tzinfo=tz)


def get_timezone_info(tz_name: str) -> Dict[str, Any]:
    """Get information about a timezone."""
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
        now_tz = datetime.datetime.now(tz)
        utc_offset = now_tz.utcoffset()
        dst_info = now_tz.dst()
        is_dst = dst_info is not None and dst_info > datetime.timedelta(0)

        return {
            "name": tz_name,
            "utc_offset_seconds": utc_offset.total_seconds() if utc_offset else 0,
            "is_dst": bool(is_dst),
            "dst_offset_seconds": dst_info.total_seconds() if dst_info and is_dst else 0,
        }
    except zoneinfo.ZoneInfoNotFoundError:
        raise ValueError(f"Unknown timezone: {tz_name}")


def detect_YYYY_format_error(date_string: str) -> tuple[bool, Optional[str]]:
    """Detect if a date string uses YYYY format."""
    import re
    year_pattern = r'\b\d{4}\b'
    if not re.search(year_pattern, date_string):
        return False, None

    potential_issues = [
        (r'\d{2}-\d{2} \d{2}:\d{2}', "ISO 8601 format detected"),
        (r'\d{4}/\d{2}/\d{2}', "YYYY/MM/DD format detected"),
    ]

    for pattern, msg in potential_issues:
        if re.search(pattern, date_string):
            return True, msg

    return False, None


def is_dst_active(tz_name: str, check_date: datetime.date | None = None) -> bool:
    """Check if DST is active for a given timezone and date."""
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
        if check_date is None:
            now_tz = datetime.datetime.now(tz)
        else:
            now_tz = datetime.datetime.combine(check_date, datetime.time.min, tzinfo=tz)

        dst_offset = now_tz.dst()
        return dst_offset is not None and dst_offset > datetime.timedelta(0)
    except zoneinfo.ZoneInfoNotFoundError:
        raise ValueError(f"Unknown timezone: {tz_name}")


def get_dst_transition_times(tz_name: str, year: int | None = None) -> tuple[datetime.datetime, datetime.datetime] | None:
    """Get DST transition times for a given year."""
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
        if year is None:
            year = datetime.datetime.now().year

        spring_date = None
        fall_date = None

        num_days = 366 if calendar.isleap(year) else 365
        prev_dst: Optional[datetime.timedelta] = None

        try:
            first_dt = datetime.datetime(year, 1, 1, 12, 0, tzinfo=tz)
            prev_dst = first_dt.dst()
        except (ValueError, OverflowError):
            prev_dst = None

        for day in range(1, num_days):
            try:
                dt = datetime.datetime(year, 1, 1, 12, 0, tzinfo=tz) + datetime.timedelta(days=day)
                cur_dst = dt.dst()
                if prev_dst is not None and cur_dst is not None and cur_dst != prev_dst:
                    if cur_dst > prev_dst and spring_date is None:
                        spring_date = dt.date()
                    elif cur_dst < prev_dst and fall_date is None:
                        fall_date = dt.date()
                prev_dst = cur_dst
            except (ValueError, OverflowError):
                continue

        return (spring_date, fall_date)
    except zoneinfo.ZoneInfoNotFoundError:
        raise ValueError(f"Unknown timezone: {tz_name}")


__all__: list[str] = [
    "TimezoneConfig",
    "TimezoneDriftDetector",
    "DSTTrapDetector",
    "detect_timezone_drift",
    "detect_dst_traps",
    "validate_timezone_config",
    "normalize_timestamp",
    "get_timezone_info",
    "detect_YYYY_format_error",
    "is_dst_active",
    "get_dst_transition_times",
]
