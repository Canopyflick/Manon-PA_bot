# utils/helpers.py
import logging, re
from datetime import datetime
from zoneinfo import ZoneInfo
from dateutil.parser import parse

logger = logging.getLogger(__name__)

# Define the Berlin timezone
BERLIN_TZ = ZoneInfo("Europe/Berlin")

# Shown on postpone buttons and charged on postpone and on late cancellation.
POSTPONE_PENALTY_MULTIPLIER = 0.65

_DATETIME_NOISE = re.compile(r"[\[\]\"'`]+")


def parse_datetime_loose(value):
    """Parse a datetime from an ISO string, a datetime, or messy LLM output.

    Strips brackets, quotes, and whitespace. Naive datetimes get Berlin tz.
    Returns None when the value cannot be parsed.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = _DATETIME_NOISE.sub("", str(value)).strip()
        if not text:
            return None
        try:
            dt = parse(text)
        except (ValueError, TypeError, OverflowError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BERLIN_TZ)
    return dt.astimezone(BERLIN_TZ)


def format_when(value, now=None) -> str:
    """Minimal human-readable datetime for user-facing messages.

    today 22:22 / tomorrow 22:22 / yesterday 22:22 / Wed 22:22 (2-6 days ahead),
    otherwise Mon 12 Oct, 22:22, with the year only when it differs from now.
    Unparseable values are returned with surrounding brackets stripped.
    """
    dt = parse_datetime_loose(value)
    if dt is None:
        text = _DATETIME_NOISE.sub("", str(value or "")).strip()
        return text or "unknown time"

    now = now or datetime.now(tz=BERLIN_TZ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=BERLIN_TZ)
    else:
        now = now.astimezone(BERLIN_TZ)

    clock = dt.strftime("%H:%M")
    day_delta = (dt.date() - now.date()).days
    if day_delta == 0:
        return f"today {clock}"
    if day_delta == 1:
        return f"tomorrow {clock}"
    if day_delta == -1:
        return f"yesterday {clock}"
    if 2 <= day_delta <= 6:
        return f"{dt.strftime('%a')} {clock}"

    date_part = f"{dt.strftime('%a')} {dt.day} {dt.strftime('%b')}"
    if dt.year != now.year:
        date_part = f"{date_part} {dt.year}"
    return f"{date_part}, {clock}"


def format_for_llm(value) -> str:
    """Unambiguous datetime for LLM context: 'Mon 2026-10-05 22:22'."""
    dt = parse_datetime_loose(value)
    if dt is None:
        return "none" if value is None else str(value)
    return dt.strftime("%a %Y-%m-%d %H:%M")


def parse_reminder_times(time_strings: list[str]) -> list[datetime]:
    """Parse ISO 8601 strings into timezone-aware datetimes (Berlin if naive)."""
    parsed: list[datetime] = []
    for raw in time_strings:
        for part in (segment.strip() for segment in raw.split(",") if segment.strip()):
            reminder_time = parse_datetime_loose(part)
            if reminder_time is not None:
                parsed.append(reminder_time)
    return parsed



def escape_markdown_v2(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

