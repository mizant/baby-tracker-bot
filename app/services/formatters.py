from datetime import datetime
from pytz import timezone
from app.config import TIMEZONE


def format_time(dt: datetime) -> str:
    tz = timezone(TIMEZONE)
    local_time = dt.astimezone(tz)
    return local_time.strftime("%H:%M")


def format_duration(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours} ч {minutes} мин"
    return f"{minutes} мин"


def format_datetime(dt: datetime) -> str:
    tz = timezone(TIMEZONE)
    local_time = dt.astimezone(tz)
    return local_time.strftime("%d.%m.%Y %H:%M")
