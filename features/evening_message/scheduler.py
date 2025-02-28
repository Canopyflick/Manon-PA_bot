# features/evening_message/scheduler.py
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from features.evening_message import send_evening_message
from utils.helpers import BERLIN_TZ

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def initialize_scheduler():
    """
    Initialize the global scheduler instance if not already created.

    Returns:
        The scheduler instance
    """
    global scheduler
    if scheduler is None:
        logger.info("Initializing evening message scheduler")
        scheduler = AsyncIOScheduler(timezone=BERLIN_TZ)
        if not scheduler.running:
            scheduler.start()
    return scheduler


def schedule_evening_message(bot, hour=20, minute=20):
    """
    Schedule the evening message to be sent daily at the specified time.

    Args:
        bot: The bot instance to use for sending messages
        hour (int): Hour of the day (0-23) in Berlin timezone
        minute (int): Minute of the hour (0-59)
    """
    global scheduler

    # Initialize scheduler if not already done
    scheduler = initialize_scheduler()

    # Job ID for the evening message job
    job_id = "evening_message_job"

    # Remove any existing job with the same ID
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    # Add the new job
    scheduler.add_job(
        send_evening_message,
        CronTrigger(hour=hour, minute=minute, timezone=BERLIN_TZ),
        args=[bot],
        id=job_id,
        name="Evening Message",
        misfire_grace_time=7200,  # 2 hours grace time
        coalesce=True  # Only run once if multiple executions are missed
    )

    next_run = scheduler.get_job(job_id).next_run_time
    logger.info(f"Evening message scheduled for {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")


def get_scheduler():
    """
    Get the current scheduler instance, initializing it if necessary.

    Returns:
        The scheduler instance
    """
    global scheduler
    if scheduler is None:
        return initialize_scheduler()
    return scheduler


def is_evening_message_scheduled():
    """
    Check if the evening message job is scheduled.

    Returns:
        bool: True if scheduled, False otherwise
    """
    global scheduler
    if scheduler is None:
        return False
    return scheduler.get_job("evening_message_job") is not None


def get_next_evening_message_time():
    """
    Get the next scheduled run time for the evening message.

    Returns:
        datetime: The next run time, or None if not scheduled
    """
    global scheduler
    if scheduler is None:
        return None

    job = scheduler.get_job("evening_message_job")
    if job:
        return job.next_run_time
    return None


# Function to be called from setup()
def setup_evening_message_scheduler(bot, hour=20, minute=20):
    """
    Sets up the evening message scheduler during application initialization.
    This function should be called from the main setup() function.

    Args:
        bot: The bot instance
        hour (int): Hour to send evening messages (default: 20)
        minute (int): Minute to send evening messages (default: 20)
    """
    try:
        now = datetime.now(tz=BERLIN_TZ)
        logger.info(f"Setting up evening message scheduler at {now}")
        schedule_evening_message(bot, hour, minute)
        logger.info(f"Evening message scheduler setup completed (daily at {hour}:{minute})")
    except Exception as e:
        logger.error(f"Error setting up evening message scheduler: {e}")