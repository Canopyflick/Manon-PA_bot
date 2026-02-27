# LLMs/orchestration.py
from datetime import datetime, timedelta
from httpx import Response
from openai import OpenAI

from telegram_helpers.get_user_message import get_user_message
from utils.environment_vars import ENV_VARS
from utils.helpers import BERLIN_TZ
from telegram_helpers.emoji_reactions import safe_set_reaction
from telegram_helpers.delete_message import delete_message, add_delete_button
from utils.session_avatar import PA
from features.goals.goals import send_goal_proposal, handle_goal_completion
from features.goals.helpers import add_user_context_to_goals
import logging, asyncio
from dateutil.parser import parse
from utils.db import (
    fetch_goal_data,
    fetch_long_term_goals,
    create_limbo_goal,
    complete_limbo_goal,
    record_reminder,
)
from LLMs.config import chains, shared_state
from LLMs.structured_output_schemas import (
    DummyClass,
    InitialClassification,
    GoalClassification,
    SetGoalAnalysis,
    LanguageCorrection,
    LanguageCheck,
    Translation,
    Translations,
    Schedule,
    Planning,
    GoalAssessment,
    GoalInstanceAssessment,
    GoalID,
    UpdatedGoalData,
    Reminder,
    Response,
    CompactSchedule,
    CompactPlanning,
)
#########################################################################

# Toggle between old (3-call) and new (2-call) compact goal pipeline
COMPACT_PIPELINE = True

logger = logging.getLogger(__name__)

client_EC = OpenAI(api_key=ENV_VARS.EC_OPENAI_API_KEY)


#########################################################################


TG_MAX = 4000  # Telegram hard limit is 4096; leave a small margin

