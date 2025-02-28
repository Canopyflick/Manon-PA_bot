# import asyncio
# import logging
# import random
# from datetime import time, datetime
#
# from features.bitcoin.monitoring import get_btc_price
# from utils.db import Database
# from utils.helpers import BERLIN_TZ
# from utils.scheduler import fetch_overdue_goals, logger
# from utils.session_avatar import PA
#
# # set the time that the message is scheduled daily for in main()
# evening_message_hours = 20
# evening_message_minutes = 20
#
#
# async def send_evening_message(bot, specific_chat_id=None):
#     try:
#         async with Database.acquire() as conn:
#             # Fetch all unique user_id/chat_id pairs
#             users = await conn.fetch("SELECT user_id, chat_id, first_name FROM manon_users")
#
#         # Fetch Bitcoin price and change percentage
#         _, detailed_message, _, usd_change = await get_btc_price()
#         change_message = ""
#         if abs(usd_change) > 10:
#             change_message = f"\n\n📈 _฿itcoin price changed by {usd_change:.2f}% in the last 24 hours._\n{detailed_message}"
#
#         evening_emojis = ["🫖", "💫", "🌇", "🌆", "💤", "😴", "🛌"]
#         random_emoji = random.choice(evening_emojis)
#
#         greeting = "Good evening"
#         announcement = "Please report on goal progress for:"
#         # Check if it's morning or not
#         evening_start = time(18, 0)  # 18:00
#         evening_end = time(23, 59)  # 23:59
#         now = datetime.now(tz=BERLIN_TZ)
#         if not (evening_start <= now.time() <= evening_end):
#             greeting = "Why hello there"
#             announcement = "Today's remaining pending goals are:"
#
#         # Loop through each user row and send a personalized message
#         for user in users:
#             user_id = user["user_id"]
#             chat_id = user["chat_id"]
#             # skip irrelevant chats if a specific chat was specified
#             if specific_chat_id and chat_id != specific_chat_id:
#                 continue
#
#             first_name = user["first_name"] or "Sardientje"  # Fallback if first_name is NULL or empt
#
#             overdue_goals, total_goal_value, total_penalty, goals_count = await fetch_overdue_goals(chat_id, user_id, timeframe="today")   # returns all pending goals today to report on, whether overdue or not
#             logging.debug(f"overdue goals for user_id {user_id}: {overdue_goals}")
#
#             # don't send evening messages to users without open goals today when they haven't requested it themselves in a specific chat, except for 15% of the time
#             if not overdue_goals and not change_message and random.random() > 0.15:
#                 return
#
#             if not overdue_goals:
#                 announcement = "\n🔎    _....._    🔍\n\nNo pending goals remaining today, you're all caught up ✨"
#
#             nightly_message = (
#                 f"*{greeting}, {first_name}!* {PA}\n"
#                 f"{announcement}\n\n"
#             )
#             stakes_message = f"_⚡{total_goal_value} & 🌚{total_penalty} on the line._\n"
#             if total_goal_value == 0 or goals_count == 1:
#                 stakes_message = None
#
#             nightly_message += change_message
#             if random.random() < 0.00273972603:  # once per year if triggered daily
#                 nightly_message += "\n\nAwel slaap wel! ❤️\n\n_'[memorabele quote enzo]'_}"
#             try:
#                 await bot.send_message(chat_id, "🌚")
#                 await asyncio.sleep(2)
#                 await bot.send_message(chat_id, nightly_message, parse_mode="Markdown")
#                 for goal in overdue_goals:
#                     if not isinstance(goal, dict) or "text" not in goal or "buttons" not in goal:
#                         continue
#                     await bot.send_message(
#                         chat_id=chat_id,
#                         text=goal["text"],
#                         reply_markup=goal["buttons"],
#                         parse_mode="Markdown"
#                     )
#                 await asyncio.sleep(4)
#                 if stakes_message:
#                     await bot.send_message(chat_id, stakes_message, parse_mode="Markdown")
#                 await bot.send_message(chat_id, random_emoji)
#                 logger.info(f"Nightly message sent successfully in chat {chat_id} for {first_name}({user_id}).")
#             except Exception as e:
#                 logger.error(f"Error in evening message sending message to chat_id {chat_id}: {e}")
#
#     except Exception as e:
#         logger.error(f"Error sending daily message: {e}")
