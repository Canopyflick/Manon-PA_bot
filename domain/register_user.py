import logging

from data.users import IUserRepository, User
from utils.db import get_first_name, Database

async def register_user(context, user_id, chat_id,
                        repository: IUserRepository):
    try:
        first_name = await get_first_name(context, user_id, chat_id)

        async with Database.acquire() as conn:
            # Check if the user already exists in the users table
            result = repository.get(user_id, chat_id)

            if result:
                return

            new_user = User()
            new_user.telegram_user_id = user_id
            new_user.telegram_chat_id = chat_id
            new_user.first_name = await get_first_name(context, user_id, chat_id)
            new_user.score = 0

            await repository.add(new_user)

            logging.info(f"Inserted new user with user_id: {user_id}, chat_id: {chat_id}, first_name: {first_name}")
            await context.bot.send_message(chat_id, text=f"_Registered new user,_ *{first_name}*_, with User ID:_",
                                           parse_mode="Markdown")
            await context.bot.send_message(chat_id, text=f"_{user_id}_", parse_mode="Markdown")
            await context.bot.send_message(chat_id, text="_in chat:_", parse_mode="Markdown")
            await context.bot.send_message(chat_id, text=f"_{chat_id}_", parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Error updating user record: {e}")
        raise
