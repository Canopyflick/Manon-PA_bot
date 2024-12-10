from utils.helpers import get_database_connection, BERLIN_TZ, add_user_context_to_goals, PA
from utils.db import update_goal_data, complete_limbo_goal, adjust_penalty_or_goal_value
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging, re, asyncio
from datetime import datetime
from collections.abc import Iterable




async def process_new_goal(update, context, user_message, description, timeframe, frequency, assistant_response):
    await goal_proposal(update, description, frequency, assistant_response)


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
    

async def send_goal_proposal(update, context, goal_id):
    try:
        # Get the needed data from user context
        goal_data = context.user_data["goals"].get(goal_id)
        logging.info(f"Goal data: {goal_data}")

        frequency = goal_data.get("goal_recurrence_type")

        # Deseriali
        schedule_reminder = goal_data.get("schedule_reminder")
        description = goal_data.get("description")
        
        evaluation_deadlines = goal_data.get("evaluation_deadlines") or goal_data.get("evaluation_deadline")
        reminders=None
        if schedule_reminder:
            reminders = goal_data.get("reminders") or goal_data.get("reminder")

        # Use the formatting function for deadlines and reminders
        deadline_count, formatted_deadlines = await format_datetime_list(evaluation_deadlines)
        reminder_count, formatted_reminders = await format_datetime_list(reminders if schedule_reminder else None)      

        time_investment = goal_data.get("time_investment_value")
        effort = goal_data.get("difficulty_multiplier")
        impact = goal_data.get("impact_multiplier")
    
        # Calculate goal value
        goal_value = round(time_investment * effort * impact, 2)
        total_goal_value = round(goal_value * deadline_count, 0)
        
        # Calculate the penalty
        # for 'no penalty':
        penalty = 1
        
        penalty_field_value = goal_data.get("failure_penalty")
        if penalty_field_value == "small":
            penalty = round(1.5 * goal_value, 2)
        elif penalty_field_value == "big":
            penalty = round(6 * goal_value, 2)
        
        total_penalty = round(penalty * deadline_count, 0)
        
        await add_user_context_to_goals(context, goal_id, penalty=penalty, goal_value=goal_value)
        
        await complete_limbo_goal(update, context, goal_id)
        
        ID = goal_id    # which is in fact group_id, if frequency == recurring
        
        # Create message text
        message_text = (
            f"{PA}‍ *{frequency.capitalize()} Goal Proposal*\n"
            f"✍️ {description}\n\n"
            f"{deadline_count} Deadline(s):\n"
            + "\n".join(formatted_deadlines)
            + f"\n\n⚡ Goal Value: {goal_value} ({total_goal_value} total)\n"
            f"🌚 Potential Penalty: {penalty} ({total_penalty} total)\n"
            f"#_{ID}_"
        )
        
        if schedule_reminder and reminder_count > 0:
            message_text += f"\n\n⏰ {reminder_count} Reminders:\n" + "\n".join(formatted_reminders)
        
        # Create inline keyboard
        keyboard = await create_proposal_keyboard(goal_id)
        
        # Send message with buttons
        await update.message.reply_text(message_text, reply_markup=keyboard, parse_mode="Markdown")
    
    except Exception as e:
        await update.message.reply_text(f"Error in send_goal_proposal(): {e}")
        logging.error(f"Error in send_goal_proposal(): {e}")
        





async def create_proposal_keyboard(goal_id):
    # First row: Accept and Reject
    button_accept = InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{goal_id}")
    button_reject = InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{goal_id}")

    # Second row: Additional buttons
    button_moon_up = InlineKeyboardButton(text="🌚⬆️", callback_data=f"penalty_up_{goal_id}")
    button_moon_down = InlineKeyboardButton(text="🌚⬇️", callback_data=f"penalty_down_{goal_id}")
    button_bolt_up = InlineKeyboardButton(text="⚡⬆️", callback_data=f"goal_value_up_{goal_id}")
    button_bolt_down = InlineKeyboardButton(text="⚡⬇️", callback_data=f"goal_value_down_{goal_id}")
        
    # Arrange buttons in the desired layout
    keyboard = InlineKeyboardMarkup([
        [button_accept, button_reject],  # First row
        [button_moon_up, button_moon_down, button_bolt_up, button_bolt_down]  # Second row
    ])
    return keyboard
    

