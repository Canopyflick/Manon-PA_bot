﻿from telegram import Update, ChatMember, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ExtBot
from telegram.error import TelegramError
from utils.environment_vars import ENV_VARS, is_running_locally
from typing import Union
from datetime import datetime, time, timedelta, timezone
import os, pytz, logging, requests, asyncio, re, random, json, subprocess
from openai import OpenAI
from typing import Union
from zoneinfo import ZoneInfo
from pprint import pformat
from dataclasses import dataclass
from utils.session_avatar import PA

logger = logging.getLogger(__name__)

# Define the Berlin timezone
BERLIN_TZ = ZoneInfo("Europe/Berlin")


#@ Dit verplaatsen naar llms.clients maybe?
client = OpenAI(api_key=ENV_VARS.OPENAI_API_KEY)
client_EC = OpenAI(api_key=ENV_VARS.EC_OPENAI_API_KEY)

#@ Dit verplaatsen naar llms.clients maybe?
async def check_chat_owner(update: Update, context) -> bool:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Get chat administrators
    admins = await context.bot.get_chat_administrators(chat_id)
    
    # Check if the user is the owner (creator)
    for admin in admins:
        if admin.user.id == user_id and admin.status == 'creator':
            return True
    return False


# Security check: is there any approved user present in the chat where the bot is used?
async def is_ben_in_chat(update, context):
    approved_user_ids = ENV_VARS.APPROVED_USER_IDS
    chat_id = update.effective_chat.id

    try:
        # Handle private chats (where chat_id == user_id)
        if chat_id in approved_user_ids:
            return True

        # Handle group or supergroup chats
        if update.effective_chat.type in ["group", "supergroup"]:
            async def check_member(user_id):
                try:
                    return await asyncio.wait_for(
                        context.bot.get_chat_member(chat_id, user_id), timeout=3
                    )
                except asyncio.TimeoutError:
                    logging.warning(f"Timeout checking user {user_id} in chat {chat_id}")
                except Exception as e:
                    logging.warning(f"Failed to check user {user_id} in chat {chat_id}: {e}")
                return None

            # Run all checks concurrently with timeouts
            results = await asyncio.gather(*[check_member(uid) for uid in approved_user_ids])

            # Check if any result is a valid member
            return any(
                member and member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]
                for member in results
            )

        return False

    except Exception as e:
        logging.error(f"Unexpected error checking chat member: {e}")
        return False

    

# Private message to Ben 
async def notify_ben(update, context):
    ben_id = ENV_VARS.BEN_ID
    first_name = update.effective_user.first_name
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message = update.message.text
    notification_message = f"You've got mail ✉️🧙‍♂️\n\nUser: {first_name}, {user_id}\nChat: {chat_id}\nMessage:\n{message}"
    logger.error(f"! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! \n\n\n\nUnauthorized Access Detected\n\n\n\n! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !\nUser: {first_name}, {user_id}\nChat: {chat_id}\nMessage: {message}")
    await context.bot.send_message(chat_id=ben_id, text=notification_message)
        


    

async def get_btc_price() -> tuple[str, str, float, float]:
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,eur&include_24hr_change=true"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses
        data = response.json()
        usd_price = float(data["bitcoin"]["usd"])  # Convert to float for formatting
        eur_price = float(data["bitcoin"]["eur"])  # Convert to float for formatting
        usd_change = float(data["bitcoin"]["usd_24h_change"])  # 24-hour percentage change

        
        mycelium_balance = 0.01614903
        mycelium_euros = round(eur_price * mycelium_balance, 2)
        
        # Format the prices with a comma as the thousands separator
        usd_price_formatted = f"{usd_price:,.0f}"
        mycelium_euros_formatted = f"{mycelium_euros:,.0f}"
        
        # Return two different outputs
        simple_message = f"${usd_price_formatted}"
        detailed_message = f"1₿ = ${usd_price_formatted}\n🍄 = €{mycelium_euros_formatted}"
        raw_float_price = usd_price
        
        return simple_message, detailed_message, raw_float_price, usd_change
    except requests.RequestException as e:
        # Default values in case of error
        simple_message = "Error"
        detailed_message = f"Error fetching Bitcoin price: {e}"
        raw_float_price = 0.0
        usd_change = 0.0
        return simple_message, detailed_message, raw_float_price, usd_change
    

