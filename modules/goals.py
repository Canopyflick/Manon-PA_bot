from utils.helpers import get_database_connection
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging
from datetime import datetime
from collections.abc import Iterable


async def process_new_goal(update, context, user_message, description, timeframe, durability, assistant_response):
    await goal_proposal(update, description, durability, assistant_response)


def format_datetime_list(datetime_input):
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
    
async def goal_proposal(update, description, durability, assistant_response):
    try:
        # Extract relevant parts of the assistant response
        reasoning = assistant_response.reasoning
        schedule_reminder = assistant_response.schedule_reminder
        
        # Use the formatting function for deadlines and reminders
        deadline_count, formatted_deadlines = format_datetime_list(
            getattr(assistant_response, 'deadline', None)
        )
        reminder_count, formatted_reminders = format_datetime_list(
            assistant_response.reminder_time if schedule_reminder else None
        )
        
        time_investment = assistant_response.time_investment_value
        effort = assistant_response.difficulty_multiplier
        impact = assistant_response.impact_multiplier
        
        # Calculate goal value
        goal_value = round(time_investment * effort * impact, 2)
        total_goal_value = goal_value * deadline_count
        
        # Calculate the penalty
        penalty = total_penalty = 0
        
        penalty_field_value = assistant_response.penalty
        if penalty_field_value == 1:
            penalty = total_penalty = round(2.5 * goal_value, 2)
        elif penalty_field_value != 0:
            penalty = penalty_field_value
            total_penalty = round(penalty * deadline_count, 2)
            
            
        
        # Create message text
        message_text = (
            f"👩‍🦰 *{durability.capitalize()} Goal Proposal*\n"
            f"✍️ {description}\n\n"
            f"{deadline_count} Deadline(s):\n"
            + "\n".join(formatted_deadlines)
            + f"\n\n⚡ Goal Value: {goal_value} ({total_goal_value} total)\n"
            f"🌚 Potential Penalty: {penalty} ({total_penalty} total)"
        )
        
        if schedule_reminder and reminder_count > 0:
            message_text += f"\n\n⏰ {reminder_count} Reminders:\n" + "\n".join(formatted_reminders)
        
        # Create buttons (rest of the function remains the same)
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        button_accept = InlineKeyboardButton(text="✅ Accept!", callback_data=f"accept_{user_id}_{first_name}")
        button_reject = InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{user_id}_{first_name}")
        button_adjust = InlineKeyboardButton(text="🛠️ Adjust", callback_data=f"adjust_{user_id}_{first_name}")
        
        # Add buttons to the keyboard
        keyboard = InlineKeyboardMarkup([[button_accept], [button_reject], [button_adjust]])
        
        # Send message with buttons
        await update.message.reply_text(message_text, reply_markup=keyboard, parse_mode="Markdown")
    
    except Exception as e:
        await update.message.reply_text(f"Error in goal_proposal(): {e}")
        logging.error(f"Error in goal_proposal(): {e}")