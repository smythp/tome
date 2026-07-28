# Runnability Assessment: Tome of Lore

**Date:** 2026-05-28
**Method:** Static analysis of source, dependencies, and test configuration
**Verdict:** RSP modules run fine individually; main entry point (tome.py) crashes on import

## Critical Blocker

**tome.py imports `pyperclip` at module level, but pyperclip is NOT in dependencies.**

```python
# tome.py line ~17
import pyperclip
```

```toml
# pyproject.toml - commented out as future
# Future: pyperclip will be needed when clipboard functionality is added
# clipboard = ["pyperclip>=1.8.0"]
```

Running `python tome.py` or `uv run tome.py` will crash immediately with `ImportError: No module named 'pyperclip'`.

**Fix:** Either add pyperclip to dependencies, or make the import conditional/lazy.

## RSP Module Status (All Good)

| Module | Imports | Status | Notes |
|--------|---------|--------|-------|
| store/store.py | sqlite3, dataclasses, datetime, pathlib, typing | ✅ OK | All stdlib |
| mark/mark.py | typing (Protocol) | ✅ OK | All stdlib |
| mode/mode.py | logging, dataclasses, typing | ✅ OK | All stdlib |
| listener/listener.py | pynput, logging, threading, dataclasses, enum | ✅ OK | pynput is in deps |
| teller/__init__.py | .base, .discovery | ✅ OK | Internal imports |
| teller/base.py | abc | ✅ OK | Stdlib |
| teller/discovery.py | importlib, logging, pathlib | ✅ OK | All stdlib |
| handlers.py | os, re, webbrowser, listener, mode | ✅ OK | Stdlib + internal |

Each RSP module can be imported independently without error (assuming pynput is installed, which it is via dependencies).

## Test Configuration Conflict

**pytest.ini and pyproject.toml disagree on test discovery paths.**

- `pytest.ini`: `testpaths = .` (discovers ALL test files, including root-level)
- `pyproject.toml`: `testpaths = ["store", "teller", "mark", "mode", "listener"]` (RSP dirs only)

**pytest.ini takes precedence** (ini files override pyproject.toml). This means `pytest` will discover:
- RSP unit tests: store/test_store.py, mark/test_mark.py, etc.
- Root integration tests: test_integration.py, test_wire.py, test_handlers.py

This isn't necessarily a bug, but it contradicts the pyproject.toml intent. The root-level tests are substantial (test_handlers.py is 45.8KB).

## Test Runnability Prediction

| Test File | Should Run? | Notes |
|-----------|-------------|-------|
| store/test_store.py | ✅ Yes | Stdlib deps only |
| store/test_store_gremlin.py | ✅ Yes | Stdlib deps only |
| store/test_store_oracle.py | ✅ Yes | Stdlib deps only |
| mark/test_mark.py | ✅ Yes | Stdlib deps only |
| mark/test_gremlin_attacks.py | ✅ Yes | Stdlib deps only |
| mode/test_mode.py | ✅ Yes | Stdlib deps only |
| mode/test_mode_oracle.py | ✅ Yes | Stdlib deps only |
| mode/test_mode_syndic.py | ✅ Yes | Stdlib deps only |
| listener/test_listener.py | ✅ Yes | pynput in deps |
| teller/test_teller.py | ✅ Yes | Internal deps only |
| teller/test_teller_gremlin.py | ✅ Yes | Internal deps only |
| teller/test_teller_oracle.py | ✅ Yes | Internal deps only |
| test_handlers.py | ✅ Yes | Does NOT import pyperclip |
| test_integration.py | ✅ Yes | Does NOT import pyperclip |
| test_wire.py | ✅ Yes | Does NOT import pyperclip |

**Key insight:** The root-level integration tests import from RSP modules and handlers directly—they do NOT import tome.py or pyperclip. So the test suite should run cleanly.

## Runtime Dependencies

| Dependency | Required By | In pyproject.toml? | Status |
|------------|-------------|---------------------|--------|
| pynput | listener.py | ✅ Yes | Installed |
| pyperclip | tome.py | ❌ No (commented out) | **MISSING** |
| espeak | teller/handlers/espeak.py | N/A (system dep) | Needed for default TTS |
| sqlite3 | store.py | N/A (stdlib) | Always available |
| hypothesis | Tests | ✅ Yes (dev dep) | Needed for property tests |
| pytest | Tests | ✅ Yes (dev dep) | Test runner |

## Database

- `lore.db` exists (36.9KB) in the project root
- `CREATE.sql` defines schema: `lore` table + `config` table + root buffer insert
- Store._init_db() auto-creates schema if missing — no manual DB setup needed
- Default DB path in tome.py is `~/.tome/lore.db`, but accepts `--db` flag

## Summary

1. **tome.py is broken** due to unconditional `import pyperclip` with no pyperclip in deps
2. **All RSP modules import cleanly** — well-isolated with minimal dependencies
3. **Test suite should pass** — tests don't touch the pyperclip import path
4. **pytest.ini overrides pyproject.toml** test discovery — may be intentional or not
5. **espeak is a runtime dep** for the default teller handler, but text/debug modes work without it
