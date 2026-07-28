# Phase 3: Runnability Assessment — Static Analysis

**Date:** 2026-05-07  
**Agent:** Architect (Phase 3, Static Analysis)  
**Method:** Full source code reading of all key files; no runtime execution (bash approval blocked)

## Executive Summary

**Verdict: RSP modules are sound. Top-level wiring has a blocking dependency bug. Test configuration has a conflict that causes unintended side effects.**

The five RSP modules (Store, Teller, Mark, Mode, Listener) are well-isolated and should import/test cleanly. The top-level `tome.py` has an unconditional `import pyperclip` on line 32, but pyperclip is commented out of `pyproject.toml` dependencies. This crashes `tome.py` on import. Additionally, `handlers.py` uses pyperclip extensively (17 occurrences across 6 handler functions), but uses lazy imports inside each function — so `import handlers` works, but calling any clipboard-related handler fails without pyperclip.

---

## BLOCKER: pyperclip Missing from Dependencies

**Severity:** Blocks `tome.py` import and all clipboard functionality  
**Root cause:** `pyproject.toml` has pyperclip commented out as a future dependency, but code already uses it extensively.

### Evidence

**tome.py line 32** (unconditional top-level import):
```python
import pyperclip  # crashes immediately if not installed
```

**pyproject.toml** (commented out):
```toml
# Future: pyperclip will be needed when clipboard functionality is added
# clipboard = ["pyperclip>=1.8.0"]
```

**handlers.py** (17 occurrences, lazy imports inside functions):
- `clipboard_handler` — line 204: `import pyperclip`
- `history_handler` — line 470: `import pyperclip`
- `_handle_all_mode_action` — line 635: `import pyperclip`
- `list_handler` — line 713: `import pyperclip`
- `read_handler` — line 1085: `import pyperclip`

Each handler function does `import pyperclip` at the top of the function body, then uses `pyperclip.paste()` or `pyperclip.copy()`. This means:
- ✅ `import handlers` works (no top-level pyperclip import)
- ❌ Calling any clipboard operation fails at runtime

**test_handlers.py** — Tests import pyperclip directly then monkeypatch it:
```python
import pyperclip
monkeypatch.setattr(pyperclip, "paste", lambda: "test content")
```
The `import pyperclip` line fails before monkeypatch can mock it, so clipboard-related tests in test_handlers.py will also fail.

Some tests use the string form `monkeypatch.setattr("pyperclip.copy", ...)` which also requires pyperclip to be importable (monkeypatch resolves the string by importing the module).

### Fix Options

1. **Add to dependencies** (simplest): Add `"pyperclip>=1.8.0"` to `[project.dependencies]` in pyproject.toml
2. **Make tome.py import lazy**: Remove line 32. handlers.py already uses lazy imports, so tome.py's top-level import is redundant — pyperclip is never called directly in tome.py
3. **Both**: Add to deps AND remove the unnecessary top-level import in tome.py

Recommendation: Option 3. The dependency should be declared, AND the redundant top-level import should be removed for consistency with the lazy pattern in handlers.py.

---

## ISSUE: pytest.ini vs pyproject.toml Conflict

**Severity:** Causes unexpected test collection behavior  
**Root cause:** Two config files disagree on testpaths

| Setting | `pytest.ini` | `pyproject.toml` |
|---------|-------------|------------------|
| testpaths | `.` (project root) | `["store", "teller", "mark", "mode", "listener"]` |
| markers | db, ui, keyboard, clipboard, integration | (none) |

`pytest.ini` takes precedence per pytest's config resolution rules. This means:

1. Running `pytest` discovers **all** test files at project root: `test_handlers.py`, `test_integration.py`, `test_wire.py`
2. The pyproject.toml testpaths (RSP-only) are silently ignored
3. Root test files have different characteristics than RSP tests (see below)

### Root Test File Characteristics

**test_integration.py** (script, not pytest):
- No `test_*` functions — it's a top-to-bottom script with `print()` statements
- Monkey-patches `os._exit` at module level (line 10-13)
- When pytest collects this file, importing it executes ALL top-level code as a side effect
- This creates a Store at `/tmp/test_integration.db`, initializes all handlers, and runs a full integration scenario during pytest collection

