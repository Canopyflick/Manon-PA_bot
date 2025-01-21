from utils.helpers import delete_message, is_ben_in_chat, notify_ben, datetime, test_emojis_with_telegram, emoji_stopwatch, send_user_context, PA, delete_message
from LLMs.orchestration import start_initial_classification
from typing import Literal, List, Union
import asyncio, logging, subprocess, re
from telegram import Bot, MessageEntity
from telegram.ext import CallbackContext
from utils.scheduler import send_evening_message, send_morning_message, fail_goals_warning
from utils.helpers import fetch_logs
from modules.stats_manager import StatsManager
from LLMs.config import shared_state

triggers = ["SeintjeNatuurlijk", "OpenAICall", "Emoji", "Stopwatch", "usercontext", "clearcontext", 
            "koffie", "coffee", "!test", "pomodoro", "tea", "gm", "gn", "resolve", "dailystats", 
            "logs", "logs100", "errorlogs", "transparant_on", "transparant_off"]

async def handle_triggers(update, context, trigger_text):    
    if trigger_text == "SeintjeNatuurlijk":
        await update.message.reply_text(f"Ja hoor, hoi! {PA}")
    elif trigger_text == "Emoji":
        await test_emojis_with_telegram(update, context)
    elif trigger_text == "Stopwatch":
        await emoji_stopwatch(update, context)
    elif trigger_text == 'pomodoro':
        await emoji_stopwatch(update, context, mode="pomodoro")
    elif trigger_text == "koffie" or trigger_text == "coffee":
        await emoji_stopwatch(update, context, mode="coffee")
    elif trigger_text == "tea":
        await emoji_stopwatch(update, context, mode="tea_long")
    elif trigger_text == "!test":
        await emoji_stopwatch(update, context, mode="test")
    elif trigger_text == "OpenAICall":
        print (f"nothing implemented yet")
    elif trigger_text == "usercontext":
        await send_user_context(update, context)
    elif trigger_text == "clearcontext":
        context.user_data.clear()
        await context.bot.setMessageReaction(chat_id=update.effective_chat.id, message_id=update.message.message_id, reaction="🫡")
    elif trigger_text == "gm":    
        bot=context.bot
        chat_id=update.message.chat_id
        await send_morning_message(bot, specific_chat_id=chat_id)
    elif trigger_text == "gn":    
        bot=context.bot
        chat_id=update.message.chat_id
        await send_evening_message(bot, specific_chat_id=chat_id)
    elif trigger_text == "resolve":    
        bot=context.bot
        chat_id=update.message.chat_id
        await fail_goals_warning(bot, chat_id=chat_id)
    elif trigger_text == "dailystats":    
        bot=context.bot
        chat_id=update.message.chat_id
        await context.bot.setMessageReaction(chat_id=update.effective_chat.id, message_id=update.message.message_id, reaction="👍")
        await StatsManager.update_daily_stats(specific_chat_id=chat_id)
    elif re.match(r"^logs\d+$", trigger_text):  # Match logs followed by digits
        num_lines = int(trigger_text[4:])  # Extract the number after 'logs'
        await context.bot.setMessageReaction(chat_id=update.effective_chat.id, message_id=update.message.message_id, reaction="👍")
        await fetch_logs(update, context, abs(num_lines))  # Ensure the number is positive
    elif trigger_text == "logs":
        await context.bot.setMessageReaction(chat_id=update.effective_chat.id, message_id=update.message.message_id, reaction="👍")
        await fetch_logs(update, context, 6)
    elif trigger_text == "errorlogs":
        await context.bot.setMessageReaction(chat_id=update.effective_chat.id, message_id=update.message.message_id, reaction="👍")
        await fetch_logs(update, context, 50, type="error")
    elif trigger_text == "transparant_on":
        shared_state["transparant_mode"] = True
        await update.message.reply_text(f"_transparant mode enabled 🟢_ {PA}", parse_mode="Markdown")
    elif trigger_text == "transparant_off":
        shared_state["transparant_mode"] = False
        await update.message.reply_text(f"_transparant mode disabled 🔴_ {PA}", parse_mode="Markdown")




