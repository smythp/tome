# Phase 4: Agent Iterability Assessment — Feedback Loops & Developer Experience

**Date:** 2026-05-31
**Method:** Independent static analysis of codebase structure, configuration, tests, and documentation

## Executive Summary

**Verdict: PARTIALLY ITERABLE — strong test foundation, but missing lint/CI/docs creates unnecessary friction**

The codebase has a surprisingly robust testing infrastructure (multi-tier pytest with Hypothesis, MockListener for headless testing, text teller mode). An agent CAN iterate — but will waste significant cycles on stale docs, missing dependencies, and the absence of lint/type-checking feedback.

---

## 1. Feedback Loops That Exist

### 1.1 Testing (STRONG)

**Multi-tier test suite with co-located tests:**
- `store/test_store.py` (26.9KB) — unit tests
- `store/test_store_gremlin.py` (12.3KB) — chaos/fuzz testing
- `store/test_store_oracle.py` (11.7KB) — invariant/property testing
- Same pattern for `teller/`, `mode/`, `mark/`, `listener/`
- `test_integration.py` — full smoke test wiring all 5 primitives
- `test_handlers.py` (45.8KB) — handler-level tests

**Testing tiers:**
| Tier | Purpose | Files | Approach |
|------|---------|-------|----------|
| Unit | Core behavior | `test_*.py` | Standard pytest |
| Gremlin | Chaos/fuzz | `test_*_gremlin.py` | Hypothesis property-based |
| Oracle | Invariants | `test_*_oracle.py` | Hypothesis stateful testing |
| Syndic | Cross-primitive | `test_mode_syndic.py` | Integration contracts |
| Integration | End-to-end | `test_integration.py` | Full app simulation |

**pytest markers** (defined in `pytest.ini`):
- `db` — database interaction tests
- `ui` — user interface tests
- `keyboard` — keyboard interaction tests
- `clipboard` — clipboard operation tests
- `integration` — integration tests

**Hypothesis integration:**
- 30 constant files in `.hypothesis/` directory
- Property-based testing for Store, Teller, Mark, Mode, Listener
- Stateful testing for oracle tests

**Headless testing support:**
- `MockListener` — simulates keyboard input without pynput/display
- `text` teller handler — avoids espeak binary dependency
- `test_integration.py` demonstrates full headless operation

**Agent can run tests with:**
```bash
.venv/bin/pytest store/ teller/ mark/ mode/ listener/  # Unit tests by package
.venv/bin/pytest -k gremlin  # Chaos tests only
.venv/bin/pytest -k oracle  # Invariant tests only
.venv/bin/pytest test_integration.py  # Smoke test
```

### 1.2 Git Version Control (BASIC)
- Git repository with history
- No CI/CD pipeline
- No pre-commit hooks
- No branch protection or automated checks

---

## 2. Feedback Loops That Are MISSING

### 2.1 No Linting (CRITICAL GAP)
- No ruff, flake8, pylint, or any linter configured
- No `.flake8`, `ruff.toml`, `.ruff.toml`, `setup.cfg`, `tox.ini` found
- No pre-commit hooks (`.pre-commit-config.yaml` absent)
- **Impact:** Agent gets zero style/quality feedback. Can introduce antipatterns silently.

### 2.2 No Type Checking (SIGNIFICANT GAP)
- No mypy configuration (`.mypy.ini`, `mypy.ini` absent)
- Code uses `Any` extensively (mode.py types Store/Mark as `Any` to avoid circular imports)
- Protocol types exist (good!) but aren't verified by any checker
- **Impact:** Agent can break interfaces without knowing until runtime.

### 2.3 No Task Runner / Makefile (MODERATE GAP)
- No Makefile, no `scripts` in pyproject.toml, no task runner
- Agent must discover commands by reading docs (which are stale)
- **Impact:** Agent wastes time figuring out how to run things.

### 2.4 No CI/CD Pipeline (MODERATE GAP)
- No `.github/` directory
- No automated test runs on commit
- Tests only run when explicitly invoked
- **Impact:** Regressions can accumulate silently.

---

## 3. Agent Iterability Blockers

### 3.1 Stale Documentation (CRITICAL)

**ARCHITECTURE.md** describes a completely different system:
- References Flask web server, RSP protocol, embeddings pipeline
- None of this exists in the codebase
- An agent reading this first would build entirely wrong mental model

**CLAUDE.md** references stale patterns:
- "Use global keyword when modifying module-level variables" — codebase uses classes now
- "Update the mode_map dictionary" — mode_map doesn't exist; Mode uses register()
- "Uses global variables for application state" — App class exists
- Only accurate parts: indentation (4 spaces), snake_case naming, SQLite usage

