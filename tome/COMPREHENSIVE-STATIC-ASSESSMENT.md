# Comprehensive Tome Codebase Assessment (Static Analysis)

**Date:** 2026-05-15  
**Method:** Static analysis only (bash execution unavailable)  
**Coverage:** All core source files, all configs, full directory tree, dependency inspection

---

## Executive Summary

Tome is a well-architected keyboard-driven hierarchical data store with audio-only interface. The RSP (Reusable Software Primitives) refactoring is genuinely well-done — clean separation of concerns, Protocol-based interfaces, proper dependency injection, and a thoughtful plugin system for TTS handlers.

The codebase is **mature and actively maintained** (3 pytest version generations, 30 Hypothesis constant files, extensive test suites with gremlin/oracle/syndic testing patterns). However, it has accumulated technical debt in documentation and project hygiene.

**Verdict: Solid architecture, minor hygiene issues, one real bug.**

---

## 1. Architecture Assessment

### 1.1 RSP Primitive Design (Excellent)

Five clean primitives with well-defined boundaries:

| Primitive | Lines | Responsibility | Interface |
|-----------|-------|---------------|----------|
| **store** | 736 | SQLite hierarchical data storage | `Store` class, `Entry` type |
| **teller** | ~300 | Pluggable TTS/text output | `BaseHandler` Protocol, plugin discovery |
| **mark** | 161 | Navigation position + stack history | `Mark` class with `Store` Protocol |
| **mode** | 287 | Modal state machine + key routing | `Mode` class, `ModeContext` DI container |
| **listener** | 242 | Keyboard input (pynput wrapper) | `KeyEvent` frozen dataclass, `Listener` Protocol |

**Strengths:**
- Protocol-based interfaces everywhere — excellent for testability
- `listener` is the ONLY pynput consumer (single import boundary)
- `ModeContext` provides clean dependency injection to handlers
- `teller` has genuine plugin discovery (drop .py in handlers/ directory)
- `KeyEvent` is a frozen dataclass with validation in `__post_init__`
- `MockListener` available for testing without display/pynput
- Each primitive has its own test suite

**Concern:**
- `handlers.py` (1294 lines, 42KB) is the one monolith remaining — all mode handlers in a single file. This is the natural next refactoring target (split into per-mode handler files).

### 1.2 Wiring Layer (tome.py — Good)

Clean 202-line orchestrator that:
- Instantiates all RSPs
- Registers mode handlers (lazy import from handlers.py)
- Routes KeyEvents through Mode
- Handles privileged quit (os._exit)
- Tracks consecutive key repeats

The `_switch_with_reset` monkey-patch on `self.mode.switch` is slightly inelegant but functional. A callback/hook system would be cleaner.

### 1.3 Data Flow

```
Keyboard → PynputListener → KeyEvent → App._on_key → Mode.handle → handler(event, ModeContext)
                                                                         ↓
                                                          Store/Mark/Teller via ModeContext
```

Clean unidirectional flow. No circular dependencies. No global state in primitives (tome.py has `App` instance state, handlers use `ModeContext`).

---

## 2. Bugs and Issues

### 2.1 REAL BUG: Undeclared pyperclip Dependency

**Severity: Medium** (works now, breaks on fresh install)

`tome.py` line 32:
```python
import pyperclip
```

`pyproject.toml` lines 17-18:
```python
# Future: pyperclip will be needed when clipboard functionality is added
# clipboard = ["pyperclip>=1.8.0"]
```

pyperclip IS installed in the venv (1.11.0 in site-packages), so it works currently. But it's not declared as a dependency — a fresh `pip install` or `uv sync` would fail to install it, and `import tome` would crash with `ModuleNotFoundError`.

