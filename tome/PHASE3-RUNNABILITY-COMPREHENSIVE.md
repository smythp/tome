# Phase 3: Runnability Assessment - Comprehensive Static Analysis

**Date:** 2025-05-14
**Method:** Static analysis (bash execution unavailable)
**Confidence:** High for blockers, Medium for test predictions

---

## Executive Summary

The tome project has **one hard blocker** preventing `python tome.py` from running: an unconditional `import pyperclip` on line 32 of `tome.py`, where pyperclip is not installed (commented out in pyproject.toml). The five RSP modules (store, teller, mark, mode, listener) are well-isolated and their unit tests should pass independently. Integration tests (test_wire.py, test_integration.py) avoid importing tome.py directly, so they should work.

---

## 1. BLOCKER: pyperclip ImportError

**File:** `tome.py`, line 32
**Issue:** `import pyperclip` is unconditional, but pyperclip is NOT installed
**Evidence:** `pyproject.toml` line 17-18 has it commented out:
```python
# Future: pyperclip will be needed when clipboard functionality is added
# clipboard = ["pyperclip>=1.8.0"]
```
**Impact:** `python tome.py` fails immediately with `ImportError: No module named 'pyperclip'`
**Fix:** Either install pyperclip (`pip install pyperclip`) or make the import conditional/lazy

---

## 2. Test Configuration Conflict

**Files:** `pytest.ini` vs `pyproject.toml [tool.pytest.ini_options]`

| Setting | pytest.ini | pyproject.toml |
|---------|-----------|----------------|
| testpaths | `.` (root) | `["store", "teller", "mark", "mode", "listener"]` |

pytest.ini takes precedence. This means:
- Root-level tests (test_handlers.py, test_integration.py, test_wire.py) ARE discovered
- RSP module tests are also discovered (since `.` includes subdirectories)
- The pyproject.toml config is effectively dead code

**Recommendation:** Remove duplicate config. Keep one source of truth.

---

## 3. RSP Module Assessment (All Should Work)

### store/
- **Imports:** sqlite3, dataclasses, datetime, pathlib, typing (all stdlib)
- **Self-bootstrapping:** `_init_db()` creates schema if table doesn't exist
- **Tests:** test_store.py (26.9KB), test_store_gremlin.py (12.3KB), test_store_oracle.py (11.7KB)
- **Prediction:** ✅ Tests should pass

### teller/
- **Imports:** logging, abc, importlib (all stdlib)
- **Handler discovery:** Auto-discovers handlers from teller/handlers/ directory
- **Handlers:** espeak.py (requires espeak binary), text.py (stdout), debug.py
- **Tests:** test_teller.py (17.1KB), test_teller_gremlin.py (13.0KB), test_teller_oracle.py
- **Prediction:** ✅ Tests should pass (espeak handler may warn if binary not installed, but shouldn't fail tests)

### mark/
- **Imports:** typing only (stdlib)
- **Uses Protocol:** for Store dependency - very clean isolation
- **Tests:** test_mark.py (40.6KB), test_gremlin_attacks.py (16.0KB)
- **Prediction:** ✅ Tests should pass

### mode/
- **Imports:** logging, dataclasses, typing (all stdlib)
- **Uses Protocol:** for Teller and KeyEvent - clean isolation
- **Tests:** test_mode.py (32.3KB), test_mode_oracle.py (15.9KB), test_mode_syndic.py (20.5KB)
- **Prediction:** ✅ Tests should pass

### listener/
- **Imports:** logging, threading, dataclasses, enum, typing (stdlib) + `pynput`
- **pynput:** IS in dependencies, should be installed
- **Tests:** test_listener.py (22.8KB)
- **Prediction:** ✅ Tests should pass (MockListener used for testing, pynput import at module level but tests likely mock it)
- **Note:** pynput requires X11/display for actual keyboard capture - headless environments may have import issues

---

## 4. Root-Level Test Assessment

### test_wire.py (smoke test)
- **Imports:** store, teller, mark, mode, listener, handlers
- **Does NOT import:** tome.py or pyperclip
- **Purpose:** Verifies RSP wiring works (create each, connect, simulate keypresses)
- **Prediction:** ✅ Should work

### test_integration.py (user session simulation)
- **Imports:** store, teller, mark, mode, listener, handlers
- **Does NOT import:** tome.py or pyperclip
- **Mocks os._exit:** to prevent test process from dying
- **Purpose:** Full user session simulation with keypresses
- **Prediction:** ✅ Should work (if pyperclip not transitively imported)

### test_handlers.py (45.8KB)
- **Imports:** handlers.py which imports listener and mode
- **handlers.py does NOT import:** pyperclip (only os, re, webbrowser, listener, mode)
- **Prediction:** ✅ Should mostly work

---

## 5. Documentation Drift

### README.md references non-existent files:
- `./setup_tome.sh` - does not exist in tree
- `./run_tests.sh` - does not exist in tree  
- `test_tome.py` - does not exist (listed under "Files")
- `utilities.py` - does not exist (listed under "Files")

### CLAUDE.md is outdated:
- Says "Run application: `python tome.py`" - this will fail due to pyperclip
- Doesn't mention RSP architecture or the five modules
- Doesn't mention `--text` flag for non-TTS testing

---

## 6. Runtime Requirements (for actual app usage)

| Requirement | Status | Impact |
|-------------|--------|--------|
| Python 3.10+ | Required | `str \| None` syntax used throughout |
| pyperclip | **NOT INSTALLED** | **tome.py won't start** |
| pynput | In dependencies | Keyboard capture |
| espeak binary | System package | TTS output (use `--text` to bypass) |
| X11/Display | System | pynput keyboard capture needs it |
| SQLite3 | Python stdlib | Always available |

---

## 7. Architecture Quality Notes

**Strengths:**
- Clean RSP isolation - each module depends only on stdlib + protocols
- Protocol-based interfaces (no concrete cross-dependencies between RSPs)
- Self-bootstrapping database (Store creates schema if needed)
- Pluggable handler discovery in teller
- MockListener for testing without X11
- Comprehensive test suites with property-based testing (hypothesis)

**Weaknesses:**
- pyperclip import blocks the entire app (should be lazy/conditional)
- Duplicate pytest config (pytest.ini vs pyproject.toml)
- Documentation significantly outdated
- text.py handler at 45.5KB is suspiciously large for a text output handler
- No CI/CD configuration visible

---

## 8. Recommended Actions (Priority Order)

1. **Fix pyperclip import** - Make it conditional or add to dependencies
2. **Consolidate pytest config** - Remove one of pytest.ini / pyproject.toml
3. **Update README.md** - Remove references to non-existent files
4. **Update CLAUDE.md** - Document RSP architecture and `--text` flag
5. **Investigate text.py size** - 45.5KB for a text handler is unusual
6. **Add CI** - Even a simple `pytest` GitHub Action would catch regressions
