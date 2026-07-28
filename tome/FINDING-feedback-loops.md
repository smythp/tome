# Finding: Tome Codebase Feedback Loop Assessment

**Date:** 2026-05-10
**Investigator:** Technical Architect Agent

## Executive Summary

Tome has **strong test infrastructure** but **absent tooling feedback loops**. The test suite is well-designed with a sophisticated three-tier pattern (standard/gremlin/oracle), but there's no linting, type checking, formatting, CI/CD, or documented test-running workflow. An agent working on this codebase can verify correctness through tests but has no guard rails for code quality.

## Feedback Loop Inventory

### 1. Unit Tests — STRONG ✅
- **15 test files**, ~8,819 lines of test code
- **Three-tier test pattern:**
  - **Standard** (`test_*.py`): Conventional pytest unit tests with fixtures
  - **Gremlin** (`test_*_gremlin.py`): Adversarial/fuzzing tests that try to break components with malicious inputs
  - **Oracle** (`test_*_oracle.py`): Edge case and property-based tests using Hypothesis, designed to expose real bugs
- **Coverage across all 5 modules:** store, teller, mark, mode, listener
- **Property-based testing:** 20+ `@given` decorators in store/test_store_oracle.py alone
- **Evidence of prior runs:** `.hypothesis/constants/` has 30 cached example files
- **Good fixtures:** MockStore, MockTeller, temp databases, text handler for non-audio testing

### 2. Integration Tests — MODERATE ⚠️
- `test_wire.py` (86 lines): Smoke test that wires all RSPs together
- `test_integration.py` (223 lines): Simulates a full user session with mocked `os._exit`
- `test_handlers.py` (1,362 lines): Tests the handler layer connecting modes to business logic
- These exist and appear well-structured but I couldn't verify they pass (pytest execution requires approval)

### 3. Agentic Testing Documentation — STRONG ✅
- `docs/agentic-testing.md` specifically documents how agents should test
- Two clear approaches: MockListener (full integration) and direct `mode.handle()` calls
- KeyEvent construction examples with all variants (chars, special keys, modifiers)
- Text handler for testing without espeak dependency

### 4. Linting — ABSENT ❌
- No flake8, ruff, pylint, or any linter configured
- No `.flake8`, `ruff.toml`, or `[tool.ruff]` in pyproject.toml
- No pre-commit hooks

### 5. Type Checking — ABSENT ❌
- No mypy, pyright, or pytype configured
- No `py.typed` marker
- No type stubs
- Some type hints exist in code (e.g., `str | None` in test fixtures) but no verification

### 6. Code Formatting — ABSENT ❌
- No black, ruff format, autopep8, or yapf configured
- No formatting rules documented

### 7. CI/CD — ABSENT ❌
- No `.github/workflows/`, `.gitlab-ci.yml`, or equivalent
- No automated test runs on commit/push

### 8. Build/Compile — N/A
- Python project, no build step needed
- `pyproject.toml` defines setuptools build backend but no build artifacts required for development

## Configuration Conflicts

**pytest.ini vs pyproject.toml testpaths conflict:**
- `pytest.ini`: `testpaths = .` (discovers ALL test files including root-level)
- `pyproject.toml`: `testpaths = ["store", "teller", "mark", "mode", "listener"]` (subdirectories only)
- **pytest.ini wins** (higher precedence), so root-level tests (`test_wire.py`, `test_integration.py`, `test_handlers.py`) ARE discovered
- But this conflict could confuse agents or developers who read pyproject.toml first

## Agent Iterability Impact

### What Works Well
1. **Test-driven verification**: Agent can run `pytest` to check if changes break anything
2. **Three-tier testing catches different failure modes**: standard tests catch regressions, gremlins catch input handling bugs, oracles catch property violations
3. **Agentic testing docs** tell the agent exactly how to construct test inputs
4. **Text handler** eliminates espeak dependency for testing
5. **MockListener** eliminates pynput/keyboard dependency for testing

### What's Missing for Agent Workflows
1. **No `make test` or documented test command** — agent must figure out `cd /path && .venv/bin/pytest`
2. **No lint feedback** — agent can introduce style violations with no signal
3. **No type checking** — agent can introduce type errors with no signal  
4. **No formatting** — agent can produce inconsistently formatted code
5. **No CI** — no automated verification on any code changes
6. **CLAUDE.md lacks test instructions** — the primary agent-facing doc doesn't mention how to run tests

## Recommendations

### High Priority (Agent Effectiveness)
1. **Add test command to CLAUDE.md**: `pytest` or `.venv/bin/pytest` with explanation of markers
2. **Resolve pytest config conflict**: Remove `[tool.pytest.ini_options]` from pyproject.toml or consolidate into one location
3. **Add ruff** for linting + formatting in one tool: minimal config, fast execution, catches real bugs

### Medium Priority (Code Quality)
4. **Add mypy or pyright**: Even basic type checking catches bugs agents commonly introduce
5. **Add a Makefile** with `test`, `lint`, `format`, `check` targets
6. **Add pre-commit config**: Catches issues before they enter the repo

### Lower Priority (Infrastructure)
7. **Add GitHub Actions CI**: Run tests + lint on push
8. **Add test coverage reporting**: Helps agents know which code paths need tests

## Raw Data

### Test File Sizes (lines)
```
  732 listener/test_listener.py
 1210 mark/test_mark.py
  444 mark/test_gremlin_attacks.py
 1093 mode/test_mode.py
  497 mode/test_mode_oracle.py
  658 mode/test_mode_syndic.py
  756 store/test_store.py
  354 store/test_store_gremlin.py
  319 store/test_store_oracle.py
  501 teller/test_teller.py
  366 teller/test_teller_gremlin.py
  218 teller/test_teller_oracle.py
 1362 test_handlers.py
  223 test_integration.py
   86 test_wire.py
 8819 total
```

### Test Tiers by Module
| Module   | Standard | Gremlin | Oracle | Syndic |
|----------|----------|---------|--------|--------|
| store    | ✅ 756L  | ✅ 354L | ✅ 319L| —      |
| teller   | ✅ 501L  | ✅ 366L | ✅ 218L| —      |
| mark     | ✅ 1210L | ✅ 444L | —      | —      |
| mode     | ✅ 1093L | —       | ✅ 497L| ✅ 658L|
| listener | ✅ 732L  | —       | —      | —      |
| root     | ✅ 1671L | —       | —      | —      |
