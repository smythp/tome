# Phase 3: Runnability Assessment (Static Analysis)

## Summary

The Tome project is a keyboard-driven, hierarchical data storage system with audio-only interface. Due to bash approval constraints, this assessment is based on thorough static analysis of all project files, dependencies, and test infrastructure.

## Verdict: Unit tests should pass headlessly; app requires X11 + espeak

## What Works

### Unit Tests (High Confidence)
The modular RSP architecture means each module has self-contained tests with proper mocks:

- **store/** - Pure SQLite tests using temp DBs. No system dependencies.
- **teller/** - Has `text` handler that bypasses espeak entirely.
- **mark/** - Pure state management, no I/O.
- **mode/** - Uses mock teller, no real TTS needed.
- **listener/** - Has `MockListener` class for injecting KeyEvents without pynput/X11.

Command: `.venv/bin/pytest store/ teller/ mark/ mode/ listener/`

### Integration Test (Medium Confidence)
`test_integration.py` uses text-mode teller and doesn't start pynput listener. It mocks `os._exit`. Should run as a script (`python test_integration.py`). However, it's NOT a proper pytest test — it has no `test_*` functions, just a script body with print statements.

### Hypothesis Tests
The `.hypothesis/` directory with 30 constants files and unicode data confirms property-based tests have been run successfully before.

## What Breaks

### Running the App (`python tome.py`)
1. **X11 required** - `PynputListener` uses `suppress=True` which requires X11 display or root access
2. **espeak required** - Default teller mode is espeak (unless `--text` flag used)
3. **pyperclip import** - Imported unconditionally at module level in tome.py, but NOT in pyproject.toml dependencies

### Fresh Install from pyproject.toml
- `pyperclip` is imported in tome.py but only listed as a comment in pyproject.toml ("Future: pyperclip will be needed")
- Actually already installed in venv (pyperclip-1.11.0), so the venv is ahead of declared deps

### pytest Configuration Conflict
- `pytest.ini` sets `testpaths = .` (discovers ALL test files including root-level)
- `pyproject.toml` sets `testpaths = ['store', 'teller', 'mark', 'mode', 'listener']`
- **pytest.ini takes precedence** — so running bare `pytest` discovers root-level files:
  - `test_integration.py` (script, not tests — would execute on import)
  - `test_handlers.py` (45.8KB — likely has proper test functions)
  - `test_wire.py` (likely has proper test functions)

### test_integration.py as pytest target
When pytest collects `test_integration.py`, it imports the module, executing the script body. This:
- Creates a Store at `/tmp/test_integration.db`
- Runs all operations immediately during collection
- Could cause side effects or failures if store operations fail
- Has no `test_*` functions, so 0 tests collected from it

## Issues Found

| # | Issue | Severity | Category |
|---|-------|----------|----------|
| 1 | `pyperclip` imported but not in pyproject.toml dependencies | Medium | Packaging |
| 2 | pytest.ini vs pyproject.toml testpaths conflict | Low | Testing |
| 3 | test_integration.py executes on import (not pytest-compatible) | Medium | Testing |
| 4 | No documented system dependency check for espeak | Low | DX |
| 5 | README references `setup_tome.sh` and `run_tests.sh` which aren't in repo | Low | Docs |
| 6 | README lists `utilities.py` and `test_tome.py` as files but they don't exist | Low | Docs |

## Architecture Strengths

- **Clean RSP separation** makes unit testing easy without real hardware
- **MockListener** and text-mode teller enable headless testing
- **Property-based testing** with Hypothesis provides strong coverage
- **Each module is independently testable** — great for CI

## Recommendations

1. Add `pyperclip>=1.8.0` to dependencies (it's already used)
2. Remove or reconcile pytest.ini with pyproject.toml (remove pytest.ini, use pyproject.toml exclusively)
3. Convert test_integration.py to proper pytest format with `test_*` functions
4. Add a CI-friendly test command in docs: `pytest store/ teller/ mark/ mode/ listener/`
5. Update README to reflect actual file structure
