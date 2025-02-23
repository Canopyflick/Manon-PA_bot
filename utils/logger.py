import logging
import os
from logging.handlers import RotatingFileHandler

from utils.helpers import add_delete_button

logger = logging.getLogger(__name__)


def configure_logging():
    # Create a formatter for logs
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler for INFO logs
    info_handler = RotatingFileHandler(
        "logs_info.log", maxBytes=1024 * 1024, backupCount=3, encoding='utf-8'  # 1 MB max, keep 3 backups
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)

    # File handler for WARNING and higher logs
    error_handler = RotatingFileHandler(
        "logs_errors.log", maxBytes=512 * 1024, backupCount=3, encoding='utf-8'  # 512 KB max, keep 3 backups
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)

    # Console handler for all logs
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)


    # Set up the root logger with the handlers
    logging.basicConfig(
        level=logging.INFO,
        handlers=[info_handler, error_handler, console_handler],
    )

    # Adjust logging levels for external libraries to reduce verbosity
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)

    # Create and return logger
    logger = logging.getLogger(__name__)
    return logger


async def fetch_logs(update, context, num_lines, type="info"):
    """
    Sends most recent logs in chat, triggered by trigger words
    """
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
