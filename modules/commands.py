from utils.helpers import emoji_stopwatch, get_random_philosophical_message, escape_markdown_v2, check_chat_owner, PA, add_delete_button, delete_message, safe_set_reaction
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
import asyncio, random, re, logging
from utils.helpers import get_btc_price
from telegram.ext import ContextTypes, CallbackContext
from LLMs.orchestration import diary_header, process_other_language, check_language, handle_goal_classification, start_initial_classification
from utils.db import get_first_name, register_user, fetch_user_stats
from utils.listener import roll_dice
from utils.scheduler import send_goals_today, fetch_overdue_goals, fetch_upcoming_goals
from modules.stats_manager import StatsManager


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
        '| gm | gn | emoji | pomodoro | koffie | !test | usercontext | clearcontext | resolve | logs<number\\_of\\_lines> | errorlogs | transparant\\_on | transparant\\_off | seintjenatuurlijk |'
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
    

async def stats_command(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    first_name = await get_first_name(context, user_id, chat_id)

    # Get comprehensive stats
    stats = await StatsManager.get_comprehensive_stats(user_id, chat_id)
    
    def get_trend_arrow(current, baseline):
        """Returns emoji arrow based on comparison with weekly baseline"""
        if current == baseline:
            return "→"
        # Invert logic for penalties (lower is better)
        if metric_name == 'Penalties/Day':
            return "🟢↑" if current < baseline else "🔴↓"
        return "🟢↑" if current > baseline else "🔴↓"

    def format_metric_line(metric_name: str, metric_values: dict, periods: list) -> str:
        """Formats a single metric line with fixed-width columns"""
        values = []
        for period in periods:
            value = metric_values.get(period, 0) or 0
            trend = get_trend_arrow(value, metric_values['week'])
            values.append(f"{value:7.1f}{trend}")
        return f"{metric_name:<14} {' | '.join(values)}"

    # Get both today's and total stats
    today_stats = await StatsManager.get_today_stats(user_id, chat_id)
    total_stats = await StatsManager.get_total_stats(user_id, chat_id)

    # Calculate today's completion rate
    today_completed = today_stats.get('completed_goals', 0)
    today_failed = today_stats.get('failed_goals', 0)
    today_total = today_completed + today_failed
    today_completion_rate = (today_completed / today_total * 100) if today_total > 0 else 0

    # Calculate all-time completion rate
    total_completed = total_stats['total_completed']
    total_failed = total_stats['total_failed']
    total_all = total_completed + total_failed
    total_completion_rate = (total_completed / total_all * 100) if total_all > 0 else 0

    # Combined metrics dictionary
    combined_metrics = {
        'Points': {
            'today': today_stats.get('points_delta', 0),
            'total': total_stats['total_score']
        },
        'Pending': {
            'today': today_stats.get('pending_goals', 0),
            'total': total_stats.get('total_pending', 0)
        },
        'Completed': {
            'today': today_completed,
            'total': total_completed
        },
        'Failed': {
            'today': today_failed,
            'total': total_failed
        },
        'New Goals': {
            'today': today_stats.get('new_goals_set', 0),
            'total': total_stats.get('total_goals_set', 0)
        },
        'Success Rate': {
            'today': today_completion_rate,
            'total': total_completion_rate
        }
    }

    # Format message
    message_parts = [
        f"<b>Stats for {first_name}</b> 👤{PA}\n",
        "<b>📊 Today & Total</b>",
        "<pre>",
        "Metric          Today | All-time",
        "──────────────────────────────"
    ]

    # Add combined metrics
    for metric_name, values in combined_metrics.items():
        if metric_name == 'Success Rate':
            message_parts.append(
                f"{metric_name:<14} {values['today']:6.1f}% | {values['total']:6.1f}%"
            )
        else:
            message_parts.append(
                f"{metric_name:<14} {values['today']:7.1f} | {values['total']:7.1f}"
            )

    message_parts.extend(["</pre>"])

    # Trends section
    message_parts.extend([
        "<b>📈 Trends</b>",
        "<pre>",
        "Metric                7d | 30d",
        "──────────────────────────────"
    ])

    # Calculate daily averages for each period
    periods = ['week', 'month', 'quarter', 'year']
    days_in_period = {'week': 7, 'month': 30, 'quarter': 91, 'year': 365}

    metrics = {
        'Goals/Day': {
            period: stats[period].get('total_goals_set', 0) / days_in_period[period]
            for period in periods
        },
        'Points/Day': {
            period: stats[period].get('total_score_gained', 0) / days_in_period[period]
            for period in periods
        },
        'Penalties/Day': {
            period: stats[period].get('total_penalties', 0) / days_in_period[period]
            for period in periods
        },
        'Complete %': {
            period: stats[period].get('avg_completion_rate', 0)
            for period in periods
        }
    }

    # Add metrics for week/month
    for metric_name, metric_data in metrics.items():
        message_parts.append(format_metric_line(
            metric_name, 
            metric_data, 
            ['week', 'month']
        ))

    message_parts.extend([
        "",
        "                      91d | 365d",
        "──────────────────────────────"
    ])

    # Add metrics for quarter/year
    for metric_name, metric_data in metrics.items():
        message_parts.append(format_metric_line(
            metric_name, 
            metric_data, 
            ['quarter', 'year']
        ))
    
    message_parts.extend([
        "</pre>",
        f"\n<i>{await nonsense(update, context, first_name)}</i>"
    ])

    stats_message = await update.message.reply_text(
        "\n".join(message_parts),
        parse_mode="HTML"
    )
    await add_delete_button(update, context, stats_message.message_id)
    
    
async def nonsense(update, context, first_name):
    demographics = ["listeners", f"people named {first_name}", "go-getters", "real humans", "people", "people", "chosen subjects", "things-with-a-hearbeat", "beings", "selected participants", "persons", "white young males", "mankind", "the populace", "the disenfranchized", "sapient specimen", "bipeds", "people-pleasers", "saviors", "heroes", "members", "Premium members", "earth dwellers", "narcissists", "cuties", "handsome motherfuckers", "Goal Gangsters", "good guys", "bad bitches", "OG VIP Hustlers", "readers", "lust objects"]
    demographic = random.choice(demographics)
    second_demographic = random.choice(demographics)
    percents = ["5%", "0.0069%", "7%", "83%", "20th percentile", "1%", "0.0420%", "19%", "6.2%", "0.12%", "half", "cohort"]
    percent = random.choice(percents)
    regions = [" globally", " worldwide", " in Wassenaar", " locally", " in the nation", ", hypothetically speaking", ", maybe!", " in the Netherlands", " (or maybe not)", " in Europe", " today", " this lunar year", " tomorrow", " (... for now, anyways)", " this side of the Atlantic", " in the observable universe"]
    region = random.choice(regions)
    adverbs = [" quite possibly ", " definitely ", " (it just so happens) ", ", presumably, ", ", without a doubt, ", ", so help us God, ", " (maybe) ", ", fugaciously, ", ", reconditely, ", " hitherto ", " (polyamorously) "]
    adverb = " "
    special_handcrafted_nonesense = ["You're in the top 1%!!!", "What a champ..!", "That's amazing!", "You could do better...", "You're in Enkhuizen!", "You're off-the-charts!", "You're well-positioned!", "You could do worse!", "You are unique!", "You are loved!", "You are on earth!", "You're alright.", "You're outperforming!", "You're better than France!", "You're semi-succesful!", "You're overachieving!"]
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
        if random.random() > 0.94:
            closing_remarks = ["Whoa...", "Just think of the implications!!", "That's insane!", "Not bad.", "... profit?!??", "Huh... Could be worse!", "Can you believe it?", "That's quite something.", "Be grateful for that.", "That's incredible.", "Big if True."]
            closing_remark = random.choice(closing_remarks)
        nonsense_messages = [f"{you_or_them}{adverb}{verb}{in_the}{top_or_bottom} {percent} of {demographic}{region}! {closing_remark}", "", "", "", "", ""]     # ~5 million unique options
        nonsense_message = nonsense_messages[0]
        # nonsense_message = random.choice(nonsense_messages)
    nonsense_message = nonsense_message.replace("  ", " ")
    return nonsense_message
    

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
                text=f"_You're all caught up_ today, _nothing overdue_ {PA}",
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
        

async def diary_command(update, context):
    try:
        chat_id = update.effective_chat.id
        message_id = update.message.message_id
        preset_reaction = "💅"
        await diary_header(update, context)
        await safe_set_reaction(context.bot, chat_id=chat_id, message_id=message_id, reaction=preset_reaction)
            
    except Exception as e:
        logging.error(f"Error in diary_command: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="An error occurred while processing your request. Please try again later.",
            parse_mode="Markdown"
        )