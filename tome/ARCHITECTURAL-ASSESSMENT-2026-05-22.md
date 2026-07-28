# Tome of Lore — Architectural Assessment

**Date**: 2026-05-22  
**Method**: Static analysis (bash execution blocked by approval gates)

## Executive Summary

Tome of Lore is a keyboard-driven, hierarchical data storage/retrieval system with an audio-only (TTS) interface. It's well-architected as 5 RSP (Reusable Software Primitive) modules with clean Protocol-based interfaces and an unusually thorough test suite. The main issues are documentation drift and a dependency declaration gap.

**Verdict**: The core RSP modules are solid. The root-level wiring layer has a few rough edges. Documentation is actively misleading in places.

---

## Architecture

### Module Structure (5 RSPs + Wiring Layer)

| Module | Purpose | Size | Tests |
|--------|---------|------|-------|
| **Store** | SQLite-backed hierarchical data storage | 24.5KB | 3 test files (store, gremlin, oracle) |
| **Teller** | TTS output abstraction (espeak/text/debug) | Multi-file | 3 test files (teller, gremlin, oracle) |
| **Mark** | Navigation state (buffer position, stack) | 4.4KB | 1 test file (40.6KB!) + gremlin |
| **Mode** | Modal state machine, routes KeyEvents | 9.6KB | 3 test files (mode, oracle, syndic) |
| **Listener** | Keyboard input via pynput | 7.5KB | 1 test file (22.8KB) |
| **Wiring** | tome.py + handlers.py (root level) | ~43KB combined | test_integration.py, test_handlers.py, test_wire.py |

### Design Quality

**Strengths:**
- Clean Protocol-based interfaces between modules (Mark.Store protocol, Mode.Teller protocol, Mode.KeyEvent protocol)
- Each RSP is self-contained with its own `__init__.py`, source, and tests
- No circular imports — protocols used for type hints instead of concrete imports
- Proper separation: listener is the ONLY place that imports pynput, teller is the ONLY place that talks to espeak
- Store handles its own schema creation — no external setup required
- Sophisticated test infrastructure: property-based testing (hypothesis), gremlin attack testing, oracle testing

**Weaknesses:**
- handlers.py (42KB, 1294 lines) is a monolithic file at root level — not an RSP, not modularized
- reference.py (81KB) at root — purpose unclear, not imported by anything visible
- `import pyperclip` at module level in tome.py — fails if not installed, but it's not declared in pyproject.toml
- `os._exit(0)` used for quit (in both tome.py and handlers.py) — kills threads but skips cleanup

---

## Runnability Assessment

### Will It Import? (Static Analysis)

| Import | Status | Notes |
|--------|--------|-------|
| `from store import Store` | ✅ Likely OK | stdlib only (sqlite3, dataclasses, pathlib) |
| `from teller import get_handler` | ✅ Likely OK | Multi-file but self-contained |
| `from mark import Mark` | ✅ Likely OK | stdlib only (typing) |
| `from mode import Mode, ModeContext` | ✅ Likely OK | stdlib only (logging, dataclasses, typing) |
| `from listener import PynputListener` | ⚠️ Depends | Requires pynput — installed in .venv ✅ |
| `import pyperclip` | ⚠️ Undeclared | Installed in .venv ✅ but NOT in pyproject.toml ❌ |

### Will It Run?

- **RSP modules individually**: Almost certainly yes. Clean stdlib dependencies, well-tested.
- **Full application (tome.py)**: Requires a display server (pynput needs X11/Wayland) and espeak installed. Won't run headless.
- **Tests**: Should work. test_integration.py mocks `os._exit` and uses text teller. RSP tests use hypothesis extensively.

### Dependency Declaration Gap

```toml
# pyproject.toml declares:
dependencies = ["pynput>=1.7.0"]

# But tome.py also needs:
import pyperclip  # NOT DECLARED — commented as "Future" in pyproject.toml
```

This means `pip install .` or `uv sync` won't install pyperclip, and `import pyperclip` in tome.py will fail on a fresh install. The dependency IS installed in the current .venv, so it works locally.

