# Phase 4 Finding: Agent Iterability Assessment

**Date:** 2026-01-27
**Phase:** 4 of tome-improvement investigation
**Question:** Can an agent iterate on this codebase? What feedback loops exist?

---

## Executive Summary

**YES, an agent can iterate on this codebase, but with significant friction.**

The test infrastructure is excellent (781 test functions!), but there's no unified "verify everything" command. An agent must manually run pytest and hope for the best on style/types.

---

## Feedback Loops Assessment

### 1. Testing Loop - STRONG ✅

- **781 test functions** across the codebase
- pytest.ini properly configured with testpaths and markers
- hypothesis for property-based testing
- Markers: `db`, `ui`, `keyboard`, `clipboard`, `integration`
- Command: `pytest`

### 2. Build/Install Loop - RECENTLY FIXED ✅

- pyproject.toml now exists (created by agent boffin_0034)
- Can install with `pip install -e .[dev]`
- Dependencies: pynput, pytest, hypothesis

### 3. Lint/Format Loop - MISSING ❌

- No ruff, flake8, black, or isort config
- No way to verify code style consistency
- Agent cannot auto-format or check formatting

### 4. Type Check Loop - MISSING ❌

- No mypy.ini or pyrightconfig.json
- Can't verify type safety
- No py.typed marker

### 5. Unified Command Loop - MISSING ❌

- No Makefile
- No single `make check` to run all verifications
- Agent must remember multiple separate commands

---

## What's Needed for Frictionless Agent Iteration

### Priority 1: Add Makefile

```makefile
.PHONY: setup test lint check

setup:
	python -m venv .venv
	.venv/bin/pip install -e .[dev]

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

check: lint test
	@echo "All checks passed!"
```

### Priority 2: Add ruff config to pyproject.toml

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
```

### Priority 3 (Optional): Add mypy config

```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_ignores = true
```

---

## Key Insight

The test coverage is impressive - 781 tests show someone cared deeply about correctness. But the project lacks the "outer loop" tooling that lets an agent confidently make changes:

| Task | Can agent do it? | Command |
|------|------------------|----------|
| Install deps | ✅ Yes | `pip install -e .[dev]` |
| Run tests | ✅ Yes | `pytest` |
| Check style | ❌ No | (no tool configured) |
| Format code | ❌ No | (no tool configured) |
| Type check | ❌ No | (no tool configured) |
| Verify all | ❌ No | (no unified command) |

---

## Recommendation

Add a Makefile with `make check` as the first priority. This gives agents (and humans) a single command to verify everything works. Then add ruff for linting/formatting.

The bones are good - the test suite is excellent. The project just needs the scaffolding to let agents iterate confidently.
