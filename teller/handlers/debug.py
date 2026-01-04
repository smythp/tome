"""Debug handler - text output with timing and metadata.

Useful for debugging, logging, and understanding teller behavior.
Shows exactly what would be spoken plus additional context.
"""

from datetime import datetime

from teller.base import BaseHandler


class DebugHandler(BaseHandler):
    """Handler that outputs text with debug metadata."""

    @property
    def name(self) -> str:
        return "debug"

    def speak(self, text: str, speed: int = 270, wait: bool = False) -> None:
        """Print text with debug metadata.

        Output format:
            [debug] 2024-01-15T10:30:45.123 | speed=270 wait=False
            > text goes here

        Args:
            text: Text to output.
            speed: Included in metadata.
            wait: Included in metadata.
        """
        timestamp = datetime.now().isoformat(timespec="milliseconds")
        print(f"[debug] {timestamp} | speed={speed} wait={wait}")
        print(f"> {text}")

    def stop(self) -> None:
        """Log stop call."""
        timestamp = datetime.now().isoformat(timespec="milliseconds")
        print(f"[debug] {timestamp} | stop() called")
