# features/morning_message/service.py
import asyncio
import random
from datetime import datetime
from models.user import User
from features.goals.service import get_overdue_goals, get_upcoming_goals
from features.morning_message.formatter import (
    format_goal_for_overview,
    format_overdue_goal_with_buttons,
    get_greeting_and_announcement
)
from features.bitcoin.monitoring import get_btc_change_message
from utils.db import Database
from utils.helpers import BERLIN_TZ
import logging
from utils.session_avatar import PA

logger = logging.getLogger(__name__)


async def create_morning_message_components(user_id, chat_id, first_name):
    """
    Create all components for the morning_message.
    Returns a dictionary with all message components.
    """
    btc_change_message = await get_btc_change_message()
    greeting, announcement = get_greeting_and_announcement()

    # Get overdue goals from early morning
    overdue_goals, _, _, has_overdue = await get_overdue_goals(user_id, chat_id, timeframe="early")
    overdue_messages = [format_overdue_goal_with_buttons(goal) for goal in overdue_goals]

    # Get upcoming goals
    goals, total_goal_value, total_penalty, goals_count = await get_upcoming_goals(
        user_id, chat_id, timeframe="rest_of_day"
    )

    # Build goals overview
    if goals_count > 0:
        goals_overview = "\n\n".join([format_goal_for_overview(goal) for goal in goals])
    else:
        goals_overview = "You have no deadlines between now and tomorrow morning ☃️"

    # Build stakes message
    stakes_message = ""
    if total_goal_value > 0 and goals_count > 1:
        stakes_message = f"_Go get some (⚡{total_goal_value}) ..!\n... or lose some ({total_penalty}🌚)_\n"

    # Random emoji for starting message
    morning_emojis = ["🍵", "☕", "🌄", "🌅", "🌞", "☃️", "❄️"]
    random_emoji = random.choice(morning_emojis)

    # Greeting message
    greeting_message = f"*{greeting}, {first_name}!* {PA}\n"
    if has_overdue:
        greeting_message += "\n_First, some unfinished business:_"

    # Main content
    main_message = f"{announcement}\n\n{goals_overview}\n\n"
    main_message += stakes_message + btc_change_message

    # Add motivational quote (rarely)
    motivational_quote = None
    if random.random() < 0.00273972603:  # Approximately once per year if triggered daily
        motivational_quote = (
            "\n\nZet je beste beentje voor, je kunt er niets aan doen, maar je kunt er wel wat aan doen! ❤️"
            "\n\n_'[memorabele quote enzo]'_}"
        )

    # Determine whether to send the message
    should_send = goals_count > 0 or btc_change_message or has_overdue or random.random() <= 0.15

    # **LOG should_send and its reasoning**
    logger.info(
        f"should_send: {should_send} | "
        f"goals_count: {goals_count}, btc_change_message: {bool(btc_change_message)}, "
        f"has_overdue: {has_overdue}, random_trigger: {random.random() <= 0.15}"
    )
    return {
        "start_emoji": random_emoji,
        "greeting": greeting_message,
        "overdue_goals": overdue_messages,
        "main_content": main_message,
        "motivational_quote": motivational_quote,
        "end_emoji": "🚀",
        "should_send": goals_count > 0 or btc_change_message or has_overdue or random.random() <= 0.15
    }


async def send_personalized_morning_message(bot, chat_id, user_id, first_name=None):
    """
    Send the personalized morning_message to a user
    """
    try:
        if not first_name:
            async with Database.acquire() as conn:
                user = await User.fetch(conn, user_id, chat_id)
                first_name = user.first_name if user else "there"

        message_components = await create_morning_message_components(user_id, chat_id, first_name)

        # Skip sending if no content
        if not message_components["should_send"]:
            return

        # Send the message sequence
        await bot.send_message(chat_id, message_components["start_emoji"])
        await bot.send_message(chat_id, message_components["greeting"], parse_mode="Markdown")

        # Send overdue goals
        for goal in message_components["overdue_goals"]:
            await asyncio.sleep(1)
            await bot.send_message(
                chat_id=chat_id,
                text=goal["text"],
                reply_markup=goal["buttons"],
                parse_mode="Markdown"
            )

        # Send main content
        await asyncio.sleep(3)
        await bot.send_message(chat_id, message_components["main_content"], parse_mode="Markdown")

        # Send motivational quote if available
        if message_components["motivational_quote"]:
            await asyncio.sleep(2)
            await bot.send_message(chat_id, message_components["motivational_quote"], parse_mode="Markdown")

        # Send final emoji
        await asyncio.sleep(4)
        await bot.send_message(chat_id, message_components["end_emoji"])

        logger.info(f"Morning message sent successfully to {first_name}({user_id}) in chat {chat_id}")

    except Exception as e:
        logger.error(f"Error sending morning_message to chat_id {chat_id}: {e}")