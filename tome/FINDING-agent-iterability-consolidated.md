# Consolidated Agent Iterability Assessment

**Date:** 2026-05-02
**Assessor:** boffin agent (technical architect)

---

## Verdict: Strong Foundation, Missing Scaffolding

Tome has excellent test infrastructure (781 test functions, property-based testing, dedicated agentic testing docs) but lacks the outer-loop tooling that enables confident agent iteration.

## Feedback Loops

### ✅ Testing — Strong
- 781 test functions across 5 RSP modules (store, teller, mark, mode, listener)
- pytest + hypothesis for property-based testing
- Markers: `db`, `ui`, `keyboard`, `clipboard`, `integration`
- Co-located tests (e.g., `store/test_store.py`)
- `docs/agentic-testing.md` explicitly documents MockListener and direct `mode.handle()` approaches
- Text teller handler (`get_handler("text")`) enables headless testing without espeak/TTS

### ✅ Build/Install — Works
- `pyproject.toml` with setuptools backend
- `pip install -e .[dev]` installs pytest + hypothesis
- `.venv` present with Python 3.12

### ⚠️ pytest Config Conflict — Real Footgun
- `pytest.ini`: `testpaths = .` (discovers ALL tests including root-level)
- `pyproject.toml`: `testpaths = ["store", "teller", "mark", "mode", "listener"]` (RSP modules only)
- **pytest.ini takes precedence** — running `pytest` discovers root-level tests (test_handlers.py, test_integration.py, test_wire.py) which may have different expectations
- Fix: Remove pytest.ini, consolidate markers into pyproject.toml

### ❌ Linting — Missing
- No ruff, flake8, pylint, black, or isort config
- No automated style feedback for agents

### ❌ Type Checking — Missing
- No mypy or pyright config
- No `py.typed` marker

### ❌ Unified Command — Missing
- No Makefile or justfile
- No `make check` equivalent
- Agent must know raw commands

### ❌ CI/CD — Missing
- No GitHub Actions or similar

## Agent Workflow Matrix

| Task | Possible? | Command |
|------|-----------|----------|
| Install deps | ✅ Yes | `pip install -e .[dev]` |
| Run all tests | ✅ Yes | `pytest` |
| Run module tests | ✅ Yes | `pytest store/` |
| Test without TTS | ✅ Yes | Text handler + MockListener |
| Check style | ❌ No | No linter configured |
| Format code | ❌ No | No formatter configured |
| Type check | ❌ No | No type checker configured |
| Verify all | ❌ No | No unified command |

## Positive Finding: Agentic Testing Docs

`docs/agentic-testing.md` is a standout — it explicitly documents two testing approaches for agents:
1. **MockListener** — full integration testing with injected KeyEvents
2. **Direct mode.handle()** — unit testing handlers in isolation

This is unusually agent-friendly for a codebase of this size.

## Recommendations (Priority Order)

1. **Remove pytest.ini** — consolidate into pyproject.toml, resolve the config conflict
2. **Add Makefile** with `setup`, `test`, `lint`, `check` targets
3. **Add ruff** for linting/formatting (fast, modern, single tool)
4. **Optionally add mypy** for type safety

---
*Note: skein tool unavailable in this environment — findings saved to file*
