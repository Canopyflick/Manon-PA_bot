import logging
from logging.handlers import RotatingFileHandler

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
