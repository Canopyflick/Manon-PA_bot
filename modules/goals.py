from jinja2.utils import F
from utils.helpers import BERLIN_TZ, add_user_context_to_goals, PA
from utils.db import update_goal_data, complete_limbo_goal, adjust_penalty_or_goal_value, fetch_template_data_from_db, Database, validate_goal_constraints, update_user_data, fetch_goal_data
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging, re, asyncio
from datetime import datetime, timedelta
from collections.abc import Iterable
from jinja2 import Template



async def format_datetime_list(datetime_input):
    """
    Formats datetime inputs that can be None, a string, or a list of strings.
    
    Args:
        datetime_input (None, str, List[str]): Input datetime(s)
    
    Returns:
        Tuple[int, List[str]]: 
        - First element is the total count of datetime entries
        - Second element is a list of formatted datetime strings
    """
    # Handle None case
    logging.critical(f"Datetime input in formatting function = {datetime_input}")
    if datetime_input is None:
        return 0, []
    
    # Convert single string to list
    if isinstance(datetime_input, str):
        datetime_input = [datetime_input]
    
    # Ensure it's a list of strings
    if not isinstance(datetime_input, list):
        return 0, []
    
    # If 4 or fewer entries, show all
    if len(datetime_input) <= 4:
        try:
            return len(datetime_input), [
                f"- {datetime.fromisoformat(dt).strftime('%A, %d %B %Y, %H:%M')}"
                for dt in datetime_input
            ]
        except (ValueError, TypeError):
            return len(datetime_input), [f"- {dt}" for dt in datetime_input]
    
    # If 5 or more entries
    try:
        formatted_datetimes = [
            f"- {datetime.fromisoformat(datetime_input[0]).strftime('%A, %d %B %Y, %H:%M')}",
            f"- {datetime.fromisoformat(datetime_input[1]).strftime('%A, %d %B %Y, %H:%M')}",
            f"...and {len(datetime_input) - 3} more entr{'y' if len(datetime_input) - 3 == 1 else 'ies'} ...",
            f"- {datetime.fromisoformat(datetime_input[-1]).strftime('%A, %d %B %Y, %H:%M')}"
        ]
    except (ValueError, TypeError):
        formatted_datetimes = [
            f"- {datetime_input[0]}",
            f"- {datetime_input[1]}",
            f"...and {len(datetime_input) - 3} more entr{'y' if len(datetime_input) - 3 == 1 else 'ies'} ...",
            f"- {datetime_input[-1]}"
        ]
    
    return len(datetime_input), formatted_datetimes
    

async def send_goal_proposal(update, context, goal_id, adjust=False):
    try:
        message_text, keyboard = await draft_goal_proposal_message(update, context, goal_id, adjust)
        
        if adjust:
            await complete_limbo_goal(update, context, goal_id, initial_update=False)     # Storing the full goal in db (for the first time or upon adjustment)
        if not adjust: 
            await complete_limbo_goal(update, context, goal_id, initial_update=True)
        # Send message with buttons
        await update.message.reply_text(message_text, reply_markup=keyboard, parse_mode="Markdown")
    
    except Exception as e:
        await update.message.reply_text(f"Error in send_goal_proposal(): {e}")
        logging.error(f"Error in send_goal_proposal(): {e}")
    
        
TEMPLATE_TEXT = """{{ PA }}‍ *{{ recurrence_type | capitalize }} Goal Proposal*
✍️ {{ goal_description }}

📅 {{ "Deadline" if deadline_count == 1 else deadline_count ~ " Deadlines" }}:
{{ formatted_deadlines }}

⚡ Goal Value: {{ goal_value | round(1) }} {% if total_goal_value | default(None) is not none %}({{ total_goal_value | round(0) | int }} total){% endif %}
🌚 Potential Penalty: {{ penalty | round(1) }} {% if total_penalty | default(None) is not none %}({{ total_penalty | round(0) | int }} total){% endif %}
{% if (schedule_reminder | default(reminder_scheduled | default(False))) and reminder_count > 0 %}
\n⏰ {{ "Reminder" if reminder_count == 1 else reminder_count ~ " Reminders" }}:
{{ formatted_reminders }}
{% endif %}#_{{ ID }}_
"""

        
async def populate_goal_template(update, context, goal_id):
    try:
        goal_data = context.user_data["goals"].get(goal_id) # In case of an adjustment, goal_data should have already been fetched from db in prepare_goal_changes()

        # Log all keys and their values
        logging.info(f"Logging entire goal_data before populating template\n:")
        for key, value in goal_data.items():
            logging.info(f"Key: {key}, Value: {value}, Type: {type(value)}")

        template = Template(TEMPLATE_TEXT)
        return template.render(**goal_data)
    except Exception as e:
        logging.error(f"Error in populate_goal_template(): {e}")
        

