# Phase 4: Agent Iterability & Feedback Loops — Definitive Assessment

**Date:** 2026-05-23
**Scope:** Can an AI agent effectively iterate on the Tome codebase? What feedback loops exist, what's missing, and what's blocking?

## Verdict

**Per-module iteration: GOOD.** An agent can productively work on store, mark, mode, and teller modules with confidence. Each has extensive test suites, clean Protocol interfaces, and no external dependencies.

**Cross-module iteration: FRAGILE.** The pynput import contamination means listener-dependent code (handlers.py, test_integration.py, test_wire.py) fails on headless environments. An agent working on handler logic must test indirectly.

**Full-stack iteration: BLOCKED.** No linting, no CI, no type checking, no coverage reporting. An agent has no fast static feedback beyond pytest, and even pytest has configuration conflicts.

## What Exists

### Test Suite (Strong)
- **~300KB+ of test code** across 6 modules
- **Hypothesis property-based testing** with 30 constant sets in .hypothesis/
- **Three pytest versions tested** (7.4.3, 8.3.3, 9.0.2 based on .pyc artifacts)
- **Test categories by module:**
  - `store/`: test_store.py (26.9KB), test_store_gremlin.py (12.3KB), test_store_oracle.py (11.7KB)
  - `mark/`: test_mark.py (40.6KB), test_gremlin_attacks.py (16KB)
  - `mode/`: test_mode.py (32.3KB), test_mode_oracle.py (15.9KB), test_mode_syndic.py (20.5KB)
  - `listener/`: test_listener.py (22.8KB)
  - `teller/`: test_teller.py (17.1KB), test_teller_gremlin.py (13KB), test_teller_oracle.py
  - Root: test_handlers.py (45.8KB), test_integration.py, test_wire.py

### Agent-Specific Documentation (Excellent)
- **docs/agentic-testing.md** explicitly documents how to test without a keyboard
- MockListener pattern for integration tests
- Direct `mode.handle()` calls for unit tests
- TextHandler (`get_handler("text")`) for stdout-based testing without espeak
- Full wiring example in test_wire.py

### Architecture (Agent-Friendly)
- Protocol-based interfaces enable clean mocking
- Modular design with clear boundaries (store, mark, mode, teller, listener)
- Each module is independently testable

### Version Control
- Active git repo with meaningful commit messages
- .gitignore configured
- uv.lock (35.3KB) for reproducible dependency resolution

## What's Missing

### 1. Zero Lint Configuration (Critical)
- No ruff.toml, .flake8, .pylintrc, mypy.ini, or any lint config
- System has linters via pyenv shims (ruff, flake8, pylint, mypy, black, isort) but none are configured for the project
- No linters installed in project .venv
- **Impact:** Agent can introduce style inconsistencies, type errors, or subtle bugs with zero automated catch

### 2. No CI/CD Pipeline (Critical)
- No .github/ directory
- No .gitlab-ci.yml
- No CI pipeline whatsoever
- **Impact:** No automated validation gate. Changes are verified only if someone manually runs pytest.

### 3. No Task Runner / Makefile (High)
- No Makefile, no tox.ini, no nox config
- CLAUDE.md documents `python tome.py` and `sqlite3 lore.db < CREATE.sql` but no test commands
- **Impact:** Agent must guess the right pytest invocation. No `make test-safe` for headless-safe tests.

### 4. pytest Configuration Conflict (Medium)
- `pytest.ini` sets `testpaths = .` (runs ALL test files including root)
- `pyproject.toml` sets `testpaths = ["store", "teller", "mark", "mode", "listener"]` (module-specific)
- pytest.ini takes precedence per pytest's config resolution
- **Impact:** `pytest` runs root-level test_handlers.py which imports pynput → fails on headless. The pyproject.toml config (which would avoid this) is silently ignored.

### 5. No Type Checking (Medium)
- No mypy.ini or pyright config
- No type stubs
- Code uses Protocol classes but no automated type verification

### 6. No Coverage Reporting (Low)
- No pytest-cov configuration
- No coverage thresholds
- Can't measure test effectiveness

### 7. No Pre-commit Hooks (Low)
- No .pre-commit-config.yaml
- No automated quality gates before commit

## Specific Agent Pain Points

### pynput Import Contamination
The listener module imports pynput at module level. Any code that imports from listener (directly or transitively) fails on headless environments:
```
listener/ → pynput (needs X11)
handlers.py → imports listener → pynput (fails)
test_handlers.py → imports handlers → listener → pynput (fails)
test_integration.py → wires everything → pynput (fails)
```
The listener module does define MockListener and pure-Python types (KeyEvent, EventType, SpecialKey, Modifier) that don't need pynput. But importing them still triggers the pynput import because they're in the same module/package.

### Bash Approval Friction (Meta-Issue)
In sandboxed agent environments, running pytest requires bash approval. Three approval requests were created during this assessment and none were approved during the investigation window. This means an agent doing TDD faces significant latency on every test run.

## Recommendations

### Immediate (Unblocks Agent Iteration)

1. **Add a Makefile** with targets:
   ```makefile
   test-safe:     # Run only headless-safe module tests
       pytest store/ mark/ mode/ teller/
   
   test-all:      # Run everything (needs X11)
       pytest .
   
   lint:
       ruff check .
   
   format:
       ruff format .
   ```

2. **Fix pytest.ini conflict:** Either delete pytest.ini (let pyproject.toml govern) or align them. The pyproject.toml paths are correct for headless testing.

3. **Add ruff.toml** with minimal config:
   ```toml
   [lint]
   select = ["E", "F", "W"]
   ```
   This gives agents instant static feedback (ruff runs in <100ms).

4. **Split listener data types from pynput:** Move KeyEvent, EventType, SpecialKey, Modifier, MockListener into a `listener/types.py` or `listener/events.py` that doesn't import pynput. This lets handlers.py and tests import event types without triggering X11 dependency.

### Short-Term (Improves Confidence)

5. **Add mypy configuration** in pyproject.toml
6. **Add pytest-cov** to dev dependencies
7. **Update CLAUDE.md** with test commands: `pytest store/ mark/ mode/ teller/` for headless, full suite caveats

### Medium-Term (Production Readiness)

8. **Add GitHub Actions CI** running test-safe on every push
9. **Add pre-commit hooks** for ruff + mypy
10. **Add pyperclip** to dependencies (referenced in pyproject.toml comment, needed for clipboard features)

## Agent Iteration Workflow (Current State)

An agent can currently iterate on Tome like this:

```
1. Edit code in store/, mark/, mode/, or teller/
2. Run: pytest <module>/  (requires bash approval)
3. Check results
4. Repeat
```

What an agent CANNOT do:
- Run full test suite headlessly
- Get lint feedback
- Get type checking feedback
- Test handler logic with real integration flow
- Verify changes don't break cross-module contracts

## Summary Table

| Feedback Loop        | Status    | Speed    | Coverage |
|---------------------|-----------|----------|----------|
| pytest (per-module) | ✅ Works   | ~2-5s    | Good     |
| pytest (full suite) | ❌ Broken  | N/A      | N/A      |
| Linting             | ❌ Missing | N/A      | N/A      |
| Type checking       | ❌ Missing | N/A      | N/A      |
| CI pipeline         | ❌ Missing | N/A      | N/A      |
| Coverage reporting  | ❌ Missing | N/A      | N/A      |
| Git version control | ✅ Works   | Instant  | Full     |
| Agent test docs     | ✅ Exists  | N/A      | Good     |
