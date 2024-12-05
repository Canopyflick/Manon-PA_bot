from utils.helpers import is_ben_in_chat, notify_ben, datetime
from modules.openai_helpers import prepare_openai_messages, send_openai_request
from typing import Literal, List, Union
from pydantic import BaseModel, Field
import asyncio, logging
from telegram import Bot





triggers = ["SeintjeNatuurlijk", "OpenAICall"]

async def handle_triggers(update, context, trigger_text):
    if trigger_text == "SeintjeNatuurlijk":
        await update.message.reply_text("Ja hoor, hoi!")
        
    elif trigger_text == "OpenAICall":
        logic
        

# First orchestration: function to analyze any chat message and categorize it. Currently treats every kind of message the same, but prepared to treat replies, mentions and regular messages differently
async def analyze_message(update, context):
    if await is_ben_in_chat(update, context):
        try:
            user_message = update.message.text
            
            # Handle dice-roll
            if user_message.isdigit() and 1 <= int(user_message) <= 6:
                await roll_dice(update, context)
                logging.info("Message received: dice roll")
                return
            
            # Handle preset triggers
            for trigger_text in triggers:
                if trigger_text in user_message:
                    await handle_triggers(update, context, trigger_text)
                    logging.info(f"Message received: Trigger ({trigger_text})")
                    return
            
            # Handle all other messages
            regular_message = True
            if update.message.reply_to_message and update.message.reply_to_message.from_user.is_bot:
                logging.info("Message received: Bot Reply\n")
                regular_message = False       
            if update.message and '@TestManon_bot' in update.message.text or '@Manon_PA_bot' in update.message.text:
                logging.info("Message received: Bot Mention\n")
                regular_message = False          
            if regular_message:
                logging.info("Message received: Regular Message\n")
            await classification_initial(update, context, user_message)
        except Exception as e:
            await update.message.reply_text(f"Error in analyze_message():\n {e}")
            logging.error(f"\n\n🚨 Error in analyze_message(): {e}\n\n")   
    else: 
        await update.message.reply_text("Uhh, hoi... Stiekem ben ik een beetje verlegen. Praat met me in een chat waar Ben bij zit, pas dan voel ik me op mijn gemak 🧙‍♂️\n\n\nPS: je kunt hier wel allerhande boodschappen ter feedback achterlaten, dan geef ik die door aan Ben (#privacy). Denk bijvoorbeeld aan feature requests, kwinkslagen, knuffelbedreigingen, valsspeelbiechten, slaapzakberichten etc.\nPPS: Die laatste verzon ChatGPT. En ik quote: 'Een heel lang bericht, waarin je jezelf zou kunnen verliezen alsof je in een slaapzak kruipt.'")
        await notify_ben(update, context)
        return
    

async def classification_initial(update, context, user_message):
    chat_id=update.effective_chat.id
    message_id = update.message.message_id
    if len(user_message) > 1600:
        await update.message.reply_text(f"Hmpff... TL;DR pl0x? 🧙‍♂️\n(_{len(user_message)}_)", parse_mode="Markdown")
        return
    
    else:
        response_text = update.message.reply_to_message.text if update.message.reply_to_message else None

        try:
            # Prepare and send OpenAI messages
            class InitialClassification(BaseModel):
                English: bool
                reasoning: str
                classification: Literal['Goals', 'Reminders', 'Meta', 'Other']
                emoji_reaction: str
                
            messages = await prepare_openai_messages(
                update, 
                

                user_message, 
                message_type='classification_initial', 
                response=response_text
            )
        
            # Prepare and send OpenAI messages
            logging.info(messages)
            assistant_response = await send_openai_request(messages, temperature=0.3, model="gpt-4o-mini", response_format=InitialClassification)
            logging.info(f"classification_initial: {assistant_response}\n")
            english = assistant_response.English
            reaction = assistant_response.emoji_reaction

            await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=reaction)
            logging.critical(f"{chat_id}")
            if not english:
                reaction = "💯" 
                await handle_language_correction_message(update, context, user_message)
                await asyncio.sleep(4)
                await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=reaction)
                return
            else:
                initial_classification = assistant_response.classification
                if initial_classification == 'Goals':
                    reaction = "⚡" 
                    await handle_goals_message(update, context, user_message)
                    await asyncio.sleep(4)
                    await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=reaction)
                elif initial_classification == 'Other':
                    reaction = "🤔" 
                    await handle_other_message(update, context, user_message)
                    await asyncio.sleep(4)
                    await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=reaction)
                elif initial_classification == 'Reminders':
                    reaction = "🫡" 
                    await asyncio.sleep(4)
                    await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=reaction)
                elif initial_classification == 'Meta':
                    reaction = "👀" 
                    await asyncio.sleep(4)
                    await context.bot.setMessageReaction(chat_id=chat_id, message_id=message_id, reaction=reaction)
                    
        except Exception as e:
            await update.message.reply_text(f"Error in  classification_initial():\n {e}")
            logging.error(f"\n\n🚨 Error in  classification_initial(): {e}\n\n")   


