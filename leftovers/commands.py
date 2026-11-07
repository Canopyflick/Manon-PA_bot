# leftovers/commands.py
from utils.helpers import escape_markdown_v2
from telegram_helpers.delete_message import delete_message, add_delete_button
from features.philosophy.philosophical_message import get_random_philosophical_message
from utils.session_avatar import PA
from telegram import Update
from telegram.constants import ChatAction
import asyncio, random, re, logging
from telegram.ext import CallbackContext
from LLMs.orchestration import process_other_language, check_language, run_chain
from telegram_helpers.security import is_ben_in_chat
from utils.db import fetch_active_goals_summary, fetch_random_todays_goal
from features.evening_message.formatter import format_goal_with_buttons
from features.goals.queries import fetch_open_source_goals
from utils.scheduler import send_goals_today, fetch_overdue_goals

logger = logging.getLogger(__name__)

# Asynchronous command functions


async def profile_command(update, context):
    await update.message.reply_text("will show all the user-specific settings, like long term goals, preferences, constitution ... + edit-button")


# fix later huhauhue
async def process_emojis(escaped_emoji_string, escaped_pending_emojis):
    # Extract the existing emojis inside the brackets from the escaped_emoji_string
    # Pattern to match content between \(...\)
    inner_emojis = ''
    if escaped_emoji_string:
        # Extract the existing emojis inside the brackets from the escaped_emoji_string
        # Pattern to match content between \(...\)
        pattern = r"\\\((.*?)\\\)"
        match = re.search(pattern, escaped_emoji_string)
        inner_emojis = match.group(1) if match else ''
    

    # Extract all 🤝 emojis from the pending emoji string
    pending_links = ''.join([char for char in escaped_pending_emojis if char == '🤝'])
    combined_inner_emojis = inner_emojis + pending_links

    # Create the new string with the updated emojis inside the brackets
    new_emoji_string = f"({combined_inner_emojis})"
    escaped_combined_string = escape_markdown_v2(new_emoji_string)

    return escaped_combined_string

            



