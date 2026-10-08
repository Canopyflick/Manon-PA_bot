"""Goals API. External apps upsert rows in manon_goals; Manon reads the same table."""

import logging
import re
from datetime import datetime, timedelta, timezone

import aiohttp
from aiohttp import web

from api.auth import set_http_session, verify_access_token
from utils.db import Database, setup_database
from utils.environment_vars import ENV_VARS
from utils.helpers import BERLIN_TZ

logger = logging.getLogger(__name__)

EXTERNAL_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
OPEN_STATUSES = ("prepared", "pending", "paused", "limbo")


def allowed_origins() -> set[str]:
    raw = ENV_VARS.GOALS_API_CORS_ORIGINS or ""
    return {item.strip() for item in raw.split(",") if item.strip()}


def _cors_headers(origin: str | None) -> dict[str, str]:
    if not origin or origin not in allowed_origins():
        return {}
    return {
        "Access-Control-Allow-Origin": origin,
        "Vary": "Origin",
        "Access-Control-Allow-Headers": "Authorization, Content-Type",
        "Access-Control-Allow-Methods": "GET, PUT, DELETE, OPTIONS",
        "Access-Control-Max-Age": "600",
    }


@web.middleware
async def cors_middleware(request: web.Request, handler):
    origin = request.headers.get("Origin")
    if request.method == "OPTIONS":
        if origin and origin not in allowed_origins():
            return web.json_response({"error": "Origin not allowed"}, status=403)
        response = web.Response(status=204)
    else:
        response = await handler(request)
    response.headers.update(_cors_headers(origin))
    return response


@web.middleware
async def auth_middleware(request: web.Request, handler):
    if request.path == "/healthz" or request.method == "OPTIONS":
        return await handler(request)
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return web.json_response({"error": "Missing bearer token"}, status=401)
    try:
        claims = await verify_access_token(header[7:].strip())
    except Exception as exc:
        logger.info("Rejected access token: %s", exc)
        return web.json_response({"error": "Invalid token"}, status=401)
    sub = claims.get("sub")
    if not sub:
        return web.json_response({"error": "Invalid token"}, status=401)
    async with Database.acquire() as conn:
        user = await conn.fetchrow(
            """
            SELECT user_id, chat_id
            FROM manon_users
            WHERE auth_user_id = $1::uuid
            """,
            sub,
        )
    if not user:
        return web.json_response({"error": "No Manon user linked to this login"}, status=403)
    request["manon_user"] = user
    return await handler(request)


def _user(request: web.Request) -> tuple[int, int]:
    user = request["manon_user"]
    return user["user_id"], user["chat_id"]


def _check_external_id(external_id: str) -> web.Response | None:
    if not EXTERNAL_ID.match(external_id or ""):
        return web.json_response({"error": "Invalid goal id"}, status=400)
    return None


async def _writable_source(conn, source: str) -> web.Response | None:
    row = await conn.fetchrow(
        "SELECT api_writable FROM goal_sources WHERE source = $1",
        source,
    )
    if not row:
        return web.json_response({"error": "Unknown source"}, status=404)
    if not row["api_writable"]:
        return web.json_response({"error": "Source is not writable via the API"}, status=403)
    return None


def _goal_payload(row) -> dict:
    done = row["status"] == "archived_done"
    completed = row["completion_time"] if done else None
    updated = row["updated_at"]
    return {
        "id": row["external_id"],
        "text": row["goal_description"] or "",
        "urgent": bool(row["urgent"]),
        "done": done,
        "completedAt": completed.isoformat() if completed else None,
        "sortOrder": row["sort_order"],
        "updatedAt": updated.isoformat() if updated else None,
    }


