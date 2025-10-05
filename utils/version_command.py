# utils/version_command.py
from utils.version import format_version_message
from telegram_helpers.delete_message import add_delete_button
from utils.session_avatar import PA
import logging

logger = logging.getLogger(__name__)

async def version_command(update, context):
    """
    Handle /version command - shows Git version information.
    """
    try:
        # Get version information
        version_message = format_version_message()
        
        # Add PA emoji to the message
        version_message += f"\n\n{PA}"
        
        # Send version information
        version_response = await update.message.reply_text(
            version_message,
            parse_mode="HTML"
        )
        
        # Add delete button
        await add_delete_button(update, context, version_response.message_id)
        
        logger.info("Version command executed successfully")
        
    except Exception as e:
        error_message = f"Error getting version info: {e}"
        logger.error(error_message)
        await update.message.reply_text(
            f"❌ {error_message} {PA}",
            parse_mode="HTML"
        )