async def wow_command(update, context):
    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    approved = await is_ben_in_chat(update, context)
    logger.info(f"🔍 /wow: user_id={user_id}, chat_id={chat_id}, chat_type={chat_type}, approved={approved}")

    try:
        # Approved user: try grandpa quote (30% of the time)
        if approved:
            use_fallback = random.random() < 0.3
            logger.info(f"🔍 /wow: use_fallback={use_fallback}")
            if not use_fallback:
                todays_goal = await fetch_random_todays_goal(user_id, chat_id)
                logger.info(f"🔍 /wow: todays_goal={'found' if todays_goal else 'None'}")
                if todays_goal:
                    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                    result = await run_chain("grandpa_quote", {"active_goals": todays_goal})
                    grandpa_quote = getattr(result, "response_text", None) or str(result)
                    random_delay = random.uniform(2, 8)
                    await asyncio.sleep(random_delay)
                    markdown_text = f"Mijn grootvader zei altijd:\n✨_{grandpa_quote}_ 🧙‍♂️✨"
                    try:
                        await update.message.reply_text(markdown_text, parse_mode="Markdown")
                    except Exception as markdown_error:
                        logger.warning(f"/wow grandpa quote Markdown send failed, retrying plain: {markdown_error}")
                        await update.message.reply_text(
                            f"Mijn grootvader zei altijd:\n✨ {grandpa_quote} 🧙‍♂️✨"
                        )
                    return

        # Non-approved user in private chat: flavor text
        if not approved and chat_type == 'private':
            await update.message.reply_text("Hihi hoi. Ik werk eigenlijk liever in een groepssetting... 🧙‍♂️")
            await asyncio.sleep(3)
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(1)
            await update.message.reply_text("... maarrr, vooruit dan maar, een stukje inspiratie kan ik je niet ontzeggen ...")
            await asyncio.sleep(2)

        # Fallback: prewritten philosophical quote
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        random_delay = random.uniform(2, 5)
        await asyncio.sleep(random_delay)
        philosophical_message = get_random_philosophical_message(normal_only=True)
        await update.message.reply_text(f'_{philosophical_message}_', parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in wow_command: {e}")


async def translate_command(update: Update, context: CallbackContext):
    logger.warning("triggered /translate")
    if not context.args:    # Check if NO argument was provided
        await update.message.reply_text(f"Provide some source text to translate {PA}")
        return
    else:
        source_text = " ".join(context.args)
        language = await check_language(update, context, source_text)
        await process_other_language(update, context, source_text, language=language, translate_command=True)
        

async def _reply_plain(message, text):
    """Status replies stay plain text so a Markdown parse error cannot swallow them."""
    return await message.reply_text(text)


async def today_command(update, context):
    """
    Sends all goals in chat with deadlines remaining on this day (until tomorrow morning), for user that requested this with /today
    """
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        logger.error("/today had nothing to reply to")
        return
    chat_id = chat.id
    user_id = user.id
    try:
        # Send upcoming goals
        upcoming_goals_message, _ = await send_goals_today(update, context, chat_id, user_id, timeframe=7)
        if upcoming_goals_message:
            await add_delete_button(update, context, upcoming_goals_message.message_id, delay=4)
            asyncio.create_task(delete_message(update, context, upcoming_goals_message.message_id, 1200))
        else:
            await _reply_plain(message, "I couldn't load today's goals. Try again.")
        
        # Fetch overdue goals
        overdue_goals_result = await fetch_overdue_goals(chat_id, user_id, timeframe="overdue_today")
        overdue_payload = overdue_goals_result[0] if overdue_goals_result else None
        if isinstance(overdue_payload, str):
            await _reply_plain(message, overdue_payload)
        elif overdue_payload:
            sent_any = False
            for goal in overdue_payload:
                if not isinstance(goal, dict) or "text" not in goal or "buttons" not in goal:
                    continue
                goal_report_prompt = await _send_goal_card(message, goal)
                asyncio.create_task(delete_message(update, context, goal_report_prompt.message_id, 1200))
                sent_any = True
            if not sent_any:
                await _reply_plain(message, f"You're all caught up today, nothing overdue {PA}")
        else:
            await _reply_plain(message, f"You're all caught up today, nothing overdue {PA}")
            
    except Exception as e:
        logger.error(f"Error in today_command: {e}")
        await _reply_plain(message, "I couldn't load today's goals. Try again.")


async def twenty_four_hours_command(update, context):
    """
    Replies with all goals that have deadlines between now + 24 hours for the user that sent /24
    """
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        logger.error("/24 had nothing to reply to")
        return
    try:
        sent, _ = await send_goals_today(update, context, chat.id, user.id, timeframe="24hs")
        if sent is None:
            await _reply_plain(message, "I couldn't load the next 24 hours. Try again.")
    except Exception as e:
        logger.error(f"Error in twenty_four_hours_command: {e}")
        await _reply_plain(message, "I couldn't load the next 24 hours. Try again.")
    

def _overdue_cards(result):
    goals = result[0] if result else None
    if not isinstance(goals, list):
        return []
    return [
        goal for goal in goals
        if isinstance(goal, dict) and "text" in goal and "buttons" in goal
    ]


async def _send_goal_card(message, goal):
    try:
        return await message.reply_text(
            goal["text"],
            reply_markup=goal["buttons"],
            parse_mode="Markdown",
        )
    except Exception as send_error:
        logger.warning("Goal card Markdown failed, sending plain text: %s", send_error)
        return await message.reply_text(
            goal["text"].replace("*", ""),
            reply_markup=goal["buttons"],
        )


async def overdue_command(update, context):
    """
    Sends expired Manon goals, plus urgent benwerktijd todos, with buttons to report progress.
    Always replies, including when nothing is overdue.
    """
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        logger.error("/overdue had nothing to reply to")
        return
    chat_id = chat.id
    user_id = user.id
    logger.info("/overdue user_id=%s chat_id=%s", user_id, chat_id)
    try:
        overdue_result, work_goals = await asyncio.wait_for(
            asyncio.gather(
                fetch_overdue_goals(chat_id, user_id, timeframe="overdue"),
                fetch_open_source_goals(user_id, chat_id, "benwerktijd", urgent_only=True),
            ),
            timeout=25,
        )
        fetch_note = overdue_result[0] if isinstance(overdue_result[0], str) else None
        cards = [] if fetch_note else _overdue_cards(overdue_result)
        cards.extend(format_goal_with_buttons(goal) for goal in work_goals)

        if fetch_note:
            await _reply_plain(message, fetch_note)
        if not cards:
            if not fetch_note:
                logger.info("/overdue reply chat_id=%s: 0 overdue goals", chat_id)
                await _reply_plain(message, "0 overdue goals ✨")
            return

        for goal in cards:
            goal_report_prompt = await _send_goal_card(message, goal)
            asyncio.create_task(delete_message(update, context, goal_report_prompt.message_id, 1200))

    except asyncio.TimeoutError:
        logger.error("/overdue timed out user_id=%s chat_id=%s", user_id, chat_id)
        await _reply_plain(message, "I couldn't check overdue goals in time. Try again in a moment.")
    except Exception as e:
        logger.error(f"Error in overdue_command: {e}")
        await _reply_plain(message, "I couldn't load overdue goals. Try again in a moment.")
        

