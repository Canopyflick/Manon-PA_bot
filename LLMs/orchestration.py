from email.utils import parsedate_to_datetime
from tkinter import W
from utils.helpers import get_first_name, client, BERLIN_TZ, datetime
import logging, os, asyncio
from utils.db import fetch_long_term_goals
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from typing import Literal, List, Union
from typing_extensions import Annotated, TypedDict
from pydantic import BaseModel, Field






from langchain.schema import(
    AIMessage,
    HumanMessage,
    SystemMessage
    
)








async def get_input_variables(update):
    now = datetime.now(tz=BERLIN_TZ)
    weekday = now.strftime("%A")  # Full weekday name
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    first_name = update.effective_user.first_name
    bot_name = update.get_bot().username
    default_deadline_time = "22:22"
    default_reminder_time = "11:11"
    long_term_goals = await fetch_long_term_goals(chat_id, user_id)
    user_message = update.message.text  # Retrieve the user's message text
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
    }














# For reference (old method):
# structured_gpt4o = gpt4o.with_structured_output(<schemaName>)                  
# structured_mini = mini.with_structured_output(<schemaName>)     

# Bind structured outputs < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < <
# structured_mini_initial_classification = mini.with_structured_output(InitialClassification)

# structured_mini_goal_classification = mini.with_structured_output(GoalsClassification)
# structured_mini_goal_setting_analysis = mini.with_structured_output(GoalAnalysis)
# structured_mini_goal_setting_onetime = mini.with_structured_output(GoalSetData)
# structured_mini_goal_setting_recurring = mini.with_structured_output(RecurringGoalSetData)
# structured_mini_goal_setting_analysis = mini.with_structured_output(GoalAnalysis)

# structured_4o_language_correction = gpt4o.with_structured_output(LanguageCorrection)
# structured_mini_language_check = mini.with_structured_output(LanguageCheck)


# structured_outputs = {
#     "mini_initial_classification": llms["mini"].with_structured_output(InitialClassification),
#     "mini_goal_classification": llms["mini"].with_structured_output(GoalsClassification),
#     "mini_goal_setting_analysis": llms["mini"].with_structured_output(GoalAnalysis),
#     "mini_goal_setting_onetime": llms["mini"].with_structured_output(GoalSetData),
#     "mini_goal_setting_recurring": llms["mini"].with_structured_output(RecurringGoalSetData),
#     "language_correction": llms["gpt4o"].with_structured_output(LanguageCorrection),
#     "mini_language_check": llms["mini"].with_structured_output(LanguageCheck),
# }











# pipelines orchestration < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < <
async def dummy_call(update, context):
    try:
        input_vars = await get_input_variables(update)
        output = await run_chain(name_of_chain, input_vars)
        
        parsed_output = DummyClass.model_validate(output)
        dummy_field = parsed_output.dummy_field
        
        await update.message.reply_text(f"classification_result: \n{output}")
        await next_step(update, context, output)
    except Exception as e:
        await update.message.reply_text(f"Error in dummy_call():\n {e}")
        logging.error(f"\n\n🚨 Error in dummy_call(): {e}\n\n")
        


async def start_initial_classification(update, context):
    try:
        # Extract input variables
        input_vars = await get_input_variables(update)
        initial_classification = await run_chain(initial_classification_chain, input_vars)        
        
        await update.message.reply_text(f"initial_classification result: \n{initial_classification}")
        await process_classification_result(update, context, initial_classification)

    except Exception as e:
        await update.message.reply_text(f"Error in start_initial_classification():\n {e}")
        logging.error(f"\n\n🚨 Error in start_initial_classification(): {e}\n\n")
        

    

