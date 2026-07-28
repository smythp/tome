# Tome Architecture Map

**Status**: Working (needs dependency file)
**Last Updated**: 2026-01-23
**Dragon Count**: 3

## What This System Does

Tome is a modal keyboard listener that routes keypresses to handlers based on current mode state. Think vim for system-wide keyboard control: press a key combo, it executes a handler that can speak text (via TTS), manipulate hierarchical data (in SQLite store), or switch modes.

## Entry Points

**Main Entry**: `tome.py`
- Imports all RSPs (Store, Mark, Mode, Listener, Teller)
- Wires dependencies (Store → Mark, Mark → Mode handlers)
- Starts listener with mode.handle_event callback
- Registers all handlers from handlers.py

**How to Run** (once dependencies are installed):
```bash
python tome.py
```

**External Dependencies**:
- `pynput` - keyboard listening (Linux/Mac/Win)
- `pyperclip` - clipboard access
- `pytest` + `hypothesis` - testing

## Architecture Pattern: RSPs (Relatively Simple Primitives)

The codebase uses 5 core RSPs that compose into the full system:

### 1. Store (`store/store.py`) 🐉 DRAGON
**What**: SQLite-backed hierarchical list storage
**Size**: 700+ lines
**Complexity**: High - soft deletes, buffer hierarchy, complex list operations

**Schema**:
```sql
CREATE TABLE items (
    id INTEGER PRIMARY KEY,
    buffer TEXT NOT NULL,      -- namespace/category
    content TEXT NOT NULL,
    position INTEGER NOT NULL, -- order within buffer
    deleted_at REAL,          -- soft delete timestamp
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
)
```

**Key Operations**:
- `append(buffer, content)` - Add item to end of buffer
- `retrieve(buffer, position)` - Get item at position
- `delete_item(item_id)` - Soft delete (sets deleted_at)
- `move_item(item_id, target_position)` - Reorder
- `list_buffers()` - Get all buffer names

**Dragon Traits**:
- Complex soft-delete logic (filters everywhere)
- Position recalculation after deletes/moves
- Multiple query patterns (by ID, by position, by buffer)
- No transactions exposed (auto-commit)

### 2. Mark (`mark/mark.py`)
**What**: Navigation state tracker
**Size**: 200 lines
**Complexity**: Medium - stateful, uses Protocol to avoid circular imports

**State Fields**:
```python
current_buffer: str | None  # Which buffer we're in
stack: list[str]            # Navigation history
last_retrieved: Item | None # Last item fetched
```

**Key Operations**:
- `set_buffer(name)` - Switch to buffer, push to stack
- `pop_buffer()` - Go back in stack
- `get_current()` - Retrieve current buffer's items
- `remember(item)` - Track last retrieved item

**Design Note**: Uses `Store` Protocol to avoid importing store.py directly.

### 3. Mode (`mode/mode.py`) 🐉 DRAGON
**What**: Modal state machine routing KeyEvents to handlers
**Size**: 300 lines
**Complexity**: High - per-mode state, complex context object

**ModeContext** (passed to every handler):
```python
@dataclass
class ModeContext:
    store: Store
    mark: Mark
    teller: Teller
    mode: Mode
    buffer_input: str        # Accumulated text input
    search_query: str        # Current search
    current_item_id: int | None
    last_action: str
    clipboard_content: str
```

**Mode Registration**:
```python
mode.register_handler(
    mode_name="insert",
    key=KeyEvent(char='a', ...),
    handler=lambda ctx: handle_append(ctx),
    description="Append item"
)
```

**Dragon Traits**:
- 9-field context object (high coupling)
- Per-mode state dict (`_state: dict[str, dict]`)
- Handler discovery via inspection
- Mode switching modifies global state

### 4. Listener (`listener/listener.py`)
**What**: Keyboard input abstraction (wraps pynput)
**Size**: 250 lines
**Complexity**: Medium - modifier tracking, thread safety

