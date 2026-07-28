# Phase 4: Agent Iterability Assessment

## Verdict: PARTIALLY ITERABLE — Good test foundation, missing outer feedback loops

An agent can make changes and verify them against the RSP unit tests, but there are significant friction points that reduce confidence and slow iteration.

## Feedback Loops That Exist

### 1. pytest with Hypothesis Property Testing (STRONG)
- 5 RSP subdirectories each have dedicated test suites: `store/`, `teller/`, `mark/`, `mode/`, `listener/`
- Test taxonomy: unit tests (`test_*.py`), oracle tests (`test_*_oracle.py`), gremlin/fuzz tests (`test_*_gremlin.py`)
- Hypothesis provides property-based testing with generated inputs — catches edge cases agents wouldn't think to test
- `.hypothesis/` directory with 30 cached constant files shows tests have been actively run
- **Working command:** `pytest store/ teller/ mark/ mode/ listener/`

### 2. docs/agentic-testing.md (STRONG)
- Excellent agent-facing documentation explaining two testing approaches:
  - MockListener for full integration testing
  - Direct `mode.handle()` calls for unit testing
- Complete KeyEvent construction examples
- Shows how to use `text` handler instead of espeak for headless testing

### 3. test_wire.py Smoke Test (MODERATE)
- Manual wiring smoke test that exercises the full RSP integration
- Good template for agents to understand component composition
- BUT: calls pyperclip on double-tap (line 83), will fail headless without mocking

### 4. CLAUDE.md (WEAK)
- Exists but doesn't document test commands
- No mention of `pytest`, test paths, or how to verify changes
- Only documents `python tome.py` and `sqlite3` commands

## Feedback Loops That Are Missing

### 1. No Linter
- No ruff, flake8, mypy, black, isort, pylint, or any static analysis tool
- An agent can introduce syntax errors, unused imports, type mismatches — no automated way to catch them
- **Impact:** Agent must rely solely on tests catching issues, which miss many bug classes

### 2. No CI/CD
- No `.github/` directory, no workflows, no automated test runs
- No way to know if the main branch is green
- **Impact:** Agent can't trust that the codebase was in a working state before making changes

### 3. No Pre-commit Hooks
- No `.pre-commit-config.yaml`, no git hooks
- **Impact:** No guardrails before commits

### 4. No Makefile or Task Runner
- No `make test`, `make lint`, `make check` targets
- No standard entry point for "verify everything"
- **Impact:** Agent must discover the right test command by reading config files

### 5. No Type Checking
- No mypy, pyright, or type annotations enforcement
- **Impact:** Refactoring is riskier — type errors only surface at runtime

## Agent Iterability Blockers

### Critical: pytest.ini vs pyproject.toml Conflict
- `pytest.ini` sets `testpaths = .` (discovers ALL test files including root-level)
- `pyproject.toml` sets `testpaths = ["store", "teller", "mark", "mode", "listener"]`
- pytest.ini takes precedence, so bare `pytest` runs root-level integration tests
- Root-level tests (`test_handlers.py`, `test_integration.py`, `test_wire.py`) import pyperclip and fail headless
- **Result:** An agent running `pytest` will see failures and not know if they're pre-existing or caused by their changes

### Critical: Undeclared pyperclip Dependency
- `tome.py` and `handlers.py` import pyperclip at module level
- pyperclip is commented out in pyproject.toml: `# clipboard = ["pyperclip>=1.8.0"]`
- A fresh `pip install -e .` won't install pyperclip, causing import failures
- Root-level tests that import handlers will crash

### Moderate: 36 Stale Assessment Files in tome/
- The `tome/` directory contains 36 markdown files from previous agent assessments
- These create noise and confusion — an agent might read stale findings and act on outdated information
- No way to distinguish current vs obsolete assessments

### Minor: CLAUDE.md Doesn't Document Test Commands
- An agent's first instinct is to check CLAUDE.md for how to run tests
- It only mentions `python tome.py` — no pytest commands, no test paths
- Agent must discover testing approach by reading pyproject.toml, pytest.ini, and docs/agentic-testing.md

## What Works Well for Agents

1. **RSP architecture is modular** — each component (store, teller, mark, mode, listener) is self-contained with its own tests. An agent can work on one RSP without understanding the others.

2. **Hypothesis property testing** — provides strong coverage with generated inputs, catches edge cases automatically.

3. **Text handler for teller** — `get_handler("text")` avoids needing espeak, enabling headless testing.

4. **MockListener** — enables integration testing without real keyboard input.

5. **Good test taxonomy** — unit, oracle, and gremlin tests provide layered verification.

## Recommendations (Priority Order)

1. **Fix pytest.ini** — Either delete it (let pyproject.toml control test discovery) or align testpaths. This is the single biggest blocker for agent iteration.

2. **Add test command to CLAUDE.md** — Add: `pytest store/ teller/ mark/ mode/ listener/ -x --tb=short`

3. **Add ruff** — Zero-config linter, catches real bugs, fast. Add to pyproject.toml:
   ```toml
   [tool.ruff]
   line-length = 120
   ```

4. **Add a Makefile** with standard targets:
   ```makefile
   test:
       pytest store/ teller/ mark/ mode/ listener/ -x --tb=short
   lint:
       ruff check .
   check: lint test
   ```

5. **Clean up tome/ directory** — Remove or archive the 36 stale assessment files.

6. **Fix pyperclip dependency** — Either add it to dependencies or gate the import behind a try/except.

## Summary

The codebase has a solid testing foundation in the RSP subdirectories. An agent who knows to run `pytest store/ teller/ mark/ mode/ listener/` can iterate effectively on individual components. But the missing outer loops (linting, CI, clear entry points) and the pytest.ini conflict mean an agent's first 10-15 minutes will be spent figuring out what works and what doesn't — time that should be spent on the actual task.

**Confidence: 8/10** — Based on thorough static analysis of all config files, test files, and project structure. Could not run tests live due to approval requirements, but the structural issues are clear from the code.
