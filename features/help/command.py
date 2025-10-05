from features.help.message import HELP_MESSAGE
from utils.session_avatar import PA
from utils.environment_vars import ENV_VARS


def is_user_ben(update) -> bool:
    """Check if the current user is Ben by checking user ID against BEN_ID and APPROVED_USER_IDS"""
    user_id = update.effective_user.id
    return user_id == ENV_VARS.BEN_ID or user_id in ENV_VARS.APPROVED_USER_IDS


async def help_command(update, context):
    help_message = HELP_MESSAGE
    chat_type = update.effective_chat.type
    
    # Check if we're in a private chat and user is NOT Ben
    if chat_type == 'private' and not is_user_ben(update):
        help_message += "\n\nHoi trouwens... 👋🧙‍♂️ Stiekem ben ik een beetje verlegen. Praat met me in een chat waar Ben bij zit, pas dan voel ik me op mijn gemak.\n\n\nPS: je kunt hier wel allerhande boodschappen ter feedback achterlaten, dan geef ik die door aan Ben (#privacy)."
        await update.message.reply_text(help_message, parse_mode="Markdown")
    else:
        # Ben is the user or we're in a group chat
        if chat_type != 'private':
            help_message += "\n\n🚧_...deze werken nog niet/nauwelijks_"
        await update.message.reply_text(help_message, parse_mode="Markdown")
