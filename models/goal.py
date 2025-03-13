import asyncpg
from datetime import datetime
from typing import Optional, Dict, Any
from utils.helpers import BERLIN_TZ


class Goal:
    def __init__(
        self,
        goal_id: int,
        user_id: int,
        chat_id: int,
        status: str,
        goal_description: str,
        deadline: Optional[datetime],  # Expected to be timezone-aware
        goal_value: Optional[float] = None,
        penalty: Optional[float] = None,
        reminder_scheduled: bool = False,
        final_iteration: str = "not applicable",
        recurrence_type: Optional[str] = None,
        timeframe: Optional[str] = None,
        **kwargs: Dict[str, Any],
    ) -> None:
        self.goal_id: int = goal_id
        self.user_id: int = user_id
        self.chat_id: int = chat_id
        self.status: str = status
        self.goal_description: str = goal_description
        self.deadline: Optional[datetime] = deadline
        self.goal_value: Optional[float] = goal_value
        self.penalty: Optional[float] = penalty
        self.reminder_scheduled: bool = reminder_scheduled
        self.final_iteration: str = final_iteration
        self.recurrence_type: Optional[str] = recurrence_type
        self.timeframe: Optional[str] = timeframe
        self.extra: Dict[str, Any] = kwargs  # Stores additional fields dynamically

    @classmethod
    def from_row(cls, row: asyncpg.Record) -> "Goal":
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
            # Additional fields:
            deadlines=row.get("deadlines"),
            set_time=row.get("set_time"),
        )

    @classmethod
    async def fetch(cls, conn: asyncpg.Connection, goal_id: int) -> Optional["Goal"]:
        query = """
            SELECT * FROM manon_goals
            WHERE goal_id = $1
        """
        row = await conn.fetchrow(query, goal_id)
        return cls.from_row(row) if row else None

    async def save(self, conn: asyncpg.Connection) -> None:
        """
        Update an existing goal. If inserting a new goal, use a separate method.
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
        await conn.execute(
            query,
            self.goal_id,
            self.status,
            self.goal_description,
            self.deadline.astimezone(BERLIN_TZ) if self.deadline else None,
            self.goal_value,
            self.penalty,
            self.reminder_scheduled,
            self.final_iteration,
        )