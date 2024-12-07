import io, sys, os, logging, asyncio
from logging.handlers import RotatingFileHandler
from telegram import ChatMember
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, CallbackQueryHandler, PollHandler, ExtBot
from datetime import datetime, timezone
from utils.helpers import get_database_connection
from utils.db import setup_database


print("... STARTING ... 👩‍🦱  \n\n")

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
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)


    # Set up the root logger with the handlers
    logging.basicConfig(
        level=logging.INFO,
        handlers=[info_handler, error_handler, console_handler],
    )
    
    # Adjust logging levels for external libraries to reduce verbosity
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)

configure_logging()

# Global bot instance
global_bot: ExtBot = None

local_flag = False


# Only load dotenv if running locally (not on Heroku)
if not os.getenv('HEROKU_ENV'):  # Check if HEROKU_ENV is not set, meaning it's local
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
        local_flag = True
    except ImportError:
        pass  # In case dotenv isn't installed, ignore this when running locally
    


# Function to reset stuff that is in context or something, ie temporary memory that is lost when the bot reboots
def reset_things_on_startup():
    logging.info(f"🕳️ Reset ... Nothing Yet (placeholder)")


# Set up the database and environment
def initialize_environment():
    setup_database()
    reset_things_on_startup()
    logging.info("Environment initialized.")
    

# Retrieve the bot token based on the environment
def get_bot_token() -> str:
    token = os.getenv('LOCAL_TELEGRAM_API_KEY' if local_flag else 'TELEGRAM_API_KEY')
    if not token:
        raise ValueError("Telegram API key is missing!")
    return token.strip()

# Register bot commands and handlers
def register_handlers(application):
    from modules.commands import start_command, help_command, stats_command, filosofie_command, btc_command, bitcoin_command, smarter_command, translate_command
    application.add_handler(CommandHandler(["start", "begroeting", "begin"], start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("filosofie", filosofie_command))
    
    # Add the /btc /bitcoin command handler
    application.add_handler(CommandHandler("btc", btc_command))
    application.add_handler(CommandHandler("bitcoin", bitcoin_command))
    
    application.add_handler(CommandHandler("smarter", smarter_command))
    application.add_handler(CommandHandler("translate", translate_command))
    
    from utils.listener import analyze_any_message, print_edit  
    # Bind the message analysis to any non-command text messages
    application.add_handler(MessageHandler(filters.TEXT, analyze_any_message))        
    # Handler for edited messages
    application.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE & filters.TEXT & ~filters.COMMAND, print_edit))


async def setup(application):
    try:
        logging.info("Running setup tasks...")
        initialize_environment()  # Sets up the database and resets reminders
        now = datetime.now(tz=timezone.utc)
        logging.info(f"Current time: {now}\n\n")
        
        # Start the bitcoin price pinger loop
        from utils.helpers import monitor_btc_price
        # This is the chat PA test channel
        chat_id = -4788252476
        # Schedule the monitor_btc_price task
        asyncio.create_task(monitor_btc_price(application.bot, chat_id))        

    except Exception as e:
        logging.error(f"Error during setup: {e}")
        import traceback
        logging.error(traceback.format_exc())
        raise
    



def main():
    logging.info("Entering main function")

    try:
        token = get_bot_token()
        if token is None:
            raise ValueError("No TELEGRAM_API_KEY found in environment variables")

        # Log if running locally or hosted
        logging.info("Using *local database* & *dev bot* (@TestManon_bot)" if local_flag else "Using *hosted database* & *prod bot* (@Manon_PA_bot)\n")
        
        # Create the bot application with ApplicationBuilder
        application = ApplicationBuilder().token(token).post_init(setup).build()

        # Set the global bot instance
        global global_bot
        global_bot = application.bot
        if not global_bot:
            raise ValueError("Failed to initialize bot")

        # Register handlers
        register_handlers(application)

        # Start the bot
        logging.info("... Starting run_polling")
        application.run_polling()
        logging.warning("Exiting run_polling ...\n")

    except Exception as e:
        logging.error(f"Error in main function: {e}")
        logging.error(f"Error type: {type(e).__name__}")
        import traceback
        logging.error(traceback.format_exc())
if __name__ == '__main__':
    # Connect to the PostgreSQL database
    conn = get_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT 1')
        logging.info("Database connection successful")
    except Exception as e:
        logging.error(f"🚨 Database connection error: {e}")
        if conn:
            conn.rollback()  # Roll back the current transaction, if any
    main()