from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from utils.helpers import get_btc_price, PA, BERLIN_TZ, datetime
from datetime import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from utils.db import Database
import asyncio, random, re, logging




scheduler = AsyncIOScheduler()

async def send_morning_message(bot):
    try:
        async with Database.acquire() as conn:
            # Fetch all unique user_id/chat_id pairs
            users = await conn.fetch("SELECT user_id, chat_id, first_name FROM manon_users")
            
        # Fetch Bitcoin price and change percentage
        _, detailed_message, _, usd_change = await get_btc_price()
        change_message = ""
        if abs(usd_change) > 5:
            change_message = f"\n\n📈 _฿itcoin price changed by {usd_change:.2f}% in the last 24 hours._\n{detailed_message}"
        
        morning_emojis = ["🍵", "☕", "🌄", "🌅", "🌞", "☃️", "❄️"]
        random_emoji = random.choice(morning_emojis)
        
        greeting = "Goord morning"
        announcement = "Your goals for the day are"
        # Check if it's morning or not
        morning_start = time(4, 0)  # 4:00 am
        morning_end = time(12, 0)  # 12:00 pm
        now = datetime.now(tz=BERLIN_TZ)
        if not (morning_start <= now.time() <= morning_end):
            greeting = "Why hey,"
            announcement = "Your upcoming goals are"

        # Loop through each user and send a personalized message
        for user in users:
            user_id = user["user_id"]
            chat_id = user["chat_id"]
            first_name = user["first_name"] or "there"  # Fallback if first_name is NULL or empt
            
            goals_today, total_goal_value, total_penalty = await fetch_todayta(chat_id, user_id)
            
            daily_message = (
                f"*{greeting}, {first_name}!* {PA}\n"
                f"{announcement}\n{goals_today}\n\n"
                f"Go get some (⚡{total_goal_value}) ... or lose some ({total_penalty}🌚 )\n"
            )
            
            daily_message += change_message
            if random.random() < 0.0273972603:  # ~10 times per year
                daily_message += "\n\nZet je beste beentje voor, je kunt er niets aan doen, maar je kunt er wel wat aan doen! ❤️\n_'[memorabele quote enzo]'_}"
            try:
                await bot.send_message(chat_id, random_emoji)
                await bot.send_message(chat_id, daily_message, parse_mode="Markdown")
                await bot.send_message(chat_id, "🚀")
                logging.info(f"Daily message sent successfully in chat {chat_id} for {first_name}({user_id}).")
            except Exception as e:
                logging.error(f"Error sending message to chat_id {chat_id}: {e}")
            
    except Exception as e:
        logging.error(f"Error sending daily message: {e}")



async def fetch_todayta(chat_id, user_id):
    try:
        async with Database.acquire() as conn:
            # Query to fetch goals with deadlines in the next 30 hours
            query = '''
                SELECT 
                    goal_description, 
                    deadline, 
                    goal_value, 
                    penalty, 
                    reminder_scheduled, 
                    final_iteration
                FROM manon_goals
                WHERE chat_id = $1 
                AND user_id = $2
                AND deadline <= NOW() + INTERVAL '28 hours'
                AND deadline >= NOW()
                ORDER BY deadline ASC
            '''
            rows = await conn.fetch(query, chat_id, user_id)

        # Format the results
        if not rows:
            return "You have no deadlines between now and tomorrow morning ☃️", 0, 0

        goals_today = []
        total_goal_value = 0
        total_penalty = 0 
        for row in rows:
            description = row["goal_description"] or "No description found... 👻"
            deadline = row["deadline"].strftime("%a\u2009%H:%M")
            goal_value = f"{row['goal_value']:.1f}" if row["goal_value"] is not None else "N/A"
            penalty = f"{row['penalty']:.1f}" if row["penalty"] is not None else "N/A"
            reminder = "⏰" if row["reminder_scheduled"] else ""
            final_iteration = " (Last in series)" if row["final_iteration"] == "yes" else ""
            
            total_goal_value += float(goal_value)
            total_penalty += float(penalty) 

            # Create a formatted string for each goal
            goals_today.append(
                f"*{description}*{final_iteration}\n"
                f"  📅 Deadline: {deadline} {reminder}\n"
                f"  ⚡/🌚 {goal_value}/{penalty}\n"
            )

        return "\n\n".join(goals_today), round(total_goal_value, 1), round(total_penalty, 1)
    except Exception as e:
        logging.error(f"Error fetching goals for chat_id {chat_id}, user_id {user_id}: {e}")
        return "An error occurred while fetching your goals. Please try again later."
