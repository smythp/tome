# Runnability Assessment

**Date:** 2026-04-22  
**Method:** File analysis only (bash execution unavailable)  
**Previous assessment:** 2026-01-23 (verdict: NOT RUNNABLE)

## Verdict: CONDITIONALLY RUNNABLE

The project has improved significantly since January 2026. The #1 critical blocker (missing `pyproject.toml`) has been resolved. The test suite is very likely runnable. The main application (`tome.py`) will fail due to an undeclared dependency.

## Changes Since Last Assessment (Jan 23, 2026)

| Issue | Jan 2026 | Apr 2026 | Status |
|-------|----------|----------|--------|
| pyproject.toml | Missing | Present | ✅ Fixed |
| Dependencies declared | No | Yes (partial) | ⚠️ Partial |
| Makefile | Missing | Still missing | ❌ Open |
| Setup instructions | Missing | Still missing | ❌ Open |

## What Works

### Test Suite (High Confidence)

Strong evidence that tests run successfully:
- `.pyc` files exist for **3 different pytest versions** (7.4.3, 8.3.3, 9.0.2) across all test files
- `.hypothesis/constants/` contains **30 entries** — hypothesis tests have run extensively
- `.venv` contains Python 3.12 with pytest and hypothesis binaries
- `pytest.ini` is properly configured with markers and test discovery

Expected command: `source .venv/bin/activate && python -m pytest`

### Individual Modules (High Confidence)

All core modules use clean imports:
- **store/store.py**: stdlib only (`sqlite3`, `dataclasses`, `datetime`, `pathlib`, `typing`)
- **mark/mark.py**: `typing` only
- **mode/mode.py**: `logging`, `dataclasses`, `typing`
- **listener/listener.py**: stdlib + `pynput` (declared in pyproject.toml)
- **teller/**: stdlib + espeak (system binary, with text/debug fallback handlers)

All cross-module dependencies use Protocol classes — no circular imports.

### Dependency Management

`pyproject.toml` declares:
```toml
dependencies = ["pynput>=1.7.0"]
[project.optional-dependencies]
dev = ["pytest>=7.0.0", "hypothesis>=6.0.0"]
```

## What's Broken

### 1. Missing pyperclip Dependency (BUG)

**File:** `tome.py`, line 32  
**Impact:** `python tome.py` will crash with `ImportError: No module named 'pyperclip'`

```python
# tome.py line 32
import pyperclip  # NOT in pyproject.toml dependencies
```

`pyproject.toml` has pyperclip commented out as a future optional dep:
```toml
# Future: pyperclip will be needed when clipboard functionality is added
# clipboard = ["pyperclip>=1.8.0"]
```

But `tome.py` imports it unconditionally at module level. Either:
- Add `pyperclip>=1.8.0` to dependencies, or
- Make the import conditional/lazy

### 2. Conflicting Test Path Configuration

**pytest.ini** (takes precedence):
```ini
testpaths = .
```

**pyproject.toml**:
```toml
testpaths = ["store", "teller", "mark", "mode", "listener"]
```

pytest.ini wins, so root-level tests (`test_handlers.py`, `test_integration.py`, `test_wire.py`) ARE discovered. But if someone removes pytest.ini thinking pyproject.toml handles config, those 3 test files will silently stop running.

**Fix:** Either consolidate to one config location, or add root `.` to pyproject.toml testpaths.

### 3. espeak System Dependency

`teller/handlers/espeak.py` depends on the system `espeak` binary. This isn't pip-installable and isn't documented. The teller has fallback handlers (`text.py`, `debug.py`), so this isn't blocking for tests, but it blocks full application use.

## What's Still Missing

### No Makefile

No `make test`, `make setup`, or `make lint` targets. An agent or new developer must know to:
1. `python -m venv .venv`
2. `source .venv/bin/activate`
3. `pip install -e ".[dev]"`
4. `python -m pytest`

### No README Setup Instructions

README.md exists but setup steps aren't documented. CLAUDE.md mentions `python tome.py` and `sqlite3 lore.db < CREATE.sql` but not environment setup.

## Recommended Fixes (Priority Order)

1. **Add pyperclip to dependencies** or make import conditional — fixes the main app crash
2. **Consolidate pytest config** into pyproject.toml, remove pytest.ini — eliminates confusion
3. **Add Makefile** with `setup`, `test`, `lint` targets — standard agent/developer workflow
4. **Add setup section to README** — clone-to-running instructions
5. **Document espeak dependency** — note it's optional with fallback handlers

## Assessment Method

This assessment was performed through static file analysis:
- Read all source files for import statements
- Compared declared dependencies against actual imports
- Checked for .pyc files as evidence of prior execution
- Compared pytest.ini and pyproject.toml configurations
- Reviewed prior assessment (RUNNABILITY_FINDINGS.md, Jan 2026)

**Limitation:** Could not execute any code. Verdicts on test suite runnability are inferred from artifact evidence (.pyc files, .hypothesis directory) rather than actual execution.
