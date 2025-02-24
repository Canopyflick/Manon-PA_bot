# utils/helpers.py
import logging, re
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Define the Berlin timezone
BERLIN_TZ = ZoneInfo("Europe/Berlin")



def escape_markdown_v2(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))


