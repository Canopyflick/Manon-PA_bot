# utils/audio_utils.py
import asyncio
import base64
import json
import os

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


async def _telegram_voice_to_wav(ogg_path: str) -> bytes:
    """Telegram voice is Opus-in-Ogg. OpenRouter 'ogg' means Vorbis; Voxtral rejects Opus."""
    wav_path = ogg_path + ".wav"
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            ogg_path,
            "-ac",
            "1",
            "-ar",
            "16000",
            wav_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        raise Exception(
            "ffmpeg is missing — required to decode Telegram voice notes"
        )

    _, stderr = await proc.communicate()
    try:
        if proc.returncode != 0:
            detail = (stderr or b"").decode("utf-8", errors="replace")[-400:]
            raise Exception(f"Could not decode Telegram voice audio: {detail}")
        with open(wav_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)


async def transcribe_voice_message(file_path: str) -> str:
    """Transcribe a Telegram voice note via OpenRouter (Voxtral Small STT)."""
    api_key = ENV_VARS.OPENROUTER_API_KEY
    if not api_key:
        raise Exception(
            "OPENROUTER_API_KEY is missing — required for voice transcription"
        )

    wav = await _telegram_voice_to_wav(file_path)
    audio_b64 = base64.b64encode(wav).decode("utf-8")
    headers = {"Authorization": f"Bearer {api_key}"}
    last_error = None

    async with aiohttp.ClientSession() as session:
        payload = {
            "model": TRANSCRIPTION_MODEL,
            "input_audio": {"data": audio_b64, "format": "wav"},
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
                last_error = f"empty transcript (wav json): {body[:400]}"
            else:
                last_error = f"{response.status} (wav json): {body[:400]}"

        form = aiohttp.FormData()
        form.add_field(
            "file",
            wav,
            filename="voice.wav",
            content_type="audio/wav",
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
                last_error = f"empty transcript (wav multipart): {body[:400]}"
            else:
                last_error = f"{response.status} (wav multipart): {body[:400]}"

    raise Exception(f"Transcription failed: {last_error}")
