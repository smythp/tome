"""Base handler protocol for teller.

All handlers must inherit from BaseHandler and implement the required methods.
"""

from abc import ABC, abstractmethod


class BaseHandler(ABC):
    """Abstract base class for TTS/output handlers.

    Handlers are pluggable backends for teller. Each handler implements
    a different output mechanism (espeak, text, debug, etc.).

    To create a new handler:
    1. Create a .py file in the handlers/ directory
    2. Define a class that inherits from BaseHandler
    3. Implement all abstract methods
    4. The handler will be auto-discovered on import
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this handler.

        This is used for registration and lookup. Should be lowercase,
        no spaces (e.g., 'espeak', 'text', 'macos_say').
        """
        pass

    @abstractmethod
    def speak(self, text: str, speed: int = 270, wait: bool = False) -> None:
        """Output the given text.

        Args:
            text: The text to speak/output.
            speed: Speech speed in words per minute (for TTS handlers).
                   Non-TTS handlers may ignore this.
            wait: If True, block until speech completes.
                  If False, return immediately (async).
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop any ongoing speech/output.

        Should be safe to call even when nothing is playing.
        For handlers without interruptible output, this is a no-op.
        """
        pass
