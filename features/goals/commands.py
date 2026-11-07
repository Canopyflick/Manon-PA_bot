import asyncio

from leftovers.commands import logger
from telegram_helpers.delete_message import add_delete_button, delete_message
from utils.scheduler import send_goals_today


async def tomorrow_command(update, context):
    """
    Replies with tomorrow's goals for the user that sent /tomorrow
    """
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        logger.error("/tomorrow had nothing to reply to")
        return
    try:
        upcoming_goals_message, _ = await send_goals_today(
            update, context, chat.id, user.id, timeframe="tomorrow"
        )
        if upcoming_goals_message is None:
            await message.reply_text("I couldn't load tomorrow's goals. Try again.")
            return
        await add_delete_button(update, context, upcoming_goals_message.message_id, delay=4)
        asyncio.create_task(delete_message(update, context, upcoming_goals_message.message_id, 1200))

    except Exception as e:
        logger.error(f"Error in tomorrow_command: {e}")
        await message.reply_text("I couldn't load tomorrow's goals. Try again.")
