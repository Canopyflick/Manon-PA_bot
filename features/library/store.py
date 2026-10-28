"""manon_library queries."""
from datetime import datetime

from utils.db import Database
from utils.helpers import BERLIN_TZ

_OPEN_ORDER = """
    ORDER BY CASE WHEN priority = 'must_read' THEN 0 ELSE 1 END,
             added_at DESC,
             item_id DESC
"""


async def file_item(user_id, chat_id, url, title, note, priority, note_was_sent=False):
    """Insert a link, or update the one already stored for this chat.

    Returns (row, action) where action is filed, updated, exists, or reopened.
    A new note can promote an item to must-read. It does not demote one.
    ``note`` may be None when the note was only a priority instruction.
    """
    title = title or url
    if priority not in ("must_read", "maybe"):
        priority = "maybe"
    note = (note or "").strip() or None
    promote = note_was_sent and priority == "must_read"
    stored_note = note if note_was_sent else None

    async with Database.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO manon_users (user_id, chat_id)
                VALUES ($1, $2)
                ON CONFLICT (user_id, chat_id) DO NOTHING
                """,
                user_id,
                chat_id,
            )
            existing = await conn.fetchrow(
                """
                SELECT * FROM manon_library
                WHERE user_id = $1 AND chat_id = $2 AND url = $3
                """,
                user_id,
                chat_id,
                url,
            )
            if existing is None:
                row = await conn.fetchrow(
                    """
                    INSERT INTO manon_library (user_id, chat_id, url, title, note, priority)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING *
                    """,
                    user_id,
                    chat_id,
                    url,
                    title,
                    note,
                    "must_read" if promote else "maybe",
                )
                return row, "filed"

            stored_title = _preferred_title(title, url, existing["title"])
            priority_changed = promote and existing["priority"] != "must_read"
            note_changed = stored_note is not None and stored_note != (existing["note"] or None)
            if existing["status"] == "open":
                if not note_changed and not priority_changed and stored_title == existing["title"]:
                    return existing, "exists"
                row = await _update_open_item(
                    conn, existing["item_id"], stored_note, promote, stored_title
                )
                if note_changed:
                    return row, "updated"
                if priority_changed:
                    return row, "priority"
                return row, "exists"

            row = await conn.fetchrow(
                """
                UPDATE manon_library
                SET status = 'open',
                    closed_at = NULL,
                    note = COALESCE($2, note),
                    priority = CASE
                        WHEN $3 THEN 'must_read'
                        ELSE priority
                    END,
                    title = $4
                WHERE item_id = $1
                RETURNING *
                """,
                existing["item_id"],
                stored_note,
                promote,
                stored_title,
            )
            return row, "reopened"


async def _update_open_item(conn, item_id, note, promote, title):
    return await conn.fetchrow(
        """
        UPDATE manon_library
        SET note = COALESCE($2, note),
            priority = CASE
                WHEN $3 THEN 'must_read'
                ELSE priority
            END,
            title = $4
        WHERE item_id = $1
        RETURNING *
        """,
        item_id,
        note,
        promote,
        title,
    )


def _preferred_title(fetched, url, current):
    if fetched and fetched != url:
        return fetched
    if current and current != url:
        return current
    return fetched or current or url


async def get_item(item_id, user_id, chat_id):
    async with Database.acquire() as conn:
        return await conn.fetchrow(
            """
            SELECT * FROM manon_library
            WHERE item_id = $1 AND user_id = $2 AND chat_id = $3
            """,
            item_id,
            user_id,
            chat_id,
        )


async def get_item_by_url(user_id, chat_id, url):
    async with Database.acquire() as conn:
        return await conn.fetchrow(
            """
            SELECT * FROM manon_library
            WHERE user_id = $1 AND chat_id = $2 AND url = $3
            """,
            user_id,
            chat_id,
            url,
        )


async def list_open_items(user_id, chat_id, limit=None):
    """Open items, must-reads first, newest first within each tier."""
    async with Database.acquire() as conn:
        if limit is None:
            rows = await conn.fetch(
                f"""
                SELECT * FROM manon_library
                WHERE user_id = $1 AND chat_id = $2 AND status = 'open'
                {_OPEN_ORDER}
                """,
                user_id,
                chat_id,
            )
        else:
            rows = await conn.fetch(
                f"""
                SELECT * FROM manon_library
                WHERE user_id = $1 AND chat_id = $2 AND status = 'open'
                {_OPEN_ORDER}
                LIMIT $3
                """,
                user_id,
                chat_id,
                limit,
            )
    return list(rows)


async def random_open_item(user_id, chat_id):
    async with Database.acquire() as conn:
        return await conn.fetchrow(
            """
            SELECT * FROM manon_library
            WHERE user_id = $1 AND chat_id = $2 AND status = 'open'
            ORDER BY random()
            LIMIT 1
            """,
            user_id,
            chat_id,
        )


async def set_item_status(item_id, user_id, chat_id, status):
    closed_at = None if status == "open" else datetime.now(tz=BERLIN_TZ)
    async with Database.acquire() as conn:
        return await conn.fetchrow(
            """
            UPDATE manon_library
            SET status = $4,
                closed_at = $5
            WHERE item_id = $1 AND user_id = $2 AND chat_id = $3
            RETURNING *
            """,
            item_id,
            user_id,
            chat_id,
            status,
            closed_at,
        )


async def set_item_priority(item_id, user_id, chat_id, priority):
    """Change priority of an open item. Returns None when it is not open."""
    async with Database.acquire() as conn:
        return await conn.fetchrow(
            """
            UPDATE manon_library
            SET priority = $4
            WHERE item_id = $1 AND user_id = $2 AND chat_id = $3 AND status = 'open'
            RETURNING *
            """,
            item_id,
            user_id,
            chat_id,
            priority,
        )


async def users_with_open_items():
    async with Database.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT user_id, chat_id
            FROM manon_library
            WHERE status = 'open'
            """
        )
    return [(row["user_id"], row["chat_id"]) for row in rows]
