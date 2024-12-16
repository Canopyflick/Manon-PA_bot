from utils.helpers import emoji_stopwatch, get_random_philosophical_message, escape_markdown_v2, check_chat_owner, PA, add_delete_button, delete_message
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
import asyncio, random, re, logging
from utils.helpers import get_btc_price
from telegram.ext import ContextTypes, CallbackContext
from LLMs.orchestration import process_other_language, check_language, handle_goal_classification, start_initial_classification
from utils.db import get_first_name, register_user
from utils.listener import roll_dice
from utils.scheduler import send_goals_today, fetch_overdue_goals, fetch_upcoming_goals


# Asynchronous command functions
async def start_command(update, context):
    await update.message.reply_text(f"Hoi! 👋{PA}‍\n\nMy name is Manon, maybe (so call me).")
    try:
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        await register_user(context, user_id, chat_id)
    except Exception as e:
        logging.error(f"Error checking user records in start_command: {e}")


async def stopwatch_command(update, context):
    if context.args:  # Input from a command like /stopwatch 10
        arg = context.args[0]
    else:  # Input from a message like "10:30"
        arg = update.message.text.strip()    
        
    # Check if input is in minute:seconds format
    if re.match(r'^\d+:\d{1,2}$', arg):  # Matches "minute:seconds" format
        try:
            minutes, seconds = map(int, arg.split(':'))
            duration = minutes * 60 + seconds
            await emoji_stopwatch(update, context, duration=duration)
            return
        except ValueError:
            await update.message.reply_text(f"Invalid input format {PA}")
            return
        
    # Check if input is in :seconds format               
    elif re.match(r'^:\d{1,2}$', arg):
        try:
            seconds = int(arg[1:])  # Extract seconds after the colon
            await emoji_stopwatch(update, context, duration=seconds)
            return
        except ValueError:
            await update.message.reply_text("Invalid seconds format. Use :seconds.")
            return
        
    # Check if input is a single number (minutes only)
    elif arg.isdigit():
        minutes = int(arg)
        duration = minutes * 60
        await emoji_stopwatch(update, context, duration=duration)
        return
        
    else:  # Invalid input
        await update.message.reply_text(f"Please provide time as minutes or minutes:seconds {PA}")
        await start_initial_classification(update, context)
        return


async def help_command(update, context):
    help_message = (
        f'*Some options* {PA}\n\n'
        '*Generic* \n'
        '👋 /start - Hi!\n'
        '⏱️ <minutes>:<seconds> - Timer\n'
        '🉑 /translate - 肏你妈\n'
        '🎲 /dice - 1-6\n'
        '🗒️🚧 /profile - What I know about you\n'
        '💭🚧 /wow - Get inspired\n\n'
        '*Info about your goals*\n'
        f'| /today | /tomorrow | /24 | /overdue |\n\n'
        '*Trigger words*\n'
        '| gm | gn | emoji | pomodoro | !test | '
    )
    chat_type = update.effective_chat.type
    if chat_type == 'private':
        help_message += "\n\nHoi trouwens... 👋🧙‍♂️ Stiekem ben ik een beetje verlegen. Praat met me in een chat waar Ben bij zit, pas dan voel ik me op mijn gemak.\n\n\nPS: je kunt hier wel allerhande boodschappen ter feedback achterlaten, dan geef ik die door aan Ben (#privacy)."
        await update.message.reply_text(help_message, parse_mode="Markdown")
    else:
        help_message += "\n\n🚧_...deze werken nog niet/nauwelijks_"
        await update.message.reply_text(help_message, parse_mode="Markdown")
    

async def tea_command(update, context):
    await emoji_stopwatch(update, context, mode="tea_short")

async def profile_command(update, context):
    await update.message.reply_text("will show all the user-specific settings, like long term goals, preferences, constitution ... + edit-button")
    

