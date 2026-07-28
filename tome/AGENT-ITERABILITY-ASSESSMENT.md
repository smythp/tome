# Tome Agent Iterability Assessment

**Date:** 2026-05-03  
**Assessor:** boffin (technical architect)  
**Method:** Static analysis of 18 test files, configs, docs, and project structure  
**Scope:** Can an AI agent confidently iterate on this codebase?

---

## Recommendation

**Tome is 70% of the way to excellent agent iterability.** The test architecture is genuinely impressive — three-tier testing (regular/oracle/gremlin) with Hypothesis property testing is rare and valuable. But three specific issues would cause an agent to waste significant cycles:

1. **Oracle tests are designed to fail** — an agent running `pytest` gets red, tries to "fix" intentional failures
2. **Conflicting pytest configs** — `pytest.ini` and `pyproject.toml` disagree on test discovery paths
3. **No standard entry points** — no Makefile, no way to run "just the stable tests"

Fix these three things and you have one of the most agent-friendly Python codebases I've seen.

---

## What's Working Well

### Three-Tier Test Strategy ✅
This is the standout strength. Each RSP module has:
- **Regular tests** (`test_store.py`, `test_mark.py`, etc.) — comprehensive CRUD and behavior tests
- **Oracle tests** (`test_store_oracle.py`, etc.) — Hypothesis property-based tests verifying invariants
- **Gremlin tests** (`test_store_gremlin.py`, etc.) — adversarial tests trying to break things

This is unusual and excellent. Most codebases have one tier at best.

### Test-First Design ✅
Tests are explicitly written before implementation (noted in docstrings). Class-based organization (`TestBasicGet`, `TestBasicSet`, `TestConstruction`) makes navigation easy.

### Protocol-Based DI ✅
Dependency injection via protocols makes mocking natural. Every test file creates lightweight mocks without framework overhead.

### No Real I/O in Tests ✅
- `MockListener` replaces pynput keyboard
- `text` handler replaces espeak TTS
- `tmp_path` for databases
- No network, no filesystem side effects

### Agentic Testing Documentation ✅
`docs/agentic-testing.md` explicitly documents how to test without a real keyboard — MockListener usage, direct `mode.handle()` calls, KeyEvent construction. This is agent-aware design.

### Test Volume and Coverage ✅
~7,600 lines of test code across 18 files. Per-module coverage is thorough:
- `store/test_store.py` — 756 lines, comprehensive CRUD
- `mark/test_mark.py` — 1,210 lines, position tracking
- `mode/test_mode.py` — 1,093 lines, state machine
- `listener/test_listener.py` — 732 lines, event construction

---

## Critical Issues for Agent Iteration

### Issue 1: Intentionally-Failing Oracle Tests 🔴
**Severity: CRITICAL for agents**

`mode/test_mode_oracle.py` line 5:
```
All tests should FAIL - they expose actual issues in the code.
```

These tests document **real bugs** (closure capture in `get_state`, race conditions in `switch()`, etc.) by writing tests that fail against the current implementation. This is a valid technique for humans who read the docstrings. For an agent, it's a trap:

1. Agent runs `pytest`
2. Sees failures in `test_mode_oracle.py`
3. Attempts to fix the "bugs" by modifying `mode.py`
4. Either breaks working code or wastes cycles on intentional behavior
5. Can't distinguish "test suite is green" from "some failures are expected"

**Fix:** Mark these tests with `@pytest.mark.xfail(reason="Known bug: closure capture in get_state")`. They still document the bug, still run, but pytest reports them as `xfail` (expected failure) rather than failure. The suite goes green.

Alternatively, move them to a `known_bugs/` directory excluded from default test discovery.

### Issue 2: Conflicting pytest Configurations 🔴
**Severity: HIGH for agents**

`pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["store", "teller", "mark", "mode", "listener"]
```

`pytest.ini`:
```ini
testpaths = .
```

`pytest.ini` takes precedence over `pyproject.toml` in pytest's config resolution. This means:
- The `pyproject.toml` config is **silently ignored**
- `testpaths = .` discovers ALL test files, including root-level `test_integration.py`, `test_handlers.py`, `test_wire.py`
- An agent reading `pyproject.toml` would believe tests are scoped to module directories
- An agent reading `pytest.ini` gets the truth but doesn't know about the conflict

**Fix:** Delete `pytest.ini` and consolidate all config into `pyproject.toml`. Add the markers to `pyproject.toml` as well. One source of truth.

### Issue 3: No Standard Entry Points 🟡
**Severity: MEDIUM-HIGH for agents**

There's no Makefile, no `scripts/` directory, no documented way to:
- Run only stable/passing tests
- Run only fast tests (skip Hypothesis)
- Run only a specific module's tests
- Lint or type-check

An agent needs to know: "What command do I run to verify my change didn't break anything?" Currently the answer is `pytest`, but that includes intentionally-failing tests and Hypothesis tests that can be slow.

**Fix:** Add a `Makefile` with:
```makefile
test:           # Fast, stable tests only
    pytest -x --ignore=mode/test_mode_oracle.py -p no:hypothesis

test-full:      # Everything including property tests
    pytest --ignore=mode/test_mode_oracle.py

test-all:       # Including known-failing oracle tests
    pytest

test-module:    # Single module: make test-module M=store
    pytest $(M)/

lint:
    ruff check .
```

---

## Secondary Issues

### Issue 4: Duplicate Mock Definitions 🟡
**Severity: MEDIUM — drift risk**

