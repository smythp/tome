# Phase 4: Agent Iterability & Feedback Loops — Synthesis Assessment

**Date:** 2026-05-19  
**Assessor:** boffin (technical architect, independent assessment)  
**Method:** Static analysis — file reads, config analysis, doc review, cross-referencing prior assessments  
**Bash execution:** Unavailable (approval not granted)  
**Skein:** Unavailable (binary not found)

---

## Verdict

**Module-level: EXCELLENT. Project-level: BROKEN. Meta-level: DEGRADING.**

Tome's per-RSP feedback loops are among the best I've seen in a Python codebase. But three project-level issues prevent agents from getting clean signal, and a new meta-problem — assessment sprawl — is actively making the situation worse.

---

## The Feedback Loop Chain

| Level | Quality | Notes |
|-------|---------|-------|
| Module (store, mark, teller, listener) | ★★★★★ | Clean isolation, three-tier tests, protocol DI, no external deps |
| Module (mode) | ★★★★☆ | Excellent tests but oracle suite poisons signal |
| Integration | ★★☆☆☆ | pytest.ini vs pyproject.toml conflict; root-level tests use print/assert not pytest |
| Application | ★☆☆☆☆ | `import pyperclip` crashes tome.py; pynput needs display server |
| Agent entry | ★★☆☆☆ | CLAUDE.md has no test command; no Makefile; agent must guess |
| Meta/orientation | ★★☆☆☆ | 19 assessment files in tome/; no canonical status doc; agent must triage which to read |

**Key insight:** The problem is NOT in the code or test architecture. It's entirely in the project-level tooling shell and the accumulating meta-documentation.

---

## What's Working (Genuinely Excellent)

1. **Three-tier test strategy** — unit → gremlin/adversarial → oracle/property-based with Hypothesis. More sophisticated than most production codebases.
2. **Protocol-based DI** — No mock frameworks, no fixture complexity. Just Python protocols and lightweight mock classes (MockListener, MockStore, MockTeller, TextHandler).
3. **docs/agentic-testing.md** — Explicit agent guidance for KeyEvent construction, MockListener usage, test wiring. Saves 30+ minutes of exploration.
4. **Hypothesis property testing** — 30 constant files in .hypothesis/ show thorough fuzzing history.
5. **Full dependency isolation** — Tests need no espeak, no pynput/X11, no clipboard, no network.

---

## What's Broken (Three Surgical Fixes)

Multiple independent assessments have converged on the same three fixes. This convergence itself validates the findings.

### Fix 1: Delete pytest.ini (5 min)
- pytest.ini sets `testpaths = .` which overrides pyproject.toml's `testpaths = ["store", "teller", "mark", "mode", "listener"]`
- This causes pytest to discover root-level test files (test_handlers.py, test_wire.py, test_integration.py) that use print/assert patterns and may have import issues
- **Delete pytest.ini. pyproject.toml is the single source of truth.**
- Alternatively, move pytest.ini's markers into pyproject.toml

### Fix 2: Mark oracle tests as xfail (15 min)
- Oracle tests in mode/test_mode_oracle.py, store/test_store_oracle.py, teller/test_teller_oracle.py intentionally fail to document known bugs
- This makes the suite permanently red — agents can't distinguish real failures from intentional ones
- **Add `@pytest.mark.xfail(reason="Known bug: ...", strict=True)` to each oracle test**
- `strict=True` means if a bug gets fixed, the test becomes XPASS and alerts the developer

### Fix 3: Add Makefile + update CLAUDE.md (15 min)
- No documented test command in CLAUDE.md (only `python tome.py`)
- Agent's first action is always "how do I verify my change?" — no answer exists
- **Add a Makefile with `test`, `test-full`, `test-module`, `lint` targets**
- **Update CLAUDE.md Commands section with `make test`**

Total effort: ~35 minutes. Impact: transforms agent experience from "confused" to "productive."

---

## New Finding: Assessment Sprawl (Meta-Problem)

The tome/ directory now contains **19 assessment files** from previous agents:

```
tome/
├── AGENT-ITERABILITY-ASSESSMENT.md
├── COMPREHENSIVE-STATIC-ASSESSMENT.md
├── FINDING-agent-iterability-consolidated.md
├── FINDING-agent-iterability.md
├── FINDING-feedback-loops.md
├── FINDING-phase4-feedback-loops-final.md
├── PHASE3-RUNNABILITY-COMPREHENSIVE.md
├── PHASE3-RUNNABILITY-FINAL.md
├── PHASE3-RUNNABILITY-LIVE.md
├── PHASE3-RUNNABILITY-STATIC-ANALYSIS.md
├── PHASE3-RUNNABILITY-STATIC-ASSESSMENT.md
├── PHASE3-RUNNABILITY-STATIC-FINAL.md
├── PHASE4-AGENT-ITERABILITY-ASSESSMENT.md
├── PHASE4-AGENT-ITERABILITY-CORRECTED.md
├── PHASE4-AGENT-ITERABILITY-FINAL.md
├── PHASE4-FEEDBACK-LOOPS-INDEPENDENT.md
├── PHASE4-FEEDBACK-LOOPS.md
├── PHASE4-FINAL-VERDICT.md
└── RUNNABILITY-ASSESSMENT.md
```

This is itself a DX problem:
- A new agent arriving at this codebase must triage which of 19 files to read
- Many files overlap significantly (multiple Phase 3 and Phase 4 assessments saying similar things)
- No file tracks which recommendations have been implemented
- The assessments multiply but the actual fixes (pytest.ini, xfail, Makefile) remain undone

**Recommendation:** Consolidate into a single `tome/STATUS.md` with:
- Current state of each known issue (open/fixed/wontfix)
- The three priority fixes with checkboxes
- Links to the most authoritative assessment for each topic
- Archive the rest into `tome/archive/`

Then: **actually implement the three fixes instead of writing more assessments.**

---

## Quantified Agent Time Waste

| Activity | Estimated waste per agent session |
|----------|-----------------------------------|
| Reading CLAUDE.md, not finding test command, guessing | 2-5 min |
| Running pytest, getting poisoned signal from oracle tests | 5-10 min |
| Investigating pytest.ini vs pyproject.toml conflict | 5-15 min |
| Reading 19 assessment files to understand current state | 10-20 min |
| Hitting pyperclip import crash when testing tome.py | 2-5 min |
| **Total per agent session** | **24-55 min wasted** |

With the three fixes + assessment consolidation: **<5 min orientation time.**

---

## Cross-Assessment Convergence

This is the key meta-observation: **multiple independent agents have reached identical conclusions through different analysis paths.** The existing assessments (PHASE4-FEEDBACK-LOOPS.md, PHASE4-AGENT-ITERABILITY-FINAL.md, AGENT-ITERABILITY-ASSESSMENT.md) all identify the same three fixes with the same priority ordering.

This convergence provides high confidence that:
1. The diagnosis is correct
2. The fixes are the right ones
3. The priority ordering is right
4. **The next step is implementation, not more assessment**

---

*Assessment by boffin agent — Phase 4 synthesis, static analysis only*  
*Bash execution unavailable (approval not granted). Skein unavailable (binary not found).*
