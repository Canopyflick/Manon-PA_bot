# features/goals/finder.py
"""Match a cancel / done / failed / edit request to the user's goals."""
import logging
import re
from datetime import datetime
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from pydantic import BaseModel

from features.goals.queries import (
    fetch_goal_candidate_lists,
    fetch_goals_for_user,
    search_user_goals,
)
from LLMs.config import llms
from utils.helpers import BERLIN_TZ, format_for_llm

logger = logging.getLogger(__name__)

MAX_FINDER_ITERATIONS = 3
# Goal cards render as #_42_ (markdown italic). Also accept a plain #42.
_GOAL_ID_RE = re.compile(r"#_?(\d+)_?")
_ACTIVE = ("pending", "prepared", "paused", "limbo")


class GoalPick(BaseModel):
    goal_id: int
    scope: Literal["instance", "series"] = "instance"

_INTENT = {
    "cancel": "cancel (delete) a goal Manon is already tracking",
    "edit": "edit a goal Manon is already tracking",
    "done": "mark a tracked goal as done",
    "failed": "mark a tracked goal as failed",
}


class FinderResult:
    def __init__(self):
        self.selections = []
        self.is_new_goal_instead = False
        self.note = ""
        self.candidate_ids = []
        self.finished = False


def mentioned_goal_ids(*texts) -> list[int]:
    seen = []
    for text in texts:
        for match in _GOAL_ID_RE.findall(text or ""):
            goal_id = int(match)
            if goal_id not in seen:
                seen.append(goal_id)
    return seen


def _format_row(row, remaining=None) -> str:
    deadline = format_for_llm(row["deadline"]) if row.get("deadline") else "no deadline"
    series = ""
    group_id = row.get("group_id") or row.get("series_id")
    recurrence = row.get("recurrence_type")
    if recurrence == "recurring" or (remaining is not None and remaining > 1):
        count = remaining if remaining is not None else "?"
        series = f", series #{group_id}, {count} active"
    description = row.get("goal_description") or "No description"
    return (
        f"#{row['goal_id']} — {description} "
        f"(deadline: {deadline}, status: {row.get('status')}{series})"
    )


def _format_candidates(entries) -> str:
    if not entries:
        return "(none)"
    return "\n".join(
        _format_row(entry, remaining=entry.get("remaining")) for entry in entries
    )


def _format_explicit(requested_ids, rows) -> str:
    if not requested_ids:
        return "None."
    by_id = {row["goal_id"]: row for row in rows}
    lines = []
    for goal_id in requested_ids:
        row = by_id.get(goal_id)
        if row is None:
            lines.append(f"#{goal_id} — not found for this user")
        elif row["status"] not in _ACTIVE:
            lines.append(f"#{goal_id} — not active (status: {row['status']})")
        else:
            lines.append(_format_row(row))
    return "\n".join(lines)


def _finder_tools(user_id, chat_id, captured: FinderResult):
    @tool
    async def search_goals(text: str = "", goal_id: int = 0, date: str = "") -> str:
        """Search this user's goals. Use when the goal is not clearly in the lists already shown.

        text: words from the goal description (optional).
        goal_id: exact id, without the # (optional).
        date: deadline day as YYYY-MM-DD (optional).
        """
        if not text and not goal_id and not date:
            return "Pass text, goal_id, or date."
        on_date = date.strip() if date else None
        if on_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", on_date):
            return "date must be YYYY-MM-DD."
        try:
            rows = await search_user_goals(
                user_id,
                chat_id,
                text=text.strip() or None,
                goal_id=goal_id or None,
                on_date=on_date,
            )
        except Exception as e:
            logger.error(f"search_goals failed: {e}")
            return f"Search failed: {e}"
        if not rows:
            return "No matching goals."
        return "\n".join(_format_row(row) for row in rows)

    @tool
    async def select_goals(
        selections: list[GoalPick] | None = None,
        is_new_goal_instead: bool = False,
        note: str = "",
        candidate_ids: list[int] | None = None,
    ) -> str:
        """Finish the search. Call this once, after any searches you need.

        selections: one entry per matched goal, with goal_id and scope.
        Use scope "series" when the user means the whole recurring goal, otherwise "instance".
        Leave selections empty when nothing matches, or when several goals fit and you cannot tell which.
        candidate_ids: up to 3 goal ids to show the user when the match is ambiguous.
        is_new_goal_instead: true only when cancelling, and the user wants to cancel something in real life
        (a subscription, trial, membership, appointment, or order) that is not one of the tracked goals.
        """
        captured.finished = True
        captured.is_new_goal_instead = bool(is_new_goal_instead)
        captured.note = note or ""
        captured.candidate_ids = []
        for goal_id in candidate_ids or []:
            try:
                parsed_id = int(goal_id)
            except (TypeError, ValueError):
                continue
            if parsed_id not in captured.candidate_ids:
                captured.candidate_ids.append(parsed_id)
            if len(captured.candidate_ids) == 3:
                break

        cleaned = []
        for item in selections or []:
            if isinstance(item, GoalPick):
                goal_id = item.goal_id
                scope = item.scope
            elif isinstance(item, dict):
                try:
                    goal_id = int(item.get("goal_id") or 0)
                except (TypeError, ValueError):
                    continue
                scope = item.get("scope") or "instance"
            else:
                continue
            if scope not in ("instance", "series"):
                scope = "instance"
            if goal_id > 0:
                cleaned.append({"goal_id": goal_id, "scope": scope})
        captured.selections = cleaned
        return "Recorded."

    return [search_goals, select_goals]


