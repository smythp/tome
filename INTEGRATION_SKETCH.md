# Integration Sketch: Tome Rewrite

Full rewrite using rock-solid primitives. No incremental migration.

## Current State Summary

**tome.py**: 2240 lines, 36+ globals, 8 modes, ~25 SQL queries scattered throughout.

## Modes in Current System

| Mode | Purpose | Key Operations |
|------|---------|----------------|
| read | Main mode, read registers | read value, double-press copy, Ctrl combos |
| clipboard | Store from clipboard | store clipboard at key |
| browse | Open URLs | open URL at key |
| history | Navigate history | up/down through entries, restore, delete |
| list | Navigate list items | up/down, append, delete |
| options | Settings | toggle strip_input, debug_mode, default_action |
| confirm | Y/N dialogs | buffer deletion confirmation |
| default | Base state | does nothing |

## Global State Categories

### Navigation State
```python
current_buffer_id = 1      # Which buffer we're in
buffer_stack = [1]         # Path back to root
buffer_path = []           # Display path ['a', 'b']
```

### Mode State
```python
mode = "default"           # Current mode name
suppress_mode_message = False
key_presses = {}           # Track for double-press
last_retrieved = {...}     # Last read key info
```

### Per-Mode State
```python
history_state = {...}      # History navigation
list_state = {...}         # List navigation
confirm_state = {...}      # Confirmation dialog
```

### Input State
```python
pressed = {shift, ctrl, alt}  # Modifier tracking
```

### Settings
```python
strip_input = True
debug_mode = False
```

## RSP Mapping

### store (done)
All data operations extracted.

### teller (in progress)
- `speak(text, speed, async)`
- `kill_speech()`

### listener (parallel)
- Wraps pynput
- Emits `KeyEvent(char, key, modifiers)`
- Tracks modifier state internally

### mode (pending)
- Routes events to handlers
- Manages mode transitions
- Holds per-mode state

## Additional Modules to Extract

### navigator.py
Buffer/path navigation logic:
```python
class Navigator:
    def __init__(self, store: Store):
        self.store = store
        self.current_buffer_id = 1
        self.buffer_stack = [1]
        self.buffer_path = []

    def enter(self, key: str) -> int | None
    def exit(self) -> bool
    def path_name(self) -> str
    def at_root(self) -> bool
```

### actions.py
Content-based actions:
```python
def is_valid_url(text: str) -> bool
def is_valid_domain(text: str) -> bool
def detect_content_type(text: str) -> str  # "url", "file", "text"
def open_url(url: str) -> bool
```

### util.py
Small helpers:
```python
def status(b: bool) -> str  # "on" / "off"
def user_index(internal: int, items: list) -> int  # 0-based to 1-based
def internal_index(user: int, items: list) -> int  # 1-based to 0-based
```

## New Directory Structure

```
tome/
├── store/              # RSP: hierarchical data store
│   ├── __init__.py
│   ├── store.py
│   └── test_*.py
│
├── teller/             # RSP: TTS output
│   ├── __init__.py
│   ├── teller.py       # Protocol + EspeakTeller
│   └── test_*.py
│
├── listener/           # RSP: keyboard input
│   ├── __init__.py
│   ├── listener.py     # Protocol + PynputListener + KeyEvent
│   └── test_*.py
│
├── mode/               # RSP: modal state machine
│   ├── __init__.py
│   ├── machine.py      # Mode class
│   ├── context.py      # ModeContext dataclass
│   ├── state.py        # HistoryState, ListState, ConfirmState
│   └── handlers/
│       ├── __init__.py
│       ├── read.py
│       ├── history.py
│       ├── list.py
│       ├── options.py
│       ├── confirm.py
│       └── clipboard.py
│
├── navigator.py        # Buffer navigation
├── actions.py          # URL/content actions
├── util.py             # Small helpers
├── main.py             # Entry point
└── tome.py             # Legacy (delete after rewrite)
```

## Mode Handler Interface (Drop-in Pattern)

Modes use auto-discovery. Drop a file in `mode/handlers/`, it gets registered.

