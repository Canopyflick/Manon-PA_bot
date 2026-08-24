# utils/audio_utils.py
import aiohttp
from utils.environment_vars import ENV_VARS

TRANSCRIPTION_MODEL = "scribe_v2"
TRANSCRIPTION_ENDPOINT = "https://api.elevenlabs.io/v1/speech-to-text"


async def transcribe_voice_message(file_path: str) -> str:
    """Transcribe an audio file with ElevenLabs Scribe v2."""
    api_key = ENV_VARS.ELEVENLABS_API_KEY
    if not api_key:
        raise Exception(
            "ELEVENLABS_API_KEY is missing — required for Scribe v2 voice transcription"
        )

    headers = {"xi-api-key": api_key}

    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            form = aiohttp.FormData()
            form.add_field(
                "file",
                f,
                filename="voice.ogg",
                content_type="audio/ogg",
            )
            form.add_field("model_id", TRANSCRIPTION_MODEL)
            form.add_field("tag_audio_events", "false")
            form.add_field("diarize", "false")

            async with session.post(
                TRANSCRIPTION_ENDPOINT, headers=headers, data=form
            ) as response:
                if response.status == 200:
                    json_response = await response.json()
                    text = (json_response.get("text") or "").strip()
                    if not text:
                        raise Exception("Transcription succeeded but returned empty text")
                    return text
                error = await response.text()
                raise Exception(f"Transcription failed: {response.status} — {error}")
