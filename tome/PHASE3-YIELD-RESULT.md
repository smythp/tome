# Phase 3 Yield Result

**Task:** Try to run the tome project. Document what works, what breaks.

**Verdict:** FAIL (not runnable-by-agents in default headless cast)
**Confidence:** 8/10

**Note on yield:** `mill_yield` was unavailable in this strand (no `mill_context`). Per tooling guidance, recording results as a file instead.

## Summary

I hit the exact same wall every prior agent hit: I cannot actually run this project in a headless cast. Execution-tier bash (running python, pytest) is blocked because no human is available to approve. That is not a footnote — that IS the finding.

## What I could verify statically

1. **README lies.** It instructs `./setup_tome.sh` and `./run_tests.sh` — both CONFIRMED absent (ls exit=2, 'No such file or directory').
2. **Stale README file list.** README references `utilities.py` and `test_tome.py`; neither exists in the tree. The real entry point is `tome.py` (5974 bytes), which imports the modular RSP structure (store, teller, mark, mode, listener).
3. **Dependency mismatch.** `pyproject.toml` declares only `pynput`; `pyperclip` is commented out as 'future.' Prior agent (cartographer) reported pyperclip is actually imported somewhere. If true, fresh installs break. Could not confirm the import site at runtime (execution blocked).
4. **Pytest split-brain CONFIRMED.** `pytest.ini` sets `testpaths=.` while `pyproject.toml [tool.pytest.ini_options]` sets `testpaths=[store, teller, mark, mode, listener]`. Deleting pytest.ini silently drops root-level tests (test_handlers.py, test_integration.py, test_wire.py).

## The meta-finding (the real disease)

The `tome/` directory contains 20+ near-duplicate PHASE3-RUNNABILITY-* and PHASE4-AGENT-ITERABILITY-* assessment files. Agent after agent gets asked to 'run the project,' can't (headless execution blocked), and produces yet another static assessment. The broken feedback loop is the disease; the duplicate files are the symptom.

## Fix direction

To make this project runnable-by-agents in headless casts, one of:
- Give the mantle an execution profile (`bash_profile: careful`), or
- Add pytest/python patterns to the mantle's `bash_tiers` safe list, or
- Run the cast in a mode that allows approval.

Until the feedback loop is fixed, further 'run the project' tasks will keep producing duplicate static assessments.

## Artifacts produced

- SKEIN finding: finding-20260702-xpqa (posted to tome-improvement)
- Writeup: tome/PHASE3-RUNNABILITY-EXECUTION-BLOCKED.md
- This yield record: tome/PHASE3-YIELD-RESULT.md
