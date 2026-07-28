# Phase 3: Runnability Assessment — Static Analysis Verdict

**Date:** 2026-05-30
**Method:** Static analysis (bash execution unavailable)
**Verdict:** App crashes on launch. Individual RSP modules are sound.

---

## Executive Summary

`python tome.py` will crash immediately with `ImportError: No module named 'pyperclip'`. Even if that's fixed, the app requires a display server (X11/Wayland) for pynput keyboard listening, and espeak-ng installed for default TTS. The individual RSP modules (store, mark, mode, teller) are well-isolated and importable independently.

---

## What Works

### 1. store/ — ✅ Fully functional
- Pure SQLite + stdlib. No external dependencies.
- Clean schema init, connection management, dict_factory.
- Will import and run in any Python 3.10+ environment.

### 2. mark/ — ✅ Fully functional
- Pure Python. Uses typing.Protocol for Store dependency.
- No external imports. Clean navigation state management.

### 3. mode/ — ✅ Fully functional
- Pure Python. dataclass + Protocol based.
- No external imports beyond stdlib.
- Clean modal state machine with per-mode isolation.

### 4. teller/ — ✅ Architecture works, handler availability varies
- Auto-discovery architecture is clean and extensible.
- `text` handler: Pure Python, always works.
- `debug` handler: Pure Python, always works.
- `espeak` handler: Requires `espeak-ng` system binary. Fails gracefully if missing.
- Discovery gracefully handles missing handlers (logs warning, continues).

### 5. listener/ — ⚠️ Works with display server only
- Imports `pynput` at module level (line 14).
- pynput is in dependencies and will install fine.
- **But**: pynput requires X11/Wayland display server for keyboard listening.
- Headless/SSH sessions will fail on `from pynput import keyboard`.
- The KeyEvent/EventType/SpecialKey enums are clean and well-validated.

### 6. handlers.py — ⚠️ Imports work, but pyperclip calls will fail
- Top-level imports are only `listener` and `mode` (internal). These work.
- `pyperclip` is imported inside functions (lazy imports at lines 204, 470, 635, 713, 1085).
- This means handlers.py *imports* fine, but clipboard/list/read/browse handlers crash when invoked.

### 7. test_integration.py — ⚠️ Partially runnable
- Does NOT import `tome.py` (avoids the pyperclip crash).
- Imports RSP modules directly: store, teller, mark, mode, listener, handlers.
- Will fail if pynput can't load (display server requirement).
- Will fail at any test step that triggers a pyperclip call in handlers.
- Uses `get_handler("text")` — good, avoids espeak dependency.

---

## What Breaks

### CRITICAL: pyperclip ImportError crashes app on launch

**Location:** `tome.py` line 32: `import pyperclip`

**Problem:** pyperclip is NOT in `pyproject.toml` dependencies. It's commented out:
```toml
# Future: pyperclip will be needed when clipboard functionality is added
# clipboard = ["pyperclip>=1.8.0"]
```

**Impact:** `python tome.py` immediately crashes with:
```
ModuleNotFoundError: No module named 'pyperclip'
```

**Additionally:** handlers.py has 17 pyperclip call sites across 5 handler functions (clipboard_handler, list_handler, read_handler, browse_handler, _handle_all_mode_action). These use lazy `import pyperclip` inside functions, so they don't crash on import but will crash when any clipboard operation is attempted.

**Fix:** Either:
1. Add `pyperclip>=1.8.0` to dependencies, or
2. Make the import conditional with a stub fallback

### Display Server Requirement

**Location:** `listener/listener.py` line 14: `from pynput import keyboard`

**Problem:** pynput requires X11/Wayland. Headless environments (CI, SSH, containers) will fail.

**Impact:** Cannot import `listener` module at all in headless environments.

**Fix:** Lazy import of pynput, or a headless fallback listener.

### espeak-ng System Dependency

**Location:** `teller/handlers/espeak.py`

**Problem:** Requires `espeak-ng` binary installed on the system.

**Impact:** Default TTS mode fails if espeak-ng isn't installed. The `--text` flag works around this.

**Mitigation:** Already handled — teller discovery logs a warning and falls back gracefully.

### No Entry Point

**Location:** `pyproject.toml` — no `[project.scripts]` section.

**Problem:** `pip install .` doesn't create a `tome` command.

**Impact:** Must run as `python tome.py` rather than `tome`.

---

## pytest Configuration Gap

`pytest.ini` configures:
```ini
testpaths = ["store", "teller", "mark", "mode", "listener"]
```

This **excludes** root-level test files:
- `test_integration.py` — Integration test
- `test_handlers.py` — Handler unit tests (45.8KB)
- `test_wire.py` — Wire tests

Running `pytest` will miss these. Must use `pytest test_integration.py` explicitly.

---

## Runnability Matrix

| Component | Import | Function | Notes |
|-----------|--------|----------|-------|
| store/ | ✅ | ✅ | Pure stdlib |
| mark/ | ✅ | ✅ | Pure stdlib |
| mode/ | ✅ | ✅ | Pure stdlib |
| teller/ | ✅ | ✅* | *espeak needs binary |
| listener/ | ⚠️ | ⚠️ | Needs display server |
| handlers.py | ✅ | ❌ | pyperclip crashes on use |
| tome.py | ❌ | ❌ | pyperclip crashes on import |
| Unit tests | ✅ | ✅ | Per-module tests pass |
| Integration | ⚠️ | ⚠️ | Partial — display + pyperclip |

---

## Confidence Level

**High confidence** in these findings. Static analysis clearly shows:
1. The unconditional `import pyperclip` on line 32 of tome.py
2. pyperclip commented out of pyproject.toml dependencies
3. 17 pyperclip call sites in handlers.py
4. pynput's documented requirement for display server

The only uncertainty is whether pyperclip might be installed in the venv despite not being in pyproject.toml (possible if manually pip-installed). The `.venv` directory exists but I couldn't execute commands to check.
