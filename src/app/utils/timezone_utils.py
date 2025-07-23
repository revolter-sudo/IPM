"""Timezone utilities for the application."""

from datetime import datetime
from pytz import timezone

IST = timezone('Asia/Kolkata')

def get_ist_now() -> datetime:
    """Get current time in IST timezone."""
    return datetime.now(IST)

def convert_to_ist(dt: datetime) -> datetime:
    """Convert any datetime to IST timezone."""
    if dt is None:
        return None
    try:
        # If datetime is naive (no timezone info)
        if dt.tzinfo is None:
            # Add IST timezone info
            dt = IST.localize(dt)
        # If datetime has different timezone, convert to IST
        return dt.astimezone(IST)
    except Exception as e:
        # If any error occurs, try to localize
        try:
            return IST.localize(dt)
        except Exception as e2:
            return dt

def format_ist_datetime(dt: datetime) -> str:
    """Format datetime in IST timezone with proper format."""
    if dt is None:
        return None
    try:
        ist_dt = convert_to_ist(dt)
        # Ensure timezone is explicitly shown as +05:30
        return ist_dt.isoformat(timespec='microseconds')
    except Exception:
        # Fallback if formatting fails
        return dt.isoformat() if dt else None