async def draft_goal_proposal_message(update, context, goal_id, adjust=False):
    try:
            
        goal_data = context.user_data["goals"].get(goal_id)    

        logging.critical(f"Goal Data in draft_goal_proposal_message:\n{goal_data}")
        await calculate_goal_values(context, goal_id, goal_data, adjust)        # adds the final template parameters to User Context
        
        message_text = await populate_goal_template(update, context, goal_id)
        keyboard = await create_proposal_keyboard(goal_id)

        return message_text, keyboard
    
    except Exception as e:
        await update.message.reply_text(f"Error in draft_goal_proposal_message(): {e}")
        logging.error(f"Error in draft_goal_proposal_message(): {e}")
        

async def run_algorithm(context, goal_id, goal_data, deadline_count):
    time = goal_data.get("time_investment_value")
    effort = goal_data.get("difficulty_multiplier")
    impact = goal_data.get("impact_multiplier")
    
    goal_value = time * effort * impact
        
    penalty = 1
    penalty_field = goal_data.get("failure_penalty")    # Directly stored from the parsed_goal_valuation Classes output
        
    if penalty_field == "small":
        penalty = 1.5 * goal_value
    elif penalty_field == "big":
        penalty = 6 * goal_value
    
    total_goal_value = None
    total_penalty = None
    if deadline_count > 1:
        total_goal_value = goal_value * deadline_count
        total_penalty = penalty * deadline_count
    
    await add_user_context_to_goals(context, goal_id, penalty=penalty, goal_value=goal_value, total_penalty=total_penalty, total_goal_value=total_goal_value)
        
# this is just for calculating and recording in user context/DB the goal and penalty values
async def calculate_goal_values(context, goal_id, goal_data=None, adjust=True):
    try:            
        reminder_times = None
            
        schedule_reminder = goal_data.get("schedule_reminder") or goal_data.get("reminder_scheduled")
        deadlines = (
            goal_data.get("evaluation_deadlines")
            or goal_data.get("evaluation_deadline")
            or goal_data.get("deadlines")
        )
        reminder_times = goal_data.get("reminder_times") or goal_data.get("reminder_time")
        
        if schedule_reminder:
            reminder_times = goal_data.get("reminder_times") or goal_data.get("reminder_time")

        deadline_count, formatted_deadlines = await format_datetime_list(deadlines)
        reminder_count, formatted_reminders = await format_datetime_list(reminder_times if schedule_reminder else None)
        

        if not adjust:  # penalty and goal_value algorithm must only be run once on initialization of proposal, not for later adjustments
            await run_algorithm(context, goal_id, goal_data, deadline_count)
            
        # Join formatted lists into strings to later avoid quotes from jinja template   (<<< this should prolly be moved to format_datetime_list() instead, don't feel like it now)
        formatted_deadlines_str = "\n".join(formatted_deadlines)
        formatted_reminders_str = "\n".join(formatted_reminders) if formatted_reminders else None

        # Adding all the last bits to user context that are needed to fill the proposal template
        await add_user_context_to_goals(
            context,
            goal_id,
            formatted_deadlines=formatted_deadlines_str,
            formatted_reminders=formatted_reminders_str,
            reminder_count=reminder_count,
            deadline_count=deadline_count,
            ID=goal_id,
            PA=PA,
        )
    
    except Exception as e:
        raise RuntimeError(f"Error in calculate_goal_values(): {e}")


async def create_proposal_keyboard(goal_id):
    # First row: Accept and Reject
    button_accept = InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{goal_id}")
    button_reject = InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{goal_id}")

    # Second row: Additional buttons
    button_moon_up = InlineKeyboardButton(text="🌚 ⬆️", callback_data=f"penalty_up_{goal_id}")
    button_moon_down = InlineKeyboardButton(text="🌚 ⬇️", callback_data=f"penalty_down_{goal_id}")
    button_bolt_up = InlineKeyboardButton(text="⚡⬆️", callback_data=f"goal_value_up_{goal_id}")
    button_bolt_down = InlineKeyboardButton(text="⚡⬇️", callback_data=f"goal_value_down_{goal_id}")
        
    # Arrange buttons in the desired layout
    keyboard = InlineKeyboardMarkup([
        [button_accept, button_reject],  # First row
        [button_moon_up, button_moon_down, button_bolt_up, button_bolt_down]  # Second row
    ])
    return keyboard

