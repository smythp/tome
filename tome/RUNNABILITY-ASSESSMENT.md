# Tome Runnability Assessment

**Date:** 2026-05-02  
**Method:** Static analysis of source code, dependencies, and configuration

## Executive Summary

Tome is a well-architected keyboard-driven hierarchical data storage system with an audio-only interface. The RSP (Reusable Software Primitive) decomposition is clean and thoughtful. However, there are several runnability issues that would trip up a new developer or agent trying to build and run the project.

**Verdict:** The individual RSP modules are likely importable and testable. The top-level `tome.py` has a missing dependency that will break on import. Test configuration has a conflict that could cause confusion.

---

## Architecture Overview

Tome consists of 5 RSP modules wired together by `tome.py`:

| Module | Role | Key Design |
|--------|------|------------|
| **Store** | Hierarchical data storage over SQLite | Self-initializing schema, soft delete, dict_factory rows |
| **Mark** | Navigation position tracking | Protocol-based Store dependency, stack history, breadcrumb paths |
| **Mode** | Modal state machine | Routes KeyEvents to handlers, per-mode isolated state, enter/exit hooks |
| **Listener** | Keyboard input abstraction | Wraps pynput, normalized KeyEvent dataclass, MockListener for testing |
| **Teller** | Pluggable TTS output | BaseHandler ABC, auto-discovery from handlers/ directory |

The architecture is clean:
- Each module defines Protocol interfaces for its dependencies (no circular imports)
- Each module has its own comprehensive test suite (unit, oracle, gremlin, property-based)
- Hypothesis is used extensively for property-based testing
- No global state in RSP modules (Store, Mark, Mode use instance state)

---

## Issues Found

### 1. Missing Dependency: `pyperclip` (BLOCKER for tome.py)

**File:** `tome.py` line ~22  
**Impact:** `tome.py` will fail on import with `ModuleNotFoundError`

```python
import pyperclip  # NOT in pyproject.toml dependencies
```

`pyproject.toml` has a comment acknowledging this:
```toml
# Future: pyperclip will be needed when clipboard functionality is added
# clipboard = ["pyperclip>=1.8.0"]
```

The dependency is commented out but `tome.py` imports it unconditionally. This means `tome.py` cannot be imported or run without manually installing pyperclip.

**Fix:** Either:
- Add `pyperclip>=1.8.0` to `[project.dependencies]`
- Or make the import conditional/lazy in `tome.py`

### 2. Conflicting pytest Configuration (CONFUSION)

**Files:** `pytest.ini` vs `pyproject.toml [tool.pytest.ini_options]`

| Setting | `pytest.ini` | `pyproject.toml` |
|---------|-------------|------------------|
| testpaths | `.` (project root) | `["store", "teller", "mark", "mode", "listener"]` |
| markers | db, ui, keyboard, clipboard, integration | (none) |

`pytest.ini` takes precedence over `pyproject.toml` (per pytest docs). This means:
- Running `pytest` will scan the entire project root, finding root-level test files (`test_handlers.py`, `test_integration.py`, `test_wire.py`) in addition to RSP tests
- The `pyproject.toml` testpaths (RSP-only) are silently ignored
- Root-level tests may have different expectations/dependencies than RSP tests

**Fix:** Decide which is canonical and remove the other. The pyproject.toml setting (RSP modules only) is probably the intended one for regular development.

### 3. System Dependency: `espeak` (SETUP)

**Impact:** TTS won't work without system-level espeak installed  
**Files:** `teller/handlers/espeak.py`, README

The README mentions espeak as a prerequisite but there's no check or graceful fallback at the application level. The teller module handles this reasonably (it has text and debug handlers as alternatives), but `tome.py` defaults to espeak mode.

### 4. README is Stale

- References `utilities.py` and `test_tome.py` which don't exist in the current structure
- Says Python 3.8+ but `pyproject.toml` requires >=3.10
- References `setup_tome.sh` and `run_tests.sh` — not verified if these exist
- Doesn't mention the RSP architecture at all

### 5. Root-Level Legacy Files

Several large files at the project root appear to be legacy/reference:
- `reference.py` (81KB) — likely the original monolithic implementation
- `handlers.py` (42KB) — appears to be pre-RSP handler code  
- `test_handlers.py` (46KB) — tests for the legacy handlers
- `lore.db` (37KB) — a development database

These add confusion about what's current vs. legacy.

---

## What Works Well

1. **RSP module isolation** — Each module is independently importable and testable. Store self-initializes its SQLite schema. Mark uses Protocol for Store dependency. Mode uses Protocols for Teller and KeyEvent.

2. **Test comprehensiveness** — Multiple test strategies per module:
   - Unit tests (`test_store.py`, `test_mark.py`, etc.)
   - Oracle tests (`test_store_oracle.py`, `test_mode_oracle.py`) — model-based verification
   - Gremlin tests (`test_store_gremlin.py`, `test_gremlin_attacks.py`) — adversarial/fuzz testing
   - Property-based tests via Hypothesis

3. **Clean dependency graph** — Protocols prevent circular imports. Each RSP can be understood in isolation.

4. **Defensive coding** — Mark has a 100K iteration guard on path traversal. KeyEvent validates exactly-one-of char/key. Store handles missing schema gracefully.

5. **MockListener for testing** — Listener provides a MockListener class, making integration tests possible without actual keyboard input.

---

## Runnability Verdict

| Component | Importable? | Testable? | Runnable? |
|-----------|------------|-----------|----------|
| store/ | ✅ Yes | ✅ Likely (pure SQLite) | N/A (library) |
| mark/ | ✅ Yes | ✅ Likely (needs Store mock/instance) | N/A (library) |
| mode/ | ✅ Yes | ✅ Likely (needs Protocol implementations) | N/A (library) |
| listener/ | ⚠️ Needs pynput | ✅ Likely (MockListener) | N/A (library) |
| teller/ | ✅ Yes | ✅ Likely (text/debug handlers) | N/A (library) |
| tome.py | ❌ Missing pyperclip | ⚠️ Not directly | ❌ Needs pyperclip + espeak + terminal |

---

## Recommended Fixes (Priority Order)

1. **Add pyperclip to dependencies** or make it a lazy/conditional import in tome.py
2. **Remove pytest.ini** and keep pyproject.toml as the single pytest config source
3. **Update README** to reflect current RSP architecture, correct Python version, and current file structure
4. **Move legacy files** (reference.py, handlers.py, test_handlers.py) to a `legacy/` directory or remove them
5. **Add a Makefile or justfile** with standard targets: `test`, `lint`, `run`