### Handler Contract

Each handler file exports:
```python
# mode/handlers/read.py

NAME = "read"                    # Mode name (required)
MESSAGE = "Read from tome"       # Spoken on mode entry (optional)

def handle(event: KeyEvent, ctx: ModeContext) -> None:
    """Handle a key event in this mode."""
    ...

def enter(ctx: ModeContext) -> None:
    """Called when entering this mode. Optional."""
    ...

def exit(ctx: ModeContext) -> None:
    """Called when exiting this mode. Optional."""
    ...
```

### ModeContext

```python
from dataclasses import dataclass
from store import Store
from teller import Teller

@dataclass
class ModeContext:
    store: Store
    teller: Teller
    navigator: Navigator
    switch: Callable[[str], None]  # Change mode
    quit: Callable[[], None]       # Exit app

    # Shared state across modes
    read: ReadState
    history: HistoryState
    list: ListState
    confirm: ConfirmState
```

### Auto-Discovery

```python
# mode/machine.py

import importlib
import pkgutil
from pathlib import Path

class Mode:
    def __init__(self, store, teller, navigator):
        self.handlers = {}
        self._discover_handlers()
        ...

    def _discover_handlers(self):
        """Auto-discover handlers in mode/handlers/"""
        handlers_path = Path(__file__).parent / "handlers"

        for module_info in pkgutil.iter_modules([str(handlers_path)]):
            if module_info.name.startswith("_"):
                continue

            module = importlib.import_module(f"mode.handlers.{module_info.name}")

            if hasattr(module, "NAME") and hasattr(module, "handle"):
                self.handlers[module.NAME] = {
                    "handle": module.handle,
                    "enter": getattr(module, "enter", None),
                    "exit": getattr(module, "exit", None),
                    "message": getattr(module, "MESSAGE", None),
                }
```

### Example Handler: read.py

```python
# mode/handlers/read.py
"""Read mode - main interaction mode."""

from listener import KeyEvent
from mode.context import ModeContext

NAME = "read"
MESSAGE = "Read from tome"

def handle(event: KeyEvent, ctx: ModeContext) -> None:
    # Handle backspace -> exit buffer
    if event.key == "backspace":
        ctx.navigator.exit()
        return

    # Handle delete -> delete register
    if event.key == "delete" and ctx.read.last_key:
        _delete_register(ctx)
        return

    # Ctrl combinations
    if event.ctrl:
        _handle_ctrl(event, ctx)
        return

    # Regular key press
    if event.char:
        _handle_keypress(event.char, ctx)

def _handle_keypress(char: str, ctx: ModeContext) -> None:
    """Handle a regular key press."""
    # Check for buffer entry
    buffer_id = ctx.navigator.enter(char)
    if buffer_id:
        ctx.read.clear()
        return

    # Read the register
    entry = ctx.store.get(char, ctx.navigator.current_buffer_id)

    # Track for double-press
    ctx.read.track_press(char, ctx.navigator.current_buffer_id)

    if not entry:
        ctx.read.last_value = None
        ctx.teller.speak(f"No data at key {char}")
        return

    ctx.read.last_key = char
    ctx.read.last_value = entry["value"]
    ctx.read.last_buffer_id = ctx.navigator.current_buffer_id

    # Check press count for double-press behavior
    if ctx.read.press_count(char) == 1:
        ctx.teller.speak(entry["value"])
    else:
        _do_default_action(entry["value"], ctx)

def _handle_ctrl(event: KeyEvent, ctx: ModeContext) -> None:
    """Handle Ctrl+key combinations."""
    if event.char == "c" and ctx.read.last_value:
        pyperclip.copy(ctx.read.last_value)
        ctx.teller.speak("Copied to clipboard")
        ctx.quit()
    elif event.char == "h" and ctx.read.last_key:
        ctx.switch("history")
    elif event.char == "l" and ctx.read.last_key:
        ctx.switch("list")
    # ... etc

def _do_default_action(value: str, ctx: ModeContext) -> None:
    """Execute default action on double-press."""
    action = ctx.store.get_config("default_action", "copy")

    if action == "auto":
        content_type = detect_content_type(value)
        if content_type == "url":
            open_url(value)
            ctx.teller.speak("Opening in browser")
            ctx.quit()
            return

    # Default: copy
    pyperclip.copy(value)
    ctx.teller.speak("Copied to clipboard")
    ctx.quit()
```

