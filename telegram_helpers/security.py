# telegram_helpers/security.py
import asyncio, logging
from telegram import ChatMember, Update
from utils.environment_vars import ENV_VARS

logger = logging.getLogger(__name__)


async def send_unauthorized_access_notification(update: Update, context):
    """
    Sends Ben a notification when an unauthorized user talks to Manon 
    
    Args:
        update: Telegram update
        context: Telegram context
    """
    ben_id = ENV_VARS.BEN_ID
    first_name = update.effective_user.first_name
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message = update.message.text
    notification_message = f"You've got mail ✉️🧙‍♂️\n\nUser: {first_name}, {user_id}\nChat: {chat_id}\nMessage:\n{message}"
    logger.error(
        f"! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! \n\n\n\nUnauthorized Access Detected\n\n\n\n! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !\nUser: {first_name}, {user_id}\nChat: {chat_id}\nMessage: {message}")
    await context.bot.send_message(chat_id=ben_id, text=notification_message)


# Security check: is there any approved user present in the chat where the bot is used?
async def is_ben_in_chat(update, context):
    """

    Args:
        update:
        context:

    Returns:

    """
    approved_user_ids = ENV_VARS.APPROVED_USER_IDS
    chat_id = update.effective_chat.id

    try:
        # Handle private chats (where chat_id == user_id)
        if chat_id in approved_user_ids:
            return True

        # Handle group or supergroup chats
        if update.effective_chat.type in ["group", "supergroup"]:
            async def check_member(user_id):
                try:
                    return await asyncio.wait_for(
                        context.bot.get_chat_member(chat_id, user_id), timeout=3
                    )
                except asyncio.TimeoutError:
                    logging.warning(f"Timeout checking user {user_id} in chat {chat_id}")
                except Exception as e:
                    logging.warning(f"Failed to check user {user_id} in chat {chat_id}: {e}")
                return None

            # Run all checks concurrently with timeouts
            results = await asyncio.gather(*[check_member(uid) for uid in approved_user_ids])

            # Check if any result is a valid member
            return any(
                member and member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]
                for member in results
            )

        return False

    except Exception as e:
        logging.error(f"Unexpected error checking chat member: {e}")
        return False
