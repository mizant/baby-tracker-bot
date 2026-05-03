from datetime import datetime, timezone as tz
from pytz import timezone
from app.config import TIMEZONE


def format_time(dt: datetime) -> str:
    # If datetime is naive (no tzinfo), assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.utc)
    tz_local = timezone(TIMEZONE)
    local_time = dt.astimezone(tz_local)
    return local_time.strftime("%H:%M")


def format_duration(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours} ч {minutes} мин"
    return f"{minutes} мин"


def format_datetime(dt: datetime) -> str:
    # If datetime is naive (no tzinfo), assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.utc)
    tz_local = timezone(TIMEZONE)
    local_time = dt.astimezone(tz_local)
    return local_time.strftime("%d.%m.%Y %H:%M")


def format_datetime_full(dt: datetime) -> str:
    """Format date and time with full date display"""
    # If datetime is naive (no tzinfo), assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.utc)
    tz_local = timezone(TIMEZONE)
    local_time = dt.astimezone(tz_local)
    return local_time.strftime("%d.%m.%Y %H:%M")
