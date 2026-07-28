# Phase 4: Agent Feedback Loop Assessment

**Date:** 2026-05-07  
**Assessor:** boffin (technical architect)  
**Method:** Static analysis of all project files, configs, docs, test files  
**Question:** Can an agent iterate on this codebase? What feedback loops exist?

---

## Executive Summary

**Tome has strong per-module feedback loops but a broken project-level feedback loop.** An agent working inside a single RSP module (store, teller, mark, mode, listener) gets excellent signal. An agent working at the integration layer or trying to verify the whole project gets poisoned signal that wastes cycles.

The fix is surgical: three changes turn this from "70% agent-iterable" to "95% agent-iterable."

---

## The Agent Experience Walkthrough

This is what actually happens when an agent tries to iterate on Tome today:

### Scenario: Agent is asked to add a feature to `store/`

```
Step 1: Agent reads CLAUDE.md
  → Sees "Run application: python tome.py" 
  → No test command listed
  → Agent guesses: pytest

Step 2: Agent runs `pytest`
  → pytest.ini (testpaths = .) overrides pyproject.toml (testpaths = ["store",...]) 
  → Discovers ALL test files including root-level ones
  → test_integration.py and test_wire.py execute print statements during collection
  → Oracle tests in mode/test_mode_oracle.py fail intentionally
  → Agent sees a mix of passes, failures, and stdout noise
  → Agent cannot determine: is the baseline green?

Step 3: Agent tries to fix failures
  → Reads test_mode_oracle.py docstring ("All tests should FAIL")
  → Maybe understands, maybe doesn't
  → Either way, can't get a clean green baseline

Step 4: Agent makes its change to store/
  → Runs pytest again
  → Same noise as before
  → Cannot tell if its change broke anything
  → Feedback loop is broken
```

### What SHOULD happen:

```
Step 1: Agent reads CLAUDE.md
  → Sees: "Run `make test` to verify changes"
  → Sees: "Run `pytest store/` for module-specific tests"

Step 2: Agent runs `make test`
  → Only stable module tests run
  → All green ✅
  → Agent knows: baseline is clean

Step 3: Agent makes its change to store/
  → Runs `pytest store/` for fast feedback
  → All green ✅
  → Runs `make test` for full verification
  → All green ✅
  → Agent knows: change is safe
```

---

## Feedback Loop Inventory

### Loops That Exist

| Loop | Signal Quality | Speed | Notes |
|------|---------------|-------|-------|
| `pytest store/` | ✅ Excellent | Fast | 26.9KB of tests, clean isolation |
| `pytest mark/` | ✅ Excellent | Fast | 40.6KB of tests + 16KB gremlin |
| `pytest mode/` | ⚠️ Poisoned | Medium | Oracle tests fail intentionally |
| `pytest teller/` | ✅ Excellent | Fast | 17.1KB + gremlin + oracle |
| `pytest listener/` | ✅ Excellent | Fast | 22.8KB of tests |
| Hypothesis property tests | ✅ Excellent | Slow | 30 constant files → thorough fuzzing |
| Git history | ✅ Good | Instant | Clean commits, proper .gitignore |
| `docs/agentic-testing.md` | ✅ Excellent | N/A | Explicit agent guidance |
| Text teller handler | ✅ Good | N/A | stdout-based test output |
| Protocol-based DI | ✅ Excellent | N/A | Natural mocking without frameworks |

### Loops That Don't Exist

| Missing Loop | Impact on Agent Iteration |
|-------------|---------------------------|
| No Makefile / task runner | Agent must guess the right pytest invocation |
| No linter (ruff, flake8) | Agent can introduce style drift with no signal |
| No type checker (mypy, pyright) | Type errors only caught at runtime |
| No CI/CD | No external verification gate |
| No coverage reporting | Agent can't see if new code is tested |
| No `make test` one-liner in CLAUDE.md | Agent's first action ("how do I test?") has no answer |
| No way to distinguish expected vs unexpected failures | Agent treats all red as bugs |

---

## Per-Module Iterability Scores

| Module | Iterability | Why |
|--------|------------|-----|
| `store/` | **9/10** | Self-contained tests, protocol DI, three test tiers, no external deps |
| `mark/` | **9/10** | Clean isolation, gremlin tests, thorough coverage |
| `listener/` | **8/10** | MockListener is well-designed, good test volume |
| `teller/` | **8/10** | Text handler enables testing, three test tiers |
| `mode/` | **6/10** | Excellent tests BUT oracle tests poison the signal |
| Integration layer | **3/10** | test_integration.py and test_wire.py are script-style, tome.py crashes on import |
| Project-wide | **4/10** | Config conflict, no entry points, no linter, no baseline green |

**Key insight:** The RSP modules are individually among the best agent-iterable code I've seen. The project-level tooling is what's broken.

---

## The Three Critical Fixes

Ranked by impact on agent iteration capability:

