from features.help.message import HELP_MESSAGE
from utils.session_avatar import PA


async def help_command(update, context):
    help_message = HELP_MESSAGE
    chat_type = update.effective_chat.type
    if chat_type == 'private':
        help_message += "\n\nHoi trouwens... 👋🧙‍♂️ Stiekem ben ik een beetje verlegen. Praat met me in een chat waar Ben bij zit, pas dan voel ik me op mijn gemak.\n\n\nPS: je kunt hier wel allerhande boodschappen ter feedback achterlaten, dan geef ik die door aan Ben (#privacy)."
        await update.message.reply_text(help_message, parse_mode="Markdown")
    else:
        help_message += "\n\n🚧_...deze werken nog niet/nauwelijks_"
        await update.message.reply_text(help_message, parse_mode="Markdown")
