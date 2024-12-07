from telegram import Update, ChatMember, Bot
from telegram.ext import CallbackContext, ExtBot
from telegram.error import TelegramError
from typing import Union
from datetime import datetime, time, timedelta, timezone
import os, psycopg2, pytz, logging, requests, asyncio, re
from openai import OpenAI
from typing import Union
from zoneinfo import ZoneInfo

# Define the Berlin timezone
BERLIN_TZ = ZoneInfo("Europe/Berlin")


# Only load dotenv if running locally (not on Heroku)
if not os.getenv('HEROKU_ENV'):
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except ImportError:
        pass  # In case dotenv isn't installed, ignore this when running locally

# Flag to indicate if running locally
LOCAL_FLAG = not os.getenv('HEROKU_ENV', False)

# Get OpenAI API key from environment variable
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found! Ensure it's set in the environment.")

client = OpenAI(api_key=OPENAI_API_KEY)


def get_database_connection():
    # Use DATABASE_URL if available (Heroku), otherwise fallback to LOCAL_DB_URL
    DATABASE_URL = os.getenv('DATABASE_URL', os.getenv('LOCAL_DB_URL'))

    if not DATABASE_URL:
        raise ValueError("Database URL not found! Ensure 'DATABASE_URL' or 'LOCAL_DB_URL' is set in the environment.")

    # Connect to the PostgreSQL database
    if os.getenv('HEROKU_ENV'):  # Running on Heroku
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    else:  # Running locally
        conn = psycopg2.connect(DATABASE_URL)  # For local development, no SSL required

    return conn



async def check_chat_owner(update: Update, context):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Get chat administrators
    admins = await context.bot.get_chat_administrators(chat_id)
    
    # Check if the user is the owner (creator)
    for admin in admins:
        if admin.user.id == user_id and admin.status == 'creator':
            return True
    return False


# Security check: am I in the chat where the bot is used?
async def is_ben_in_chat(update, context):
    USER_ID = 1875436366
    chat_id = update.effective_chat.id
    try:
        # Get information about your status in the chat
        member = await context.bot.get_chat_member(chat_id, USER_ID)
        # Check if you're a member, administrator, or have any active role in the chat
        if member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Error checking chat member: {e}")
        return False
    

# Private message to Ben (test once then delete)
async def notify_ben(update,context):
        USER_ID = 1875436366
        first_name = update.effective_user.first_name
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        message = update.message.text
        notification_message = f"You've got mail ✉️🧙‍♂️\n\nUser: {first_name}, {user_id}\nChat: {chat_id}\nMessage:\n{message}"
        logging.error(f"! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! \n\n\n\nUnauthorized Access Detected\n\n\n\n! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !\nUser: {first_name}, {user_id}\nChat: {chat_id}\nMessage: {message}")
        await context.bot.send_message(chat_id=USER_ID, text=notification_message)
        

async def get_first_name(context_or_bot: Union[Bot, ExtBot, CallbackContext], user_id: int) -> str:
    global global_bot
    try:
        # Check if context_or_bot is a CallbackContext
        if isinstance(context_or_bot, CallbackContext):
            bot = context_or_bot.bot
        # If it's a Bot or ExtBot instance, use it directly
        elif isinstance(context_or_bot, (Bot, ExtBot)):
            bot = context_or_bot
        else:
            # Fallback to global bot if available
            if global_bot is None:
                raise ValueError("No bot instance available")
            bot = global_bot

        # Now, 'bot' is guaranteed to be a Bot or ExtBot instance
        chat_member = await bot.get_chat_member(user_id, user_id)
        return chat_member.user.first_name

    except Exception as e:
        logging.error(f"Error fetching user details for user_id {user_id}: {e}")
        return "Lodewijk 🚨🐛"
    

async def get_btc_price() -> tuple[str, str, float]:
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,eur"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses
        data = response.json()
        usd_price = float(data["bitcoin"]["usd"])  # Convert to float for formatting
        eur_price = float(data["bitcoin"]["eur"])  # Convert to float for formatting
        
        mycelium_balance = 0.01614903
        mycelium_euros = round(eur_price * mycelium_balance, 2)
        
        # Format the prices with a comma as the thousands separator
        usd_price_formatted = f"{usd_price:,.0f}"
        mycelium_euros_formatted = f"{mycelium_euros:,.0f}"
        
        # Return two different outputs
        simple_message = f"${usd_price_formatted}"
        detailed_message = f"1₿ = ${usd_price_formatted}\n🍄 = €{mycelium_euros_formatted}"
        raw_float_price = usd_price
        
        return simple_message, detailed_message, raw_float_price
    except requests.RequestException as e:
        return f"Error fetching Bitcoin price: {e}"
    

# Function to check Bitcoin price every hour and send a message if it exceeds the threshold
async def monitor_btc_price(bot: Bot, chat_id: int):
    lower_threshold = 90000
    upper_threshold = 111111
    upper_threshold_alerted = False
    lower_threshold_alerted = False
    while True:
        _, _, price = await get_btc_price()
        if price is not None:
            print(f"Bitcoin price: ${price:,.2f}")  # Log the price
            if price > upper_threshold and not upper_threshold_alerted:
                message = f"*🚀 Bitcoin price alert!*\n1₿ is now ${price:,.2f} USD, exceeding the threshold of ${upper_threshold:,.2f}"
                await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                upper_threshold_alerted = True
                lower_threshold_alerted = False  # Reset lower threshold flag

            elif price < lower_threshold and not lower_threshold_alerted:
                message = f"*📉 Bitcoin price alert!*\n1₿ is now ${price:,.2f} USD, dropping below the threshold of ${lower_threshold:,.2f}"
                await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                lower_threshold_alerted = True
                upper_threshold_alerted = False  # Reset upper threshold flag
                
        await asyncio.sleep(600)  # Wait for 10 minutes before checking again
        

