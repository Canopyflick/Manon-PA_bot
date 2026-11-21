"""House commands. /door is the last three front-door changes. /sensors is the live reading."""

import os
from datetime import datetime

import httpx

from features.help.command import is_user_ben
from features.home.format import format_door, format_sensors
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


async def sensors_command(update, context):
    if not is_user_ben(update):
        await update.message.reply_text(RESTRICTED)
        return
    payload = await fetch_readings()
    if payload is None:
        await update.message.reply_text(UNAVAILABLE)
        return
    await update.message.reply_text(format_sensors(payload))


async def fetch_readings() -> dict | None:
    url = os.environ.get("HOME_API_URL", "").rstrip("/")
    token = os.environ.get("HOME_API_TOKEN", "")
    if not url or not token:
        return None
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                f"{url}/v1/readings",
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    if not isinstance(body, dict):
        return None
    return body