### Example Handler: history.py

```python
# mode/handlers/history.py
"""History mode - navigate through entry history."""

from listener import KeyEvent
from mode.context import ModeContext

NAME = "history"
MESSAGE = "Viewing history"

def enter(ctx: ModeContext) -> None:
    """Set up history state when entering."""
    if ctx.history.global_mode:
        # Global history already set up
        return

    # Load history for the selected key
    key = ctx.read.last_key
    buffer_id = ctx.read.last_buffer_id

    entries = ctx.store.history(key, buffer_id, include_deleted=True)

    ctx.history.active = True
    ctx.history.key = key
    ctx.history.buffer_id = buffer_id
    ctx.history.entries = entries
    ctx.history.current_index = 0

def exit(ctx: ModeContext) -> None:
    """Clean up when exiting."""
    ctx.history.active = False
    ctx.history.global_mode = False

def handle(event: KeyEvent, ctx: ModeContext) -> None:
    if event.key in ("backspace", "escape"):
        ctx.switch("read")
        return

    if event.ctrl:
        if event.char == "p" or event.key == "up":
            _navigate("older", ctx)
        elif event.char == "n" or event.key == "down":
            _navigate("newer", ctx)
        elif event.char == "r":
            _restore_entry(ctx)
        elif event.char == "c":
            _copy_entry(ctx)
        # ... etc

def _navigate(direction: str, ctx: ModeContext) -> None:
    """Navigate through history entries."""
    # ... implementation
```

## Key Operations by Mode

### read mode
```
key press      → read value, track press count
double-press   → copy (or auto-action based on content)
Ctrl+c         → copy to clipboard, exit
Ctrl+b         → open URL, exit
Ctrl+h         → enter history mode for this key
Ctrl+y         → save clipboard to this key
Ctrl+g         → create buffer at this key, enter it
Ctrl+o         → switch to options mode
Ctrl+j         → read clipboard aloud
Ctrl+l         → enter list mode for this key
Ctrl+t         → read timestamp
Delete         → soft delete register
Backspace      → exit buffer (navigator.exit())
Esc            → announce buffer name
```

### history mode
```
Ctrl+p / up    → older entry
Ctrl+n / down  → newer entry
Ctrl+z         → restore as new entry
Ctrl+r         → undelete entry
Ctrl+c         → copy current
Ctrl+b         → browse URL
Ctrl+t         → read timestamp
Delete         → soft delete entry
Esc/backspace  → exit to read mode
```

### list mode
```
n/j/down/Ctrl+n → next item (toward higher numbers)
p/k/up/Ctrl+p   → prev item (toward item 1)
.               → jump to end
,               → jump to top
a               → append clipboard as new item 1
Delete          → soft delete current item
Enter           → read current item
Esc/backspace   → exit to read mode
```

### options mode
```
s → toggle strip_input
d → toggle debug_mode
a → toggle default_action (copy/auto)
Esc/backspace → exit to read mode
```

### confirm mode
```
y → confirm action (e.g., delete buffer)
n → cancel
Esc → cancel
```

### clipboard mode
```
key press → store clipboard at key
(enter buffer works)
```

## Global Hotkeys (in main event handler)

These are handled BEFORE mode dispatch:
```
q           → quit
Ctrl+Alt+v  → kill speech
Ctrl+h      → global history (only in root buffer, no key selected)
Delete      → buffer deletion (only in non-root buffer, no register selected)
```

## The New main.py

