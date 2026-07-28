# Phase 3: Runnability — The Feedback Loop Is Broken

**Date:** 2026-07-02
**Agent:** cartographer (Phase 3)
**Verdict:** NOT runnable-by-agents in the default headless cast environment.

## The Honest Result

I was asked to "try to run this project." I could not. Not because the code is
necessarily broken, but because **execution-tier bash commands are blocked in
headless casts** — there is no human present to approve running `python` or
`pytest`. Every attempt returned:

> APPROVAL-tier command blocked in headless mode (no human available to approve)

This is the same wall every prior agent hit. **This is the finding.**

## Smoking Gun: The Duplicate Files

The `tome/` directory contains ~40 near-duplicate assessment files:

- 11 files named `PHASE3-RUNNABILITY-*` (COMPREHENSIVE, DEFINITIVE, DEFINITIVE-FINAL,
  FINAL, HONEST, LIVE, LIVE-ASSESSMENT, STATIC-ANALYSIS, STATIC-ASSESSMENT,
  STATIC-FINAL, VERDICT)
- 15+ files named `PHASE4-AGENT-ITERABILITY-*`
- Plus scattered RUNNABILITY-ASSESSMENT and FINDING-feedback-loops variants

Agents cannot run the project, so they produce a static assessment, cannot converge
or verify, and the next agent starts over. The proliferation of `-FINAL`,
`-DEFINITIVE`, `-DEFINITIVE-FINAL` suffixes is the fingerprint of a broken
iteration loop: nobody can confirm anything, so nothing is ever actually final.

## What I CAN Confirm Statically

1. **README is stale/lying.** It instructs `./setup_tome.sh` and `./run_tests.sh`
   — both CONFIRMED ABSENT (`ls` exit 2, "No such file or directory"). It also
   lists `utilities.py` and `test_tome.py` in its Files section — neither exists
   in the tree. The README describes a project that no longer exists.

2. **pytest split-brain (CONFIRMED).** `pytest.ini` sets `testpaths = .` while
   `pyproject.toml [tool.pytest.ini_options]` sets
   `testpaths = [store, teller, mark, mode, listener]`. Different test discovery
   depending on which config wins. Deleting `pytest.ini` silently drops all
   root-level tests (test_handlers.py, test_integration.py, test_wire.py).
   A silent-failure trap for any agent "cleaning up" config.

3. **Dependency mismatch (structurally real).** `pyproject.toml` declares only
   `pynput`; `pyperclip` is commented out as "future." Cartographer Phase 2
   reported pyperclip is actually imported. I could not run an import to confirm
   at runtime (blocked), but if any module imports pyperclip, fresh installs from
   pyproject alone will break.

4. **tome.py exists and is the real entry point** (5974 bytes). It imports the
   modular RSP structure: store, teller, mark, mode, listener. The README's
   `./tome.py` is plausible; the setup script it depends on is not.

## What I Could NOT Verify (execution blocked)

- Whether core imports actually succeed
- Whether pyperclip is importable in the venv
- Whether the test suite passes
- Whether tome.py runs

I am NOT presenting any of these as confirmed. That would repeat the sin visible
in some of the `-LIVE` assessment files, which appear to assert runtime results
that could not have been produced in a headless cast.

## The Real Fix (root cause, not symptoms)

The breakage is not "missing scripts." It is that **the agents asked to assess
runnability are structurally unable to run anything.** Two paths:

1. **Give the assessment mantle an execution profile.** Set
   `"bash_profile": "careful"` or add `python`/`pytest` to the mantle's
   `bash_tiers` "safe" list, so headless casts can actually run the suite. Without
   this, you will keep generating PHASE3-RUNNABILITY-N+1.md forever.

2. **Fix the static breakages so a human/CI run is trivial:** rewrite README to
   match reality (or add the missing setup_tome.sh / run_tests.sh), resolve the
   pytest config split-brain (pick one config, delete the other), and declare
   pyperclip in dependencies if it is imported.

Then **delete the ~40 duplicate assessment files** — they are noise that actively
misleads the next agent into thinking the work is done.
