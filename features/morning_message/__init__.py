# features/morning_message/__init__.py
from utils.db import Database
from features.morning_message.service import send_personalized_morning_message
import logging

logger = logging.getLogger(__name__)


async def send_morning_message(bot, specific_chat_id=None):
    """
    Sends a personalized morning message to all users (everywhere the bot is active, or to a specific chat, if provided).
    """
    always_send = False
    if specific_chat_id:
        always_send=True
    try:
        async with Database.acquire() as conn:
            users = await conn.fetch("SELECT user_id, chat_id, first_name FROM manon_users")

        for user in users:
            user_id = user["user_id"]
            chat_id = user["chat_id"]

            if specific_chat_id and chat_id != specific_chat_id:    # skip all users not in the specific chat
                continue

            first_name = user.get("first_name") or "there"
            await send_personalized_morning_message(bot, chat_id, user_id, first_name, always_send)

    except Exception as e:
        logger.error(f"Error sending morning messages: {e}")