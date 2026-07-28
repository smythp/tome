# Phase 4: Agent Iterability Assessment

## Verdict: PARTIALLY ITERABLE — Strong tests, weak DX scaffolding

**Confidence: 7/10**

## Feedback Loops Available

### 1. pytest (PRIMARY — the only real feedback loop)
- **Location**: Tests colocated with modules (`store/test_store.py`, `mark/test_mark.py`, etc.)
- **Framework**: pytest + hypothesis (property-based testing)
- **Run command**: `.venv/bin/python -m pytest` (NOT documented in CLAUDE.md)
- **Test categories**:
  - Unit tests: `test_store.py`, `test_mark.py`, `test_mode.py`, `test_listener.py`, `test_teller.py`
  - Gremlin tests (adversarial/fuzzing): `test_gremlin_attacks.py`, `test_store_gremlin.py`, `test_teller_gremlin.py`
  - Oracle tests (correctness verification): `test_store_oracle.py`, `test_mode_oracle.py`, `test_teller_oracle.py`
  - Syndic tests: `test_mode_syndic.py`
  - Integration: `test_integration.py` (root level)
  - Handler tests: `test_handlers.py` (root level, 45.8KB)
- **Markers**: `db`, `ui`, `keyboard`, `clipboard`, `integration`
- **Test volume**: Substantial — test files are often larger than source files (test_mark.py is 40.6KB vs mark.py)

### 2. No linting (MISSING)
- No ruff, flake8, pylint, or any linting tool configured
- No `.flake8`, `ruff.toml`, or linting section in pyproject.toml

### 3. No type checking (MISSING)
- No mypy, pyright, or type checker configured
- No `py.typed` marker, no type stubs

### 4. No build system / task runner (MISSING)
- No Makefile, no `just`, no npm scripts, no tox
- No standardized way to run common tasks

### 5. No CI/CD (MISSING)
- No `.github/workflows/`, no `.gitlab-ci.yml`, no CI config

### 6. No pre-commit hooks (MISSING)
- No `.pre-commit-config.yaml`

## Issues Degrading Agent Iterability

### Critical: CLAUDE.md doesn't mention test commands
CLAUDE.md lists `python tome.py` for running the app and `sqlite3 lore.db < CREATE.sql` for DB init, but says NOTHING about running tests. An agent following CLAUDE.md guidance would not know how to run the test suite. This is the single biggest gap for agent iteration.

### Moderate: Config conflict between pyproject.toml and pytest.ini
- `pyproject.toml` defines `testpaths = ["store", "teller", "mark", "mode", "listener"]`
- `pytest.ini` defines `testpaths = .`
- pytest.ini takes precedence (INI files override pyproject.toml)
- Result: pytest collects from `.` (entire project root), not the module directories
- This means root-level tests (test_integration.py, test_handlers.py, test_wire.py) ARE collected, but it's confusing having two conflicting configs

### Moderate: No Makefile or task runner
Common commands that should be one-liners:
- `make test` → run all tests
- `make test-store` → run store tests only  
- `make lint` → run linter
- `make check` → run all checks

Without these, agents must know the exact incantation (`.venv/bin/python -m pytest -x store/`) which is error-prone.

### Minor: No linting means silent style drift
An agent can introduce style inconsistencies with no automated feedback. Over time this degrades readability.

### Minor: No type checking means refactoring is risky
Without types, an agent changing a function signature has no way to verify all callers are updated (except tests, if they cover it).

## What Works Well

1. **Test architecture is excellent**: The gremlin/oracle/syndic pattern is sophisticated. Property-based testing with hypothesis catches edge cases that unit tests miss.
2. **Tests are colocated**: Easy for an agent to find tests for a module — they're in the same directory.
3. **pytest markers**: Allow targeted test runs (e.g., skip `ui` tests in headless environments).
4. **Integration test exists**: `test_integration.py` exercises the full stack, giving confidence that module changes don't break the system.
5. **Virtual environment is pre-configured**: `.venv/` exists with pytest and hypothesis installed.

## Recommendations

1. **Add test commands to CLAUDE.md** — This is the highest-leverage fix. Add:
   ```
   ## Testing
   - Run all tests: `.venv/bin/python -m pytest`
   - Run module tests: `.venv/bin/python -m pytest store/`
   - Run specific test: `.venv/bin/python -m pytest store/test_store.py::test_name`
   - Skip UI tests: `.venv/bin/python -m pytest -m 'not ui'`
   ```

2. **Resolve pytest config conflict** — Either remove `pytest.ini` or align it with `pyproject.toml`. One source of truth.

3. **Add a Makefile** — Even a minimal one with `test`, `test-fast`, and `lint` targets dramatically improves agent DX.

4. **Add ruff** — Fast, zero-config Python linter. One line in pyproject.toml. Catches issues that tests don't.

5. **Add mypy (basic)** — Even `mypy --ignore-missing-imports` catches obvious type errors.

## Summary

The test suite is the crown jewel — it's well-designed with multiple testing paradigms (unit, property-based, adversarial, oracle). But the surrounding DX infrastructure is nearly absent. An agent can iterate using pytest, but will waste time figuring out how to run it, navigating config conflicts, and lacking fast feedback from linting/types. The fixes are low-effort, high-impact.
