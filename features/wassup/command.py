# features/wassup/command.py

from telegram import Update
from telegram.ext import ContextTypes
from utils.db import Database
from utils.session_avatar import PA
from datetime import datetime
from utils.helpers import BERLIN_TZ
import random
import logging

logger = logging.getLogger(__name__)


async def wassup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Fetches a random goal with status 'prepared' (open-ended goals) and reminds the user about it.
    Sends two messages:
    1. "On <date> you expressed the intention to one day✨ do something. You said:"
    2. "<goal_description>"
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    try:
        async with Database.acquire() as conn:
            # Fetch all prepared goals for this user
            prepared_goals = await conn.fetch("""
                SELECT goal_id, goal_description, set_time
                FROM manon_goals 
                WHERE user_id = $1 AND chat_id = $2 AND status = 'prepared'
                ORDER BY set_time DESC
            """, user_id, chat_id)
            
            if not prepared_goals:
                await update.message.reply_text(
                    f"You don't have any open-ended goals waiting in the wings {PA}\n\n"
                    "Try expressing something you'd like to do 'at some point' and I'll save it for later!",
                    parse_mode="Markdown"
                )
                return
            
            # Pick a random goal
            random_goal = random.choice(prepared_goals)
            goal_description = random_goal['goal_description']
            set_time = random_goal['set_time']
            
            # Format the date
            if isinstance(set_time, str):
                set_time = datetime.fromisoformat(set_time.replace('Z', '+00:00'))
            elif set_time.tzinfo is None:
                set_time = set_time.replace(tzinfo=BERLIN_TZ)
            
            formatted_date = set_time.strftime('%A, %d %B %Y')
            
            # Send the two messages as requested
            await update.message.reply_text(
                f"{PA} On {formatted_date} you expressed the intention to one day✨ do something. You said:",
                parse_mode="Markdown"
            )
            
            await update.message.reply_text(
                f"_{goal_description}_",
                parse_mode="Markdown"
            )
            
            logger.info(f"Reminded user {user_id} about prepared goal: {goal_description[:50]}...")
            
    except Exception as e:
        logger.error(f"Error in wassup_command: {e}")
        await update.message.reply_text(
            f"Something went wrong while fetching your open-ended goals {PA}",
            parse_mode="Markdown"
        )