```python
#!/usr/bin/env python3
"""Tome of Lore - keyboard-driven audio-only knowledge manager."""

from store import Store
from teller import EspeakTeller, MockTeller
from listener import PynputListener, KeyEvent
from mode import Mode
from mode.handlers import (
    ReadHandler, HistoryHandler, ListHandler,
    OptionsHandler, ConfirmHandler, ClipboardHandler
)
from navigator import Navigator
import sys

def main():
    # Determine if testing
    testing = "--test" in sys.argv

    # Wire up primitives
    store = Store("lore.db")
    teller = MockTeller() if testing else EspeakTeller()
    navigator = Navigator(store)

    # Create mode machine
    mode = Mode(store, teller, navigator)

    # Register handlers
    mode.register("read", ReadHandler())
    mode.register("history", HistoryHandler())
    mode.register("list", ListHandler())
    mode.register("options", OptionsHandler())
    mode.register("confirm", ConfirmHandler())
    mode.register("clipboard", ClipboardHandler())

    # Global hotkeys (before mode dispatch)
    def handle_global(event: KeyEvent) -> bool:
        """Handle global hotkeys. Returns True if consumed."""

        # q to quit
        if event.char == "q":
            teller.speak("Quit")
            sys.exit(0)

        # Ctrl+Alt+v to kill speech
        if event.char == "v" and event.ctrl and event.alt:
            teller.stop()
            teller.speak("Silenced")
            return True

        # Global history (Ctrl+h in root, no key selected)
        if (event.char == "h" and event.ctrl and
            mode.current == "read" and
            navigator.at_root() and
            not mode.has_selected_key()):
            mode.enter_global_history()
            return True

        # Buffer deletion (Delete in non-root buffer)
        if (event.key == "delete" and
            mode.current == "read" and
            not navigator.at_root() and
            not mode.has_selected_key()):
            mode.confirm_buffer_deletion()
            return True

        return False

    # Event loop
    def on_key(event: KeyEvent):
        if not handle_global(event):
            mode.handle(event)

    # Startup
    teller.speak("Tome of lore")
    mode.switch("read")

    # Start listening
    listener = PynputListener()
    listener.start(on_key)

if __name__ == "__main__":
    main()
```

## State Classes

```python
# mode/state.py

from dataclasses import dataclass, field

@dataclass
class HistoryState:
    active: bool = False
    key: str | None = None
    buffer_id: int | None = None
    entries: list = field(default_factory=list)
    current_index: int = 0
    global_mode: bool = False

@dataclass
class ListState:
    active: bool = False
    list_id: int | None = None
    key: str | None = None
    buffer_id: int | None = None
    items: list = field(default_factory=list)
    current_index: int = 0

@dataclass
class ConfirmState:
    active: bool = False
    action: str | None = None
    params: dict = field(default_factory=dict)
    prompt: str | None = None
    previous_mode: str | None = None

@dataclass
class ReadState:
    last_key: str | None = None
    last_value: str | None = None
    last_buffer_id: int | None = None
    press_counts: dict = field(default_factory=dict)  # key -> count
```

## Testing Strategy

With the new architecture:

1. **store tests** (done) - Pure data operations
2. **teller tests** - MockTeller records calls
3. **listener tests** - MockListener injects events
4. **mode tests** - Full integration with mocks

Example mode test:
```python
def test_read_double_press_copies():
    store = Store(":memory:")
    teller = MockTeller()
    navigator = Navigator(store)
    mode = Mode(store, teller, navigator)
    mode.register("read", ReadHandler())

    # Set up data
    store.set("a", "hello")
    mode.switch("read")

    # Simulate two presses
    mode.handle(KeyEvent(char="a"))
    mode.handle(KeyEvent(char="a"))

    # Check clipboard was set (would need clipboard mock)
    assert "Copied" in teller.spoken[-1]
```

## Migration Checklist

- [x] store RSP
- [ ] teller RSP (in progress)
- [ ] listener RSP (in parallel)
- [ ] mode RSP
- [ ] navigator module
- [ ] actions module
- [ ] util module
- [ ] main.py wiring
- [ ] handlers: read
- [ ] handlers: history
- [ ] handlers: list
- [ ] handlers: options
- [ ] handlers: confirm
- [ ] handlers: clipboard
- [ ] integration tests
- [ ] delete tome.py
