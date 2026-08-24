# utils/audio_utils.py
import aiohttp
from utils.environment_vars import ENV_VARS

TRANSCRIPTION_MODEL = "@preset/assistant-voice-transcription"
TRANSCRIPTION_ENDPOINT = "https://openrouter.ai/api/v1/audio/transcriptions"


async def transcribe_voice_message(file_path: str) -> str:
    """Transcribe an audio file via the shared OpenRouter voice-transcription preset."""
    api_key = ENV_VARS.OPENROUTER_API_KEY
    if not api_key:
        raise Exception(
            "OPENROUTER_API_KEY is missing — required for voice transcription"
        )

    headers = {"Authorization": f"Bearer {api_key}"}
    data = {"model": TRANSCRIPTION_MODEL}

    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            form = aiohttp.FormData()
            form.add_field(
                "file",
                f,
                filename="voice.ogg",
                content_type="audio/ogg",
            )
            for key, val in data.items():
                form.add_field(key, val)

            async with session.post(
                TRANSCRIPTION_ENDPOINT, headers=headers, data=form
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