**KeyEvent Structure**:
```python
@dataclass(frozen=True)
class KeyEvent:
    char: str | None           # Regular keys ('a', '1')
    key: SpecialKey | None     # Special keys (ESCAPE, ENTER)
    modifiers: frozenset[Modifier]  # SHIFT, CTRL, ALT
    event_type: EventType      # PRESS or RELEASE
```

**Implementations**:
- `PynputListener` - Real keyboard (uses pynput, suppresses keys)
- `MockListener` - Testing (inject events via `.inject()`)

**Key Detail**: This is the ONLY module that imports pynput.

### 5. Teller (`teller/teller.py`)
**What**: TTS/output abstraction with pluggable handlers
**Size**: 150 lines
**Complexity**: Low - simple handler registry

**Handler Discovery**:
```python
# teller/discovery.py scans teller/handlers/*.py
# Auto-registers any class inheriting from BaseHandler
```

**Handler Protocol** (`teller/base.py`):
```python
class BaseHandler(ABC):
    @property
    def name(self) -> str: ...
    def speak(self, text, speed=270, wait=False): ...
    def stop(self): ...
```

**Built-in Handlers**:
- `espeak` - Linux TTS via espeak CLI
- `text` - Print to stdout (testing)
- `macos_say` - macOS TTS (if available)

## Data Flow

### Typical User Journey: "Append item to shopping list"

```
1. User presses <Ctrl+Space> (wake Tome)
   ├─> PynputListener._on_press()
   ├─> Normalizes to KeyEvent(char=' ', modifiers={CTRL}, PRESS)
   └─> Calls mode.handle_event(event)

2. Mode routes to current mode's handler
   ├─> mode._current_mode = "insert"
   ├─> Looks up handler for KeyEvent in insert mode
   └─> Calls handle_insert(ModeContext)

3. Handler uses ModeContext to access RSPs
   ├─> ctx.buffer_input += <user types "milk">
   ├─> ctx.teller.speak("Type item name")
   └─> User presses <Enter>

4. Enter handler finalizes
   ├─> ctx.store.append("shopping", ctx.buffer_input)
   ├─> ctx.mark.remember(new_item)
   ├─> ctx.teller.speak("Added milk to shopping")
   └─> ctx.mode.switch("normal")

5. Listener continues (loop)
```

### Import Dependency Graph

```
tome.py (entry point)
  ├─> store/store.py (no external deps, just sqlite3)
  ├─> mark/mark.py (uses Store Protocol)
  ├─> mode/mode.py (uses Store/Mark/Teller Protocols)
  ├─> listener/listener.py (imports pynput ← ONLY PLACE)
  ├─> teller/teller.py
  │     └─> teller/discovery.py (scans handlers/)
  │           └─> teller/handlers/*.py (inherit BaseHandler)
  └─> handlers.py (imports listener.KeyEvent, mode.ModeContext)
        └─> Defines all mode handlers
```

**Key Design**: Protocols avoid circular imports. Mark uses `Store` Protocol, Mode uses `Store`/`Mark`/`Teller` Protocols.

## Directory Structure

```
tome/
├─ tome.py              # Entry point, wires RSPs
├─ handlers.py          # All mode handlers (insert, search, delete, etc.)
├─ store/
│  ├─ store.py          # 🐉 SQLite storage (700 lines)
│  └─ test_store.py     # Property-based tests (hypothesis)
├─ mark/
│  ├─ mark.py           # Navigation state
│  └─ test_mark.py
├─ mode/
│  ├─ mode.py           # 🐉 Modal routing (300 lines)
│  └─ test_mode.py
├─ listener/
│  ├─ listener.py       # Keyboard abstraction
│  └─ test_listener.py
├─ teller/
│  ├─ teller.py         # TTS registry
│  ├─ base.py           # Handler protocol
│  ├─ discovery.py      # Auto-load handlers
│  └─ handlers/
│      ├─ espeak.py     # Linux TTS
│      ├─ text.py       # Debug handler
│      └─ macos_say.py  # macOS TTS
├─ pytest.ini           # Test config (markers: unit, integration, slow)
├─ ARCHITECTURE.md      # Orientation doc
└─ CLAUDE.md            # Project guidelines
```