# Function to check Bitcoin price every ten minutes and send a message if it exceeds the threshold
async def monitor_btc_price(bot: Bot, chat_id: int):
    lower_threshold = 88888
    upper_threshold = 111111
    upper_threshold_alerted = False
    lower_threshold_alerted = False
    while True:
        _, _, price, _ = await get_btc_price()
        if price is not None:
            print(f"Bitcoin price: ${price:,.2f}")  # Log the price
            if price > upper_threshold and not upper_threshold_alerted:
                message = f"*🚀 Bitcoin price alert!*\n1₿ is now ${price:,.2f} USD, exceeding the threshold of ${upper_threshold:,.2f}"
                await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                upper_threshold_alerted = True
                lower_threshold_alerted = False  # Reset lower threshold flag

            elif price < lower_threshold and not lower_threshold_alerted:
                message = f"*📉 Bitcoin price alert!*\n1₿ is now ${price:,.2f} USD, dropping below the threshold of ${lower_threshold:,.2f}"
                await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                lower_threshold_alerted = True
                upper_threshold_alerted = False  # Reset upper threshold flag
                
        await asyncio.sleep(600)  # Wait for 10 minutes before checking again
        

# Randomly pick a message
def get_random_philosophical_message(normal_only = False, prize_only = False):
    normal_messages = [
            "Hätte hätte, Fahrradkette",  # Message 1
            "千里之行，始于足下",        
            "Ask, believe, receive ✨",   
            "A few words on looking for things. When you go looking for something specific, "
            "your chances of finding it are very bad. Because, of all the things in the world, "
            "you're only looking for one of them. When you go looking for anything at all, "
            "your chances of finding it are very good. Because, of all the things in the world, "
            "you're sure to find some of them",
            "Je kan het best, de tijd gaat met je mee",
            "If the human brain were so simple that we could understand it, we would be so simple that we couldn't",       
            "Ik hoop maar dat er roze koeken zijn",  
            "Hoge loofbomen, dik in het blad, overhuiven de weg",   
            "It is easy to find a logical and virtuous reason for not doing what you don't want to do",  
            "Our actions are like ships which we may watch set out to sea, and not know when or with what cargo they will return to port",
            "A sufficiently intimate understanding of mistakes is indistinguishable from mastery",
            "He who does not obey himself will be commanded",
            "All evils are due to a lack of Telegram bots",
            "Art should disturb the comfortable, and comfort the disturbed",
            "Begin de dag met tequila",
            "Don't wait. The time will never be just right",
            "If we all did the things we are capable of doing, we would literally astound ourselves",
            "There's power in looking silly and not caring that you do",                                        # Message 19
            "...",
            "Een goed begin is de halve dwerg",
            "En ik lach in mezelf want de sletten ik breng",
            "Bij nader inzien altijd achteraf",
            "Sometimes we live no particular way but our own",                                                  # Message 24
            "If it is to be said, so it be, so it is",                                                          # Message 25
            "Te laat, noch te vroeg, arriveert (n)ooit de Takentovenaar"                                        # Message 26
        ]
    
    prize_messages = [
        {
            "message": "Als je muisjes op je mouwen knoeit, katten ze niet",
            "prize": "raad het Nederlandse spreekwoord waarvan dit is... afgeleid..?, en win 2 punten"
        },
        {
            "message": "Ik schaam me een beetje dat ik niet met een turkencracker overweg kan",
            "prize": "raad het keukengerei dat hier bedoeld wordt, en win 1 punt"
        },
        {
            "message": "De oom uit de eik batsen",
            "prize": "raad het Nederlandse spreekwoord waarvan dit nogal afleidt, en win 1 punt"
        },
        {
            "message": "Je niet laten prikken door dat stekelige mythische wezen, maar andersom!",
            "prize": "raad het Nederlandse spreekwoord dat hier zo'n beetje is omgedraaid, en win 1 punt"
        },
        {
            "message": "De kastanjes in het vuur flikkeren",                                                                            # Message 5
            "prize": "raad het Nederlandse spreekwoord waarvan dit is afgeleid, en verlies 1 punt"
        },
        {
            "message": "Inwoners uit deze gemeente zijn het staan zat",
            "prize": "raad de verborgen gemeente, en win 2 punten"
        },
        {
            "message": "Welke rij planten zit er in dit huidvraagje verscholen?",                                                       # Message 7
            "prize": "raad de plantenrij, en win 1 punt"
        },
        {
            "message": "De Total Expense Ratio, ING... naar! Daenerys zet in.",                                                         # Message 8
            "prize": "raad het Nederlandse spreekwoord waarvan dit toch echt enigszins is afgeleid, en win 2 punten"
        }
    ]
    
    # New message to append to each prize submessage
    additional_message = "\n(uitreiking door Ben)"

    # Loop through each dictionary in the list and modify the 'prize' value
    for prize_message in prize_messages:
        prize_message["prize"] += additional_message
    
    # Combine all messages for random selection
    all_messages = [
        *normal_messages,
        *[f"{msg['message']}\n\n{msg['prize']}" for msg in prize_messages]
    ]

    # Combine prize messages into a single list of formatted strings
    formatted_prize_messages = [
        f"{msg['message']}\n\n{msg['prize']}" for msg in prize_messages
    ]
    
    selected = random.choice(all_messages)
    
    if normal_only:
        selected = random.choice(normal_messages)
        
    if prize_only:
        selected = random.choice(formatted_prize_messages)

    # For prize messages, only wrap the philosophical part in italics
    for prize_msg in prize_messages:
        full_prize_msg = f"{prize_msg['message']}\n\n{prize_msg['prize']}"
        if selected == full_prize_msg:
            return f"✨_{prize_msg['message']}_✨\n\n{prize_msg['prize']}"
    
    # If it's a normal message, wrap the entire thing
    return f"✨_{selected}_✨"



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
        # Below are just 1-sec notification messages mimicing an alarm
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