async def stats_command(update, context, ready=False):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    first_name = await get_first_name(context, user_id, chat_id)
    # Unpack the retrieved stats
    if ready:
        # Fetch all stats data from the database
        stats = await get_user_stats(update.effective_user.id)
        goals_finished_week = stats["goals_finished_week"]
        goals_failed_week = stats["goals_failed_week"]
        goals_pending_week = stats["goals_pending_week"]
        points_remaining = stats["points_remaining"]
        penalties_remaining = stats["penalties_remaining"]
        all_time_success = stats["all_time_success"]
        monthly_success = stats["monthly_success"]
    demographics = ["listeners", f"people named {first_name}", "go-getters", "real humans", "people", "people", "chosen subjects", "things-with-a-hearbeat", "beings", "selected participants", "persons", "white young males", "mankind", "the populace", "the disenfranchized", "sapient specimen", "bipeds", "people-pleasers", "saviors", "heroes", "members", "Premium members", "earth dwellers", "narcissists", "cuties", "handsome motherfuckers", "Goal Gangsters", "good guys", "bad bitches", "OG VIP Hustlers", "readers", "lust objects"]
    demographic = random.choice(demographics)
    second_demographic = random.choice(demographics)
    percents = ["5%", "0.0069%", "7%", "83%", "20th percentile", "1%", "0.0420%", "111%", "6.2%", "0.12%", "half", "cohort"]
    percent = random.choice(percents)
    regions = [" globally", " worldwide", " in Wassenaar", " locally", " in the nation", ", hypothetically speaking", ", maybe!", " in the Netherlands", " (or maybe not)", " in Europe", " today", " this lunar year", " tomorrow", " for a while", " (... for now, anyways)", " this side of the Atlantic", " in the observable universe"]
    region = random.choice(regions)
    adverbs = [" quite possibly ", " definitely ", " (it just so happens) ", ", presumably, ", ", without a doubt, ", ", so help us God, ", " (maybe) ", ", fugaciously, ", ", reconditely, ", " hitherto ", " (polyamorously) "]
    adverb = " "
    special_handcrafted_nonesense = ["You're in the top 1%!!!", "What a champ..!", "That's amazing!", "You could do better...", "You're in Enkhuizen!", "You're off-the-charts!", "You're well-positioned!", "You could do worse!", "You are unique!", "You are loved!", "You are on earth!", "The kids are not alright.", "You're alright.", "You're outperforming!", "You're better than France!", "You're semi-succesful!"]
    if random.random() > 0.97:
        nonsense_message = random.choice(special_handcrafted_nonesense)
    else:
        if random.random() > 0.8:
            adverb = random.choice(adverbs)
        verbs = ["might be ", "have the potential to one day end up ", "will soon find yourself ", "are on course to being ", "deserve to be ", "should be ", "could've been ", "haven't been ", "stand a good chance of being ", "are exactly ", "are statistically unlikely to be ", f"are (much unlike other {second_demographic}) ", f"are, quite unlike other {second_demographic}, ", f"are (at least compared to other {second_demographic}) ", "are destined to be "]
        verb = "are"
        if random.random() > 0.8:
            verb = random.choice(verbs)
        top_or_bottom = "top"
        if random.random() > 0.8:
            top_or_bottom = "bottom"
        you_or_them = "You"
        if random.random() > 0.9:
            verb = ""     # Because many of these don't work with plural
            if random.random() > 0.6:
                you_or_them = "Your enemies are"
            else:
                you_or_them = "Your friends are"
        in_the = " in the "
        if random.random() > 0.94:
            if random.random() > 0.8:
                in_the = " better than the "
            else:
                in_the = " worse than the "
        closing_remark = ""
        if random.random() > 0.96:
            closing_remarks = ["Whoa...", "Just think of the implications!!", "That's insane!", "Not bad.", "... profit?!??", "Huh, could be worse!", "Can you believe it?", "That's quite something.", "Be grateful for that."]
            closing_remark = random.choice(closing_remarks)
        nonsense_messages = [f"{you_or_them}{adverb}{verb}{in_the}{top_or_bottom} {percent} of {demographic}{region}! {closing_remark}", "", "", "", "", ""]     # ~5 million unique options
        nonsense_message = nonsense_messages[0]
    
    nonsense_message = nonsense_message.replace("  ", " ")
    logging.warning(f"Nonsense message >>> {nonsense_message}")
    # nonsense_message = random.choice(nonsense_messages)

    # Construct the message
    stats_message = (
        f"👤 *{first_name}*\n"
        f"✅ This week: [goals_finished_week] done\n"
        f"❌ [goals_failed_week] failed\n"
        f"🔄 [goals_pending_week] pending\n"
        f"🎯  [points_remaining] | ⚠️ [penalties_remaining] remaining on line\n"
        f"🔥 All-time: [all_time_success:.1f]%\n"
        f"📅 Monthly: [monthly_success:.1f]%\n\n"
        f"_{nonsense_message}_"
    )
    
    # Send the message
    await update.message.reply_text(stats_message, parse_mode="Markdown")
    