async def unpack_query(update):
    query = update.callback_query
    match = re.match(r"^(goal_value_up|goal_value_down|penalty_up|penalty_down)_(\d+)$", query.data)
    if match:    
        full_action = match.group(1)  # e.g., "goal_value_up"
        goal_id = int(match.group(2))  # e.g., 123
        # Determine action and direction
        if "goal_value" in full_action:
            action = "goal_value"
        elif "penalty" in full_action:
            action = "penalty"
        if "up" in full_action:
            direction = "up"
        else:
            direction = "down"       
            
        return goal_id, action, direction, query, full_action
    else:
        logging.error(f"Invalid callback data format: {query}")
        

async def handle_proposal_change_click(update, context):
        goal_id, action, direction, query, full_action = await unpack_query(update)
        new_value = await adjust_penalty_or_goal_value(update, context, goal_id, action, direction)
        # Ensure the value is properly formatted
        if new_value is None:    
            await query.answer(f"Error updating value {PA}")
            return

        # Get the current message text
        original_proposal = query.message.text

        # Replace the specific lines directly
        lines = original_proposal.split('\n')
        updated_lines = []

        logging.info(f"Button click received for Goal ID {goal_id}, {full_action}. Action: {action} & Direction: {direction}.")
        for line in lines:
            if "Goal Value" in line and action == "goal_value":
                updated_lines.append(f"⚡️ Goal Value: {new_value}")
                logging.warning(f"Goal line changed: {updated_lines}")
            elif "Potential Penalty" in line and action == "penalty":
                updated_lines.append(f"🌚 Potential Penalty: {new_value}")
                logging.warning(f"Penalty line changed: {updated_lines}")
            else:
                updated_lines.append(line)

        # Join the updated lines back into the message
        updated_message = '\n'.join(updated_lines)

        # Recreate inline keyboard
        keyboard = await create_proposal_keyboard(goal_id)       
        # Edit the message
        try:
            await query.edit_message_text(updated_message, reply_markup=keyboard, parse_mode="Markdown")
            await query.answer(f"Value updated successfully! {PA}")
        except Exception as e:
            logging.error(f"Error editing message text: {e}")
            await query.answer(f"Error updating message text {PA}\n{e}")
        

async def accept_goal_proposal(update, context):
    chat_id=update.effective_chat.id
    user_id=update.effective_user.id
    try:
        goal_id = 0
        query = update.callback_query
        match = re.match(r"^accept_(\d+)$", query.data)
        if match:
            goal_id = int(match.group(1))
        
        # Update goal status
        await update_goal_data(goal_id, status="pending")
        await update_user_data(user_id, chat_id, increment_pending_goals=1)
        
        # Validate goal constraints
        async with Database.acquire() as conn:
            validation_result = await validate_goal_constraints(goal_id, conn)
            if not validation_result['valid']:
                error_msg = f"{PA} Goal ID {goal_id} has issues:\n{validation_result['errors']}"
                logging.error(error_msg)
                await context.bot.send_message(chat_id=chat_id, text=f"{error_msg}")
                return

            logging.info(f"⏰ Goal ID {goal_id} complies with all constraints: {validation_result['valid']}")
            
            # Update message
            description = await fetch_goal_data(goal_id, columns="goal_description", single_value=True)
            updated_message = f"You *Accepted* Goal Proposal #{goal_id}\n> > > _progressed to pending status_\n\n✍️ {description}"
            await query.edit_message_text(updated_message, parse_mode="Markdown")

    except Exception as e:
        logging.warning(f"Error accepting goal proposal: {e}")
        raise  # You might want to add this to propagate the error
   

async def reject_goal_proposal(update, context):
    query = update.callback_query

    goal_id = 0
    query = update.callback_query
    match = re.match(r"^reject_(\d+)$", query.data)
    if match:
        goal_id = int(match.group(1))
    try:
        await update_goal_data(goal_id, status="archived_canceled")
        
        description = await fetch_goal_data(goal_id, columns="goal_description", single_value=True)
        updated_message = f"You *Rejected* Goal Proposal #{goal_id}\n> > > _filed in Archived:Canceled_\n\n✍️ {description}"
    
        await query.edit_message_text(updated_message, parse_mode="Markdown")
        return     
    except Exception as e:
        logging.error(f"NOPE in reject_goal_proposal(): {e}")
        raise
    

