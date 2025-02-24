import asyncio
import unicodedata

from utils.helpers import logger


async def test_emojis_with_telegram(update, context):
    """
    Reacts to the message with different emojis at 1 second intervals, cycling through all emojis from emoji_list and logging results
    """
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


async def safe_set_reaction(bot, chat_id, message_id, reaction):
    """Safely try to set a message reaction, logging errors if the reaction is invalid (instead of breaking the flow)."""
    try:
        await bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=reaction)
    except Exception as e:
        logger.warning(f"Failed to set reaction '{reaction}': {e}")


def log_emoji_details(emoji, source="Unknown"):
    print(f"Source: {source}")
    print(f"Emoji: {emoji}")
    print(f"Unicode representation: {emoji.encode('unicode_escape')}")
    print(f"Name: {unicodedata.name(emoji, 'Unknown')}")
    print(f"Length: {len(emoji)}")
    print("-" * 40)
