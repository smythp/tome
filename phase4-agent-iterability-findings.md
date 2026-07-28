# Phase 4: Agent Iterability — Feedback Loops (CANONICAL)

**Verdict: Iterable for a human / approved-bash agent. NOT iterable for a headless agent.**
Confidence: 8/10 (static analysis; runtime execution was blocked, see caveat).

This file is the canonical Phase 4 finding. It intentionally OVERWRITES a prior
version that described a different ("kree") codebase and invented dependencies
(evdev, Xlib, pygments) not present in this repo. Do not mint new PHASE4-*-FINAL
variants — edit this file.

---

## The core question

Can an agent make a change, get feedback on whether it worked, and converge?
That requires reachable feedback loops. Here's the honest split.

## Feedback loops that EXIST (and are good)

1. **Substantial test suite.** `test_*.py` across `store/`, `teller/`, `mark/`,
   `mode/`, `listener/` plus root `test_handlers.py`, `test_integration.py`,
   `test_wire.py`, `test_deletion.py`. The `__pycache__` holds compiled test
   artifacts for pytest 7.4.3, 8.3.3, 9.0.2, and 9.0.3 — proof these tests have
   been run repeatedly over time. The loop is real.
2. **Property-based testing.** `.hypothesis/` cache plus `*_gremlin` (adversarial)
   and `*_oracle` / `*_syndic` test variants. This is a strong correctness loop —
   better than most projects this size.
3. **End-to-end integration sim.** `test_integration.py` is a deterministic
   session simulator: it mocks `os._exit`, drives synthetic `KeyEvent`s through
   the real `Mode`/`Store`/`Mark`/handler stack, and prints state. No real
   keyboard or TTS hardware needed — exactly the kind of loop an agent can use.
4. **Manual run path documented.** `CLAUDE.md`: `python tome.py`, and
   `sqlite3 lore.db < CREATE.sql` to init the DB.

## Feedback loops that DO NOT exist

1. **No CI.** No `.github/`, no workflows. Nothing enforces the test loop.
2. **No lint.** No ruff/flake8/pylint config, no `.flake8`/`.ruff.toml`/`setup.cfg`.
3. **No type checking.** No mypy/pyright config.
4. **No `make test` / `make lint` convenience targets.** Agents must know the
   incantations; there's no single discoverable entry point.

## Blockers that actively damage iteration

1. **Config split-brain (real, verified).** `pytest.ini` sets `testpaths = .`
   while `pyproject.toml [tool.pytest.ini_options]` sets
   `testpaths = ["store","teller","mark","mode","listener"]`. `pytest.ini`
   takes precedence, so root-level tests (`test_integration.py`, `test_wire.py`,
   `test_deletion.py`, `test_handlers.py`) ARE discovered today — but delete or
   rename `pytest.ini` and they silently vanish from discovery. An agent
   "cleaning up duplicate config" can break the test loop without any error.
2. **First-run crash on fresh install (Phase 3 finding).** `tome.py:32` imports
   `pyperclip` unconditionally; `pyproject.toml` keeps pyperclip commented out
   (lines 17-18). A clean `pip install -e .` then `python tome.py` raises
   ImportError. The very first loop a new agent hits is broken.
3. **Headless execution gap (the decisive one).** A headless cast has no
   approval path for bash, so `pytest`/`python` cannot be run at all. The test
   loop EXISTS but is UNREACHABLE for a headless agent. The loop is alive for a
   human or an approved-bash agent and dead for a headless one.

## The loudest signal: assessment churn

The `tome/` directory contains ~40 near-duplicate assessment files —
`PHASE3-RUNNABILITY-*` (COMPREHENSIVE, DEFINITIVE, DEFINITIVE-FINAL, FINAL,
HONEST, LIVE, LIVE-ASSESSMENT, STATIC-*, VERDICT...), `PHASE4-AGENT-ITERABILITY-*`
(ASSESSMENT, COMPREHENSIVE, CORRECTED, DEFINITIVE, FINAL, FINAL-ASSESSMENT,
FINAL-VERDICT, FINDING-FINAL, INDEPENDENT, VERDICT...), plus a swarm of
`FINDING-feedback-loops-*` and `RUNNABILITY-*` files.

This litter is itself the strongest iterability finding. Prior agents could not
run the code, so they had no ground truth to converge on — and instead of
resolving the assessment they re-generated it under a new -FINAL suffix each
time. **Assessment churn is the symptom of a broken iteration loop.** A working
feedback loop produces convergence; a broken one produces file proliferation.
This very repo is the case study.

## What would actually fix iterability

In priority order:

1. **Give headless casts an execution profile** (e.g. allow `pytest`/`python`
   in the mantle's safe bash tier). This is the highest-leverage fix: it turns
   the dead loop live and stops the churn at its root.
2. **Resolve the pytest config split-brain.** Pick ONE source of truth. If you
   keep root tests, set `testpaths` to include `.` (or list every dir) in a
   single file and delete the other. Recommend consolidating into
   `pyproject.toml` and deleting `pytest.ini`, but ONLY after adding the root
   test dirs to `testpaths` so discovery doesn't regress.
3. **Fix the pyperclip import** — either guard it (`try/except ImportError`) or
   uncomment the clipboard optional-dependency and document it.
4. **Add a Makefile** with `test`, `lint`, `setup` targets so the loop is
   discoverable, not folklore.
5. **Add ruff** for a fast quality loop (low effort, high signal).
6. **Garbage-collect the `tome/` assessment swarm** down to this one canonical
   file once the execution loop works.

## Caveat on confidence

Everything above is static analysis. I could not run a single command — bash is
APPROVAL-tier and there was no approver in this headless cast. The test loop's
EXISTENCE is verified (files + compiled artifacts); its current GREEN/RED state
is NOT verified. I will not present unrun tests as passing.

---
*Phase 4 assessment — boffin. Canonical; supersedes the PHASE4-* swarm in tome/.*
