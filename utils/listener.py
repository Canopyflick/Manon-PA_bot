﻿from utils.helpers import is_ben_in_chat, notify_ben, datetime, test_emojis_with_telegram, emoji_stopwatch, send_user_context, PA
from LLMs.orchestration import start_initial_classification # prepare_openai_messages, send_openai_request, 
from typing import Literal, List, Union
import asyncio, logging
from telegram import Bot






triggers = ["SeintjeNatuurlijk", "OpenAICall", "Emoji", "Stopwatch", "usercontext", "clearcontext", "koffie", "coffee", "!test", "pomodoro"]

async def handle_triggers(update, context, trigger_text):
    if trigger_text == "SeintjeNatuurlijk":
        await update.message.reply_text("Ja hoor, hoi!")
    elif trigger_text == "Emoji":
        await test_emojis_with_telegram(update, context)
    elif trigger_text == "Stopwatch":
        await emoji_stopwatch(update, context)
    elif trigger_text == 'pomodoro':
        await emoji_stopwatch(update, context, mode="pomodoro")
    elif trigger_text == "koffie" or trigger_text == "coffee":
        await emoji_stopwatch(update, context, mode="coffee")
    elif trigger_text == "!test":
        await emoji_stopwatch(update, context, mode="test")
    elif trigger_text == "OpenAICall":
        print (f"nothing implemented yet")
    elif trigger_text == "usercontext":
        await send_user_context(update, context)
    elif trigger_text == "clearcontext":
        context.user_data.clear()



        

# First orchestration: function to analyze any chat message and categorize it. Currently treats every kind of message the same, but prepared to treat replies, mentions and regular messages differently
async def analyze_any_message(update, context):
    if not await is_ben_in_chat(update, context):
        await update.message.reply_text("Uhh, hoi... Stiekem ben ik een beetje verlegen. Praat met me in een chat waar Ben bij zit, pas dan voel ik me op mijn gemak 🧙‍♂️\n\n\nPS: je kunt hier wel allerhande boodschappen ter feedback achterlaten, dan geef ik die door aan Ben (#privacy). Denk bijvoorbeeld aan feature requests, kwinkslagen, knuffelbedreigingen, valsspeelbiechten, slaapzakberichten etc.\nPPS: Die laatste verzon ChatGPT. En ik quote: 'Een heel lang bericht, waarin je jezelf zou kunnen verliezen alsof je in een slaapzak kruipt.'")
        await notify_ben(update, context)
        return
    else:
        try:
            user_message = update.message.text
            
            # Reject longs messages
            if len(user_message) > 1600:
                await update.message.reply_text(f"Hmpff... TL;DR pl0x? 🧙‍♂️\n(_{len(user_message)}_)", parse_mode="Markdown")
                return
            
            # Handle dice-roll
            if user_message.isdigit() and 1 <= int(user_message) <= 6:
                await roll_dice(update, context)
                logging.info("Message received: dice roll")
                return
            
            # Handle preset triggers
            for trigger_text in triggers:
                user_message = user_message.lower()
                if trigger_text.lower() == user_message:
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
                
            await start_initial_classification(update, context)     # <<<
            
        except Exception as e:
            logging.error(f"\n\n🚨 Error in analyze_any_message(): {e}\n\n")
            await update.message.reply_text(f"Error in analyze_any_message():\n {e}")


    









    


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

