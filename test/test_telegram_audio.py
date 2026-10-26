"""Share-sheet audio is not a Telegram voice note."""

from __future__ import annotations

import unittest

from utils.telegram_audio import audio_file_from_message


class _Media:
    def __init__(self, file_id, mime_type=None, file_name=None):
        self.file_id = file_id
        self.mime_type = mime_type
        self.file_name = file_name


class _Message:
    def __init__(self, voice=None, audio=None, document=None):
        self.voice = voice
        self.audio = audio
        self.document = document


class TelegramAudioTests(unittest.TestCase):
    def test_voice_note(self) -> None:
        self.assertEqual(
            audio_file_from_message(_Message(voice=_Media("v1", "audio/ogg"))),
            ("v1", ".ogg"),
        )

    def test_shared_mp3(self) -> None:
        self.assertEqual(
            audio_file_from_message(_Message(audio=_Media("a1", "audio/mpeg", "memo.mp3"))),
            ("a1", ".mp3"),
        )

    def test_shared_ogg_document(self) -> None:
        self.assertEqual(
            audio_file_from_message(
                _Message(document=_Media("d1", "application/octet-stream", "Voice.ogg"))
            ),
            ("d1", ".ogg"),
        )

    def test_image_document_is_ignored(self) -> None:
        self.assertIsNone(
            audio_file_from_message(_Message(document=_Media("img", "image/jpeg", "shot.jpg")))
        )
