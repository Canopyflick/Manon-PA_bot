# utils/audio_utils.py
import base64
import json

import aiohttp
from utils.environment_vars import ENV_VARS

# OpenRouter presets (@preset/...) are chat-only. STT requires a catalog slug.
TRANSCRIPTION_MODEL = "mistralai/voxtral-small-24b-2507-stt"
TRANSCRIPTION_ENDPOINT = "https://openrouter.ai/api/v1/audio/transcriptions"


def _transcript_text(payload) -> str:
    if isinstance(payload, str):
        return payload.strip()
    if not isinstance(payload, dict):
        return ""

    text = (payload.get("text") or "").strip()
    if text:
        return text

    segments = payload.get("segments") or []
    from_segments = " ".join(
        (seg.get("text") or "").strip()
        for seg in segments
        if isinstance(seg, dict)
    ).strip()
    if from_segments:
        return from_segments

    error = payload.get("error")
    if isinstance(error, dict):
        raise Exception(error.get("message") or json.dumps(error))
    if error:
        raise Exception(str(error))
    return ""


async def transcribe_voice_message(file_path: str) -> str:
    """Transcribe an audio file via OpenRouter (Voxtral Small STT)."""
    api_key = ENV_VARS.OPENROUTER_API_KEY
    if not api_key:
        raise Exception(
            "OPENROUTER_API_KEY is missing — required for voice transcription"
        )

    with open(file_path, "rb") as f:
        raw = f.read()
    audio_b64 = base64.b64encode(raw).decode("utf-8")
    headers = {"Authorization": f"Bearer {api_key}"}
    last_error = None

    async with aiohttp.ClientSession() as session:
        for audio_format in ("ogg", "opus"):
            payload = {
                "model": TRANSCRIPTION_MODEL,
                "input_audio": {"data": audio_b64, "format": audio_format},
            }
            async with session.post(
                TRANSCRIPTION_ENDPOINT,
                headers={**headers, "Content-Type": "application/json"},
                json=payload,
            ) as response:
                body = await response.text()
                if response.status == 200:
                    try:
                        text = _transcript_text(json.loads(body))
                    except json.JSONDecodeError:
                        text = body.strip()
                    if text:
                        return text
                    last_error = f"empty transcript (format={audio_format}): {body[:400]}"
                    continue
                last_error = f"{response.status} (format={audio_format}): {body[:400]}"
                if response.status < 400 or response.status >= 500:
                    break

        form = aiohttp.FormData()
        form.add_field(
            "file",
            raw,
            filename="voice.ogg",
            content_type="audio/ogg",
        )
        form.add_field("model", TRANSCRIPTION_MODEL)
        async with session.post(
            TRANSCRIPTION_ENDPOINT, headers=headers, data=form
        ) as response:
            body = await response.text()
            if response.status == 200:
                try:
                    text = _transcript_text(json.loads(body))
                except json.JSONDecodeError:
                    text = body.strip()
                if text:
                    return text
                last_error = f"empty transcript (multipart): {body[:400]}"
            else:
                last_error = f"{response.status} (multipart): {body[:400]}"

    raise Exception(f"Transcription failed: {last_error}")
