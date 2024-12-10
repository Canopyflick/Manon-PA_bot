from re import A
from utils.helpers import BERLIN_TZ, datetime, timedelta, add_user_context_to_goals, PA, add_delete_button
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from modules.goals import send_goal_proposal
import logging, os, asyncio
from utils.db import (
    fetch_long_term_goals,
    update_goal_data,
    create_limbo_goal,
    complete_limbo_goal,
)
from LLMs.config import chains
from langchain.memory import ConversationBufferMemory
from LLMs.classes import (
    DummyClass,
    InitialClassification,
    GoalClassification,
    SetGoalAnalysis,
    GoalSetData,
    LanguageCorrection,
    LanguageCheck,
    Translation,
    Schedule,
    Planning,
    GoalAssessment,
    GoalInstanceAssessment,
)

#########################################################################
import unicodedata

def log_emoji_details(emoji, source="Unknown"):
    print(f"Source: {source}")
    print(f"Emoji: {emoji}")
    print(f"Unicode representation: {emoji.encode('unicode_escape')}")
    print(f"Name: {unicodedata.name(emoji, 'Unknown')}")
    print(f"Length: {len(emoji)}")
    print("-" * 40)
#########################################################################    



async def get_input_variables(update, source_text=None, target_language="English"):
    now = datetime.now(tz=BERLIN_TZ)
    weekday = now.strftime("%A")  # Full weekday name
    tomorrow = (now + timedelta(days=1)).strftime("%A")
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    first_name = update.effective_user.first_name
    bot_name = update.get_bot().username
    default_deadline_time = "22:22"
    default_reminder_time = "11:11"
    long_term_goals = await fetch_long_term_goals(chat_id, user_id)
    user_message = source_text if source_text else update.message.text
    response_text = update.message.reply_to_message.text if update.message.reply_to_message else None
    
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
        logging.info(f"Chain '{chain_name}' executed successfully: {result}")
        return result

    except KeyError as e:
        logging.error(f"Chain is missing a required key: {e}")
        raise ValueError(f"Invalid chain structure: missing {e}")

    except Exception as e:
        logging.error(f"Error running chain: {e}")
        raise RuntimeError(f"Failed to execute chain: {e}")



# pipelines orchestration < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < <
async def dummy_call(update, context):
    try:
        input_vars = await get_input_variables(update)
        output = await run_chain(name_of_chain, input_vars)
        
        parsed_output = DummyClass.model_validate(output)
        dummy_field = parsed_output.dummy_field
        
        await update.message.reply_text(f"classification_result: \n{output}")
        
        if dummy_field == "something in particular":
            await next_step(update, context, output)
        else: 
            await update.message.reply_text(f"_Next step for {dummy_field} not yet implemented_", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error in dummy_call():\n {e}")
        logging.error(f"\n\n🚨 Error in dummy_call(): {e}\n\n")
        


async def start_initial_classification(update, context):
    try:
        # Extract input variables
        input_vars = await get_input_variables(update)
        initial_classification = await run_chain("initial_classification", input_vars)        
        
        await update.message.reply_text(f"initial_classification result: \n{initial_classification}")
        await process_classification_result(update, context, initial_classification)

    except Exception as e:
        await update.message.reply_text(f"Error in start_initial_classification():\n {e}")
        logging.error(f"\n\n🚨 Error in start_initial_classification(): {e}\n\n")
    

async def process_classification_result(update, context, initial_classification):
    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    user_message = update.message.text
    try:
        # Parse the classification result
        parsed_result = InitialClassification.model_validate(initial_classification)
        # later_reaction = parsed_result.emoji_reaction (deleted this, cause buggy)
        language = parsed_result.user_message_language

        # log_emoji_details(later_reaction, "gpt-4o-mini")

        if language != "English" and language != "Dutch":
            preset_reaction = "💯"
            await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=preset_reaction)
            await process_other_language(update, context, user_message, language)
            # await asyncio.sleep(5)
            # await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=later_reaction)
            return

        initial_classification = parsed_result.classification
        # Respond based on classification
        if initial_classification == "Goals":
            preset_reaction = "⚡"
            await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=preset_reaction)
            await handle_goal_classification(update, context)             # < < < < <
            # await asyncio.sleep(5)
            # await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=later_reaction)
        elif initial_classification == "Reminders":
            preset_reaction = "🫡"
            await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=preset_reaction)
            await update.message.reply_text("Your message has been classified as a reminder.")                                  # < < < < <
            # await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=later_reaction)
        elif initial_classification == "Meta":
            preset_reaction = "💩"
            await update.message.reply_text("This is a meta query about the bot.")                                              # < < < < <
            # await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=later_reaction)
        else:
            preset_reaction = "😘"
            await update.message.reply_text("Your message doesn't fall into any specific category.")                            # < < < < <
            # await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=later_reaction)

    except Exception as e:
        await update.message.reply_text(f"Error in process_classification_result():\n {e}")
        logging.error(f"\n\n🚨 Error in process_classification_result(): {e}\n\n")
        

