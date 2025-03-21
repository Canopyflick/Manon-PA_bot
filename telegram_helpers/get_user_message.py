# telegram_helpers/get_user_message.py
from telegram import Update
from utils.helpers import logger

def get_user_message(update: Update, context) -> str:
    try:
        if update.message.text:
            return update.message.text
        else:
            return context.user_data.get("user_message")
    except Exception as e:
        logger.error(f"couldn't get user message: {e}")
