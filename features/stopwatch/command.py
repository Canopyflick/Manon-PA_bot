import asyncio
import re

from LLMs.orchestration import start_initial_classification
from utils.helpers import logger
from telegram_helpers.delete_message import delete_message
from utils.session_avatar import PA


async def stopwatch_command(update, context):
    if context.args:  # Input from a command like /stopwatch 10
        arg = context.args[0]
    else:  # Input from a message like "10:30"
        arg = update.message.text.strip()

    # Check if input is in minute:seconds format
    if re.match(r'^\d+:\d{1,2}$', arg):  # Matches "minute:seconds" format
        try:
            minutes, seconds = map(int, arg.split(':'))
            duration = minutes * 60 + seconds
            await emoji_stopwatch(update, context, duration=duration)
            return
        except ValueError:
            await update.message.reply_text(f"Invalid input format {PA}")
            return

    # Check if input is in :seconds format
    elif re.match(r'^:\d{1,2}$', arg):
        try:
            seconds = int(arg[1:])  # Extract seconds after the colon
            await emoji_stopwatch(update, context, duration=seconds)
            return
        except ValueError:
            await update.message.reply_text("Invalid seconds format. Use :seconds.")
            return

    # Check if input is a single number (minutes only)
    elif arg.isdigit():
        minutes = int(arg)
        duration = minutes * 60
        await emoji_stopwatch(update, context, duration=duration)
        return

    else:  # Invalid input
        await update.message.reply_text(f"Please provide time as minutes or minutes:seconds {PA}")
        await start_initial_classification(update, context)
        return


async def tea_command(update, context):
    await emoji_stopwatch(update, context, mode="tea_short")


async def emoji_stopwatch(update, context, **kwargs):
    chat_id = update.effective_chat.id
    message_id = update.message.message_id

    # Determine mode from kwargs
    mode = kwargs.get("mode", "default")
    logger.info(f"⏱️Stopwatch started in {mode} mode")

    # Define default durations
    durations = {
        "default": 10 * 60,     # 10 minutes
        "pomodoro": 25 * 60,     # 25 minutes
        "coffee": 3 * 60 + 30,  # 3 minutes 30 seconds
        "tea_long": 6 * 60,
        "tea_short": 2 * 60 + 30,
        "test": 5,
    }
    # Check for custom duration from /stopwatch, fallback to predefined durations
    custom_duration = kwargs.get("duration")
    duration = durations.get(mode, durations["default"])
    if custom_duration is not None:
            duration = custom_duration

    # Calculate total minutes and per-minute interval
    total_minutes = duration // 60
    remaining_seconds = duration % 60

    # Define custom responses dynamically
    custom_responses = {
        "default": {"initial": "🆒", "final": "🦄", "final_message": "⏰"},
        "pomodoro": {"initial": "👨‍💻", "final": "🍾", "final_message": "🍅"},
        "coffee": {"initial": "❤️‍🔥", "final": "🦄", "final_message": "☕"},
        "tea_long": {"initial": "❤️‍🔥", "final": "🦄", "final_message": "🫖"},
        "tea_short": {"initial": "❤️‍🔥", "final": "🦄", "final_message": "🍵"},
        "test": {"initial": "💩", "final": "👌", "final_message": "🕸️"},
    }

    # Merge `kwargs` for custom modes
    custom_responses.update(kwargs.get("reactions", {}))

    # Retrieve mode-specific responses
    mode_responses = custom_responses.get(mode, custom_responses["default"])
    initial_emoji = mode_responses["initial"]
    final_emoji = mode_responses["final"]
    final_message = mode_responses["final_message"]

    # Send initialization message with duration
    duration_headsup = await update.message.reply_text(
        text=f"{final_message if len(final_message) < 3 else '⏱️'} {PA}\n\n*{total_minutes} minutes {remaining_seconds} seconds*",
        parse_mode="Markdown"
    )
    # Delete duration_headsup message after duration - 4 seconds (delay), but never < 2 seconds
    delay = 56
    if duration < 60 :
        delay = duration - 4
        if delay < 2:
            delay = 2
    asyncio.create_task(delete_message(update, context, duration_headsup.message_id, delay))

    async def run_stopwatch(duration):
        # Emoji sequence for all durations
        emoji_sequence = [
            f"{i//10}️⃣{i%10}️⃣" if i > 9 else f"{i}️⃣"
            for i in range(1, 100)  # Arbitrary large limit to accommodate long durations
        ]

        # React with the initial emoji
        await context.bot.setMessageReaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=initial_emoji
        )

        # Calculate the total minutes
        total_minutes = duration // 60
        remaining_seconds = duration % 60

        # Send emojis every minute
        if total_minutes > 0:
            for minute in range(1, total_minutes + 1):
                if minute > len(emoji_sequence):  # Avoid index errors
                    break

                # Send the emoji for the current minute
                await asyncio.sleep(60)  # Wait for one minute
                count_message = await context.bot.send_message(chat_id, text=(emoji_sequence[minute - 1]))
                asyncio.create_task(delete_message(update, context, count_message.message_id, 180))

        # Wait for any remaining seconds
        await asyncio.sleep(remaining_seconds)

        # Send the final messages
        await update.message.reply_text(final_message)                                                          #1
        # Below are just 1-sec notification messages mimicking an alarm
        temporary_notification_message = await context.bot.send_message(chat_id, text="⏱️")                      #2
        asyncio.create_task(delete_message(update, context,  temporary_notification_message.message_id, 1))
        await asyncio.sleep(0.1)
        temporary_notification_message = await context.bot.send_message(chat_id, text="⏱️")                      #3
        asyncio.create_task(delete_message(update, context,  temporary_notification_message.message_id, 1))
        await asyncio.sleep(0.2)
        temporary_notification_message = await context.bot.send_message(chat_id, text="⏱️")                      #4
        asyncio.create_task(delete_message(update, context,  temporary_notification_message.message_id, 1))
        temporary_notification_message = await context.bot.send_message(chat_id, text="⏱️")                      #5
        asyncio.create_task(delete_message(update, context,  temporary_notification_message.message_id, 1))

        # React with the final emoji
        await context.bot.setMessageReaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=final_emoji
        )

    # Run the stopwatch in the background
    asyncio.create_task(run_stopwatch(duration))
