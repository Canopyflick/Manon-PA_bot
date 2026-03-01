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
from utils.db import Database, fetch_random_todays_goal
from utils.helpers import BERLIN_TZ
from LLMs.orchestration import run_chain
import logging
from utils.session_avatar import PA

logger = logging.getLogger(__name__)


async def create_morning_message_components(user_id, chat_id, first_name):
    """
    Create all components for the morning_message.
    Returns a dictionary with all message components.
    """
    try:
        btc_change_message = await get_btc_change_message()
    except Exception as e:
        logger.error(f"Error fetching BTC change message: {e}")

    try:
        greeting, announcement = get_greeting_and_announcement()
    except Exception as e:
        logger.error(f"Error getting greeting/announcement: {e}")

        # Get overdue goals from early morning
    try:
        goals_report = await get_overdue_goals(user_id, chat_id, timeframe="early")
        has_overdue = goals_report.has_goals
        overdue_messages = [format_overdue_goal_with_buttons(goal) for goal in goals_report.goals]
    except Exception as e:
        logger.error(f"Error fetching overdue goals: {e}")

    # Get upcoming goals
    goals, total_goal_value, total_penalty, goals_count = await get_upcoming_goals(
        user_id, chat_id, timeframe="rest_of_day"
    )

    # Build goals overview
    if goals_count > 0:
        goals_overview = "\n\n".join([format_goal_for_overview(goal) for goal in goals])
        # Only include announcement when there are goals
        main_message = f"{announcement}\n\n{goals_overview}\n\n"
    else:
        goals_overview = "You have no deadlines between now and tomorrow morning ☃️"
        # Skip the announcement when there are no goals
        main_message = f"{goals_overview}\n\n"

    # Build stakes message
    stakes_message = ""
    if total_goal_value > 0 and goals_count > 1:
        stakes_message = f"_Go get some (⚡{total_goal_value:.1f}) ..!\n... or lose some ({total_penalty:.1f}🌚)_\n"

    # Random emoji for starting message
    morning_emojis = ["🍵", "☕", "🌄", "🌅", "🌞", "☃️", "❄️"]
    random_emoji = random.choice(morning_emojis)

    # Greeting message
    greeting_message = f"*{greeting}, {first_name}!* {PA}\n"
    if has_overdue:
        greeting_message += "\n_First, some unfinished business:_"

    # Main content
    main_message += stakes_message + btc_change_message

    # Add motivational quote (rarely)
    motivational_quote = None
    if random.random() < 0.00273972603:  # Approximately once per year if triggered daily
        motivational_quote = (
            "\n\nZet je beste beentje voor, je kunt er niets aan doen, maar je kunt er wel wat aan doen! ❤️"
            "\n\n_'[memorabele quote enzo]'_}"
        )

    random_trigger = random.random() <= 0.00137  # Approx. once per two years if triggered daily

    # Determine whether to send the message
    should_send = goals_count > 0 or btc_change_message or has_overdue or random_trigger

    # **LOG should_send and its reasoning**
    logger.info(
        f"should_send: {should_send} | "
        f"goals_count: {goals_count}, btc_change_message: {bool(btc_change_message)}, "
        f"has_overdue: {has_overdue}, random_trigger: {random_trigger}"
    )

    return {
        "start_emoji": random_emoji,
        "greeting": greeting_message,
        "overdue_goals": overdue_messages,
        "main_content": main_message,
        "motivational_quote": motivational_quote,
        "end_emoji": "🚀",
        "should_send": should_send
    }


async def send_personalized_morning_message(bot, chat_id, user_id, first_name=None, always_send=False):
    """
    Send the personalized morning_message to a user

    Args:
        always_send: False by default, True when triggered by user request instead of Cron job
    """
    try:

        if not first_name:
            async with Database.acquire() as conn:
                user = await User.fetch(conn, user_id, chat_id)
                first_name = user.first_name if user else "there"

        message_components = await create_morning_message_components(user_id, chat_id, first_name)

        # Skip sending if no content
        if not message_components["should_send"] and not always_send:
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

        # 30% chance: send a grandpa quote based on a random today's goal
        if random.random() < 0.3:
            todays_goal = await fetch_random_todays_goal(user_id, chat_id)
            if todays_goal:
                try:
                    result = await run_chain("grandpa_quote", {"active_goals": todays_goal})
                    grandpa_quote = result.response_text
                    await asyncio.sleep(random.uniform(3, 6))
                    await bot.send_message(chat_id, f"Mijn grootvader zei altijd:\n✨_{grandpa_quote}_ 🧙‍♂️✨", parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Error sending grandpa quote in morning message: {e}")

        logger.info(f"Morning message sent successfully to {first_name}({user_id}) in chat {chat_id}")

    except Exception as e:
        logger.error(f"Error sending morning_message to chat_id {chat_id}: {e}")