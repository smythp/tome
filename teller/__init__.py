"""teller - Pluggable TTS/output primitive.

A flexible text-to-speech and output library with pluggable handlers.
Designed for reuse across projects.

Basic usage:
    from teller import speak, announce, stop

    speak("Hello world")          # Uses default handler
    announce("Urgent message")    # Stops current, then speaks
    stop()                        # Interrupt speech

Handler management:
    from teller import get_handler, list_handlers, set_default_handler

    list_handlers()               # ['espeak', 'text', 'debug']
    set_default_handler('text')   # Switch to text output
    handler = get_handler('debug')
    handler.speak("Direct call")

Adding handlers:
    Drop a .py file in teller/handlers/ with a class that inherits
    from BaseHandler. It will be auto-discovered on import.
"""

import logging
from typing import Dict, List, Optional

from .base import BaseHandler
from .discovery import discover_handlers

logger = logging.getLogger(__name__)

# Handler registry - populated on import
_handlers: Dict[str, BaseHandler] = {}
_handler_classes: Dict[str, type] = {}

# Default handler instance
_default_handler: Optional[BaseHandler] = None


def _init_handlers() -> None:
    """Initialize handler registry via discovery."""
    global _handlers, _handler_classes, _default_handler

    _handlers, _handler_classes = discover_handlers()

    # Set default handler (prefer espeak if available, else text)
    if "espeak" in _handlers:
        _default_handler = _handlers["espeak"]
    elif "text" in _handlers:
        _default_handler = _handlers["text"]
    elif _handlers:
        _default_handler = next(iter(_handlers.values()))
    else:
        logger.warning("[teller] No handlers discovered")


# --- Public API ---

def speak(text: str, speed: int = 270, wait: bool = False) -> None:
    """Speak/output text using the default handler.

    Args:
        text: Text to speak.
        speed: Speech speed in WPM (for TTS handlers).
        wait: If True, block until complete.
    """
    if _default_handler is None:
        logger.error("[teller] No handler available")
        return
    _default_handler.speak(text, speed=speed, wait=wait)


def announce(text: str, speed: int = 270) -> None:
    """Interrupt any current speech and speak immediately.

    Useful for urgent messages that shouldn't wait.

    Args:
        text: Text to speak.
        speed: Speech speed in WPM.
    """
    if _default_handler is None:
        logger.error("[teller] No handler available")
        return
    _default_handler.stop()
    _default_handler.speak(text, speed=speed, wait=False)


def stop() -> None:
    """Stop any ongoing speech."""
    if _default_handler is not None:
        _default_handler.stop()


def get_handler(name: str) -> BaseHandler:
    """Get a handler by name.

    Args:
        name: Handler name (e.g., 'espeak', 'text', 'debug').

    Returns:
        A fresh handler instance.

    Raises:
        KeyError: If handler not found.
    """
    if name not in _handler_classes:
        available = ", ".join(_handler_classes.keys()) if _handler_classes else "none"
        raise KeyError(f"Handler '{name}' not found. Available: {available}")
    # Return fresh instance to avoid shared mutable state
    return _handler_classes[name]()


def list_handlers() -> List[str]:
    """List all available handler names.

    Returns:
        List of handler names.
    """
    return list(_handlers.keys())


def set_default_handler(name: str) -> None:
    """Set the default handler used by speak() and announce().

    Args:
        name: Handler name.

    Raises:
        KeyError: If handler not found.
    """
    global _default_handler
    _default_handler = get_handler(name)


# Initialize on import
_init_handlers()


__all__ = [
    "speak",
    "announce",
    "stop",
    "get_handler",
    "list_handlers",
    "set_default_handler",
    "BaseHandler",
]
