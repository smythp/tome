# Phase 3: Runnability Assessment (Static Analysis)

**Date**: 2026-05-18
**Method**: Static analysis only (Python execution not approved)
**Assessor**: Technical architect agent

## Executive Summary

The Tome of Lore project has **partial runnability** — its core modules are well-structured and testable in isolation, but the top-level application (`tome.py`) has an undeclared dependency that would cause a fresh install to fail immediately. Test configuration has a conflict that changes test discovery behavior depending on which config file takes precedence.

## Verdict: CONDITIONAL PASS

The project will run correctly in its *current* venv (all deps are installed). A fresh `pip install` from pyproject.toml would fail on `import pyperclip` in tome.py.

---

## Findings

### 1. Shadow Dependency: pyperclip (CRITICAL)

**Impact**: Fresh install fails immediately on `python tome.py`

- `pyperclip` is imported in 4 files: `tome.py`, `handlers.py`, `reference.py`, `test_handlers.py`
- It is NOT declared in `pyproject.toml` dependencies (commented out as "Future")
- It IS installed in the current `.venv` (pyperclip-1.11.0)
- This means the project works locally but fails on any fresh clone + install

**Fix**: Add `"pyperclip>=1.8.0"` to the `[project.dependencies]` list in pyproject.toml.

### 2. Test Configuration Conflict (MODERATE)

**Impact**: Test discovery differs depending on which config is used

- `pytest.ini` says `testpaths = .` (scan everything)
- `pyproject.toml` says `testpaths = ["store", "teller", "mark", "mode", "listener"]` (module dirs only)
- **pytest.ini wins** (it takes precedence over pyproject.toml)
- Result: Running `pytest` discovers ALL test files including root-level `test_handlers.py`, `test_integration.py`, `test_wire.py`
- The pyproject.toml config would miss these root-level tests

**Fix**: Remove pytest.ini (let pyproject.toml be authoritative) OR update pyproject.toml testpaths to include `.` and remove pytest.ini.

### 3. Undeclared System Dependency: espeak (MODERATE)

**Impact**: Default teller mode fails without espeak installed

- `tome.py` defaults to `teller_mode="espeak"` 
- espeak is a system binary, not a Python package
- No documentation of this requirement in README or pyproject.toml
- The `--text` flag provides a fallback, but the default path breaks

**Fix**: Document espeak requirement in README. Consider making text mode the default with espeak as opt-in.

### 4. test_integration.py is Not a Pytest Test (LOW)

**Impact**: Integration test must be run manually, not via `pytest`

- Uses `print()` statements and manual assertions
- Monkeypatches `os._exit` at module level (dangerous if collected by pytest)
- Has no `test_` functions — it's a script
- Would be collected by pytest (due to pytest.ini testpaths=.) but wouldn't contribute tests

**Fix**: Either convert to proper pytest test or rename to not match `test_*.py` pattern (e.g., `run_integration.py`).

### 5. Multiple pytest Cache Versions (INFORMATIONAL)

- `__pycache__` dirs contain compiled test files for pytest 7.4.3, 8.3.3, and 9.0.2
- Currently installed: pytest 9.0.2
- Indicates active development over time
- No functional impact, just noise

---

## Module Health Summary

| Module | Has Tests | Test Type | Likely Runnable |
|--------|-----------|-----------|----------------|
| store/ | ✅ test_store.py, test_store_gremlin.py, test_store_oracle.py | pytest + hypothesis | ✅ Yes (pure Python, SQLite) |
| teller/ | ✅ test_teller.py, test_teller_gremlin.py, test_teller_oracle.py | pytest + hypothesis | ⚠️ Partial (espeak tests need binary) |
| mark/ | ✅ test_mark.py, test_gremlin_attacks.py | pytest + hypothesis | ✅ Yes (depends on store) |
| mode/ | ✅ test_mode.py, test_mode_oracle.py, test_mode_syndic.py | pytest + hypothesis | ✅ Yes (depends on teller, store, mark) |
| listener/ | ✅ test_listener.py | pytest + hypothesis | ⚠️ Partial (pynput may need display) |

## What I Could NOT Verify

- Actual pytest execution (bash approval for Python was not granted)
- Import resolution at runtime
- Whether hypothesis tests pass or timeout
- Database initialization behavior
- pynput's behavior without a display server

## Recommendations (Priority Order)

1. **Add pyperclip to dependencies** — one-line fix, eliminates fresh-install failure
2. **Resolve pytest.ini vs pyproject.toml** — pick one source of truth
3. **Document espeak requirement** — or change default teller mode
4. **Rename test_integration.py** — prevent pytest collection issues
5. **Add a CI config** — even a simple GitHub Actions running `pytest` on the module dirs
