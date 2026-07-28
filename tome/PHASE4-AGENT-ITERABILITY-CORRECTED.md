# Phase 4: Agent Iterability & Feedback Loops — Corrected Assessment

**Date:** 2026-05-15  
**Method:** Static analysis (bash/skein unavailable)  
**Key contribution:** Corrects a factual error in all prior assessments regarding oracle tests

---

## Critical Correction: Oracle Tests Are NOT All Intentionally Failing

Every prior assessment (PHASE4-FEEDBACK-LOOPS.md, PHASE4-FEEDBACK-LOOPS-INDEPENDENT.md, FINDING-phase4-feedback-loops-final.md, AGENT-ITERABILITY-ASSESSMENT.md) makes the same error: they recommend adding `@pytest.mark.xfail` to **all three** oracle test files. This is wrong.

### The Three Oracle Files

| File | Type | Intent | xfail? |
|------|------|--------|--------|
| `mode/test_mode_oracle.py` | Edge case bug documentation | Docstring: "All tests should FAIL - they expose actual issues" | **YES** — these document real bugs |
| `store/test_store_oracle.py` | Hypothesis property-based testing | Docstring: "Property-based verification of Store invariants. Uses Hypothesis to verify mathematical properties hold for ALL inputs." | **NO** — these SHOULD pass |
| `teller/test_teller_oracle.py` | Hypothesis property-based testing | Docstring: "property-based verification using Hypothesis. Verify mathematical properties hold for ALL inputs." | **NO** — these SHOULD pass |

### Why This Matters

If an agent follows the prior recommendations and marks all oracle tests as xfail:
- `store/test_store_oracle.py` tests would be suppressed — hiding real regressions in Store invariants
- `teller/test_teller_oracle.py` tests would be suppressed — hiding real regressions in Handler protocol properties
- Only `mode/test_mode_oracle.py` actually needs xfail markers

The word "oracle" is used for two different testing patterns in this codebase:
1. **Bug oracle** (mode): Tests that encode known bugs as documentation. They FAIL to show the bugs exist.
2. **Property oracle** (store, teller): Tests that verify invariants must hold for ALL inputs. They SHOULD PASS.

---

## Feedback Loop Assessment

### Loops That Exist (Strengths)

| Loop | Signal Quality | Notes |
|------|---------------|-------|
| `pytest store/` | ✅ Excellent | 26.9KB tests + 12.3KB gremlin + 11.7KB Hypothesis oracle |
| `pytest mark/` | ✅ Excellent | 40.6KB tests + 16KB gremlin attacks |
| `pytest teller/` | ✅ Excellent | 17.1KB tests + gremlin + Hypothesis oracle |
| `pytest listener/` | ✅ Excellent | 22.8KB tests, MockListener for headless |
| `pytest mode/` | ⚠️ Poisoned by oracle | 32.3KB tests + 20.5KB syndic are excellent; 15.9KB oracle fails intentionally |
| Hypothesis property tests | ✅ Excellent | 30 constant files = extensively exercised |
| `docs/agentic-testing.md` | ✅ Excellent | Shows KeyEvent construction, MockListener, text handler |
| Protocol-based DI | ✅ Excellent | Natural mocking without frameworks |
| Text teller handler | ✅ Good | `get_handler("text")` for stdout-based testing |
| Git history | ✅ Good | Clean commits, proper .gitignore |

### Loops That Are Broken or Missing

| Missing/Broken Loop | Impact | Fix Effort |
|--------------------|--------|------------|
| pytest.ini vs pyproject.toml conflict | **Critical** — test discovery poisoned | 5 min (delete pytest.ini) |
| mode oracle tests permanently red | **High** — can't get green baseline | 15 min (add xfail to mode oracle ONLY) |
| No Makefile / task runner | **High** — agent must guess commands | 15 min |
| CLAUDE.md lacks test commands | **High** — no documented entry point | 5 min |
| test_integration.py executes at import | **Medium** — stdout noise during collection | 10 min (wrap in pytest functions) |
| test_wire.py executes at import | **Medium** — same issue | 10 min |
| No linter (ruff/flake8) | **Medium** — style drift undetected | 10 min |
| No type checker (mypy/pyright) | **Low** — Protocols help but not verified | 30 min |
| No CI/CD | **Low** — no external verification | 1+ hour |
| No coverage reporting | **Low** — can't see test gaps | 10 min |

### The Config Conflict Explained

```
pytest.ini:      testpaths = .          (discovers EVERYTHING)
pyproject.toml:  testpaths = ["store", "teller", "mark", "mode", "listener"]
```

