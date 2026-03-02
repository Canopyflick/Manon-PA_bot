# features/agent/tools.py

import logging
import re
from datetime import datetime
from langchain_core.tools import tool
from utils.db import Database
from utils.helpers import BERLIN_TZ
from features.bitcoin.monitoring import get_btc_price
from features.weather.monitoring import get_weather_change_message

logger = logging.getLogger(__name__)


# ─── SQL Safety ──────────────────────────────────────────────────────────────

FORBIDDEN_SQL_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|"
    r"COPY|EXECUTE|DO\s|CALL|SET\s|VACUUM|REINDEX|COMMENT|SECURITY|pg_)\b",
    re.IGNORECASE,
)


def validate_sql(query: str) -> tuple[bool, str]:
    """Returns (is_safe, reason). Rejects anything that is not a pure SELECT."""
    stripped = query.strip().rstrip(";").strip()
    if not stripped.upper().startswith("SELECT"):
        return False, "Query must start with SELECT"
    match = FORBIDDEN_SQL_PATTERNS.search(stripped)
    if match:
        return False, f"Forbidden keyword: {match.group()}"
    if ";" in stripped:
        return False, "Multiple statements not allowed"
    return True, "OK"


# ─── Tool Factory ────────────────────────────────────────────────────────────

def create_agent_tools(user_id: int, chat_id: int) -> list:
    """Create tool instances with user_id/chat_id baked in via closure."""

    @tool
    async def get_active_goals() -> str:
        """Get the user's active goals (pending, prepared, paused, limbo).
        Returns goal_id, description, status, deadline, and recurrence type."""
        async with Database.acquire() as conn:
            rows = await conn.fetch("""
                SELECT goal_id, goal_description, status, deadline, recurrence_type
                FROM manon_goals
                WHERE user_id = $1 AND chat_id = $2
                  AND status IN ('pending', 'prepared', 'paused', 'limbo')
                ORDER BY deadline ASC NULLS LAST
                LIMIT 20
            """, user_id, chat_id)
        if not rows:
            return "No active goals."
        lines = []
        for r in rows:
            dl = r["deadline"].strftime("%Y-%m-%d %H:%M") if r["deadline"] else "none"
            lines.append(
                f"#{r['goal_id']} [{r['status']}] {r['goal_description'][:80]} "
                f"(deadline: {dl}, {r['recurrence_type']})"
            )
        return "\n".join(lines)

    @tool
    async def get_overdue_goals() -> str:
        """Get the user's overdue goals — pending goals whose deadline has passed."""
        now = datetime.now(BERLIN_TZ)
        async with Database.acquire() as conn:
            rows = await conn.fetch("""
                SELECT goal_id, goal_description, deadline, goal_value, penalty
                FROM manon_goals
                WHERE user_id = $1 AND chat_id = $2
                  AND status = 'pending'
                  AND deadline < $3
                ORDER BY deadline ASC
                LIMIT 15
            """, user_id, chat_id, now)
        if not rows:
            return "No overdue goals."
        lines = []
        for r in rows:
            dl = r["deadline"].strftime("%Y-%m-%d %H:%M") if r["deadline"] else "?"
            lines.append(
                f"#{r['goal_id']} {r['goal_description'][:80]} "
                f"(was due: {dl}, value: {r['goal_value']}, penalty: {r['penalty']})"
            )
        return "\n".join(lines)

    @tool
    async def get_goals_today() -> str:
        """Get goals with a deadline today."""
        now = datetime.now(BERLIN_TZ)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(hour=23, minute=59, second=59)
        async with Database.acquire() as conn:
            rows = await conn.fetch("""
                SELECT goal_id, goal_description, status, deadline, goal_value
                FROM manon_goals
                WHERE user_id = $1 AND chat_id = $2
                  AND deadline >= $3 AND deadline <= $4
                  AND status IN ('pending', 'prepared', 'paused')
                ORDER BY deadline ASC
            """, user_id, chat_id, start, end)
        if not rows:
            return "No goals due today."
        lines = []
        for r in rows:
            dl = r["deadline"].strftime("%H:%M") if r["deadline"] else "?"
            lines.append(
                f"#{r['goal_id']} [{r['status']}] {r['goal_description'][:80]} "
                f"(due: {dl}, value: {r['goal_value']})"
            )
        return "\n".join(lines)

    @tool
    async def get_user_stats() -> str:
        """Get the user's overall stats: score, completed goals, failed goals,
        penalties, and completion rate."""
        async with Database.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT score, pending_goals, finished_goals, failed_goals,
                       penalties_accrued
                FROM manon_users
                WHERE user_id = $1 AND chat_id = $2
            """, user_id, chat_id)
        if not row:
            return "User not found."
        total = row["finished_goals"] + row["failed_goals"]
        rate = f"{row['finished_goals'] / total * 100:.1f}%" if total > 0 else "N/A"
        return (
            f"Score: {row['score']:.1f}\n"
            f"Pending: {row['pending_goals']}\n"
            f"Finished: {row['finished_goals']}\n"
            f"Failed: {row['failed_goals']}\n"
            f"Penalties accrued: {row['penalties_accrued']:.1f}\n"
            f"Completion rate: {rate}"
        )

    @tool
    async def get_recent_stats(days: int = 7) -> str:
        """Get daily stats snapshots for the last N days (default 7).
        Shows score changes, goals set/finished/failed per day."""
        days = max(1, min(days, 90))
        async with Database.acquire() as conn:
            rows = await conn.fetch("""
                SELECT date, score, goals_set, goals_finished, goals_failed,
                       score_gained, penalties_incurred, completion_rate
                FROM manon_stats_snapshots
                WHERE user_id = $1 AND chat_id = $2
                  AND date >= CURRENT_DATE - $3::int
                ORDER BY date DESC
            """, user_id, chat_id, days)
        if not rows:
            return f"No stats snapshots in the last {days} days."
        lines = []
        for r in rows:
            lines.append(
                f"{r['date']}: score={r['score']:.1f} "
                f"(+{r['score_gained']:.1f}/-{r['penalties_incurred']:.1f}) "
                f"set={r['goals_set']} done={r['goals_finished']} "
                f"fail={r['goals_failed']} rate={r['completion_rate'] or 'N/A'}"
            )
        return "\n".join(lines)

    @tool
    async def get_goal_details(goal_id: int) -> str:
        """Get full details for a specific goal by its ID number."""
        async with Database.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT goal_id, goal_description, status, recurrence_type,
                       timeframe, goal_value, deadline, deadlines, interval,
                       reminder_time, reminders_times, reminder_scheduled,
                       set_time, completion_time, difficulty_multiplier,
                       impact_multiplier, penalty, total_penalty, attempt,
                       iteration, final_iteration, goal_category
                FROM manon_goals
                WHERE goal_id = $1 AND user_id = $2 AND chat_id = $3
            """, goal_id, user_id, chat_id)
        if not row:
            return f"Goal #{goal_id} not found (or belongs to a different user)."
        parts = []
        for key in row.keys():
            val = row[key]
            if val is not None:
                parts.append(f"{key}: {val}")
        return "\n".join(parts)

    @tool
    async def get_btc_price_tool() -> str:
        """Get the current Bitcoin price in USD and EUR, plus 24h change."""
        btc = await get_btc_price()
        return f"{btc.detailed_message}\n24h change: {btc.usd_change:+.2f}%"

    @tool
    async def get_weather_tool() -> str:
        """Get weather temperature info for Leipzig (significant temperature
        changes between yesterday, today, and 4 days out)."""
        msg = await get_weather_change_message()
        return msg if msg else "No significant temperature changes to report."

    # Build dynamic description with user context for custom SQL
    custom_sql_description = (
        "Execute a read-only SQL query against the database. Only SELECT "
        "statements are allowed. No INSERT/UPDATE/DELETE/DROP/ALTER.\n\n"
        "Available tables and key columns:\n"
        "- manon_goals: goal_id, user_id, chat_id, group_id, status "
        "('limbo'|'prepared'|'pending'|'paused'|'archived_done'|"
        "'archived_failed'|'archived_canceled'), recurrence_type, "
        "timeframe, goal_value, goal_description, set_time, deadline, "
        "deadlines[], interval, reminder_time, reminders_times[], "
        "reminder_scheduled, time_investment_value, difficulty_multiplier, "
        "impact_multiplier, penalty, total_penalty, attempt, iteration, "
        "final_iteration, goal_category[], completion_time\n"
        "- manon_users: user_id, chat_id (composite PK), first_name, "
        "pending_goals, finished_goals, failed_goals, score, "
        "penalties_accrued, inventory (JSONB), any_reminder_scheduled, "
        "long_term_goals\n"
        "- manon_stats_snapshots: snapshot_id, user_id, chat_id, date, "
        "score, goals_set, goals_finished, goals_failed, score_gained, "
        "penalties_incurred, completion_rate, snapshot_time\n"
        "- manon_reminders: reminder_id, user_id, chat_id, reminder_text, "
        "reminder_category[], set_time, time\n\n"
        "Tips:\n"
        "- All timestamps are in Europe/Berlin timezone\n"
        f"- The current user_id is {user_id} and chat_id is {chat_id} — "
        "use these to filter queries\n"
        "- Use AT TIME ZONE 'Europe/Berlin' for date operations if needed\n"
        "- LIMIT results to keep output concise (max 20 rows recommended)\n"
        "- goal_category and deadlines are PostgreSQL arrays\n"
        "- Status flow: limbo → prepared → pending → archived_done/failed/canceled"
    )

    @tool(description=custom_sql_description)
    async def run_custom_query(sql: str) -> str:
        """Execute a read-only SQL query."""
        is_safe, reason = validate_sql(sql)
        if not is_safe:
            return f"BLOCKED: {reason}"
        try:
            async with Database.acquire() as conn:
                rows = await conn.fetch(sql)
            if not rows:
                return "Query returned no results."
            result_lines = []
            for i, row in enumerate(rows[:20]):
                parts = [f"{k}: {v}" for k, v in dict(row).items()]
                result_lines.append(f"Row {i+1}: {', '.join(parts)}")
            suffix = f"\n... ({len(rows) - 20} more rows)" if len(rows) > 20 else ""
            return "\n".join(result_lines) + suffix
        except Exception as e:
            return f"SQL error: {e}"

    return [
        get_active_goals,
        get_overdue_goals,
        get_goals_today,
        get_user_stats,
        get_recent_stats,
        get_goal_details,
        get_btc_price_tool,
        get_weather_tool,
        run_custom_query,
    ]
