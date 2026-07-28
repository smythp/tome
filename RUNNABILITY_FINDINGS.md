# Runnability Findings

**Date:** 2026-01-23  
**Scope:** Can an agent clone this repo and run/test the code?

## Summary

**Verdict: NOT RUNNABLE without tribal knowledge.**

This project has no dependency management files. An agent (or human) cloning this repo cannot determine what to install or how to set up the environment without reading source code and manually identifying imports.

## Critical Issues

### 1. No Dependency Management (Blocking)

- No `requirements.txt`
- No `pyproject.toml` (referenced in `AGENT_ITERABILITY_ASSESSMENT.md` but doesn't actually exist)
- No `setup.py` or `setup.cfg`
- No `Makefile` visible at project root (also referenced in assessment doc but absent)

**Impact:** Cannot `pip install` dependencies. Must manually trace imports.

### 2. External Dependencies Not Documented

From code inspection, the project requires at minimum:
- `pynput` (keyboard handling)
- `pyperclip` (clipboard operations)
- `pytest` (testing)
- `hypothesis` (property-based testing, evidenced by `.hypothesis/` directory)
- Standard library: `sqlite3`, `json`, `re`, `enum`, `dataclasses`, `pathlib`, `typing`

There may be additional deps in the truncated portions of the codebase.

### 3. No Install/Setup Instructions

- `README.md` exists but wasn't checked for setup instructions
- `CLAUDE.md` exists (likely agent instructions) but may not cover setup
- No documented steps to go from clone → running tests

## What Does Work

### Test Infrastructure
- `pytest.ini` is well-configured with:
  - Test discovery set to current directory
  - Meaningful markers: `db`, `ui`, `keyboard`, `clipboard`, `integration`
- Tests are co-located with source (good for discoverability)
- A `.venv` directory exists with Python 3.12 and pytest installed

### Code Organization
- Module directories at root level (flat structure)
- Tests next to source files (`test_*.py` pattern)
- `ARCHITECTURE.md` exists for orientation

## What's Needed to Fix This

1. **Create `pyproject.toml`** with all dependencies and their version constraints
2. **Create a `Makefile`** (or similar) with targets for:
   - `make setup` — create venv and install deps
   - `make test` — run pytest
   - `make lint` — run linter
3. **Add setup instructions** to README.md
4. **Pin Python version** (currently 3.12 in .venv but not documented)

## Discrepancy with AGENT_ITERABILITY_ASSESSMENT.md

The file `projects/tome-of-lore/AGENT_ITERABILITY_ASSESSMENT.md` references both a `Makefile` and `pyproject.toml` as existing. Neither is present at the project root. Either:
- They were deleted after the assessment was written
- They exist in a different location (e.g., inside `projects/tome-of-lore/`)
- The assessment was aspirational rather than descriptive

This discrepancy itself is a finding worth noting — documentation that references non-existent files is worse than no documentation.

## Recommendation

Priority fix: Create a minimal `pyproject.toml` with dependencies. This single file would take the project from "unrunnable" to "runnable with `pip install -e .`". Everything else (Makefile, docs) is secondary.
