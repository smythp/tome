# Agentic Testing

Testing Tome without real keyboard input. Useful for automated tests and agent-driven workflows.

## Two Approaches

### 1. MockListener (Full Integration)

The `MockListener` class implements the same `Listener` protocol as the real `PynputListener` but allows injecting `KeyEvent` objects directly.

```python
from listener import MockListener, KeyEvent, EventType, SpecialKey, Modifier

# Create and start the mock listener
mock = MockListener()
mock.start(my_callback)

# Inject a simple character keypress
event = KeyEvent(
    char='a',
    key=None,
    modifiers=frozenset(),
    event_type=EventType.PRESS
)
mock.inject(event)

# Inject with modifiers (Ctrl+O)
ctrl_o = KeyEvent(
    char='o',
    key=None,
    modifiers=frozenset({Modifier.CTRL}),
    event_type=EventType.PRESS
)
mock.inject(ctrl_o)

# Inject special keys (Escape, arrows, etc.)
escape = KeyEvent(
    char=None,
    key=SpecialKey.ESCAPE,
    modifiers=frozenset(),
    event_type=EventType.PRESS
)
mock.inject(escape)

# Stop when done
mock.stop()
```

**When to use:** Integration tests where you want the full listener → callback flow.

### 2. Direct mode.handle() Calls

Bypass the listener entirely and call `mode.handle(event)` directly with constructed `KeyEvent` objects.

```python
from listener import KeyEvent, EventType, SpecialKey, Modifier
from mode import Mode
from store import Store
from teller import get_handler
from mark import Mark

# Setup components
store = Store("/path/to/test.db")
teller = get_handler("text")  # Use text handler for testing (prints to stdout)
mark = Mark(store)
mode = Mode(teller, store, mark)

# Register handlers and switch to a mode
mode.register("read", my_read_handler, message="Read mode")
mode.switch("read")

# Send keypresses directly
event = KeyEvent(char='a', key=None, modifiers=frozenset(), event_type=EventType.PRESS)
mode.handle(event)

# With repeat_count for double-tap detection
mode.handle(event, repeat_count=2)
```

**When to use:** Unit testing mode handlers in isolation.

## KeyEvent Construction

A `KeyEvent` must have exactly one of `char` or `key` set (not both, not neither).

### Character Keys

```python
# Lowercase letter
KeyEvent(char='a', key=None, modifiers=frozenset(), event_type=EventType.PRESS)

# Number
KeyEvent(char='5', key=None, modifiers=frozenset(), event_type=EventType.PRESS)

# With Shift (uppercase)
KeyEvent(char='A', key=None, modifiers=frozenset({Modifier.SHIFT}), event_type=EventType.PRESS)

# With Ctrl
KeyEvent(char='c', key=None, modifiers=frozenset({Modifier.CTRL}), event_type=EventType.PRESS)
```

### Special Keys

```python
# Available special keys:
# SpecialKey.ESCAPE, BACKSPACE, DELETE, ENTER, TAB, UP, DOWN, LEFT, RIGHT

KeyEvent(char=None, key=SpecialKey.ESCAPE, modifiers=frozenset(), event_type=EventType.PRESS)
KeyEvent(char=None, key=SpecialKey.UP, modifiers=frozenset(), event_type=EventType.PRESS)
```

### Modifiers

```python
# Available modifiers: Modifier.SHIFT, Modifier.CTRL, Modifier.ALT

# Single modifier
frozenset({Modifier.CTRL})

# Multiple modifiers
frozenset({Modifier.CTRL, Modifier.SHIFT})
```

### Event Types

```python
# Press event (most common for testing)
EventType.PRESS

# Release event (rarely needed for testing)
EventType.RELEASE
```

## Test Teller

For testing, use the `text` handler instead of `espeak`:

```python
from teller import get_handler

# Prints to stdout instead of speaking
teller = get_handler("text")
```

## Example: Full Test Setup

See `test_wire.py` for a complete example of wiring components together for testing.

```python
#!/usr/bin/env python3
import tempfile
from store import Store
from teller import get_handler
from mark import Mark
from mode import Mode
from listener import KeyEvent, EventType, Modifier

# Create temp database
db_file = tempfile.mktemp(suffix=".db")
store = Store(db_file)

# Wire components
teller = get_handler("text")
mark = Mark(store)
mode = Mode(teller, store, mark)

# Register handlers
from handlers import read_handler, options_handler
mode.register("read", read_handler, message="Read mode")
mode.register("options", options_handler, message="Options mode")

# Start in read mode
mode.switch("read")

# Store test data
store.set("a", "hello world")

# Simulate keypress
event = KeyEvent(char='a', key=None, modifiers=frozenset(), event_type=EventType.PRESS)
mode.handle(event)
# Output: "hello world"

# Simulate Ctrl+O (switch to options)
ctrl_o = KeyEvent(char='o', key=None, modifiers=frozenset({Modifier.CTRL}), event_type=EventType.PRESS)
mode.handle(ctrl_o)
# Now in options mode
```
