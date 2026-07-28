# Phase 3: Runnability Assessment — Static Analysis

**Date:** 2026-05-13
**Method:** Static analysis (no execution — bash approval unavailable)
**Scope:** Full codebase import chain, dependency resolution, runtime requirements

---

## Verdict: NOT RUNNABLE (1 blocker, 2 environmental issues)

---

## 🔴 BLOCKER: `pyperclip` imported but not installed

**Impact:** `python tome.py` crashes immediately with `ModuleNotFoundError`

**Evidence:**
- `tome.py` line 32: `import pyperclip` — unconditional, top-level import
- `pyproject.toml`: pyperclip is NOT in `dependencies` (commented out as future)
- `uv.lock`: pyperclip absent (grep confirms zero matches)
- `handlers.py`: 17 occurrences of `pyperclip` across 6+ handler functions (local imports)

**Root cause:** The import was added to `tome.py` before pyperclip was added as a dependency. The `pyproject.toml` has a comment: `# Future: pyperclip will be needed when clipboard functionality is added` — but it's already being used extensively.

**Fix options (pick one):**
1. **Add dependency:** Add `"pyperclip>=1.8.0"` to `pyproject.toml` dependencies, run `uv lock && uv sync`
2. **Defer import:** Remove top-level `import pyperclip` from `tome.py` (handlers.py already uses local imports via `import pyperclip` inside each function that needs it)
3. **Both:** Add the dependency AND keep the local import pattern (most robust)

**Recommendation:** Option 3. Add pyperclip to dependencies (it's clearly needed — 17 usages in handlers.py) AND remove the top-level import from tome.py line 32 since every handler already does its own local import.

---

## 🟡 ISSUE: `pynput` requires display server (X11/Wayland)

**Impact:** Fails in headless environments (SSH, CI, containers, WSL without display)

**Evidence:**
- `listener/listener.py` line 14: `from pynput import keyboard` — top-level, unconditional
- `listener/__init__.py` re-exports everything, triggering the import
- `tome.py` line 29: `from listener import PynputListener, KeyEvent, EventType`
- pynput IS properly declared in `pyproject.toml` dependencies

**Behavior:** On a headless system, importing `pynput.keyboard` raises an exception because pynput tries to connect to the display server at import time.

**Workaround for testing:** `MockListener` exists and is used in tests, but the import of `listener/__init__.py` still triggers the pynput import. Tests that import listener will fail headless.

**Fix options:**
1. Lazy-import pynput inside `PynputListener.__init__()` or `start()` instead of module level
2. Guard with try/except at module level, making PynputListener unavailable when pynput can't connect
3. Accept this as a known constraint (tome is a desktop app, pynput is appropriate)

**Recommendation:** Option 2 for best DX. Wrap the pynput import in a try/except, set `PynputListener = None` on failure, and document that `MockListener` is the headless alternative.

---

## 🟡 ISSUE: `espeak` binary dependency (graceful degradation)

**Impact:** Default TTS mode (`espeak`) is silent if espeak/espeak-ng not installed

**Evidence:**
- `teller/handlers/espeak.py`: `_find_espeak()` uses `shutil.which()` to find binary
- If not found, logs warning but handler still registers (speak becomes a no-op)
- `teller/__init__.py`: Falls back to `text` handler if espeak unavailable
- `tome.py`: `--text` flag explicitly selects text output

**Assessment:** This is handled well — graceful degradation, fallback handler, CLI flag. Not a blocker.

---

## ✅ What Works (Pure Python, no issues)

| Module | Status | Notes |
|--------|--------|-------|
| `store/` | ✅ Clean | sqlite3 (stdlib), proper schema init via `_init_db()` |
| `mark/` | ✅ Clean | Pure Python, uses Protocol for Store dependency |
| `mode/` | ✅ Clean | Pure Python, uses Protocols, no external deps |
| `teller/base.py` | ✅ Clean | Pure ABC |
| `teller/discovery.py` | ✅ Clean | importlib (stdlib) |
| `teller/handlers/text.py` | ✅ Clean | Just prints to stdout |
| `teller/__init__.py` | ✅ Clean | Discovery gracefully handles missing handlers |
| `handlers.py` (import) | ✅ Clean | Only stdlib + internal imports at top level |

---

## Database Initialization

- `Store.__init__()` calls `_init_db()` which creates tables automatically
- `CREATE.sql` exists as a manual alternative (`sqlite3 lore.db < CREATE.sql`)
- `tome.py` creates `~/.tome/` directory and uses `~/.tome/lore.db`
- A `lore.db` already exists in project root (36.9KB) — likely dev/test data
- Schema: `lore` table (hierarchical entries) + `config` table (key-value settings)

---

## Test Infrastructure

| Aspect | Status | Notes |
|--------|--------|-------|
| Framework | pytest + hypothesis | Both declared as dev dependencies |
| Config conflict | ⚠️ Minor | `pytest.ini` says `testpaths = .` but `pyproject.toml` says `testpaths = ["store", "teller", "mark", "mode", "listener"]`. pytest.ini wins (it takes precedence). |
| Test files | Extensive | All RSP modules have tests, including gremlin (fuzz) and oracle (property) variants |
| MockListener | Available | For testing without display server |
| Headless test runs | ⚠️ Risky | `import listener` triggers pynput import; tests touching listener may fail headless |

---

## Architecture Observations

1. **Clean RSP design** — Each module (Store, Teller, Mark, Mode, Listener) is a self-contained primitive with its own Protocol definitions to avoid circular imports.

2. **Handler pattern** — `handlers.py` contains all mode handler functions. These use local `import pyperclip` inside function bodies (good practice for optional deps), but `tome.py` defeats this by importing pyperclip unconditionally at module level.

3. **Mode registration** — `tome.py` calls `self.mode.register('read', read_handler, message='Read from tome')` which is a convenience API on `Mode.register()` that accepts `(name, handler, **kwargs)` and wraps into `ModeConfig`.

4. **Discovery pattern** — `teller/discovery.py` scans `teller/handlers/` for `BaseHandler` subclasses, instantiates them, and registers by `.name` property. Clean and extensible.

---

## Priority Fix Order

1. **[CRITICAL]** Add `pyperclip>=1.8.0` to pyproject.toml dependencies + remove top-level import from tome.py line 32
2. **[NICE-TO-HAVE]** Guard pynput import in listener.py for headless environments
3. **[COSMETIC]** Resolve pytest.ini vs pyproject.toml testpaths conflict
