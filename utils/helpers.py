from telegram import Update, ChatMember, Bot
from telegram.ext import CallbackContext, ExtBot
from typing import Union
from datetime import timedelta, datetime
import os, psycopg2, pytz, logging
from openai import OpenAI


cet = pytz.timezone('Europe/Berlin')  # Automatically adjusts for CET/CEST based on the date


# Only load dotenv if running locally (not on Heroku)
if not os.getenv('HEROKU_ENV'):
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except ImportError:
        pass  # In case dotenv isn't installed, ignore this when running locally

# Flag to indicate if running locally
LOCAL_FLAG = not os.getenv('HEROKU_ENV', False)

# Get OpenAI API key from environment variable
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found! Ensure it's set in the environment.")

client = OpenAI(api_key=OPENAI_API_KEY)

def get_database_connection():
    # Use DATABASE_URL if available (Heroku), otherwise fallback to LOCAL_DB_URL
    DATABASE_URL = os.getenv('DATABASE_URL', os.getenv('LOCAL_DB_URL'))

    if not DATABASE_URL:
        raise ValueError("Database URL not found! Ensure 'DATABASE_URL' or 'LOCAL_DB_URL' is set in the environment.")

    # Connect to the PostgreSQL database
    if os.getenv('HEROKU_ENV'):  # Running on Heroku
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    else:  # Running locally
        conn = psycopg2.connect(DATABASE_URL)  # For local development, no SSL required

    return conn



async def check_chat_owner(update: Update, context):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Get chat administrators
    admins = await context.bot.get_chat_administrators(chat_id)
    
    # Check if the user is the owner (creator)
    for admin in admins:
        if admin.user.id == user_id and admin.status == 'creator':
            return True
    return False


# Security check: am I in the chat where the bot is used?
async def is_ben_in_chat(update, context):
    USER_ID = 1875436366
    chat_id = update.effective_chat.id
    try:
        # Get information about your status in the chat
        member = await context.bot.get_chat_member(chat_id, USER_ID)
        # Check if you're a member, administrator, or have any active role in the chat
        if member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Error checking chat member: {e}")
        return False
    

# Private message to Ben (test once then delete)
async def notify_ben(update,context):
        USER_ID = 1875436366
        first_name = update.effective_user.first_name
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        message = update.message.text
        notification_message = f"You've got mail ✉️🧙‍♂️\n\nUser: {first_name}, {user_id}\nChat: {chat_id}\nMessage:\n{message}"
        logging.error(f"! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! \n\n\n\nUnauthorized Access Detected\n\n\n\n! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !\nUser: {first_name}, {user_id}\nChat: {chat_id}\nMessage: {message}")
        await context.bot.send_message(chat_id=USER_ID, text=notification_message)
        

async def get_first_name(context_or_bot: Union[Bot, ExtBot, CallbackContext], user_id: int) -> str:
    global global_bot
    try:
        # Check if context_or_bot is a CallbackContext
        if isinstance(context_or_bot, CallbackContext):
            bot = context_or_bot.bot
        # If it's a Bot or ExtBot instance, use it directly
        elif isinstance(context_or_bot, (Bot, ExtBot)):
            bot = context_or_bot
        else:
            # Fallback to global bot if available
            if global_bot is None:
                raise ValueError("No bot instance available")
            bot = global_bot

        # Now, 'bot' is guaranteed to be a Bot or ExtBot instance
        chat_member = await bot.get_chat_member(user_id, user_id)
        return chat_member.user.first_name

    except Exception as e:
        logging.error(f"Error fetching user details for user_id {user_id}: {e}")
        return "Lodewijk 🚨🐛"