async def handle_goals_message(update, context, user_message):
    try:
        # Prepare and send OpenAI messages
        class GoalsClassification1(BaseModel):
            reasoning: str
            classification: Literal['Set', 'Report_done', 'Report_failed', 'Postpone', 'Cancel', 'Pause', 'None']
            
        messages = await prepare_openai_messages(
            update, 
            user_message, 
            message_type='classification_goals_initial'
        )
        
        # Prepare and send OpenAI messages
        logging.info(messages)
        assistant_response = await send_openai_request(messages, temperature=0.3, model="gpt-4o-mini", response_format=GoalsClassification1)
        goals_classification = assistant_response.classification
        await update.message.reply_text(f"goals_classification: {goals_classification}")
        logging.info(f"classification_goals_initial: {assistant_response}\n")
        
        if goals_classification == 'Set':
            await handle_goals_set_message(update, context, user_message)
    except Exception as e:
        await update.message.reply_text(f"Error in handle_goals_message():\n {e}")
        logging.error(f"Error in handle_goals_message(): {e}")  
        
        
async def handle_goals_set_message(update, context, user_message, smarter=None):
    model = "gpt-4o-mini"
    if smarter:
        model = "gpt-4o"
    try:
        # Prepare and send OpenAI messages
        class GoalsClassification2(BaseModel):
            reasoning: str
            description: str
            goal_timeframe: Literal['today', 'by_date', 'open-ended']
            goal_category: List[Literal['productivity', 'work', 'chores', 'relationships', 'self-development', 'money', 'impact', 'health', 'fun', 'other']]
            goal_durability: Literal['one-time', 'recurring']
            
        messages = await prepare_openai_messages(
            update, 
            user_message, 
            message_type='classification_goals_setting'
        )
        
        # Prepare and send OpenAI messages
        logging.info(messages)
        assistant_response = await send_openai_request(messages, temperature=0.3, model=model, response_format=GoalsClassification2)
        logging.info(f"classification_goals_setting: {assistant_response}\n")
        reasoning = assistant_response.reasoning
        goal_timeframe = assistant_response.goal_timeframe
        description = assistant_response.description
        goal_category = assistant_response.goal_category
        goal_durability = assistant_response.goal_durability
        
        await update.message.reply_text(f"goals_setting: {description}\n{goal_timeframe}\n{goal_category}\n{goal_durability}\n({reasoning})")
        
        # Handle goals without deadline clue
        if goal_durability == 'open-ended':
            await update.message.reply_text(f"> prepare open-ended goal >)")
            return

        # Handle one-time goals with deadline clue
        if goal_durability == 'one-time' and (goal_timeframe == 'today' or goal_timeframe == 'by_date'):
            await get_goal_set_data(update, context, user_message, smarter, description=description, timeframe=goal_timeframe)
        
        # Handle recurring goals
        if goal_durability == 'recurring':
            await update.message.reply_text(f"_> ... splitting up recurring goal into its individual ones ... >_", parse_mode="Markdown")
            await get_goal_set_data(update, context, user_message, smarter, description=description, timeframe=goal_timeframe, durability='recurring')


    except Exception as e:
        await update.message.reply_text(f"Error in handle_goals_set_message():\n {e}")
        logging.error(f"Error in handle_goals_set_message(): {e}")  
    

        


