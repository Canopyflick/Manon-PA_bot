# utils/helpers.py
import logging, re
from datetime import datetime
from zoneinfo import ZoneInfo
from dateutil.parser import parse

logger = logging.getLogger(__name__)

# Define the Berlin timezone
BERLIN_TZ = ZoneInfo("Europe/Berlin")


def parse_reminder_times(time_strings: list[str]) -> list[datetime]:
    """Parse ISO 8601 strings into timezone-aware datetimes (Berlin if naive)."""
    parsed: list[datetime] = []
    for raw in time_strings:
        for part in (segment.strip() for segment in raw.split(",") if segment.strip()):
            reminder_time = parse(part)
            if reminder_time.tzinfo is None:
                reminder_time = reminder_time.replace(tzinfo=BERLIN_TZ)
            parsed.append(reminder_time)
    return parsed



def escape_markdown_v2(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