### 3.2 Missing pyperclip Dependency (CRITICAL)
- `tome.py` line 32: `import pyperclip` (top-level, unconditional)
- `pyproject.toml`: pyperclip is commented out, not in dependencies
- `.venv` likely lacks pyperclip
- **Impact:** `import tome` or `from tome import App` crashes immediately
- Note: `test_integration.py` works by importing primitives directly, bypassing tome.py

### 3.3 Conflicting pytest Configuration (MODERATE)
- `pytest.ini`: `testpaths = .` (searches everything)
- `pyproject.toml`: `testpaths = ["store", "teller", "mark", "mode", "listener"]`
- pytest.ini takes precedence (ini > pyproject.toml)
- With `testpaths = .`, pytest also discovers tests in `__pycache__/`, `tome/`, etc.
- Agents may get different test counts depending on which config they think is active

### 3.4 Import-Time Side Effects (MODERATE)
- `teller/__init__.py` line 142: `_init_handlers()` runs on `import teller`
- Discovers and instantiates all handlers at import time
- If espeak binary is missing, this may warn/fail unpredictably
- Makes isolated unit testing of teller consumers harder

### 3.5 35+ Stale Assessment Files in `tome/` (LOW-MODERATE)
- Directory contains duplicate/superseded assessments from prior agents:
  - 10 PHASE4-* files, 8 PHASE3-* files, 6 FINDING-* files, etc.
- Creates noise for agents exploring the codebase
- No clear "latest" or "canonical" indicator

### 3.6 handlers.py Monolith (LOW-MODERATE)
- 1,294 lines, 42KB — all 7 mode handlers in one file
- Hard for agents to understand individual handler behavior
- No clear separation between handler concerns

### 3.7 reference.py (81KB) — Unclear Purpose
- Largest Python file in the project
- No clear documentation of what it contains or why
- Agents may waste time trying to understand it

---

## 4. What Works Well for Agents

### 4.1 Clean 5-Primitive Architecture
- `store/`, `teller/`, `mark/`, `mode/`, `listener/` — each isolated
- Each primitive has its own `__init__.py` with clear public API
- Each has co-located tests
- Dependencies flow one way: `tome.py` → primitives

### 4.2 Protocol-Based Loose Coupling
- `mode.py` defines `Teller` and `KeyEvent` as Protocol types
- Primitives don't import each other directly (except through tome.py wiring)
- Easy to test in isolation with mocks

### 4.3 MockListener for Headless Testing
- `listener/listener.py` provides `MockListener`
- `test_integration.py` demonstrates full headless testing pattern
- Agent can run all tests without a display or keyboard

### 4.4 Text Teller Mode
- `teller/handlers/text.py` outputs to stdout instead of espeak
- `--text` flag on `tome.py` enables it
- Tests use `get_handler("text")` for silent operation

### 4.5 Hypothesis Integration
- Property-based and stateful testing built in
- Gremlin tests catch edge cases agents might miss
- Oracle tests verify invariants hold across state transitions

---

## 5. Recommendations (Priority Order)

### P0 — Fix Before Agent Iteration
1. **Fix pyperclip dependency** — Either add to dependencies or make import conditional
2. **Delete or rewrite ARCHITECTURE.md** — It describes a different system entirely
3. **Update CLAUDE.md** — Replace stale patterns with current architecture
4. **Resolve pytest.ini vs pyproject.toml conflict** — Pick one source of truth

### P1 — Add Missing Feedback Loops
5. **Add ruff configuration** — Fast linter/formatter, minimal config needed
6. **Add Makefile** with standard targets: `make test`, `make lint`, `make check`
7. **Add mypy configuration** — Start with `--ignore-missing-imports`, tighten over time

### P2 — Reduce Noise
8. **Clean up tome/ directory** — Archive or delete the 35+ stale assessment files
9. **Split handlers.py** — Move each handler to its own file under `handlers/`
10. **Document reference.py** — Add header explaining purpose, or remove if unused

### P3 — CI/CD
11. **Add GitHub Actions** — Run pytest + ruff on every push
12. **Add pre-commit hooks** — Catch issues before commit

---

## 6. Verdict

**Can an agent iterate on this codebase?** Yes, with caveats.

**The good:** Excellent test infrastructure. An agent that discovers `test_integration.py` can use it as a pattern to understand the full system. The 5-primitive architecture is clean and each package is independently testable. MockListener and text teller enable headless CI/testing.

**The bad:** An agent's first 15-30 minutes will be wasted on misleading documentation (ARCHITECTURE.md, CLAUDE.md). The pyperclip crash blocks importing the main app module. The missing lint/type-check means agents get no feedback on code quality — only runtime failures.

**The ugly:** 35+ stale assessment files in `tome/` from prior agent runs create significant noise and confusion about what's canonical.

**Overall score: 6/10 for agent iterability.**
- Tests: 9/10
- Documentation: 2/10
- Tooling (lint/types/CI): 1/10
- Architecture clarity: 8/10
- Noise level: 4/10
