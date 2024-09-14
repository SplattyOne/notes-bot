import logging
import os
import subprocess
import traceback

import speech_recognition

logger = logging.getLogger(__name__)


class SpeechRecognizer:
    def __init__(self, tmp_dir: str = 'tmp') -> None:
        self._recognizer = speech_recognition.Recognizer()
        self._tmp_dir = tmp_dir

    def recognize(self, source_path: str) -> str | None:
        target_path = os.path.join(self._tmp_dir, os.path.basename(source_path) + '.wav')
        subprocess.run(['ffmpeg', '-i', source_path, target_path, '-y'])
        text = None
        with speech_recognition.AudioFile(target_path) as source:
            try:
                # self._recognizer.adjust_for_ambient_noise(source)
                audio = self._recognizer.record(source)
                text = self._recognizer.recognize_whisper(audio, language='Russian')
                logger.info('Recognized text: %s', text)
            except Exception:
                logger.error('Exception:\n %s', traceback.format_exc())
        os.unlink(target_path)
        return text
