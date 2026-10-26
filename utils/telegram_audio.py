"""Telegram voice notes versus audio sent through the system share sheet."""

from __future__ import annotations

_AUDIO_EXTENSIONS = frozenset(
    {"aac", "flac", "m4a", "mp3", "mpeg", "mpga", "ogg", "opus", "wav"}
)
_MIME_SUFFIX = {
    "audio/aac": ".aac",
    "audio/flac": ".flac",
    "audio/x-flac": ".flac",
    "audio/m4a": ".m4a",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/ogg": ".ogg",
    "audio/opus": ".ogg",
    "application/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/wave": ".wav",
    "audio/x-wav": ".wav",
}


def _normalized_mime(mime: str | None) -> str:
    if not mime:
        return ""
    return mime.split(";", 1)[0].strip().lower()


def _extension(file_name: str | None) -> str | None:
    if not file_name or "." not in file_name:
        return None
    ext = file_name.rsplit(".", 1)[-1].lower()
    if ext in _AUDIO_EXTENSIONS:
        return ext
    return None


def suffix_for_audio(mime: str | None, file_name: str | None) -> str:
    ext = _extension(file_name)
    if ext == "opus":
        return ".ogg"
    if ext:
        return f".{ext}"
    return _MIME_SUFFIX.get(_normalized_mime(mime), ".ogg")


def _is_audio_document(mime: str | None, file_name: str | None) -> bool:
    if _normalized_mime(mime).startswith("audio/"):
        return True
    return _extension(file_name) is not None


def audio_file_from_message(message) -> tuple[str, str] | None:
    """Return (file_id, suffix) for a voice note, audio message, or audio file."""
    voice = getattr(message, "voice", None)
    if voice is not None:
        return voice.file_id, suffix_for_audio(getattr(voice, "mime_type", None), None)

    audio = getattr(message, "audio", None)
    if audio is not None:
        return audio.file_id, suffix_for_audio(
            getattr(audio, "mime_type", None),
            getattr(audio, "file_name", None),
        )

    document = getattr(message, "document", None)
    if document is None:
        return None
    mime = getattr(document, "mime_type", None)
    file_name = getattr(document, "file_name", None)
    if not _is_audio_document(mime, file_name):
        return None
    return document.file_id, suffix_for_audio(mime, file_name)
