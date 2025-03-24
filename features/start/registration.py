from utils.db import get_first_name, Database
from logger.logger import logger


async def register_user(context, user_id, chat_id):
    try:
        first_name = await get_first_name(context, user_id, chat_id)

        async with Database.acquire() as conn:
            # Check if the user already exists in the users table
            result = await conn.fetchrow(
                "SELECT first_name FROM manon_users WHERE user_id = $1 AND chat_id = $2",
                user_id, chat_id
            )

            if result is None:
                # User doesn't exist, insert with first_name
                await conn.execute("""
                    INSERT INTO manon_users (user_id, chat_id, first_name)
                    VALUES ($1, $2, $3)
                """, user_id, chat_id, first_name)
                logger.warning(f"Inserted new user with user_id: {user_id}, chat_id: {chat_id}, first_name: {first_name}")
                await context.bot.send_message(chat_id, text=f"_Registered new user_ [*{first_name}*]_ with User ID:_", parse_mode="Markdown")
                await context.bot.send_message(chat_id, text=f"{user_id}", parse_mode="Markdown")
                await context.bot.send_message(chat_id, text="_in chat:_", parse_mode="Markdown")
                await context.bot.send_message(chat_id, text=f"{chat_id}", parse_mode="Markdown")
            elif result['first_name'] is None:
                # User exists but first_name is missing, update it
                await conn.execute("""
                    UPDATE manon_users
                    SET first_name = $1
                    WHERE user_id = $2 AND chat_id = $3
                """, first_name, user_id, chat_id)
                logger.warning(f"Updated first_name for user_id: {user_id}, chat_id: {chat_id} to {first_name}")

            else:
                return f"Registered user {first_name} called /start"

    except Exception as e:
        logger.error(f"Error updating user record: {e}")
        raise
