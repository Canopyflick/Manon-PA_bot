﻿# leftovers/commands.py
from utils.helpers import escape_markdown_v2, add_delete_button, delete_message
from features.philosophy.philosophical_message import get_random_philosophical_message
from utils.session_avatar import PA
from telegram import Update
from telegram.constants import ChatAction
import asyncio, random, re, logging
from telegram.ext import CallbackContext
from LLMs.orchestration import process_other_language, check_language
from utils.scheduler import send_goals_today, fetch_overdue_goals, fetch_upcoming_goals

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
    # Check if the chat is private or group/supergroup
    if chat_type == 'private':
        await update.message.reply_text("Hihi hoi. Ik werk eigenlijk liever in een groepssetting... 🧙‍♂️")
        await asyncio.sleep(3)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(1)
        await update.message.reply_text("... maarrr, vooruit dan maar, een stukje inspiratie kan ik je niet ontzeggen ...")
        philosophical_message = get_random_philosophical_message(normal_only=True)
        await asyncio.sleep(2)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(4)
        await asyncio.sleep(1)
        await update.message.reply_text(f'_{philosophical_message}_', parse_mode="Markdown")
        return
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        goal_text = fetch_goal_text(update)
        if goal_text != '' and goal_text != None:
                messages = await prepare_openai_messages(update, user_message="onzichtbaar", message_type = 'grandpa quote', goal_text=goal_text)
                grandpa_quote = await send_openai_request(messages, "gpt-4o")
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
                random_delay = random.uniform(2, 8)
                await asyncio.sleep(random_delay)
                await update.message.reply_text(f"Mijn grootvader zei altijd:\n✨_{grandpa_quote}_ 🧙‍♂️✨", parse_mode="Markdown")
        else:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            random_delay = random.uniform(2, 5)
            await asyncio.sleep(random_delay)
            philosophical_message = get_random_philosophical_message(normal_only=True)
            await update.message.reply_text(f'_{philosophical_message}_', parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in filosofie_command: {e}")


async def translate_command(update: Update, context: CallbackContext):
    logger.warning("triggered /translate")
    if not context.args:    # Check if NO argument was provided
        await update.message.reply_text(f"Provide some source text to translate {PA}")
        return
    else:
        source_text = " ".join(context.args)
        language = await check_language(update, context, source_text)
        await process_other_language(update, context, source_text, language=language, translate_command=True)
        

async def today_command(update, context):
    """
    Sends all goals in chat with deadlines remaining on this day (until tomorrow morning), for user that requested this with /today
    """
    try:
        chat_id = update.message.chat_id
        user_id = update.effective_user.id
        
        # Send upcoming goals
        upcoming_goals_message, _ = await send_goals_today(update, context, chat_id, user_id, timeframe=7)
        if upcoming_goals_message:
            await add_delete_button(update, context, upcoming_goals_message.message_id, delay=4)
            asyncio.create_task(delete_message(update, context, upcoming_goals_message.message_id, 1200))
        
        # Fetch overdue goals
        overdue_goals_result = await fetch_overdue_goals(chat_id, user_id, timeframe="overdue_today")
        if overdue_goals_result[0]:
            overdue_today = overdue_goals_result[0]
            for goal in overdue_today:
                if not isinstance(goal, dict) or "text" not in goal or "buttons" not in goal:
                    continue
                goal_report_prompt = await context.bot.send_message(
                    chat_id=chat_id,
                    text=goal["text"],
                    reply_markup=goal["buttons"],
                    parse_mode="Markdown"
                )
                asyncio.create_task(delete_message(update, context, goal_report_prompt.message_id, 1200))
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"_You're all caught up_ today, _nothing overdue_ {PA}",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Error in today_command: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="An error occurred while processing your request. Please try again later.",
            parse_mode="Markdown"
        )


async def twenty_four_hours_command(update, context):
    """
    Replies with all goals that have deadlines between now + 24 hours for the user that sent /24
    """
    chat_id = update.message.chat_id
    user_id = update.effective_user.id
    await send_goals_today(update, context, chat_id, user_id, timeframe="24hs")
    

async def overdue_command(update, context):
    """
    Sends all expired goals in chat for user that requested this with /overdue, with buttons to report progress
    """
    try:
        chat_id = update.message.chat_id
        user_id = update.effective_user.id
        
        # Fetch overdue goals
        overdue_goals_result = await fetch_overdue_goals(chat_id, user_id, timeframe="overdue")
        if overdue_goals_result[0]:
            overdue_today = overdue_goals_result[0]
            for goal in overdue_today:
                if not isinstance(goal, dict) or "text" not in goal or "buttons" not in goal:
                    continue
                goal_report_prompt = await context.bot.send_message(
                    chat_id=chat_id,
                    text=goal["text"],
                    reply_markup=goal["buttons"],
                    parse_mode="Markdown"
                )
                asyncio.create_task(delete_message(update, context, goal_report_prompt.message_id, 1200))
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="0 overdue goals ✨",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Error in today_command: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="An error occurred while processing your request in overdue_command()",
            parse_mode="Markdown"
        )
        

async def tomorrow_command(update, context):
    """
    Replies with tomorrow's goals for the user that sent /tomorrow
    """
    try:
        chat_id = update.message.chat_id
        user_id = update.effective_user.id
        
        # Send upcoming goals
        result = await fetch_upcoming_goals(chat_id, user_id, timeframe="tomorrow")
        if result:
            message_text = result[0]
            upcoming_goals_message = await context.bot.send_message(chat_id, text=message_text, parse_mode="Markdown")
            await add_delete_button(update, context, upcoming_goals_message.message_id, delay=4)
            asyncio.create_task(delete_message(update, context, upcoming_goals_message.message_id, 1200))
            
    except Exception as e:
        logger.error(f"Error in today_command: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="An error occurred while processing your request. Please try again later.",
            parse_mode="Markdown"
        )
        

