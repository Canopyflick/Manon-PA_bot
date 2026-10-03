# features/goals/cancel.py
"""Cancel a goal or a recurring series, with a 12-hour free window and Undo."""
import logging
import re
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from utils.db import Database, update_goal_data, update_user_data
from utils.helpers import BERLIN_TZ, POSTPONE_PENALTY_MULTIPLIER
from utils.session_avatar import PA

logger = logging.getLogger(__name__)

FREE_CANCEL_WINDOW = timedelta(hours=12)
_OPEN_STATUSES = ("pending", "paused", "prepared")


def _aware(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=BERLIN_TZ)
    return value.astimezone(BERLIN_TZ)


def cancellation_charge(set_time, penalty, now) -> float:
    """Score to subtract when cancelling. 0 inside the free window or when there is no penalty.

    ``now`` is the moment of cancellation. Pass the original cancellation time on undo
    so the refund matches what was charged.
    """
    if penalty is None or float(penalty) <= 0:
        return 0.0
    set_at = _aware(set_time)
    moment = _aware(now)
    if set_at is not None and moment is not None and moment - set_at <= FREE_CANCEL_WINDOW:
        return 0.0
    return round(float(penalty) * POSTPONE_PENALTY_MULTIPLIER, 1)


def pick_charge_row(rows):
    """The instance that pays: earliest deadline, including one already overdue."""
    dated = [row for row in rows if row.get("deadline") is not None]
    if not dated:
        return None
    return min(dated, key=lambda row: _aware(row["deadline"]))


def charge_label(amount, set_time, now) -> str:
    if amount:
        return f"(-{amount})"
    set_at = _aware(set_time)
    moment = _aware(now)
    if set_at is not None and moment is not None and moment - set_at <= FREE_CANCEL_WINDOW:
        return "(free, set <12h ago)"
    return "(free)"


async def _rows_to_cancel(user_id, chat_id, goal_id, scope):
    async with Database.acquire() as conn:
        anchor = await conn.fetchrow(
            """
            SELECT * FROM manon_goals
            WHERE goal_id = $1 AND user_id = $2 AND chat_id = $3
            """,
            goal_id,
            user_id,
            chat_id,
        )
        if not anchor or anchor["status"] not in _OPEN_STATUSES:
            return []
        if scope != "series":
            return [anchor]
        series_id = anchor["group_id"] or anchor["goal_id"]
        rows = await conn.fetch(
            """
            SELECT * FROM manon_goals
            WHERE user_id = $1 AND chat_id = $2
              AND status IN ('pending', 'paused', 'prepared')
              AND COALESCE(group_id, goal_id) = $3
            ORDER BY deadline ASC NULLS LAST, goal_id ASC
            """,
            user_id,
            chat_id,
            series_id,
        )
    return list(rows)


async def _refresh_reminders(bot):
    try:
        from features.reminders.reminders import check_upcoming_reminders
        await check_upcoming_reminders(bot)
    except Exception as e:
        logger.error(f"Could not refresh reminders after a goal cancellation change: {e}")


async def cancel_goal_selection(update, context, goal_id, scope):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    rows = await _rows_to_cancel(user_id, chat_id, goal_id, scope)
    if not rows:
        await update.message.reply_text(f"Couldn't cancel #{goal_id} {PA}")
        return

    now = datetime.now(tz=BERLIN_TZ)
    charge_row = pick_charge_row(rows)
    if charge_row is None:
        amount = 0.0
        charged_set_time = rows[0]["set_time"]
    else:
        amount = cancellation_charge(charge_row["set_time"], charge_row["penalty"], now)
        charged_set_time = charge_row["set_time"]

    for row in rows:
        await update_goal_data(row["goal_id"], status="archived_canceled", completion_time=now)

    pending_count = sum(1 for row in rows if row["status"] == "pending")
    user_updates = {}
    if pending_count:
        user_updates["increment_pending_goals"] = -pending_count
    if amount:
        user_updates["increment_score"] = -amount
        user_updates["increment_penalties_accrued"] = amount
    if user_updates:
        await update_user_data(user_id, chat_id, **user_updates)

    anchor = next((row for row in rows if row["goal_id"] == goal_id), rows[0])
    description = anchor["goal_description"] or "No description"
    extra = len(rows) - 1
    text = f"🗑️ *Canceled* #{anchor['goal_id']}\n✍️ _{description}_"
    if extra:
        noun = "instance" if extra == 1 else "instances"
        text += f"\n+ {extra} remaining {noun}"
    text += f"\n{charge_label(amount, charged_set_time, now)}"
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("↩️ Undo", callback_data=f"uncancel_{anchor['goal_id']}")]]
    )
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await _refresh_reminders(context.bot)
    logger.info(
        f"Canceled #{anchor['goal_id']} scope={scope} rows={len(rows)} charge={amount}"
    )


async def undo_goal_cancellation(update, context):
    query = update.callback_query
    match = re.match(r"^uncancel_(\d+)$", query.data or "")
    if not match:
        await query.answer("Invalid action.")
        return

    goal_id = int(match.group(1))
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    async with Database.acquire() as conn:
        anchor = await conn.fetchrow(
            """
            SELECT * FROM manon_goals
            WHERE goal_id = $1 AND user_id = $2 AND chat_id = $3
            """,
            goal_id,
            user_id,
            chat_id,
        )
        if (
            not anchor
            or anchor["status"] != "archived_canceled"
            or anchor["completion_time"] is None
        ):
            await query.answer("Nothing to undo.")
            return

        series_id = anchor["group_id"] or anchor["goal_id"]
        rows = await conn.fetch(
            """
            SELECT * FROM manon_goals
            WHERE user_id = $1 AND chat_id = $2
              AND status = 'archived_canceled'
              AND completion_time = $3
              AND COALESCE(group_id, goal_id) = $4
            ORDER BY goal_id ASC
            """,
            user_id,
            chat_id,
            anchor["completion_time"],
            series_id,
        )

    if not rows:
        await query.answer("Nothing to undo.")
        return

    completion_time = anchor["completion_time"]
    charge_row = pick_charge_row(rows)
    amount = 0.0
    if charge_row is not None:
        amount = cancellation_charge(
            charge_row["set_time"], charge_row["penalty"], completion_time
        )

    pending_restored = 0
    for row in rows:
        restore = "prepared" if row["timeframe"] == "open-ended" else "pending"
        if restore == "pending":
            pending_restored += 1
        await update_goal_data(row["goal_id"], status=restore, completion_time=None)

    user_updates = {}
    if pending_restored:
        user_updates["increment_pending_goals"] = pending_restored
    if amount:
        user_updates["increment_score"] = amount
        user_updates["increment_penalties_accrued"] = -amount
    if user_updates:
        await update_user_data(user_id, chat_id, **user_updates)

    extra = len(rows) - 1
    text = f"↩️ *Restored* #{goal_id}"
    if extra:
        text += f" and {extra} more"
    if amount:
        text += f"\nRefunded {amount}"
    await query.edit_message_text(text, parse_mode="Markdown")
    await query.answer("Restored.")
    await _refresh_reminders(context.bot)
    logger.info(f"Undid cancellation of #{goal_id} ({len(rows)} rows, refund {amount})")
