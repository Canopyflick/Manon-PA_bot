"""Library intake, /library, item buttons, and the Friday pick."""
import asyncio
import logging
import re

import aiohttp

from features.library.messages import (
    closed_keyboard,
    format_closed,
    format_file_result,
    format_item_message,
    format_library_list,
    format_random_pick,
    item_keyboard,
    markup_is_full,
    random_keyboard,
    report_keyboard,
)
from features.library.parsing import extract_title, parse_library_message
from features.library.store import (
    file_item,
    get_item,
    get_item_by_url,
    list_open_items,
    random_open_item,
    set_item_priority,
    set_item_status,
    users_with_open_items,
)
from utils.session_avatar import PA

logger = logging.getLogger(__name__)

_NOTE_MAX = 500
_TITLE_READ_LIMIT = 250_000
_FETCH_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
_CALLBACK = re.compile(r"^lib_(read|archive|reopen|promote|demote)_(\d+)$")
_REPORT = re.compile(r"^lib_report_(\d+)$")


async def handle_library_message(update, context, user_message):
    """File or settle a link when the message is only a URL (plus an optional note)."""
    parsed = parse_library_message(user_message)
    if parsed is None:
        return False

    kind, url, extra = parsed
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        if kind == "status":
            await _mark_by_url(update, user_id, chat_id, url, extra)
        else:
            await _file_from_message(update, user_id, chat_id, url, extra)
    except Exception as e:
        logger.error(f"library intake failed: {e}")
        await update.message.reply_text(f"Couldn't file that link {PA}")
    return True


async def library_command(update, context):
    limit = None
    if context.args:
        token = context.args[0] if len(context.args) == 1 else ""
        if not token.isdigit() or int(token) < 1:
            await update.message.reply_text("Use /library or /library 5")
            return
        limit = int(token)

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        items = await list_open_items(user_id, chat_id, limit)
    except Exception as e:
        logger.error(f"library list failed: {e}")
        await update.message.reply_text(f"Couldn't open your library {PA}")
        return
    await _send_compact_list(update.message, items, 0 if limit is None else limit)


async def handle_library_callback(update, context):
    query = update.callback_query
    match = _CALLBACK.match(query.data or "")
    if not match:
        await query.answer("Invalid action.")
        return

    action = match.group(1)
    item_id = int(match.group(2))
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        if action in ("read", "archive"):
            status = "read" if action == "read" else "archived"
            await _close_item(query, item_id, user_id, chat_id, status)
        elif action == "reopen":
            await _reopen_item(query, item_id, user_id, chat_id)
        else:
            priority = "must_read" if action == "promote" else "maybe"
            await _retier_item(query, item_id, user_id, chat_id, priority)
    except Exception as e:
        logger.error(f"library callback {action} #{item_id} failed: {e}")
        try:
            await query.answer("Something went wrong.")
        except Exception:
            logger.error(f"couldn't answer library callback for #{item_id}")


async def handle_library_report(update, context):
    query = update.callback_query
    match = _REPORT.match(query.data or "")
    if not match:
        await query.answer("Invalid action.")
        return

    limit_token = int(match.group(1))
    limit = None if limit_token == 0 else limit_token
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    await query.answer()
    try:
        items = await list_open_items(user_id, chat_id, limit)
    except Exception as e:
        logger.error(f"library report failed: {e}")
        await query.message.reply_text(f"Couldn't open your library {PA}")
        return

    if not items:
        await query.message.reply_text(f"Your library is empty {PA}")
        return

    for index, item in enumerate(items):
        if index:
            await asyncio.sleep(0.25)
        try:
            await query.message.reply_text(
                format_item_message(item),
                parse_mode="HTML",
                reply_markup=item_keyboard(item, full=True),
            )
        except Exception as e:
            logger.error(f"library report stopped after {index} items: {e}")
            await query.message.reply_text(f"Stopped after {index} items {PA}")
            break

    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception as e:
        logger.info(f"could not clear the library report button: {e}")


async def send_random_library_item(bot, user_id, chat_id):
    """Send one open library item. Returns False when there is nothing to send."""
    try:
        item = await random_open_item(user_id, chat_id)
        if not item:
            return False
        text = format_random_pick(item)
        markup = random_keyboard(item)
        try:
            await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
        except Exception as e:
            logger.warning(f"library pick HTML failed, retrying plain: {e}")
            await bot.send_message(chat_id, _plain(text), reply_markup=markup)
        return True
    except Exception as e:
        logger.error(f"random library item failed for user {user_id}: {e}")
        return False


async def send_weekly_library_pick(bot):
    try:
        pairs = await users_with_open_items()
    except Exception as e:
        logger.error(f"weekly library pick could not list users: {e}")
        return
    for user_id, chat_id in pairs:
        await send_random_library_item(bot, user_id, chat_id)


