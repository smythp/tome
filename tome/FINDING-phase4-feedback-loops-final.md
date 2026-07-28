# Phase 4: Agent Iterability — Consolidated Finding

**Date:** 2026-05-08
**Assessor:** boffin (technical architect)
**Method:** Static analysis of all project files, configs, docs, test files, plus synthesis of two prior assessments

---

## Verdict

**Module-level iteration: excellent. Project-level iteration: broken.**

Tome's RSP modules are individually among the best-tested Python code I've seen for agent iteration. The three-tier test strategy (regular/oracle/gremlin), protocol-based DI, Hypothesis property testing, and explicit agentic testing docs show genuine care for testability.

The problem is entirely at the project level: a config conflict poisons test discovery, oracle tests make the suite permanently red, and there's no documented entry point for "verify my change."

---

## Existing Feedback Loops (What's Working)

| Loop | Signal Quality | Notes |
|------|---------------|-------|
| `pytest store/` | ✅ Excellent | 26.9KB of tests, clean isolation |
| `pytest mark/` | ✅ Excellent | 40.6KB tests + 16KB gremlin |
| `pytest teller/` | ✅ Excellent | 17.1KB + gremlin + oracle |
| `pytest listener/` | ✅ Excellent | 22.8KB of tests |
| `pytest mode/` | ⚠️ Poisoned | Oracle tests fail intentionally |
| Hypothesis property tests | ✅ Excellent | 30 constant files → thorough fuzzing |
| Protocol-based DI | ✅ Excellent | Natural mocking without frameworks |
| `docs/agentic-testing.md` | ✅ Excellent | Explicit agent guidance |
| Text teller handler | ✅ Good | stdout-based testing without audio |
| MockListener | ✅ Good | Integration testing without keyboard |
| Git history | ✅ Good | Clean commits, proper .gitignore |

## Broken/Missing Feedback Loops

| Missing Loop | Impact |
|-------------|--------|
| pytest.ini vs pyproject.toml conflict | **CRITICAL** — pytest.ini wins (testpaths=.), silently overrides pyproject.toml (testpaths=[modules]), collects root-level scripts |
| Oracle tests designed to fail | **CRITICAL** — suite permanently red, agents try to "fix" intentional failures |
| No Makefile / task runner | **HIGH** — agent must guess commands |
| CLAUDE.md doesn't document test commands | **HIGH** — agent's first action fails |
| No linter (ruff/flake8) | **MEDIUM** — style drift with no signal |
| No type checker (mypy/pyright) | **MEDIUM** — type errors only at runtime |
| No CI/CD | **LOW** — no external verification gate |
| No coverage reporting | **LOW** — can't verify new code is tested |
| Test markers defined but unused | **LOW** — missed selective-run opportunity |
| Mock definition drift (MockTeller speak() vs tell()) | **LOW** — syndic tests use wrong protocol method |

---

## The Agent Experience Today vs. Ideal

### Today:
```
1. Agent reads CLAUDE.md → no test command listed
2. Agent guesses `pytest` → pytest.ini overrides pyproject.toml
3. Root-level test files collected, oracle tests fail intentionally
4. Agent sees red → can't establish green baseline
5. Agent makes change → can't tell if it broke anything
6. Feedback loop: BROKEN
```

### After 3 fixes:
```
1. Agent reads CLAUDE.md → sees `make test`
2. Agent runs `make test` → only stable module tests run
3. All green ✅ → baseline established
4. Agent makes change → runs `pytest store/` for fast feedback
5. All green ✅ → runs `make test` for full verification
6. Feedback loop: WORKING
```

---

## Priority Fixes (35 minutes total)

### Fix 1: Delete pytest.ini (5 min) — BIGGEST BANG FOR BUCK
Remove `pytest.ini` entirely. Consolidate markers into `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["store", "teller", "mark", "mode", "listener"]
python_files = "test_*.py"
python_functions = "test_*"
markers = [
    "db: tests that interact with the database",
    "ui: tests for user interface components",
    "keyboard: tests involving keyboard interaction",
    "clipboard: tests involving clipboard operations",
    "integration: integration tests combining multiple components",
]
```

### Fix 2: Mark oracle tests as xfail (15 min) — MAKES SUITE GREEN
In every oracle test file (`test_mode_oracle.py`, `test_store_oracle.py`, `test_teller_oracle.py`):
```python
@pytest.mark.xfail(reason="Known bug: closure capture in get_state", strict=True)
def test_get_state_closure_capture(self):
    ...
```
`strict=True` means if the bug gets fixed, pytest flags it as XPASS — prompting removal of the marker.

### Fix 3: Add Makefile + update CLAUDE.md (15 min) — GIVES AGENTS A FRONT DOOR
```makefile
.PHONY: test test-full test-module lint

test:  ## Fast stable tests (agent default)
	.venv/bin/pytest -x -q

test-full:  ## All tests including hypothesis
	.venv/bin/pytest -v

test-module:  ## Single module: make test-module M=store
	.venv/bin/pytest -x -q $(M)/

lint:  ## Check code style
	.venv/bin/ruff check .
```

Update CLAUDE.md:
```markdown
## Commands
- Run tests: `make test` (fast, stable tests)
- Run all tests: `make test-full` (including hypothesis property tests)
- Run module tests: `make test-module M=store`
- Lint: `make lint`
```

---

## Relationship to Prior Assessments

This finding synthesizes and validates:
- `tome/AGENT-ITERABILITY-ASSESSMENT.md` (2026-05-03) — thorough, accurate, identified all 7 issues
- `tome/PHASE4-FEEDBACK-LOOPS.md` (2026-05-07) — added agent walkthrough and signal quality ratings

All three assessments converge on the same top-3 fixes. The core insight is consistent: **module-level testing is excellent, project-level tooling is broken, and the fix is surgical.**

---

*Assessment by boffin agent — Phase 4 feedback loop analysis, static analysis only*
*Bash execution was unavailable (approval not granted) — findings based on file reads and config analysis*
