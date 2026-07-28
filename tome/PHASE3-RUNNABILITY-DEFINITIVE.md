# Phase 3: Runnability Assessment — Definitive Static Analysis

**Date:** 2026-05-21
**Method:** Comprehensive static analysis (all key source files read and traced)
**Bash execution:** Not available (approval not granted)

## Executive Summary

**Verdict: The main application will NOT run from a clean install.** Module tests should mostly pass. The codebase has one hard blocker, one config conflict, and several environment-dependent issues.

## Finding 1: HARD BLOCKER — pyperclip ImportError

**Severity:** Critical — prevents application startup

- `tome.py` line 32: `import pyperclip` — unconditional top-level import
- `pyproject.toml` line 17: pyperclip is commented out as `# Future`
- A clean `pip install .` or `pip install -e .[dev]` does NOT install pyperclip
- Running `python tome.py` → immediate `ImportError: No module named 'pyperclip'`

**Impact:** The main application cannot start at all from a clean install.

**Workaround:** `pip install pyperclip` manually, but this shouldn't be required.

**Fix:** Either:
1. Add `pyperclip` to `dependencies` in pyproject.toml, or
2. Move the import inside `clipboard_handler()` in handlers.py (lazy import), or
3. Remove the top-level import from tome.py and use conditional import where needed

**Note:** `handlers.py` does NOT import pyperclip at the top level (its imports are: os, re, webbrowser, listener, mode). The pyperclip usage is likely inside `clipboard_handler()`. This means tests that import handlers directly (test_handlers.py, test_integration.py, test_wire.py) bypass this blocker.

## Finding 2: pytest Configuration Conflict

**Severity:** Medium — causes unexpected test discovery behavior

- `pytest.ini` line 2: `testpaths = .` (discover from project root)
- `pyproject.toml` line 25: `testpaths = ["store", "teller", "mark", "mode", "listener"]` (module tests only)
- Per pytest precedence rules, `pytest.ini` wins over `pyproject.toml`

**Consequence:** Running `pytest` discovers ALL test files including root-level:
- `test_handlers.py` (45.8KB) — proper pytest file, should work
- `test_integration.py` (5.6KB) — **script, not pytest tests**
- `test_wire.py` (2.4KB) — **script, not pytest tests**

**Side effects of collecting scripts as tests:**
- `test_integration.py` line 10-14: monkey-patches `os._exit` at import time (module-level code)
- `test_wire.py` line 4-9: executes Store creation, Mode wiring, and print statements at import time
- These side effects run when pytest merely *collects* these files, potentially affecting other tests

**Fix:** Either:
1. Delete `pytest.ini` (let pyproject.toml control test discovery), or
2. Align pytest.ini testpaths with pyproject.toml, or
3. Add `collect_ignore` in conftest.py for the script files

## Finding 3: pynput Requires X11/Display

**Severity:** Medium — prevents running in headless/CI environments

- `listener/listener.py` line 14: `from pynput import keyboard` — top-level unconditional import
- `PynputListener.start()` creates `keyboard.Listener(suppress=True)` which requires X11
- In headless/SSH/CI environments, `pynput` import may succeed but `listener.start()` will fail

**Impact on tests:** Minimal. Tests use `MockListener` and import `KeyEvent`/`EventType`/`SpecialKey` which don't require X11. The `from pynput import keyboard` at line 14 runs on any import of the listener module, but pynput itself can usually be imported without X11 — it's the `keyboard.Listener()` call that fails.

**Impact on app:** `python tome.py` would fail on `self.listener.start(self._on_key)` in headless environments, even if the pyperclip issue is fixed.

## Finding 4: Module Tests Should Pass

**Confidence:** High (based on .pyc evidence and code structure)

**Evidence of prior successful runs:**
- `.pyc` files exist for pytest 7.4.3, 8.3.3, and 9.0.2 across all modules
- `.hypothesis/` directory with 30 constant files confirms property-based tests have run
- All modules (store, teller, mark, mode, listener) have proper pytest test files

**Module breakdown:**

| Module | Test Files | Expected Status |
|--------|-----------|----------------|
| store | test_store.py, test_store_gremlin.py, test_store_oracle.py | Should pass — pure SQLite, no external deps |
| teller | test_teller.py, test_teller_gremlin.py, test_teller_oracle.py | Should pass — text handler doesn't need espeak binary |
| mark | test_mark.py, test_gremlin_attacks.py | Should pass — depends on store only |
| mode | test_mode.py, test_mode_syndic.py | Should pass — uses mock teller/store |
| mode | test_mode_oracle.py | **Expected failures** — documents closure bug |
| listener | test_listener.py | Should pass — uses MockListener |

## Finding 5: Known mode.py Closure Bug

**Severity:** Low (known and documented)

- `mode.py`: `get_state()` lambda captures `self._current` by reference
- After a handler calls `ctx.switch()`, `get_state()` returns the NEW mode's state dict, not the original mode's
- `test_mode_oracle.py` documents this with tests explicitly expected to fail
- The `test_mode_oracle.py` .pyc files (28-29KB) confirm these tests have been compiled/run

## Finding 6: Script Tests vs Pytest Tests

**Severity:** Low — cosmetic/structural issue

- `test_integration.py`: Manual integration test using print() statements, no pytest assertions
- `test_wire.py`: Smoke test using print() statements, no pytest assertions  
- Both are designed to be run as `python test_integration.py` / `python test_wire.py`
- If collected by pytest (which happens due to pytest.ini), they:
  - Execute module-level code during collection
  - May pass vacuously (no assertions to fail) or cause side effects
  - `test_integration.py`'s `os._exit` patch is particularly dangerous

## Finding 7: espeak Binary Dependency

**Severity:** Low — has fallback

- `teller/handlers/espeak.py` shells out to the `espeak` binary
- Running with `--text` flag uses TextHandler (prints to stdout) instead
- Teller discovery is graceful — if espeak isn't available, text handler is used
- Tests use text handler, so espeak absence doesn't affect test runs

## Finding 8: Database Layer

**Severity:** None — works correctly

- SQLite-based, `CREATE.sql` exists, `lore.db` exists (37KB)
- Store creates tables if needed on init
- No external database dependencies
- Should work anywhere Python runs

## Runnability Matrix

| Scenario | Will it work? | Blocker |
|----------|:---:|---|
| `pip install .` then `python tome.py` | ❌ | pyperclip not in dependencies |
| `pip install pyperclip` then `python tome.py` (desktop) | ✅* | *pynput needs X11 |
| `pip install pyperclip` then `python tome.py` (headless) | ❌ | pynput needs X11 |
| `python tome.py --text` (desktop, pyperclip installed) | ✅ | — |
| `pytest` (module tests only, pyproject.toml paths) | ✅ | pytest.ini overrides paths |
| `pytest store/ teller/ mark/ mode/ listener/` (explicit) | ✅ | — |
| `pytest` (with pytest.ini, all tests) | ⚠️ | Side effects from script collection |
| `python test_wire.py` | ✅ | — |
| `python test_integration.py` | ✅ | — |

## Recommended Fixes (Priority Order)

1. **Add pyperclip to dependencies** or make the import conditional — Critical
2. **Delete pytest.ini** or align it with pyproject.toml — Medium
3. **Add `if __name__ == '__main__'` guards** to test_integration.py and test_wire.py — Low
4. **Document X11 requirement** for pynput in README — Low
