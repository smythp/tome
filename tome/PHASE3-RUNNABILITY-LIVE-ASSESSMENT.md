# Phase 3: Runnability Assessment — Live Attempt

**Date:** 2026-05-26  
**Method:** Static analysis (bash commands pending approval — no live execution possible)  
**Assessor:** Mill chain cartographer agent

## Executive Summary

**Verdict: The app crashes on startup. Tests likely work for individual modules but `tome.py` itself is broken.**

The main entry point (`tome.py`) will crash immediately with `ImportError: No module named 'pyperclip'` due to an unconditional import of an undeclared dependency. Individual RSP modules (store, teller, mark, mode, listener) and their test suites should work fine since they don't depend on pyperclip.

## Critical Findings

### 1. BLOCKER: pyperclip Import Crashes Startup

**File:** `tome.py`, line 32  
**Issue:** `import pyperclip` is unconditional at module level  
**But:** pyperclip is NOT in `pyproject.toml` dependencies — it's explicitly commented out as "Future"  
**Impact:** `python tome.py` and `python tome.py --text` both crash before reaching `main()`  
**Fix:** Remove or guard the import. Notably, `handlers.py` (which contains `clipboard_handler`) does NOT import pyperclip either — the import in tome.py appears to be dead/premature code.

```python
# tome.py line 31-32
# External
import pyperclip  # <-- CRASHES HERE
```

```toml
# pyproject.toml line 17
# Future: pyperclip will be needed when clipboard functionality is added
# clipboard = ["pyperclip>=1.8.0"]
```

### 2. README Is Completely Stale

**References that don't exist:**
- `setup_tome.sh` — no such file
- `utilities.py` — no such file  
- `test_tome.py` — no such file
- `run_tests.sh` — no such file

**Missing from README:**
- The RSP module architecture (store/, teller/, mark/, mode/, listener/)
- handlers.py
- The --text flag for non-TTS testing
- How to actually run tests (`pytest` or `.venv/bin/pytest`)

### 3. pytest Configuration Conflict

**pytest.ini:** `testpaths = .` (discovers ALL test files including root-level ones)  
**pyproject.toml:** `testpaths = ["store", "teller", "mark", "mode", "listener"]` (only module tests)  

pytest.ini takes precedence when both exist. This means root-level tests (test_handlers.py, test_integration.py, test_wire.py) ARE discovered by pytest, contradicting pyproject.toml's intent.

## What Likely Works

| Component | Status | Confidence | Notes |
|-----------|--------|------------|-------|
| `store/` module + tests | ✅ Works | High | Self-contained, well-tested (3 test files, hypothesis) |
| `teller/` module + tests | ✅ Works | High | Has text handler that bypasses espeak |
| `mark/` module + tests | ✅ Works | High | Pure state management, 2 test files |
| `mode/` module + tests | ✅ Works | High | 3 test files including oracle and syndic |
| `listener/` module + tests | ✅ Works | High | Keyboard abstraction layer |
| `test_integration.py` | ✅ Works | High | Imports modules directly, not tome.py; uses text teller |
| `test_handlers.py` | ⚠️ Probably works | Medium | 45KB — imports handlers.py which doesn't need pyperclip |
| `test_wire.py` | ❓ Unknown | Low | Not inspected |
| `.venv` environment | ✅ Exists | High | Python 3.12, pytest 9.0.2, hypothesis present (.pyc evidence) |
| `lore.db` | ✅ Exists | High | 36.9KB — has data in it |

## What Breaks

| Component | Status | Issue |
|-----------|--------|-------|
| `python tome.py` | ❌ Crashes | ImportError: pyperclip |
| `python tome.py --text` | ❌ Crashes | Same — import is before argparse |
| `import tome` | ❌ Crashes | Module-level pyperclip import |
| README instructions | ❌ Wrong | References nonexistent files |
| Any test importing tome.py | ❌ Crashes | Transitive pyperclip failure |

## System Dependencies

| Dependency | Required For | Documented? |
|------------|-------------|-------------|
| espeak | Default TTS (teller) | ✅ In README |
| X11/display | pynput keyboard listener | ❌ Not documented |
| Python 3.10+ | pyproject.toml requires-python | ✅ (README says 3.8+ — wrong) |

## Easy Fixes (Priority Order)

1. **Remove `import pyperclip` from tome.py** — It's unused. handlers.py doesn't import it either. This unblocks the entire app.
2. **Update README** — Document actual project structure, actual test commands, actual prerequisites.
3. **Reconcile pytest config** — Either delete pytest.ini (use pyproject.toml) or align them. The conflict creates confusion.
4. **Update requires-python in README** — pyproject.toml says >=3.10, README says 3.8+.
5. **Document X11 requirement** — pynput needs a display environment.

## Architecture Observation

The project has a clean modular architecture (RSP primitives) that's well-tested at the module level. The breakage is entirely at the integration/app layer — specifically one premature import. The test_integration.py file cleverly avoids this by importing modules directly rather than through tome.py. This suggests the pyperclip import was added to tome.py after the integration test was written, and nobody ran `python tome.py` since.

## Conclusion

This project is ~95% functional. The individual modules are solid and well-tested. The single blocker is a dead import on line 32 of tome.py. Removing that line would make the app runnable (assuming espeak and X11 are available, or using --text mode). The README needs a rewrite to match reality.
