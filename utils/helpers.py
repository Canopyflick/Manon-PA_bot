# utils/helpers.py
import unicodedata
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.error import TelegramError
import os, logging, asyncio, re
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Define the Berlin timezone
BERLIN_TZ = ZoneInfo("Europe/Berlin")



def escape_markdown_v2(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))


async def check_chat_owner(update: Update, context: CallbackContext):
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
    

async def test_emojis_with_telegram(update, context):
    emoji_list = [
        '🤔', '💩', '💋', '👻', '🎃', '🎄', '🌚', '🤮', '👎', '🫡',
        '👀', '🍌', '😎', '🆒', '👾', '😘'
    ]

    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    
    for emoji in emoji_list:
        try:
            await context.bot.setMessageReaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction=emoji
            )
            print(f"Success: Emoji '{emoji}' works as a reaction.")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error: Emoji '{emoji}' failed. Reason: {e}")


async def delete_message(update, context, message_id=None, delay=None):
    try:
        if delay:
            await asyncio.sleep(delay)
        if message_id:      # aka triggered within a function
            chat_id = update.effective_chat.id
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        else:
            try:            # aka triggered by a button labeled "delete_message" 
                query = update.callback_query
                await query.answer()  

                # Delete the message containing the button
                await query.message.delete()
            except Exception as e:
                await query.message.reply_text(f"Failed to delete the message: {e}")
    except Exception as e:
        logger.error(f"Error in delete_message: {e}")
        
    


async def add_delete_button(update, context, message_id, delay=0):
    """
    Adds a delete button to a specific message.

    Args:
        context: The context object from the Telegram bot.
        chat_id: The ID of the chat where the message is located.
        message_id: The ID of the message to which the button should be added.
    """
    chat_id = update.effective_chat.id
    # Create an inline keyboard with a static delete button
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🗑️", callback_data="delete_message")]]
    )
    
    # Edit the message to include the inline keyboard
    await asyncio.sleep(delay)
    await context.bot.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=keyboard
    )


async def safe_set_reaction(bot, chat_id, message_id, reaction):
    """Safely set a message reaction, logging errors if the reaction is invalid (instead of breaking the flow)."""
    try:
        await bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=reaction)
    except Exception as e:
        logger.warning(f"Failed to set reaction '{reaction}': {e}")
        


async def fetch_logs(update, context, num_lines, type="info"):
    try:
        # Determine the log file path
        log_file_path = "logs_info.log"  # Adjust to logs_errors.log if needed
        if type == "error":
            log_file_path = "logs_errors.log"

        # Check if the log file exists
        if not os.path.exists(log_file_path):
            await update.message.reply_text(f"Log file not found at {log_file_path}")
            return

        # Read the last num_lines lines from the log file
        with open(log_file_path, "r", encoding="utf-8") as log_file:
            lines = log_file.readlines()

        # Fetch the most recent lines
        recent_logs = "".join(lines[-num_lines:])

        # Truncate to the latest 4096 characters (Telegram's limit)
        truncated_logs = recent_logs[-4096:]

        # Send the truncated logs to the chat
        message = await update.message.reply_text(truncated_logs)
        await add_delete_button(update, context, message_id=message.id)
    except Exception as e:
        await update.message.reply_text(f"Unexpected error: {e}")

def log_emoji_details(emoji, source="Unknown"):
    print(f"Source: {source}")
    print(f"Emoji: {emoji}")
    print(f"Unicode representation: {emoji.encode('unicode_escape')}")
    print(f"Name: {unicodedata.name(emoji, 'Unknown')}")
    print(f"Length: {len(emoji)}")
    print("-" * 40)


async def handle_trashbin_click(update, context):
    """
    Function to handle the trashbin button click (delete the message) that's added to some messages
    """
    query = update.callback_query

    # Double-check if the callback data is 'delete_message'
    if query.data == "delete_message":
        # Delete the message that contains the button
        await query.message.delete()

    # Acknowledge the callback to remove the 'loading' animation
    await query.answer()