async def handle_proposal_change_click(update, context):
    query = update.callback_query
    match = re.match(r"^(goal_value_up|goal_value_down|penalty_up|penalty_down)_(\d+)$", query.data)
    data = query.data  # Callback data (e.g., "penalty_down_123")
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
            await asyncio.sleep(1)
        except Exception as e:
            logging.error(f"Error editing message text: {e}")
            await query.answer(f"Error updating message text {PA}\n{e}")
    else:
        logging.error(f"Invalid callback data format: {query}")
        

async def accept_goal_proposal(update, context):
    try:
        goal_id = 0
        query = update.callback_query
        match = re.match(r"^accept_(\d+)$", query.data)
        if match:
            goal_id = int(match.group(1))
    
        conn = get_database_connection()
        await update_goal_data(goal_id, status="pending")
        validation_result = await validate_goal_constraints(goal_id, conn)
        if not validation_result['valid']:
            logging.error(f"⏰ Goal ID {goal_id} has issues: {validation_result['errors']}")
            await update.message.reply_text(f"⏰ Goal ID {goal_id} has issues: {validation_result['errors']}")
            return
        updated_message = f"You *accepted* Goal Proposal #{goal_id}\n> > > _progressed to pending status_\n\n✍️ Description"
        await query.edit_message_text(updated_message, parse_mode="Markdown")
        return
    except Exception as e:
        logging.warning(f"Error accepting goal proposal: {e}")
   

async def reject_goal_proposal(update, context):
    query = update.callback_query

    goal_id = 0
    query = update.callback_query
    match = re.match(r"^accept_(\d+)$", query.data)
    data = query.data  # Callback data (e.g., "penalty_down_123")
    if match:
        goal_id = int(match.group(2))
    await update_goal_data(goal_id, status="archived_canceled")

    updated_message = f"You *rejected* Goal Proposal #{goal_id}\n> > > _filed in Archived:Canceled_\n\n✍️ Description"
    
    await query.edit_message_text(updated_message, parse_mode="Markdown")
    return     


async def validate_goal_constraints(goal_id, conn):
    """
    Validates a goal's data against predefined constraints.
    
    Args:
        goal_id (int): The ID of the goal to validate.
        conn (psycopg2 connection): The database connection.

    Returns:
        dict: A dictionary with validation results and messages.
    """
    query = '''
        SELECT * FROM manon_goals WHERE goal_id = %s;
    '''
    cursor = conn.cursor()
    cursor.execute(query, (goal_id,))
    goal = cursor.fetchone()
    cursor.close()
    conn.close()

    if not goal:
        return {'valid': False, 'message': 'Goal not found.'}

    # Map goal data to variables
    columns = [desc[0] for desc in cursor.description]
    goal_data = dict(zip(columns, goal))
    
    errors = []

    # Validation rules
    if goal_data['status'] not in ('limbo', 'prepared', 'pending', 'paused', 'archived_done', 'archived_failed', 'archived_canceled', None):
        errors.append('Invalid status value.')

    if goal_data['goal_recurrence_type'] not in ('one-time', 'recurring', None):
        errors.append('Invalid recurrence type.')

    if goal_data['goal_timeframe'] not in ('today', 'by_date', 'open-ended', None):
        errors.append('Invalid timeframe.')

    if goal_data['goal_timeframe'] in ('today', 'by_date') and not goal_data['deadline']:
        errors.append('Deadline must be set for "today" or "by_date" timeframes.')

    if goal_data['goal_timeframe'] == 'open-ended' and goal_data['deadline']:
        errors.append('Deadline must not be set for "open-ended" timeframe.')

    if goal_data['final_iteration'] not in ('not_applicable', 'false', 'true', None):
        errors.append('Invalid final iteration value.')

    if goal_data['goal_category'] is None or not isinstance(goal_data['goal_category'], list):
        errors.append('Goal category must be a non-null array.')

    # Return validation results
    if errors:
        return {'valid': False, 'errors': errors}
    return {'valid': True, 'message': 'Goal is valid.'}