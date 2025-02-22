import asyncio

from leftovers.commands import logger


async def roll_dice(update, context, user_guess=None):
    chat_id = update.effective_chat.id

    try:
        # Send the dice and capture the message object
        dice_message = await context.bot.send_dice(
            chat_id,
            reply_to_message_id=update.message.message_id
        )

        # Check the outcome of the dice roll
        rolled_value = dice_message.dice.value
        if not user_guess:
            return
        else:
            # Give a reply based on the rolled value
            await asyncio.sleep(4)
            if rolled_value == user_guess:
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text="🎊",
                    reply_to_message_id=update.message.message_id
                )
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text="Correct :)",
                    parse_mode="Markdown",
                    reply_to_message_id=update.message.message_id
                )
            else:
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text="nope.",
                    parse_mode="Markdown",
                    reply_to_message_id=update.message.message_id
            )
    except Exception as e:
        logger.error(f"Error in roll_dice: {e}")
