# Phase 3: Runnability — Honest Assessment

**Date:** 2026-06-29
**Agent:** cartographer (Phase 3 continuation)
**Verdict:** UNVERIFIABLE AT RUNTIME — static analysis only

## The Core Constraint (itself a finding)

I was asked to *actually run* this project. I could not. Every attempt to invoke Python through bash was blocked:

```
APPROVAL-tier command blocked in headless mode (no human available to approve)
```

Three separate bash invocations failed:
1. `.venv/bin/python --version && import pynput && import pyperclip`
2. `.venv/bin/python --version`
3. (combined import checks)

**This is a real iterability finding, not just an excuse.** A headless agent cast against this repo has *no execution feedback loop*. It cannot run tests, cannot verify imports, cannot confirm the app starts. The mantle would need a `bash_profile: careful` or a `bash_tiers.safe` allowlist entry for `.venv/bin/python` / `pytest` to close the loop. As configured, every "try to run it" task collapses into static analysis — which is almost certainly why the `tome/` directory contains 30+ near-duplicate PHASE3/PHASE4 assessment files. Agents keep being asked to run it, keep being unable to, and keep regenerating static write-ups.

## What I CAN Verify (static)

### Will break on fresh install ❌
`tome.py` line 32: `import pyperclip` — unconditional, module-level.
`pyproject.toml` lines 17-18: pyperclip is *commented out*, only declared dependency is `pynput>=1.7.0`.

→ A clean `pip install -e .` followed by `python tome.py` raises `ModuleNotFoundError: No module named 'pyperclip'` at import time. The app cannot start on a fresh environment. **One-line fix:** add `pyperclip>=1.8.0` to dependencies.

(Note: the existing `.venv` reportedly has pyperclip 1.11.0 installed per Phase 2, so the app *might* run in *this* venv — but that's an undeclared, accidental dependency, not a reproducible install.)

### Conflicting pytest config ❌
- `pytest.ini`: `testpaths = .` (root)
- `pyproject.toml [tool.pytest.ini_options]`: `testpaths = ["store", "teller", "mark", "mode", "listener"]`

`pytest.ini` wins (it takes precedence over pyproject). Root-level tests (`test_integration.py`, `test_wire.py`, `test_handlers.py`, `test_deletion.py`) are currently discovered. If someone deletes `pytest.ini` expecting pyproject to take over, those root tests silently vanish from discovery.

### Espeak runtime dependency ❌ (undocumented)
Default teller mode is `espeak` (tome.py line 195). `espeak` is a system binary, not pip-installable. No OS install instructions exist. Even with all Python deps satisfied, `python tome.py` (without `--text`) will fail or be silent if espeak isn't on PATH. The `--text` flag bypasses this.

### Runtime environment requirement ❌ (likely)
`PynputListener` (tome.py line 29, 48) captures global keyboard input via pynput. This typically requires an X11/Wayland display or accessibility permissions. In a headless environment, `listener.start()` would likely fail or hang. This app is fundamentally interactive/desktop — not headless-runnable by design.

## What I CANNOT Verify (needs execution)

- Whether the test suite actually passes *today* (the `.pyc` files prove it ran historically under pytest 7.4.3 / 8.3.3 / 9.0.2 / 9.0.3 — but "ran" ≠ "passed", and not recently confirmed).
- Whether `python tome.py --text` reaches an interactive state in *this* venv.
- Whether any of the modules have runtime import errors beyond pyperclip.
- Actual Python version in the venv (symlink points to pyenv 3.12.0, but unconfirmed live).

## Honest Verdict

**On a fresh clone:** NOT RUNNABLE without fixes (pyperclip undeclared + espeak undocumented + display requirement).

**In the existing `.venv` with `--text`:** PLAUSIBLY runnable, but unconfirmed — I was structurally prevented from verifying.

## Priority Fixes (to make it genuinely runnable + verifiable)
1. Declare `pyperclip>=1.8.0` in `pyproject.toml` dependencies.
2. Document espeak install (`apt install espeak` / `brew install espeak`) in README.
3. Consolidate pytest config — delete `pytest.ini`, add `.` to pyproject testpaths.
4. Add a `Makefile` with `setup`/`test`/`run` targets.
5. **Give test-running agents an execution profile** so "run it" tasks stop degrading into static-analysis duplicates.