### Fix 1: Delete pytest.ini, consolidate into pyproject.toml
**Impact: Eliminates config confusion**
**Effort: 5 minutes**

```toml
# pyproject.toml - add markers from pytest.ini
[tool.pytest.ini_options]
testpaths = ["store", "teller", "mark", "mode", "listener"]
python_files = "test_*.py"
python_functions = "test_*"
markers = [
    "db: tests that interact with the database",
    "ui: tests for user interface components",
    "keyboard: tests involving keyboard interaction",
    "clipboard: tests involving clipboard operations",
    "integration: integration tests combining multiple components",
    "slow: tests that take significant time (hypothesis)",
]
```

Then delete `pytest.ini`.

This single change means `pytest` discovers only the RSP module tests, excluding the problematic root-level scripts. An agent running `pytest` gets meaningful signal immediately.

### Fix 2: Mark oracle tests as xfail
**Impact: Makes the suite green**
**Effort: 15 minutes**

In every oracle test file (`test_mode_oracle.py`, `test_store_oracle.py`, `test_teller_oracle.py`):

```python
@pytest.mark.xfail(reason="Known bug: closure capture in get_state", strict=True)
def test_get_state_closure_capture(self):
    ...
```

`strict=True` means if the bug gets fixed, the test starts passing, and pytest flags it as `XPASS` (unexpected pass) — prompting the agent or human to remove the xfail marker. The tests still document the bugs, still run, but don't pollute the pass/fail signal.

### Fix 3: Add Makefile + update CLAUDE.md
**Impact: Gives agents a verified entry point**
**Effort: 15 minutes**

```makefile
.PHONY: test test-full test-module lint

test:  ## Fast stable tests (agent default)
	.venv/bin/pytest -x -q

test-full:  ## All tests including hypothesis
	.venv/bin/pytest -v

test-module:  ## Single module: make test-module M=store
	.venv/bin/pytest -x -q $(M)/

lint:  ## Check code style
	.venv/bin/ruff check .
```

Then update CLAUDE.md:
```markdown
## Commands
- Run tests: `make test` (fast, stable tests)
- Run all tests: `make test-full` (including hypothesis property tests)  
- Run module tests: `make test-module M=store`
- Lint: `make lint`
```

---

## What Makes Tome's Module-Level Testing Excellent

Worth calling out what's working, because it's genuinely rare:

1. **Three-tier test strategy**: Regular → Oracle → Gremlin gives graduated confidence. Regular tests verify happy paths. Oracle tests encode known bugs as living documentation. Gremlin tests adversarially attack edge cases. This is more sophisticated than most production codebases.

2. **Protocol-based DI without frameworks**: No pytest fixtures with complex setup, no mock libraries, no dependency injection containers. Just Python protocols and lightweight mock classes. An agent can read the test, understand the mock, and extend it without learning a framework.

3. **Hypothesis property testing**: 30 constant files in `.hypothesis/` means these tests have been run many times and found real edge cases. Property tests provide a fundamentally different kind of feedback than example-based tests.

4. **docs/agentic-testing.md**: Explicitly documents how to construct KeyEvents, use MockListener, and wire components for testing. This is the kind of document that saves an agent 30 minutes of exploration.

5. **Text teller handler**: `get_handler("text")` prints to stdout instead of invoking espeak. This means tests can verify speech output without audio hardware. Simple, effective.

---

## Comparison with the Existing Assessment

The previous `AGENT-ITERABILITY-ASSESSMENT.md` (by the earlier boffin agent) is thorough and accurate. My Phase 4 assessment adds:

1. **The agent experience walkthrough** — concrete step-by-step of what happens vs. what should happen
2. **Per-module iterability scores** — highlighting the gap between module-level (excellent) and project-level (broken)
3. **Signal quality ratings** — not just "does the loop exist" but "how good is the signal"
4. **The key insight**: the problem is entirely at the project-level tooling layer, not the code or test architecture

The existing assessment's recommendations are correct. This assessment validates them and adds the "why" from an agent-iteration perspective.

---

## Bottom Line

Tome's RSP modules are individually **excellent** for agent iteration — among the best I've seen in a Python codebase. The three-tier test strategy, protocol-based DI, and agentic testing docs show genuine care for testability.

The problem is entirely at the project level: a config conflict that poisons test discovery, oracle tests that make the suite permanently red, and no documented entry point for "verify my change." These are 35 minutes of fixes that would transform the agent experience from "confused and wasting cycles" to "confident and productive."

**Priority order:**
1. Delete `pytest.ini` (5 min) — biggest bang for buck
2. Mark oracle tests as `xfail` (15 min) — makes suite green
3. Add Makefile + update CLAUDE.md (15 min) — gives agents a front door

---

*Assessment by boffin agent — Phase 4 feedback loop analysis, static analysis only*
*Bash execution was unavailable (approval not granted) — findings based on file reads and config analysis*
