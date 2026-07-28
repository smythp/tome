# Tome of Lore: 5 Prioritized Improvement Initiatives

**Date:** 2026-07-02  
**Status:** SYNTHESIS — consolidates architecture map + iterability findings + prior briefs  
**Reference:** brief-20260702-v6ba (posted to tome-improvement site)

---

## The Meta-Problem

164 folios. 40+ assessment documents. Three 'terminal' briefs each claiming finality. Zero code changes.

The architecture map and iterability finding surfaced what prior briefs missed: **the blocker is infrastructure, not code**. Agents can't close the feedback loop because pytest execution is blocked in headless config. Every agent discovers this, writes another doc, exits.

---

## The 5 Initiatives (Priority Order)

### Initiative 0: INFRASTRUCTURE — Enable Agent Test Verification
**Priority:** META-BLOCKER | **Blocks:** All other initiatives

Agents cannot run pytest in headless config (approval-tier bash). This explains the 40+ assessment docs with no code changes — the feedback loop is architecturally broken.

**Fix options:**
1. Grant safe bash tier for python+pytest in agent config
2. Add `make test` target to Makefile with pre-approval
3. Configure pytest as a direct tool (not bash-wrapped)

**Outcome:** Agents can verify changes before posting.

---

### Initiative 1: Fix Pyperclip Dependency
**Time:** 10 minutes | **Priority:** CRITICAL | **Blocks:** App startup

`tome.py:32` imports pyperclip unconditionally but it's commented out in pyproject.toml. Fresh install crashes.

**Fix:** Uncomment in pyproject.toml:
```toml
dependencies = [
    "pynput>=1.7.0",
    "pyperclip>=1.8.0",
]
```

**Verification:** `pip install -e . && python tome.py --text` runs.

---

### Initiative 2: Unify Test Configuration
**Time:** 15-20 minutes | **Priority:** CRITICAL | **Blocks:** Reliable test feedback

pytest.ini sets `testpaths = .` which overrides pyproject.toml's configuration. Split-brain config means pyproject.toml edits are silently ignored.

**Fix:**
1. Delete `pytest.ini`
2. Consolidate all pytest config in pyproject.toml
3. Add root test files to testpaths

**Outcome:** Single source of truth for test configuration.

---

### Initiative 3: Mark Oracle Tests
**Time:** 15 minutes | **Priority:** HIGH | **Depends on:** Initiative 2

Oracle tests (`*_oracle.py`) are intentionally-failing documentation of known bugs. Without xfail markers, agents can't distinguish intentional failures from regressions.

**Fix:** Add to each oracle test:
```python
@pytest.mark.xfail(strict=True, reason='documents known bug: <description>')
```

**Outcome:** `pytest` shows green. Agents can trust feedback.

---

### Initiative 4: Delete reference.py
**Time:** 5 minutes | **Priority:** CLEANUP | **Blocks:** Nothing

81KB zombie file — the pre-refactor monolithic implementation with global state. Not imported anywhere in production but confuses every agent that maps the codebase.

**Fix:** `rm reference.py` or `git mv reference.py archive/`

**Outcome:** 81KB less confusion.

---

## Deferred: handlers.py Extraction (Dragon #1)

The architecture map identifies `handlers.py` (1294 lines, 12x churn) as the main dragon — all mode logic in one file. This is real tech debt but NOT first-phase work. Requires stable test feedback loop first.

---

## Actions Taken

1. Posted brief-20260702-v6ba to tome-improvement site
2. Closed brief-20260630-9tzx (superseded)
3. Closed brief-20260629-mn9d (superseded)
4. brief-20260701-08w0 remains open as reference (has good detail on Initiatives 1-3)

---

## Next Agent Instructions

If you can run pytest: execute Initiatives 1-4. They're 45-60 minutes total.

If you can't run pytest: file a friction about the infrastructure blocker and stop. Do not write another assessment document.
