# models/user.py
import asyncpg
from typing import Optional, Dict, Any
from utils.helpers import BERLIN_TZ

class User:
    def __init__(
        self,
        user_id: int,
        chat_id: int,
        first_name: str,
        pending_goals: int = 0,
        finished_goals: int = 0,
        failed_goals: int = 0,
        score: float = 0.0,
        penalties_accrued: float = 0.0,
        inventory: Optional[Dict[str, int]] = None,
        any_reminder_scheduled: bool = False,
        long_term_goals: Optional[str] = None,
    ) -> None:
        self.user_id: int = user_id
        self.chat_id: int = chat_id
        self.first_name: str = first_name
        self.pending_goals: int = pending_goals
        self.finished_goals: int = finished_goals
        self.failed_goals: int = failed_goals
        self.score: float = score
        self.penalties_accrued: float = penalties_accrued
        self.inventory: Dict[str, int] = inventory or {"boosts": 1, "challenges": 1, "links": 1}
        self.any_reminder_scheduled: bool = any_reminder_scheduled
        self.long_term_goals: Optional[str] = long_term_goals

    @classmethod
    def from_row(cls, row: asyncpg.Record) -> "User":
        return cls(
            user_id=row["user_id"],
            chat_id=row["chat_id"],
            first_name=row.get("first_name", "Josefientje"),
            pending_goals=row.get("pending_goals", 0),
            finished_goals=row.get("finished_goals", 0),
            failed_goals=row.get("failed_goals", 0),
            score=row.get("score", 0.0),
            penalties_accrued=row.get("penalties_accrued", 0.0),
            inventory=row.get("inventory"),
            any_reminder_scheduled=row.get("any_reminder_scheduled", False),
            long_term_goals=row.get("long_term_goals"),
        )

    @classmethod
    async def fetch(cls, conn: asyncpg.Connection, user_id: int, chat_id: int) -> Optional["User"]:
        query = """
            SELECT * FROM manon_users
            WHERE user_id = $1 AND chat_id = $2
        """
        row = await conn.fetchrow(query, user_id, chat_id)
        return cls.from_row(row) if row else None

    async def save(self, conn: asyncpg.Connection) -> None:
        """
        If the user exists, update; otherwise insert.
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
        await conn.execute(
            query,
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
            self.chat_id,
        )

