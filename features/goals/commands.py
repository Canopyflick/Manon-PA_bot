import asyncio

from leftovers.commands import logger
from telegram_helpers.delete_message import add_delete_button, delete_message
from utils.db import fetch_upcoming_goals


async def tomorrow_command(update, context):
    """
    Replies with tomorrow's goals for the user that sent /tomorrow
    """
    try:
        chat_id = update.message.chat_id
        user_id = update.effective_user.id

        # Send upcoming goals
        result = await fetch_upcoming_goals(chat_id, user_id, timeframe="tomorrow")
        if result:
            message_text = result[0]
            upcoming_goals_message = await context.bot.send_message(chat_id, text=message_text, parse_mode="Markdown")
            await add_delete_button(update, context, upcoming_goals_message.message_id, delay=4)
            asyncio.create_task(delete_message(update, context, upcoming_goals_message.message_id, 1200))

    except Exception as e:
        logger.error(f"Error in today_command: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="An error occurred while processing your request. Please try again later.",
            parse_mode="Markdown"
        )
