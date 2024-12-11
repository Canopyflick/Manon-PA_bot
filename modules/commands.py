from utils.helpers import emoji_stopwatch, get_first_name, get_random_philosophical_message, escape_markdown_v2, check_chat_owner, PA
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
import asyncio, random, re, logging
from utils.helpers import get_btc_price
from telegram.ext import ContextTypes, CallbackContext
from LLMs.orchestration import process_other_language, check_language, handle_goal_classification
from utils.db import register_user


# Asynchronous command functions
async def start_command(update, context):
    await update.message.reply_text(f'Hoi! 👋{PA}‍\n\nIk ben Manon. Jij bent als het goed is Ben, dus je weet alles al.\nWas je nog niet geregistreerd, dan ben je dat nu. De groeten.')
    try:
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        await register_user(context, user_id, chat_id)
    except Exception as e:
        logging.error(f"Error checking user records in start_command: {e}")


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
        return


async def help_command(update, context):
    help_message = (
        '*The available commands:* 🧙‍♂️\n'
        '👋 /start - Hi!\n'
        '❓ /help - This list\n'
        '🗒️ /profile - What I know about you\n'
        '💭 /filosofie - Get inspired'
    )
    chat_type = update.effective_chat.type
    if chat_type == 'private':
        help_message += "\n\nHoi trouwens... 👋🧙‍♂️ Stiekem ben ik een beetje verlegen. Praat met me in een chat waar Ben bij zit, pas dan voel ik me op mijn gemak.\n\n\nPS: je kunt hier wel allerhande boodschappen ter feedback achterlaten, dan geef ik die door aan Ben (#privacy)."
        await update.message.reply_text(help_message, parse_mode="Markdown")
    else:  
        await update.message.reply_text(help_message, parse_mode="Markdown")
    

async def profile_command(update, context):
    await update.message.reply_text("will show all the user-specific settings, like long term goals, preferences, constitution ... + edit-button")
    

async def stats_command(update, context):
    stats_message = (
        '*Your Statistics:* 📊\n'
        '👤 *Username:* {username_placeholder}\n'
        '🎯 *Goals Set:* {goals_set_placeholder}\n'
        '✅ *Goals Completed:* {goals_completed_placeholder}\n'
        '🔥 *Success Rate:* {success_rate_placeholder}%\n'
        '🏆 *Rank:* {rank_placeholder}\n'
        '\nKeep up the good work! {PA} '
    )
    chat_type = update.effective_chat.type
    if chat_type == 'private':
        help_message += f"\n\nHoi trouwens... 👋{PA} Stiekem ben ik een beetje verlegen. Praat met me in een chat waar Ben bij zit, pas dan voel ik me op mijn gemak.\n\n\nPS: je kunt hier wel allerhande boodschappen ter feedback achterlaten, dan geef ik die door aan Ben (#privacy)."
        await update.message.reply_text(help_message, parse_mode="Markdown")
    else:  
        await update.message.reply_text(help_message, parse_mode="Markdown")
    

async def profile_command(update, context):
    await update.message.reply_text("will show all the user-specific settings, like long term goals, preferences, constitution ... + edit-button")
    
    




# Function to handle the trashbin button click (delete the message)
async def handle_trashbin_click(update, context):
    query = update.callback_query

    # Double-check if the callback data is 'delete_message'
    if query.data == "delete_message":
        # Delete the message that contains the button
        await query.message.delete()

    # Acknowledge the callback to remove the 'loading' animation
    await query.answer()
            

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

            



async def filosofie_command(update, context):
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
        logging.error(f"Error in filosofie_command: {e}")



async def btc_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    simple_message, _, _ = await get_btc_price()
    await update.message.reply_text(simple_message)
    

async def bitcoin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, detailed_message, _ = await get_btc_price()
    await update.message.reply_text(detailed_message)


async def smarter_command(update: Update, context: CallbackContext):
    logging.warning("triggered /smarter")
    await handle_goal_classification(update, context, smarter=True)
    

async def translate_command(update: Update, context: CallbackContext):
    logging.warning("triggered /translate")
    if not context.args:    # Check if NO argument was provided
        await update.message.reply_text(f"Provide some source text to translate {PA}")
        return
    else:
        source_text = " ".join(context.args)
        language = await check_language(update, context, source_text)
        await process_other_language(update, context, source_text, language=language, translate_command=True)