# features/morning_message/scheduler.py
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from features.morning_message import send_morning_message
from utils.helpers import BERLIN_TZ
from utils.scheduler import scheduler


logger = logging.getLogger(__name__)


def initialize_scheduler():
    """
    Initialize the global scheduler instance if not already created.

    Returns:
        The scheduler instance
    """
    if not scheduler.running:
        logger.info("Starting scheduler in morning message module")
        scheduler.start()
    return scheduler


def schedule_morning_message(bot, hour=6, minute=6):
    """
    Schedule the morning message to be sent daily at the specified time.

    Args:
        bot: The bot instance to use for sending messages
        hour (int): Hour of the day (0-23) in Berlin timezone
        minute (int): Minute of the hour (0-59)
    """

    # Initialize scheduler if not already done
    initialize_scheduler()

    # Job ID for the morning message job
    job_id = "morning_message_job"

    # Remove any existing job with the same ID
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    # Add the new job
    scheduler.add_job(
        send_morning_message,
        CronTrigger(hour=hour, minute=minute, timezone=BERLIN_TZ),
        args=[bot],
        id=job_id,
        name="Morning Message",
        misfire_grace_time=7200,  # 2 hours grace time
        coalesce=True  # Only run once if multiple executions are missed
    )

    next_run = scheduler.get_job(job_id).next_run_time
    logger.info(f"Morning message scheduled for {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")


def get_scheduler():
    """
    Get the current scheduler instance, initializing it if necessary.

    Returns:
        The scheduler instance
    """
    if not scheduler.running:
        return initialize_scheduler()
    return scheduler


def is_morning_message_scheduled():
    """
    Check if the morning message job is scheduled.

    Returns:
        bool: True if scheduled, False otherwise
    """
    return scheduler.get_job("morning_message_job") is not None


def get_next_morning_message_time():
    """
    Get the next scheduled run time for the morning message.

    Returns:
        datetime: The next run time, or None if not scheduled
    """
    job = scheduler.get_job("morning_message_job")
    if job:
        return job.next_run_time
    return None


# Function to be called from setup()
def setup_morning_message_scheduler(bot, hour=6, minute=6):
    """
    Sets up the morning message scheduler during application initialization.
    This function should be called from the main setup() function.

    Args:
        bot: The bot instance
        hour (int): Hour to send morning messages (default: 6)
        minute (int): Minute to send morning messages (default: 6)
    """
    try:
        now = datetime.now(tz=BERLIN_TZ)
        logger.info(f"Setting up morning message scheduler at {now}")
        schedule_morning_message(bot, hour, minute)
        logger.info(f"Morning message scheduler setup completed (daily at {hour}:{minute})")
    except Exception as e:
        logger.error(f"Error setting up morning message scheduler: {e}")