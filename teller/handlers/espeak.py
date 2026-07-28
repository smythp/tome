"""Espeak handler - real TTS via espeak/espeak-ng subprocess.

Uses the system espeak installation to synthesize and play speech.
Works with both espeak and espeak-ng.
"""

import subprocess
import shutil
import logging
from typing import Optional

from teller.base import BaseHandler

logger = logging.getLogger(__name__)


class EspeakHandler(BaseHandler):
    """Handler that uses espeak for text-to-speech."""

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._espeak_cmd = self._find_espeak()

    @property
    def name(self) -> str:
        return "espeak"

    def _find_espeak(self) -> Optional[str]:
        """Find espeak or espeak-ng executable."""
        for cmd in ["espeak-ng", "espeak"]:
            if shutil.which(cmd):
                return cmd
        logger.warning("[teller/espeak] espeak not found on system")
        return None

    def speak(self, text: str, speed: int = 270, wait: bool = False) -> None:
        """Speak text using espeak.

        Args:
            text: Text to speak.
            speed: Words per minute (espeak -s flag).
            wait: If True, block until speech completes.
        """
        if not self._espeak_cmd:
            logger.error("[teller/espeak] espeak not available")
            return

        # Reap or stop any ongoing speech first.
        self.stop()

        if not text:
            return

        # Build command
        # -s: speed in WPM
        # -z: no final pause
        cmd = [self._espeak_cmd, f"-s{speed}", "-z", text]

        try:
            process = subprocess.Popen(cmd)
            self._process = process
            if wait:
                process.wait()
                if self._process is process:
                    self._process = None
        except Exception as e:
            logger.error(f"[teller/espeak] Failed to speak: {e}")
            if self._process is not None:
                self.stop()

    def stop(self) -> None:
        """Stop any ongoing speech and reap the child process."""
        process = self._process
        if process is None:
            return

        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=0.5)
            else:
                process.wait(timeout=0)
        except Exception:
            try:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=0.5)
            except Exception:
                pass
        finally:
            if self._process is process:
                self._process = None
