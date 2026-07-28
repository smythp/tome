# Phase 3: Runnability Assessment (Static Analysis)

**Date:** 2026-05-16
**Method:** Static analysis only (bash execution blocked by approval queues)
**Confidence:** 7/10

## Executive Summary

The Tome project has a solid RSP (Rock-Solid Primitives) architecture with well-isolated submodules, but the integration layer has a **startup blocker** and several rough edges. Submodule test suites are likely healthy and runnable. The application itself cannot start.

## BLOCKER

### 1. pyperclip ImportError crashes startup
- **File:** `tome.py` line 32: `import pyperclip`
- **Problem:** Unconditional top-level import, but pyperclip is NOT in `pyproject.toml` dependencies (commented out as 'future' at line 17-18)
- **Impact:** `python tome.py` crashes immediately with `ModuleNotFoundError`
- **Fix:** Either add pyperclip to dependencies, or make the import conditional/lazy

## Test Infrastructure Issues

### 2. pytest.ini vs pyproject.toml conflict
- `pytest.ini` sets `testpaths = .` (project root)
- `pyproject.toml` sets `testpaths = ["store", "teller", "mark", "mode", "listener"]`
- **pytest.ini takes precedence** (ini files override pyproject.toml)
- This means `pytest` discovers ALL test files including root-level ones
- Not necessarily broken, but the configurations disagree about intent

### 3. test_wire.py and test_integration.py are scripts, not pytest tests
- Both use `print()` statements and manual flow
- Neither contains `test_` functions that pytest would collect
- They work as `python test_wire.py` / `python test_integration.py` but NOT via `pytest`
- test_integration.py monkeypatches `os._exit` at module level (line 13-14) which could affect other tests if pytest imports it

### 4. test_handlers.py imports register_confirm_action
- **VERIFIED:** `register_confirm_action` exists at line 184 of `handlers.py`
- Import should succeed; this 46KB test file with proper pytest fixtures should work

## Documentation Staleness

### 5. README.md references nonexistent files
- `./setup_tome.sh` - does not exist
- `./run_tests.sh` - does not exist
- `utilities.py` - does not exist
- `test_tome.py` - does not exist
- README describes the pre-RSP monolithic architecture
- The project has been significantly refactored but README wasn't updated

### 6. CREATE.sql is documentation-only
- `Store._init_db()` creates the schema programmatically (lines 58-100 of store.py)
- CREATE.sql matches the schema but isn't used at runtime
- Could mislead contributors into thinking it's needed

## Submodule Assessment (Likely Healthy)

### store/ - LIKELY WORKS ✅
- `test_store.py` (756 lines) - proper pytest fixtures, tmp_path, comprehensive CRUD tests
- `test_store_gremlin.py` - adversarial/edge case tests
- `test_store_oracle.py` - property-based tests
- No external dependencies beyond stdlib + pytest + hypothesis
- Store self-initializes schema, uses `:memory:` or tmp_path in tests

### teller/ - LIKELY WORKS ✅
- `test_teller.py`, `test_teller_gremlin.py`, `test_teller_oracle.py`
- Protocol-based design with pluggable handlers
- TextHandler (stdout) and DebugHandler work without system dependencies
- EspeakHandler gracefully degrades if espeak binary missing (logs warning, returns None)
- Auto-discovery system is clean and well-structured

### mark/ - LIKELY WORKS ✅
- `test_mark.py` (40KB) - extensive navigation tests
- `test_gremlin_attacks.py` - adversarial input tests
- Protocol-based Store dependency (easy to mock)
- No external dependencies

### mode/ - LIKELY WORKS ✅
- `test_mode.py`, `test_mode_oracle.py`, `test_mode_syndic.py`
- Protocol-based interfaces for Teller and KeyEvent
- ModeContext dataclass is well-structured
- No external dependencies

### listener/ - WORKS WITH CAVEATS ⚠️
- `test_listener.py` (22KB)
- Imports pynput at module level (IS in dependencies)
- pynput may need X11/display access, could fail in headless CI
- Tests likely mock the pynput layer

## Root-level Tests

### test_handlers.py - LIKELY WORKS ✅
- 46KB, 1362 lines of proper pytest tests
- Uses unittest.mock extensively
- Imports from handlers.py, listener, mode modules
- Well-structured fixtures (mock_store, mock_teller, mock_context)
- Does NOT import pyperclip directly (handlers.py imports it lazily in clipboard_handler)

### test_wire.py - SCRIPT ONLY ⚠️
- 87 lines, runs as standalone script
- Tests RSP wiring: Store → Teller → Mark → Mode → handle events
- No pytest test functions

### test_integration.py - SCRIPT ONLY ⚠️
- 224 lines, comprehensive user session simulation
- Monkeypatches os._exit (dangerous if imported by pytest)
- Tests all mode handlers with real Store data
- No pytest test functions

## Architecture Observations

### Strengths
- Clean RSP module boundaries with Protocol-based interfaces
- Each submodule is independently testable
- Teller handler auto-discovery is elegant
- Store self-initializes (no external schema dependency)
- Comprehensive test coverage per submodule
- Multiple test tiers: unit, gremlin (adversarial), oracle (property-based), syndic

### Concerns
- `handlers.py` (42KB, 1294 lines) is a monolith - all mode handlers in one file
- `reference.py` (81KB) is the old monolith, still in repo but not imported
- pyperclip dependency management is inconsistent
- Integration test scripts aren't collected by pytest
- Multiple pytest versions in .pyc cache (7.4.3, 8.3.3, 9.0.2) suggests version churn

## Environment
- Python 3.12 via pyenv
- .venv exists with pytest installed
- hypothesis installed (used for oracle/property tests)
- pynput installed
- pyperclip NOT installed

## Recommended Fixes (Priority Order)

1. **Fix pyperclip blocker** - Add to dependencies OR make import lazy/conditional
2. **Reconcile pytest config** - Pick one of pytest.ini or pyproject.toml, delete the other
3. **Convert integration scripts** - Add test_ functions or move to a scripts/ directory
4. **Update README** - Reflect current RSP architecture
5. **Guard os._exit monkeypatch** - In test_integration.py, scope it properly
