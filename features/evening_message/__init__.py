# features/evening_message/__init__.py
from utils.db import Database
from features.evening_message.service import send_personalized_evening_message
import logging

logger = logging.getLogger(__name__)


async def send_evening_message(bot, specific_chat_id=None):
    """
    Sends a personalized evening message to all users (everywhere the bot is active, or to a specific chat, if provided).
    """
    try:
        async with Database.acquire() as conn:
            users = await conn.fetch("SELECT user_id, chat_id, first_name FROM manon_users")

        for user in users:
            user_id = user["user_id"]
            chat_id = user["chat_id"]

            if specific_chat_id and chat_id != specific_chat_id:    # skip all users not in the specific chat
                continue

            first_name = user.get("first_name") or "Sardientje"  # Fallback if first_name is NULL or empty
            await send_personalized_evening_message(bot, chat_id, user_id, first_name)

    except Exception as e:
        logger.error(f"Error sending evening messages: {e}")