# Runnability Assessment — May 2026

**Date:** 2026-05-25  
**Method:** Static analysis + venv inspection (bash execution gated by approval)  
**Previous assessments:** 2026-01-26 (INCOMPLETE), 2026-04-22 (CONDITIONALLY RUNNABLE)

## Verdict: CONDITIONALLY RUNNABLE (with corrections to prior assessment)

The test suite is almost certainly runnable. The main application requires X11/display and espeak, so it won't run in headless/CI environments without the `--text` flag.

## Key Correction to April 2026 Assessment

The April assessment stated:
> `python tome.py` will crash with `ImportError: No module named 'pyperclip'`

**This is incorrect for the current environment.** `pyperclip-1.11.0` IS installed in the venv (confirmed via `ls .venv/lib/python3.12/site-packages/pyperclip*`), even though it remains commented out in `pyproject.toml`. The app will NOT crash on import. However, pyperclip is still an **undeclared dependency** — a packaging bug that would bite anyone doing a fresh `pip install`.

## Environment State

| Component | Status | Details |
|-----------|--------|---------|
| Python | ✅ 3.12.0 | via pyenv, symlinked in .venv |
| venv | ✅ Present | `.venv/` with activate scripts |
| pynput | ✅ 1.8.1 | Declared in pyproject.toml |
| pytest | ✅ 9.0.2 | In dev dependencies |
| hypothesis | ✅ 6.152.1 | In dev dependencies |
| pyperclip | ⚠️ 1.11.0 | Installed but NOT declared |
| evdev | ✅ 1.9.2 | Installed (pynput backend) |
| python-xlib | ✅ 0.33 | Installed (pynput backend) |
| espeak | ❓ Unknown | System binary, not pip-installable |

## What Works

### Test Suite (Very High Confidence)

Strong evidence of successful prior execution:
- `.hypothesis/` directory with **30 entries** in constants — extensive property-based testing history
- `.pyc` files from **3 different pytest versions** (7.4.3, 8.3.3, 9.0.2)
- All test dependencies installed and at compatible versions
- Test files use clean mocking patterns (MagicMock for Store, Teller, ModeContext)
- No external system dependencies in test code — handlers are tested via mock contexts

**Expected command:** `source .venv/bin/activate && python -m pytest`

### Individual RSP Modules (High Confidence)

All core modules use clean, testable imports:
- **store/**: stdlib only (sqlite3, dataclasses, datetime, pathlib, typing)
- **mark/**: typing only
- **mode/**: logging, dataclasses, typing
- **listener/**: stdlib + pynput (declared)
- **teller/**: stdlib + espeak system binary (has text/debug fallback handlers)

Cross-module dependencies use Protocol classes — no circular import risk.

### Main Application with `--text` Flag (Medium Confidence)

`tome.py` accepts `--text` flag which uses text output instead of espeak:
```python
teller_mode = "text" if args.text else "espeak"
```

With `--text`, the espeak dependency is bypassed. However, `PynputListener` still requires X11/display access, which blocks headless execution.

## What's Broken

### 1. Undeclared pyperclip Dependency (Packaging Bug)

**Impact:** Fresh `pip install -e .` will NOT install pyperclip → `ImportError` on `import pyperclip` (tome.py line 32)  
**Current state:** Works in existing venv because pyperclip was manually installed  
**Fix:** Add `"pyperclip>=1.8.0"` to `dependencies` in pyproject.toml, or make the import lazy/conditional

### 2. Conflicting pytest Configuration

**pytest.ini** (wins due to precedence):
```ini
testpaths = .
```

**pyproject.toml**:
```toml
testpaths = ["store", "teller", "mark", "mode", "listener"]
```

pytest.ini discovers root-level tests (`test_handlers.py`, `test_integration.py`, `test_wire.py`). If someone removes pytest.ini assuming pyproject.toml handles config, those 3 test files silently stop running.

**Fix:** Consolidate into one location. Either delete pytest.ini and add `"."` to pyproject.toml testpaths, or remove pytest config from pyproject.toml.

### 3. espeak System Dependency (Undocumented)

README lists espeak as a prerequisite but provides no installation instructions. The teller module has fallback handlers (text, debug), and the `--text` CLI flag bypasses espeak entirely.

### 4. X11/Display Requirement

pynput requires X11 or a display server for keyboard listening. The app cannot run in:
- SSH sessions without X forwarding
- Docker containers without display
- CI/CD pipelines
- Headless servers

This is fundamental to the app's design (keyboard-driven interface) and not a bug.

## What's Still Missing

| Item | Impact | Priority |
|------|--------|----------|
| Makefile | No `make test`, `make setup` | Medium |
| Setup docs in README | Clone-to-running not documented | Medium |
| CI configuration | No automated test runs | Low |
| Type checking setup | No mypy/pyright config | Low |

## Recommended Fixes (Priority Order)

1. **Add pyperclip to dependencies** — one-line fix, eliminates the only ImportError risk
2. **Consolidate pytest config** — delete pytest.ini, update pyproject.toml testpaths to include `"."`
3. **Add Makefile** — `make setup`, `make test`, `make run` targets
4. **Document setup steps** — especially espeak installation per OS

## Assessment Method & Limitations

This assessment was performed through:
- Static analysis of all source files and their imports
- Direct inspection of `.venv/lib/python3.12/site-packages/` contents
- Review of `.venv/bin/` symlinks and binaries
- Analysis of `.hypothesis/` and `.pyc` artifacts as execution evidence
- Comparison with two prior assessments (Jan 2026, Apr 2026)

**Limitation:** Could not execute any Python code due to bash approval gates. All runnability verdicts are inferred from static analysis and artifact evidence, not actual execution. The one new finding (pyperclip IS installed) was confirmed by directory listing, not by import.

**What would change with execution access:**
- Could confirm test suite passes (high confidence it does based on evidence)
- Could confirm exact espeak availability
- Could test `--text` mode operation
- Could verify pynput initializes correctly on this system