async def report_goal_progress(update, context):
    query = update.callback_query
    callback_data = query.data

    # Extract the action and goal_id using the regex groups
    match = (
    re.match(r"^(finished|failed)_(\d+)$", callback_data) or
    re.match(r"^(postpone)_(\d+)_(today|tomorrow)$", callback_data)
    )
    if not match:
        await query.answer("Invalid action.")
        return

    action = match.group(1)  # finished, failed, or postpone
    goal_id = int(match.group(2))  # The goal_id as an integer
        
    # Perform actions based on the extracted data
    if action == "finished":
        await handle_goal_completion(update, goal_id)
        await query.answer("🥂")
    elif action == "failed":
        await handle_goal_failure(update, goal_id)
        await query.answer("🌚")
        # Add logic to handle a failed goal
    elif action == "postpone":
        action = 'postponed'
        await handle_goal_push(update, goal_id, query)
        await query.answer("New day, new youuu")        
        
    # edit the original message
    try:
        emojis = {
            "finished": "✅",
            "failed": "❌",
            "postponed": "⏭️"
        }
        emoji = emojis[action]
        description = await fetch_goal_data(goal_id, columns="goal_description", single_value=True)
        text = f"Goal #{goal_id} is being {'' if action == 'postponed' else 'filed as '}{action.capitalize()} {emoji}\n✍️ {description}"     # Translate to past tense later

        await query.edit_message_text(
            text=text,
            reply_markup=None  
        )
    except Exception as e:
        logging.error(f"couldn't edit expiration message for {goal_id}: {e}")
    

async def handle_goal_completion(update, goal_id):
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        await update_goal_data(goal_id, status="archived_done", completion_time=datetime.now(tz=BERLIN_TZ))
        goal_value  = await fetch_goal_data(goal_id, columns="goal_value", single_value=True)
        await update_user_data(user_id, chat_id, increment_score=goal_value, increment_finished_goals=1, increment_pending_goals=-1)
        logging.info(f"✅ Goal #{goal_id} completed: archived and user score increased by {goal_value}")
    except Exception as e:
        logging.error(f"couldn't handle_goal_completion for goal {goal_id}:\n{e}'")   
    
    
    
async def handle_goal_failure(update, goal_id):
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        await update_goal_data(goal_id, status="archived_failed", completion_time=datetime.now(tz=BERLIN_TZ))
        penalty  = await fetch_goal_data(goal_id, columns="penalty", single_value=True)
        score_decrease = penalty * -1
        await update_user_data(user_id, chat_id, increment_score=score_decrease, increment_penalties_accrued=penalty, increment_failed_goals=1, increment_pending_goals=-1)
        logging.info(f"✅ Goal #{goal_id}'s 'failure completed: archived and {score_decrease} penalty charged ")
    except Exception as e:
        logging.error(f"couldn't handle_goal_failure for goal {goal_id}:\n{e}'")
    

async def handle_goal_push(update, goal_id, query):
    try:
        # Calculate the new deadline
        overdue_deadline = await fetch_goal_data(goal_id, columns="deadline", single_value=True)
        # postpone_to_day = match.group(3)    # not yet implemented
        logging.critical(f"overdue deadline: {overdue_deadline}")
        if overdue_deadline is None:
            raise ValueError(f"Deadline not found for goal ID: {goal_id}")
        # Ensure overdue_deadline is a datetime object
        if not isinstance(overdue_deadline, datetime):
            raise TypeError(f"Expected datetime object for deadline, got {type(overdue_deadline).__name__}")
        tomorrow = overdue_deadline + timedelta(days=1)
        tomorrow_formatted = tomorrow.strftime('%a, %d %B')
    
        description = await fetch_goal_data(goal_id, columns="goal_description", single_value=True)

        # set new deadline and increment goal
        await update_goal_data(goal_id, deadline=tomorrow, increment_iteration=True)      
    
        # charge penalty
        postpone_multiplier = 0.65
        penalty = await fetch_goal_data(goal_id, columns="penalty", single_value=True) * postpone_multiplier
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        score_change = penalty * postpone_multiplier * -1
        await update_user_data(user_id, chat_id, increment_score=score_change, increment_penalties_accrued=penalty)
        
        text = f"⏭️ Postponed goal #{goal_id} to {tomorrow_formatted}. Charged a partial penalty: score {score_change} {PA}\n\n✍️ _{description}_"
        await asyncio.sleep(6)
        await query.edit_message_text(
                text=text,
                parse_mode="Markdown"
        )
    except Exception as e:
        logging.info(f"Error postponing goal: {e}")
