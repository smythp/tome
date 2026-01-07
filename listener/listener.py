"""
Listener RSP - Keyboard input abstraction.

Wraps pynput. Listens for keypresses, handles modifiers, emits KeyEvents.
This module is the ONLY place that imports pynput.
"""

import logging
import threading
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Protocol

from pynput import keyboard


logger = logging.getLogger(__name__)


class SpecialKey(Enum):
    """Special (non-character) keys."""
    ESCAPE = auto()
    BACKSPACE = auto()
    DELETE = auto()
    ENTER = auto()
    TAB = auto()
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


class Modifier(Enum):
    """Modifier keys."""
    SHIFT = auto()
    CTRL = auto()
    ALT = auto()


class EventType(Enum):
    """Key event type."""
    PRESS = auto()
    RELEASE = auto()


@dataclass(frozen=True)
class KeyEvent:
    """
    Normalized keyboard event.

    Exactly one of char or key will be set (not both, not neither).
    - char: for regular character keys ('a', '1', '!', etc.)
    - key: for special keys (escape, backspace, arrows, etc.)

    modifiers: set of modifiers held at time of event
    event_type: press or release
    """
    char: str | None
    key: SpecialKey | None
    modifiers: frozenset[Modifier]
    event_type: EventType

    def __post_init__(self):
        # Validate: exactly one of char or key must be set
        has_char = self.char is not None
        has_key = self.key is not None
        if has_char == has_key:
            raise ValueError("KeyEvent must have exactly one of char or key set")
        # Validate: char must be exactly one character (and not empty)
        if has_char and (not self.char or len(self.char) != 1):
            raise ValueError("KeyEvent char must be exactly one character")
        # Validate: key must be a SpecialKey enum if set
        if has_key and not isinstance(self.key, SpecialKey):
            raise TypeError("KeyEvent key must be a SpecialKey enum value")


class Listener(Protocol):
    """Protocol for keyboard listeners."""

    def start(self, callback: Callable[[KeyEvent], None]) -> None:
        """Start listening for keyboard events. Calls callback for each event."""
        ...

    def stop(self) -> None:
        """Stop listening."""
        ...


class MockListener:
    """Mock listener for testing - allows injecting KeyEvents."""

    def __init__(self):
        self._callback: Callable[[KeyEvent], None] | None = None
        self._running: bool = False
        self._lock = threading.Lock()

    def start(self, callback: Callable[[KeyEvent], None]) -> None:
        """Start listening. Raises if already started."""
        with self._lock:
            if self._running:
                raise RuntimeError("MockListener already started")
            self._callback = callback
            self._running = True

    def stop(self) -> None:
        """Stop listening. No-op if not started (idempotent)."""
        with self._lock:
            self._running = False
            self._callback = None

    def inject(self, event: KeyEvent) -> None:
        """Inject a KeyEvent - calls the callback if started."""
        with self._lock:
            if not self._running:
                raise RuntimeError("MockListener not started")
            callback = self._callback
        if callback:
            callback(event)


# Mapping from pynput special keys to our SpecialKey enum
PYNPUT_TO_SPECIAL: dict[keyboard.Key, SpecialKey] = {
    keyboard.Key.esc: SpecialKey.ESCAPE,
    keyboard.Key.backspace: SpecialKey.BACKSPACE,
    keyboard.Key.delete: SpecialKey.DELETE,
    keyboard.Key.enter: SpecialKey.ENTER,
    keyboard.Key.tab: SpecialKey.TAB,
    keyboard.Key.up: SpecialKey.UP,
    keyboard.Key.down: SpecialKey.DOWN,
    keyboard.Key.left: SpecialKey.LEFT,
    keyboard.Key.right: SpecialKey.RIGHT,
}

# Mapping from pynput modifier keys to our Modifier enum
# pynput uses shift/ctrl/alt for left, shift_r/ctrl_r/alt_r for right
PYNPUT_TO_MODIFIER: dict[keyboard.Key, Modifier] = {
    keyboard.Key.shift: Modifier.SHIFT,
    keyboard.Key.shift_r: Modifier.SHIFT,
    keyboard.Key.ctrl: Modifier.CTRL,
    keyboard.Key.ctrl_r: Modifier.CTRL,
    keyboard.Key.alt: Modifier.ALT,
    keyboard.Key.alt_r: Modifier.ALT,
}


class PynputListener:
    """Real keyboard listener using pynput."""

    def __init__(self):
        self._callback: Callable[[KeyEvent], None] | None = None
        self._modifiers: set[Modifier] = set()
        self._listener: keyboard.Listener | None = None
        self._lock = threading.Lock()

    def start(self, callback: Callable[[KeyEvent], None]) -> None:
        """Start listening for keyboard events. Raises if already started."""
        with self._lock:
            if self._listener is not None:
                raise RuntimeError("PynputListener already started")
            self._callback = callback
            self._modifiers = set()
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
                suppress=True,  # Prevent keys from passing through to other apps
            )
            self._listener.start()

    def stop(self) -> None:
        """Stop listening. No-op if not started (idempotent)."""
        with self._lock:
            if self._listener:
                self._listener.stop()
                self._listener = None
            self._callback = None
            self._modifiers = set()

    def _on_press(self, key) -> None:
        """Handle key press from pynput."""
        # Check if it's a modifier key
        if key in PYNPUT_TO_MODIFIER:
            with self._lock:
                self._modifiers.add(PYNPUT_TO_MODIFIER[key])
            return  # Don't emit event for modifier keys themselves

        event = self._normalize_key(key, EventType.PRESS)
        if event:
            self._emit(event)

    def _on_release(self, key) -> None:
        """Handle key release from pynput."""
        # Check if it's a modifier key
        if key in PYNPUT_TO_MODIFIER:
            with self._lock:
                self._modifiers.discard(PYNPUT_TO_MODIFIER[key])
            return  # Don't emit event for modifier keys themselves

        event = self._normalize_key(key, EventType.RELEASE)
        if event:
            self._emit(event)

    def _normalize_key(self, key, event_type: EventType) -> KeyEvent | None:
        """Convert pynput key to KeyEvent, or None if should be skipped."""
        with self._lock:
            modifiers = frozenset(self._modifiers)

        # Try to get char attribute (regular character key)
        try:
            char = key.char
            if char and len(char) == 1:
                return KeyEvent(
                    char=char,
                    key=None,
                    modifiers=modifiers,
                    event_type=event_type,
                )
        except AttributeError:
            pass

        # Check if it's a known special key
        if key in PYNPUT_TO_SPECIAL:
            return KeyEvent(
                char=None,
                key=PYNPUT_TO_SPECIAL[key],
                modifiers=modifiers,
                event_type=event_type,
            )

        # Unknown key - skip and log
        logger.debug(f"Skipping unknown key: {key}")
        return None

    def _emit(self, event: KeyEvent) -> None:
        """Emit event to callback, catching exceptions."""
        with self._lock:
            callback = self._callback
        if not callback:
            return
        try:
            callback(event)
        except Exception:
            logger.exception(f"Callback raised exception for event: {event}")
