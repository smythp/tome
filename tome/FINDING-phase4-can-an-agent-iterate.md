# Phase 4 Finding: Can an Agent Iterate on This Codebase?

**Question:** What feedback loops exist (tests, build, lint)? Can an agent actually iterate here?

**Verdict:** Technical feedback loops are PARTIAL. The epistemic feedback loop is BROKEN. The repo is living proof that agents re-do rather than iterate.

---

## 1. Test loop: PRESENT but misconfigured

Substantial test infrastructure exists:
- `store/` (test_store 26.9KB, test_store_gremlin, test_store_oracle)
- `teller/` (test_teller 17.1KB, gremlin, oracle)
- `mark/` (test_mark 40.6KB, test_gremlin_attacks 16KB)
- `mode/` (test_mode 32.3KB, oracle, syndic)
- `listener/` (test_listener 22.8KB)
- root: test_handlers.py (45.8KB), test_integration.py, test_wire.py
- Hypothesis property-based testing in use (`.hypothesis/` dir, hypothesis dep declared)

**Config conflict (real papercut):** Two disagreeing pytest configs.
- `pyproject.toml` `[tool.pytest.ini_options]`: `testpaths = [store, teller, mark, mode, listener]`
- `pytest.ini`: `testpaths = .`

When both exist, `pytest.ini` takes precedence (pytest's config-file precedence order). So a bare `pytest` collects from root — pulling in reference.py (81KB) and root test files the pyproject config intended to exclude. An agent running `pytest` gets behavior that contradicts the pyproject config. This trips up iteration.

**Test pass-state: UNVERIFIED.** I attempted to run `pytest --co -q` but the command was blocked (headless mode, no approval available). I did NOT confirm the tests pass. What would verify it: run `.venv/bin/python -m pytest --co -q` from repo root in a profile that permits execution.

**Version churn signal:** Compiled test bytecode exists for pytest 7.4.3, 8.3.3, 9.0.2, 9.0.3 (plus 8.3.5 on py38). Multiple agents ran tests under many pytest versions — not a clean, pinned loop.

## 2. Lint loop: ABSENT

No ruff / flake8 / black / mypy config anywhere. No pre-commit. There is no automated style or type feedback.

## 3. CI loop: ABSENT

No `.github/workflows`. No automated feedback on push.

## 4. Build loop: IRRELEVANT

setuptools backend is declared, but this is a script app (`python tome.py`), not a distributable. The build loop doesn't matter here.

---

## 5. THE CORE FINDING — the broken loop is epistemic, not technical

The `tome/` directory contains ~40 near-duplicate assessment markdown files. The pattern is unmistakable:

- `PHASE3-RUNNABILITY-{COMPREHENSIVE, DEFINITIVE-FINAL, DEFINITIVE, FINAL, HONEST, LIVE-ASSESSMENT, LIVE, STATIC-ANALYSIS, STATIC-ASSESSMENT, STATIC-FINAL, VERDICT}.md`
- `PHASE4-AGENT-ITERABILITY-{ASSESSMENT, COMPREHENSIVE, CORRECTED, DEFINITIVE, FINAL-ASSESSMENT, FINAL, FINAL-VERDICT, FINDING-FINAL, INDEPENDENT, VERDICT}.md`
- `PHASE4-FEEDBACK-LOOPS-{, INDEPENDENT, SYNTHESIS, VERIFIED}.md`
- Plus root-level duplicates: `RUNNABILITY_ASSESSMENT.md`, `RUNNABILITY_ASSESSMENT_MAY2026.md`, `RUNNABILITY_FINDINGS.md`, `phase3-runnability-findings.md`, `phase4-agent-iterability-findings.md`.

**This IS the answer to "can an agent iterate?"** The observable behavior of agents on this repo is that they DON'T iterate. They re-litigate the same question and spawn a new near-duplicate file each time (note the escalating suffixes: FINAL, DEFINITIVE, FINAL-VERDICT — the naming itself is a fossil record of agents unable to converge).

The loop that's broken isn't the test loop. It's the KNOWLEDGE loop:
- No canonical output location
- No dedup or "append to existing finding" discipline
- Each agent starts fresh and adds noise rather than editing prior work

**Irony:** I am writing this in the very directory whose sprawl I'm diagnosing. The highest-integrity action would be to CONSOLIDATE, not add. This file is itself evidence of the pathology unless the convention below is adopted.

---

## Highest-leverage fixes (ranked)

1. **Establish a canonical findings location + edit-in-place convention.** One file per question. Agents EDIT it, not fork it. This fixes the epistemic loop — the actual bottleneck.
2. **Resolve the pytest config conflict.** Delete one config; keep a single source of truth for testpaths.
3. **Add a minimal lint loop** (ruff) so agents get fast, automatable style/type feedback.
4. **Pin pytest** in the dev deps to stop version churn.
5. **Add CI** last — it only matters once 1–4 make the loop trustworthy.

More test infrastructure is NOT the answer. The repo already has plenty. The missing piece is a discipline that lets agents converge instead of re-doing.