def split_message(text: str, max_len: int = TG_MAX) -> list[str]:
    """Split a long string into Telegram-safe chunks, breaking on paragraph
    boundaries where possible, then on newlines, then hard-cutting."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while len(text) > max_len:
        split_at = text.rfind("\n\n", 0, max_len)
        if split_at == -1:
            split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at].rstrip())
        text = text[split_at:].lstrip()
    if text:
        chunks.append(text)
    return chunks


async def get_input_variables(update, context, source_text=None, target_language="English", goal_data=None):
    now = datetime.now(tz=BERLIN_TZ)
    weekday = now.strftime("%A")  # Full weekday name
    tomorrow = (now + timedelta(days=1))
    # Calculate the next Wednesday
    days_until_wednesday = (2 - now.weekday() + 7) % 7  # 2 is Wednesday (0=Monday, 6=Sunday)
    if days_until_wednesday == 0:  # If today is Wednesday, move to next week
        days_until_wednesday = 7
    next_wednesday = now + timedelta(days=days_until_wednesday)
    # Set time to 12:00:00 for next Wednesday
    next_wednesday_at_noon = next_wednesday.replace(hour=12, minute=0, second=0)

    next_year = now.replace(year=now.year + 1)
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    first_name = update.effective_user.first_name
    bot_name = update.get_bot().username
    default_deadline_time = "22:22"
    default_reminder_time = "11:11"
    long_term_goals = await fetch_long_term_goals(chat_id, user_id)
    user_message = source_text if source_text else get_user_message(update, context)
    response_text = update.message.reply_to_message.text if update.message.reply_to_message else None
    goal_data = goal_data if goal_data else "No goal_data passed as argument"

    # Ensure proper formatting for the template
    now_formatted = f"{now.date()}T18:01:00{now.strftime('%z')}"
    tomorrow_formatted = f"{tomorrow.date()}T18:01:00{tomorrow.strftime('%z')}"
    next_wednesday_formatted = next_wednesday_at_noon.strftime("%Y-%m-%dT%H:%M:%S%z")
    

    if response_text:
        user_message = f"{user_message}\n\n(As a reply to message: {response_text})"
        
    return {
        "first_name": first_name,
        "bot_name": bot_name,
        "user_message": user_message,
        "now": now.strftime("%Y-%m-%d %H:%M:%S"),  # Include current datetime as string
        "weekday": weekday,
        "user_id": user_id,
        "chat_id": chat_id,
        "default_deadline_time": default_deadline_time,
        "default_reminder_time": default_reminder_time,
        "long_term_goals": long_term_goals,
        "response_text": response_text,
        "target_language": target_language,
        "tomorrow": tomorrow,
        "tomorrow_formatted": tomorrow_formatted,
        "now_formatted": now_formatted,
        "next_wednesday": next_wednesday_formatted,
        "next_year": next_year,
        "goal_data": goal_data,
        "PA": PA,
    }


async def run_chain(chain_name, input_variables: dict):
    """
    A generic async function to run a given structured chain.
    Handles prompt formatting, invoking the LLM, and returning results.
    
    Args:
        chain (dict): A dictionary containing the template and LLM structured chain.
        input_variables (dict): Input variables to format the prompt.

    Returns:
        The result of invoking the chain's LLM with the formatted prompt.
    """
    try:
        # Resolve the chain by its name
        chain = chains.get(chain_name)
        if not chain:
            raise KeyError(f"Chain '{chain_name}' not found in the chains dictionary.")
        # Generate the prompt using the chain's template
        prompt_value = chain["template"].format_prompt(**input_variables)
        
        # Invoke the LLM with the formatted prompt
        result = await chain["chain"].ainvoke(prompt_value.to_messages())
        
        # Log and return the result
        logger.info(f"Chain '{chain_name}' executed successfully: {result}")
        return result

    except KeyError as e:
        logger.error(f"Chain is missing a required key: {e}")
        raise ValueError(f"Invalid chain structure: missing {e}")

    except Exception as e:
        logger.error(f"Error running chain: {e}")
        raise RuntimeError(f"Failed to execute chain: {e}")



# pipelines orchestration < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < <
async def dummy_call(update, context):
    try:
        input_vars = await get_input_variables(update, context)
        output = await run_chain("name_of_chain", input_vars)
        
        parsed_output = DummyClass.model_validate(output)
        dummy_field = parsed_output.dummy_field
        
        if shared_state["transparant_mode"]:
            debug_message = await update.message.reply_text(f"classification_result: \n{output}")
            await add_delete_button(update, context, debug_message.message_id)
            asyncio.create_task(delete_message(update, context, debug_message.message_id, 120))
        
        if dummy_field == "something in particular":
            await next_step(update, context, output)
        else: 
            await update.message.reply_text(f"_Next step for {dummy_field} not yet implemented_", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error in dummy_call():\n {e}")
        logger.error(f"\n\n🚨 Error in dummy_call(): {e}\n\n")


async def start_initial_classification(update, context, override_text=None):
    try:
        # Extract input variables
        input_vars = await get_input_variables(update, context)
        initial_classification = await run_chain("initial_classification", input_vars)        
        
        if shared_state["transparant_mode"]:
            debug_message = await update.message.reply_text(f"Initial Classification Result: \n{initial_classification}")
            await add_delete_button(update, context, debug_message.message_id)
            asyncio.create_task(delete_message(update, context, debug_message.message_id, 120))
        
        await process_classification_result(update, context, initial_classification)

    except Exception as e:
        await update.message.reply_text(f"Error in start_initial_classification():\n {e}")
        logger.error(f"\n\n🚨 Error in start_initial_classification(): {e}\n\n")
    

async def process_classification_result(update, context, initial_classification):
    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    user_message = get_user_message(update, context)
    try:
        # Parse the classification result
        parsed_result = InitialClassification.model_validate(initial_classification)
        # later_reaction = parsed_result.emoji_reaction (deleted this, cause buggy)
        language = parsed_result.user_message_language

        # log_emoji_details(later_reaction, "gpt-4o-mini")

        if language != "English" and language != "Dutch":
            preset_reaction = "💯"
            await safe_set_reaction(context.bot, chat_id=chat_id, message_id=message_id, reaction=preset_reaction)
            await process_other_language(update, context, user_message, language)
            # await asyncio.sleep(5)
            # await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=later_reaction)
            return

        initial_classification = parsed_result.classification
        # Respond based on classification
        if initial_classification == "Goals":
            preset_reaction = "⚡"
            await safe_set_reaction(context.bot, chat_id=chat_id, message_id=message_id, reaction=preset_reaction)
            await handle_goal_classification(update, context)                           # < < < < <
            # await asyncio.sleep(5)
            # await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=later_reaction)
        elif initial_classification == "Reminders":
            preset_reaction = "🫡"
            await safe_set_reaction(context.bot, chat_id=chat_id, message_id=message_id, reaction=preset_reaction)
            await reminder_setting(update, context)                                     # < < < < <
            # await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=later_reaction)
        elif initial_classification == "Meta":
            preset_reaction = "💩"
            await update.message.reply_text("This is a meta query about the bot.\n_(remaining flow not yet implemented)_", parse_mode="Markdown")                                              # < < < < <
            await safe_set_reaction(context.bot, chat_id=chat_id, message_id=message_id, reaction=preset_reaction)
        else:
            preset_reaction = "😘"
            await other_message(update, context)                                        # < < < < <
            await safe_set_reaction(context.bot, chat_id=chat_id, message_id=message_id, reaction=preset_reaction)
            

    except Exception as e:
        await update.message.reply_text(f"{PA} Error in process_classification_result():\n {e}")
        logger.error(f"\n\n🚨 Error in process_classification_result(): {e}\n\n")
        

async def handle_goal_classification(update, context, smarter=False):
    try:
        input_vars = await get_input_variables(update, context)
        goal_classification=None
        if smarter:
            goal_classification = await run_chain("goal_classification_smart", input_vars)  
        else:
            goal_classification = await run_chain("goal_classification", input_vars)   
        
        parsed_goal_classification = GoalClassification.model_validate(goal_classification)

        if shared_state["transparant_mode"]:
            debug_message = await update.message.reply_text(f"goal_classification: \n{parsed_goal_classification}")
            await add_delete_button(update, context, debug_message.message_id)
            asyncio.create_task(delete_message(update, context, debug_message.message_id, 120))


        goal_result = parsed_goal_classification.classification

        if goal_result == "Set":
            goal_id = await create_limbo_goal(update, context)
            if goal_id is None:
                await update.message.reply_text(f"Cannot proceed with goal setting. Are you already registered? {PA}\n\n/start")
                return
            # Initialize a dictionary for the goal in user context
            if "goals" not in context.user_data:
                context.user_data["goals"] = {}
            # Create an empty dictionary for the specific goal_id
            context.user_data["goals"][goal_id] = {}
            
            await goal_setting_analysis(update, context, goal_id, smarter)                                                                        # < < < < <
        elif goal_result == "Edit":
            logger.info(f"User wants to edit a goal >> find_goal_id()")
            await find_goal_id(update, context, type="edit")
        elif goal_result == "Report_done":
            logger.info(f"User wants to report a goal as done >> find_goal_id()")
            await find_goal_id(update, context, type="done")
        else: 
            await update.message.reply_text(f"_Goal result '{goal_result}' not yet implemented_", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error in handle_goal_classification():\n {e}")
        logger.error(f"\n\n🚨 Error in handle_goal_classification(): {e}\n\n")


async def goal_setting_analysis(update, context, goal_id, smarter=False):
    try:
        input_vars = await get_input_variables(update, context)
        goal_setting_analysis = await run_chain("goal_setting_analysis", input_vars)
        parsed_goal_analysis = SetGoalAnalysis.model_validate(goal_setting_analysis)
        
        if shared_state["transparant_mode"]:
            debug_message = await update.message.reply_text(f"parsed_goal_analysis: \n{parsed_goal_analysis}")
            await add_delete_button(update, context, debug_message.message_id)
            asyncio.create_task(delete_message(update, context, debug_message.message_id, 120))

        recurrence_type = parsed_goal_analysis.evaluation_frequency
        timeframe = parsed_goal_analysis.timeframe
        
        await add_user_context_to_goals(
            context,
            goal_id,
            recurrence_type=recurrence_type,
            timeframe=timeframe,
            category=parsed_goal_analysis.category
        )

        if timeframe == "open-ended":
            # shortcut the save, skip valuation and proposal at this point for this goal_type
            description = parsed_goal_analysis.description
            await add_user_context_to_goals(context, goal_id, goal_description=description)
            await complete_limbo_goal(update, context, goal_id, initial_update=True)
            return
        
        elif COMPACT_PIPELINE:
            await compact_goal_pipeline(update, context, goal_id, recurrence_type, smarter)
        elif recurrence_type == 'one-time':
            await goal_valuation(update, context, goal_id, smarter=smarter)
        elif recurrence_type == 'recurring':
            await goal_valuation(update, context, goal_id, "recurring", smarter)
        else:
            await update.message.reply_text(
                f"Next step for ANDERS not yet implemented: ???"
            )
    except Exception as e:
        await update.message.reply_text(f"Error in goal_setting_analysis():\n {e}")
        logger.error(f"\n\n🚨 Error in goal_setting_analysis(): {e}\n\n")
        

async def goal_valuation(update, context, goal_id, recurrence_type="one-time", smarter=False):
    try:
        input_vars = await get_input_variables(update, context)
        parsed_goal_valuation = None
        if recurrence_type == 'recurring':
            goal_valuation = await run_chain("recurring_goal_valuation", input_vars)
            parsed_goal_valuation = GoalInstanceAssessment.model_validate(goal_valuation)
        elif recurrence_type == 'one-time':
            goal_valuation = await run_chain("goal_valuation", input_vars)
            parsed_goal_valuation = GoalAssessment.model_validate(goal_valuation)
        
        if shared_state["transparant_mode"]:
            debug_message = await update.message.reply_text(f"Parsed Goal Valuation: \n{parsed_goal_valuation}")
            await add_delete_button(update, context, debug_message.message_id)
            asyncio.create_task(delete_message(update, context, debug_message.message_id, 200))     # Clean chat, clean life
        
        await add_user_context_to_goals(
            context,
            goal_id,
            parsed_goal_valuation=parsed_goal_valuation,
        )

        await prepare_goal_proposal(update, context, goal_id, recurrence_type=recurrence_type, smarter=smarter)
        
    except Exception as e:
        await update.message.reply_text(f"Error in goal_valuation():\n {e}")
        logger.error(f"\n\n🚨 Error in goal_valuation(): {e}\n\n")
        

async def prepare_goal_proposal(update, context, goal_id, recurrence_type, smarter=False):
    try:
        input_vars = await get_input_variables(update, context)
        parsed_planning = None
        if recurrence_type == 'recurring':
            if smarter:
                output = await run_chain("schedule_goals_smart", input_vars)        
                parsed_planning = Planning.model_validate(output)
            else:
                output = await run_chain("schedule_goals", input_vars)        
                parsed_planning = Planning.model_validate(output)               
        elif recurrence_type == 'one-time':
            if smarter:
                output = await run_chain("schedule_goal_smart", input_vars)
                parsed_planning = Schedule.model_validate(output)
            else:
                output = await run_chain("schedule_goal", input_vars)
                parsed_planning = Schedule.model_validate(output)
                
        if shared_state["transparant_mode"]:
            debug_message = await update.message.reply_text(f"prepare_goal_proposal: \n{parsed_planning}") 
            await add_delete_button(update, context, debug_message.message_id)
            asyncio.create_task(delete_message(update, context, debug_message.message_id, 120))
        
        await add_user_context_to_goals(
            context,
            goal_id,
            parsed_planning=parsed_planning
        )
        
        await send_goal_proposal(update, context, goal_id)
            
    except Exception as e:
        await update.message.reply_text(f"Error in prepare_goal_proposal():\n {e}")
        logger.error(f"\n\n🚨 Error in prepare_goal_proposal(): {e}\n\n")


async def compact_goal_pipeline(update, context, goal_id, recurrence_type, smarter=False):
    """Compact pipeline: combined valuation + scheduling in one LLM call (replaces goal_valuation + prepare_goal_proposal)."""
    try:
        input_vars = await get_input_variables(update, context)

        if recurrence_type == 'recurring':
            chain_name = "compact_planning_smart" if smarter else "compact_planning"
            result = await run_chain(chain_name, input_vars)
            parsed_result = CompactPlanning.model_validate(result)
        else:
            chain_name = "compact_schedule_smart" if smarter else "compact_schedule"
            result = await run_chain(chain_name, input_vars)
            parsed_result = CompactSchedule.model_validate(result)

        if shared_state["transparant_mode"]:
            debug_message = await update.message.reply_text(f"compact_goal_pipeline: \n{parsed_result}")
            await add_delete_button(update, context, debug_message.message_id)
            asyncio.create_task(delete_message(update, context, debug_message.message_id, 200))

        # Store valuation and planning fields in context (same field names as old pipeline)
        await add_user_context_to_goals(context, goal_id, parsed_goal_valuation=parsed_result)
        await add_user_context_to_goals(context, goal_id, parsed_planning=parsed_result)

        await send_goal_proposal(update, context, goal_id)

    except Exception as e:
        await update.message.reply_text(f"Error in compact_goal_pipeline():\n {e}")
        logger.error(f"\n\n🚨 Error in compact_goal_pipeline(): {e}\n\n")


# /translate + any other non-English or non-Dutch messages pass through this
async def process_other_language(update, context, user_message, language=None, translate_command=False):
    if language == "German" and translate_command:          # translate to Dutch")
        await translate(update, context, source_text=user_message, target_language='Dutch')
    elif language == "German":
        await language_correction(update, context)          # revise
    elif language == "Dutch" and translate_command or language == "English":         # translate to German
        await translate(update, context, source_text=user_message, target_language='German', verbose=True)
    elif language == "Dutch":                               # don't translate, will be processed as any English message
        logger.info(f"Dutch jatog")
    else:
        await update.message.reply_text(f"# translate to English")
        await translate(update, context, source_text=user_message, target_language="English")      # translate to English


async def translate(update, context, source_text, target_language="German", verbose=False):
    try:
        input_vars = await get_input_variables(update, context, source_text, target_language)
        if verbose:
            output = await run_chain("translations", input_vars)
        
            parsed_output = Translations.model_validate(output)
            casual = parsed_output.casual
            formal = parsed_output.formal 
            degenerate = parsed_output.degenerate 
        
            casual_message = await update.message.reply_text(f"*{casual}*", parse_mode="Markdown")
            formal_message = await update.message.reply_text(f"{formal}", parse_mode="Markdown")
            slang_message = await update.message.reply_text(f"{degenerate}", parse_mode="Markdown")

            # Add delete buttons to each message
            await add_delete_button(update, context, casual_message.message_id, delay=5)
            await add_delete_button(update, context, formal_message.message_id, delay=0)
            await add_delete_button(update, context, slang_message.message_id, delay=0)
        if not verbose:
            output = await run_chain("translation", input_vars)
        
            parsed_output = Translation.model_validate(output)
            translation = parsed_output.translation
        
            translation_message = await update.message.reply_text(f"*{translation}*", parse_mode="Markdown")

            # Add delete buttons to each message
            await add_delete_button(update, context, translation_message.message_id, delay=0)

    except Exception as e:
        await update.message.reply_text(f"Error in translate():\n {e}")
        logger.error(f"\n\n🚨 Error in translate(): {e}\n\n")
        

async def language_correction(update, context):
    try:
        input_vars = await get_input_variables(update, context)
        output = await run_chain("language_correction", input_vars)
        
        parsed_output = LanguageCorrection.model_validate(output)
        corrected_text = parsed_output.corrected_text
        changes = parsed_output.changes     # not doing anything with this right now, would be nice to be able to request it with an emoji reaction 
        
        await update.message.reply_text(f"classification_result: \n{parsed_output}")
        await update.message.reply_text(f"*{corrected_text}*", parse_mode="Markdown")
        
        # await see_changes_flow (update, context, output)
    except Exception as e:
        await update.message.reply_text(f"Error in revision:\n {e}")
        logger.error(f"\n\n🚨 Error in revision: {e}\n\n")
        
    
async def check_language(update, context, source_text):
    try:
        input_vars = await get_input_variables(update, context, source_text=source_text)
        output = await run_chain("language_check", input_vars)
        
        parsed_output = LanguageCheck.model_validate(output)
        language = parsed_output.user_message_language
        
        logger.info(f"Language checked: {language}")
        
        return language
    
    except Exception as e:
        await update.message.reply_text(f"Error in check_language():\n {e}")
        logger.error(f"\n\n🚨 Error in check_language(): {e}\n\n")


# for now, this only works for (replies to) messages that contain the goal_id in plaintext. Should later be expanded with some database content (with the user's recently set goals) that provide potentially relevant goal ids as sadditional context
async def find_goal_id(update, context, type=None):
    try:
        input_vars = await get_input_variables(update, context)
        output = await run_chain("find_goal_id", input_vars)
        
        parsed_output = GoalID.model_validate(output)
        goal_id = parsed_output.ID
        
        if shared_state["transparant_mode"]:
            debug_message = await update.message.reply_text(f"Found Goal ID that should be edited: \n*#{output}*", parse_mode = "Markdown")
            await add_delete_button(update, context, debug_message.message_id)
            asyncio.create_task(delete_message(update, context, debug_message.message_id, 120))
        
        if goal_id == 0:
            await update.message.reply_text(f"Couldn't find goal {PA}", parse_mode = "Markdown")
            logger.warning(f"\n\n🚨 Goal ID not found\n\n")
            return
        else:
            if type == "edit":
                await prepare_goal_changes(update, context, goal_id)
            if type == "done":
                await handle_goal_completion(update, goal_id)
    except Exception as e:
        await update.message.reply_text(f"🚨 Goal ID not found:\n {e}")
        logger.error(f"\n\n🚨 Goal ID not found): {e}\n\n")
        

async def prepare_goal_changes(update, context, goal_id):
    try:
        # retrieve all goal data the user might want to adjust
        columns = "goal_description, status, recurrence_type, timeframe, goal_value, penalty, reminder_scheduled, reminder_time, deadline, deadlines"
        # template_required_columns = "goal_description, status, recurrence_type"
        rows_dictionary = await fetch_goal_data(goal_id, columns=columns)
        
        input_vars = await get_input_variables(update, context, goal_data=rows_dictionary)
        output = await run_chain("prepare_goal_changes", input_vars)
        
        parsed_output = UpdatedGoalData.model_validate(output)
        changes_summary = parsed_output.summary_of_changes
        
        if shared_state["transparant_mode"]:
            debug_message = await update.message.reply_text(f"Summary of changes the llm wants to make: \n{changes_summary}", parse_mode = "Markdown")
            await add_delete_button(update, context, debug_message.message_id)
            asyncio.create_task(delete_message(update, context, debug_message.message_id, 120))


        logger.info(f"here's the parsed output: {parsed_output}")


        # put everything in user context (clear first)
        if "goals" in context.user_data:
            # Remove the specific goal_id subkey if it exists
            context.user_data["goals"].pop(goal_id, None)
        await add_user_context_to_goals(context, goal_id, **parsed_output.model_dump())     # flattens the dictionary, to be accepted as **kwargs
        
        await send_goal_proposal(update, context, goal_id, adjust=True)

    except Exception as e:
        await update.message.reply_text(f"🚨 prepare_goal_changes:\n {e}")
        logger.error(f"\n\n🚨 prepare_goal_changes:\n {e}\n\n")


async def reminder_setting(update, context):
    try:
        input_vars = await get_input_variables(update, context)
        output = await run_chain("reminder_setting", input_vars)
        
        parsed_output = Reminder.model_validate(output)
        
        # Parse the time string into a datetime object
        reminder_time = parse(parsed_output.time)
        if reminder_time.tzinfo is None:
                reminder_time = reminder_time.replace(tzinfo=BERLIN_TZ)

        now = datetime.now(tz=BERLIN_TZ)
        if reminder_time.date() == now.date():
            logger.warning(f"reminder requested on the same day")
        
        if shared_state["transparant_mode"]:
            debug_message = await update.message.reply_text(f"Reminder setting result: \n{output}")
            await add_delete_button(update, context, debug_message.message_id)
            asyncio.create_task(delete_message(update, context, debug_message.message_id, 120))
        
        await record_reminder(update, context, output)
    
    except Exception as e:
        await update.message.reply_text(f"Error in reminder_setting():\n {e}")
        logger.error(f"\n\n🚨 Error in reminder_setting(): {e}\n\n")
        

async def other_message(update, context):
    try:
        input_vars = await get_input_variables(update, context)
        output = await run_chain("other", input_vars)
        
        parsed_output = Response.model_validate(output)
        response = parsed_output.response_text
        
        if shared_state["transparant_mode"]:
            debug_message = await update.message.reply_text(f"other_message_result: \n{output}")
            await add_delete_button(update, context, debug_message.message_id)
            asyncio.create_task(delete_message(update, context, debug_message.message_id, 120))

        other_message = await update.message.reply_text(response)
        await add_delete_button(update, context, other_message.message_id)
        
    except Exception as e:
        await update.message.reply_text(f"Error in other_message():\n {e}")
        logger.error(f"\n\n🚨 Error in other_message(): {e}\n\n")
        

async def other_message_pro(update, context):
    try:
        now = datetime.now(tz=BERLIN_TZ)
        weekday = now.strftime("%A") 
        user_message = get_user_message(update, context)
        await safe_set_reaction(context.bot, update.effective_chat.id, update.message.message_id, "💅")
        response_text = update.message.reply_to_message.text if update.message.reply_to_message else None

        if response_text:
            user_message = f"{user_message}\n\n(As a reply to message: {response_text})"
        
        response = client_EC.responses.create(
            model="gpt-5.2-pro",
            instructions=f"""
                It is currently: {weekday}, {now}. You are a virtual PA called Manon. A user in a Telegram group is sending you a message. It's your task to respond to it, be as glib and helpful as possible.
                Don't mince words, don't be nuanced, just give your best attempt at the most accurate and helpful response. No intro, no outro, no disclaimers. The user already knows that you're a chatbot and they should not take your words for truth.
                Always include a {PA} somewhere in your response. If you expect your response to be helpful to the user, also include a 🍌. If you think it's probavly medium-helpful, include a 🕳️. If you don't think it's helpful, include a 🍆.""",
            input=f"User message:\n{user_message}",
        )

        if shared_state["transparant_mode"]:
            debug_message = await update.message.reply_text(f"other_message_result: \n{response}")
            await add_delete_button(update, context, debug_message.message_id)
            asyncio.create_task(delete_message(update, context, debug_message.message_id, 120))

        response_message = response.output_text
        chunks = split_message(response_message)
        for i, chunk in enumerate(chunks):
            sent = await update.message.reply_text(chunk)
            await add_delete_button(update, context, sent.message_id)
        
    except Exception as e:
        await update.message.reply_text(f"Error in other_message_1():\n {e}")
        logger.error(f"\n\n🚨 Error in other_message_1(): {e}\n\n")
 