**Fix:** Either add `pyperclip>=1.8.0` to `dependencies` in pyproject.toml, or remove the import from tome.py (it may only be used in handlers.py's clipboard mode).

### 2.2 pytest Configuration Conflict

**Severity: Low** (confusing but probably intentional)

- `pytest.ini`: `testpaths = .` (discovers ALL test files including root-level)
- `pyproject.toml`: `testpaths = ["store", "teller", "mark", "mode", "listener"]` (only primitive tests)

pytest.ini takes precedence, so root-level tests (`test_handlers.py`, `test_integration.py`, `test_wire.py`) ARE discovered. This is probably intentional but the contradiction is confusing. Pick one config location.

### 2.3 os._exit(0) in Two Places

**Severity: Info** (intentional but worth noting)

- `tome.py` line 103: In `_on_key` when 'q' is pressed
- `handlers.py` line 23: In `quit_app` helper

Both are justified — pynput runs daemon threads that `sys.exit()` can't kill. But it means no cleanup code after `os._exit` runs (atexit handlers, context managers, etc.). The `shutdown()` call before `os._exit` in tome.py mitigates this.

---

## 3. Documentation Issues

### 3.1 README.md is Stale

**References 4 non-existent files:**
- `utilities.py` — doesn't exist
- `test_tome.py` — doesn't exist (tests are in primitive directories)
- `setup_tome.sh` — doesn't exist
- `run_tests.sh` — doesn't exist

**Version mismatch:**
- README says "Python 3.8+"
- pyproject.toml says `requires-python = ">=3.10"`
- Code uses `str | None` syntax (Python 3.10+)

### 3.2 CLAUDE.md is Minimal but Accurate

Covers the basics (commands, code style, structure) but doesn't mention:
- The RSP architecture
- The 5 primitives and their boundaries
- How to run tests (`pytest` or `.venv/bin/pytest`)
- The --text flag for non-audio testing
- How handler plugins work

### 3.3 Assessment Proliferation

12+ assessment files in `tome/` directory and root:
- `RUNNABILITY_ASSESSMENT.md`, `RUNNABILITY_FINDINGS.md`
- `phase3-runnability-findings.md`, `phase4-agent-iterability-findings.md`
- `ARCHITECTURE.md`, `ARCHITECTURE_MAP.md`
- Multiple `PHASE3-*`, `PHASE4-*`, `FINDING-*` files in `tome/`
- `tome_improvement_brief.md`

These represent prior agent assessments that haven't been consolidated or cleaned up. They add noise and suggest the assessment cycle has been somewhat repetitive.

---

## 4. Test Infrastructure

### 4.1 Test Coverage (Excellent)

| Primitive | Test Files | Notable Patterns |
|-----------|-----------|------------------|
| store | test_store.py (27KB), test_store_gremlin.py (12KB), test_store_oracle.py (12KB) | Gremlin attacks, oracle contracts |
| teller | test_teller.py (17KB), test_teller_gremlin.py (13KB), test_teller_oracle.py | Gremlin + oracle |
| mark | test_mark.py (41KB), test_gremlin_attacks.py (16KB) | Largest test suite, gremlin attacks |
| mode | test_mode.py (32KB), test_mode_oracle.py (16KB), test_mode_syndic.py (21KB) | Oracle + syndic patterns |
| listener | test_listener.py (23KB) | Standard tests |
| root | test_handlers.py (46KB), test_integration.py (6KB), test_wire.py (2KB) | Integration + wiring |

**Total test code: ~280KB** — substantially more test code than production code (~85KB). This is a well-tested project.

### 4.2 Testing Patterns

- **Hypothesis property-based testing** with 30 constant files — tests have been extensively exercised
- **Gremlin attacks**: Adversarial inputs (mark, store, teller)
- **Oracle tests**: Contract verification against expected behaviors
- **Syndic tests**: Additional mode coverage
- **MockListener**: Enables testing without X11/display
- **3 pytest versions** in pyc files (7.4.3 → 8.3.3 → 9.0.2) — actively maintained

### 4.3 Could Not Verify

Bash execution was unavailable, so I could NOT run:
- `pytest` to verify test pass/fail status
- Import checks to verify all modules load correctly
- Runtime behavior verification
- espeak availability check

---

## 5. Dependencies

### 5.1 Declared vs Installed

| Package | pyproject.toml | Installed | Status |
|---------|---------------|-----------|--------|
| pynput | >=1.7.0 (required) | 1.8.1 | ✅ |
| pytest | >=7.0.0 (dev) | 9.0.2 | ✅ |
| hypothesis | >=6.0.0 (dev) | 6.152.1 | ✅ |
| pyperclip | commented out | 1.11.0 | ⚠️ Installed but not declared |

### 5.2 Runtime Requirements

- **Python 3.12.0** via pyenv (declared >=3.10)
- **X11/display** for pynput keyboard listening (headless will fail)
- **espeak** binary for default TTS handler
- **SQLite3** for data storage (bundled with Python)

---

## 6. Agent Iterability Assessment

### 6.1 Strengths for Agent Work

1. **Clean module boundaries** — each primitive can be worked on independently
2. **Protocol interfaces** — easy to mock, test, and swap implementations
3. **--text flag** — `python tome.py --text` avoids needing espeak
4. **MockListener** — tests don't need X11/display
5. **Comprehensive test suite** — changes can be verified
6. **CLAUDE.md exists** — basic guidance available

### 6.2 Friction Points for Agents

1. **Can't run in headless** — listener.py imports pynput at module level, which may fail without display
2. **Stale README** — misleading file references
3. **handlers.py monolith** — 1294 lines is a lot to work with in one file
4. **Assessment clutter** — 12+ prior assessment files create noise
5. **Dual pytest config** — confusing which tests are "supposed" to run
6. **No CI** — no automated test runs, no pre-commit hooks
7. **pyperclip import** — may cause import failure in clean environments

### 6.3 Recommended Next Steps

1. **Fix pyperclip**: Add to dependencies or make import conditional
2. **Consolidate pytest config**: Pick pytest.ini OR pyproject.toml, delete the other
3. **Update README**: Fix file references, update Python version
4. **Enhance CLAUDE.md**: Add RSP architecture overview, test commands, handler plugin docs
5. **Clean up assessments**: Consolidate or remove the 12+ assessment files
6. **Split handlers.py**: One handler file per mode (read_handler.py, options_handler.py, etc.)
7. **Add conditional pynput import**: Allow import in headless environments for testing

---

## 7. File Inventory

### Production Code (~85KB)
- `tome.py` (6KB) — main wiring
- `handlers.py` (42KB) — mode handlers
- `store/store.py` (25KB) — data storage
- `mode/mode.py` (10KB) — modal state machine
- `listener/listener.py` (8KB) — keyboard input
- `mark/mark.py` (4KB) — navigation state
- `teller/` (~8KB total) — TTS with plugin discovery

### Test Code (~280KB)
- See Section 4.1 for breakdown

### Legacy
- `reference.py` (81KB) — original monolithic implementation

### Meta/Docs
- `CLAUDE.md`, `README.md`, `ARCHITECTURE.md`, `ARCHITECTURE_MAP.md`
- 12+ assessment files in `tome/` and root
- `docs/` with roadmap, ideas, agentic-testing notes
