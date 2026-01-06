"""mode - Modal state machine.

Routes KeyEvents to appropriate handlers. Manages mode transitions.
Provides ModeContext to handlers with teller, store, and per-mode state.

Basic usage:
    from mode import Mode, ModeConfig, ModeContext

    mode = Mode(teller, store)
    mode.register('read', ModeConfig(handler=read_handler, message='read mode'))
    mode.switch('read')
    mode.handle(key_event)
"""

from .mode import (
    Mode,
    ModeConfig,
    ModeContext,
    Teller,
    KeyEvent,
)

__all__ = [
    "Mode",
    "ModeConfig",
    "ModeContext",
    "Teller",
    "KeyEvent",
]
