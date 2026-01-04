"""Text handler - outputs to stdout.

Simple handler for testing, CLI use, or when no audio is needed.
Just prints the text that would be spoken.
"""

from teller.base import BaseHandler


class TextHandler(BaseHandler):
    """Handler that outputs text to stdout."""

    @property
    def name(self) -> str:
        return "text"

    def speak(self, text: str, speed: int = 270, wait: bool = False) -> None:
        """Print text to stdout.

        Args:
            text: Text to output.
            speed: Ignored (no audio).
            wait: Ignored (output is instant).
        """
        if text:
            print(text)

    def stop(self) -> None:
        """No-op - text output is instant."""
        pass