### Config Conflict: pytest.ini vs pyproject.toml

```ini
# pytest.ini (takes precedence)
testpaths = .

# pyproject.toml
testpaths = ["store", "teller", "mark", "mode", "listener"]
```

pytest.ini wins (pytest config precedence). This means `pytest` runs ALL test files including root-level test_handlers.py, test_integration.py, and test_wire.py. The pyproject.toml config is effectively dead code.

---

## Documentation Assessment

### README.md — Stale

References files that don't exist:
- `utilities.py` — doesn't exist
- `test_tome.py` — doesn't exist  
- `setup_tome.sh` — doesn't exist
- `run_tests.sh` — doesn't exist

Doesn't mention the RSP module structure at all. Still describes the pre-RSP monolithic architecture.

### CLAUDE.md — Actively Misleading

Describes patterns from a previous version that no longer apply:
- "Use `global` keyword when modifying module-level variables" — RSP modules use clean OOP with no global state
- "When adding new modes, update the mode_map dictionary" — there's no mode_map; Mode uses register()
- "Uses global variables for application state" — false for RSP modules; only partially true for handlers.py

An agent following CLAUDE.md guidance would write code that doesn't match the actual architecture.

### ARCHITECTURE.md / ARCHITECTURE_MAP.md — Exist but not checked in detail

These 11-16KB files exist at root and likely have better architectural documentation, but I didn't verify their accuracy.

---

## Agent Iterability Assessment

### Evidence of Repeated Agent Work

The `tome/` directory contains **23 assessment files** from previous agents:
- Multiple PHASE3-RUNNABILITY-* files (7 variants)
- Multiple PHASE4-AGENT-ITERABILITY-* files (4 variants)
- Multiple FINDING-* files
- COMPREHENSIVE-STATIC-ASSESSMENT.md

Plus 2 more in `projects/tome-of-lore/`. This strongly suggests agents keep re-analyzing the same things without the findings being integrated back into the project.

### Key Barriers to Agent Productivity

1. **CLAUDE.md is wrong** — agents following it will produce code that doesn't fit the architecture
2. **README is wrong** — agents will look for files that don't exist
3. **pytest config conflict** — agents may get confused about which tests to run
4. **No entry point documentation** — no clear "start here" for understanding the RSP architecture
5. **handlers.py is a black hole** — 42KB monolith that an agent needs to understand to work on modes, but it's not structured as an RSP

### Recommendations

1. **Fix CLAUDE.md** to describe actual RSP architecture, not the old global-state approach
2. **Fix README.md** to remove nonexistent file references and describe the RSP module structure
3. **Add pyperclip to pyproject.toml dependencies** or remove the import from tome.py
4. **Resolve pytest.ini vs pyproject.toml conflict** — pick one source of truth
5. **Consider splitting handlers.py** into per-mode handler files (or at least document its structure)
6. **Clean up tome/ directory** — 23 assessment files add noise; consolidate or move to an archive

---

## Test Infrastructure (Notable)

The test suite is genuinely impressive for a personal project:

- **Property-based testing** with hypothesis across all RSP modules
- **Gremlin attack testing** (store, mark, teller) — fuzzing-style adversarial tests
- **Oracle testing** (store, mode, teller) — reference implementation comparison
- **Syndic testing** (mode) — unclear what this tests specifically
- **Cross-version testing** — .pyc files show tests run against pytest 7.4.3, 8.3.3, and 9.0.2
- **Integration test** — test_integration.py simulates a full user session with mocked exit

Total test code: ~300KB+ across 15 test files. Test-to-source ratio is very high.

---

## Files Examined

- tome.py, handlers.py (first 60 lines), pyproject.toml, pytest.ini, CLAUDE.md, README.md
- store/store.py (first 80 lines), mark/mark.py, mode/mode.py (first 80 lines), listener/listener.py (first 80 lines)
- CREATE.sql, docs/roadmap.md, test_integration.py (full)
- .venv/lib/python3.12/site-packages/ (package listing)
- Full directory tree
