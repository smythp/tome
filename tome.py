"""
Tome of Lore - Main Application

Wires together the RSP primitives:
- Store: Hierarchical data storage + config
- Teller: TTS output (espeak)
- Mark: Navigation state (buffer position, stack)
- Mode: Modal state machine
- Listener: Keyboard input
"""

import os
import signal
import sys
import time
from types import FrameType
from typing import Callable


class _ShutdownRequested(BaseException):
    """Internal control flow used to unwind startup after handled shutdown."""


def get_default_db() -> str:
    """Get default database path (~/.tome/lore.db), creating dir if needed."""
    tome_dir = os.path.expanduser("~/.tome")
    os.makedirs(tome_dir, exist_ok=True)
    return os.path.join(tome_dir, "lore.db")


# RSPs
from store import Store
from teller import get_handler as get_teller
from mark import Mark
from mode import Mode
from listener import EventType, KeyEvent, Listener, NoListener, PynputListener

# External
import pyperclip


# =============================================================================
# App State
# =============================================================================

class App:
    """Main application - wires RSPs and manages state."""

    def __init__(
        self,
        db_path: str = "lore.db",
        teller_mode: str = "espeak",
        listener: Listener | None = None,
    ):
        # Core RSPs
        self.store = Store(db_path)
        self.teller = get_teller(teller_mode)
        self.mark = Mark(self.store)
        self.listener = listener if listener is not None else PynputListener()
        self.mode = Mode(
            self.teller,
            self.store,
            self.mark,
            quit_callback=self.request_shutdown,
        )

        # Consecutive key tracking (reset on mode change)
        self._last_key: str | None = None
        self._repeat_count: int = 0

        self._running = False
        self._shutdown_started = False
        self._modes_registered = False
        self._previous_signal_handlers: dict[int, Callable | int | None] = {}
        self._unwind_on_signal = False

        # Register mode switch hook to reset repeat tracking
        self._original_switch = self.mode.switch
        self.mode.switch = self._switch_with_reset

    @property
    def running(self) -> bool:
        """Return whether the app run loop is active."""
        return self._running

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

        # Privileged quit handling - 'q' always exits
        if event.char == 'q':
            self.teller.speak("quit", wait=True)  # Block until spoken
            self.request_shutdown()
            return

        repeat = self._track_repeat(event)
        self.mode.handle(event, repeat_count=repeat)

    def run(self, *, block: bool = True) -> None:
        """Start the application."""
        self._begin_start()
        if block:
            self._unwind_on_signal = True
            self._install_signal_handlers()
        try:
            self._start()
            if not block:
                return

            while self._running:
                time.sleep(0.1)
        except _ShutdownRequested:
            pass
        except KeyboardInterrupt:
            self.request_shutdown()
        except Exception:
            self.shutdown()
            raise
        finally:
            if block:
                self.shutdown()
                self._restore_signal_handlers()
                self._unwind_on_signal = False

    def _begin_start(self) -> None:
        """Publish startup state before signals or listener callbacks can fire."""
        if self._running:
            raise RuntimeError("App already running")
        self._running = True
        self._shutdown_started = False

    def _start(self) -> None:
        """Start modes, welcome output, and listener."""
        self._raise_if_shutdown()

        try:
            # Register modes
            self._register_modes()
            self._raise_if_shutdown()

            # Start in read mode
            self.mode.switch("read")
            self._raise_if_shutdown()

            # Speak welcome
            self.teller.speak("Tome of lore")
            self._raise_if_shutdown()

            self._start_listener()
            self._raise_if_shutdown()
        except _ShutdownRequested:
            raise
        except Exception:
            self.shutdown()
            raise

    def _raise_if_shutdown(self) -> None:
        """Stop startup from continuing after callbacks request shutdown."""
        if self._shutdown_started:
            raise _ShutdownRequested()

    def _start_listener(self) -> None:
        """Start the listener at the final startup boundary."""
        self._raise_if_shutdown()
        self.listener.start(self._on_key)

    def request_shutdown(self) -> None:
        """Request application shutdown from callbacks or signal handlers."""
        self._running = False
        self.shutdown()

    def shutdown(self) -> None:
        """Clean shutdown."""
        if self._shutdown_started:
            return
        self._shutdown_started = True
        self._running = False

        self._flush_output()
        try:
            self.listener.stop()
        finally:
            self.teller.stop()
            self._flush_output()

    def _flush_output(self) -> None:
        """Flush redirected text output before process exit."""
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.flush()
            except Exception:
                pass

    def _handle_signal(self, signum: int, frame: FrameType | None) -> None:
        """Convert termination signals into ordered shutdown."""
        self.request_shutdown()
        if self._unwind_on_signal:
            raise _ShutdownRequested()

    def _install_signal_handlers(self) -> None:
        """Install signal handlers for blocking production runs."""
        for signum in (signal.SIGTERM,):
            try:
                self._previous_signal_handlers[signum] = signal.getsignal(signum)
                signal.signal(signum, self._handle_signal)
            except (OSError, ValueError):
                pass

    def _restore_signal_handlers(self) -> None:
        """Restore signal handlers changed by run()."""
        for signum, handler in self._previous_signal_handlers.items():
            try:
                signal.signal(signum, handler)
            except (OSError, ValueError):
                pass
        self._previous_signal_handlers.clear()

    def _register_modes(self) -> None:
        """Register all mode handlers."""
        if self._modes_registered:
            return

        from handlers import (
            options_handler,
            confirm_handler,
            clipboard_handler,
            browse_handler,
            history_handler,
            list_handler,
            read_handler,
        )

        # Register all modes
        self.mode.register(
            "read",
            read_handler,
            message="Read from tome",
        )
        self.mode.register(
            "options",
            options_handler,
            message="Options: Press s for strip input, d for debug mode, a for default action",
        )
        self.mode.register(
            "confirm",
            confirm_handler,
            message=None,  # Dynamic message set when entering
        )
        self.mode.register(
            "clipboard",
            clipboard_handler,
            message="Store from clipboard",
        )
        self.mode.register(
            "browse",
            browse_handler,
            message="Browse URL",
        )
        self.mode.register(
            "history",
            history_handler,
            message="History mode",
        )
        self.mode.register(
            "list",
            list_handler,
            message="List mode",
        )
        self._modes_registered = True


# =============================================================================
# Entry Point
# =============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Tome of Lore")
    parser.add_argument("--text", action="store_true", help="Use text output instead of speech")
    parser.add_argument("--no-listener", action="store_true", help="Run without a keyboard listener")
    parser.add_argument("--db", default=get_default_db(), help="Database file path (default: ~/.tome/lore.db)")
    args = parser.parse_args()

    teller_mode = "text" if args.text else "espeak"
    listener = NoListener() if args.no_listener else None
    app = App(db_path=args.db, teller_mode=teller_mode, listener=listener)
    app.run()


if __name__ == "__main__":
    main()
