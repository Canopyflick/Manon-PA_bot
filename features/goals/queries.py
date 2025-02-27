# features/goals/queries.py
from models.goal import Goal
from utils.db import Database
from datetime import datetime, timedelta
from utils.helpers import BERLIN_TZ
import logging

logger = logging.getLogger(__name__)


async def get_pending_goals_by_timeframe(user_id, chat_id, *, start_time=None, end_time=None):
    """
    Generic function to fetch pending goals within a time range.

    Args:
        user_id: User ID
        chat_id: Chat ID
        start_time: Starting datetime (defaults to now)
        end_time: Ending datetime

    Returns:
        List of Goal objects
    """
    try:
        start_time = start_time or datetime.now(BERLIN_TZ)

        async with Database.acquire() as conn:
            query = """
                SELECT * FROM manon_goals
                WHERE user_id = $1 
                AND chat_id = $2
                AND status = 'pending'
                AND deadline >= $3
            """

            params = [user_id, chat_id, start_time]

            if end_time:
                query += " AND deadline <= $4"
                params.append(end_time)

            query += " ORDER BY deadline ASC"

            rows = await conn.fetch(query, *params)
            return [Goal.from_row(row) for row in rows]

    except Exception as e:
        logger.error(f"Error fetching goals for user_id {user_id}, chat_id {chat_id}: {e}")
        return []
