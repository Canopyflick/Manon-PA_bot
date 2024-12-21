from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from utils.helpers import get_btc_price, PA, BERLIN_TZ, datetime, timedelta
from datetime import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from utils.db import Database, get_first_name, fetch_upcoming_goals
import asyncio, random, re, logging


scheduler = AsyncIOScheduler()

# still wanna add: 1. Prompt to report on yesterday's unfinished goals (separate message with buttons for each)
async def send_morning_message(bot, specific_chat_id=None):
    try:
        async with Database.acquire() as conn:
            # Fetch all unique user_id/chat_id pairs
            users = await conn.fetch("SELECT user_id, chat_id, first_name FROM manon_users")
            
        # 1. Add Bitcoin price if it changed a lot 
        _, detailed_message, _, usd_change = await get_btc_price()
        change_message = ""
        if abs(usd_change) > 5:
            change_message = f"\n\n📈 _฿itcoin price changed by {usd_change:.2f}% in the last 24 hours._\n{detailed_message}"
        
        morning_emojis = ["🍵", "☕", "🌄", "🌅", "🌞", "☃️", "❄️"]
        random_emoji = random.choice(morning_emojis)
        
        greeting = "Good morning"
        announcement = "Your goals for the day are:"
        # Check if it's morning or not
        morning_start = time(4, 0)  # 4:00 am
        morning_end = time(12, 0)  # 12:00 pm
        now = datetime.now(tz=BERLIN_TZ)
        if not (morning_start <= now.time() <= morning_end):
            greeting = "Why hello there"
            announcement = "Your upcoming goals are:"

        # 2. Loop through each user row and send a personalized message
        for user in users:
            user_id = user["user_id"]
            chat_id = user["chat_id"]
            if specific_chat_id and chat_id != specific_chat_id:
                continue
                
            first_name = user["first_name"] or "there"  # Fallback if first_name is NULL or empt
            
            # 3. Check any overdue goals since last night (usually none)
            overdue_goals, _, _, goals_count = await fetch_overdue_goals(chat_id, user_id, timeframe="yesterday")   # overdue between 4 AM and now yesterday
            logging.debug(f"overdue goals for user_id {user_id}: {overdue_goals}")

            greeting_message = f"*{greeting}, {first_name}!* {PA}\n"
            recap_message = None
            if overdue_goals:
                recap_message = f"\n_First, some unfinished business:_"
            
            # 4. Check schedule today: all upcoming goals
            goals_today, total_goal_value, total_penalty, goals_count = await fetch_upcoming_goals(chat_id, user_id, timeframe=10)    # fetching upcoming goals from now until 10am tomorrow
            logging.warning(f"Alles gefetcht:\n{goals_today}, \n{total_goal_value}, \n{total_penalty}, \n{goals_count}")
            morning_message = (
                f"{announcement}\n\n{goals_today}\n\n"
            )
            stakes_message = f"_Go get some (⚡{total_goal_value}) ..!\n... or lose some ({total_penalty}🌚)_\n"
            if total_goal_value == 0 or goals_count == 1:
                stakes_message = ''
            if goals_count == 0:
                announcement = ''
            logging.warning(f"morning message: {morning_message}")
            morning_message += stakes_message
            
            morning_message += change_message
            if random.random() < 0.00273972603:  # once per year if triggered daily
                morning_message += "\n\nZet je beste beentje voor, je kunt er niets aan doen, maar je kunt er wel wat aan doen! ❤️\n\n_'[memorabele quote enzo]'_}"
            try:
                await bot.send_message(chat_id, random_emoji)
                if recap_message:
                    greeting_message += recap_message
                await bot.send_message(chat_id, greeting_message, parse_mode="Markdown")
                if overdue_goals:
                    for goal in overdue_goals:
                        if not isinstance(goal, dict) or "text" not in goal or "buttons" not in goal:
                            continue
                        await asyncio.sleep(1)
                        await bot.send_message(
                            chat_id=chat_id,
                            text=goal["text"],
                            reply_markup=goal["buttons"],
                            parse_mode="Markdown" 
                        )
                await asyncio.sleep(3)
                await bot.send_message(chat_id, morning_message, parse_mode="Markdown")
                await asyncio.sleep(4)
                await bot.send_message(chat_id, "🚀")
                logging.info(f"Daily message sent successfully in chat {chat_id} for {first_name}({user_id}).")
            except Exception as e:
                logging.error(f"Error sending morning message to chat_id {chat_id}: {e}")
            
    except Exception as e:
        logging.error(f"Error sending daily message: {e}")