def _parse_done_since(raw: str | None) -> datetime | web.Response:
    if not raw:
        return datetime.now(BERLIN_TZ) - timedelta(days=2)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return web.json_response({"error": "done_since must be an ISO timestamp"}, status=400)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parse_completed_at(value, done: bool) -> datetime | None | web.Response:
    if not done:
        return None
    if value is None:
        return datetime.now(BERLIN_TZ)
    if not isinstance(value, str):
        return web.json_response({"error": "completedAt must be an ISO timestamp or null"}, status=400)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return web.json_response({"error": "completedAt must be an ISO timestamp or null"}, status=400)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BERLIN_TZ)
    return parsed


async def healthz(_request: web.Request) -> web.Response:
    try:
        async with Database.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        logger.exception("healthz database check failed")
        return web.json_response({"ok": False}, status=503)
    return web.json_response({"ok": True})


async def list_goals(request: web.Request) -> web.Response:
    source = request.match_info["source"]
    done_since = _parse_done_since(request.query.get("done_since"))
    if isinstance(done_since, web.Response):
        return done_since
    user_id, chat_id = _user(request)
    async with Database.acquire() as conn:
        rejected = await _writable_source(conn, source)
        if rejected:
            return rejected
        rows = await conn.fetch(
            """
            SELECT external_id, goal_description, urgent, status,
                   completion_time, sort_order, updated_at
            FROM manon_goals
            WHERE user_id = $1 AND chat_id = $2 AND source = $3
              AND (
                    status = ANY($4::text[])
                    OR (status = 'archived_done' AND completion_time >= $5)
                  )
            ORDER BY sort_order NULLS LAST, created_at ASC
            """,
            user_id,
            chat_id,
            source,
            list(OPEN_STATUSES),
            done_since,
        )
    return web.json_response({"goals": [_goal_payload(row) for row in rows]})


async def upsert_goal(request: web.Request) -> web.Response:
    source = request.match_info["source"]
    external_id = request.match_info["external_id"]
    rejected_id = _check_external_id(external_id)
    if rejected_id:
        return rejected_id
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Expected JSON"}, status=400)
    if not isinstance(body, dict):
        return web.json_response({"error": "Expected a JSON object"}, status=400)
    text = body.get("text")
    if not isinstance(text, str) or not text.strip() or len(text) > 4000:
        return web.json_response({"error": "text is required (max 4000 characters)"}, status=400)
    if not isinstance(body.get("done"), bool):
        return web.json_response({"error": "done must be a boolean"}, status=400)
    if not isinstance(body.get("urgent"), bool):
        return web.json_response({"error": "urgent must be a boolean"}, status=400)
    urgent = body["urgent"]
    completed = _parse_completed_at(body.get("completedAt"), body["done"])
    if isinstance(completed, web.Response):
        return completed
    sort_order = body.get("sortOrder", None)
    if sort_order is not None and not isinstance(sort_order, (int, float)):
        return web.json_response({"error": "sortOrder must be a number or null"}, status=400)
    status = "archived_done" if body["done"] else "prepared"
    user_id, chat_id = _user(request)

    async with Database.acquire() as conn:
        rejected = await _writable_source(conn, source)
        if rejected:
            return rejected
        async with conn.transaction():
            await conn.execute("SELECT set_config('app.actor', $1, true)", source)
            row = await conn.fetchrow(
                """
                INSERT INTO manon_goals (
                    user_id, chat_id, status, timeframe, recurrence_type,
                    goal_description, source, external_id, urgent, sort_order,
                    completion_time, set_time
                ) VALUES (
                    $1, $2, $3, 'open-ended', 'one-time',
                    $4, $5, $6, $7, $8,
                    $9, NOW()
                )
                ON CONFLICT (source, external_id) WHERE external_id IS NOT NULL
                DO UPDATE SET
                    goal_description = EXCLUDED.goal_description,
                    status = EXCLUDED.status,
                    urgent = EXCLUDED.urgent,
                    sort_order = COALESCE(EXCLUDED.sort_order, manon_goals.sort_order),
                    completion_time = EXCLUDED.completion_time,
                    timeframe = 'open-ended'
                WHERE manon_goals.user_id = EXCLUDED.user_id
                  AND manon_goals.chat_id = EXCLUDED.chat_id
                RETURNING external_id, goal_description, urgent, status,
                          completion_time, sort_order, updated_at
                """,
                user_id,
                chat_id,
                status,
                text.strip(),
                source,
                external_id,
                urgent,
                float(sort_order) if sort_order is not None else None,
                completed,
            )
    if not row:
        return web.json_response({"error": "Goal belongs to another user"}, status=403)
    return web.json_response(_goal_payload(row))