# First orchestration: function to analyze any chat message and categorize it. Currently treats replies differently, mentions and regular messages differently
async def analyze_any_message(update, context):
    if not await is_ben_in_chat(update, context):   # currently non-Bens are blocked from most functionality
        await update.message.reply_text("Uhh, hoi... Stiekem ben ik een beetje verlegen. Praat met me in een chat waar Ben bij zit, pas dan voel ik me op mijn gemak 🧙‍♂️\n\n\nPS: je kunt hier wel allerhande boodschappen ter feedback achterlaten, dan geef ik die door aan Ben (#privacy). Denk bijvoorbeeld aan feature requests, kwinkslagen, knuffelbedreigingen, valsspeelbiechten, slaapzakberichten etc.\nPPS: Die laatste verzon ChatGPT. En ik quote: 'Een heel lang bericht, waarin je jezelf zou kunnen verliezen alsof je in een slaapzak kruipt.'")
        await notify_ben(update, context)
        return
    else:
        try:
            user_message = update.message.text
            
            # Reject long messages
            if len(user_message) > 1800:
                await update.message.reply_text(f"Hmpff... TL;DR pl0x? 🧙‍♂️\n(_{len(user_message)}_)", parse_mode="Markdown")
                return
            
            # Handle preset triggers
            for trigger_text in triggers:
                user_message = user_message.lower()
                if trigger_text.lower() == user_message:
                    logging.info(f"Message received: Trigger ({trigger_text})")
                    await handle_triggers(update, context, trigger_text)
                    return
            # Handle dynamic "logs<num>" triggers
            match = re.match(r"^logs(\d+)$", user_message.lower())
            if match:
                logging.info(f"Message received: Dynamic logs trigger ({user_message.lower()})")
                num_lines = int(match.group(1))  # Extract the number after 'logs'
                await handle_triggers(update, context, f"logs{num_lines}")  # Pass it dynamically
                return
            
            # Handle all other messages
            bot_response_wanted = True
            regular_message = True
            bot_reply_message = False
            bot_mention_message = False
            
            # Check if the message is a reply to another message
            if update.message.reply_to_message:
                if update.message.reply_to_message.from_user.is_bot:
                    logging.info("Message received: Bot Reply\n")
                    regular_message = False   
                    bot_reply_message = True
                else:
                    shutup_message = await update.message.reply_text(f"OOKAY I'll shut up for this one {PA}\n_(unless you still tagged me)_", parse_mode="Markdown")
                    await delete_message(update, context, shutup_message.id, 3)
                    bot_response_wanted = False
                    
            # Check if the message mentions the bot specifically
            message_text = update.message.text or ""
            if ('@TestManon_bot' in message_text) or ('@Manon_PA_bot' in message_text):
                logging.info("Message received: Bot Mention\n")
                bot_response_wanted = True
                regular_message = False          
                bot_mention_message = True
                
            # Parse message entities to handle mentions
            if update.message.entities:
                for entity in update.message.entities:
                    if entity.type == MessageEntity.MENTION:
                        # Extract the mentioned username
                        mention = update.message.text[entity.offset: entity.offset + entity.length]
                
                        # Attempt to get user information based on the mention
                        try:
                            # Remove the '@' symbol to get the username
                            username = mention[1:]
                            user = await context.bot.get_chat(username)
                    
                            # Check if the mentioned user is a bot
                            if not user.is_bot:
                                logging.info(f"Message received: Non-Bot User Mentioned ({username})\n")
                                bot_response_wanted = False
                                break  # No need to check further mentions
                        except Exception as e:
                            # Handle cases where the user cannot be found
                            logging.warning(f"Could not retrieve user for mention {mention}: {e}")
                            continue  # Skip to the next mention
                        
            # Handle messages that contain @ and are not specific bot mentions
            if regular_message and '@' in message_text and bot_response_wanted:
                shutup_message = await update.message.reply_text(f"OOKAY I'll shut up for this one {PA}")
                await delete_message(update, context, shutup_message.id, 2)
                bot_response_wanted = False    
            
            # Final decision to respond
            if bot_response_wanted:
                if regular_message or bot_reply_message or bot_mention_message:
                    logging.info("Message received that wants a bot reponse\n")
                    await start_initial_classification(update, context)                                     # < < <
            
        except Exception as e:
            logging.error(f"\n\n🚨 Error in analyze_any_message(): {e}\n\n")
            await update.message.reply_text(f"Error in analyze_any_message():\n {e}")


async def roll_dice(update, context, user_guess=None):
    chat_id = update.effective_chat.id

    try:
        # Send the dice and capture the message object
        dice_message = await context.bot.send_dice(
            chat_id,
            reply_to_message_id=update.message.message_id
        )
        
        # Check the outcome of the dice roll
        rolled_value = dice_message.dice.value
        if not user_guess:
            return
        else:
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

