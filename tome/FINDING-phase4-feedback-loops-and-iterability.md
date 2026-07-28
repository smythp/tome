# FINDING: Can an agent iterate on this codebase? (Phase 4)

**Question:** What feedback loops exist (tests, build, lint) and can an agent actually close the loop?

**Verdict:** NO (partial raw material, every actual loop broken or absent). Runtime UNVERIFIED — execution-tier bash blocked in headless cast, no approver.

---

## Summary

The raw material for iteration exists — a large test suite, hypothesis property tests, a lockfile — but every actual feedback loop is either broken, absent, or unrunnable in this environment. The strongest empirical proof is the codebase itself: ~50 redundant assessment files and zero fixes across many prior agent runs.

## Feedback loops, one by one

### 1. Tests — EXIST, extensive
Substantial suite: store/ (test_store 26.9KB, gremlin, oracle), teller/, mark/ (test_mark 40.6KB, gremlin_attacks), mode/ (mode, oracle, syndic), listener/ (22.8KB), plus root test_handlers.py (45.8KB), test_integration.py, test_wire.py. Real coverage *if it can run*.

### 2. Test discovery — BROKEN / CONFLICTED
- `pyproject.toml` → `testpaths = [store, teller, mark, mode, listener]` (package subdirs only)
- `pytest.ini` → `testpaths = .` (root + recurse)
- pytest.ini wins when both exist. So effective discovery is `.`, which finds root test_handlers/test_integration/test_wire AND recurses. But the two configs discover DIFFERENT test sets — a genuine trap depending on which config an agent trusts.
- **No conftest.py** anywhere → no shared fixtures, no sys.path setup. Root test_handlers.py imports root `handlers.py`; subdir tests import local modules. Import behavior depends on invocation cwd. Fragile.

### 3. Build — AMBIGUOUS
- `setuptools.build_meta`, one real dep (`pynput>=1.7.0`), `uv.lock` present (uv is intended toolchain).
- **No `[tool.setuptools.packages]`** with a flat layout containing 5+ top-level packages (store, teller, mark, mode, listener) plus root modules. `pip install -e .` will likely error on ambiguous flat-layout auto-discovery.

### 4. Lint — NONE
No ruff/flake8/black/mypy config anywhere (grep hits are all doc prose, not config). No `.pre-commit-config.yaml`. No `[tool.ruff/black/mypy]` in pyproject. Zero static-analysis loop.

### 5. CI — NONE
No `.github/workflows`, no `.gitlab-ci.yml`, no `*.yml` at all. Git repo exists (.gitignore present) but `git log` is blocked in headless — commit cadence unverifiable.

### 6. Runtime verification — BLOCKED
pytest cannot be run: approval-tier bash blocked, no approver. Same wall as Phase 3. Not fabricating a pass.

## Meta-signals (churn without convergence)
- `__pycache__` holds bytecode for pytest **7.4.3, 8.3.3, 9.0.2, 9.0.3** — many agents ran/attempted tests across different pytest installs. Churn, no convergence.
- Dangling `.pyc` for `utilities` and `test_tome` (cpython-38 AND -312) but the `.py` source is GONE. `import utilities` could mislead; stale bytecode is a hazard.
- `.hypothesis/` examples DB exists → property tests ran historically. The loop worked at some point.

## The documentation graveyard — strongest iterability signal
~43 assessment/finding markdown files in `tome/` (PHASE3-RUNNABILITY-* ×13, PHASE4-AGENT-ITERABILITY-* ×11, FINDING-* ×7, etc.), plus ~8 more at root, plus duplicates in `projects/tome-of-lore/`. Agents cannot close the loop, so each emits a fresh redundant report instead of fixing anything. This IS the finding: the agent feedback loop does not close.

## Recommendations (priority order)
1. Grant this cast a `careful` bash_profile so runtime can actually be verified — otherwise every agent hits the same wall and writes another report.
2. Reconcile the two pytest configs into a single source of truth; add a `conftest.py` for sys.path/fixtures.
3. Fix flat-layout build (add `[tool.setuptools.packages.find]` or move to src layout).
4. Add a minimal lint + CI loop (ruff + one GitHub Actions job running pytest).
5. Purge dangling `.pyc` (utilities, test_tome) and consolidate/delete the ~50 redundant assessment files.

**runtime_verified: false**
