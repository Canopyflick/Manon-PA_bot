# features/goals/queries.py
from models.goal import Goal
from utils.db import Database
from datetime import datetime
from utils.helpers import BERLIN_TZ
from utils.db_helpers import build_query_with_datetime_params
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

        base_query = """
            SELECT * FROM manon_goals
            WHERE user_id = $1 
            AND chat_id = $2
            AND source = 'manon'
            AND status = 'pending'
        """

        params = [user_id, chat_id]

        datetime_filters = []
        if start_time:
            datetime_filters.append(('deadline', '>=', start_time))
        if end_time:
            datetime_filters.append(('deadline', '<=', end_time))

        query, params = build_query_with_datetime_params(
            base_query,
            params,
            datetime_filters,
            order_by="deadline ASC"
        )

        async with Database.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [Goal.from_row(row) for row in rows]

    except Exception as e:
        logger.error(f"Error fetching goals for user_id {user_id}, chat_id {chat_id}: {e}")
        return []


async def fetch_open_source_goals(user_id, chat_id, source):
    """Open goals from one app, such as benwerktijd. Urgent ones come first."""
    try:
        async with Database.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM manon_goals
                WHERE user_id = $1 AND chat_id = $2
                  AND source = $3
                  AND status IN ('prepared', 'pending', 'paused', 'limbo')
                ORDER BY urgent DESC, sort_order NULLS LAST, goal_id ASC
                """,
                user_id,
                chat_id,
                source,
            )
            return [Goal.from_row(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching {source} goals for user_id {user_id}, chat_id {chat_id}: {e}")
        return []


async def fetch_urgent_open_goals(user_id, chat_id):
    """Open goals marked urgent, from any source. These have no deadline window."""
    try:
        async with Database.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM manon_goals
                WHERE user_id = $1 AND chat_id = $2
                  AND urgent = true
                  AND status IN ('prepared', 'pending')
                ORDER BY sort_order NULLS LAST, goal_id ASC
                """,
                user_id,
                chat_id,
            )
            return [Goal.from_row(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching urgent goals for user_id {user_id}, chat_id {chat_id}: {e}")
        return []


def collapse_goal_candidates(
    upcoming_rows,
    recent_rows,
    series_counts=None,
    upcoming_limit=8,
    recent_limit=8,
):
    """One row per recurring series: next upcoming, then recently set, no overlap.

    ``upcoming_rows`` must already be ordered by deadline ascending.
    ``recent_rows`` must already be ordered by set_time descending.
    A series id is ``group_id`` when set, otherwise ``goal_id``.
    """
    series_counts = series_counts or {}

    def series_id(row):
        return row.get("group_id") or row["goal_id"]

    def entry(row):
        sid = series_id(row)
        return {
            "goal_id": row["goal_id"],
            "series_id": sid,
            "goal_description": row.get("goal_description"),
            "status": row.get("status"),
            "deadline": row.get("deadline"),
            "set_time": row.get("set_time"),
            "recurrence_type": row.get("recurrence_type"),
            "timeframe": row.get("timeframe"),
            "remaining": series_counts.get(sid, 1),
        }

    upcoming = []
    seen_series = set()
    for row in upcoming_rows:
        sid = series_id(row)
        if sid in seen_series:
            continue
        seen_series.add(sid)
        upcoming.append(entry(row))
        if len(upcoming) >= upcoming_limit:
            break

    recent = []
    seen_recent = set()
    for row in recent_rows:
        sid = series_id(row)
        if sid in seen_series or sid in seen_recent:
            continue
        seen_recent.add(sid)
        recent.append(entry(row))
        if len(recent) >= recent_limit:
            break

    return {"upcoming": upcoming, "recent": recent}


async def fetch_goal_candidate_lists(user_id, chat_id, upcoming_limit=8, recent_limit=8):
    """Next upcoming goals plus recently set goals, series collapsed and de-duplicated."""
    try:
        async with Database.acquire() as conn:
            upcoming_rows = await conn.fetch(
                """
                SELECT goal_id, group_id, goal_description, status, deadline,
                       set_time, recurrence_type, timeframe
                FROM manon_goals
                WHERE user_id = $1 AND chat_id = $2
                  AND source = 'manon'
                  AND status IN ('pending', 'paused')
                  AND deadline IS NOT NULL
                  AND deadline >= NOW()
                ORDER BY deadline ASC
                LIMIT 80
                """,
                user_id,
                chat_id,
            )
            recent_rows = await conn.fetch(
                """
                SELECT goal_id, group_id, goal_description, status, deadline,
                       set_time, recurrence_type, timeframe
                FROM manon_goals
                WHERE user_id = $1 AND chat_id = $2
                  AND source = 'manon'
                  AND status IN ('pending', 'prepared', 'paused')
                ORDER BY set_time DESC NULLS LAST
                LIMIT 80
                """,
                user_id,
                chat_id,
            )
            count_rows = await conn.fetch(
                """
                SELECT COALESCE(group_id, goal_id) AS series_id, COUNT(*)::int AS remaining
                FROM manon_goals
                WHERE user_id = $1 AND chat_id = $2
                  AND source = 'manon'
                  AND status IN ('pending', 'paused', 'prepared')
                GROUP BY 1
                """,
                user_id,
                chat_id,
            )
        series_counts = {row["series_id"]: row["remaining"] for row in count_rows}
        return collapse_goal_candidates(
            upcoming_rows,
            recent_rows,
            series_counts=series_counts,
            upcoming_limit=upcoming_limit,
            recent_limit=recent_limit,
        )
    except Exception as e:
        logger.error(f"Error fetching goal candidates for user {user_id}: {e}")
        return {"upcoming": [], "recent": []}


async def fetch_goals_for_user(user_id, chat_id, goal_ids):
    """Active goals among the given ids that belong to this user and chat."""
    if not goal_ids:
        return []
    try:
        async with Database.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT goal_id, group_id, goal_description, status, deadline,
                       set_time, recurrence_type, timeframe
                FROM manon_goals
                WHERE user_id = $1 AND chat_id = $2
                  AND goal_id = ANY($3::int[])
                """,
                user_id,
                chat_id,
                list(goal_ids),
            )
        return list(rows)
    except Exception as e:
        logger.error(f"Error fetching goals {goal_ids} for user {user_id}: {e}")
        return []


async def search_user_goals(user_id, chat_id, text=None, goal_id=None, on_date=None, limit=10):
    """Read-only search scoped to one user and chat. At most ``limit`` rows."""
    clauses = [
        "user_id = $1",
        "chat_id = $2",
        "source = 'manon'",
        "status IN ('pending', 'prepared', 'paused', 'limbo')",
    ]
    params = [user_id, chat_id]
    if goal_id:
        params.append(int(goal_id))
        clauses.append(f"goal_id = ${len(params)}")
    if text:
        escaped = str(text).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params.append(f"%{escaped}%")
        clauses.append(f"goal_description ILIKE ${len(params)} ESCAPE '\\'")
    if on_date:
        params.append(on_date)
        clauses.append(
            f"(deadline AT TIME ZONE 'Europe/Berlin')::date = ${len(params)}::date"
        )
    params.append(limit)
    query = f"""
        SELECT goal_id, group_id, goal_description, status, deadline,
               recurrence_type, timeframe
        FROM manon_goals
        WHERE {' AND '.join(clauses)}
        ORDER BY deadline ASC NULLS LAST, set_time DESC
        LIMIT ${len(params)}
    """
    async with Database.acquire() as conn:
        return list(await conn.fetch(query, *params))


async def goal_ids_for_scope(user_id, chat_id, goal_id, scope):
    """Instance: that goal. Series: every open row in the same series."""
    if scope != "series":
        return [goal_id]
    try:
        async with Database.acquire() as conn:
            anchor = await conn.fetchrow(
                """
                SELECT goal_id, group_id
                FROM manon_goals
                WHERE goal_id = $1 AND user_id = $2 AND chat_id = $3
                """,
                goal_id,
                user_id,
                chat_id,
            )
            if not anchor:
                return []
            series_id = anchor["group_id"] or anchor["goal_id"]
            rows = await conn.fetch(
                """
                SELECT goal_id
                FROM manon_goals
                WHERE user_id = $1 AND chat_id = $2
                  AND source = 'manon'
                  AND status IN ('pending', 'paused', 'prepared')
                  AND COALESCE(group_id, goal_id) = $3
                ORDER BY deadline ASC NULLS LAST, goal_id ASC
                """,
                user_id,
                chat_id,
                series_id,
            )
        return [row["goal_id"] for row in rows] or [goal_id]
    except Exception as e:
        logger.error(f"Error expanding series for goal {goal_id}: {e}")
        return [goal_id]