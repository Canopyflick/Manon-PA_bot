# features/goals/morning_message_deprecated.py
# import asyncio
# import random
# from datetime import time, datetime
#
# from features.bitcoin.monitoring import get_btc_change_message
# from utils.db import Database, fetch_upcoming_goals
# from utils.helpers import BERLIN_TZ
# from utils.scheduler import fetch_overdue_goals, logger
# from utils.session_avatar import PA
# from utils.string_resources import GREETING_GOOD_MORNING, GREETING_WHY_HELLO_THERE
#
#
# async def send_morning_message(bot, specific_chat_id=None):
#     """
#     Sends a personalized morning_message to all users (or to a specific chat, if provided).
#
#     The message includes a random morning emoji, a personalized greeting, overdue goals (if any),
#     upcoming goals, and a Bitcoin price update if the change exceeds 5%. The greeting and announcement
#     are adjusted based on whether it's morning (4 AM–12 PM) or later in the day.
#     """
#     try:
#         async with Database.acquire() as conn:
#             users = await conn.fetch("SELECT user_id, chat_id, first_name FROM manon_users")
#
#         btc_change_message = await get_btc_change_message()
#         greeting, announcement = _get_greeting_and_announcement()
#
#         for user in users:
#             user_id = user["user_id"]
#             chat_id = user["chat_id"]
#             if specific_chat_id and chat_id != specific_chat_id:
#                 continue
#
#             first_name = user.get("first_name") or "there"
#             await _send_personalized_message(bot, chat_id, user_id, first_name, greeting, announcement,
#                                              btc_change_message, specific_chat_id)
#     except Exception as e:
#         logger.error(f"Error sending daily message: {e}")
#
#
# def _get_greeting_and_announcement():
#     """
#     Determines the appropriate greeting and announcement based on the current time (in the Berlin timezone).
#
#     Returns:
#         tuple: (greeting, announcement) where:
#             - greeting: A morning greeting if between 4 AM and 12 PM, otherwise an alternative greeting.
#             - announcement: A corresponding message about today's or upcoming goals.
#     """
#     now = datetime.now(tz=BERLIN_TZ)
#     morning_start, morning_end = time(4, 0), time(12, 0)
#     if morning_start <= now.time() <= morning_end:
#         return GREETING_GOOD_MORNING, "Your goals for the day are:"
#     else:
#         return GREETING_WHY_HELLO_THERE, "Your upcoming goals are:"
#
#
# async def _send_personalized_message(bot, chat_id, user_id, first_name, greeting, announcement, btc_change_message, specific_chat_id):
#     """
#     Composes and sends a personalized morning_message to a single user. The message sequence includes:
#
#     - A random morning emoji.
#     - A greeting (with overdue goal notifications if applicable).
#     - A detailed message about upcoming goals and stakes.
#     - A rare motivational quote (triggered with a very low probability).
#     - A final rocket emoji to conclude the message sequence.
#
#     Parameters:
#         bot: The Telegram bot instance used to send messages.
#         chat_id (int): The target chat ID.
#         user_id (int): The unique user ID.
#         first_name (str): The first name of the user (with a fallback if not provided).
#         greeting (str): The determined greeting based on the time of day.
#         announcement (str): The announcement message about goals.
#         btc_change_message (str): A formatted Bitcoin update message, if applicable.
#     """
#     try:
#         # Check for overdue goals from yesterday
#         overdue_goals, _, _, _ = await fetch_overdue_goals(chat_id, user_id, timeframe="yesterday")
#         greeting_message = f"*{greeting}, {first_name}!* {PA}\n"
#         if overdue_goals:
#             greeting_message += "\n_First, some unfinished business:_"
#
#         # Fetch upcoming goals from now until 10 AM tomorrow
#         goals_today, total_goal_value, total_penalty, goals_count = await fetch_upcoming_goals(chat_id, user_id,
#                                                                                                timeframe=10)
#
#         # don't send morning messages to users without upcoming goals if there's no bitcoin change and they haven't requested it themselves in a specific chat, except for 15% of the time
#         if goals_count == 0 and not btc_change_message and not specific_chat_id and not overdue_goals and random.random() > 0.15:
#             return
#
#         morning_message = f"{announcement}\n\n{goals_today}\n\n"
#         stakes_message = f"_Go get some (⚡{total_goal_value}) ..!\n... or lose some ({total_penalty}🌚)_\n"
#         if total_goal_value == 0 or goals_count == 1:
#             stakes_message = ""
#         if goals_count == 0:
#             announcement = ""
#         morning_message += stakes_message + btc_change_message
#
#         # Occasionally add a special motivational quote (approximately once per year if triggered daily)
#         if random.random() < 0.00273972603:
#             morning_message += (
#                 "\n\nZet je beste beentje voor, je kunt er niets aan doen, maar je kunt er wel wat aan doen! ❤️"
#                 "\n\n_'[memorabele quote enzo]'_}"
#             )
#
#         # Send the message components with pauses between them
#         morning_emojis = ["🍵", "☕", "🌄", "🌅", "🌞", "☃️", "❄️"]
#         random_emoji = random.choice(morning_emojis)
#         await bot.send_message(chat_id, random_emoji)
#         await bot.send_message(chat_id, greeting_message, parse_mode="Markdown")
#
#         if overdue_goals:
#             for goal in overdue_goals:
#                 if not isinstance(goal, dict) or "text" not in goal or "buttons" not in goal:
#                     continue
#                 await asyncio.sleep(1)
#                 await bot.send_message(
#                     chat_id=chat_id,
#                     text=goal["text"],
#                     reply_markup=goal["buttons"],
#                     parse_mode="Markdown"
#                 )
#         await asyncio.sleep(3)
#         await bot.send_message(chat_id, morning_message, parse_mode="Markdown")
#         await asyncio.sleep(4)
#         await bot.send_message(chat_id, "🚀")
#         logger.info(f"Daily message sent successfully in chat {chat_id} for {first_name}({user_id}).")
#     except Exception as e:
#         logger.error(f"Error sending morning_message to chat_id {chat_id}: {e}")

