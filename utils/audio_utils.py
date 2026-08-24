# utils/audio_utils.py
import aiohttp
from utils.helpers import logger
from utils.environment_vars import ENV_VARS

TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"
TRANSCRIPTION_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"

async def transcribe_voice_message(file_path: str) -> str:
    """
    Uses OpenAI's gpt-4o-mini-transcribe model to transcribe an audio file to text.
    """
    headers = {
        "Authorization": f"Bearer {ENV_VARS.AUDIO_OPENAI_API_KEY or ENV_VARS.OPENAI_API_KEY}"
    }

    if ENV_VARS.AUDIO_OPENAI_API_KEY:
        logger.warning(
            f"⚠️ Temporarily using testManon's project key (as AUDIO_OPENAI_API_KEY) for audio transcription — "
            f"remember to remove it once {TRANSCRIPTION_MODEL} becomes available for Manon's project key as well")

    data = {
        "model": TRANSCRIPTION_MODEL,
        "response_format": "text"
    }

    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            form = aiohttp.FormData()
            form.add_field("file", f, filename="voice.ogg", content_type="application/octet-stream")
            for key, val in data.items():
                form.add_field(key, val)

            async with session.post(TRANSCRIPTION_ENDPOINT, headers=headers, data=form) as response:
                if response.status == 200:
                    # Try to extract 'text' from JSON response or return raw text
                    try:
                        json_response = await response.json()
                        return json_response["text"]
                    except Exception:
                        return (await response.text()).strip()
                else:
                    error = await response.text()
                    raise Exception(f"Transcription failed: {response.status} — {error}")
