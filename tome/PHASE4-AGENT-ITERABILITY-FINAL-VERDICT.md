# Phase 4: Agent Iterability & Feedback Loops

## Verdict: PARTIALLY ITERABLE — Strong tests exist but poor discoverability and no guard rails

**Confidence: 7/10** (static analysis only — bash commands were blocked)

---

## Executive Summary

The Tome codebase has surprisingly strong test infrastructure buried beneath poor discoverability. An agent CAN iterate on this codebase, but will waste significant time figuring out HOW. The tests themselves are well-designed (3-tier: unit, oracle, gremlin), but there's no lint, no CI, no Makefile, and CLAUDE.md doesn't even mention pytest.

---

## What Works Well (Agent Strengths)

### 1. Comprehensive Test Suite
- **3-tier testing**: unit tests, oracle tests (property-based via Hypothesis), gremlin tests (adversarial)
- **Per-primitive coverage**: store/, teller/, mark/, mode/, listener/ each have dedicated test files
- **Root-level integration**: test_handlers.py (1362 lines), test_integration.py, test_wire.py
- **Good fixtures**: MockListener, TextHandler enable fully headless testing
- **Hypothesis**: Property-based testing catches edge cases agents would miss

### 2. Tests Bypass the pyperclip Crash
- `tome.py` imports `pyperclip` (not installed), making `import tome` crash
- But ALL test files import from primitives directly (store, teller, mark, mode, listener, handlers)
- `handlers.py` does NOT import pyperclip — only `tome.py` does
- This means the entire test suite should run fine despite the broken main entry point

### 3. Clean RSP Architecture
- Five independent primitives with clear boundaries
- Each primitive is independently testable
- `test_wire.py` provides a great smoke test pattern for wiring validation

---

## What's Missing (Agent Friction)

### 1. CLAUDE.md Doesn't Mention Testing (CRITICAL)
- CLAUDE.md lists `python tome.py` and `sqlite3 lore.db < CREATE.sql`
- **No mention of pytest, hypothesis, or how to run tests**
- An agent reading CLAUDE.md would not know tests exist or how to run them
- Fix: Add `Run tests: .venv/bin/pytest` and `Run single primitive: .venv/bin/pytest store/`

### 2. pytest.ini vs pyproject.toml Conflict
- `pyproject.toml` sets `testpaths = ["store", "teller", "mark", "mode", "listener"]` (primitives only)
- `pytest.ini` sets `testpaths = .` (everything)
- pytest.ini wins (takes precedence), so root-level tests DO run
- But this is confusing — an agent might read pyproject.toml and think root tests are excluded
- Fix: Remove the `[tool.pytest.ini_options]` section from pyproject.toml, or consolidate in one place

### 3. No Build Tooling
- No Makefile (no `make test`, `make lint`, `make check`)
- No tox.ini
- No .pre-commit-config.yaml
- No CI workflows (.github/workflows/)
- Agent must discover `.venv/bin/pytest` by examining the venv directory
- Fix: Add a minimal Makefile with test/lint/check targets

### 4. No Static Analysis
- No linter configured (no ruff, flake8, pylint)
- No type checker (no mypy, pyright)
- No formatter (no black, ruff format)
- Agent gets zero static feedback — only test pass/fail
- Fix: Add ruff (fast, minimal config needed)

### 5. Assessment Document Sprawl
- **28 documents** in tome/ directory alone from previous agent analyses
- Plus 4 more at root level (RUNNABILITY_*.md, phase3-*.md, phase4-*.md)
- Plus 2 in projects/tome-of-lore/
- **34 total assessment docs** creating noise when agents explore the codebase
- Previous agents analyzed extensively but left actual fixes undone
- Fix: Consolidate into 1-2 canonical docs, archive or delete the rest

### 6. handlers.py is 1294 Lines
- Single file contains ALL mode handlers
- Hard for agents to reason about (context window pressure)
- Fix: Split into per-mode handler files (read_handler.py, options_handler.py, etc.)

---

## Feedback Loop Assessment

| Loop | Exists? | Quality | Agent Discoverable? |
|------|---------|---------|--------------------|
| Unit tests | ✅ Yes | Strong (Hypothesis) | ❌ Not in CLAUDE.md |
| Integration tests | ✅ Yes | Good | ❌ Not documented |
| Smoke tests | ✅ Yes (test_wire.py) | Good pattern | ❌ Not documented |
| Linter | ❌ No | N/A | N/A |
| Type checker | ❌ No | N/A | N/A |
| CI | ❌ No | N/A | N/A |
| Build system | ❌ No | N/A | N/A |

---

## Recommended Fixes (Priority Order)

1. **Update CLAUDE.md** — Add test commands, venv activation, and primitive test paths
2. **Add Makefile** — `make test`, `make lint`, `make check` targets
3. **Fix pytest config** — Consolidate to one location (pytest.ini or pyproject.toml, not both)
4. **Add ruff** — Minimal linter config for static feedback
5. **Clean up assessment docs** — 34 docs is absurd; consolidate to 1-2
6. **Split handlers.py** — 1294 lines in one file hurts agent reasoning

---

## Methodology Note

This assessment was performed entirely via static analysis (file reads, tree inspection, grep). Bash commands for running pytest were submitted but never received approval. The conclusions about test runnability are based on import chain analysis, not actual execution. Confidence would be 9/10 with live test execution confirming the static analysis.
