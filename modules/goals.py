from utils.helpers import BERLIN_TZ, add_user_context_to_goals, PA
from utils.db import update_goal_data, complete_limbo_goal, adjust_penalty_or_goal_value, fetch_template_data_from_db, Database, validate_goal_constraints
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging, re, asyncio
from datetime import datetime
from collections.abc import Iterable
from jinja2 import Template




async def process_new_goal(update, context, user_message, goal_description, timeframe, recurrence_type, assistant_response):
    await goal_proposal(update, goal_description, recurrence_type, assistant_response)


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
    

async def send_goal_proposal(update, context, goal_id):     # Only for the initial sending, when no proposal exists yet for this goal
    try:
        message_text, keyboard = await draft_goal_proposal_message(update, context, goal_id, adjust=False)
                
        await complete_limbo_goal(update, context, goal_id) # Storing the full goal in db for the first time
       
        # Send message with buttons
        await update.message.reply_text(message_text, reply_markup=keyboard, parse_mode="Markdown")
    
    except Exception as e:
        await update.message.reply_text(f"Error in send_goal_proposal(): {e}")
        logging.error(f"Error in send_goal_proposal(): {e}")
    
        
TEMPLATE_TEXT = """{{ PA }}‍ *{{ recurrence_type | capitalize }} Goal Proposal*
✍️ {{ goal_description }}

📅 {{ "Deadline" if deadline_count == 1 else deadline_count ~ " Deadlines" }}:
{{ formatted_deadlines }}

⚡ Goal Value: {{ goal_value | round(1) }} {% if total_goal_value is not none %}({{ total_goal_value | round(0) | int }} total){% endif %}
🌚 Potential Penalty: {{ penalty | round(1) }} {% if total_penalty is not none %}({{ total_penalty | round(0) | int }} total){% endif %}
{% if schedule_reminder and reminder_count > 0 %}\n⏰ {{ "Reminder" if reminder_count == 1 else reminder_count ~ " Reminders" }}:\n{{ formatted_reminders }}\n{% endif %}#_{{ ID }}_"""

        
async def populate_goal_template(update, context, goal_id):
    try:
        goal_data = context.user_data["goals"].get(goal_id) # In case of an adjustment, goal_data should have already been fetched from db in calculate_goal_values (called in draft_goal_proposal_message)      

        template = Template(TEMPLATE_TEXT)
        return template.render(**goal_data)
    except Exception as e:
        logging.error(f"Error in populate_goal_template(): {e}")
        

async def draft_goal_proposal_message(update, context, goal_id, adjust):
    try:
        if not adjust:      # for first initialization of the goal proposal, retrieving data from user context
            goal_data = context.user_data["goals"].get(goal_id)
            logging.critical(f"Goal Data in draft_goal_proposal_message: {goal_data}")
            await calculate_goal_values(context, goal_id, goal_data, adjust)        # adds the final template parameters to User Context
        
            message_text = await populate_goal_template(update, context, goal_id)
            logging.critical(f"Message text:\n{message_text}")
            keyboard = await create_proposal_keyboard(goal_id)

            return message_text, keyboard
        else:               # for adjustment of a previously initialized goal proposal, retrieving data from db
            print(f"Get That Shit FROM THE DATABASE! ???? hm this happens in calculate_goal_values already wouldn't it??'")
    except Exception as e:
        await update.message.reply_text(f"Error in draft_goal_proposal_message(): {e}")
        logging.error(f"Error in draft_goal_proposal_message(): {e}")
        

async def run_algorithm(context, goal_id, goal_data, deadline_count):
    time = goal_data.get("time_investment_value")
    effort = goal_data.get("difficulty_multiplier")
    impact = goal_data.get("impact_multiplier")
    
    goal_value = time * effort * impact
    total_goal_value = goal_value * deadline_count
        
    penalty = 1
    penalty_field = goal_data.get("failure_penalty")    # Directly stored from the parsed_goal_valuation Classes output
        
    if penalty_field == "small":
        penalty = 1.5 * goal_value
    elif penalty_field == "big":
        penalty = 6 * goal_value
        
    total_penalty = penalty * deadline_count
    
    await add_user_context_to_goals(context, goal_id, penalty=penalty, goal_value=goal_value, total_penalty=total_penalty, total_goal_value=total_goal_value)
        
# this is just for calculating and recording in user context/DB the goal and penalty values
async def calculate_goal_values(context, goal_id, goal_data=None, adjust=True):
    try:            
        reminder_times = None
        if adjust:
            await fetch_template_data_from_db(context, goal_id)
            print(f"Get That Shit FROM THE DATABASE! en put into goal_data")
            
        schedule_reminder = goal_data.get("schedule_reminder")
        deadlines = goal_data.get("evaluation_deadlines") or [goal_data.get("evaluation_deadline")]
        reminder_times = goal_data.get("reminder_times") or [goal_data.get("reminder_time")]
        
        if schedule_reminder:
            reminder_times = goal_data.get("reminder_times") or [goal_data.get("reminder_time")]

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
    try:
        goal_id = 0
        query = update.callback_query
        match = re.match(r"^accept_(\d+)$", query.data)
        if match:
            goal_id = int(match.group(1))
        
        # Update goal status
        await update_goal_data(goal_id, status="pending")
        
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
            updated_message = f"You *Accepted* Goal Proposal #{goal_id}\n> > > _progressed to pending status_\n\n✍️ Description"
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

        updated_message = f"You *Rejected* Goal Proposal #{goal_id}\n> > > _filed in Archived:Canceled_\n\n✍️ Description"
    
        await query.edit_message_text(updated_message, parse_mode="Markdown")
        return     
    except Exception as e:
        logging.error(f"NOPE in reject_goal_proposal(): {e}")
        raise

