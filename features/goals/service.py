# features/goals/service.py
from models.goals_report import GoalsReport
from datetime import datetime, timedelta
from utils.helpers import BERLIN_TZ
from features.goals.queries import get_pending_goals_by_timeframe
import logging

logger = logging.getLogger(__name__)


async def get_overdue_goals(user_id, chat_id, timeframe="today"):
    """
    Get overdue goals based on timeframe
    Returns a GoalsReport instance containing goals and summary information:
        - goals
        - total_goal_value
        - total_penalty
        - goals_count
    """
    now = datetime.now(BERLIN_TZ)

    if timeframe == "early":
        # For morning_message: any open deadlines since 4am (the previous evening message handled everything up to 4am)
        start_time = datetime.combine(now.date(), datetime.min.time()).replace(hour=4, tzinfo=BERLIN_TZ)
        end_time = now
    elif timeframe == "overdue":
        # All pending goals with deadlines in the past
        end_time = now
        start_time = None  # No start limit
    elif timeframe == "today":
        # All pending goals with deadlines today up until 4am tomorrow
        now = datetime.now(BERLIN_TZ)
        tomorrow = now.date() + timedelta(days=1)
        end_time = datetime.combine(tomorrow, datetime.min.time()).replace(hour=4, tzinfo=BERLIN_TZ)
        start_time = None  # No start limit

    goals = await get_pending_goals_by_timeframe(
        user_id, chat_id,
        start_time=start_time,
        end_time=end_time
    )

    total_goal_value = sum(goal.goal_value or 0 for goal in goals)
    total_penalty = sum(goal.penalty or 0 for goal in goals)
    goals_count = len(goals)

    return GoalsReport(goals, total_goal_value, total_penalty, goals_count)

async def get_upcoming_goals(user_id, chat_id, timeframe=6):
    """
    Get upcoming goals based on timeframe
    """
    now = datetime.now(BERLIN_TZ)

    if timeframe == "24hs":
        end_time = now + timedelta(hours=24)
    elif timeframe == "rest_of_day":
        end_time = datetime.combine(now.date(), datetime.min.time()).replace(hour=4, tzinfo=BERLIN_TZ) + timedelta(
            days=1)
    elif isinstance(timeframe, int):
        end_time = now + timedelta(hours=timeframe)
    # Add other timeframe conditions...

    goals = await get_pending_goals_by_timeframe(
        user_id, chat_id,
        start_time=now,
        end_time=end_time
    )

    total_goal_value = sum(goal.goal_value or 0 for goal in goals)
    total_penalty = sum(goal.penalty or 0 for goal in goals)

    return goals, total_goal_value, total_penalty, len(goals)