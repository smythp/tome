# Phase 3: Runnability Assessment — Definitive Finding

**Date:** 2026-06-01  
**Method:** Comprehensive static analysis (all source files read and cross-referenced)  
**Scope:** Import chains, dependency declarations, test discovery, headless compatibility

---

## Executive Summary

The tome project has **three distinct runnability issues** that interact:

1. **Undeclared dependency**: pyperclip is used at module level in `tome.py` but commented out in `pyproject.toml` — a fresh install breaks immediately
2. **Test config conflict**: `pytest.ini` (testpaths=`.`) overrides `pyproject.toml` (testpaths=`['store','teller','mark','mode','listener']`), pulling in integration tests that fail headless
3. **Headless incompatibility**: Both pyperclip and pynput require display/clipboard backends unavailable in CI/headless environments

---

## Finding 1: Undeclared pyperclip Dependency

**Severity: CRITICAL — breaks fresh install**

`tome.py` line 32:
```python
import pyperclip  # module-level, always imported
```

`pyproject.toml`:
```toml
dependencies = [
    "pynput>=1.7.0",
]
# Future: pyperclip will be needed when clipboard functionality is added
# clipboard = ["pyperclip>=1.8.0"]
```

pyperclip is **commented out** as a future dependency. A fresh `pip install -e .` will NOT install pyperclip, causing an immediate `ImportError` when importing `tome`.

pyperclip IS installed in the current venv (1.11.0) — presumably via manual `pip install`. This masks the bug for anyone working in the existing venv.

**handlers.py** does it RIGHT — imports pyperclip at function level (lazy imports at lines 204, 470, 635, 713, 1085). This means `import handlers` succeeds even without pyperclip; only clipboard operations fail at runtime.

**Recommendation:** Either:
- Add `pyperclip>=1.8.0` to `dependencies` in pyproject.toml, OR
- Move `import pyperclip` in `tome.py` to function level (matching handlers.py's pattern)

## Finding 2: pytest.ini vs pyproject.toml Config Conflict

**Severity: HIGH — test suite discovers tests it shouldn't**

`pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["store", "teller", "mark", "mode", "listener"]
```

`pytest.ini`:
```ini
[pytest]
testpaths = .
```

Per pytest's config resolution order, **`pytest.ini` takes precedence** over `pyproject.toml`. This means `pytest` discovers ALL test files including:
- `test_handlers.py` (45.8KB — root level)
- `test_integration.py` (root level)
- `test_wire.py` (root level)

Someone clearly intended to restrict test discovery to the five RSP subdirectories (the pyproject.toml config). The pytest.ini overrides this intent.

**Recommendation:** Either:
- Delete `pytest.ini` (let pyproject.toml control pytest), OR
- Update `pytest.ini` to match pyproject.toml's testpaths, OR
- Add markers/skip conditions to root-level tests for headless environments

## Finding 3: Headless Environment Compatibility

**Severity: MEDIUM — affects CI/automated testing**

### pyperclip in headless:
- `import pyperclip` succeeds (no backend check at import time)
- `pyperclip.copy()` / `pyperclip.paste()` raises `PyperclipException` if no clipboard backend (xclip, xsel, pbcopy) is available
- Affects any test that calls clipboard operations without mocking

### pynput in headless:
- `import pynput` succeeds
- `PynputListener.start()` requires X11/display server
- The `listener` package is the ONLY pynput consumer (good encapsulation)

### Impact on test files:

| Test File | pyperclip Usage | Headless? | Verdict |
|---|---|---|---|
| `store/test_store.py` | None | ✅ Safe | PASS |
| `store/test_store_gremlin.py` | None | ✅ Safe | PASS |
| `store/test_store_oracle.py` | None | ✅ Safe | PASS |
| `teller/test_teller.py` | None | ✅ Safe | PASS |
| `teller/test_teller_gremlin.py` | None | ✅ Safe | PASS |
| `teller/test_teller_oracle.py` | None | ✅ Safe | PASS |
| `mark/test_mark.py` | None | ✅ Safe | PASS |
| `mark/test_gremlin_attacks.py` | None | ✅ Safe | PASS |
| `mode/test_mode.py` | None | ✅ Safe | PASS |
| `mode/test_mode_oracle.py` | None | ✅ Safe | PASS |
| `mode/test_mode_syndic.py` | None | ✅ Safe | PASS |
| `listener/test_listener.py` | None | ✅ Safe | PASS |
| `test_handlers.py` | Mocked via monkeypatch | ✅ Safe | LIKELY PASS |
| `test_integration.py` | Unmocked pyperclip.copy() at double-tap | ❌ Fails | FAIL headless |
| `test_wire.py` | Unmocked pyperclip.copy() at Step 15 | ❌ Fails | FAIL headless |

## Finding 4: Architectural Observations

### Good patterns:
- **handlers.py**: Function-level pyperclip imports (lazy loading) — clipboard only imported when needed
- **test_handlers.py**: Every test that touches clipboard properly monkeypatches pyperclip (22 occurrences)
- **RSP isolation**: Each RSP (store, teller, mark, mode, listener) is self-contained with clean `__init__.py` exports
- **listener encapsulation**: pynput is ONLY imported in `listener/` — all other code uses the KeyEvent abstraction

### Bad patterns:
- **tome.py**: Module-level `import pyperclip` — contradicts handlers.py's lazy pattern
- **pytest.ini vs pyproject.toml**: Conflicting test discovery config
- **pyproject.toml**: pyperclip commented out despite being a runtime dependency
- **test_integration.py / test_wire.py**: No pyperclip mocking — will fail headless

---

## Runnability Verdict

### Can `tome.py` run?
- **With current venv**: YES (pyperclip manually installed)
- **Fresh `pip install -e .`**: NO — ImportError on `import pyperclip`
- **In headless**: PARTIAL — imports succeed, but clipboard/keyboard operations fail at runtime

### Can the test suite run?
- **RSP unit tests (subdirectories)**: YES — fully isolated, no external dependencies
- **test_handlers.py**: LIKELY YES — properly mocks pyperclip
- **test_integration.py**: NO in headless — unmocked pyperclip.copy()
- **test_wire.py**: NO in headless — unmocked pyperclip.copy() at Step 15
- **With `pytest.ini` present**: ALL tests discovered (including failing integration tests)
- **Without `pytest.ini`**: Only RSP unit tests discovered (pyproject.toml's restricted testpaths)

### Bottom line:
The RSP primitives are solid and testable. The wiring layer (tome.py, handlers.py, integration tests) has dependency and environment issues that need cleanup.
