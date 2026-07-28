# Phase 4: Agent Iterability Assessment — Feedback Loops & Development Workflow

**Date:** 2026-05-29
**Agent:** boffin (Phase 4)
**Method:** Static analysis (bash approval unavailable)
**Confidence:** 7/10

## Executive Summary

An agent CAN iterate effectively on individual RSP components thanks to comprehensive unit tests and explicit agentic testing documentation. However, the project lacks build tooling (no Makefile), linting, and has conflicting test configs that create friction. End-to-end iteration is broken due to the missing pyperclip dependency.

## Feedback Loops That Exist

### 1. pytest — Primary Feedback Loop ✅
- **Config:** Both `pyproject.toml` and `pytest.ini` (conflicting — see Issues)
- **Test paths:** store/, teller/, mark/, mode/, listener/ (per pyproject.toml)
- **Command:** `.venv/bin/pytest` or `python -m pytest`
- **Coverage:** Each RSP has dedicated test files:
  - `store/test_store.py` (26.9KB) — standard tests
  - `store/test_store_gremlin.py` (12.3KB) — fuzz/chaos tests
  - `store/test_store_oracle.py` (11.7KB) — property-based oracle tests
  - Same pattern for teller, mark, mode, listener
  - Plus `test_mode_syndic.py` (20.5KB) — Hypothesis-based tests

### 2. Smoke Tests ✅
- `test_wire.py` — Verifies RSP components wire together correctly
- `test_integration.py` — Simulates a full user session with multiple modes

### 3. Text Handler for Headless Testing ✅
- `teller/handlers/text.py` — Prints to stdout instead of speaking via espeak
- Allows full testing without audio hardware or display server
- Used via: `teller = get_handler("text")`

### 4. MockListener for Input Simulation ✅
- `listener.MockListener` — Injects KeyEvents without real keyboard
- Enables testing the full listener → callback pipeline

### 5. Agentic Testing Documentation ✅
- `docs/agentic-testing.md` (4.5KB) — Explicitly teaches agents how to:
  - Construct KeyEvent objects
  - Use MockListener vs direct mode.handle() calls
  - Wire up test components
  - Use the text handler
- This is **unusually good** — most projects don't have agent-specific testing docs

### 6. Project Guidelines ✅
- `CLAUDE.md` — Code style, naming conventions, architecture notes
- Helps agents maintain consistency when making changes

## What's Missing

### 1. No Makefile or Task Runner ❌
- No `make test`, `make lint`, `make check`
- Agent must know to run `.venv/bin/pytest` directly
- No single command to verify everything is clean

### 2. No Linter or Type Checker ❌
- No ruff, flake8, pylint, or mypy configuration
- Agents can introduce style violations and type errors silently
- No formatting tool (black, autopep8)

### 3. Conflicting pytest Configurations ⚠️
- `pytest.ini` sets `testpaths = .` (runs ALL test files, including root-level ones)
- `pyproject.toml` sets `testpaths = ["store", "teller", "mark", "mode", "listener"]`
- pytest.ini takes precedence (it's loaded first)
- This means `pytest` discovers different tests than what pyproject.toml intends
- Could confuse agents about which tests are canonical

### 4. No CI Pipeline ❌
- No GitHub Actions, GitLab CI, or similar
- No automated verification on commit/push
- Agent has no way to know if changes break other environments

### 5. No Pre-commit Hooks ❌
- No `.pre-commit-config.yaml`
- No git hooks for automated checking

### 6. Missing pyperclip Dependency ❌
- `tome.py` line 32: `import pyperclip` at module level
- `pyperclip` not in `pyproject.toml` dependencies (commented out as "Future")
- App crashes on startup → end-to-end testing is impossible
- Blocks any agent from testing the full application flow

### 7. 30+ Stale Assessment Files 🗑️
- `tome/` directory contains 30+ markdown files from previous agent assessments
- Creates noise when agents scan the project structure
- Example: PHASE3-RUNNABILITY-*.md (8 files), PHASE4-*.md (10+ files)

## Agent Iteration Verdict

### What an Agent CAN Do Well:
1. **Modify individual RSP components** — Each has isolated, comprehensive tests
2. **Add new test cases** — Testing patterns are clear and well-documented
3. **Wire components together** — test_wire.py provides a template
4. **Test without hardware** — TextHandler + MockListener enable headless testing

### What an Agent CANNOT Do Well:
1. **Run the full app** — pyperclip crash blocks this entirely
2. **Verify code quality** — No linter means silent degradation
3. **Know which tests to trust** — Conflicting pytest configs create ambiguity
4. **Run a single verification command** — No Makefile or equivalent

### Friction Points for Agents:
1. Must discover `.venv/bin/pytest` path (not in CLAUDE.md commands section as test command)
2. Must know pytest.ini overrides pyproject.toml
3. Must navigate 30+ stale assessment files to find actual project code
4. No way to verify type correctness of changes

## Recommendations

1. **Add a Makefile** with `test`, `lint`, `check`, `clean` targets
2. **Add ruff** for linting + formatting (fast, minimal config)
3. **Fix pytest config** — remove pytest.ini or align it with pyproject.toml
4. **Add pyperclip** to dependencies (or guard the import)
5. **Clean up stale assessment files** — archive or delete the 30+ markdown files
6. **Add test command to CLAUDE.md** — Tell agents exactly how to run tests
7. **Add mypy or pyright** for type checking (even basic mode helps)
