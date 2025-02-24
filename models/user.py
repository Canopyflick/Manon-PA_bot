# models/user.py
import asyncpg
from datetime import datetime
from utils.helpers import BERLIN_TZ

class User:
    def __init__(self, user_id, chat_id, first_name, pending_goals=0,
                 finished_goals=0, failed_goals=0, score=0.0, penalties_accrued=0.0,
                 inventory=None, any_reminder_scheduled=False, long_term_goals=None):
        self.user_id = user_id
        self.chat_id = chat_id
        self.first_name = first_name
        self.pending_goals = pending_goals
        self.finished_goals = finished_goals
        self.failed_goals = failed_goals
        self.score = score
        self.penalties_accrued = penalties_accrued
        self.inventory = inventory or {"boosts": 1, "challenges": 1, "links": 1}
        self.any_reminder_scheduled = any_reminder_scheduled
        self.long_term_goals = long_term_goals

    @classmethod
    def from_row(cls, row: asyncpg.Record):
        return cls(
            user_id=row["user_id"],
            chat_id=row["chat_id"],
            first_name=row.get("first_name"),
            pending_goals=row.get("pending_goals", 0),
            finished_goals=row.get("finished_goals", 0),
            failed_goals=row.get("failed_goals", 0),
            score=row.get("score", 0.0),
            penalties_accrued=row.get("penalties_accrued", 0.0),
            inventory=row.get("inventory"),
            any_reminder_scheduled=row.get("any_reminder_scheduled", False),
            long_term_goals=row.get("long_term_goals")
        )

    @classmethod
    async def fetch(cls, conn, user_id: int, chat_id: int):
        query = """
            SELECT * FROM manon_users
            WHERE user_id = $1 AND chat_id = $2
        """
        row = await conn.fetchrow(query, user_id, chat_id)
        if row:
            return cls.from_row(row)
        return None

    async def save(self, conn):
        """
        If the user exists, update; otherwise insert.
        For simplicity, here’s an update example.
        """
        query = """
            UPDATE manon_users
            SET first_name = $2,
                pending_goals = $3,
                finished_goals = $4,
                failed_goals = $5,
                score = $6,
                penalties_accrued = $7,
                inventory = $8,
                any_reminder_scheduled = $9,
                long_term_goals = $10
            WHERE user_id = $1 AND chat_id = $11
        """
        # You could add logic to perform an insert if no rows were affected.
        await conn.execute(query,
            self.user_id,
            self.first_name,
            self.pending_goals,
            self.finished_goals,
            self.failed_goals,
            self.score,
            self.penalties_accrued,
            self.inventory,
            self.any_reminder_scheduled,
            self.long_term_goals,
            self.chat_id
        )