**test_wire.py** (script, not pytest):
- Same pattern — no `test_*` functions, runs as a script
- Creates temp DB, wires all RSPs, sends fake keypresses
- Side effects execute during pytest collection

**test_handlers.py** (proper pytest):
- 45.8KB of proper pytest test classes and functions
- Uses fixtures, monkeypatch, MagicMock
- Clipboard tests will fail without pyperclip (see above)

### Fix

Remove `pytest.ini` and keep `pyproject.toml` as the single config source. Move the markers to pyproject.toml. If root-level tests should also run, add `.` or specific files to the pyproject.toml testpaths.

---

## Module-by-Module Assessment

| Module | Importable? | Tests Pass? | Notes |
|--------|------------|-------------|-------|
| store/ | ✅ Yes | ✅ Likely | Pure SQLite, no external deps |
| teller/ | ✅ Yes | ✅ Likely | Has text/debug fallback handlers |
| mark/ | ✅ Yes | ✅ Likely | Depends on Store (easily mocked) |
| mode/ | ✅ Yes | ✅ Likely | Uses Protocols, no hard deps |
| listener/ | ⚠️ Needs pynput | ✅ Likely | MockListener available; pynput IS in deps |
| handlers.py | ✅ Yes | ⚠️ Clipboard tests fail | Lazy pyperclip imports = importable but clipboard ops fail |
| tome.py | ❌ No | ❌ No | Top-level `import pyperclip` crashes import |
| test_handlers.py | ⚠️ Partial | ⚠️ Partial | Non-clipboard tests should pass |
| test_integration.py | ⚠️ Side effects | N/A | Script, not pytest-compatible |
| test_wire.py | ⚠️ Side effects | N/A | Script, not pytest-compatible |

---

## Architecture Observations

### What's Good

1. **RSP isolation is excellent.** Each module has Protocol-based interfaces, no circular imports, own test suite.
2. **Lazy imports in handlers.py** are the right pattern — module imports cleanly, runtime deps resolve only when needed.
3. **Multiple test strategies** — unit, oracle, gremlin, property-based (Hypothesis). Comprehensive.
4. **Mode constructor** `Mode(teller, store, mark)` is consistently used across tome.py, test_integration.py, and test_wire.py.
5. **MockListener** enables integration testing without actual keyboard.

### What Needs Work

1. **tome.py breaks the lazy import pattern.** handlers.py does it right (lazy pyperclip), but tome.py does `import pyperclip` at the top level for no reason (pyperclip is never called directly in tome.py).
2. **Script-style test files** (test_integration.py, test_wire.py) should be converted to pytest functions or moved to a `scripts/` directory.
3. **Stale README** references nonexistent files, wrong Python version.
4. **Legacy files at root** (reference.py at 81KB, handlers.py at 42KB, lore.db) add confusion.

---

## Confidence Level

**High confidence** on the pyperclip blocker and pytest config conflict — these are verified through direct source reading.

**Medium confidence** on "tests likely pass" for RSP modules — based on code structure analysis, not actual execution. The .venv exists with pytest and hypothesis installed (verified via .venv/bin/ contents), and pynput is declared in deps, but I couldn't verify actual installation state.

**Unknown**: Whether pyperclip happens to be installed in the .venv despite not being in pyproject.toml. If manually installed, many of the issues above would be latent (present but not manifesting). The pyproject.toml bug would still be real — it would just be hidden.

---

## Previous Assessment Comparison

This assessment confirms and extends three prior findings:

1. **RUNNABILITY_FINDINGS.md** (2026-01-23): Identified missing dependency management. Since then, pyproject.toml was created but pyperclip was left commented out.
2. **phase3-runnability-findings.md** (2026-01-26): Incomplete due to no bash access. Same constraint hit here.
3. **tome/RUNNABILITY-ASSESSMENT.md** (2026-05-02): Identified the same pyperclip blocker and pytest conflict. My assessment adds the handlers.py lazy import analysis, test_handlers.py monkeypatch failure mode, and the script-style test collection issue.

New findings in this assessment:
- handlers.py uses **lazy** pyperclip imports (good pattern, but tests still break)
- test_handlers.py clipboard tests fail because `import pyperclip` runs before monkeypatch
- test_integration.py and test_wire.py execute as **side effects** during pytest collection
- tome.py's top-level `import pyperclip` is **redundant** — it's never used directly in that file
