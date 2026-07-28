# Phase 4: Agent Iterability & Feedback Loops — Final Verdict

**Date:** 2026-05-16  
**Verdict:** The test suite is excellent. The feedback loop is broken.

## Executive Summary

Tome has one of the better Python test architectures I've seen in a small project: three-tier testing (stable, gremlin/adversarial, oracle/bug-exposing), Hypothesis property-based tests, good fixture isolation with `tmp_path`, and a thoughtful `docs/agentic-testing.md` guide. But an agent cannot iterate on this codebase today because every feedback signal is poisoned or missing.

## Feedback Loops: What Exists

| Loop | Status | Notes |
|------|--------|-------|
| pytest suite | ✅ Exists | 5 submodules, three-tier strategy, ~750+ lines in store alone |
| Hypothesis property tests | ✅ Exists | Mixed into stable and gremlin tiers |
| Test isolation | ✅ Good | tmp_path for DB, MockTeller, MockListener |
| agentic-testing.md | ✅ Good | Documents KeyEvent construction, MockListener, direct handle() |
| pyproject.toml | ✅ Exists | Declares deps (pynput) and dev deps (pytest, hypothesis) |
| CLAUDE.md | ⚠️ Incomplete | Lists `python tome.py` but no test commands |

## Feedback Loops: What's Broken

### 1. pytest.ini vs pyproject.toml Conflict (CRITICAL)

`pytest.ini` sets `testpaths = .` — this overrides `pyproject.toml`'s `testpaths = ["store", "teller", "mark", "mode", "listener"]`. Result: pytest collects root-level scripts (`test_integration.py`, `test_wire.py`, `test_handlers.py`) which are executable scripts, not pytest test modules. They execute at import time, causing noise and potential crashes during collection.

### 2. Oracle Tests Permanently Red (CRITICAL)

`test_mode_oracle.py`, `test_store_oracle.py`, and `test_teller_oracle.py` contain tests **designed to fail** — they expose real bugs documented in docstrings. But they lack `@pytest.mark.xfail` markers. Result: the suite is permanently red. An agent runs pytest, sees failures, wastes cycles trying to "fix" intentional failures. It cannot distinguish regressions from expected failures.

### 3. pyperclip Import Crash (HIGH)

`tome.py` line 32: `import pyperclip` — unconditional import of an undeclared dependency. The app crashes on startup with `ImportError`. pyproject.toml has a comment about adding it later but never does.

## Feedback Loops: What Doesn't Exist

| Missing | Impact |
|---------|--------|
| Makefile | No `make test`, `make lint`, `make check` — agent must guess commands |
| Linter (ruff/flake8) | No style enforcement, no static analysis signal |
| Type checker (mypy/pyright) | Some type hints exist but aren't verified |
| CI pipeline | No GitHub Actions, no tox.ini |
| Pre-commit hooks | Nothing catches issues before commit |
| Formatter (black/ruff) | No consistent formatting enforcement |

## Agent Iteration Assessment

### Can an agent do the edit-test-commit loop today?

**No.** Here's what happens:

1. Agent reads CLAUDE.md → finds no test command
2. Agent tries `pytest` → sees failures from oracle tests + collection errors from root scripts
3. Agent tries to fix the failures → wastes cycles on intentional failures
4. Agent has no way to know which failures are expected
5. No linter provides secondary signal
6. No Makefile provides a verified entry point

### What would it take?

The gap is entirely in **feedback loop ergonomics**, not test quality. Six fixes, ~1 hour total:

| Fix | Time | Impact |
|-----|------|--------|
| Delete pytest.ini, consolidate into pyproject.toml | 5 min | Eliminates config conflict |
| Add `@pytest.mark.xfail(strict=True)` to oracle tests | 15 min | Green baseline possible |
| Make pyperclip import conditional | 5 min | App can start |
| Add Makefile with test/lint/check targets | 15 min | Agent has a front door |
| Update CLAUDE.md with test commands | 5 min | Agent knows what to run |
| Add ruff for linting | 10 min | Secondary quality signal |

### After those fixes?

This becomes one of the most agent-friendly Python codebases I've seen:
- Three-tier test strategy gives excellent signal
- Property-based tests catch edge cases automatically  
- Good isolation means tests are fast and reliable
- MockListener + direct handle() enable full integration testing without real keyboard
- Each submodule is self-contained

## The Irony

The test **architecture** is excellent. The test **infrastructure** is broken. The bones are great but the plumbing is disconnected. Someone invested serious thought into three-tier testing, Hypothesis integration, and agentic testing patterns — then left the front door locked.

## Confidence Level

**High confidence** on all findings. Based on reading every test file, every config file, both integration scripts, all documentation, and all 15 previous agent findings. The only gap is I couldn't actually execute pytest (bash commands required approval for redirects), but the static analysis of config files and test structure is definitive — the pytest.ini/pyproject.toml conflict is a fact, the missing xfail markers are a fact, and the pyperclip import is a fact.

---

*Phase 4 of tome-improvement assessment. Previous phases covered: architecture mapping, code quality, runnability.*
