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

        if not text:
            return

        # Kill any ongoing speech first
        self.stop()

        # Build command
        # -s: speed in WPM
        # -z: no final pause
        cmd = [self._espeak_cmd, f"-s{speed}", "-z", text]

        try:
            if wait:
                subprocess.call(cmd)
            else:
                self._process = subprocess.Popen(cmd)
        except Exception as e:
            logger.error(f"[teller/espeak] Failed to speak: {e}")

    def stop(self) -> None:
        """Stop any ongoing speech."""
        # Terminate our tracked process if running
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=0.5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None

        # Also try to kill any orphaned espeak processes
        try:
            subprocess.run(
                ["killall", "-q", "espeak", "espeak-ng"],
                capture_output=True,
                timeout=1
            )
        except Exception:
            pass
