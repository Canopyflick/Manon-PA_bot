# models/goal.py
from datetime import datetime

import asyncpg

from utils.helpers import BERLIN_TZ


class Goal:
    def __init__(self, goal_id, user_id, chat_id, status, goal_description,
                 deadline: datetime, goal_value=None, penalty=None,
                 reminder_scheduled=False, final_iteration="not applicable",
                 recurrence_type=None, timeframe=None, **kwargs):
        self.goal_id = goal_id
        self.user_id = user_id
        self.chat_id = chat_id
        self.status = status
        self.goal_description = goal_description
        self.deadline = deadline  # expected to be timezone-aware
        self.goal_value = goal_value
        self.penalty = penalty
        self.reminder_scheduled = reminder_scheduled
        self.final_iteration = final_iteration
        self.recurrence_type = recurrence_type
        self.timeframe = timeframe
        # Other fields (like deadlines, set_time, etc.) can be added as needed:
        self.extra = kwargs

    @classmethod
    def from_row(cls, row: asyncpg.Record):
        return cls(
            goal_id=row["goal_id"],
            user_id=row["user_id"],
            chat_id=row["chat_id"],
            status=row["status"],
            goal_description=row.get("goal_description"),
            deadline=row.get("deadline"),
            goal_value=row.get("goal_value"),
            penalty=row.get("penalty"),
            reminder_scheduled=row.get("reminder_scheduled", False),
            final_iteration=row.get("final_iteration", "not applicable"),
            recurrence_type=row.get("recurrence_type"),
            timeframe=row.get("timeframe"),
            # Add other fields if needed:
            deadlines=row.get("deadlines"),
            set_time=row.get("set_time")
        )

    @classmethod
    async def fetch(cls, conn, goal_id: int):
        query = """
            SELECT * FROM manon_goals
            WHERE goal_id = $1
        """
        row = await conn.fetchrow(query, goal_id)
        if row:
            return cls.from_row(row)
        return None

    async def save(self, conn):
        """
        For simplicity, this is an update method.
        For new goals, you might have a separate create method.
        """
        query = """
            UPDATE manon_goals
            SET
                status = $2,
                goal_description = $3,
                deadline = $4,
                goal_value = $5,
                penalty = $6,
                reminder_scheduled = $7,
                final_iteration = $8
            WHERE goal_id = $1
        """
        await conn.execute(query,
            self.goal_id,
            self.status,
            self.goal_description,
            self.deadline.astimezone(BERLIN_TZ) if self.deadline else None,
            self.goal_value,
            self.penalty,
            self.reminder_scheduled,
            self.final_iteration
        )