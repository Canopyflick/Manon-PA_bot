import asyncio
import re
from datetime import date, datetime, timedelta

from LLMs.config import shared_state
from LLMs.orchestration import logger, get_input_variables, run_chain
from LLMs.structured_output_schemas import DiaryHeader
from telegram_helpers.delete_message import delete_message, add_delete_button
from utils.helpers import BERLIN_TZ

INTERVAL_OFFSETS = {
    "day": (-1, 1),
    "week": (-7, 7),
    "month": (-30, 30),
    "quarter": (-90, 90),
    "year": (-365, 365),
}

LINK_DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2}),?\s*(\w{3})")
CMD_PATTERN = re.compile(r"^/(?:diary|header)\b", re.IGNORECASE)
LEGACY_NAV_LABEL = re.compile(r">> \((\w+)\)\s*$", re.MULTILINE)

RELATIVE_DATES = {
    "today": 0,
    "yesterday": -1,
    "tomorrow": 1,
}

header_top = """\
---
Heading:
Comfort:
Home (Leipzig): true
Walk >30mins.: false
Whereabouts:
Sports:
Drugs:
E:
Purchases:
Meditate:
Interessant:
---
"""

header_footer = """\
[[_The Hotseat]]<<

---

- [ ] 
"""


def format_link_target(d: date) -> str:
    return f"{d.isoformat()}, {d.strftime('%a')}"


def build_interval_nav(base_date: date) -> str:
    lines = []
    for label, (prev_off, next_off) in INTERVAL_OFFSETS.items():
        prev = format_link_target(base_date + timedelta(days=prev_off))
        nxt = format_link_target(base_date + timedelta(days=next_off))
        lines.append(f"<< [[{prev}]] | [[{nxt}]] >> {label}")
    return "\n".join(lines)


def resolve_base_date(user_message: str) -> date | None:
    text = CMD_PATTERN.sub("", user_message or "").strip().lower()
    today = datetime.now(tz=BERLIN_TZ).date()
    if not text:
        return today
    if text in RELATIVE_DATES:
        return today + timedelta(days=RELATIVE_DATES[text])
    match = LINK_DATE_PATTERN.search(user_message)
    if match:
        try:
            return date.fromisoformat(match.group(1))
        except ValueError:
            pass
    return None


def normalize_nav_labels(nav_block: str) -> str:
    return LEGACY_NAV_LABEL.sub(r">> \1", nav_block)


async def diary_header(update, context):
    try:
        logger.info("Diary command triggered")
        input_vars = await get_input_variables(update, context)
        base_date = resolve_base_date(input_vars["user_message"])
        parsed_output = None

        if base_date is not None:
            dates_header = build_interval_nav(base_date)
        else:
            output = await run_chain("diary_header", input_vars)
            parsed_output = DiaryHeader.model_validate(output)
            dates_header = normalize_nav_labels(parsed_output.header)

        header = f"{header_top}{dates_header}\n{header_footer}"

        if parsed_output and shared_state["transparant_mode"]:
            debug_message = await update.message.reply_text(parsed_output)
            await add_delete_button(update, context, debug_message.message_id)
            asyncio.create_task(delete_message(update, context, debug_message.message_id, 120))

        await update.message.reply_text(header)

    except Exception as e:
        await update.message.reply_text(f"Error in diary_header():\n {e}")
        logger.error(f"\n\n🚨 Error in diary_header(): {e}\n\n")
