import io, sys, os, logging, asyncio
from logging.handlers import RotatingFileHandler
from telegram import ChatMember
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, CallbackQueryHandler, PollHandler, ExtBot
from datetime import datetime, timezone
from utils.helpers import BERLIN_TZ, PA, monitor_btc_price
from utils.db import setup_database, Database
from utils.scheduler import send_morning_message, scheduler, AsyncIOScheduler, CronTrigger, DateTrigger, IntervalTrigger, send_evening_message, evening_message_hours, evening_message_minutes

print(f"... STARTING ... {PA}  \n\n")

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

logging = configure_logging()

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
async def reset_things_on_startup():
    logging.info(f"🕳️ Reset ... Nothing Yet (placeholder)")


# Set up the database and environment
async def initialize_environment():
    try:
        # Initialize database tables
        await setup_database()
        await reset_things_on_startup()
        logging.info("Environment initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing environment: {e}")
        raise
    

# Retrieve the bot token based on the environment
def get_bot_token() -> str:
    token = os.getenv('LOCAL_TELEGRAM_API_KEY' if local_flag else 'TELEGRAM_API_KEY')
    if not token:
        raise ValueError("Telegram API key is missing!")
    return token.strip()

# Register bot commands and handlers
def register_handlers(application):
    from modules.commands import (
    start_command, help_command, stats_command, filosofie_command, btc_command, 
    bitcoin_command, smarter_command, translate_command, profile_command, overdue_command,
    stopwatch_command, tea_command, dice_command, today_command, twenty_four_hours_command,
    tomorrow_command
    )
    application.add_handler(CommandHandler(["start", "begroeting", "begin"], start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler(["filosofie", "philosophy"], filosofie_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler(["stopwatch", "timer"], stopwatch_command))
    application.add_handler(CommandHandler(["tea"], tea_command))
    application.add_handler(CommandHandler(["dice", "die"], dice_command))
    application.add_handler(CommandHandler(["today", "vandaag"], today_command))
    application.add_handler(CommandHandler(["24", "24hs"], twenty_four_hours_command))
    application.add_handler(CommandHandler(["overdue", "expired"], overdue_command))
    application.add_handler(CommandHandler(["tomorrow", "morgen"], tomorrow_command))
    
    # /btc /bitcoin command handler
    application.add_handler(CommandHandler("btc", btc_command))
    application.add_handler(CommandHandler("bitcoin", bitcoin_command))
    
    application.add_handler(CommandHandler("smarter", smarter_command))
    application.add_handler(CommandHandler("translate", translate_command))
    
    from utils.listener import analyze_any_message, print_edit  
    # For any message starting with a digit or colon
    application.add_handler(MessageHandler(filters.Regex(r'^[\d:]'), stopwatch_command))
    # Bind the message analysis to any non-command text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_any_message))
    # Handler for edited messages
    application.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE & filters.TEXT & ~filters.COMMAND, print_edit))
    
    # Buttons
    from utils.helpers import delete_message
    application.add_handler(CallbackQueryHandler(delete_message, pattern=r"delete_message"))
    
    from modules.goals import handle_proposal_change_click, accept_goal_proposal, reject_goal_proposal, report_goal_progress
    application.add_handler(CallbackQueryHandler(
        handle_proposal_change_click,
        pattern=r"^(goal_value_up|goal_value_down|penalty_up|penalty_down)_(\d+)$"
        ))
    application.add_handler(CallbackQueryHandler(accept_goal_proposal, pattern=r"^accept_(\d+)$"))
    application.add_handler(CallbackQueryHandler(reject_goal_proposal, pattern=r"^reject_(\d+)$"))
    application.add_handler(CallbackQueryHandler(report_goal_progress, pattern=r"^(finished|failed)_(\d+)$"))
    application.add_handler(CallbackQueryHandler(report_goal_progress, pattern=r"^postpone_(\d+)_(today|tomorrow)$"))




    
async def setup(application):
    try:
        logging.info("Running setup tasks...")
        now = datetime.now(tz=BERLIN_TZ)        

        logging.info(f"Current time: {now}\n")
        
        # Initialize the database
        await Database.initialize()
        
        logging.info("Database initialization completed.")

        scheduler.add_job(send_morning_message, CronTrigger(hour=6, minute=6), args=[application.bot])
        scheduler.add_job(send_evening_message, CronTrigger(hour=evening_message_hours, minute=evening_message_minutes), args=[application.bot])
        scheduler.start()
        logging.info("Scheduler started successfully")
        

        # Initialize database and reset necessary data
        await initialize_environment()
        
        # Start the bitcoin price monitor
        chat_id = -4788252476  # PA test channel
        asyncio.create_task(monitor_btc_price(application.bot, chat_id))
        
        logging.info("Setup completed successfully")

    except Exception as e:
        logging.error(f"Error during setup: {e}")
        import traceback
        logging.error(traceback.format_exc())
        raise
    

def main():
    logging.info("Entering main function")

    try:
        # Create and get the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        token = get_bot_token()
        if token is None:
            raise ValueError("No TELEGRAM_API_KEY found in environment variables")

        # Log if running locally or hosted
        logging.info("Using *dev bot* (@TestManon_bot)" if local_flag else "Using & *prod bot* (@Manon_PA_bot)\n")
        
        # Create the bot application with ApplicationBuilder
        application = ApplicationBuilder().token(token).post_init(setup).build()

        # Set the global bot instance
        global global_bot
        global_bot = application.bot
        if not global_bot:
            raise ValueError("Failed to initialize bot")

        # Register handlers
        register_handlers(application)

        logging.info("... Starting run_polling")

        # Start the bot
        application.run_polling()
        logging.warning("*** *** *** Exiting run_polling ...")
        
    except Exception as e:
        logging.error(f"Error in main function: {e}")
        logging.error(f"Error type: {type(e).__name__}")
        import traceback
        logging.error(traceback.format_exc())
    finally:
        # Clean up the database connection pool
        try:
            loop.run_until_complete(Database.close())
        except Exception as e:
            logging.error(f"Error closing database: {e}")
        finally:
            loop.close()
        logging.info("Database connection closed\n*** *** *** *** *** *** <3")

if __name__ == '__main__':
    main()
    