pytest.ini takes precedence. This means `pytest` discovers:
- All module tests (correct) ✅
- `test_handlers.py` at root (46KB — probably fine) ⚠️
- `test_integration.py` at root (executes at import via print()) ❌
- `test_wire.py` at root (executes at import via print()) ❌
- `mode/test_mode_oracle.py` (intentionally fails) ❌

Result: agent sees stdout noise + expected failures + real results = can't determine baseline.

---

## Agent Iterability Verdict

| Scope | Score | Rationale |
|-------|-------|-----------|
| Per-module (store, mark, teller, listener) | **9/10** | Clean isolation, Protocol interfaces, comprehensive tests, agentic-testing.md |
| Per-module (mode) | **7/10** | Excellent test_mode.py + test_mode_syndic.py, but oracle poisons signal |
| Cross-module wiring | **6/10** | test_wire.py demonstrates it works, but is a script not a pytest test |
| Project-level | **3/10** | Config conflict, permanently red suite, no documented entry point |
| **Overall** | **6/10** | Excellent foundations undermined by project-level tooling gaps |

---

## Three Surgical Fixes (35 minutes total)

### Fix 1: Delete pytest.ini (5 min) — BIGGEST BANG FOR BUCK

```bash
rm pytest.ini
```

pyproject.toml already has correct config with `testpaths = ["store", "teller", "mark", "mode", "listener"]`. Deleting pytest.ini lets pyproject.toml take effect. Root-level scripts stop polluting discovery.

If root-level tests (test_handlers.py) should also run, add the root to pyproject.toml's testpaths.

### Fix 2: Mark ONLY mode oracle tests as xfail (15 min)

**ONLY in `mode/test_mode_oracle.py`** — NOT in store or teller oracle files:

```python
@pytest.mark.xfail(reason="Known bug: closure capture in get_state", strict=True)
def test_get_state_returns_wrong_mode_state_after_switch(self):
    ...
```

Apply to each test function in mode/test_mode_oracle.py. `strict=True` means if a bug gets fixed, the test becomes XPASS, prompting removal of the marker.

**Do NOT add xfail to:**
- `store/test_store_oracle.py` — these are Hypothesis property tests that SHOULD pass
- `teller/test_teller_oracle.py` — these are Hypothesis property tests that SHOULD pass

### Fix 3: Add Makefile + update CLAUDE.md (15 min)

```makefile
.PHONY: test test-full test-module

test:  ## Run stable module tests
	.venv/bin/pytest -x -q

test-full:  ## All tests including slow Hypothesis
	.venv/bin/pytest -v --hypothesis-seed=0

test-module:  ## Single module: make test-module M=store
	.venv/bin/pytest -x -q $(M)/
```

Update CLAUDE.md to include:
```markdown
## Testing
- Run tests: `make test` or `.venv/bin/pytest -x -q`
- Run module tests: `.venv/bin/pytest store/` (or mark/, teller/, mode/, listener/)
- Run all tests: `make test-full`
```

---

## What Makes Tome's Testing Architecture Excellent

Worth highlighting what's working — it's genuinely rare:

1. **Three-tier test strategy**: Regular → Oracle → Gremlin gives graduated confidence
2. **Protocol-based DI without frameworks**: No pytest fixtures with complex setup, no mock libraries. Just Python Protocols and lightweight mock classes.
3. **Hypothesis property testing**: 30 constant files = tests have been run extensively and found real edge cases
4. **docs/agentic-testing.md**: Explicitly documents KeyEvent construction, MockListener usage, text handler — saves agents 30 min of exploration
5. **Text teller handler**: `get_handler("text")` prints to stdout. Tests verify speech without audio hardware.
6. **MockListener**: Tests don't need X11/display

---

## Summary

Tome's RSP modules are individually excellent for agent iteration. The architecture, test strategy, and documentation show genuine care for testability. The problem is entirely at the project level: a config conflict, one set of intentionally-failing tests without xfail markers, and no documented entry point.

**Key correction from prior assessments:** Only `mode/test_mode_oracle.py` needs xfail. The store and teller oracle tests are Hypothesis property tests that verify invariants and SHOULD pass. Marking them as xfail would suppress real regression signals.

**35 minutes of surgical fixes would take agent iterability from 6/10 to 9/10.**

---

*Assessment by boffin agent — Phase 4 corrected analysis*  
*Bash execution unavailable (approval not granted), skein CLI not available*  
*Static analysis of: pyproject.toml, pytest.ini, CLAUDE.md, all oracle test files, agentic-testing.md, test_integration.py, test_wire.py, all prior assessment files*
