import logging
import os
import typing
import traceback

import speech_recognition

from utils.convert import convert_to_wav
from utils.asynctools import async_wrapper

logger = logging.getLogger(__name__)


class SpeechRecognizerProtocol(typing.Protocol):
    def recognize(self, voice_path: str) -> str | None:
        ...

    async def async_recognize(self, voice_path: str) -> str | None:
        ...


class SpeechRecognizer(SpeechRecognizerProtocol):
    def __init__(self, tmp_dir: str = 'tmp') -> None:
        self._recognizer = speech_recognition.Recognizer()
        self._tmp_dir = tmp_dir

    def recognize(self, source_path: str) -> str | None:
        target_path = convert_to_wav(source_path, self._tmp_dir)
        text = None
        with speech_recognition.AudioFile(target_path) as source:
            try:
                # self._recognizer.adjust_for_ambient_noise(source)
                audio = self._recognizer.record(source)
                text = self._recognizer.recognize_whisper(
                    audio, language='Russian', load_options={'download_root': self._tmp_dir})
                logger.info('Recognized text: %s', text)
            except Exception:
                logger.error('Exception:\n %s', traceback.format_exc())
        os.unlink(target_path)
        return text

    @async_wrapper
    def async_recognize(self, source_path: str) -> str | None:
        return self.recognize(source_path)
