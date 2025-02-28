# features/evening_message/service.py
import asyncio
import random
import logging
from datetime import datetime
from features.goals.service import get_overdue_goals
from features.evening_message.formatter import (
    format_goal_with_buttons,
    get_greeting_and_announcement,
    get_random_evening_emoji
)
from features.bitcoin.monitoring import get_btc_price
from utils.db import Database
from utils.helpers import BERLIN_TZ
from utils.session_avatar import PA

logger = logging.getLogger(__name__)


async def create_evening_message_components(user_id, chat_id, first_name):
    """
    Create all components for the evening message.
    Returns a dictionary with all message components.
    """
    # Get Bitcoin price information
    _, detailed_message, _, usd_change = await get_btc_price()
    btc_change_message = ""
    if abs(usd_change) > 10:
        btc_change_message = f"\n\n📈 _฿itcoin price changed by {usd_change:.2f}% in the last 24 hours._\n{detailed_message}"

    # Get greeting and announcement based on time of day
    greeting, announcement = get_greeting_and_announcement()

    # Get all pending goals for today to report on
    goals_report = await get_overdue_goals(user_id, chat_id, timeframe="today")

    # Format goals with buttons
    goal_messages = []
    for goal in goals_report.goals:
        goal_messages.append(format_goal_with_buttons(goal))

    # Build main message
    if not goals_report.has_goals:
        announcement = "\n🔎    _....._    🔍\n\nNo pending goals remaining today, you're all caught up ✨"

    main_message = f"*{greeting}, {first_name}!* {PA}\n{announcement}\n\n"
    main_message += btc_change_message

    # Stakes message (only for multiple goals)
    stakes_message = None
    if goals_report.total_goal_value > 0 and goals_report.goals_count > 1:
        stakes_message = f"_⚡{goals_report.total_goal_value} & 🌚{goals_report.total_penalty} on the line._\n"

    # Random motivational quote (very rarely)
    motivational_quote = None
    if random.random() < 0.00273972603:  # once per year if triggered daily
        motivational_quote = "\n\nAwel slaap wel! ❤️\n\n_'[memorabele quote enzo]'_}"

    # Random emoji
    random_emoji = get_random_evening_emoji()

    # Determine whether to send the message
    should_send = goals_report.goals_count > 0 or btc_change_message or random.random() <= 0.15

    return {
        "start_emoji": "🌚",
        "greeting": main_message,
        "goals": goal_messages,
        "stakes_message": stakes_message,
        "motivational_quote": motivational_quote,
        "end_emoji": random_emoji,
        "should_send": should_send
    }


async def send_personalized_evening_message(bot, chat_id, user_id, first_name):
    """
    Send the personalized evening message to a user
    """
    try:
        message_components = await create_evening_message_components(user_id, chat_id, first_name)

        # Skip sending if no content
        if not message_components["should_send"]:
            return

        # Send the message sequence
        await bot.send_message(chat_id, message_components["start_emoji"])
        await asyncio.sleep(2)
        await bot.send_message(chat_id, message_components["greeting"], parse_mode="Markdown")

        # Send individual goals with buttons
        for goal in message_components["goals"]:
            await bot.send_message(
                chat_id=chat_id,
                text=goal["text"],
                reply_markup=goal["buttons"],
                parse_mode="Markdown"
            )

        # Send stakes message if available
        if message_components["stakes_message"]:
            await asyncio.sleep(4)
            await bot.send_message(chat_id, message_components["stakes_message"], parse_mode="Markdown")

        # Send motivational quote if available
        if message_components["motivational_quote"]:
            await asyncio.sleep(2)
            await bot.send_message(chat_id, message_components["motivational_quote"], parse_mode="Markdown")

        # Send final emoji
        await bot.send_message(chat_id, message_components["end_emoji"])

        logger.info(f"Evening message sent successfully to {first_name}({user_id}) in chat {chat_id}")

    except Exception as e:
        logger.error(f"Error sending evening message to chat_id {chat_id}: {e}")