async def send_goals_today(update, context, chat_id, user_id, timeframe):
    try:
        first_name = await get_first_name(context, user_id, chat_id)
        greetings = ["Whoa hey, ", "hellooo, ", "Hi, ", "👋, ", "", "☃️, ", "Why hello there, ", "Hey, ", "Alright, listen up, "]
        greeting = random.choice(greetings)
        announcement = "Your remaining goals today are:"
        
        if timeframe == "24hs":
            announcement = "Your next 24 hours ..."
       
        goals_today, total_goal_value, total_penalty, goals_count = await fetch_upcoming_goals(chat_id, user_id, timeframe)
        
        if "You have no deadlines" in goals_today and timeframe == "24hs":
            goals_today = f"... nothing I know about happens {PA}"
            
        update_message = (
            f"*{greeting}{first_name}!* {PA}\n"
            f"{announcement}\n\n{goals_today}\n\n"
        )
        stakes_message = f"_Still ⚡{total_goal_value}/🌚{total_penalty} at stake._"
        if total_goal_value == 0 or goals_count == 1:
            stakes_message = ""
                
        update_message += stakes_message
 
        try:
            update_message = await context.bot.send_message(chat_id, update_message, parse_mode="Markdown")
            
            logging.info(f"goals overview message sent successfully in chat {chat_id} for {first_name}({user_id}).")
            
            return update_message, goals_count # for the today-command
        
        except Exception as e:
            logging.error(f"Error sending message to chat_id {chat_id}: {e}")
            return None, 0
            
    except Exception as e:
        logging.error(f"Error sending goals message: {e}")
        return None, 0

        
# set the time that the message is scheduled daily for in main()
evening_message_hours = 20
evening_message_minutes = 20
async def send_evening_message(bot, specific_chat_id=None):
    try:
        async with Database.acquire() as conn:
            # Fetch all unique user_id/chat_id pairs
            users = await conn.fetch("SELECT user_id, chat_id, first_name FROM manon_users")
            
        # Fetch Bitcoin price and change percentage
        _, detailed_message, _, usd_change = await get_btc_price()
        change_message = ""
        if abs(usd_change) > 10:
            change_message = f"\n\n📈 _฿itcoin price changed by {usd_change:.2f}% in the last 24 hours._\n{detailed_message}"
        
        evening_emojis = ["🫖", "💫", "🌇", "🌆", "💤", "😴", "🛌"]
        random_emoji = random.choice(evening_emojis)
        
        greeting = "Good evening"
        announcement = "Please report on goal progress for:"
        # Check if it's morning or not
        evening_start = time(18, 0)  # 18:00
        evening_end = time(23, 59)  # 23:59
        now = datetime.now(tz=BERLIN_TZ)
        if not (evening_start <= now.time() <= evening_end):
            greeting = "Why hello there"
            announcement = "Your overdue goals are:"

        # Loop through each user row and send a personalized message
        for user in users:
            user_id = user["user_id"]
            chat_id = user["chat_id"]
            # skip irrelevant chats if a specific chat was specified
            if specific_chat_id and chat_id != specific_chat_id:
                continue
                
            first_name = user["first_name"] or "Sardientje"  # Fallback if first_name is NULL or empt
            
            overdue_goals, total_goal_value, total_penalty, goals_count = await fetch_overdue_goals(chat_id, user_id, timeframe="today")   # only check goals that overdue yesterday
            logging.debug(f"overdue goals for user_id {user_id}: {overdue_goals}")

            if isinstance(overdue_goals, str):
                announcement = "No pending overdue goals, you're all caught up ✨"
            
            nightly_message = (
                f"*{greeting}, {first_name}!* {PA}\n"
                f"{announcement}\n\n"
            )
            stakes_message = f"_⚡{total_goal_value} & 🌚{total_penalty} on the line._\n"
            if total_goal_value == 0 or goals_count == 1:
                stakes_message = None
            
            nightly_message += change_message
            if random.random() < 0.00273972603:  # once per year if triggered daily
                nightly_message += "\n\nAwel slaap wel! ❤️\n\n_'[memorabele quote enzo]'_}"
            try:
                await bot.send_message(chat_id, "🌚")
                await asyncio.sleep(2)
                await bot.send_message(chat_id, nightly_message, parse_mode="Markdown")
                for goal in overdue_goals:
                    if not isinstance(goal, dict) or "text" not in goal or "buttons" not in goal:
                        continue
                    await bot.send_message(
                        chat_id=chat_id,
                        text=goal["text"],
                        reply_markup=goal["buttons"],
                        parse_mode="Markdown"
                    )
                await asyncio.sleep(4)
                if stakes_message:
                    await bot.send_message(chat_id, stakes_message, parse_mode="Markdown")
                await bot.send_message(chat_id, random_emoji)
                logging.info(f"Nightly message sent successfully in chat {chat_id} for {first_name}({user_id}).")
            except Exception as e:
                logging.error(f"Error in evening message sending message to chat_id {chat_id}: {e}")
            
    except Exception as e:
        logging.error(f"Error sending daily message: {e}")


