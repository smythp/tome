# Phase 4: Agent Iterability Assessment

**Verdict: Agent CAN iterate, with MODERATE friction** (confidence: 8/10)

## The Core Question

Can an agent make changes to this codebase and verify they work?

**Yes.** The test suite is the primary feedback loop and it's excellent. An agent can read code, make changes, run `pytest`, and see what breaks. But there's unnecessary friction in orientation and tooling.

## Feedback Loops That Exist

### 1. Tests (PRIMARY — Strong)

Three-tier test strategy across all 5 RSP modules:

| Tier | Purpose | Files | Example |
|------|---------|-------|---------|
| Unit | Correctness | `test_store.py`, `test_mark.py`, `test_mode.py`, `test_listener.py`, `test_teller.py` | Assert specific behavior |
| Gremlin | Adversarial/fuzz | `test_gremlin_attacks.py`, `test_store_gremlin.py`, `test_teller_gremlin.py` | Malformed input, edge cases |
| Oracle | Property-based | `test_store_oracle.py`, `test_mode_oracle.py`, `test_teller_oracle.py` | Hypothesis-generated inputs |

Plus root-level integration tests:
- `test_wire.py` — Smoke test for RSP wiring (perfect "did I break anything" check)
- `test_integration.py` — Full user session simulation
- `test_handlers.py` — Handler behavior tests

**Run command:** `.venv/bin/pytest` (or `python -m pytest`)

**Caveat:** `pytest.ini` sets `testpaths = .` (discovers everything), while `pyproject.toml` sets `testpaths = ["store", "teller", "mark", "mode", "listener"]`. Since `pytest.ini` takes precedence, running bare `pytest` discovers root-level tests too. This is actually fine for agents — more coverage — but the inconsistency is confusing.

### 2. Agentic Testing Docs (Strong)

`docs/agentic-testing.md` is excellent. It explains:
- How to use `MockListener` for integration tests without real keyboard
- How to call `mode.handle()` directly for unit tests
- `KeyEvent` construction patterns
- The `text` teller handler for test output

This is exactly what an agent needs to write new tests.

### 3. Build (Adequate)

- `pyproject.toml` with setuptools backend
- `uv.lock` for reproducible installs
- `.venv` with Python 3.12, pytest, hypothesis pre-installed
- Pure Python — no build step needed for development

### 4. Git (Adequate)

- Clean atomic commits in history
- Meaningful commit messages
- `.gitignore` covers standard artifacts

## Feedback Loops That Are Missing

### 1. Linting / Type Checking (Missing — High Impact)

No ruff, flake8, mypy, pylint, or any static analysis. This means:
- Type errors caught only at runtime
- Unused imports accumulate silently
- Style drift goes undetected
- An agent can introduce subtle bugs that tests don't catch

**Recommendation:** Add ruff. It's fast, zero-config by default, catches real bugs.

### 2. CI Pipeline (Missing — Medium Impact)

No GitHub Actions, no automated verification. Changes are verified only if someone remembers to run tests.

### 3. Task Runner / Makefile (Missing — Medium Impact)

No `make test`, `make lint`, `make check`. An agent must know the exact pytest invocation. This is a small friction but it compounds.

### 4. Coverage Reporting (Missing — Low Impact)

No `.coveragerc`, no coverage plugin. An agent can't tell if their new code is tested.

### 5. Pre-commit Hooks (Missing — Low Impact)

No automated quality gates before commit.

## The Orientation Problem

**CLAUDE.md is the biggest friction point for agents.**

Current CLAUDE.md tells agents:
- Run: `python tome.py` (which crashes due to pyperclip)
- Init DB: `sqlite3 lore.db < CREATE.sql`
- Code style guidelines

It does NOT mention:
- How to run tests (`pytest`)
- The 3-tier test strategy
- The RSP architecture
- `docs/agentic-testing.md` exists
- The pyperclip blocker
- Which modules are safe to import

An agent arriving cold wastes significant cycles figuring out what this project even is and how to verify changes.

## Agent Iteration Workflow (Current State)

What an agent must do today:

```
1. Read CLAUDE.md                    → Gets minimal guidance
2. Read pyproject.toml               → Discovers RSP module names
3. files_tree to understand layout   → Sees test files everywhere
4. Guess that pytest is the runner   → Correct but not documented
5. Run pytest                        → Discovers tests pass
6. Maybe find agentic-testing.md     → Lucky if they do
7. Make changes
8. Run pytest again
9. Check results
```

What it SHOULD be:

```
1. Read CLAUDE.md                    → Full orientation in 30 seconds
2. Run `make test`                   → Verify baseline
3. Make changes
4. Run `make check`                  → Tests + lint
5. Done
```

## Top 3 Improvements for Agent Iterability

### 1. Expand CLAUDE.md (Highest Impact, Lowest Effort)

Add to CLAUDE.md:
- `## Testing` section with `pytest` command
- Mention 3-tier test strategy
- Link to `docs/agentic-testing.md`
- Brief RSP architecture description (5 modules, what each does)
- Known issues (pyperclip blocker)
- "After making changes, run `pytest` to verify"

### 2. Add a Makefile (High Impact, Low Effort)

```makefile
.PHONY: test lint check

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check .

check: lint test
```

Gives agents a single `make check` command.

### 3. Add ruff (Medium Impact, Low Effort)

```toml
# pyproject.toml
[tool.ruff]
target-version = "py310"
select = ["E", "F", "W", "I"]
```

Fast linting catches bugs that tests miss.

## Summary

| Dimension | Status | Notes |
|-----------|--------|-------|
| Tests | ✅ Strong | 3-tier strategy, good coverage |
| Test docs | ✅ Strong | agentic-testing.md is excellent |
| Build | ✅ Adequate | pyproject.toml + uv.lock + .venv |
| Git | ✅ Adequate | Clean history, good .gitignore |
| Agent orientation | ⚠️ Weak | CLAUDE.md is minimal |
| Task runner | ❌ Missing | No Makefile |
| Linting | ❌ Missing | No static analysis |
| CI | ❌ Missing | No automated pipeline |
| Coverage | ❌ Missing | No coverage reporting |

The test suite saves this project. Without it, agent iterability would be poor. With it, an agent can be productive — they just waste cycles on orientation that could be eliminated with a better CLAUDE.md.
