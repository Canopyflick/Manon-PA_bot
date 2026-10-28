"""Recognize a library intake message and pull a page title out of HTML.

A library message is the whole text: a URL, or a URL, a colon, and a note.
A URL mentioned inside a sentence is not one.
"""
import html
import re

_STATUS_WORDS = {
    "done": "read",
    "read": "read",
    "archive": "archived",
    "archived": "archived",
}

# Longer keywords first so "archived" is not consumed as "archive".
_ATTACHED_STATUS = re.compile(
    r"^(https?://\S+?):(archived|archive|done|read)\s*$",
    re.IGNORECASE,
)
_NOTE = re.compile(
    r"^(https?://\S+):\s+(\S.*?)\s*$",
    re.IGNORECASE,
)
_EMPTY_NOTE = re.compile(
    r"^(https?://\S+):\s*$",
    re.IGNORECASE,
)
_BARE_URL = re.compile(
    r"^https?://\S+$",
    re.IGNORECASE,
)

_OG_TITLE = re.compile(
    r"""<meta\s[^>]*?property\s*=\s*["']og:title["'][^>]*?content\s*=\s*["']([^"']*)["']""",
    re.IGNORECASE,
)
_OG_TITLE_REV = re.compile(
    r"""<meta\s[^>]*?content\s*=\s*["']([^"']*)["'][^>]*?property\s*=\s*["']og:title["']""",
    re.IGNORECASE,
)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

_TITLE_MAX = 300


def parse_library_message(text):
    """Return ("file", url, note), ("status", url, "read"|"archived"), or None.

    ``note`` is None when the message is only a URL. A status word
    (done, read, archive, archived) after the colon marks the item instead
    of filing a note. Colons inside the URL, including ports, stay part of it.
    """
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not text:
        return None

    attached = _ATTACHED_STATUS.match(text)
    if attached:
        return ("status", attached.group(1), _STATUS_WORDS[attached.group(2).lower()])

    noted = _NOTE.match(text)
    if noted:
        url, note = noted.group(1), noted.group(2).strip()
        status = _STATUS_WORDS.get(note.lower())
        if status:
            return ("status", url, status)
        return ("file", url, note)

    empty = _EMPTY_NOTE.match(text)
    if empty:
        return ("file", empty.group(1), None)

    if _BARE_URL.match(text):
        return ("file", text, None)
    return None


def extract_title(page_html):
    """og:title, then <title>. None when nothing usable is there."""
    if not isinstance(page_html, str) or not page_html:
        return None
    for pattern in (_OG_TITLE, _OG_TITLE_REV):
        match = pattern.search(page_html)
        if match:
            title = _clean_title(match.group(1))
            if title:
                return title
    match = _TITLE.search(page_html)
    if match:
        return _clean_title(match.group(1))
    return None


def _clean_title(raw):
    text = html.unescape(raw or "")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None
    if len(text) > _TITLE_MAX:
        return text[: _TITLE_MAX - 1].rstrip() + "…"
    return text
