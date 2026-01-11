# Tome of Lore - Phase 2: Data Flow & Hotspots

## Data Flow Analysis

### Architecture Pattern

Tome follows a **hub-and-spoke architecture**:
- **Store** (hub): All persistence goes through SQLite via the Store class
- **Handlers** (spokes): Stateless event processors that coordinate between components
- **Mark** (context): Navigation state and temporary scratch space
- **Mode** (router): State machine that dispatches events to handlers

### Key User Journeys

#### 1. Store Clipboard Data
```
User presses key in clipboard mode
  ↓
tome.py._on_key() captures KeyEvent
  ↓
Mode.handle() routes to clipboard_handler
  ↓
clipboard_handler:
  - pyperclip.paste() → get clipboard data
  - strip if configured (from Store.get_config)
  - Store.set() → SQLite persist
  - speak confirmation → Teller
  - switch to read mode

Data path: System Clipboard → Handlers → Store → SQLite
```

#### 2. Read and Copy Value
```
User presses alphanumeric in read mode
  ↓
tome.py._on_key() with repeat tracking
  ↓
Mode.handle() routes to read_handler
  ↓
First press:
  - Store.get() → SQLite read
  - Update Mark.last_retrieved (scratch space)
  - Teller.speak(value)
  ↓
Second consecutive press:
  - pyperclip.copy(value from Mark.last_retrieved)
  - quit_app()

Data path: SQLite → Store → Mark (tracking) → Clipboard → Exit
```

#### 3. Navigate Buffers (Hierarchical)
```
User presses buffer key (e.g., 'p' for projects)
  ↓
read_handler:
  - Store.get('p') → check data_type
  - if TYPE_BUFFER → get buffer_id from value field
  - Mark.into(buffer_id) → push to navigation stack
  - speak confirmation
  ↓
User presses Backspace:
  - Mark.back() → pop from navigation stack
  - speak confirmation

Data path: Store → Mark (stack) → Store (context change)
State: Mark maintains buffer_id stack for navigation
```

#### 4. Browse URL
```
User in browse mode, presses key
  ↓
browse_handler:
  - Store.get(key) → SQLite read
  - Validate URL (regex patterns)
  - If domain without protocol → prepend 'http://'
  - webbrowser.open(url) → system browser
  - quit_app()

Data path: SQLite → Store → Handlers → System Browser → Exit
```

#### 5. History Navigation
```
User presses Ctrl+H on last_retrieved key
  ↓
read_handler:
  - Store.history(key, buffer_id) → SQLite query with deleted entries
  - Setup state in Mark.last_retrieved (temp channel)
  - switch to history mode
  ↓
history_handler initialization:
  - Read setup from Mark.last_retrieved._history_setup
  - Transfer to Mode state dict
  - Navigate with j/k keys
  - speak entries with position ("Entry 3 of 10")

Data path: SQLite → Store → Mark (temp) → Mode state → Handlers → Teller
Coupling point: Mark.last_retrieved used as inter-mode communication
```

#### 6. List Management
```
User presses Ctrl+L on key
  ↓
read_handler:
  - Check Store.get(key) for existing data
  - Create or convert to TYPE_LIST
  - Store.create_list() or Store.list_items()
  - Setup state via Mark.last_retrieved._list_setup
  - switch to list mode
  ↓
list_handler:
  - Navigate items with j/k
  - Enter to copy item
  - Store.list_append() for new items
  - Delete to remove items

Data path: SQLite → Store → Mark (temp) → Mode state → Handlers → Store (mutations) → SQLite
```

### Data Flow Observations

**Central Hub Pattern:**
- Store is the single source of truth
- No caching layer - every read hits SQLite
- No batch operations - each mutation is immediate

**State Management:**
- Handlers are stateless (pure functions)
- Mark maintains navigation state (buffer stack)
- Mode.state dict holds mode-specific state
- Mark.last_retrieved serves as scratch space AND inter-mode communication channel (coupling!)

**Configuration:**
- Config reads happen inline (Store.get_config on each use)
- No config cache or validation
- No environment variable support

**Exit Strategy:**
- Multiple operations end with quit_app() (os._exit(0))
- No cleanup, no state persistence on exit
- Assumes SQLite auto-commits are sufficient

## Hotspot Analysis

### Git Forensics Status

Git log analysis requires approval (bash command waiting in Horizon). However, we can identify **complexity hotspots** from code analysis.

### Complexity Hotspots

#### 1. handlers.py (36KB) - PRIMARY DRAGON

**read_handler function** is the highest-risk area:

**Why it's a dragon:**
- **Cognitive complexity:** 15+ distinct control flow paths
- **High coupling:** Depends on Store, Mark, Mode, Teller, pyperclip, webbrowser
- **Frequency:** Called on EVERY keypress in read mode (default mode)
- **Mutation surface:** Updates Mark.last_retrieved, switches modes, can quit app
- **Multi-responsibility:** Handles reads, copies, buffer navigation, mode switches, deletions

**Control flow branches in read_handler:**
```
- Delete key → soft-delete entry
- Backspace → navigate back in buffer stack
- Alphanumeric + Ctrl:
  - Ctrl+C → copy and quit
  - Ctrl+B → browse URL and quit
  - Ctrl+T → read timestamp
  - Ctrl+H → enter history mode
  - Ctrl+Y → write clipboard and quit
  - Ctrl+G → create/enter buffer
  - Ctrl+L → enter list mode
  - Ctrl+O → enter options mode
  - Ctrl+J → read clipboard aloud
- Alphanumeric (no Ctrl):
  - If buffer key → enter buffer
  - If list → read/enter list mode
  - First press → read value
  - Second press → copy OR smart action (based on config)
```

