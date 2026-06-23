import asyncio

from leftovers.commands import logger
from telegram_helpers.delete_message import add_delete_button, delete_message
from utils.scheduler import send_goals_today


async def tomorrow_command(update, context):
    """
    Replies with tomorrow's goals for the user that sent /tomorrow
    """
    chat_id = update.message.chat_id
    user_id = update.effective_user.id
    try:
        upcoming_goals_message, _ = await send_goals_today(
            update, context, chat_id, user_id, timeframe="tomorrow"
        )
        if upcoming_goals_message:
            await add_delete_button(update, context, upcoming_goals_message.message_id, delay=4)
            asyncio.create_task(delete_message(update, context, upcoming_goals_message.message_id, 1200))

    except Exception as e:
        logger.error(f"Error in tomorrow_command: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="An error occurred while processing your request. Please try again later.",
            parse_mode="Markdown"
        )