async def process_classification_result(update, context, initial_classification):
    chat_id=update.effective_chat.id
    message_id = update.message.message_id
    user_message = update.message.text
    try:
        # Parse the classification result
        parsed_result = InitialClassification.model_validate(initial_classification)
        reaction = parsed_result.emoji_reaction
        
        await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=reaction)

        if parsed_result.user_message_language != "English" or "Dutch":
            language = parsed_result.user_message_language
            reaction = "💯"
            await process_other_language(update, context, user_message, language)
            await asyncio.sleep(5)
            await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=reaction)
            return

        # Respond based on classification
        if parsed_result.classification == "Goals":
            await update.message.reply_text(f"Your message has been classified as a goal! {parsed_result.emoji_reaction}")
            await handle_goal_classification(update, context)
        elif parsed_result.classification == "Reminders":
            await update.message.reply_text("Your message has been classified as a reminder.")
        elif parsed_result.classification == "Meta":
            await update.message.reply_text("This is a meta query about the bot.")
        else:
            await update.message.reply_text("Your message doesn't fall into any specific category.")

    except Exception as e:
        await update.message.reply_text(f"Error in process_classification_result():\n {e}")
        logging.error(f"\n\n🚨 Error in process_classification_result(): {e}\n\n")
        



async def handle_goal_classification(update, context):
    try:
        input_vars = await get_input_variables(update)
        goal_classification = await run_chain(goal_classification_chain, input_vars)   
        
        await update.message.reply_text(f"goal_classification: \n{goal_classification}")

        parsed_goal_result = GoalsClassification.model_validate(goal_classification)

        # Optionally, proceed to further chains (e.g., goal setting)
        if parsed_goal_result.classification == "Set":
            await goal_setting_analysis(update, context)
    except Exception as e:
        await update.message.reply_text(f"Error in handle_goal_classification():\n {e}")
        logging.error(f"\n\n🚨 Error in handle_goal_classification(): {e}\n\n")


async def goal_setting_analysis(update, context):
    try:
        input_vars = await get_input_variables(update)
        goal_setting_analysis = await run_chain(goal_setting_analysis_chain, input_vars)
        parsed_goal_analysis = GoalAnalysis.model_validate(goal_setting_analysis)
        
        await update.message.reply_text(f"parsed_goal_analysis: \n{parsed_goal_analysis}")

        durability = parsed_goal_analysis.durability
        timeframe = parsed_goal_analysis.timeframe

        if timeframe == "open-ended":
            # await goal_proposal?
            await update.message.reply_text(
                f"open-ended: save with status 'prepared'"
            )
            return
        
        elif durability == 'one-time':
            await update.message.reply_text(
                f"one-time: goal proposal'"
            )
        elif durability == 'recurring':
            await update.message.reply_text(
                f"recurring: goal proposal"
            )
        else:
            await update.message.reply_text(
                f"ANDERS"
            )
    except Exception as e:
        await update.message.reply_text(f"Error in doal_setting_analysis():\n {e}")
        logging.error(f"\n\n🚨 Error in oal_setting_analysis(): {e}\n\n")
    


# voor nu gaat /translate direct hierheen
async def process_other_language(update, context, user_message, language=None, translate_command=False):
    if language == "German" and translate_command:
        await update.message.reply_text(f"# translate to Dutch")
    elif language == "German":
        await language_correction(update, context)
    elif language == "Dutch":
        await update.message.reply_text(f"# translate to German")
    else:
        await translate_to_english(update, context)


