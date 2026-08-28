# utils/audio_utils.py
import base64

import aiohttp
from utils.environment_vars import ENV_VARS

# OpenRouter presets (@preset/...) are chat-only. STT requires a catalog slug.
TRANSCRIPTION_MODEL = "mistralai/voxtral-small-24b-2507-stt"
TRANSCRIPTION_ENDPOINT = "https://openrouter.ai/api/v1/audio/transcriptions"


async def transcribe_voice_message(file_path: str) -> str:
    """Transcribe an audio file via OpenRouter (Voxtral Small STT)."""
    api_key = ENV_VARS.OPENROUTER_API_KEY
    if not api_key:
        raise Exception(
            "OPENROUTER_API_KEY is missing — required for voice transcription"
        )

    with open(file_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": TRANSCRIPTION_MODEL,
        "input_audio": {"data": audio_b64, "format": "ogg"},
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            TRANSCRIPTION_ENDPOINT, headers=headers, json=payload
        ) as response:
            if response.status == 200:
                try:
                    json_response = await response.json()
                    text = (json_response.get("text") or "").strip()
                except Exception:
                    text = (await response.text()).strip()
                if not text:
                    raise Exception("Transcription succeeded but returned empty text")
                return text
            error = await response.text()
            raise Exception(f"Transcription failed: {response.status} — {error}")
