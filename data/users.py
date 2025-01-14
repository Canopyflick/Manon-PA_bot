from abc import ABC, abstractmethod
from typing import List

from utils.db import Database

# Domain


# Data layer
class UserRepository(IUserRepository):
    async def add(self, user: User):
        async with Database.acquire() as conn:
            query = f"""
                INSERT INTO manon_users (user_id, chat_id, first_name)
                VALUES ({user.telegram_user_id}, {user.telegram_chat_id}, {user.first_name})
            """
            await conn.execute(query)

    async def get(self, telegram_user_id: int, telegram_chat_id: int) -> User | None:
        async with Database.acquire() as conn:
            query = f"""
                SELECT *
                FROM manon_users
                WHERE user_id = {telegram_user_id} AND chat_id = {telegram_chat_id}
            """

            result = await conn.fetchrow(query)

            if not result:
                return None

