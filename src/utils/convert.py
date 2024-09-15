import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def convert_to_wav(source_path: str, tmp_dir: str) -> str:
    if os.path.splitext(source_path)[1] == '.wav':
        return source_path
    target_path = os.path.join(tmp_dir, os.path.basename(source_path) + '.wav')
    subprocess.run(['ffmpeg', '-i', source_path, target_path, '-y'])
    return target_path