async def profile_command(update, context):
    await update.message.reply_text("will show all the user-specific settings, like long term goals, preferences, constitution ... + edit-button")
    
    
async def dice_command(update, context):
    if context.args:  # Input from a command like /stopwatch 10
        arg = context.args[0]
        if arg.isdigit() and 1 <= int(arg) <= 6:
            await roll_dice(update, context, user_guess=arg)
            logging.info(f"Dice roll {arg}")
            return
    else:
        await roll_dice(update, context, user_guess=None)
        logging.info("Dice roll numberless")
    

# Function to handle the trashbin button click (delete the message)
async def handle_trashbin_click(update, context):
    query = update.callback_query

    # Double-check if the callback data is 'delete_message'
    if query.data == "delete_message":
        # Delete the message that contains the button
        await query.message.delete()

    # Acknowledge the callback to remove the 'loading' animation
    await query.answer()
            

# fix later huhauhue
async def process_emojis(escaped_emoji_string, escaped_pending_emojis):
    # Extract the existing emojis inside the brackets from the escaped_emoji_string
    # Pattern to match content between \(...\)
    inner_emojis = ''
    if escaped_emoji_string:
        # Extract the existing emojis inside the brackets from the escaped_emoji_string
        # Pattern to match content between \(...\)
        pattern = r"\\\((.*?)\\\)"
        match = re.search(pattern, escaped_emoji_string)
        inner_emojis = match.group(1) if match else ''
    

    # Extract all 🤝 emojis from the pending emoji string
    pending_links = ''.join([char for char in escaped_pending_emojis if char == '🤝'])
    combined_inner_emojis = inner_emojis + pending_links

    # Create the new string with the updated emojis inside the brackets
    new_emoji_string = f"({combined_inner_emojis})"
    escaped_combined_string = escape_markdown_v2(new_emoji_string)

    return escaped_combined_string

            



