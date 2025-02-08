import os, pytz, logging, requests, asyncio, re, random, json
from datetime import time, datetime, timezone, timedelta
from utils.helpers import BERLIN_TZ
from utils.session_avatar import PA
from utils.db import Database, get_first_name
from utils.scheduler import scheduler, AsyncIOScheduler, CronTrigger, DateTrigger, IntervalTrigger

logger = logging.getLogger(__name__)

# Cleanup of old jobs before scheduling new ones
def cleanup_old_reminders():
    for job in scheduler.get_jobs():
        if job.id.startswith(('goalreminder_', 'regularreminder_')):
            scheduler.remove_job(job.id)
            

async def check_upcoming_reminders(bot):
    
    """Check for and schedule Goals' & Regular reminders due in the next 24 hours"""
    
    try: 
        cleanup_old_reminders()
    except Exception as e:
        logging.errror(f"Couldn't clean up past reminders")
        
    try:
        now = datetime.now(tz=BERLIN_TZ)
        tomorrow = now + timedelta(days=1)
        now_str = now.isoformat()
        tomorrow_str = tomorrow.isoformat()
        
        # Query for Goals' reminders in the next 24 hours
        goals_query = """
            SELECT 
                goal_id, user_id, chat_id, goal_description, deadline, reminder_time
            FROM manon_goals
            WHERE 
                reminder_scheduled = True 
                AND reminder_time >= $1 
                AND reminder_time <= $2
                AND status = 'pending'
            ORDER BY reminder_time
        """
        
        # Query for Regular (standalone) reminders in the next 24 hours
        reminders_query = """
            SELECT 
                reminder_id, user_id, chat_id, reminder_text, time
            FROM manon_reminders
            WHERE 
                time >= $1 
                AND time <= $2
            ORDER BY time
        """
        
        async with Database.acquire() as conn:
            # First query for goals' reminders
            goals_rows = await conn.fetch(goals_query, now_str, tomorrow_str)
            # Second query for regular reminders
            reminder_rows = await conn.fetch(reminders_query, now_str, tomorrow_str)

            # Schedule each Goals' reminder
            for row in goals_rows:
                reminder_time = row['reminder_time']
                # Calculate delay until reminder time
                delay = (reminder_time - now).total_seconds()
                if delay > 0:
                    # Schedule the reminder
                    scheduler.add_job(
                        send_reminder,
                        'date',
                        run_date=reminder_time,
                        args=[bot, row],
                        id=f"goalreminder_{row['goal_id']}",
                        replace_existing=True
                    )
                    logger.info(f"Scheduled Goals' reminder for goal #{row['goal_id']} at {reminder_time}")
                    
            # Schedule each Regular reminder
            for row in reminder_rows:
                reminder_time = row['time']
                # Calculate delay until reminder time
                delay = (reminder_time - now).total_seconds()
                if delay > 0:
                    # Schedule the reminder
                    scheduler.add_job(
                        send_reminder,
                        'date',
                        run_date=reminder_time,
                        args=[bot, row],
                        id=f"regularreminder_{row['reminder_id']}",
                        replace_existing=True
                    )
                    logger.info(f"Scheduled Regular reminder: #{row['reminder_id']} at {reminder_time}")

    except Exception as e:
        logger.error(f"Error checking upcoming reminders: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def send_reminder(bot, reminder_data):
    """Send a regular reminder message or for a specific goal."""
    try:
        user_id = reminder_data.get('user_id')
        chat_id = reminder_data.get('chat_id')

        # Fetch user details
        chat_member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        first_name = chat_member.user.first_name

        # Extract reminder details
        goal_description = reminder_data.get('goal_description', None)
        reminder_text = reminder_data.get('reminder_text', None)

        if goal_description:
            deadline = reminder_data.get('deadline')
            # reformat deadline
            try:
                deadline = reminder_data.get('deadline')
                if isinstance(deadline, str):
                    deadline_date = datetime.strptime(deadline, "%Y-%m-%d")
                else:  # Assuming it's already a datetime object
                    deadline_date = deadline
                formatted_deadline = deadline_date.strftime("%A, %B %d, %Y")
            except (ValueError, TypeError) as e:
                formatted_deadline = "Invalid date format"
                logger.error(f"Date parsing error: {e}")
                
            message = (
                f"{PA} Reminder for [{first_name}](tg://user?id={user_id})\n\n"
                f"You have a pending goal with a deadline on {formatted_deadline}:\n"
                f"✍️ _{goal_description}_"
            )
        elif reminder_text:
            message = (
                f"{PA} Reminder for [{first_name}](tg://user?id={user_id}):\n\n"
                f"{reminder_text}"
            )
        else:
            logger.error("Error: No goal_description or reminder_text provided.")
            return

        # Send the message
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error sending reminder: {e}")