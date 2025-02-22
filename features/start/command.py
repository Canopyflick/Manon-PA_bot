from leftovers.commands import logger
from features.start.registration import register_user
from utils.session_avatar import PA


async def start_command(update, context):
    await update.message.reply_text(f"Hoi! 👋{PA}‍\n\nMy name is Manon, maybe (so call me).")
    try:
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        await register_user(context, user_id, chat_id)
    except Exception as e:
        logger.error(f"Error checking user records in start_command: {e}")
