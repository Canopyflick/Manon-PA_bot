"""HTML text and keyboards for library messages."""
import html
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from utils.helpers import BERLIN_TZ


def priority_label(priority):
    return "must-read" if priority == "must_read" else "maybe"


def format_added(value):
    if value is None:
        return ""
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=BERLIN_TZ)
    else:
        value = value.astimezone(BERLIN_TZ)
    return value.strftime("%d %b %Y").lstrip("0")


def link_html(item):
    url = item["url"] or ""
    title = (item["title"] or url).strip() or url
    if len(title) > 180:
        title = title[:177].rstrip() + "…"
    return f'<a href="{html.escape(url, quote=True)}">{html.escape(title)}</a>'


def _note_line(item):
    note = (item["note"] or "").strip()
    if not note:
        return None
    return f"<i>{html.escape(note)}</i>"


def format_file_result(item, action):
    label = priority_label(item["priority"])
    added = format_added(item["added_at"])
    item_id = item["item_id"]
    if action == "filed":
        head = f"📚 Filed #{item_id} ({label})"
    elif action == "updated":
        head = f"📚 Already in your library #{item_id} (added {added}). Updated the note ({label})"
    elif action == "exists":
        head = f"📚 Already in your library #{item_id} (added {added})"
    elif action == "reopened":
        head = f"📚 Reopened #{item_id} ({label})"
    else:
        head = f"📚 #{item_id} is {label}"
    parts = [head, "", link_html(item)]
    note = _note_line(item)
    if note:
        parts.append(note)
    return "\n".join(parts)


def format_item_message(item):
    star = "⭐ " if item["priority"] == "must_read" else ""
    parts = [f"{star}#{item['item_id']} {link_html(item)}", format_added(item["added_at"])]
    note = _note_line(item)
    if note:
        parts.append(note)
    return "\n".join(parts)


def format_closed(item):
    if item["status"] == "read":
        head = f"✅ Read #{item['item_id']}"
    else:
        head = f"🗄 Archived #{item['item_id']}"
    parts = [head, "", link_html(item)]
    note = _note_line(item)
    if note:
        parts.append(note)
    return "\n".join(parts)


def format_random_pick(item):
    parts = [f"📚 On {format_added(item['added_at'])} you filed this for later:", "", link_html(item)]
    note = _note_line(item)
    if note:
        parts.append(note)
    return "\n".join(parts)


def format_library_list(items, limit=None):
    head = "📚 <b>Library</b>"
    if limit:
        head += f" · {len(items)}"
    lines = [head]
    current = None
    for item in items:
        tier = item["priority"]
        if tier != current:
            current = tier
            lines.append("")
            if tier == "must_read":
                lines.append("⭐ <b>Must-read</b>")
            else:
                lines.append("🤷 <b>Maybe</b>")
        lines.append("")
        lines.append(f"#{item['item_id']} {link_html(item)} · {format_added(item['added_at'])}")
        note = _note_line(item)
        if note:
            lines.append(note)
    return "\n".join(lines)


def toggle_button(item):
    item_id = item["item_id"]
    if item["priority"] == "must_read":
        return InlineKeyboardButton("⬇️ Make maybe", callback_data=f"lib_demote_{item_id}")
    return InlineKeyboardButton("⬆️ Make must-read", callback_data=f"lib_promote_{item_id}")


def item_keyboard(item, *, full):
    toggle = toggle_button(item)
    if not full:
        return InlineKeyboardMarkup([[toggle]])
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Read", callback_data=f"lib_read_{item['item_id']}"),
        InlineKeyboardButton("🗄 Archive", callback_data=f"lib_archive_{item['item_id']}"),
        toggle,
    ]])


def closed_keyboard(item):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("↩️ Undo", callback_data=f"lib_reopen_{item['item_id']}")
    ]])


def random_keyboard(item):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Read", callback_data=f"lib_read_{item['item_id']}"),
        InlineKeyboardButton("🗄 Archive", callback_data=f"lib_archive_{item['item_id']}"),
    ]])


def report_keyboard(limit_token):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📋 Report", callback_data=f"lib_report_{limit_token}")
    ]])


def markup_is_full(message):
    markup = getattr(message, "reply_markup", None) if message else None
    if not markup or not markup.inline_keyboard:
        return False
    return len(markup.inline_keyboard[0]) >= 3