# fetches (overdue) pending goals, puts each in a separate message with buttons for reporting progress
async def fetch_overdue_goals(chat_id, user_id, timeframe="today"):
    try:
        async with Database.acquire() as conn:
            # Prepare base query with placeholders
            base_query = '''
                SELECT
                    goal_id,
                    goal_description, 
                    deadline, 
                    goal_value, 
                    penalty, 
                    reminder_scheduled, 
                    final_iteration
                FROM manon_goals
                WHERE chat_id = $1 
                AND user_id = $2
                AND status = 'pending'
            '''        
            time_condition = "AND deadline <= NOW()"    
            # Dynamic time condition logic
            if timeframe == "today":            # all pending goals today (4AM this morning - 4AM later tonight) > for the final evening message
                time_condition = """
                AND deadline >= DATE_TRUNC('day', NOW()) + INTERVAL '4 hours'
                AND deadline <= DATE_TRUNC('day', NOW()) + INTERVAL '28 hours'
                """
            elif timeframe == "overdue":        # all pending goals with deadlines in the past > for /overdue
                time_condition = """
                AND deadline <= NOW()
                """
            elif timeframe == "overdue_today":    # all pending goals that overdue today: for /today-command
                time_condition = """
                AND deadline >= DATE_TRUNC('day', NOW()) + INTERVAL '4 hours'
                AND deadline <= NOW()
                """
            elif timeframe == "overdue_old":    # These need to periodically be archived_failed > penaltied     
                time_condition = """
                AND deadline <= DATE_TRUNC('day', NOW()) - INTERVAL '1 day'
                """
            elif timeframe == "yesterday":      # For the morning message, any open deadlines SINCE last night's final evening message (only from 4AM to now, usually 4-6am, unless morning message runs later)
                time_condition = """
                AND DEADLINE <= NOW()
                AND deadline >= DATE_TRUNC('day', NOW()) + INTERVAL '4 hours'
                """
            else:
                raise ValueError(f"Invalid timeframe: {timeframe}")
                
            # Build query
            query = base_query + time_condition
            params = [chat_id, user_id]
            query += " ORDER BY deadline ASC"

            # Execute the query
            rows = await conn.fetch(query, *params)

            # Format the results
            if not rows:
                logging.info(f"No overdue goals!")
                return [], 0, 0, 0

        pending_goals = []
        total_goal_value = 0
        total_penalty = 0 
        today = datetime.now().date()
        yesterday = (datetime.now() - timedelta(days=1)).date()
        goals_count = 0
        now = datetime.now(tz=BERLIN_TZ)
        one_hour_from_now = now + timedelta(hours=1)

        for row in rows:
            goals_count += 1
            goal_id = row ["goal_id"]
            description = row["goal_description"] or "No description found... 👻"
            deadline_dt = row["deadline"]
            logging.critical(f"😴 Deadline for goal_id {goal_id}: {deadline_dt}, tzinfo: {deadline_dt.tzinfo}")

            deadline_date = deadline_dt.date()
            postpone_to_day = "mañana"
            # Determine postpone_to_day based on time comparison
            if deadline_dt <= one_hour_from_now:
                postpone_to_day = "tomorrow"
            else:
                postpone_to_day = "today"

            # Format the deadline
            if deadline_date == today:
                deadline = f"{deadline_dt.strftime('%H:%M')} today"
            elif deadline_date == yesterday:
                deadline = f"{deadline_dt.strftime('%H:%M')} yesterday"
            else:
                deadline = f"{deadline_dt.strftime('%a, %d %B')}"

            goal_value = f"{row['goal_value']:.1f}" if row["goal_value"] is not None else "N/A"
            penalty = float(f"{row['penalty']:.1f}") if row["penalty"] is not None else 0  # Use 0.0 as a default
            reminder = "⏰" if row["reminder_scheduled"] else ""
            final_iteration = " (❗Last in series)" if row["final_iteration"] == "yes" else ""
            
            total_goal_value += float(goal_value)
            total_penalty += float(penalty) 

            # Message text for the goal
            pending_goal_text = (
                f"*{description}* {final_iteration}\n"
                f"📅 Deadline: {deadline} {reminder}\n"
                f"⚡ {goal_value} | 🌚 {penalty}\n"
                f"#{goal_id}"
            )

            cost_to_postpone = round(penalty * 0.65, 1)
            
            # Inline keyboard buttons for each goal
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Done", callback_data=f"finished_{goal_id}"),
                    InlineKeyboardButton("❌ Failed", callback_data=f"failed_{goal_id}")
                ],
                [
                    InlineKeyboardButton(f"⏭️ {postpone_to_day.capitalize()}..! (-{cost_to_postpone})", callback_data=f"postpone_{goal_id}_{postpone_to_day}")
                ]
            ])
            # Append each goal as a dictionary with text and buttons
            pending_goals.append({"text": pending_goal_text, "buttons": buttons})
            logging.info(f"adding overdue goal:\n{pending_goal_text}")

        return pending_goals, round(total_goal_value, 1), round(total_penalty, 1), goals_count
    except Exception as e:
        logging.error(f"Error fetching overdue goals for chat_id {chat_id}, user_id {user_id}: {e}")
        return "An error occurred while fetching your overdue goals. Please try again later.", None, None, None
        