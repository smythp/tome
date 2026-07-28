# Agent Iterability Assessment: Tome Codebase

**Assessor:** Independent static analysis (bash execution blocked by approval gates)
**Date:** 2026-05-20
**Verdict:** MODERATE iterability — strong test foundations, weak automation tooling

---

## Executive Summary

The Tome codebase has an unusually rich test suite for its size, with four distinct testing paradigms (unit, gremlin/fuzzing, oracle, integration). However, it lacks the automation scaffolding (task runner, linter, type checker, CI) that makes agent iteration *smooth*. An agent can iterate, but through a single narrow feedback channel: `pytest`.

## What Works Well

### 1. Multi-Paradigm Test Suite
- **Unit tests:** `test_mark.py` (40KB), `test_store.py` (27KB), `test_mode.py` (32KB), `test_listener.py` (23KB), `test_handlers.py` (46KB)
- **Gremlin/fuzzing tests:** `test_gremlin_attacks.py`, `test_store_gremlin.py`, `test_teller_gremlin.py` — adversarial input testing
- **Oracle tests:** `test_mode_oracle.py`, `test_store_oracle.py`, `test_teller_oracle.py` — behavioral correctness verification
- **Integration tests:** `test_integration.py` (full user session simulation), `test_wire.py` (component wiring smoke test)
- **Property-based tests:** Hypothesis integration with 30+ cached constants in `.hypothesis/`

### 2. Hardware-Free Testing
- `TextHandler` (teller): prints to stdout instead of calling espeak — no audio hardware needed
- `MockListener`: injects `KeyEvent` objects without real keyboard — no input hardware needed
- Direct `mode.handle()` calls bypass the listener entirely for unit testing
- These are **critical** for agent iteration — agents can't press keys or listen to audio

### 3. Agentic Testing Documentation
- `docs/agentic-testing.md` explicitly documents how to test without hardware
- Shows both MockListener (full integration) and direct handle() (unit) approaches
- Includes complete KeyEvent construction reference
- Points to `test_wire.py` as a working example

### 4. Simple Setup
- `.venv` exists with pytest and hypothesis pre-installed
- No build step needed — pure Python with direct imports
- SQLite database (no external services)
- Single command to run: `.venv/bin/python -m pytest`

## What's Missing

### 1. No Task Runner (Critical)
- No `Makefile`, `justfile`, `taskfile`, or `nox`/`tox` config
- Agent must know the exact pytest invocation
- CLAUDE.md mentions `python tome.py` and `sqlite3 lore.db < CREATE.sql` but **does not mention how to run tests**
- This is the single biggest gap for agent iterability

### 2. No Static Analysis Tooling
- No linter: no ruff, flake8, pylint config
- No type checker: no mypy, pyright, pytype config
- No formatter: no black, ruff format config
- No pre-commit hooks
- Result: an agent gets zero feedback on code style, type safety, or common errors without running the full test suite

### 3. No CI/CD Pipeline
- No `.github/workflows/`, `.gitlab-ci.yml`, or equivalent
- No automated quality gate
- No coverage reporting (no `pytest-cov` in dependencies)

### 4. Configuration Conflict
- `pytest.ini` sets `testpaths = .` (scans everything)
- `pyproject.toml` sets `testpaths = ['store', 'teller', 'mark', 'mode', 'listener']`
- pytest.ini takes precedence (pytest checks ini files first)
- Root-level tests (`test_handlers.py`, `test_integration.py`, `test_wire.py`) ARE discovered via pytest.ini but WOULD NOT be discovered via pyproject.toml alone
- This is a latent bug waiting to bite an agent that reads pyproject.toml but not pytest.ini

## The Feedback Loop

An agent iterating on this codebase has exactly **one feedback loop**:

```
edit code → run pytest → read output → repeat
```

This loop is well-built:
- Tests are comprehensive and cover edge cases
- Gremlin tests catch robustness issues
- Oracle tests verify behavioral invariants
- Property-based tests explore input space

But it's the **only** loop. Compare to a well-instrumented codebase:

| Feedback Channel | Tome | Well-instrumented |
|---|---|---|
| Unit tests | ✅ | ✅ |
| Integration tests | ✅ | ✅ |
| Property tests | ✅ | ✅ |
| Fuzz/gremlin tests | ✅ | Sometimes |
| Linter | ❌ | ✅ |
| Type checker | ❌ | ✅ |
| Coverage report | ❌ | ✅ |
| CI pipeline | ❌ | ✅ |
| Task runner | ❌ | ✅ |
| Pre-commit hooks | ❌ | ✅ |

## Meta-Observation: The Approval Gate Problem

Both this agent and the previous agent were unable to actually run the test suite due to bash command approval gates. This is itself evidence about agent iterability:

- An agent needs **command execution** to close the feedback loop
- Approval gates block **autonomous iteration**
- The static analysis capability (reading code, understanding tests) is strong
- But the dynamic feedback (actually running tests) requires human-in-the-loop

This is an environmental constraint, not a codebase issue. But it means the codebase's strong test suite is effectively unreachable for agents in approval-gated environments.

## Recommendations

### High Impact, Low Effort
1. **Add test command to CLAUDE.md**: `.venv/bin/python -m pytest` — one line, huge agent impact
2. **Add a Makefile** with `make test`, `make lint`, `make check` targets
3. **Resolve pytest.ini vs pyproject.toml conflict** — pick one source of truth

### Medium Impact, Medium Effort
4. **Add ruff** for linting + formatting (single tool, fast, zero-config sensible defaults)
5. **Add pytest-cov** for coverage reporting
6. **Add pre-commit** hooks (ruff + pytest smoke)

### Lower Priority
7. **Add mypy/pyright** for type checking (significant effort given current untyped codebase)
8. **Add CI pipeline** (GitHub Actions or similar)

## Confidence Assessment

- **Test suite quality:** HIGH confidence — read all test files, clear multi-paradigm approach
- **Missing tooling:** HIGH confidence — checked for all standard config files
- **Configuration conflict:** HIGH confidence — read both files, verified pytest precedence rules
- **Test runnability:** LOW confidence — could not actually run tests to verify they pass
- **Agent iteration speed:** MEDIUM confidence — strong static evidence but no dynamic verification

## Verdict

**Score: 6/10 for agent iterability**

The codebase has better-than-average test foundations (multi-paradigm testing is rare), but below-average automation scaffolding. An agent can iterate, but slowly — through a single feedback channel, without style or type guidance, and with a configuration conflict that could cause confusion.

The gap between the test suite quality (excellent) and the automation tooling (minimal) is the defining characteristic. Closing that gap — especially items 1-3 from the recommendations — would significantly improve agent iterability at low cost.
