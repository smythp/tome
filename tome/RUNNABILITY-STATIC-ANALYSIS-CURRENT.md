# Tome of Lore - Static Runnability Assessment

## Executive Summary

**Verdict: Will not start.** The application has a blocking import error (`pyperclip`) at module level that prevents startup. The test suite is likely runnable for the RSP modules but has a config conflict between `pytest.ini` and `pyproject.toml`. The underlying architecture is clean and well-structured.

## Critical Issues

### 1. pyperclip ImportError (BLOCKER)
- **File**: `tome.py`, line 32
- **Problem**: `import pyperclip` at module level, but pyperclip is NOT in `pyproject.toml` dependencies
- **Evidence**: pyproject.toml line 17 explicitly comments it out: `# Future: pyperclip will be needed when clipboard functionality is added`
- **Impact**: `python tome.py` will crash immediately with `ModuleNotFoundError: No module named 'pyperclip'`
- **Fix**: Either add `pyperclip>=1.8.0` to dependencies, or gate the import behind a try/except or move it to the clipboard handler

### 2. pytest.ini vs pyproject.toml testpaths conflict
- **pytest.ini**: `testpaths = .` (searches entire project)
- **pyproject.toml**: `testpaths = ["store", "teller", "mark", "mode", "listener"]` (only RSP dirs)
- **Impact**: pytest.ini takes precedence (it's loaded first), so `pytest` runs ALL test files including root-level `test_handlers.py`, `test_integration.py`, `test_wire.py`. pyproject.toml's testpaths are ignored.
- **Risk**: Root-level tests may import `tome.py` which triggers the pyperclip ImportError, potentially cascading test failures
- **Fix**: Remove pytest.ini or align the two configs

### 3. README is stale
- Says Python 3.8+ but pyproject.toml requires >=3.10 (and code uses 3.10+ syntax like `str | None`)
- References `setup_tome.sh` - file does not exist in project
- References `run_tests.sh` - file does not exist
- References `utilities.py` - file does not exist
- References `test_tome.py` - file does not exist
- The actual project structure has evolved significantly beyond what README describes

## Environment Assessment

- **Python**: 3.12.0 via pyenv (venv exists at `.venv/`)
- **espeak**: Installed at `/usr/bin/espeak`
- **pynput**: Listed as dependency, likely installed (couldn't verify - bash approval pending)
- **pyperclip**: Almost certainly NOT installed (not in any dependency list)
- **uv.lock**: Present (35KB), suggesting uv was used for dependency management

## Architecture Assessment

The codebase follows a clean RSP (Reusable Software Primitive) design:

| RSP | Purpose | Quality |
|-----|---------|--------|
| **Store** (`store/store.py`, 736 lines) | SQLite-backed hierarchical data storage | Solid - proper schema init, dict_factory, soft delete |
| **Teller** (`teller/`) | TTS output with pluggable handlers | Clean - auto-discovery, BaseHandler ABC, espeak/text/debug backends |
| **Mark** (`mark/mark.py`, 162 lines) | Navigation state (buffer position, stack) | Clean - proper validation, cycle detection in path traversal |
| **Mode** (`mode/mode.py`, 287 lines) | Modal state machine with per-mode state | Well-designed - protocols, on-enter/exit hooks, isolated state |
| **Listener** (`listener/listener.py`, 243 lines) | Keyboard input via pynput | Good - normalized KeyEvents, MockListener for testing |
| **Handlers** (`handlers.py`, 1294 lines) | Mode-specific logic | Large but functional - all mode behaviors in one file |

### Design Strengths
- Each RSP is independently testable with clean interfaces
- Protocol-based typing avoids circular imports
- MockListener enables keyboard testing without pynput/display
- Handler discovery is automatic (drop a .py file in handlers/)
- Mark has cycle detection (100K iteration guard)

### Design Concerns
- `handlers.py` at 1294 lines is a monolith - could be split per mode
- `tome.py` uses `os._exit(0)` for shutdown (kills threads but bypasses cleanup)
- Global quit handler ('q' always exits) is hardcoded in `tome.py._on_key`
- pynput requires X11/Wayland display server - no headless mode for the listener

## Test Suite Assessment

Extensive test coverage with multiple testing strategies:

| Test Category | Files | Purpose |
|--------------|-------|--------|
| **Regular** (`test_*.py`) | 5 files (~140KB total) | Standard unit/integration tests |
| **Oracle** (`test_*_oracle.py`) | 3 files | Property-based oracle testing |
| **Gremlin** (`test_*_gremlin.py`) | 3 files | Fuzzing/chaos testing |
| **Syndic** (`test_mode_syndic.py`) | 1 file | Cross-component syndication tests |

- Uses Hypothesis for property-based testing (`.hypothesis/` dir with 30 cached constants)
- pytest markers defined: db, ui, keyboard, clipboard, integration
- Root-level test files: `test_handlers.py`, `test_integration.py`, `test_wire.py`
- Could not run tests (bash approval pending) but static analysis suggests RSP-level tests should pass if pyperclip issue doesn't cascade

## Recommendations (Priority Order)

1. **Fix pyperclip import** - Either add to deps or lazy-import it. This is the only thing preventing startup.
2. **Resolve pytest config conflict** - Delete pytest.ini and let pyproject.toml be the single source of truth.
3. **Update README** - Reflect actual project structure, correct Python version, remove references to nonexistent files.
4. **Consider splitting handlers.py** - 1294 lines is manageable but would benefit from per-mode files.
5. **Add CI configuration** - The test suite is sophisticated enough to warrant automated runs.

## What I Could Not Verify

- Whether tests actually pass (bash commands for running Python were awaiting approval)
- Whether pyperclip is installed in the venv despite not being in pyproject.toml
- Whether pynput is installed and functional
- Runtime behavior of the application
- Database state in `lore.db`
