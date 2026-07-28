# Tome of Lore: Runnability Assessment (Static Analysis)

**Date**: 2026-05-29
**Method**: Static code analysis (no execution — bash commands awaited approval that never came)
**Confidence**: 7/10

---

## Executive Summary

The RSP (Reusable Software Primitive) modules are well-structured and their unit tests would likely pass. The main application (`tome.py`) has a hard blocker: it imports `pyperclip` at module level, but pyperclip is not installed and not in `pyproject.toml` dependencies. This means `python tome.py` crashes immediately with `ImportError`.

---

## What Would Work

### Unit Tests (HIGH confidence: 8/10)

The per-module test suites should pass:

- **store/test_store.py** (26.9KB) — Pure SQLite with temp DBs, no external deps
- **mark/test_mark.py** (40.6KB) — Pure Python, uses Protocol-based mocks
- **mode/test_mode.py** (32.3KB) — Pure Python, uses Protocols
- **teller/test_teller.py** (17.1KB) — Auto-discovers handlers, text handler works without espeak
- **listener/test_listener.py** (22.8KB) — Has MockListener; real PynputListener tests may need display server

Property-based testing (Hypothesis) is set up with existing `.hypothesis/` data:
- store/test_store_gremlin.py, test_store_oracle.py
- mark/test_gremlin_attacks.py
- mode/test_mode_oracle.py, test_mode_syndic.py
- teller/test_teller_gremlin.py, test_teller_oracle.py

### Integration Test (MEDIUM confidence: 6/10)

`test_integration.py` exercises the full stack with text teller and mocked `os._exit`. It doesn't import `tome.py` directly (imports individual RSPs + handlers), so it avoids the pyperclip blocker. The `from listener import ...` line imports pynput at module level — this may fail in headless environments.

### RSP Architecture

The modular design is solid:
- Each RSP (Store, Teller, Mark, Mode, Listener) is independent
- Protocol-based dependency injection throughout
- Clean separation of concerns
- No circular imports between RSPs

---

## What Would Break

### 1. BLOCKER: `import pyperclip` in tome.py (line 32)

```python
# External
import pyperclip  # <-- CRASHES: not installed, not in pyproject.toml
```

**Impact**: `python tome.py` fails immediately with `ImportError`.
**Fix**: Either install pyperclip and add to dependencies, or make the import conditional.

Note: pyperclip is explicitly commented out in pyproject.toml:
```toml
# Future: pyperclip will be needed when clipboard functionality is added
# clipboard = ["pyperclip>=1.8.0"]
```

### 2. pynput requires display server

`listener/listener.py` line 14: `from pynput import keyboard` — this fails in headless/SSH sessions without X11/Wayland. Affects:
- Running the app in CI
- Running tests that import from `listener` in headless environments
- The `suppress=True` flag in PynputListener also needs elevated permissions on some systems

### 3. espeak is a system dependency

The default teller mode is 'espeak' (a system binary, not a Python package). Users need either:
- `espeak` installed system-wide, or
- `--text` flag to use text output fallback

### 4. README is severely outdated

References that don't exist:
- `setup_tome.sh` (no such file)
- `run_tests.sh` (no such file)
- `test_tome.py` (tests are now per-module)
- `utilities.py` (no such file)

Doesn't mention:
- RSP architecture
- `pyproject.toml` / `uv` tooling
- Per-module test structure
- `--text` flag

### 5. Database path inconsistency

- `tome.py` defaults to `~/.tome/lore.db` (creates directory)
- `CREATE.sql` and README reference `lore.db` in project root
- A `lore.db` (36.9KB) exists in project root — likely a dev database

### 6. pytest.ini vs pyproject.toml conflict

- `pyproject.toml`: `testpaths = ["store", "teller", "mark", "mode", "listener"]`
- `pytest.ini`: `testpaths = .`
- pytest.ini takes precedence, so root-level tests (test_handlers.py, test_integration.py, test_wire.py) also run
- Probably intentional but undocumented

### 7. Accumulated assessment files in tome/ directory

~30 assessment/finding files from previous agents cluttering the `tome/` directory. These should be cleaned up or archived.

---

## Verdict

| Component | Status | Notes |
|-----------|--------|-------|
| RSP unit tests | ✅ Likely PASS | Well-isolated, proper mocking |
| Property tests | ✅ Likely PASS | Hypothesis data cached |
| Integration test | ⚠️ Conditional | Depends on pynput import in headless env |
| `python tome.py` | ❌ FAIL | `import pyperclip` — missing dependency |
| App with pyperclip fixed | ⚠️ Conditional | Needs display server for pynput, espeak for TTS |

**Bottom line**: The RSP primitives are well-engineered and testable. The main app entry point has a one-line blocker (`import pyperclip`) that's trivially fixable. The architecture is sound; the wiring layer needs a dependency fix.
