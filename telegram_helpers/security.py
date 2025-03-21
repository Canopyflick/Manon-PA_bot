# telegram_helpers/security.py
import asyncio, logging
from telegram import ChatMember, Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext

from telegram_helpers.get_user_message import get_user_message
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
    message = get_user_message(update, context)
    notification_message = f"You've got mail ✉️🧙‍♂️\n\nUser: {first_name}, {user_id}\nChat: {chat_id}\nMessage:\n{message}"
    logger.error(
        f"! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! \n\n\n\nUnauthorized Access Detected\n\n\n\n! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !\nUser: {first_name}, {user_id}\nChat: {chat_id}\nMessage: {message}")
    await context.bot.send_message(chat_id=ben_id, text=notification_message)


# Security check: is there any approved user present in the chat where the bot is used?
async def is_ben_in_chat(update, context):
    """
    TODO: add description
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
                    member = await asyncio.wait_for(
                        context.bot.get_chat_member(chat_id, user_id), timeout=3
                    )
                    return member
                except TelegramError as te:
                    if "member not found" in str(te).lower():
                        logging.info(f"User {user_id} is not a member of chat {chat_id}")
                    else:
                        logging.warning(f"Failed to check user {user_id} in chat {chat_id}: {te}")
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


async def check_chat_owner(update: Update, context: CallbackContext):
    """"
    TODO: add description
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    try:
        # Get chat administrators
        admins = await context.bot.get_chat_administrators(chat_id)

        # Check if the user is the owner (creator)
        for admin in admins:
            if admin.user.id == user_id and admin.status == 'creator':
                return True
        return False
    except TelegramError as e:
        print(f"Error fetching chat admins, returned False as a fallback (retry if Ben =)): {e}")
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(
                "🚫 Ik kon ffkes niet checken of je de eigenaar van deze chat bent. Probeer het later opnieuw 🧙‍♂️"
            )
        else:
            print("No message object available to send a reply.")
        return False
