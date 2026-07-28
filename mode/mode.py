"""
Mode RSP - Modal state machine.

Routes KeyEvents to appropriate handlers. Manages mode transitions.
Provides ModeContext to handlers with teller, store, and per-mode state.

This module is the ONLY place that manages modal state.

Matches tome.py requirements:
- Mode messages spoken on entry
- Previous mode tracking for return
- On-enter/on-exit hooks
- Per-mode isolated state
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, Protocol, Any


logger = logging.getLogger(__name__)


class Teller(Protocol):
    """Protocol for TTS output."""

    def speak(self, text: str) -> None:
        """Speak text."""
        ...

    def stop(self) -> None:
        """Stop speaking."""
        ...


# Store is provided by store/store.py - a full SQLite-backed hierarchical store
# Mode handlers receive it via ModeContext but Mode itself doesn't use it directly
# Type hint as Any to avoid circular imports; real type is store.store.Store


# Forward reference for KeyEvent - actual type from listener.py
class KeyEvent(Protocol):
    """Protocol for keyboard events (from listener.py)."""
    char: str | None
    key: Any  # SpecialKey enum
    modifiers: frozenset
    event_type: Any  # EventType enum


@dataclass
class ModeContext:
    """
    Context provided to mode handlers.

    Provides access to:
    - teller: TTS output
    - store: Data storage
    - mark: Navigation state (buffer position, stack)
    - switch: Callable to change modes
    - back: Callable to return to previous mode
    - current_mode: Name of the current mode
    - previous_mode: Name of the previous mode (or None)
    - get_state: Callable to get per-mode state dict
    - repeat_count: Number of times this key was pressed rapidly (1=single, 2=double, etc.)
    """
    teller: Teller
    store: Any  # Actually store.store.Store, typed as Any to avoid circular import
    mark: Any  # Actually mark.mark.Mark, typed as Any to avoid circular import
    switch: Callable[..., None]  # switch(mode_name, *, silent=False, setup=None)
    back: Callable[[], None]  # Return to previous mode
    current_mode: str
    previous_mode: str | None
    get_state: Callable[[], dict]
    repeat_count: int = 1  # Per-event, passed through handle()
    quit: Callable[[], None] | None = None


@dataclass
class ModeConfig:
    """Configuration for a registered mode."""
    handler: Callable[[KeyEvent, ModeContext], None]
    message: str | None = None  # Spoken when entering mode
    on_enter: Callable[[], None] | None = None  # Called when entering mode
    on_exit: Callable[[], None] | None = None  # Called when leaving mode


class Mode:
    """
    Modal state machine.

    Tracks current mode, routes KeyEvents to handlers, manages transitions.
    Each mode has isolated state that persists across mode switches.

    Features matching tome.py:
    - Mode messages spoken on entry
    - Previous mode tracking (for back())
    - On-enter/on-exit hooks
    - Silent transitions (suppress_message)
    """

    def __init__(
        self,
        teller: Teller,
        store: Any,
        mark: Any = None,
        quit_callback: Callable[[], None] | None = None,
        on_switch: Callable[[str | None, str], None] | None = None,
    ):
        """
        Create Mode instance.

        Args:
            teller: TTS output (Teller protocol)
            store: Data storage (store.store.Store)
            mark: Navigation state (mark.mark.Mark), optional
            quit_callback: Optional application shutdown callback.
            on_switch: Optional callback called for each successful switch request.
        """
        self._teller = teller
        self._store = store
        self._mark = mark
        self._current: str | None = None
        self._previous: str | None = None
        self._modes: dict[str, ModeConfig] = {}
        self._state: dict[str, dict] = {}  # Per-mode state dicts
        self._quit_callback = quit_callback
        self._on_switch = on_switch

    @property
    def current(self) -> str | None:
        """Get current mode name, or None if no mode set."""
        return self._current

    @property
    def previous(self) -> str | None:
        """Get previous mode name, or None if no previous mode."""
        return self._previous

    def register(
        self,
        name: str,
        handler: Callable[[KeyEvent, ModeContext], None],
        message: str | None = None,
        on_enter: Callable[[], None] | None = None,
        on_exit: Callable[[], None] | None = None,
    ) -> None:
        """
        Register a mode with its handler and configuration.

        Args:
            name: Mode name (must be non-empty string)
            handler: Callable that handles KeyEvents for this mode
            message: Optional message spoken when entering this mode
            on_enter: Optional callback when entering this mode
            on_exit: Optional callback when leaving this mode

        Raises:
            TypeError: If name is not a string or handler is not callable
            ValueError: If name is empty or whitespace-only
        """
        if not isinstance(name, str):
            raise TypeError(f"Mode name must be a string, got {type(name).__name__}")

        if not name or not name.strip():
            raise ValueError("Mode name cannot be empty or whitespace-only")

        if not callable(handler):
            raise TypeError(f"Handler must be callable, got {type(handler).__name__}")

        self._modes[name] = ModeConfig(
            handler=handler,
            message=message,
            on_enter=on_enter,
            on_exit=on_exit,
        )

        # Initialize per-mode state if not exists
        if name not in self._state:
            self._state[name] = {}

    def switch(
        self,
        mode_name: str,
        *,
        silent: bool = False,
        setup: dict | None = None,
    ) -> None:
        """
        Switch to a different mode.

        Args:
            mode_name: Name of the mode to switch to
            silent: If True, don't speak the mode message
            setup: Optional replacement state for the destination mode. This is
                   applied before on_enter/message hooks run.

        Raises:
            TypeError: If mode_name is not a string
            KeyError: If mode_name is not registered
        """
        if not isinstance(mode_name, str):
            raise TypeError(f"mode_name must be a string, got {type(mode_name).__name__}")

        if mode_name not in self._modes:
            raise KeyError(f"Mode '{mode_name}' is unknown - not registered")

        if setup is not None and not isinstance(setup, dict):
            raise TypeError(f"setup must be a dict, got {type(setup).__name__}")

        previous_mode = self._current
        if self._on_switch:
            try:
                self._on_switch(previous_mode, mode_name)
            except Exception:
                logger.exception("on_switch raised exception")

        if setup is not None:
            self._state[mode_name].clear()
            self._state[mode_name].update(setup)

        # Call on_exit for current mode
        if self._current is not None and self._current in self._modes:
            config = self._modes[self._current]
            if config.on_exit:
                try:
                    config.on_exit()
                except Exception:
                    logger.exception(f"on_exit for mode '{self._current}' raised exception")

        # Track previous mode (only if actually changing)
        if mode_name != self._current:
            self._previous = self._current

        # Update current mode
        self._current = mode_name

        # Call on_enter for new mode
        config = self._modes[mode_name]
        if config.on_enter:
            try:
                config.on_enter()
            except Exception:
                logger.exception(f"on_enter for mode '{mode_name}' raised exception")

        # Speak mode message (unless silent or no message)
        if not silent and config.message:
            self._teller.speak(config.message)

    def back(self) -> None:
        """
        Return to the previous mode.

        If no previous mode, does nothing.
        """
        if self._previous is not None:
            self.switch(self._previous)

    def handle(self, event: KeyEvent, repeat_count: int = 1) -> None:
        """
        Route an event to the current mode's handler.

        Args:
            event: KeyEvent to handle
            repeat_count: Number of rapid repeats of this key (1=single, 2=double, etc.)

        Raises:
            TypeError: If event doesn't look like a KeyEvent
            RuntimeError: If no mode is currently set (switch not called)
        """
        # Validate event has required KeyEvent attributes (strict duck typing)
        if not hasattr(event, 'char') or not hasattr(event, 'key'):
            raise TypeError(
                f"event must be a KeyEvent (with char and key attributes), "
                f"got {type(event).__name__}"
            )

        if self._current is None:
            raise RuntimeError("Cannot handle event - no mode set (call switch() first)")

        config = self._modes[self._current]
        handler = config.handler

        # Capture mode name at context creation time (not by reference)
        # This ensures get_state() always returns this handler's state,
        # even if the handler calls switch() to change modes mid-execution
        current_mode_name = self._current

        # Create context for this handler call
        context = ModeContext(
            teller=self._teller,
            store=self._store,
            mark=self._mark,
            switch=self.switch,
            back=self.back,
            current_mode=current_mode_name,
            previous_mode=self._previous,
            get_state=lambda: self._state[current_mode_name],
            repeat_count=repeat_count,
            quit=self._quit_callback,
        )

        try:
            handler(event, context)
        except Exception:
            logger.exception(f"Handler for mode '{current_mode_name}' raised exception")
            self._state[current_mode_name].clear()
            # Don't re-raise - allow continued operation

    def list_modes(self) -> list[str]:
        """Return list of registered mode names."""
        return list(self._modes.keys())

    def get_message(self, mode_name: str) -> str | None:
        """Get the message for a mode, or None if not set."""
        if mode_name not in self._modes:
            raise KeyError(f"Mode '{mode_name}' is unknown - not registered")
        return self._modes[mode_name].message

    def set_message(self, mode_name: str, message: str | None) -> None:
        """Set the message for a mode (e.g., for confirm mode's dynamic prompt)."""
        if mode_name not in self._modes:
            raise KeyError(f"Mode '{mode_name}' is unknown - not registered")
        self._modes[mode_name].message = message