async def wow_command(update, context):
    chat_type = update.effective_chat.type
    # Check if the chat is private or group/supergroup
    if chat_type == 'private':
        await update.message.reply_text("Hihi hoi. Ik werk eigenlijk liever in een groepssetting... 🧙‍♂️")
        await asyncio.sleep(3)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(1)
        await update.message.reply_text("... maarrr, vooruit dan maar, een stukje inspiratie kan ik je niet ontzeggen ...")
        philosophical_message = get_random_philosophical_message(normal_only=True)
        await asyncio.sleep(2)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(4)
        await asyncio.sleep(1)
        await update.message.reply_text(f'_{philosophical_message}_', parse_mode="Markdown")
        return
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        goal_text = fetch_goal_text(update)
        if goal_text != '' and goal_text != None:
                messages = await prepare_openai_messages(update, user_message="onzichtbaar", message_type = 'grandpa quote', goal_text=goal_text)
                grandpa_quote = await send_openai_request(messages, "gpt-4o")
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
                random_delay = random.uniform(2, 8)
                await asyncio.sleep(random_delay)
                await update.message.reply_text(f"Mijn grootvader zei altijd:\n✨_{grandpa_quote}_ 🧙‍♂️✨", parse_mode="Markdown")
        else:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            random_delay = random.uniform(2, 5)
            await asyncio.sleep(random_delay)
            philosophical_message = get_random_philosophical_message(normal_only=True)
            await update.message.reply_text(f'_{philosophical_message}_', parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in filosofie_command: {e}")



async def btc_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    simple_message, _, _, _ = await get_btc_price()
    await update.message.reply_text(simple_message)
    

async def bitcoin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, detailed_message, _, _ = await get_btc_price()
    await update.message.reply_text(detailed_message)


async def smarter_command(update: Update, context: CallbackContext):
    logging.warning("triggered /smarter")
    await handle_goal_classification(update, context, smarter=True)
    

async def translate_command(update: Update, context: CallbackContext):
    logging.warning("triggered /translate")
    if not context.args:    # Check if NO argument was provided
        await update.message.reply_text(f"Provide some source text to translate {PA}")
        return
    else:
        source_text = " ".join(context.args)
        language = await check_language(update, context, source_text)
        await process_other_language(update, context, source_text, language=language, translate_command=True)
        

async def today_command(update, context):
    try:
        chat_id = update.message.chat_id
        user_id = update.effective_user.id
        
        # Send upcoming goals
        upcoming_goals_message, _ = await send_goals_today(update, context, chat_id, user_id, timeframe=7)
        if upcoming_goals_message:
            await add_delete_button(update, context, upcoming_goals_message.message_id, delay=4)
            asyncio.create_task(delete_message(update, context, upcoming_goals_message.message_id, 1200))
        
        # Fetch overdue goals
        overdue_goals_result = await fetch_overdue_goals(chat_id, user_id, timeframe="overdue_today")
        if overdue_goals_result[0]:
            overdue_today = overdue_goals_result[0]
            for goal in overdue_today:
                if not isinstance(goal, dict) or "text" not in goal or "buttons" not in goal:
                    continue
                goal_report_prompt = await context.bot.send_message(
                    chat_id=chat_id,
                    text=goal["text"],
                    reply_markup=goal["buttons"],
                    parse_mode="Markdown"
                )
                asyncio.create_task(delete_message(update, context, goal_report_prompt.message_id, 1200))
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"_You're all caught up today, nothing overdue_ {PA}",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logging.error(f"Error in today_command: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="An error occurred while processing your request. Please try again later.",
            parse_mode="Markdown"
        )


async def twenty_four_hours_command(update, context):
    chat_id = update.message.chat_id
    user_id = update.effective_user.id
    await send_goals_today(update, context, chat_id, user_id, timeframe="24hs")
    

async def overdue_command(update, context):
    try:
        chat_id = update.message.chat_id
        user_id = update.effective_user.id
        
        # Fetch overdue goals
        overdue_goals_result = await fetch_overdue_goals(chat_id, user_id, timeframe="overdue")
        if overdue_goals_result[0]:
            overdue_today = overdue_goals_result[0]
            for goal in overdue_today:
                if not isinstance(goal, dict) or "text" not in goal or "buttons" not in goal:
                    continue
                goal_report_prompt = await context.bot.send_message(
                    chat_id=chat_id,
                    text=goal["text"],
                    reply_markup=goal["buttons"],
                    parse_mode="Markdown"
                )
                asyncio.create_task(delete_message(update, context, goal_report_prompt.message_id, 1200))
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="0 overdue goals ✨",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logging.error(f"Error in today_command: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="An error occurred while processing your request in overdue_command()",
            parse_mode="Markdown"
        )
        
async def tomorrow_command(update, context):
    try:
        chat_id = update.message.chat_id
        user_id = update.effective_user.id
        
        # Send upcoming goals
        result = await fetch_upcoming_goals(chat_id, user_id, timeframe="tomorrow")
        if result:
            message_text = result[0]
            upcoming_goals_message = await context.bot.send_message(chat_id, text=message_text, parse_mode="Markdown")
            await add_delete_button(update, context, upcoming_goals_message.message_id, delay=4)
            asyncio.create_task(delete_message(update, context, upcoming_goals_message.message_id, 1200))
            
    except Exception as e:
        logging.error(f"Error in today_command: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="An error occurred while processing your request. Please try again later.",
            parse_mode="Markdown"
        )