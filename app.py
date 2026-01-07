"""
Tome of Lore - Main Application

Wires together the RSP primitives:
- Store: Hierarchical data storage + config
- Teller: TTS output (espeak)
- Mark: Navigation state (buffer position, stack)
- Mode: Modal state machine
- Listener: Keyboard input
"""

import sys
import time
from typing import Callable

# RSPs
from store import Store
from teller import get_handler as get_teller
from mark import Mark
from mode import Mode, ModeContext
from listener import PynputListener, KeyEvent, EventType

# External
import pyperclip


# =============================================================================
# App State
# =============================================================================

class App:
    """Main application - wires RSPs and manages state."""

    def __init__(self, db_path: str = "lore.db"):
        # Core RSPs
        self.store = Store(db_path)
        self.teller = get_teller("espeak")
        self.mark = Mark(self.store)
        self.mode = Mode(self.teller, self.store, self.mark)
        self.listener = PynputListener()

        # Consecutive key tracking (reset on mode change)
        self._last_key: str | None = None
        self._repeat_count: int = 0

        # Register mode switch hook to reset repeat tracking
        self._original_switch = self.mode.switch
        self.mode.switch = self._switch_with_reset

    def _switch_with_reset(self, name: str, *, silent: bool = False) -> None:
        """Wrap mode.switch to reset repeat tracking on mode change."""
        self._reset_repeat()
        self._original_switch(name, silent=silent)

    def _reset_repeat(self) -> None:
        """Reset consecutive key tracking."""
        self._last_key = None
        self._repeat_count = 0

    def _track_repeat(self, event: KeyEvent) -> int:
        """
        Track consecutive key presses, return repeat count.

        Returns 1 for first press, 2 for second consecutive, etc.
        No time window - just consecutive same-key presses.
        Reset happens on mode switch or different key.
        """
        if event.event_type != EventType.PRESS:
            return 1

        # Get key identity (char or special key name)
        key_id = event.char if event.char else str(event.key)

        if key_id == self._last_key:
            self._repeat_count += 1
        else:
            self._repeat_count = 1
            self._last_key = key_id

        return self._repeat_count

    def _on_key(self, event: KeyEvent) -> None:
        """Handle keyboard event - route to Mode."""
        # Only handle press events (not release)
        if event.event_type != EventType.PRESS:
            return

        repeat = self._track_repeat(event)
        self.mode.handle(event, repeat_count=repeat)

    def run(self) -> None:
        """Start the application."""
        # Register modes
        self._register_modes()

        # Start in read mode
        self.mode.switch("read")

        # Speak welcome
        self.teller.speak("Tome of lore")

        # Start listening
        self.listener.start(self._on_key)

        try:
            # Block forever (listener runs in background thread)
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self) -> None:
        """Clean shutdown."""
        self.listener.stop()
        self.teller.stop()

    def _register_modes(self) -> None:
        """Register all mode handlers."""
        # Import handlers
        from handlers import (
            options_handler,
            # confirm_handler,
            # clipboard_handler,
            # browse_handler,
            # history_handler,
            # list_handler,
            # read_handler,
        )

        # Register modes
        self.mode.register(
            "options",
            options_handler,
            message="Options: Press s for strip input, d for debug mode, a for default action",
        )

        # Placeholder for read mode (required as home mode)
        self.mode.register(
            "read",
            lambda event, ctx: None,  # TODO: replace with read_handler
            message="Read from tome",
        )


# =============================================================================
# Entry Point
# =============================================================================

def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()
