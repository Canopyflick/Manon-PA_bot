# utils/listener.py
from telegram_helpers.delete_message import delete_message
from telegram_helpers.security import send_unauthorized_access_notification, is_ben_in_chat
from utils.session_avatar import PA
from LLMs.orchestration import start_initial_classification
import logging
from telegram import MessageEntity
from utils.string_resources import SHY_MESSAGE
from utils.triggers import handle_preset_triggers

logger = logging.getLogger(__name__)


async def analyze_any_message(update, context):
    """
    Entry point for processing all incoming chat messages.

    This function performs a series of checks and processing steps to determine how the bot should handle
    each new message.
    """
    if not await is_ben_in_chat(update, context):   # blocks non-Bens from most functionality
        await update.message.reply_text(SHY_MESSAGE)
        await send_unauthorized_access_notification(update, context)
        return

    try:
        user_message = update.message.text

        # Reject long messages
        if await handle_long_message(update, context, user_message):
            return

        # Check for preset triggers which bypass normal responses
        if await handle_preset_triggers(update, context, user_message):
            return

        # Determine the type of message (returns categorization tuple of bools)
        bot_response_wanted, regular_message, bot_reply_message, bot_mention_message = await check_reply_or_mention(update, context)

        # Bot shuts up in case user sends '@' (TODO: skip in private chats)
        bot_response_wanted = await suppress_bot_response(update, context, regular_message, bot_response_wanted)

        # Final decision to respond
        if bot_response_wanted:
            if regular_message or bot_reply_message or bot_mention_message:
                logger.info("Message received that wants a bot reponse\n")
                await start_initial_classification(update, context)                                     # < < <

    except Exception as e:
        logger.error(f"\n\n🚨 Error in analyze_any_message(): {e}\n\n")
        await update.message.reply_text(f"Error in analyze_any_message():\n {e}")


async def handle_long_message(update, context, user_message):
    if len(user_message) > 1800:
        await update.message.reply_text(
            f"Hmpff... TL;DR pl0x? 🧙‍♂️\n(_{len(user_message)}_)", parse_mode="Markdown"
        )
        return True
    return False


async def check_reply_or_mention(update, context):
    """
    Determine the type of message received.
    Returns a tuple of bools:
       (bot_response_wanted, regular_message, bot_reply_message, bot_mention_message)
    """
    bot_response_wanted = True
    regular_message = True
    bot_reply_message = False
    bot_mention_message = False
    message_text = update.message.text or ""

    # Check if the message is a reply, to bot or someone else
    if update.message.reply_to_message:
        if update.message.reply_to_message.from_user.is_bot:
            logger.info("Message received: Bot Reply")
            regular_message = False
            bot_reply_message = True
        else:
            reply = await update.message.reply_text(
                f"OOKAY I'll shut up for this one {PA}\n_(unless you still tagged me)_",
                parse_mode="Markdown"
            )
            await delete_message(update, context, reply.id, 3)
            bot_response_wanted = False

    # check if there's a non-bot mention
    bot_response_wanted = await process_entities(update, context, bot_response_wanted)

    # Check for direct bot mentions
    if ('@TestManon_bot' in message_text) or ('@Manon_PA_bot' in message_text):
        logger.info("Message received: Bot Mention")
        bot_response_wanted = True
        regular_message = False
        bot_mention_message = True


    return bot_response_wanted, regular_message, bot_reply_message, bot_mention_message

async def process_entities(update, context, bot_response_wanted):
    """
    Process message entities to check for non-bot user mentions.
    Returns updated bot_response_wanted flag.
    """
    if update.message.entities:
        for entity in update.message.entities:
            if entity.type == MessageEntity.MENTION:
                mention = update.message.text[entity.offset: entity.offset + entity.length]
                try:
                    username = mention[1:]
                    user = await context.bot.get_chat(username)
                    if not user.is_bot:
                        logger.info(f"Message received: Non-Bot User Mentioned ({username})")
                        bot_response_wanted = False
                        break
                except Exception as e:
                    logger.warning(f"Could not retrieve user for mention {mention}: {e}")
    return bot_response_wanted

async def suppress_bot_response(update, context, regular_message, bot_response_wanted):
    """
    Ignore messages that include '@'
    """
    message_text = update.message.text or ""
    if regular_message and '@' in message_text and bot_response_wanted:
        reply = await update.message.reply_text(f"OOKAY I'll shut up for this one {PA}")
        await delete_message(update, context, reply.id, 2)
        bot_response_wanted = False
    return bot_response_wanted


async def print_edit(update, context):
    logger.info("Someone edited a message")