**Coupling diagram for read_handler:**
```
        read_handler
             |
    +--------+--------+
    |        |        |
  Store    Mark    Mode
    |        |        |
  SQLite   stack   state
           |
      last_retrieved (scratch + channel)
```

**In-degree coupling:**
- read_handler is the DEFAULT mode - everything starts here
- Other modes return to read mode on completion
- Most user workflows begin and end in read_handler

#### 2. store.py (23KB) - INFRASTRUCTURE DRAGON

**Why it's a dragon:**
- **Single responsibility violation:** Handles DB schema, queries, config, history, lists, buffers
- **High in-degree:** Every component depends on Store
- **No separation of concerns:** Persistence + domain logic mixed
- **Schema management:** CREATE.sql separate from code (sync risk)

**Likely internal complexity (from external observation):**
```
- Database initialization and migrations
- Hierarchical buffer queries (recursive?)
- History tracking with deleted flag
- List operations (append, items, delete)
- Config get/set
- Entry CRUD with data_type discrimination
```

**Risk factors:**
- If Store breaks, entire system breaks
- No abstraction layer - handlers directly call SQLite methods
- Testing requires full DB setup

#### 3. mark.py - STATE DRAGON

**Why it's a dragon:**
- **Implicit coupling:** last_retrieved used as inter-mode communication channel
- **Stack management:** Buffer navigation stack (into/back)
- **Unclear contracts:** What goes in last_retrieved? When is it cleared?

**Usage patterns:**
```python
# As tracking:
ctx.mark.last_retrieved = {"key": char, "buffer_id": ..., "value": ...}

# As inter-mode channel (COUPLING!):
ctx.mark.last_retrieved = {
    "_history_setup": {...},  # For history mode
    "_list_setup": {...},     # For list mode
}
```

**Risk:** Adding new modes requires knowing the implicit contract of last_retrieved.

#### 4. mode.py - STATE MACHINE DRAGON

**Why it's a dragon:**
- **Dynamic typing:** Mode.state is a dict with no schema
- **Unclear contracts:** What keys exist in state? What types?
- **Mode registration:** Handlers registered at runtime
- **Event routing:** Dispatches to handlers based on current mode

**Risk factors:**
- Adding a mode requires understanding state dict conventions
- No type checking on state access
- Mode switches can leave stale state

### Dragon Summary Table

| Component | Size | Complexity | In-Degree | Churn Risk | Dragon Level |
|-----------|------|------------|-----------|------------|-------------|
| read_handler | 150+ LOC | VERY HIGH | CRITICAL | HIGH | 🐉🐉🐉🐉 |
| Store class | 23KB | HIGH | CRITICAL | MEDIUM | 🐉🐉🐉 |
| Mark.last_retrieved | N/A | MEDIUM | HIGH | MEDIUM | 🐉🐉 |
| Mode.state dict | N/A | MEDIUM | MEDIUM | LOW | 🐉 |
| history_handler | ~150 LOC | MEDIUM | LOW | LOW | 🔥 |
| list_handler | ~150 LOC | MEDIUM | LOW | LOW | 🔥 |

**Legend:**
- 🐉🐉🐉🐉 = Here be monsters - touch with extreme caution
- 🐉🐉🐉 = Major dragon - comprehensive tests required
- 🐉🐉 = Minor dragon - coupling risk
- 🔥 = Hotspot - complex but isolated

## Recommendations for Dragon Taming

### Immediate Risks

1. **read_handler complexity bomb**
   - 15+ control flow paths in one function
   - Consider: Extract Ctrl+key handlers to separate functions
   - Consider: Command pattern for actions

2. **Mark.last_retrieved coupling**
   - Used for both tracking AND inter-mode communication
   - Consider: Separate channels (e.g., mode_transition_data)
   - Consider: Explicit mode setup methods

3. **No config caching**
   - Every action reads config from SQLite
   - Consider: Load config on startup, cache in memory

4. **Store single responsibility violation**
   - DB + domain logic mixed
   - Consider: Repository pattern (BufferRepo, HistoryRepo, ConfigRepo)

### Testing Coverage Gaps

**From test files observed:**
- test_handlers.py (42KB) - likely covers main flows
- test_store.py (27KB) - likely covers DB operations
- test_mode.py (32KB) - likely covers mode switching

**What's probably NOT tested:**
- Ctrl+key combinations with edge cases
- Mode transitions with stale state
- Config changes mid-operation
- Buffer navigation edge cases (deep nesting)
- History with large result sets

### Refactoring Opportunities

**Low-hanging fruit:**
1. Extract Ctrl+key handlers from read_handler
2. Cache config in memory
3. Type last_retrieved with dataclass/NamedTuple

**Medium effort:**
4. Split Store into focused repositories
5. Command pattern for reversible actions
6. Explicit mode transition protocol

**High effort:**
7. Event sourcing for history (vs soft deletes)
8. CQRS for read vs write paths
9. Separate UI state from domain state

## Next Steps

Once git log approval comes through, we can:
1. Identify churn hotspots (most-changed files)
2. Cross-reference with complexity dragons
3. Prioritize refactoring based on churn × complexity

For now, the complexity analysis identifies **read_handler** and **Store** as the primary dragons requiring careful handling.
