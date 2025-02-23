import asyncio
import re, logging
from pprint import pformat

from LLMs.config import shared_state
from features.stats.stats_manager import StatsManager
from utils.helpers import test_emojis_with_telegram, delete_message, add_delete_button
from utils.logger import fetch_logs
from features.stopwatch.command import emoji_stopwatch
from utils.scheduler import fail_goals_warning, send_next_jobs
from features.goals.evening_message import send_evening_message
from features.goals.morning_message import send_morning_message
from utils.session_avatar import PA

logger = logging.getLogger(__name__)

triggers = ["SeintjeNatuurlijk", "OpenAICall", "Emoji", "Stopwatch", "usercontext", "clearcontext",
            "koffie", "coffee", "!test", "pomodoro", "tea", "gm", "gn", "resolve", "dailystats",
            "logs", "logs100", "errorlogs", "transparant_on", "transparant_off", "Jobs"]


async def handle_triggers(update, context, trigger_text):
    if trigger_text == "SeintjeNatuurlijk":
        await update.message.reply_text(f"Ja hoor, hoi! {PA}")
    elif trigger_text == "Emoji":
        await test_emojis_with_telegram(update, context)
    elif trigger_text == "Stopwatch":
        await emoji_stopwatch(update, context)
    elif trigger_text == 'pomodoro':
        await emoji_stopwatch(update, context, mode="pomodoro")
    elif trigger_text == "koffie" or trigger_text == "coffee":
        await emoji_stopwatch(update, context, mode="coffee")
    elif trigger_text == "tea":
        await emoji_stopwatch(update, context, mode="tea_long")
    elif trigger_text == "!test":
        await emoji_stopwatch(update, context, mode="test")
    elif trigger_text == "OpenAICall":
        print (f"nothing implemented yet")
    elif trigger_text == "usercontext":
        await send_user_context(update, context)
    elif trigger_text == "clearcontext":
        context.user_data.clear()
        await context.bot.setMessageReaction(chat_id=update.effective_chat.id, message_id=update.message.message_id, reaction="🫡")
    elif trigger_text == "gm":
        bot=context.bot
        chat_id=update.message.chat_id
        await send_morning_message(bot, specific_chat_id=chat_id)
    elif trigger_text == "gn":
        bot=context.bot
        chat_id=update.message.chat_id
        await send_evening_message(bot, specific_chat_id=chat_id)
    elif trigger_text == "resolve":
        bot=context.bot
        chat_id=update.message.chat_id
        await fail_goals_warning(bot, chat_id=chat_id)
    elif trigger_text == "dailystats":
        bot=context.bot
        chat_id=update.message.chat_id
        await context.bot.setMessageReaction(chat_id=update.effective_chat.id, message_id=update.message.message_id, reaction="👍")
        await StatsManager.update_daily_stats(specific_chat_id=chat_id)
    elif re.match(r"^logs\d+$", trigger_text):  # Match logs followed by digits
        num_lines = int(trigger_text[4:])  # Extract the number after 'logs'
        await context.bot.setMessageReaction(chat_id=update.effective_chat.id, message_id=update.message.message_id, reaction="👍")
        await fetch_logs(update, context, abs(num_lines))  # Ensure the number is positive
    elif trigger_text == "logs":
        await context.bot.setMessageReaction(chat_id=update.effective_chat.id, message_id=update.message.message_id, reaction="👍")
        await fetch_logs(update, context, 6)
    elif trigger_text == "errorlogs":
        await context.bot.setMessageReaction(chat_id=update.effective_chat.id, message_id=update.message.message_id, reaction="👍")
        await fetch_logs(update, context, 50, type="error")
    elif trigger_text == "transparant_on":
        shared_state["transparant_mode"] = True
        await update.message.reply_text(f"_transparant mode enabled 🟢_ {PA}\n_(spamming additional logs in chat)_", parse_mode="Markdown")
    elif trigger_text == "transparant_off":
        shared_state["transparant_mode"] = False
        await update.message.reply_text(f"_transparant mode disabled 🔴_ {PA}\n_(no additional logs in chat  )_", parse_mode="Markdown")
    elif trigger_text == "Jobs":
        await send_next_jobs(update, context, 7)


async def handle_preset_triggers(update, context, user_message):
    message_lower = user_message.lower()
    for trigger_text in triggers:
        if trigger_text.lower() == message_lower:
            logger.info(f"Message received: Trigger ({trigger_text})")
            await handle_triggers(update, context, trigger_text)
            return True
    # Handle dynamic logs trigger
    match = re.match(r"^logs(\d+)$", message_lower)
    if match:
        logger.info(f"Message received: Dynamic logs trigger ({message_lower})")
        num_lines = int(match.group(1))
        await handle_triggers(update, context, f"logs{num_lines}")
        return True
    return False


async def send_user_context(update, context):
    """
    Displays current user context for current user (short-term user-specific storage)
    """
    # Retrieve the user context
    user_context = context.user_data

    # Format the context data for display
    if user_context:
        chat_id = update.effective_chat.id
        for key, value in user_context.items():
            if key == "goals" and isinstance(value, dict):
                # Special handling for `goals` sub-keys
                for goal_id, goal_data in value.items():
                    formatted_message = (
                        f"{PA} HERE IS YOU CONTEXT FOR GOAL #{goal_id}\n"
                        + pformat(goal_data, indent=6)
                    )
                    context_message = await update.message.reply_text(formatted_message)
                    asyncio.create_task(delete_message(update, context, context_message.message_id, 180))
                    await add_delete_button(update, context, context_message.message_id)
            else:
                # Handle other top-level keys
                formatted_message = f"{PA} Here is your context for KEY: {key}\n"
                if isinstance(value, dict):
                    formatted_message += "\n" + pformat(value, indent=10)
                else:
                    formatted_message += f" {value}"

                context_message = await update.message.reply_text(formatted_message)
                asyncio.create_task(delete_message(update, context, context_message.message_id, 180))
                await add_delete_button(update, context, context_message.message_id)
    else:
        await update.message.reply_text(f"Your user context is currently empty {PA}")
