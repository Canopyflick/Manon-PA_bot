from utils.helpers import is_ben_in_chat, notify_ben
from modules.openai_helpers import prepare_openai_messages, send_openai_request
from typing import Literal
from pydantic import BaseModel
import asyncio, logging

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
    if len(user_message) > 1600:
        await update.message.reply_text(f"Hmpff... TL;DR pl0x? 🧙‍♂️")
        return
    
    else:
        response_text = update.message.reply_to_message.text if update.message.reply_to_message else None

        try:
            # Prepare and send OpenAI messages
            class Classificatie(BaseModel):
                English: bool
                reasoning: str
                classification: Literal['Goals', 'Reminders', 'Meta', 'Other']
            
            messages = await prepare_openai_messages(
                update, 
                user_message, 
                message_type='classification_initial', 
                response=response_text
            )
        
            # Prepare and send OpenAI messages
            logging.info(messages)
            assistant_response = await send_openai_request(messages, temperature=0.3, response_format=Classificatie)
            logging.info(f"classification_initial: {assistant_response}\n")
            classificatie_initial = assistant_response.classification
            reasoning = assistant_response.reasoning
            await update.message.reply_text(f"Initial classification: {classificatie_initial}\n({reasoning})")
    
        except Exception as e:
            await update.message.reply_text(f"Error in  classification_initial():\n {e}")
            logging.error(f"\n\n🚨 Error in  classification_initial(): {e}\n\n")   
            

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
                text="🎉",
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

