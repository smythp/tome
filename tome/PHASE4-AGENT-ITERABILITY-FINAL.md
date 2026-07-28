# Phase 4: Agent Iterability Assessment - Final Report

## Verdict: YES, agents can iterate — with meaningful caveats

The test infrastructure is **unusually strong** for a project of this size. Three-tier testing (unit, gremlin/adversarial, oracle/property-based) with Hypothesis is exceptional. But the feedback loop has blind spots that slow agent iteration.

---

## What Exists (Strengths)

### Test Suite Architecture
- **Unit tests per RSP**: store (756 lines), mark (1210 lines), mode (1093 lines), listener (732 lines), teller (501 lines)
- **Gremlin/adversarial tests**: mark/test_gremlin_attacks.py, store/test_store_gremlin.py, teller/test_teller_gremlin.py — chaos testing that exploits assumptions
- **Oracle/property tests**: store/test_store_oracle.py, mode/test_mode_oracle.py, teller/test_teller_oracle.py — Hypothesis-based invariant verification
- **Syndic tests**: mode/test_mode_syndic.py — comprehensive state machine testing
- **Integration tests**: test_wire.py (smoke test), test_integration.py (full user session)
- **Handler tests**: test_handlers.py (45.8KB — substantial coverage of the main application logic)

### Mock Infrastructure
- **MockListener**: Injects KeyEvent objects without pynput/display server
- **MockStore**: In-memory key-value store for isolated testing
- **MockTeller**: Captures speak calls for assertion
- **TextHandler**: Real teller handler that prints to stdout instead of speaking (replaces espeak dependency)

### Documentation
- **docs/agentic-testing.md**: Explicit guidance for agents — MockListener usage, direct mode.handle() patterns, KeyEvent construction, full test setup examples
- **CLAUDE.md**: Project conventions, commands, code style, structure
- **Test-first culture**: Comments like "Tests written BEFORE implementation" in test files

### Dependency Isolation
- Tests don't require espeak (text handler)
- Tests don't require pynput/X11 (MockListener)
- Tests don't require clipboard (pyperclip commented out in pyproject.toml)
- Each RSP module is independently testable

---

## What's Missing (Weaknesses)

### 1. No Static Analysis Tooling (HIGH IMPACT)
- No ruff, flake8, pylint, or mypy configuration
- No black, isort, or autopep8 for formatting
- No pre-commit hooks
- **Impact**: Agent can't quickly catch syntax errors, unused imports, type mismatches, or style drift without running the full test suite

### 2. No Task Runner / Makefile (MEDIUM IMPACT)
- No `make test`, `make lint`, `make check` entry points
- Agent must know to activate `.venv` and run `pytest` directly
- No standard commands documented beyond `python tome.py`
- **Impact**: Higher cognitive overhead for agents; must discover execution patterns

### 3. Conflicting Test Configs (MEDIUM IMPACT)
- `pytest.ini`: `testpaths = .` (discovers ALL test files in project root)
- `pyproject.toml`: `testpaths = ["store", "teller", "mark", "mode", "listener"]` (only RSP modules)
- pytest.ini takes precedence, but the conflict is confusing
- **Impact**: Agent may run different test subsets depending on which config they read

### 4. No Coverage Reporting (LOW-MEDIUM IMPACT)
- No pytest-cov configuration
- Agent can't verify it tested what it changed
- **Impact**: Silent gaps in test coverage go undetected

### 5. No CI/CD Pipeline (LOW IMPACT for solo dev)
- No .github/workflows, no CI scripts
- No automated gating before merge
- Agent must run tests manually
- **Impact**: No safety net; all quality assurance is manual

### 6. Integration Tests Aren't Proper pytest (LOW IMPACT)
- test_wire.py and test_integration.py use `print()`/`assert` patterns, not pytest conventions
- They work as scripts but don't integrate with pytest's reporting
- **Impact**: `pytest` may not report their failures clearly

---

## The Agent Feedback Loop

```
Step                          Status    Speed
─────────────────────────────────────────────
1. Read code (files_read)     ✅ great   instant
2. Understand structure        ✅ great   instant (CLAUDE.md, agentic-testing.md)
3. Write tests first           ✅ good    n/a (culture documented)
4. Run tests (pytest)          ✅ works   ~5-30s (needs .venv activation)
5. Check regressions           ✅ works   ~30-60s (full suite)
6. Verify style/types          ❌ absent  n/a (no tooling)
7. Verify coverage             ❌ absent  n/a (no tooling)
8. Automated gate              ❌ absent  n/a (no CI)
```

The test suite IS the primary feedback loop, and it's a strong one. Steps 1-5 are well-supported. Steps 6-8 are missing entirely.

---

## Recommendations (Priority Order)

### 1. Add ruff (5 minutes, HIGH value)
```toml
# pyproject.toml addition
[tool.ruff]
line-length = 120
select = ["E", "F", "W", "I"]
```
- Catches syntax errors, unused imports, style issues in <1s
- Single tool replaces flake8 + isort + pyflakes
- Zero config needed to start, then tune

### 2. Add a Makefile (10 minutes, HIGH value)
```makefile
.PHONY: test lint check

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check .

check: lint test

test-unit:
	.venv/bin/pytest store/ teller/ mark/ mode/ listener/

test-all:
	.venv/bin/pytest .
```
- Standard entry points agents and humans both understand
- Documents the "right" way to run things

### 3. Reconcile pytest configs (5 minutes, MEDIUM value)
- Delete pytest.ini, consolidate into pyproject.toml
- Or: update pytest.ini to match pyproject.toml's testpaths
- Pick one source of truth

### 4. Add mypy (15 minutes, MEDIUM value)
- The code already uses type hints extensively
- mypy would catch type mismatches the tests miss
- Start with `--ignore-missing-imports` for gradual adoption

### 5. Add pytest-cov (5 minutes, LOW-MEDIUM value)
```toml
[tool.pytest.ini_options]
addopts = "--cov=store --cov=teller --cov=mark --cov=mode --cov=listener"
```

### 6. Convert integration tests to pytest (30 minutes, LOW value)
- Wrap test_wire.py and test_integration.py in pytest test classes
- Keep the same logic, just use pytest assertions and fixtures

---

## Summary

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Test depth | ★★★★★ | Three tiers: unit, gremlin, oracle |
| Test isolation | ★★★★★ | Full mock infrastructure, no external deps |
| Agent documentation | ★★★★☆ | agentic-testing.md is excellent; CLAUDE.md is adequate |
| Feedback speed | ★★★☆☆ | Tests work but no fast lint; must run full suite |
| Static analysis | ★☆☆☆☆ | Nothing configured |
| Task runner / DX | ★★☆☆☆ | No Makefile, no standard commands |
| CI/CD gating | ★☆☆☆☆ | None |
| **Overall iterability** | **★★★☆☆** | Strong foundation, weak tooling shell |

The core is excellent — the test suite itself is better than most production codebases. What's missing is the *shell* around it: the linting, formatting, type checking, coverage, and automation that turns a good test suite into a fast, reliable feedback loop for agents.

Adding ruff + Makefile (15 minutes of work) would jump the overall rating to ★★★★☆.
