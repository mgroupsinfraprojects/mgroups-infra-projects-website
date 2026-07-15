from datetime import datetime
from zoneinfo import ZoneInfo

APP_TZ = ZoneInfo("Asia/Kolkata")

def now_ist():
    """Current India local time stored as a naive datetime for SQLite compatibility.

    SQLite does not preserve tzinfo when SQLAlchemy DateTime is round-tripped.
    For this single-timezone India deployment, storing naive IST is explicit and
    avoids the misleading DateTime(timezone=True) schema flag.
    """
    return datetime.now(APP_TZ).replace(tzinfo=None)

def today_code():
    return now_ist().strftime("%Y%m%d")

def timestamp_code():
    return now_ist().strftime("%Y%m%d_%H%M%S")

def html_datetime_value(dt=None):
    """Value for <input type='datetime-local'>; browser wants no timezone suffix."""
    value = dt or now_ist()
    if getattr(value, "tzinfo", None) is not None:
        value = value.astimezone(APP_TZ).replace(tzinfo=None)
    return value.strftime("%Y-%m-%dT%H:%M")

def parse_local_datetime(value):
    """Parse HTML datetime/date input as naive IST local time."""
    if not value:
        return now_ist()
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return now_ist()