# Randomly pick a message
def get_random_philosophical_message(normal_only = False, prize_only = False):
    normal_messages = [
            "Hätte hätte, Fahrradkette",  # Message 1
            "千里之行，始于足下",        
            "Ask, believe, receive ✨",   
            "A few words on looking for things. When you go looking for something specific, "
            "your chances of finding it are very bad. Because, of all the things in the world, "
            "you're only looking for one of them. When you go looking for anything at all, "
            "your chances of finding it are very good. Because, of all the things in the world, "
            "you're sure to find some of them",
            "Je kan het best, de tijd gaat met je mee",
            "If the human brain were so simple that we could understand it, we would be so simple that we couldn't",       
            "Ik hoop maar dat er roze koeken zijn",  
            "Hoge loofbomen, dik in het blad, overhuiven de weg",   
            "It is easy to find a logical and virtuous reason for not doing what you don't want to do",  
            "Our actions are like ships which we may watch set out to sea, and not know when or with what cargo they will return to port",
            "A sufficiently intimate understanding of mistakes is indistinguishable from mastery",
            "He who does not obey himself will be commanded",
            "Elke dag is er wel iets waarvan je zegt: als ik die taak nou eens zou afronden, "  
            "dan zou m'n dag meteen een succes zijn. Maar ik heb er geen zin in. Weet je wat, ik stel het "
            "me als doel bij Taeke, en dan ben ik misschien wat gemotiveerder om het te doen xx 🙃",
            "All evils are due to a lack of Telegram bots",
            "Art should disturb the comfortable, and comfort the disturbed",
            "Begin de dag met tequila",
            "Don't wait. The time will never be just right",
            "If we all did the things we are capable of doing, we would literally astound ourselves",
            "There's power in looking silly and not caring that you do",                                        # Message 20
            "...",
            "Een goed begin is de halve dwerg",
            "En ik lach in mezelf want de sletten ik breng",
            "Bij nader inzien altijd achteraf",
            "Sometimes we live no particular way but our own",                                                  # Message 25
            "If it is to be said, so it be, so it is",                                                          # Message 26
            "Te laat, noch te vroeg, arriveert (n)ooit de Takentovenaar"                                        # Message 27
        ]
    
    prize_messages = [
        {
            "message": "Als je muisjes op je mouwen knoeit, katten ze niet",
            "prize": "raad het Nederlandse spreekwoord waarvan dit is... afgeleid..?, en win 2 punten"
        },
        {
            "message": "Ik schaam me een beetje dat ik niet met een turkencracker overweg kan",
            "prize": "raad het keukengerei dat hier bedoeld wordt, en win 1 punt"
        },
        {
            "message": "De oom uit de eik batsen",
            "prize": "raad het Nederlandse spreekwoord waarvan dit nogal afleidt, en win 1 punt"
        },
        {
            "message": "Je niet laten prikken door dat stekelige mythische wezen, maar andersom!",
            "prize": "raad het Nederlandse spreekwoord dat hier zo'n beetje is omgedraaid, en win 1 punt"
        },
        {
            "message": "De kastanjes in het vuur flikkeren",                                                                            # Message 5
            "prize": "raad het Nederlandse spreekwoord waarvan dit is afgeleid, en verlies 1 punt"
        },
        {
            "message": "Inwoners uit deze gemeente zijn het staan zat",
            "prize": "raad de verborgen gemeente, en win 2 punten"
        },
        {
            "message": "Welke rij planten zit er in dit huidvraagje verscholen?",                                                       # Message 7
            "prize": "raad de plantenrij, en win 1 punt"
        },
        {
            "message": "De Total Expense Ratio, ING... naar! Daenerys zet in.",                                                         # Message 8
            "prize": "raad het Nederlandse spreekwoord waarvan dit toch echt enigszins is afgeleid, en win 2 punten"
        }
    ]
    
    # New message to append to each prize submessage
    additional_message = "\n(uitreiking door Ben)"

    # Loop through each dictionary in the list and modify the 'prize' value
    for prize_message in prize_messages:
        prize_message["prize"] += additional_message
    
    # Combine all messages for random selection
    all_messages = [
        *normal_messages,
        *[f"{msg['message']}\n\n{msg['prize']}" for msg in prize_messages]
    ]

    # Combine prize messages into a single list of formatted strings
    formatted_prize_messages = [
        f"{msg['message']}\n\n{msg['prize']}" for msg in prize_messages
    ]
    
    selected = random.choice(all_messages)
    
    if normal_only:
        selected = random.choice(normal_messages)
        
    if prize_only:
        selected = random.choice(formatted_prize_messages)

    # For prize messages, only wrap the philosophical part in italics
    for prize_msg in prize_messages:
        full_prize_msg = f"{prize_msg['message']}\n\n{prize_msg['prize']}"
        if selected == full_prize_msg:
            return f"✨_{prize_msg['message']}_✨\n\n{prize_msg['prize']}"
    
    # If it's a normal message, wrap the entire thing
    return f"✨_{selected}_✨"



def escape_markdown_v2(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))


async def check_chat_owner(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    try:
        # Get chat administrators
        admins = await context.bot.get_chat_administrators(chat_id)
    
        # Check if the user is the owner (creator)
        for admin in admins:
            if admin.user.id == user_id and admin.status == 'creator':
                return True
        return False
    except TelegramError as e:
        print(f"Error fetching chat admins, returned False as a fallback (retry if Ben =)): {e}")
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(
                "🚫 Ik kon ffkes niet checken of je de eigenaar van deze chat bent. Probeer het later opnieuw 🧙‍♂️"
            )
        else:
            print("No message object available to send a reply.")
        return False