# Tome Mode Inventory

## Overview

8 modes total. Each mode is a key handler function that receives a pynput key event.

---

## 1. default mode

**Function:** `default(key)`
**Message:** "Tome of Lore"

**What it does:** Nothing. Empty handler - mode switching is done at key_handler level.

**State:** None

**Keys:** None

**RSP mapping:** Trivial - just a placeholder mode.

---

## 2. read mode (HOME MODE)

**Function:** `read(key)`
**Message:** "Read from tome"

**What it does:** Primary interaction mode. Read values, navigate buffers, trigger actions.

**State accessed:**
- `current_buffer_id` → Mark.buffer_id
- `buffer_stack` → Mark.stack
- `buffer_path` → Mark.path
- `last_retrieved` → Mark.last_retrieved
- `key_presses` → double-tap tracking (new: Listener?)
- `history_state` → Mode.get_state()
- `strip_input` → Store.get_config()
- `default_action` → Store.get_config()

**Keys:**
| Key | Action |
|-----|--------|
| `[a-z0-9]` | Read value at key (1st press), copy/action (2nd press) |
| `Delete` | Soft-delete last retrieved entry |
| `Ctrl+C` | Copy last value, exit |
| `Ctrl+B` | Browse URL, exit |
| `Ctrl+T` | Read timestamp of last value |
| `Ctrl+H` | Enter history mode for last key |
| `Ctrl+Y` | Write clipboard to last key, exit |
| `Ctrl+G` | Create buffer at last key |
| `Ctrl+O` | Enter options mode |
| `Ctrl+J` | Read clipboard aloud |
| `Ctrl+L` | Enter list mode for last key |
| (buffer key) | Enter buffer, stay in read mode |

**Complexity:** HIGH - this is the main mode, ~300 lines

---

## 3. history mode

**Function:** `history(key)`
**Message:** "Viewing history"

**What it does:** Navigate through historical values for a key or global history.

**State accessed:**
- `history_state` → Mode.get_state() with structure:
  ```python
  {
    'active': bool,
    'key': str,
    'buffer_id': int,
    'entries': list,
    'current_index': int,
    'global_mode': bool
  }
  ```
- `last_retrieved` → Mark.last_retrieved

**Keys:**
| Key | Action |
|-----|--------|
| `Up` / `Ctrl+P` | Previous (older) entry |
| `Down` / `Ctrl+N` | Next (newer) entry |
| `Ctrl+Z` | Restore selected entry as current |
| `Ctrl+R` | Undelete a soft-deleted entry |
| `Ctrl+T` | Read timestamp |
| `Ctrl+C` | Copy to clipboard |
| `Ctrl+B` | Browse URL |
| `Ctrl+J` | Read clipboard |
| `Delete` | Soft-delete entry |
| `Escape` | Exit to read mode |
| (any other char) | Exit to read mode |

**Complexity:** MEDIUM - ~150 lines including helper functions

---

## 4. options mode

**Function:** `options(key)`
**Message:** "Options: Press s for strip input, d for debug mode, a for default action"

**What it does:** Toggle application settings.

**State accessed:**
- `strip_input` → Store.get_config/set_config
- `debug_mode` → Store.get_config/set_config
- `default_action` → Store.get_config/set_config

**Keys:**
| Key | Action |
|-----|--------|
| `s` | Toggle strip_input |
| `d` | Toggle debug_mode |
| `a` | Toggle default_action (copy/auto) |
| `Escape` | Exit to read mode |

**Complexity:** LOW - ~35 lines

---

## 5. clipboard mode

**Function:** `clipboard(key)`
**Message:** "Store from clipboard"

**What it does:** Store clipboard content at a key.

**State accessed:**
- `current_buffer_id` → Mark.buffer_id
- `strip_input` → Store.get_config()

**Keys:**
| Key | Action |
|-----|--------|
| `[a-z0-9]` | Store clipboard at key, exit |
| `Escape` | Exit to read mode |

**Complexity:** LOW - ~40 lines

---

## 6. browse mode

**Function:** `browse(key)`
**Message:** "Browse URL"

**What it does:** Enter URL by key presses, then browse.

**State accessed:**
- `current_buffer_id` → Mark.buffer_id
- (builds URL from key presses - transient state)

**Keys:**
| Key | Action |
|-----|--------|
| `[a-z0-9]` | Read value at key, open as URL |
| `Escape` | Exit to read mode |

**Complexity:** LOW - ~40 lines

---

## 7. list mode

**Function:** `list_mode(key)`
**Message:** "List mode"