async def handle_goal_classification(update, context):
    try:
        input_vars = await get_input_variables(update)
        goal_classification = await run_chain("goal_classification", input_vars)   
        
        parsed_goal_classification = GoalClassification.model_validate(goal_classification)
        await update.message.reply_text(f"goal_classification: \n{parsed_goal_classification}")
        
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
            
            await goal_setting_analysis(update, context, goal_id)                                                                        # < < < < <
            
        else: 
            await update.message.reply_text(f"_goal_result {goal_result} not yet implemented_", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error in handle_goal_classification():\n {e}")
        logging.error(f"\n\n🚨 Error in handle_goal_classification(): {e}\n\n")


async def goal_setting_analysis(update, context, goal_id):
    try:
        input_vars = await get_input_variables(update)
        goal_setting_analysis = await run_chain("goal_setting_analysis", input_vars)
        parsed_goal_analysis = SetGoalAnalysis.model_validate(goal_setting_analysis)
        
        await update.message.reply_text(f"parsed_goal_analysis: \n{parsed_goal_analysis}")

        evaluation_frequency = parsed_goal_analysis.evaluation_frequency
        timeframe = parsed_goal_analysis.timeframe
        goal_category = parsed_goal_analysis.category
        
        await add_user_context_to_goals(
            context,
            goal_id,
            goal_recurrence_type=evaluation_frequency,
            goal_timeframe=timeframe,
            goal_category=goal_category
        )

        if timeframe == "open-ended":
            # await goal_proposal?
            await update.message.reply_text(
                f"Next step for open-ended: save with status 'prepared'"
            )
            return
        
        elif evaluation_frequency == 'one-time':
            await goal_valuation(update, context, goal_id)
        elif evaluation_frequency == 'recurring':
            await goal_valuation(update, context, goal_id, "recurring")
        else:
            await update.message.reply_text(
                f"Next step for ANDERS: ???"
            )
    except Exception as e:
        await update.message.reply_text(f"Error in goal_setting_analysis():\n {e}")
        logging.error(f"\n\n🚨 Error in goal_setting_analysis(): {e}\n\n")
        

async def goal_valuation(update, context, goal_id, frequency="one-time"):
    try:
        input_vars = await get_input_variables(update)
        parsed_goal_valuation = None
        if frequency == 'recurring':
            await update.message.reply_text(f"complete recurring in goal_valuation")
            goal_valuation = await run_chain("recurring_goal_valuation", input_vars)
            parsed_goal_valuation = GoalInstanceAssessment.model_validate(goal_valuation)
        elif frequency == 'one-time':
            goal_valuation = await run_chain("goal_valuation", input_vars)
            parsed_goal_valuation = GoalAssessment.model_validate(goal_valuation)
            
        await update.message.reply_text(f"goal_valuation: \n{parsed_goal_valuation}")
        
        await add_user_context_to_goals(
            context,
            goal_id,
            parsed_goal_valuation=parsed_goal_valuation,
        )

        await prepare_goal_proposal(update, context, goal_id, frequency=frequency)
        
    except Exception as e:
        await update.message.reply_text(f"Error in goal_valuation():\n {e}")
        logging.error(f"\n\n🚨 Error in goal_valuation(): {e}\n\n")
        

async def prepare_goal_proposal(update, context, goal_id, frequency):
    try:
        input_vars = await get_input_variables(update)
        parsed_planning = None
        if frequency == 'recurring':
            output = await run_chain("schedule_goals", input_vars)        
            parsed_planning = Planning.model_validate(output)
        elif frequency == 'one-time':
            output = await run_chain("schedule_goal", input_vars)
            parsed_planning = Schedule.model_validate(output)

        await update.message.reply_text(f"prepare_goal_proposal: \n{parsed_planning}", parse_mode="markdown")  
        
        await add_user_context_to_goals(
            context,
            goal_id,
            description=parsed_planning.description,
            parsed_planning=parsed_planning
        )
        
        await send_goal_proposal(update, context, goal_id)
            
    except Exception as e:
        await update.message.reply_text(f"Error in prepare_goal_proposal():\n {e}")
        logging.error(f"\n\n🚨 Error in prepare_goal_proposal(): {e}\n\n")
    




# voor nu gaat /translate direct hierheen
async def process_other_language(update, context, user_message, language=None, translate_command=False):
    if language == "German" and translate_command:
        await update.message.reply_text(f"# translate to Dutch")
        await translate(update, context, source_text=user_message, target_language='Dutch')
    elif language == "German":
        await language_correction(update, context)
    elif language == "Dutch":
        logging.info(f"Dutch jatog")
        # await update.message.reply_text(f"# translate to German")     # Just process as any other message
    else:
        await translate(update, context, source_text=user_message)      # translate to German


async def translate(update, context, source_text, target_language="German"):
    try:
        input_vars = await get_input_variables(update, source_text, target_language)
        output = await run_chain("translation", input_vars)
        
        parsed_output = Translation.model_validate(output)
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

    except Exception as e:
        await update.message.reply_text(f"Error in translate():\n {e}")
        logging.error(f"\n\n🚨 Error in translate(): {e}\n\n")
        

async def language_correction(update, context):
    try:
        input_vars = await get_input_variables(update)
        output = await run_chain("language_correction", input_vars)
        
        parsed_output = LanguageCorrection.model_validate(output)
        corrected_text = parsed_output.corrected_text
        changes = parsed_output.changes
        
        await update.message.reply_text(f"classification_result: \n{parsed_output}")
        await update.message.reply_text(f"*{corrected_text}*", parse_mode="Markdown")
        
        # await see_changes_flow (update, context, output)
    except Exception as e:
        await update.message.reply_text(f"Error in revision:\n {e}")
        logging.error(f"\n\n🚨 Error in revision: {e}\n\n")
        

