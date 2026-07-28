# Feedback Loops & Agent Iterability Assessment

**Date**: 2026-05-22  
**Method**: Static analysis (test execution not available)  
**Scope**: All feedback loops available to agents working on this codebase

---

## Executive Summary

**Verdict**: The test suite is strong and comprehensive, but it's the *only* feedback loop. No linter, no type checker, no CI, no Makefile. An agent can iterate effectively using `pytest`, but has zero guardrails against style drift, type errors, or regressions that slip past the test suite.

**Agent iterability rating**: 6/10 — good test coverage compensates for missing tooling, but the gap creates real risk.

---

## Feedback Loop Assessment

### 1. Tests — STRONG ✅

**15 test files** across the codebase with multi-tier coverage:

| Tier | Files | Purpose |
|------|-------|---------|
| Unit | `test_store.py`, `test_mark.py`, `test_mode.py`, `test_listener.py`, `test_teller.py`, `test_handlers.py` | Core functionality |
| Gremlin | `test_store_gremlin.py`, `test_gremlin_attacks.py`, `test_teller_gremlin.py` | Chaos/fuzz testing |
| Oracle | `test_store_oracle.py`, `test_mode_oracle.py`, `test_teller_oracle.py` | Property-based (Hypothesis) |
| Syndic | `test_mode_syndic.py` | Cross-component coordination |
| Integration | `test_integration.py`, `test_wire.py` | End-to-end wiring |

**Strengths:**
- Tests co-located with each RSP module (store/, mark/, mode/, listener/, teller/)
- Test-first design philosophy (documented in test_store.py docstring)
- pytest + Hypothesis for property-based testing
- Markers for categorization: `@pytest.mark.db`, `@pytest.mark.ui`, `@pytest.mark.keyboard`, `@pytest.mark.clipboard`, `@pytest.mark.integration`
- Fixtures use `tmp_path` for database isolation — no shared state between tests
- Massive test code volume: ~300KB+ of test code across all files

**Weaknesses:**
- pytest.ini (`testpaths = .`) conflicts with pyproject.toml (`testpaths = ["store", "teller", "mark", "mode", "listener"]`). pytest.ini wins, which means root-level test files (test_handlers.py, test_integration.py, test_wire.py) ARE collected, but this conflict is confusing.
- No test count available without execution, but file sizes suggest 200-400+ test functions

### 2. Build — MINIMAL ⚠️

- Pure Python, no compilation step
- `pyproject.toml` with setuptools backend, but no `setup.py`
- Virtual environment present (`.venv/` with Python 3.12)
- Dependencies: `pynput>=1.7.0` (runtime), `pytest>=7.0.0` + `hypothesis>=6.0.0` (dev)
- `uv.lock` present — suggests `uv` is the package manager
- No build validation — an agent can break imports and only discover it when tests run

### 3. Lint — ABSENT ❌

- No ruff, flake8, pylint, or any linter configured
- No formatter (black, autopep8, yapf)
- No import sorting (isort)
- CLAUDE.md specifies style conventions (4-space indent, snake_case, etc.) but nothing enforces them
- **Impact**: Agents can introduce style drift silently. Over many agent sessions, code style will diverge.

### 4. Type Checking — ABSENT ❌

- No mypy, pyright, or pytype configuration
- No `py.typed` marker
- No type stubs
- From code samples reviewed, type hints appear minimal or absent
- **Impact**: Type errors are caught only at runtime or by tests. Refactoring is riskier.

### 5. CI — ABSENT ❌

- No `.github/workflows/` directory
- No Makefile
- No pre-commit hooks (`.pre-commit-config.yaml`)
- No tox.ini
- **Impact**: No automated test runs on push. Regressions can be committed without detection.

---

## Agent Iterability Assessment

### What Works Well for Agents

1. **Single-command feedback**: `.venv/bin/pytest` runs the full suite. Simple, fast feedback.
2. **Co-located tests**: Agent modifying `store/store.py` can immediately run `store/test_store.py`.
3. **CLAUDE.md exists**: Agents get project conventions immediately.
4. **ARCHITECTURE.md is detailed**: 474-line architecture document with component maps, data flow, and dependency graphs.
5. **Minimal dependencies**: Only `pynput` at runtime. Low chance of dependency hell.
6. **Test isolation**: `tmp_path` fixtures mean tests don't interfere with each other or production data.
7. **Multi-tier testing**: Gremlin tests catch edge cases that unit tests miss. Oracle tests catch invariant violations.

### What Hurts Agent Iterability

1. **No Makefile / task runner**: Agent must discover how to run things. No `make test`, `make lint`, `make check`.
2. **No lint = silent style drift**: Agent changes compile and pass tests but introduce inconsistent style.
3. **Large monolithic files**: `handlers.py` (42.3KB), `reference.py` (81KB), `test_handlers.py` (45.8KB). Hard for agents to hold in context.
4. **Config conflict**: pytest.ini vs pyproject.toml testpaths disagreement is a trap.
5. **Global state**: CLAUDE.md explicitly mentions `global` keyword usage. Global state makes reasoning about side effects harder.
6. **No type hints**: Agent can't verify interface contracts without running tests.
7. **No pre-commit hooks**: Agent can commit broken code with no safety net.

### Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Style drift across agent sessions | High | Medium | Add ruff |
| Breaking import chains | Medium | High | Add smoke test or type checker |
| pytest config confusion | Medium | Low | Consolidate to pyproject.toml, delete pytest.ini |
| Regression in untested paths | Low | High | Already mitigated by extensive test suite |
| Agent modifying wrong file due to monoliths | Medium | Medium | Consider splitting large files |

---

## Recommendations

### Quick Wins (< 30 min each)

1. **Add a Makefile** with `test`, `test-fast`, `lint` targets. Gives agents a standard entry point.
2. **Add ruff** — single tool for linting + formatting. Add `[tool.ruff]` to pyproject.toml.
3. **Delete pytest.ini** — consolidate all pytest config into pyproject.toml. Add root test files to testpaths.
4. **Add pre-commit hooks** — `.pre-commit-config.yaml` with ruff + pytest smoke test.

### Medium Effort (1-2 hours)

5. **Add GitHub Actions CI** — run `pytest` on push. Even a single workflow file adds a critical safety net.
6. **Add basic type hints** to public APIs — enables mypy or pyright for interface verification.
7. **Split handlers.py** — 42KB monolith could become per-handler modules under `handlers/`.

### Strategic

8. **Add mypy with gradual typing** — start with `--ignore-missing-imports` and strict on new code.

---

## Conclusion

The test suite is the crown jewel of this codebase's feedback system — multi-tier, property-based, well-structured. But it operates alone. Adding ruff (5 min), a Makefile (10 min), and deleting pytest.ini (1 min) would materially improve agent iterability for under 20 minutes of work.
