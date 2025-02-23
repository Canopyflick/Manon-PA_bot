# utils/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from utils.helpers import BERLIN_TZ
from utils.session_avatar import PA
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from features.goals.goals import handle_goal_failure
from utils.db import Database, fetch_goal_data, get_first_name, fetch_upcoming_goals
import asyncio, random, logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=BERLIN_TZ)


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
            
            logger.info(f"goals overview message sent successfully in chat {chat_id} for {first_name}({user_id}).")
            
            return update_message, goals_count # for the today-command
        
        except Exception as e:
            logger.error(f"Error sending message to chat_id {chat_id}: {e}")
            return None, 0
            
    except Exception as e:
        logger.error(f"Error sending goals message: {e}")
        return None, 0



async def fetch_overdue_goals(chat_id, user_id, timeframe="today"):
    """
    1. fetches (overdue) pending goals
    2. puts each in a separate message with buttons for reporting progress
    """
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
                AND deadline AT TIME ZONE 'Europe/London' >= DATE_TRUNC('day', NOW()) + INTERVAL '4 hours'
                AND deadline <= DATE_TRUNC('day', NOW()) + INTERVAL '28 hours'
                """
            elif timeframe == "overdue":        # all pending goals with deadlines in the past > for /overdue
                time_condition = """
                AND deadline <= NOW()
                """
            elif timeframe == "overdue_today":    # all pending goals that went overdue today: for /today-command
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
            elif timeframe == "older":      # For the midday penalization warning message. 
                time_condition = """
                AND DEADLINE <= NOW() - INTERVAL '1 day'
                """
            elif timeframe == "older_followup":      # For the midday penalization, deleting all overdue goals older than 26 hours
                time_condition = """
                AND DEADLINE <= NOW() - INTERVAL '30 hours'
                """
            else:
                raise ValueError(f"Invalid timeframe: {timeframe}")
                
            # Build query
            query = base_query + time_condition
            params = [chat_id, user_id]
            query += " ORDER BY deadline ASC"
            logger.info(f"Query executed: {query}")
            logger.info(f"Query parameters: {params}")

            # Execute the query
            rows = await conn.fetch(query, *params)

            # Format the results
            if not rows:
                logger.info(f"No overdue goals!")
                return [], 0, 0, 0


        pending_goals = []
        total_goal_value = 0
        total_penalty = 0 
        today = datetime.now().date()
        yesterday = (datetime.now() - timedelta(days=1)).date()
        goals_count = 0
        now = datetime.now(tz=BERLIN_TZ)

        logger.info(f"Using timeframe '{timeframe}' for user_id {user_id} in chat {chat_id}: Fetched {len(rows)} rows")
        for row in rows:
            logger.info(f"Goal ID {row['goal_id']}: deadline = {row['deadline']}")
            goals_count += 1
            goal_id = row ["goal_id"]
            description = row["goal_description"] or "No description found... 👻"
            deadline_dt = row["deadline"]
            logging.critical(f"😴 Deadline for goal_id {goal_id}: {deadline_dt}, tzinfo: {deadline_dt.tzinfo}")

            deadline_date = deadline_dt.date()
            postpone_to_day = "mañana"
            # Determine if the goal should be postponed to today or tomorrow
            if deadline_dt.date() < now.date():
                # Overdue from a previous day
                if deadline_dt.time() < now.time():
                    # Deadline earlier in the day than the current time 
                    postpone_to_day = "tomorrow"
                else:
                    # Deadline later in the day
                    postpone_to_day = "today"
            elif deadline_dt.date() == now.date():
                # Due today: always only give the option to postpone to tomorrow (cause if you wanna still do it today because deadline is in the future, then you can just report Done and don't need to postpone)
                postpone_to_day = "tomorrow"


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
            final_iteration = " (❗Last in series❗)" if row["final_iteration"] == "yes" else ""
            
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
            logger.info(f"adding overdue goal:\n{pending_goal_text}")

        return pending_goals, round(total_goal_value, 1), round(total_penalty, 1), goals_count
    except Exception as e:
        logger.error(f"Error fetching overdue goals for chat_id {chat_id}, user_id {user_id}: {e}")
        return "An error occurred while fetching your overdue goals. Please try again later.", None, None, None
        

async def fail_goals_warning(bot, chat_id=None):
    delete_all_expired_goals = False
    try:
        async with Database.acquire() as conn:
            # Fetch all unique user_id/chat_id pairs
            if not chat_id:
                users = await conn.fetch("SELECT user_id, chat_id, first_name FROM manon_users")
            else: 
                delete_all_expired_goals = True
                users = await conn.fetch(f"SELECT user_id, first_name FROM manon_users WHERE chat_id = {chat_id}")  # Like this, with the unparameterized SQL query, the code could be susceptible to SQL injection attacks #security. Could be fun to try to hack myself
        warning_emojis = ["⚠️", "👮‍♀️"]
        random_emoji = random.choice(warning_emojis)
        if random.random() < 0.02:
            random_emoji = "🍆"

        now = datetime.now(tz=BERLIN_TZ)
        ultimatum_time = now + timedelta(minutes=5)
        if chat_id:
            ultimatum_time = now + timedelta(minutes=5)
        logger.info(f'ultimatum time for automatic goal_archival set for {ultimatum_time}')
        formatted_ultimatum_time = ultimatum_time.strftime('%H:%M')

        # 2. Loop through each user row and send a personalized message
        for user in users:
            user_id = user["user_id"]
            user_chat_id = chat_id if chat_id else user["chat_id"]
            if chat_id:
                overdue_goals, _, _, goals_count = await fetch_overdue_goals(user_chat_id, user_id, timeframe="overdue")   # all overdue goals
            elif not chat_id:
                user_chat_id = user["chat_id"]
                overdue_goals, _, _, goals_count = await fetch_overdue_goals(user_chat_id, user_id, timeframe="older")   # overdue for more than 24 hours
            first_name = user["first_name"] or "Katja"  # Fallback if first_name is NULL or empt
            # 3. Check any >24hs old overdue goals (or all overdue goals, if trigger-word-triggered)
             
            logging.debug(f"overdue goals for user_id {user_id}: {overdue_goals}")
            if not overdue_goals and delete_all_expired_goals:
                await bot.send_message(chat_id, f"You have no overdue goals to resolve {PA}")
                continue
            elif overdue_goals:
                greeting = (
                    f"Hi {first_name}, you have "
                    f"{'one older /overdue goal' if goals_count == 1 else f'{goals_count} older /overdue goals'} open {PA}\n\n"
                    f"Report on {'it' if goals_count == 1 else 'them'} by {formatted_ultimatum_time} today if you want to avoid automatic archiving and penalization 🍆 🌚"
                )     
                if delete_all_expired_goals:
                    greeting.replace("older ", "")
                # 4. send messages
                if random.random() < 0.0273972603:  # once per year if triggered every 10 days
                    greeting += "\n_Oh yeah, and also: mindfulness could be a great option right now. Same goes for right now, by the way"
                try:
                    await bot.send_message(chat_id, random_emoji)
                    await bot.send_message(chat_id, greeting, parse_mode="Markdown")
                    for goal in overdue_goals:
                        logger.warning(f"Overdue goals for user_id {user_id}: {overdue_goals}")

                        if not isinstance(goal, dict) or "text" not in goal or "buttons" not in goal:
                            continue
                        await asyncio.sleep(1)
                        await bot.send_message(
                            chat_id=chat_id,
                            text=goal["text"],
                            reply_markup=goal["buttons"],
                            parse_mode="Markdown" 
                        )
                        
                        # Extract goal_id from the callback_data of the first button
                        try:
                            first_button = goal["buttons"].inline_keyboard[0][0]  # First row, first button
                            callback_data = first_button.callback_data
                            goal_id = int(callback_data.split('_')[-1])  # Assuming goal_id is after the last '_'
                        except (AttributeError, IndexError, ValueError) as e:
                            logger.error(f"Failed to extract 'goal_id' from goal: {goal}, error: {e}")
                            continue
                        
                        # Extract hour and minute for the CronTrigger, then schedule archiving/penalizing job
                        ultimatum_hour = ultimatum_time.hour
                        ultimatum_minute = ultimatum_time.minute
                        scheduler.add_job(
                            scheduled_goal_archival, 
                            DateTrigger(run_date=ultimatum_time),
                            args=[bot, goal_id, ultimatum_time, delete_all_expired_goals],
                            misfire_grace_time=3600,
                            coalesce=True
                        )
                    if not chat_id:
                        logger.info(f"Daily older overdue goals warning message sent successfully in chat {chat_id} for {first_name}({user_id}).")
                    elif chat_id:
                        logger.info(f"Trigger-word-triggered older overdue goals warning message sent successfully in chat {chat_id} for {first_name}({user_id}).")
                except Exception as e:
                    logger.error(f"Error sending overdue goals warning message to chat_id {chat_id}: {e}")
            
    except Exception as e:
        logger.error(f"Error sending overdue goals warning message: {e}")


async def scheduled_goal_archival(bot, goal_id, ultimatum_time, delete_all_expired_goals):
    try:
        logger.info(f'Archiving goal {goal_id}')
        status = await fetch_goal_data(goal_id, columns="status", single_value=True)
        if status == "pending":     # only needs to be actually run if the user didn't report anything after the warning
            update = 1.5 
            await handle_goal_failure(update, goal_id, query=None, bot=bot, delete_all_expired_goals=delete_all_expired_goals)
        else:
            logger.info(f"Goal #{goal_id} was not archived at {ultimatum_time}, because it was not pending anymore (user processed it themselves)")
    except Exception as e:
        logger.error(f"Error in schedule_goal_deletion(): {e}")


async def send_next_jobs(update, context, N=5):
    """
    Function to send the next N jobs in chat (triggered by trigger text)
    """
    jobs = scheduler.get_jobs()  # Fetch all scheduled jobs
    jobs.sort(key=lambda job: job.next_run_time)  # Sort by next run time

    if not jobs:
        await update.message.reply_text(f"No scheduled jobs at the moment {PA}")
        return

    # Get the next N jobs
    job_details = []
    for job in jobs[:N]:
        run_time = job.next_run_time.strftime('%H:%M:%S (%a)') if job.next_run_time else "Unknown"
        job_name = job.name if job.name else "Unnamed job"
        job_details.append(f"🕒 {run_time}\n{job.name}")

    # Send the job list as a message
    job_list_text = "\n".join(job_details)
    await update.message.reply_text(f"{PA} Here are the next scheduled jobs:\n\n{job_list_text}")
