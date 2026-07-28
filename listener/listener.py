"""
Listener RSP - Keyboard input abstraction.

Wraps pynput. Listens for keypresses, handles modifiers, emits KeyEvents.
This module is the ONLY place that imports pynput, and it does so lazily
when the real listener starts.
"""

import importlib
import logging
import threading
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Protocol


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

    @property
    def running(self) -> bool:
        """Return whether the mock listener is started."""
        with self._lock:
            return self._running

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


class NoListener:
    """Explicit no-listener harness for headless runs."""

    def start(self, callback: Callable[[KeyEvent], None]) -> None:
        """Start without registering any input source."""
        return

    def stop(self) -> None:
        """Stop is a no-op."""
        return


# Mapping from pynput key names to our enums. Pynput is imported lazily in
# PynputListener.start() so importing listener is safe without X11.
PYNPUT_NAME_TO_SPECIAL: dict[str, SpecialKey] = {
    "esc": SpecialKey.ESCAPE,
    "backspace": SpecialKey.BACKSPACE,
    "delete": SpecialKey.DELETE,
    "enter": SpecialKey.ENTER,
    "tab": SpecialKey.TAB,
    "up": SpecialKey.UP,
    "down": SpecialKey.DOWN,
    "left": SpecialKey.LEFT,
    "right": SpecialKey.RIGHT,
}

# Pynput uses shift/ctrl/alt for left, shift_r/ctrl_r/alt_r for right.
PYNPUT_NAME_TO_MODIFIER: dict[str, Modifier] = {
    "shift": Modifier.SHIFT,
    "shift_r": Modifier.SHIFT,
    "ctrl": Modifier.CTRL,
    "ctrl_r": Modifier.CTRL,
    "alt": Modifier.ALT,
    "alt_r": Modifier.ALT,
}


class PynputListener:
    """Real keyboard listener using pynput."""

    def __init__(self):
        self._callback: Callable[[KeyEvent], None] | None = None
        self._modifiers: set[Modifier] = set()
        self._listener: Any | None = None
        self._lock = threading.Lock()

    def _load_keyboard(self):
        """Import pynput.keyboard only when a real listener starts."""
        return importlib.import_module("pynput.keyboard")

    def start(self, callback: Callable[[KeyEvent], None]) -> None:
        """Start listening for keyboard events. Raises if already started."""
        with self._lock:
            if self._listener is not None:
                raise RuntimeError("PynputListener already started")
            keyboard = self._load_keyboard()
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
        modifier = PYNPUT_NAME_TO_MODIFIER.get(self._key_name(key))
        if modifier:
            with self._lock:
                self._modifiers.add(modifier)
            return  # Don't emit event for modifier keys themselves

        event = self._normalize_key(key, EventType.PRESS)
        if event:
            self._emit(event)

    def _on_release(self, key) -> None:
        """Handle key release from pynput."""
        # Check if it's a modifier key
        modifier = PYNPUT_NAME_TO_MODIFIER.get(self._key_name(key))
        if modifier:
            with self._lock:
                self._modifiers.discard(modifier)
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
        special = PYNPUT_NAME_TO_SPECIAL.get(self._key_name(key))
        if special:
            return KeyEvent(
                char=None,
                key=special,
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
        except Exception as e:
            logger.exception(f"Callback raised exception: {e}")

    def _key_name(self, key) -> str:
        """Return a stable pynput key name without importing pynput at module load."""
        name = getattr(key, "name", None)
        if isinstance(name, str):
            return name
        return str(key).split(".")[-1]
