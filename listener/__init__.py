"""listener - Keyboard input abstraction.

Wraps pynput. Listens for keypresses, handles modifiers, emits KeyEvents.
This package is the ONLY place that imports pynput.

Basic usage:
    from listener import KeyEvent, SpecialKey, Modifier, EventType
    from listener import PynputListener, MockListener

    # Real keyboard
    listener = PynputListener()
    listener.start(lambda event: print(event))

    # Testing
    mock = MockListener()
    mock.start(handler)
    mock.inject(KeyEvent(char='a', key=None, modifiers=frozenset(), event_type=EventType.PRESS))
"""

from .listener import (
    KeyEvent,
    SpecialKey,
    Modifier,
    EventType,
    Listener,
    MockListener,
    PynputListener,
)

__all__ = [
    "KeyEvent",
    "SpecialKey",
    "Modifier",
    "EventType",
    "Listener",
    "MockListener",
    "PynputListener",
]
