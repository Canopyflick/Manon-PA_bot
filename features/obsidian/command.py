from features.obsidian.diary_header import diary_header
from leftovers.commands import logger
from utils.helpers import safe_set_reaction
from utils.session_avatar import PA


async def diary_command(update, context):
    try:
        chat_id = update.effective_chat.id
        message_id = update.message.message_id
        preset_reaction = "🎄"
        await safe_set_reaction(context.bot, chat_id=chat_id, message_id=message_id, reaction=preset_reaction)
        await diary_header(update, context)

    except Exception as e:
        logger.error(f"Error in diary_command: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"An error occurred while processing your request. Please try again later {PA}",
            parse_mode="Markdown"
        )