## Dragons 🐉

### Dragon 1: Store (store/store.py)
**Why it's a dragon**:
- 700 lines of complex list operations
- Soft delete everywhere (every query filters `deleted_at IS NULL`)
- Position recalculation after moves/deletes (easy to get wrong)
- No transaction API (auto-commit only)
- High in-degree: imported by Mark, Mode, handlers

**Known issues**:
- Position gaps after multiple deletes (cosmetic, not functional)
- No rollback mechanism
- Concurrent access not handled (SQLite default = lock)

**Touch carefully**: Any change affects Mark navigation and all handlers.

### Dragon 2: Mode + ModeContext (mode/mode.py)
**Why it's a dragon**:
- ModeContext has 9 fields (high coupling)
- Every handler gets this massive context object
- Per-mode state management via `_state` dict
- Mode switching mutates global state

**Known issues**:
- Adding a field to ModeContext breaks all handlers
- No clear lifetime for per-mode state
- Mode transitions can leave stale state

**Touch carefully**: This is the central nervous system. Changes ripple everywhere.

### Dragon 3: Listener Modifier Tracking (listener/listener.py)
**Why it's a dragon**:
- Mutable set (`_modifiers`) with threading.Lock
- Modifier state persists across key events
- Race condition if stop() called during event

**Known issues**:
- Modifier keys don't emit events (intentional but surprising)
- Left/right modifiers collapse to same enum value

**Touch carefully**: Thread safety is subtle here.

## Hotspot Analysis

No git history available in this environment, but based on complexity:

**High-churn candidates** (if this were actively developed):
1. `handlers.py` - New features = new handlers
2. `store/store.py` - Data model changes
3. `mode/mode.py` - Mode transitions and state

**Low-churn areas**:
- `listener/listener.py` - Stable abstraction
- `teller/base.py` - Protocol unlikely to change

## Health Assessment

**Working**:
- ✅ Core RSPs are well-tested (pytest + hypothesis)
- ✅ Protocol-based dependency inversion
- ✅ Co-located tests
- ✅ Clear separation of concerns

**Broken**:
- ❌ No dependency file (`requirements.txt` or `pyproject.toml`)
- ❌ Can't run `pip install` to set up environment
- ❌ No Makefile for common tasks

**Missing**:
- 🔶 No integration tests (only unit tests)
- 🔶 No performance benchmarks for Store
- 🔶 No logging configuration
- 🔶 No graceful shutdown (listener.stop() not called)

## Runnability Blockers

**Immediate fix needed**:
```toml
# pyproject.toml (doesn't exist yet)
[project]
name = "tome"
version = "0.1.0"
dependencies = [
    "pynput>=1.7.6",
    "pyperclip>=1.8.2",
]

[project.optional-dependencies]
test = [
    "pytest>=7.4.0",
    "hypothesis>=6.82.0",
]
```

Then: `pip install -e .` and it's runnable.

## Questions for Human Context

Code tells WHAT, not WHY. These areas need human input:

1. **Why soft deletes instead of hard deletes?** Is there an undo feature planned?
2. **Why modal architecture?** Is this inspired by vim/emacs? What's the use case?
3. **Why suppress keypresses?** (listener.py sets `suppress=True`). This blocks all keys from reaching other apps. Is Tome meant to be always-on?
4. **Why SQLite for what looks like ephemeral state?** Is persistence across restarts required?
5. **What's the "tome" metaphor?** Store → buffers → items maps to book → chapters → entries?

## Next Steps for Improvement

**Priority 1: Make it runnable**
- Add `pyproject.toml` with dependencies
- Add `Makefile` with `setup` and `test` targets

**Priority 2: Safety**
- Add integration test that runs full listener → mode → store flow
- Add transaction API to Store
- Add graceful shutdown (catch KeyboardInterrupt, call listener.stop())

**Priority 3: Developer experience**
- Add logging config
- Add Store performance benchmarks
- Document mode handler patterns in CLAUDE.md

---

*This map produced by The Cartographer. Dragons marked where complexity and coupling intersect. Human context needed for WHY questions.*
