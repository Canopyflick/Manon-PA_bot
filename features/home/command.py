"""House commands. /door is the last three front-door changes. /sensors is the live reading."""

import os
from datetime import datetime

import httpx

from features.help.command import is_user_ben
from features.home.format import format_door, format_sensors
from features.home.story import format_story
from utils.helpers import BERLIN_TZ

RESTRICTED = "This command is restricted."
UNAVAILABLE = "The house didn't answer."


async def door_command(update, context):
    if not is_user_ben(update):
        await update.message.reply_text(RESTRICTED)
        return
    payload = await fetch_readings()
    if payload is None:
        await update.message.reply_text(UNAVAILABLE)
        return
    events = payload.get("door_events")
    if not isinstance(events, list):
        events = []
    today = datetime.now(BERLIN_TZ).date()
    await update.message.reply_text(format_door(events, today))


async def home_command(update, context):
    if not is_user_ben(update):
        await update.message.reply_text(RESTRICTED)
        return
    period = _period(update, context) or "today"
    if period not in ("today", "week", "month"):
        await update.message.reply_text("Try /home, /home week, or /home month.")
        return
    payload = await fetch_readings(period)
    if payload is None:
        await update.message.reply_text(UNAVAILABLE)
        return
    await update.message.reply_text(format_story(payload))


def _period(update, context) -> str:
    if context.args:
        return context.args[0].lower()
    text = ""
    if update.message is not None and update.message.text:
        text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        return ""
    return parts[1].split("@", 1)[0].lower()


async def sensors_command(update, context):
    if not is_user_ben(update):
        await update.message.reply_text(RESTRICTED)
        return
    payload = await fetch_readings()
    if payload is None:
        await update.message.reply_text(UNAVAILABLE)
        return
    await update.message.reply_text(format_sensors(payload))


async def fetch_readings(period: str | None = None) -> dict | None:
    url = os.environ.get("HOME_API_URL", "").rstrip("/")
    token = os.environ.get("HOME_API_TOKEN", "")
    if not url or not token:
        return None
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            address = f"{url}/v1/readings"
            if period:
                address = f"{address}?period={period}"
            response = await client.get(
                address,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    if not isinstance(body, dict):
        return None
    return body