def _system_prompt(intent, now, candidates, explicit_text) -> str:
    weekday = now.strftime("%A")
    cancel_rule = ""
    if intent == "cancel":
        cancel_rule = (
            "\nIf the user is describing a real-life cancellation they still have to do "
            "(subscription, trial, membership, appointment, order) and it is not one of "
            "the tracked goals above, call select_goals with an empty selections list and "
            "is_new_goal_instead true. Do not pick a vaguely similar goal.\n"
        )
    return f"""It is {weekday}, {now.strftime("%Y-%m-%d %H:%M")} (Europe/Berlin).
The user wants to {_INTENT.get(intent, intent)}.

Explicit #ids mentioned (already looked up):
{explicit_text}

Upcoming goals (next due instance; a recurring series appears once):
{_format_candidates(candidates["upcoming"])}

Recently set goals, excluding anything already listed above:
{_format_candidates(candidates["recent"])}

Use search_goals only when the goal is not clearly in those lists or the explicit ids.
Then call select_goals exactly once.
- Prefer an explicit #id when it is active and matches the request.
- scope "series" for the whole recurring goal; "instance" for one occurrence.
- If several goals fit and you cannot tell which, return no selections. Put up to 3 plausible ids in candidate_ids and explain in note.
- For edit, done, and failed, is_new_goal_instead must stay false.
{cancel_rule}"""


async def _validate_selections(user_id, chat_id, selections):
    if not selections:
        return []
    rows = await fetch_goals_for_user(
        user_id, chat_id, [item["goal_id"] for item in selections]
    )
    active = {row["goal_id"] for row in rows if row["status"] in _ACTIVE}
    return [item for item in selections if item["goal_id"] in active]


async def _run_finder_loop(model_key, user_id, chat_id, intent, request_text, explicit_text, candidates):
    captured = FinderResult()
    tools = _finder_tools(user_id, chat_id, captured)
    llm = llms[model_key]
    llm_with_tools = llm.bind_tools(tools, tool_choice="required")
    tool_map = {item.name: item for item in tools}
    now = datetime.now(tz=BERLIN_TZ)
    messages = [
        SystemMessage(content=_system_prompt(intent, now, candidates, explicit_text)),
        HumanMessage(content=request_text or "(empty message)"),
    ]

    for iteration in range(MAX_FINDER_ITERATIONS):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)
        if not response.tool_calls:
            break
        for call in response.tool_calls:
            tool_fn = tool_map.get(call["name"])
            if tool_fn is None:
                result_text = f"Unknown tool: {call['name']}"
            else:
                result_text = await tool_fn.ainvoke(call["args"])
            if captured.finished:
                captured.selections = await _validate_selections(
                    user_id, chat_id, captured.selections
                )
                logger.info(
                    f"finder selected {captured.selections} "
                    f"new_goal={captured.is_new_goal_instead} via {model_key}"
                )
                return captured
            messages.append(ToolMessage(content=str(result_text), tool_call_id=call["id"]))
        logger.info(f"finder iter {iteration + 1} on {model_key} did not select yet")

    captured.selections = await _validate_selections(user_id, chat_id, captured.selections)
    return captured


async def find_matching_goals(user_id, chat_id, intent, request_text, reply_text=None):
    """Return a FinderResult. IDs are limited to this user's active goals."""
    candidates = await fetch_goal_candidate_lists(user_id, chat_id)
    requested_ids = mentioned_goal_ids(request_text, reply_text)
    explicit_rows = await fetch_goals_for_user(user_id, chat_id, requested_ids)
    explicit_text = _format_explicit(requested_ids, explicit_rows)
    full_request = request_text or ""
    if reply_text:
        full_request = f"{full_request}\n\n(As a reply to message: {reply_text})"

    primary = "openrouter_smart" if "openrouter_smart" in llms else "smart"
    try:
        return await _run_finder_loop(
            primary, user_id, chat_id, intent, full_request, explicit_text, candidates
        )
    except Exception as e:
        logger.warning(f"Goal finder ({primary}) failed: {e}")
        if primary == "smart":
            raise
        return await _run_finder_loop(
            "smart", user_id, chat_id, intent, full_request, explicit_text, candidates
        )
