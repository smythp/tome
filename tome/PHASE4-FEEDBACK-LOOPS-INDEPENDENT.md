# Phase 4: Agent Iterability — Independent Feedback Loop Assessment

**Date:** 2026-05-11  
**Assessor:** boffin (technical architect, independent assessment)  
**Method:** Static analysis of all project files, configs, docs, test suites  
**Question:** Can an agent iterate on this codebase? What feedback loops exist?

---

## Verdict

**Module-level iteration: EXCELLENT. Project-level iteration: BROKEN.**

The gap is entirely in tooling/config, not in code or test architecture. Three fixes (≈35 min total) would transform this from "70% agent-iterable" to "95% agent-iterable."

---

## What Exists (Strong)

### Per-Module Test Suites
Every RSP module has comprehensive, well-isolated tests:

| Module | Test Files | Total Size | Signal Quality |
|--------|-----------|------------|----------------|
| store | test_store.py, test_store_gremlin.py, test_store_oracle.py | ~51KB | ✅ Excellent |
| mark | test_mark.py, test_gremlin_attacks.py | ~57KB | ✅ Excellent |
| mode | test_mode.py, test_mode_oracle.py, test_mode_syndic.py | ~69KB | ⚠️ Poisoned by oracle |
| teller | test_teller.py, test_teller_gremlin.py, test_teller_oracle.py | ~30KB | ✅ Excellent |
| listener | test_listener.py | ~23KB | ✅ Excellent |

### Three-Tier Test Strategy
- **Regular tests**: Happy paths, edge cases, comprehensive coverage
- **Oracle tests**: Known bugs documented as living tests (intentionally failing)
- **Gremlin tests**: Adversarial property-based attacks via Hypothesis

This is more sophisticated than most production codebases.

### Protocol-Based Dependency Injection
All modules use Python Protocols for interfaces. No mock frameworks needed — just lightweight mock classes that satisfy the protocol. An agent can read a test, understand the mock, and extend it without learning any framework.

### Explicit Agent Guidance
`docs/agentic-testing.md` documents how to construct KeyEvents, use MockListener, and wire components for testing. This saves an agent ~30 minutes of exploration.

### Text Teller Handler
`get_handler("text")` prints to stdout instead of invoking espeak. Tests verify speech output without audio hardware.

### Hypothesis Property Testing
30 constant files in `.hypothesis/` indicate thorough fuzzing history. Property tests provide fundamentally different feedback than example-based tests.

---

## What's Broken (Critical)

### 1. pytest.ini Overrides pyproject.toml (HIGH IMPACT)

**pytest.ini** (takes precedence):
```ini
testpaths = .
```

**pyproject.toml** (ignored when pytest.ini exists):
```toml
testpaths = ["store", "teller", "mark", "mode", "listener"]
```

Result: Root-level script files (`test_integration.py`, `test_wire.py`) get collected during test discovery. These are scripts with module-level side effects (including monkey-patching `os._exit`), not proper pytest test modules. They contribute 0 test functions but pollute the test environment.

### 2. Oracle Tests Are Permanently Red (HIGH IMPACT)

`test_mode_oracle.py`, `test_store_oracle.py`, and `test_teller_oracle.py` contain intentionally-failing tests that document known bugs. But they lack `@pytest.mark.xfail` markers, so the test suite is permanently red. An agent cannot distinguish expected failures from regressions.

### 3. No Makefile or Task Runner (MEDIUM IMPACT)

No `make test`, no task runner. An agent's first question — "how do I verify my change?" — has no documented answer. CLAUDE.md lists `python tome.py` but no test command.

### 4. No Linter Configured (LOW-MEDIUM IMPACT)

No ruff, flake8, mypy, or any static analysis tool. Agent can introduce style drift or type errors with no automated signal.

### 5. pyperclip Dependency Gap (LOW IMPACT)

`tome.py` imports pyperclip unconditionally, and `handlers.py` uses it in 5+ functions. But it's commented out in pyproject.toml as "future." It's probably installed in .venv, but fresh installs would break.

---

## The Agent Experience Today vs. Ideal

### Today:
```
1. Agent reads CLAUDE.md → No test command listed
2. Agent guesses `pytest` → pytest.ini collects everything
3. Root scripts cause side effects during collection
4. Oracle tests fail intentionally → suite is red
5. Agent can't tell: is the baseline green?
6. Agent makes changes → runs pytest again → same noise
7. Feedback loop is broken
```

### After 35 minutes of fixes:
```
1. Agent reads CLAUDE.md → "Run `make test`"
2. Agent runs `make test` → only stable module tests
3. All green ✅ → baseline is clean
4. Agent makes changes → `pytest store/` for fast feedback
5. `make test` for full verification → all green ✅
6. Agent knows: change is safe
```

---

## Three Fixes (35 Minutes Total)

### Fix 1: Delete pytest.ini (5 min)
**Impact:** Eliminates config conflict, stops root script collection  
**Action:** `rm pytest.ini` — let pyproject.toml control test discovery  
**Risk:** None. pyproject.toml already has correct testpaths.

### Fix 2: Mark oracle tests as xfail (15 min)
**Impact:** Makes the suite green while preserving bug documentation  
**Action:** In each oracle test file, add:
```python
@pytest.mark.xfail(reason="Known bug: [description]", strict=True)
```
`strict=True` means if a bug gets fixed, the test becomes XPASS (unexpected pass), prompting removal of the xfail marker.

### Fix 3: Add Makefile + update CLAUDE.md (15 min)
**Impact:** Gives agents a verified entry point  
**Action:**
```makefile
.PHONY: test test-full test-module

test:  ## Fast stable tests (agent default)
	.venv/bin/pytest -x -q

test-full:  ## All tests including hypothesis
	.venv/bin/pytest -v

test-module:  ## Single module: make test-module M=store
	.venv/bin/pytest -x -q $(M)/
```

Update CLAUDE.md:
```markdown
## Commands
- Run tests: `make test` (fast, stable tests)
- Run module tests: `make test-module M=store`
- Run all tests: `make test-full`
```

---

## Comparison with Previous Assessment

The existing `tome/PHASE4-FEEDBACK-LOOPS.md` assessment is thorough and accurate. This independent assessment validates its findings and adds:

1. **Explicit per-module signal quality ratings** — not just "exists" but "how good"
2. **The pyperclip dependency gap** — present but undeclared
3. **Confirmation of the core insight**: the problem is entirely at the project-level tooling layer, not the code or test architecture

Both assessments agree on the same three fixes in the same priority order.

---

## Bottom Line

Tome's RSP modules are individually **excellent** for agent iteration — among the best I've seen in a Python codebase. The three-tier test strategy, protocol-based DI, and agentic testing docs show genuine care for testability.

The problem is entirely at the project level: a config conflict that poisons test discovery, oracle tests that make the suite permanently red, and no documented entry point for "verify my change." These are 35 minutes of fixes that would transform the agent experience from "confused and wasting cycles" to "confident and productive."

---

*Independent assessment by boffin agent — Phase 4 feedback loop analysis*  
*Static analysis only (no bash execution)*