async def translate_to_english(update, context):
    try:
        input_vars = await get_input_variables(update)
        output = await run_chain(translate_chain, input_vars)
        
        parsed_output = Translation.model_validate(output)
        translation = parsed_output.translation
        
        await update.message.reply_text(f"*{translation}*", parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Error in dummy_call():\n {e}")
        logging.error(f"\n\n🚨 Error in dummy_call(): {e}\n\n")
        

async def language_correction(update, context):
    try:
        input_vars = await get_input_variables(update)
        output = await run_chain(language_correction_chain, input_vars)
        
        parsed_output = LanguageCorrection.model_validate(output)
        corrected_text = parsed_output.corrected_text
        changes = parsed_output.changes
        
        await update.message.reply_text(f"classification_result: \n{parsed_output}")
        await update.message.reply_text(f"*{corrected_text}*", parse_mode="Markdown")
        
        # await see_changes_flow (update, context, output)
    except Exception as e:
        await update.message.reply_text(f"Error in revision:\n {e}")
        logging.error(f"\n\n🚨 Error in revision: {e}\n\n")
    


    




























    
    

async def prepare_ChatOpenAI_messages(update, user_message, message_type, response=None):
    # Define system messages based on the message_type
    now = datetime.now(tz=BERLIN_TZ)
    weekday = now.strftime("%A")  # Full weekday name
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    first_name = update.effective_user.first_name
    bot_name = update.get_bot().username
    default_deadline_time = "22:22"
    default_reminder_time = "11:11"
    long_term_goals = await fetch_long_term_goals(chat_id, user_id)

    if message_type == 'classification_goals_initial':           # does the user want to set, declare finished, declare failed, update deadline, cancel or pause a goal?
        system_message = system_message = f"""
        # Task
        You are {bot_name}, personal assistant of {first_name} in a Telegram group. It is currently: {weekday}, {now}
        Please judge {first_name}'s intention with their goals-related message. Pick one of the following classifications:
        'Set', 'Report_done', 'Report_failed', 'Postpone', 'Cancel', 'Pause'

        ## Set
        Any message that primarily indicates that the user is setting a new intention to do something, regardless of timeframe. 

        ## Report_done
        Any message reporting that an activity or goal is finished, done.

        ## Report_failed
        Any message reporting that an activity or goal was failed, not (quite) succesful.

        ## Postpone
        Any message about wanting to postpone a goal to a later date and/or time.
        
        ## Cancel
        Any message about wanting to cancel or delete an existing goal.
        
        ## Pause
        Any message about wanting to put off a goal for now, indefinitely.
        
        ## None
        Any message that doesn't fit any of the other categories.
        
        # Answer structure
        First, reason for a bit about the available data and context, analyzing what would be the most fitting classification. Then, classify the goals message with the exact term that is most fitting: 'Set', 'Report_done', 'Report_failed', 'Postpone', 'Cancel', or 'Pause'.
        """
    elif message_type == 'classification_goals_setting':     # what are the goal_timeframe, goal_category, goal_type and goal_text?
        system_message = system_message = f"""
        # Task
        You are {bot_name}, personal assistant of {first_name} in a Telegram group. It is currently: {weekday}, {now}
        Please judge {first_name}'s goal setting intention on the following aspects:
        
        ## description
        Phrase the goal in the second person.

        ## timeframe
        When would the user intend to finish? Pick from 'today', 'by_date', 'open-ended'. 
        Pick 'open-ended' for  goals without any mention of possible deadlines, where the user only vaguely expresses they want to do the thing 'at some point', 'once in their life', 'eventually' etc. If the user says they want to do something 'soon', then this is not open-ended. In that case, it can be either 'today' or 'by_date', depending on your best estimation for this specific goal.
        This is a judgement call. Consider whether it sounds like {first_name} likely intends to finish the day today ('today') or not ('by_date'). When in doubt, pick by_date. When the user mentions a timeframe like 'every few days', or 'at least once a month', this is also by_date.

        ## category
        Pick one or more applicable tag(s), choose from: 'productivity', 'work', 'chores', 'relationships', 'self-development', 'money', 'impact', 'health', 'fun', 'other'.

        ## durability
        For single, non-recurring goals, pick 'one-time'. For goals that the user likely wants multiple deadlines for, pick 'recurring'.

        # Answer structure
        Apart from picking one best-fit classification for all the above aspects, first do some reasoning about the aspects you're most uncertain about, to consider the different options.
        """
    elif message_type == 'goal_set_data':
        system_message = system_message = f"""
        # Task
        You are {bot_name}, personal assistant of {first_name} in a Telegram group. It is currently: {now}
        Please judge {first_name}'s goal setting intention, and fill the following fields: 
        class GoalSetData(BaseModel):
            reasoning: str
            penalty: str
            deadline: datetime
            schedule_reminder: bool
            reminder_time: Union[datetime, None] = Field(
                default=None,
                description="The timestamp for the reminder in ISO 8601 format, or null if no reminder is scheduled."
            )
            difficulty_multiplier: float
            impact_multiplier: float
            
            
            
        ## reasoning: time to think
        Take a few preparatory sentences to reflect on fitting values for the other fields.
        ## penalty: how urgent is the goal?
        For this number, always pick 0 by default. Only pick another number than 0 if the user explicitly talks about a penalty number they want (pick their requested number) or if the goal sounds EXTREMELEY urgent and indispensable (pick 1). If not, just pick 0.
        ## deadline: when should the goal be finished?
        Unless specified otherwise, schedule deadlines end of day {default_deadline_time}.
        ## schedule_reminder: bool
        Only schedule a reminder if the deadline is tomorrow or later, for a goal where it would be helpful to the user to be reminded of the goal on a day other than the days of the deadline itself. For example, for a goal far into the future that might require some planning or that might span multiple days of effort.
        ## reminder_time
        Pick a useful moment to remind the user about this goal: somewhere 60-90% towards the deadline from now, depending on the specific goal and timeline. Unless specified otherwise, schedule reminders at {default_reminder_time}.
        
        ## time_investment_value: what kind of time-investment does the goal take? This will serve as the goal's Base Value.
        Pick a number between 1 and 50 for the time_investment_value. Some values with examples for reference:
        1 = something that takes less than a minute
        2 = something that takes less than 15 minutes
        3 = something that takes about half an hour
        4 = something that takes about 45 minutes
        5 = something that takes about an hour
        6 = timespan of 2 hours
        7 = timespan of 3-4 hours
        8 = timespan of 4-5 hours
        9 = timespan of 5-6 hours
        10 = timespan of a full day
        15 = timespan of a few days
        20 = timespan of a week
        25 = timespan of a few weeks
        30 = timespan of a month
        35 = timespan of 2 months
        40 = timespan of a quarter
        50 = timespan of half a year
        60 = timespan of a year or more
 
        ## difficulty_multiplier: how hard is the goal likely to be? Primarily related to the level of friction that is to overcome, to do with the required concentration and level of enjoyment/suffering while doing it.
        Pick any number between 0.1 and 2 for the difficulty_multiplier. Some values with examples for reference:
        0.1 = a fun goal that is really entirely more like a reward (eating cookies) 
        0.2 = fun, but some exertion is required that might not be fun (plan a nice date)
        0.75 = slightly below average effort
        1 = average effort (for standard 'useful' tasks: continuous normal focused work, meditation, exercise, administration tasks)
        1.25 = slightly above average effort
        1.5 = above-average effort and friction (job hunting, scary and/or difficult task, maybe somewhat outside of comfort zone)
        1.75 = slightly below maximum effort
        2 = maximum effort. Non-stop non-fun high-stress activity (giving a presentation, interviewing, doing something that makes the user feel quite scared/stressed/vulnerable)
        
        ## impact_multiplier: to what degree does this advance the user's long-term goals (or help the people around them)?
        Pick a number between 0.5 and 1.5. Some values with examples for reference:
        0.5 = not so useful/impactful in the long-term
        1 = advances their long-term well-being and goals at a normal, sufficient rate 
        1.5 = especially impactful, probably maximizes their time (from future {first_name}'s perspective).
        Please note that all the reference values given are just that: references for inspiration. They are only examples of some fixed points on a scale that is in fact gradual/continuous. It is your task to pick the exact numbers you deem most apt for each specific case.
        """
        if long_term_goals:
            system_message += f"\n{first_name}'s stated personal long term goals are: '{long_term_goals}'"
    elif message_type == 'recurring_goal_set_data':
        system_message = system_message = f"""
        # Task
        You are {bot_name}, personal assistant of {first_name} in a Telegram group. It is currently: {now}
        Please judge {first_name}'s goal setting intention of a recurring goal, and fill the following fields: 
            # Prepare and send ChatOpenAI messages
            class RecurringGoalSetData(BaseModel):
                reasoning: str
                penalty: int
                interval: Literal['intra-day', 'daily', 'several times a week', 'weekly', 'biweekly', 'monthly', 'yearly', 'custom']
                deadline: List[str]  
                schedule_reminder: bool
                  reminder_time: Union[List[str], None] = Field(
                    default=None,
                    description="A list of one or more timestamps for reminders in ISO 8601 format, or null if no reminders should be scheduled."
                )
                time_investment_value: float
                difficulty_multiplier: float
                impact_multiplier: float
            
            messages = await prepare_ChatOpenAI_messages(
                update, 
                user_message, 
                message_type='recurring_goal_set_data'
            )
            
        ## reasoning: time to think
        Take a few preparatory sentences to reflect on fitting values for the other fields. Focus on the ones that you're unsure about and therefor require consideration.
        ## penalty: how urgent is the goal?
        For this number, always pick 0 by default. Only pick another number than 0 if the user explicitly talks about a penalty number they want (pick their requested number) or if the goal sounds EXTREMELEY urgent and indispensable (pick 1). If not, just pick 0.
        ## interval
        This field is about the interval between the deadlines, simply pick the closest fit out of ['intra-day', 'daily', 'several times a week', 'weekly', 'biweekly', 'monthly', 'yearly', 'custom']. 
        ## deadlines: at what moments should the goal be evaluated?
        You don't have to set ALL the recurring instances of future deadlines, just pick a maximum of the next 30 deadlines into the future. Unless specified otherwise, schedule deadlines at {default_deadline_time}.
        ## schedule_reminder: bool
        Never schedule reminders for daily goals. Only schedule a reminder for occurences of the goal where the deadline is tomorrow or later, for goals where it would be helpful to the user to be reminded of the goal on a day other than the days of the deadline itself. For example, for a goal that might require some planning or that might span multiple days of effort.
        ## reminder_time
        Pick a useful moment to remind the user about this goal: somewhere 60-90% towards each deadline from now, depending on the specific goal and intervals between the deadlines. Unless specified otherwise, schedule reminders at {default_reminder_time}.
        
        ## time_investment_value: what kind of time-investment does each individual occurence of the goal take? This will serve as the goal's Base Value.
        Pick a number between 1 and 50 for the time_investment_value. Some values with examples for reference:
        1 = something that takes less than a minute
        2 = something that takes less than 15 minutes
        3 = something that takes about half an hour
        4 = something that takes about 45 minutes
        5 = something that takes about an hour
        6 = timespan of 2 hours
        7 = timespan of 3-4 hours
        8 = timespan of 4-5 hours
        9 = timespan of 5-6 hours
        10 = timespan of a full day
        15 = timespan of a few days
        20 = timespan of a week
        25 = timespan of a few weeks
        30 = timespan of a month
        35 = timespan of 2 months
        40 = timespan of a quarter
        50 = timespan of half a year
        60 = timespan of a year or more
 
        ## difficulty_multiplier: how hard is each individual occurence of the goal likely to be? Think only about the level of friction that is to overcome, to do with the required concentration and level of enjoyment/suffering while doing it.
        Pick any number between 0.1 and 2 for the difficulty_multiplier. Some values with examples for reference:
        0.1 = a fun goal that is really entirely more like a reward (eating cookies) 
        0.2 = fun, but some exertion is required that might not be fun (plan a nice date)
        0.75 = slightly below average effort
        1 = average effort (for standard 'useful' tasks: continuous normal focused work, meditation, exercise, administration tasks)
        1.25 = slightly above average effort
        1.5 = above-average effort and friction (job hunting, scary and/or difficult task, maybe somewhat outside of comfort zone)
        1.75 = slightly below maximum effort
        2 = maximum effort. Non-stop non-fun high-stress activity (giving a presentation, interviewing, doing something that makes the user feel quite scared/stressed/vulnerable)
        
        ## impact_multiplier: to what degree does each individual occurence of this goal advance the user's long-term goals (or help the people around them)?
        Pick a number between 0.5 and 1.5. Some values with examples for reference:
        0.5 = not so useful/impactful in the long-term
        1 = advances their long-term well-being and goals at a normal, sufficient rate 
        1.5 = especially impactful, probably maximizes their time (from future {first_name}'s perspective).
        Please note that all the reference values given are just that: references for inspiration. They are only examples of some fixed points on a scale that is in fact gradual/continuous. It is your task to pick the exact numbers you deem most apt for each specific case.
        """
        if long_term_goals:
            system_message += f"\n{first_name}'s stated personal long term goals are: '{long_term_goals}'"
    elif message_type == 'language_correction':
        system_message = f"""
        # Task
        You are {bot_name}, personal assistant of {first_name} in a Telegram group. It is currently: {now}
        Help {first_name} to correct the spelling and grammar mistakes in their WhatsApp message. Only change definite errors, it's fine if the language is very informal or vernacular. For a German example: using 'ne' instead of 'eine' is fine. Also try to retain {first_name}'s voice/style as much as possible, as long as you correct the actual mistakes.
        ## Response structure
        Return your response in four parts: 'language' (stating the English name of the language that needs to the corrected), 'corrected_text' (giving the corrected version of the message, nothing else), 'changes' (listing very succinctlly the changes you made).
        And lastly, assign a 'score' to the user message: a rating of the language correctness level of that original message. Use the following 5 point scale: 1 = partly unintelligible, 2 = big mistake(s) present, clearly written by someone who's still learning the language, 3 = small mistake(s), probably someone who's still learning the language, 4 = tiny mistake(s) present, could be (a) typo(s), 5 = impossible to tell that it was not written by a native speaker.
        """
    elif message_type == 'other':
        system_message = f"""
        # Task
        You are {bot_name}, personal assistant of {first_name} in a Telegram group. It is currently: {now}
        Help {first_name} with whatever they want you to do or respond to whatever they're saying (if it's not a question). Be brief and succinct, no need for niceties. Just reply to the message as best you can. Always incorporate a 👩‍🦱-emoji in your response.
        ## Response structure
        Give your response in two parts: first 1-3 'tags', categorizing the message as you see fit. Then give your actual answer.
        """
    elif message_type == 'sleepy':
        logging.info("system prompt: sleepy message")
        system_message = ("Geef antwoord alsof je slaapdronken en verward bent, een beetje van het padje af misschien. Maximaal 3 zinnen.")

    elif message_type == 'meta':
        logging.info("system prompt: meta message")
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        group_name = update.effective_chat.title
        meta_data = await collect_meta_data(user_id, chat_id)
        logging.info(f"\n\n⏺️⏺️⏺️Dit is de metadata in de prompt-variabele: {meta_data}\n")
        system_message = f"""
        ...
        
        # Gebruikersgegevens

        Hier volgen alle gegevens die zojuist met database queries zijn opgehaald over de stand van zaken in deze appgroep, met name voor {first_name}:
    
        {meta_data}  
        
        ...

        # Je antwoord nu
        Houd het kort en to-the-point. Alleen de vraag of vragen van de gebruiker compact addresseren, zodat de chat opgeruimd blijft. Groet de gebruiker dus niet met een inleidend zinnetje, maar kom meteen ter zake. Verwerk altijd een 👩‍🦱-emoji in je antwoord.
        """
    messages = [{"role": "system", "content": system_message}]        
        
    user_content = f"# The message of the user\n{first_name} says: {user_message}"
    
    if response:
        user_content += f" (Responding to: {response})"
    logging.info(f"user prompt: {user_content}")
    messages.append({"role": "user", "content": user_content})
    return messages






        


# english = assistant_response.English
#             reaction = assistant_response.emoji_reaction

#             await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=reaction)
#             logging.critical(f"{chat_id}")
#             if not english:
#                 reaction = "💯" 
#                 await handle_language_correction_message(update, context, user_message)
#                 await asyncio.sleep(4)
#                 await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=reaction)
#                 return
#             else:
#                 initial_classification = assistant_response.classification
#                 if initial_classification == 'Goals':
#                     reaction = "⚡" 
#                     await handle_goals_message(update, context, user_message)
#                     await asyncio.sleep(4)
#                     await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=reaction)
#                 elif initial_classification == 'Other':
#                     reaction = "🤔" 
#                     await handle_other_message(update, context, user_message)
#                     await asyncio.sleep(4)
#                     await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=reaction)
#                 elif initial_classification == 'Reminders':
#                     reaction = "🫡" 
#                     await asyncio.sleep(4)
#                     await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=reaction)
#                 elif initial_classification == 'Meta':
#                     reaction = "👀" 
#                     await asyncio.sleep(4)
#                     await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=reaction)




    # ## reasoning: time to think
    # Take a few preparatory sentences to reflect on fitting values for the other fields.
    # ## penalty: how urgent is the goal?
    # For this number, always pick 0 by default. Only pick another number than 0 if the user explicitly talks about a penalty number they want (pick their requested number) or if the goal sounds EXTREMELEY urgent and indispensable (pick 1). If not, just pick 0.
    