**What it does:** Navigate and manipulate ordered lists.

**State accessed:**
- `list_state` → Mode.get_state() with structure:
  ```python
  {
    'active': bool,
    'list_id': int,
    'key': str,
    'buffer_id': int,
    'items': list,
    'current_index': int
  }
  ```
- `current_buffer_id` → Mark.buffer_id
- `last_retrieved` → Mark.last_retrieved

**Keys:**
| Key | Action |
|-----|--------|
| `Up` / `Left` / `p` / `k` / `Ctrl+P` | Previous item (toward item 1) |
| `Down` / `Right` / `n` / `j` / `Ctrl+N` | Next item (away from item 1) |
| `,` | Jump to top (item 1) |
| `.` | Jump to end (highest number) |
| `a` | Append clipboard to list (becomes new item 1) |
| `Enter` | Read current item |
| `Delete` | Delete current item |
| `Backspace` | Exit to read mode |
| `?` | Help |

**Complexity:** MEDIUM - ~170 lines including enter_list_mode helper

---

## 8. confirm mode

**Function:** `confirm(key)`
**Message:** None (dynamic based on action)

**What it does:** Confirmation dialog for destructive actions (delete buffer).

**State accessed:**
- `confirm_state` → Mode.get_state() with structure:
  ```python
  {
    'active': bool,
    'action': str,  # e.g., 'delete_buffer'
    'params': dict,
    'prompt': str,
    'previous_mode': str
  }
  ```

**Keys:**
| Key | Action |
|-----|--------|
| `y` | Confirm action |
| `n` / `Escape` | Cancel, return to previous mode |

**Complexity:** LOW - ~50 lines

---

## 9. read_clipboard (not a mode, just a function)

**Function:** `read_clipboard()`
**Message:** "Reading clipboard"

Just speaks clipboard content. Called from other modes, not a standalone mode.

---

## Shared State Summary

| State | Current | RSP Target |
|-------|---------|------------|
| current_buffer_id | global | Mark.buffer_id |
| buffer_stack | global | Mark.stack |
| buffer_path | global | Mark.path |
| last_retrieved | global dict | Mark.last_retrieved |
| key_presses | global dict | Listener (repeat_count) or app state |
| history_state | global dict | Mode.get_state() |
| list_state | global dict | Mode.get_state() |
| confirm_state | global dict | Mode.get_state() |
| strip_input | global | Store.get_config() |
| debug_mode | global | Store.get_config() |
| default_action | config | Store.get_config() |
| suppress_mode_message | global | Mode.switch(silent=True) |

---

## Helper Functions Used by Modes

These need to be ported or replaced:

- `retrieve(key, buffer_id, fetch='single'|'history')` → Store.get(), Store.history()
- `store(key, value, ...)` → Store.set()
- `enter_buffer(key)` → Mark.into() + Store lookup
- `create_buffer_at_key(key, parent)` → Store.create_buffer()
- `is_key_a_buffer(key, buffer_id)` → Store.is_buffer()
- `soft_delete_entry(id)` → Store.delete()
- `restore_entry(id)` → Store.restore()
- `get_list_items(list_id)` → Store.list_items()
- `connect()` → Store handles internally
- `speak(text)` → Teller.speak()
- `copy(text)` → pyperclip.copy() (external)
- `paste()` → pyperclip.paste() (external)
- `open_url(url)` → webbrowser.open() (external)
- `exit()` → sys.exit() or app.quit()

---

## Mode Transition Graph

```
                    ┌──────────┐
                    │  default │ (startup only)
                    └────┬─────┘
                         │
                         ▼
    ┌──────────────────────────────────────┐
    │               read                    │ ◄─── HOME MODE
    │  (primary interaction)               │
    └──┬────┬────┬────┬────┬────┬────┬────┘
       │    │    │    │    │    │    │
       ▼    ▼    ▼    ▼    ▼    ▼    ▼
   history list confirm options clipboard browse (enter buffer)
       │    │    │    │    │    │         │
       └────┴────┴────┴────┴────┴─────────┘
                         │
                         ▼
                    (back to read)
```

---

## Complexity Ranking (for porting order)

1. **options** - LOW, pure config toggles
2. **confirm** - LOW, simple y/n
3. **clipboard** - LOW, store and exit
4. **browse** - LOW, read and open
5. **history** - MEDIUM, stateful navigation
6. **list** - MEDIUM, stateful navigation
7. **read** - HIGH, kitchen sink

Recommendation: Port in this order.
