# features/morning_message/formatter.py
from datetime import datetime, time, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.helpers import BERLIN_TZ
from utils.string_resources import GREETING_GOOD_MORNING, GREETING_WHY_HELLO_THERE


def format_goal_for_overview(goal):
    """Format a single goal for the overview message"""
    today = datetime.now(BERLIN_TZ).date()
    deadline_dt = goal.deadline
    deadline_date = deadline_dt.date()

    # Format the deadline
    if deadline_date == today:
        deadline_str = f"{deadline_dt.strftime('%H:%M')} today"
    else:
        deadline_str = f"{deadline_dt.strftime('%a %H:%M')}"

    goal_value_str = f"{goal.goal_value:.1f}" if goal.goal_value is not None else "N/A"
    penalty_str = f"{goal.penalty:.1f}" if goal.penalty is not None else "N/A"
    reminder_str = "⏰" if goal.reminder_scheduled else ""
    final_iteration_str = " (❗Last in series❗)" if goal.final_iteration == "yes" else ""

    return (
        f"*{goal.goal_description or 'No description found... 👻'}*{final_iteration_str}\n"
        f"  📅 Deadline: {deadline_str} {reminder_str}\n"
        f"  ⚡ {goal_value_str} | 🌚 {penalty_str}\n"
    )


def format_overdue_goal_with_buttons(goal):
    """Format a single overdue goal with action buttons"""
    today = datetime.now(BERLIN_TZ).date()
    yesterday = (datetime.now(BERLIN_TZ) - timedelta(days=1)).date()
    now = datetime.now(BERLIN_TZ)

    deadline_dt = goal.deadline
    deadline_date = deadline_dt.date()

    # Format the deadline
    if deadline_date == today:
        deadline_str = f"{deadline_dt.strftime('%H:%M')} today"
    elif deadline_date == yesterday:
        deadline_str = f"{deadline_dt.strftime('%H:%M')} yesterday"
    else:
        deadline_str = f"{deadline_dt.strftime('%a, %d %B')}"

    goal_value_str = f"{goal.goal_value:.1f}" if goal.goal_value is not None else "N/A"
    penalty = goal.penalty or 0
    penalty_str = f"{penalty:.1f}"
    reminder_str = "⏰" if goal.reminder_scheduled else ""
    final_iteration_str = " (❗Last in series❗)" if goal.final_iteration == "yes" else ""

    # Determine postpone day
    postpone_to_day = "tomorrow"
    if deadline_dt.date() < now.date():
        if deadline_dt.time() < now.time():
            postpone_to_day = "tomorrow"
        else:
            postpone_to_day = "today"
    elif deadline_dt.date() == now.date():
        postpone_to_day = "tomorrow"

    # Message text
    text = (
        f"*{goal.goal_description or 'No description found... 👻'}* {final_iteration_str}\n"
        f"📅 Deadline: {deadline_str} {reminder_str}\n"
        f"⚡ {goal_value_str} | 🌚 {penalty_str}\n"
        f"#{goal.goal_id}"
    )

    # Buttons
    cost_to_postpone = round(penalty * 0.65, 1)
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Done", callback_data=f"finished_{goal.goal_id}"),
            InlineKeyboardButton("❌ Failed", callback_data=f"failed_{goal.goal_id}")
        ],
        [
            InlineKeyboardButton(
                f"⏭️ {postpone_to_day.capitalize()}..! (-{cost_to_postpone})",
                callback_data=f"postpone_{goal.goal_id}_{postpone_to_day}"
            )
        ]
    ])

    return {"text": text, "buttons": buttons}


def get_greeting_and_announcement():
    """Get appropriate greeting based on time of day"""
    now = datetime.now(tz=BERLIN_TZ)
    morning_start, morning_end = time(4, 0), time(12, 0)
    if morning_start <= now.time() <= morning_end:
        return GREETING_GOOD_MORNING, "Your goals for the day are:"
    else:
        return GREETING_WHY_HELLO_THERE, "Your upcoming goals are:"