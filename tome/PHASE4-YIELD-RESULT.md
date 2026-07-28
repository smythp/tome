# Phase 4 Yield Result — Can an agent iterate on this codebase?

> mill_yield was unavailable in this strand (no mill_context wired in). Per guidance, recording ordinary task output to file. Durable artifact posted to SKEIN as finding-20260702-tgej on site tome-improvement.

## Verdict: FAIL — an agent CANNOT iterate on this codebase in the current headless configuration

**Confidence: 8/10**

Not because the feedback loops are missing — they are strong — but because the **execution gate severs them**. This is now confirmed 3x independently in this strand alone (pytest --collect-only blocked as APPROVAL-tier in headless mode, no human to approve).

## The finding has two layers

### Layer 1 — What feedback loops EXIST (statically verifiable)

- **Tests: YES, extensive.** `test_*.py` across store/teller/mark/mode/listener plus root `test_handlers.py`, `test_integration.py`, `test_wire.py`. Gremlin/oracle/syndic property tests. Hypothesis in use (`.hypothesis/` present with examples DB). This is a serious suite.
- **Build: YES.** `pyproject.toml` (setuptools backend), `uv.lock` present. `uv sync` / `pip install -e .` viable.
- **Lint: ABSENT.** No ruff/flake8/black config, no `[tool.ruff]` in pyproject, no pre-commit. No lint feedback loop.
- **CI: ABSENT.** No `.github/` or CI config in tree. No automated gate.

### Layer 2 — Can an agent actually CLOSE these loops? (the real finding)

- **pytest split-brain (config trap).** `pytest.ini` sets `testpaths = .`; `pyproject.toml [tool.pytest.ini_options]` sets `testpaths = [store, teller, mark, mode, listener]`. When both files exist, **`pytest.ini` takes precedence** — so the pyproject `testpaths` is DEAD CONFIG, silently ignored. An agent editing pyproject testpaths thinks they're changing scope; nothing happens. Confirmed both configs present this strand; exact collected count NOT verified (couldn't run).
- **Environment drift.** `.pyc` artifacts for pytest 7.4.3, 8.3.3, 9.0.2, 9.0.3 AND python 3.12 and 3.8 — multiple toolchain versions have run here over time.
- **The BLOCKING finding.** Execution-tier bash is blocked in headless cast. Agent cannot run pytest, cannot run the app, cannot verify any fix. The loop requires executing code; the environment forbids it without human approval.

## Synthesis

The feedback loops are **DESIGNED but not CLOSABLE** by a headless agent. Tests exist and look strong, but an agent can't run them -> can't get red/green -> can't verify a change -> produces static assessment #N+1.

The `tome/` directory is the empirical proof: **40+ near-duplicate PHASE3/PHASE4/RUNNABILITY assessment files** (AGENT-ITERABILITY-ASSESSMENT, -COMPREHENSIVE, -CORRECTED, -DEFINITIVE, -FINAL, -FINAL-VERDICT, -INDEPENDENT, -VERDICT ... and the parallel PHASE3 set). This is the fossil record of a broken loop. Every agent asked "can you iterate" discovers it can't run tests and writes another doc. **The broken feedback loop is the disease; the duplicate files are the symptom.**

## Highest-leverage fix

Grant the assessment mantle a `careful`/`safe` bash tier for `python` + `pytest` (add matching patterns to the mantle's `bash_tiers` safe list, or set `bash_profile: careful`). That single change converts every future assessment from static speculation into a verified result and stops the duplicate-file explosion.

Secondary (cheap, real) fixes once execution is possible:
1. Delete `pytest.ini` OR remove the pyproject `[tool.pytest.ini_options]` block — resolve the split-brain so testpaths is unambiguous.
2. Add a linter (ruff) + pre-commit to create a fast, executable feedback loop.
3. Add minimal CI (`.github/workflows`) so the gate exists independent of any single agent's environment.
4. Consolidate the 40+ `tome/` assessment files into ONE living document; stop minting new differently-named files.

## Artifacts
- SKEIN finding: finding-20260702-tgej (tome-improvement)
- This file: tome/PHASE4-YIELD-RESULT.md
