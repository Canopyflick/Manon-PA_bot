# telegram_helpers/delete_message.py
import asyncio

from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from utils.helpers import logger


async def delete_message(update, context, message_id=None, delay=None):
    """
    Deletes a chat message after X seconds delay. Can be triggered using message ID or via callback query (for messages with the trashbin delete button)
    """
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