async def get_goal_set_data(update, context, user_message, description, timeframe, durability="one-time", smarter=None):
    model = "gpt-4o-mini"
    if smarter:
        model = "gpt-4o"
        
    # Prepare output structures
    class GoalSetData(BaseModel):
        reasoning: str
        penalty: int
        deadline: str  # Use string instead of datetime for compatibility
        schedule_reminder: bool
        reminder_time: Union[str, None] = Field(
            default=None,
            description="The timestamp for the reminder in ISO 8601 format, or null if no reminder is scheduled."
        )
        time_investment_value: float
        effort_multiplier: float
        impact_multiplier: float
        
                
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
        effort_multiplier: float
        impact_multiplier: float
        penalty: int
        
    # Prepare messages and send OpenAI calls    
    try:
        if durability == "one-time":
            message_type = "goal_set_data"
            response_format = GoalSetData
        elif durability == "recurring":
            message_type = "recurring_goal_set_data"
            response_format = RecurringGoalSetData
        else:
            logging.error("Invalid durability in get_goal_set_data()")
            return

        messages = await prepare_openai_messages(update, user_message, message_type=message_type)
        logging.info(messages)

        assistant_response = await send_openai_request(
            messages, temperature=0.3, model=model, response_format=response_format
        )
        logging.info(f"{message_type}: {assistant_response}\n")
        penalty=assistant_response.penalty
        await update.message.reply_text(f"PENALTY: \n{penalty}\n")
        goal_value = round(
            assistant_response.time_investment_value
            * assistant_response.effort_multiplier
            * assistant_response.impact_multiplier,
            2
        )
        await update.message.reply_text(f"Calculated goal_value: {goal_value}")
        
        interval = None
        if durability == 'recurring':
            interval = assistant_response.interval
        await update.message.reply_text(f"INTERVAL: {interval}")
        
        from modules.goals import process_new_goal
        logging.info(f"going to process_new_goal() for {durability} goal(s)")
        await process_new_goal(update, context, user_message, description, timeframe, durability, assistant_response)
        
    except Exception as e:
        await update.message.reply_text(f"Error in get_goal_set_data() for {durability} goal:\n {e}")
        logging.error(f"Error in get_goal_set_data() for {durability} goal: {e}")


            
async def handle_language_correction_message(update, context, user_message):
    try:
        # Prepare and send OpenAI messages
        class LanguageCorrection(BaseModel):
            language: str
            corrected_text: str
            changes: str
            score: int
            
        messages = await prepare_openai_messages(
            update, 
            user_message, 
            message_type='language_correction'
        )
        
        # Prepare and send OpenAI messages
        logging.info(messages)
        assistant_response = await send_openai_request(messages, temperature=0.3, model="gpt-4o", response_format=LanguageCorrection)
        logging.info(f"language_correction: {assistant_response}\n")
        language = assistant_response.language
        corrected_text = assistant_response.corrected_text
        changes = assistant_response.changes
        score = assistant_response.score
        await update.message.reply_text(f"Language correction: {language}, level {score}")
        await update.message.reply_text(f"*{corrected_text}*", parse_mode="Markdown")
        await update.message.reply_text(f"{changes}")
    except Exception as e:
        await update.message.reply_text(f"Error in handle_language_correction_message():\n {e}")
        logging.error(f"Error in handle_language_correction_message(): {e}")  
        

async def handle_other_message(update, context, user_message):
     
    try:
        # Prepare and send OpenAI messages
        class HelpfulAnswer(BaseModel):
            tags: List[str]
            answer: str
            
        messages = await prepare_openai_messages(
            update, 
            user_message, 
            message_type='other'
        )
        
        # Prepare and send OpenAI messages
        logging.info(messages)
        assistant_response = await send_openai_request(messages, temperature=0.7, model="gpt-4o", response_format=HelpfulAnswer)
        logging.info(f"helpful answer: {assistant_response}\n")
        tags = assistant_response.tags
        answer = assistant_response.answer
        await update.message.reply_text(f"{tags}")
        await update.message.reply_text(f"*{answer}*", parse_mode="Markdown")
        
    except Exception as e:
        await update.message.reply_text(f"Error in handle_other_message():\n {e}")
        logging.error(f"Error in handle_other_message(): {e}")  
    


async def roll_dice(update, context):
    user_message = update.message.text
    chat_id = update.effective_chat.id

    try:
        # Send the dice and capture the message object
        dice_message = await context.bot.send_dice(
            chat_id,
            reply_to_message_id=update.message.message_id
        )

        # Extract the value that the user guessed
        user_guess = int(user_message)

        # Check the outcome of the dice roll
        rolled_value = dice_message.dice.value

        # Give a reply based on the rolled value
        await asyncio.sleep(4)
        if rolled_value == user_guess:
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text="🎊",
                reply_to_message_id=update.message.message_id
            )
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text="Correct :)",
                parse_mode="Markdown",
                reply_to_message_id=update.message.message_id
            )
        else:
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text="nope.",
                parse_mode="Markdown",
                reply_to_message_id=update.message.message_id
            )
    except Exception as e:
        logging.error(f"Error in roll_dice: {e}")


async def print_edit(update, context):
    logging.info("Someone edited a message")

