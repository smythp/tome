# Phase 4: Feedback Loops & Agent Iterability — Independent Verification

**Date:** 2026-05-25
**Assessor:** boffin (technical architect)
**Method:** Independent static analysis, cross-referenced with boffin_11's assessment
**Bash execution:** Unavailable (approval gates never granted — itself evidence of iterability friction)

---

## Verdict

**I independently verify boffin_11's Phase 4 assessment (tome/PHASE4-FEEDBACK-LOOPS.md).** The analysis is accurate, the recommendations are correct, and the priority ordering is right.

**Tome has excellent per-module feedback loops but a broken project-level feedback loop.**

---

## What I Independently Confirmed

### 1. pytest.ini vs pyproject.toml Conflict (VERIFIED)
- `pytest.ini` sets `testpaths = .` (discovers everything)
- `pyproject.toml` sets `testpaths = ["store", "teller", "mark", "mode", "listener"]` (scoped)
- pytest.ini wins (ini takes precedence over pyproject.toml)
- This means bare `pytest` finds root-level script-style tests and oracle tests, poisoning signal

### 2. Zero Static Analysis Tools (VERIFIED)
- Grepped pyproject.toml for ruff, mypy, flake8, pylint, black, isort — zero matches
- No .pre-commit-config.yaml
- No tox.ini
- No .github/ directory (no CI)
- The only feedback loop is pytest

### 3. Test Infrastructure Quality (VERIFIED)
- store/test_store.py: 90 tests
- mark/test_mark.py: 94 tests  
- Three-tier strategy: Regular → Oracle → Gremlin across store, mark, teller, mode
- Hypothesis property-based testing with 30 cached constant files
- docs/agentic-testing.md provides explicit agent guidance
- Protocol-based DI enables clean mocking without frameworks
- TextHandler teller enables headless testing

### 4. No Makefile or Task Runner (VERIFIED)
- No Makefile exists
- CLAUDE.md documents `python tome.py` but no test command
- Agent must guess `pytest` as entry point

### 5. Oracle Tests Poison Suite Signal (VERIFIED via static read)
- mode/test_mode_oracle.py exists with intentionally-failing tests
- teller/test_teller_oracle.py and store/test_store_oracle.py also exist
- Without xfail markers, `pytest` can never be fully green

---

## Additional Finding: Bash Approval Gates as Iterability Evidence

I attempted to run `pytest --collect-only` and `pytest -x` four separate times during this assessment. All four requests sat in approval limbo indefinitely. This is direct evidence of the iterability problem:

- An agent that cannot run tests cannot iterate
- The approval gate for read-only pytest collection is overly cautious
- Even `pytest --co -q` (just listing test names) required approval

This suggests that beyond the three fixes in the original assessment, there's a fourth concern: **the execution environment must trust agents to run tests.** A Makefile with `make test` doesn't help if the agent can't execute `make`.

---

## Confirmed Priority Order

1. **Delete pytest.ini** (5 min) — biggest impact, removes config conflict
2. **Mark oracle tests as xfail** (15 min) — makes suite baseline green
3. **Add Makefile + update CLAUDE.md** (15 min) — gives agents a documented entry point

These three changes move project-level iterability from ~4/10 to ~9/10.

---

## Per-Module Scores (Independently Assessed)

| Module | Score | Notes |
|--------|-------|-------|
| store/ | 9/10 | 90 tests + gremlin + oracle, clean isolation |
| mark/ | 9/10 | 94 tests + gremlin, thorough edge cases |
| listener/ | 8/10 | MockListener well-designed, good volume |
| teller/ | 8/10 | TextHandler enables headless testing |
| mode/ | 6/10 | Excellent tests, oracle tests poison signal |
| Integration | 3/10 | Script-style tests, no proper pytest structure |
| Project-wide | 4/10 | Config conflict, no linter, no baseline green |

---

*Independent verification by boffin agent — static analysis only*
*Cross-referenced with boffin_11's PHASE4-FEEDBACK-LOOPS.md*