async def add_user_context_to_goals(context, goal_id, **kwargs):
    """
    Adds or updates fields for a specific goal_id in user_data, flattening dictionaries and removing parent key names, such that only the deepest child keys remain (preserving all types).

    Args:
        context: The context object from the Telegram bot.
        goal_id: The unique ID of the goal to update.
        **kwargs: Key-value pairs to add or update in the goal's context.
    """
    # Ensure the goals dictionary exists
    if "goals" not in context.user_data:
        context.user_data["goals"] = {}

    # Ensure the specific goal_id dictionary exists
    if goal_id not in context.user_data["goals"]:
        context.user_data["goals"][goal_id] = {}

    # Flatten and store all input data
    for key, value in kwargs.items():
        if isinstance(value, dict):  # Flatten nested dictionaries
            for sub_key, sub_value in value.items():
                logger.info(f"Adding |{sub_key}| : |{sub_value}| to context")
                context.user_data["goals"][goal_id][sub_key] = sub_value
        elif hasattr(value, "__dict__"):  # Flatten custom objects
            for sub_key, sub_value in value.__dict__.items():
                logger.info(f"Adding |{sub_key}| : |{sub_value}| to context")
                context.user_data["goals"][goal_id][sub_key] = sub_value
        else:  # Directly store primitive types
            logger.info(f"Adding |{key}| : |{value}| to context")
            context.user_data["goals"][goal_id][key] = value


async def send_user_context(update, context):
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