async def _file_from_message(update, user_id, chat_id, url, note_raw):
    if note_raw:
        title, interpreted = await asyncio.gather(
            fetch_page_title(url),
            interpret_note(note_raw),
        )
        note, priority = interpreted
    else:
        title = await fetch_page_title(url)
        note, priority = None, "maybe"

    row, action = await file_item(
        user_id,
        chat_id,
        url,
        title or url,
        note,
        priority,
        note_was_sent=bool(note_raw),
    )
    await _reply_html(
        update.message,
        format_file_result(row, action),
        item_keyboard(row, full=False),
    )


async def _mark_by_url(update, user_id, chat_id, url, status):
    item = await get_item_by_url(user_id, chat_id, url)
    if item is None:
        await update.message.reply_text(f"That link isn't in your library {PA}")
        return
    if item["status"] == status:
        word = "read" if status == "read" else "archived"
        await update.message.reply_text(f"#{item['item_id']} is already {word} {PA}")
        return
    updated = await set_item_status(item["item_id"], user_id, chat_id, status)
    await _reply_html(update.message, format_closed(updated), closed_keyboard(updated))


async def _close_item(query, item_id, user_id, chat_id, status):
    current = await get_item(item_id, user_id, chat_id)
    if current is None:
        await query.answer("That one isn't yours.")
        return
    if current["status"] != "open":
        await query.answer("Already settled.")
        return
    updated = await set_item_status(item_id, user_id, chat_id, status)
    if updated is None:
        await query.answer("That one isn't yours.")
        return
    await query.answer("Read" if status == "read" else "Archived")
    await _edit_html(query, format_closed(updated), closed_keyboard(updated))


async def _reopen_item(query, item_id, user_id, chat_id):
    current = await get_item(item_id, user_id, chat_id)
    if current is None:
        await query.answer("That one isn't yours.")
        return
    if current["status"] == "open":
        await query.answer("Already open.")
        return
    updated = await set_item_status(item_id, user_id, chat_id, "open")
    await query.answer("Back in the library.")
    await _edit_html(query, format_item_message(updated), item_keyboard(updated, full=True))


async def _retier_item(query, item_id, user_id, chat_id, priority):
    updated = await set_item_priority(item_id, user_id, chat_id, priority)
    if updated is None:
        await query.answer("That one's already closed.")
        return
    full = markup_is_full(query.message)
    text = format_item_message(updated) if full else format_file_result(updated, "priority")
    await query.answer("Must-read" if priority == "must_read" else "Maybe")
    await _edit_html(query, text, item_keyboard(updated, full=full))


async def _send_compact_list(message, items, limit_token):
    if not items:
        await message.reply_text(f"Your library is empty {PA}")
        return
    limit = None if limit_token == 0 else limit_token
    chunks = _split(format_library_list(items, limit))
    last = len(chunks) - 1
    for index, chunk in enumerate(chunks):
        markup = report_keyboard(limit_token) if index == last else None
        await _reply_html(message, chunk, markup)


async def fetch_page_title(url):
    timeout = aiohttp.ClientTimeout(total=5)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                url,
                headers={"User-Agent": _FETCH_UA, "Accept": "text/html"},
                allow_redirects=True,
                max_redirects=5,
            ) as resp:
                if resp.status >= 400:
                    return None
                ctype = (resp.headers.get("Content-Type") or "").lower()
                if ctype and "html" not in ctype and "xml" not in ctype and "text/" not in ctype:
                    return None
                raw = await resp.content.read(_TITLE_READ_LIMIT)
                encoding = resp.charset or "utf-8"
                return extract_title(raw.decode(encoding, errors="replace"))
    except Exception as e:
        logger.info(f"library title fetch failed for {url}: {e}")
        return None


async def interpret_note(raw):
    """Clean a note and decide must-read vs maybe. Falls back to the raw note."""
    raw = raw.strip()[:_NOTE_MAX]
    try:
        from LLMs.orchestration import run_chain
        result = await run_chain("library_note", {"note": raw})
    except Exception as e:
        logger.error(f"library note interpretation failed: {e}")
        return raw, "maybe"

    note = getattr(result, "note", None)
    if isinstance(note, str):
        note = note.strip()[:_NOTE_MAX] or None
    else:
        note = None
    priority = getattr(result, "priority", "maybe")
    if priority not in ("must_read", "maybe"):
        priority = "maybe"
    return note, priority


def _split(text):
    from LLMs.orchestration import split_message
    return split_message(text)


async def _reply_html(message, text, reply_markup):
    try:
        await message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.warning(f"library HTML send failed, retrying plain: {e}")
        await message.reply_text(_plain(text), reply_markup=reply_markup)


async def _edit_html(query, text, reply_markup):
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        if "not modified" in str(e).lower():
            return
        logger.warning(f"library HTML edit failed, retrying plain: {e}")
        await query.edit_message_text(_plain(text), reply_markup=reply_markup)


def _plain(text):
    import html as html_lib
    return html_lib.unescape(re.sub(r"<[^>]+>", "", text))
