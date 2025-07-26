"""Timezone utilities for the application."""

from datetime import datetime, timedelta, timezone
from pytz import timezone as pytz_timezone
import pytz

# Define IST timezone
IST = pytz_timezone('Asia/Kolkata')


def get_ist_now() -> datetime:
    """
    Get current IST time as a naive datetime (no tzinfo attached).
    Internally it's in IST but tzinfo is stripped to avoid +05:30 in outputs.
    """
    return datetime.now(IST).replace(tzinfo=None)


def convert_to_ist(dt: datetime) -> datetime:
    """
    Convert any datetime to timezone-aware IST datetime.
    Returns aware datetime (with +05:30 offset).
    """
    if dt is None:
        return None
    try:
        if dt.tzinfo is None:
            # Naive datetime: localize it to IST
            return IST.localize(dt)
        # Aware datetime: convert to IST
        return dt.astimezone(IST)
    except Exception:
        try:
            return IST.localize(dt)
        except Exception:
            return dt


def format_ist_datetime(dt: datetime) -> str:
    """
    Convert datetime to IST and return ISO format string without +05:30.
    Example: '2025-07-26T17:02:53.566039'
    """
    if dt is None:
        return None
    try:
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        ist_dt = dt.astimezone(IST)
        # Remove tzinfo for clean output
        return ist_dt.replace(tzinfo=None).isoformat(timespec='microseconds')
    except Exception:
        return dt.replace(tzinfo=None).isoformat(timespec='microseconds') if dt else None