`MockStore` is defined independently in:
- `mode/test_mode.py` — returns `str | None` from `get()`
- `mode/test_mode_syndic.py` — has `get(key, default=None)` signature with call tracking
- `mode/test_mode_oracle.py` — minimal `get(key)` returning `None`
- `mark/test_mark.py` — returns dict entries with `id`, `buffer_id`, `content`, `type`

Similarly, `MockTeller` has 3 different implementations:
- `mode/test_mode.py` — captures `spoken: list[str]`
- `mode/test_mode_syndic.py` — has `tell()` and `clear()` methods (different API!)
- `mode/test_mode_oracle.py` — minimal `speak()` and `stop()`

The syndic version uses `tell()` while the real Teller uses `speak()`. This is a latent bug — the syndic mock doesn't match the protocol.

**Fix:** Create `conftest.py` files with shared fixtures, or a `test_utils.py` module. At minimum, ensure all mocks match the actual Protocol interface.

### Issue 5: Gremlin Tests with Ambiguous Pass/Fail 🟡
**Severity: MEDIUM — agent confusion**

Some gremlin tests document behavior without clear expectations:
```python
def test_get_sleeps_forever(self):
    """BROKE: path() blocks if store.get() sleeps."""
    # BROKE: path() has no timeout, blocks forever
    # This test would hang - commented out for safety
```

An agent sees a test that's commented out, labeled "BROKE", and doesn't know what to do. Is this a TODO? A known issue? Should it be fixed?

**Fix:** Either:
- `@pytest.mark.skip(reason="Would hang — path() has no timeout")` — visible in test output
- Move to a `known_issues.md` document
- Add a non-blocking version with `pytest.mark.timeout`

### Issue 6: No Linting or Type Checking 🟡
**Severity: MEDIUM — missing feedback loop**

No ruff, flake8, mypy, or pyright config. An agent can introduce style violations or type errors with no automated feedback.

**Fix:** Add ruff (fast, modern, minimal config):
```toml
# pyproject.toml
[tool.ruff]
line-length = 100
select = ["E", "F", "W"]
```

### Issue 7: Test Markers Defined But Unused 🟢
**Severity: LOW — missed opportunity**

`pytest.ini` defines markers (`db`, `ui`, `keyboard`, `clipboard`, `integration`) but I found no `@pytest.mark.db` or similar in any test file. These markers would enable selective test runs.

**Fix:** Apply markers to tests, especially:
- `@pytest.mark.slow` for Hypothesis tests
- `@pytest.mark.integration` for root-level test files
- `@pytest.mark.xfail` for known-bug oracle tests

---

## Agent Workflow Capability Matrix

| Workflow | Status | Notes |
|----------|--------|-------|
| Run tests | ⚠️ Partial | Works but includes intentional failures |
| Run fast tests only | ❌ No | No way to skip Hypothesis |
| Run stable tests only | ❌ No | No way to exclude oracle failures |
| Lint before commit | ❌ No | No linter configured |
| Type check | ❌ No | No type checker configured |
| Verify single module | ⚠️ Manual | `pytest store/` works but undocumented |
| Set up from scratch | ✅ Yes | `pyproject.toml` + `uv.lock` exist |
| Understand test intent | ⚠️ Partial | Good names, but oracle/gremlin intent unclear |
| Know what's green | ❌ No | Can't distinguish expected vs unexpected failures |

---

## Prioritized Action Plan

### Phase 1: Make the Suite Green (1 hour)
1. Add `@pytest.mark.xfail(reason="...")` to all intentionally-failing oracle tests
2. Delete `pytest.ini`, consolidate config into `pyproject.toml`
3. Verify `pytest` produces a clean green run

### Phase 2: Add Standard Entry Points (30 minutes)
4. Create `Makefile` with `test`, `test-full`, `test-all`, `test-module` targets
5. Document in `CLAUDE.md`: "Run `make test` to verify changes"

### Phase 3: Strengthen Feedback Loops (1 hour)
6. Add ruff config to `pyproject.toml`
7. Add `make lint` target
8. Extract shared mock fixtures into `conftest.py` files
9. Fix `MockTeller` in `test_mode_syndic.py` to match actual protocol (`speak()` not `tell()`)

### Phase 4: Polish (optional)
10. Apply test markers (`@pytest.mark.slow`, `@pytest.mark.integration`)
11. Convert commented-out gremlin tests to proper `skip` markers
12. Add mypy or pyright for type checking

---

## Comparison to Previous Assessment

The Phase 4 assessment (`phase4-agent-iterability-findings.md`) correctly identified:
- ✅ Missing linting
- ✅ Missing type checking  
- ✅ Missing Makefile
- ✅ Need for `pyproject.toml` improvements

But missed:
- ❌ The intentionally-failing oracle tests (the #1 agent trap)
- ❌ The pytest.ini vs pyproject.toml conflict
- ❌ Mock definition drift across test files
- ❌ The syndic MockTeller protocol mismatch

The previous assessment also referenced "kree codebase" (wrong project name) and recommended a `requirements.txt` even though `pyproject.toml` and `uv.lock` already exist. This suggests it may have been working from incomplete context.

---

## Bottom Line

Tome has excellent test architecture — the three-tier strategy with property-based testing is genuinely good. The gap is entirely in the **feedback loop ergonomics**: an agent can't run `pytest` and trust a green result because intentional failures poison the signal. Fix the oracle tests, consolidate the config, and add a Makefile, and this becomes a codebase where agents can iterate with confidence.

---

*Assessment by boffin agent — static analysis only (pytest execution unavailable during assessment)*