async def delete_goal(request: web.Request) -> web.Response:
    source = request.match_info["source"]
    external_id = request.match_info["external_id"]
    rejected_id = _check_external_id(external_id)
    if rejected_id:
        return rejected_id
    user_id, chat_id = _user(request)
    async with Database.acquire() as conn:
        rejected = await _writable_source(conn, source)
        if rejected:
            return rejected
        async with conn.transaction():
            await conn.execute("SELECT set_config('app.actor', $1, true)", source)
            row = await conn.fetchrow(
                """
                UPDATE manon_goals
                SET status = 'archived_canceled',
                    completion_time = COALESCE(completion_time, NOW())
                WHERE source = $1 AND external_id = $2
                  AND user_id = $3 AND chat_id = $4
                  AND status <> 'archived_canceled'
                RETURNING goal_id
                """,
                source,
                external_id,
                user_id,
                chat_id,
            )
            if row:
                return web.Response(status=204)
            exists = await conn.fetchval(
                """
                SELECT 1 FROM manon_goals
                WHERE source = $1 AND external_id = $2
                  AND user_id = $3 AND chat_id = $4
                """,
                source,
                external_id,
                user_id,
                chat_id,
            )
    if exists:
        return web.Response(status=204)
    return web.json_response({"error": "Goal not found"}, status=404)


async def reorder_goals(request: web.Request) -> web.Response:
    source = request.match_info["source"]
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Expected JSON"}, status=400)
    ids = body.get("ids") if isinstance(body, dict) else None
    if not isinstance(ids, list) or any(not isinstance(item, str) or not EXTERNAL_ID.match(item) for item in ids):
        return web.json_response({"error": "ids must be a list of goal ids"}, status=400)
    user_id, chat_id = _user(request)
    orders = [float(index) for index in range(len(ids))]
    async with Database.acquire() as conn:
        rejected = await _writable_source(conn, source)
        if rejected:
            return rejected
        async with conn.transaction():
            await conn.execute("SELECT set_config('app.actor', $1, true)", source)
            await conn.execute(
                """
                UPDATE manon_goals AS g
                SET sort_order = data.ord
                FROM unnest($1::text[], $2::float8[]) AS data(external_id, ord)
                WHERE g.source = $3
                  AND g.external_id = data.external_id
                  AND g.user_id = $4
                  AND g.chat_id = $5
                """,
                ids,
                orders,
                source,
                user_id,
                chat_id,
            )
    return web.json_response({"ok": True})


def create_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware, auth_middleware])
    app.router.add_get("/healthz", healthz)
    app.router.add_get("/v1/sources/{source}/goals", list_goals)
    app.router.add_put("/v1/sources/{source}/goals:order", reorder_goals)
    app.router.add_put("/v1/sources/{source}/goals/{external_id}", upsert_goal)
    app.router.add_delete("/v1/sources/{source}/goals/{external_id}", delete_goal)
    app.router.add_route("OPTIONS", "/{tail:.*}", lambda _request: web.Response(status=204))
    return app


async def serve() -> None:
    if not ENV_VARS.SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is required to start the goals API")
    await Database.initialize()
    await setup_database()
    session = aiohttp.ClientSession()
    set_http_session(session)
    runner = web.AppRunner(create_app())
    await runner.setup()
    port = ENV_VARS.GOALS_API_PORT
    await web.TCPSite(runner, "0.0.0.0", port).start()
    logger.info("Goals API listening on 0.0.0.0:%s", port)
    await asyncio_forever()


async def asyncio_forever() -> None:
    import asyncio

    await asyncio.Event().wait()
