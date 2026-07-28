# Strategic Improvement Brief - Tome of Lore Agent Iterability

*Synthesized from AGENT_ITERABILITY_ASSESSMENT.md*
*Date: 2026-01-21*

## Strategic Context

The Tome of Lore has **solid foundations for agent iteration** but needs **feedback loop infrastructure improvements**. The codebase is well-organized with focused modules, clear separation of concerns, and standard tooling - but lacks the integrated verification workflow that enables confident, rapid iteration.

## Five Strategic Initiatives

These initiatives build on each other, creating compounding improvements to iterability.

---

### Initiative 1: Enable Reliable Basic Iteration
**Timeline:** Immediate (1-2 hours)
**Drives:** Momentum, Energy
**Removes constraint:** Agents can't iterate confidently today

**What:**
- Add `make check` target combining lint + test
- Add CONTRIBUTING.md documenting the iteration loop
- Ensure `make test` runs without TTS hardware dependency

**Why this first:**
Without a reliable "did my change work?" signal, iteration is uncertain and slow. This creates the foundation everything else builds on. The energy here is removing friction - making the basic loop work.

**Concrete deliverable:**
```makefile
check: lint test
	@echo "✓ All checks passed"
```

---

### Initiative 2: Add Type-Level Feedback
**Timeline:** Short-term (2-4 hours)
**Drives:** Clarity, Structure
**Removes constraint:** Only runtime errors caught

**What:**
- Configure mypy with strict mode
- Add type checking to `make check`
- Fix any revealed type issues

**Why this second:**
Once the basic loop works, add another feedback layer. Type checking catches errors before tests run, tightening the loop. The structure here is making implicit contracts explicit.

**Concrete deliverable:**
```toml
[tool.mypy]
strict = true
warn_unreachable = true
```

---

### Initiative 3: Test TTS Integration Without Hardware
**Timeline:** Short-term (3-6 hours)
**Drives:** Flow, Material
**Removes constraint:** Can't test TTS interactions in CI

**What:**
- Create mock TTS fixtures for pytest
- Add integration tests for navigation flows
- Add error handling path tests

**Why this third:**
With basic and type checking working, expand test coverage. The flow here is creating test conditions that match real use without physical dependencies. Material constraint: TTS hardware won't exist in CI.

**Concrete deliverable:**
```python
@pytest.fixture
def mock_tts():
    with patch('tome.tts.speak') as m:
        yield m

def test_navigation_speaks(mock_tts, browser):
    browser.next()
    mock_tts.assert_called_once()
```

---

### Initiative 4: Add Continuous Integration
**Timeline:** Medium-term (4-8 hours)
**Drives:** Structure, Momentum
**Removes constraint:** No automated verification gate

**What:**
- Add GitHub Actions workflow
- Run `make check` on every commit
- Add test coverage reporting
- Add pre-commit hooks

**Why this fourth:**
With comprehensive local checks working, automate them. The structure here is creating a forcing function - the gate that ensures quality. Momentum: every commit proves itself.

**Concrete deliverable:**
```yaml
# .github/workflows/check.yml
name: Check
on: [push, pull_request]
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: make check
```

---

### Initiative 5: Document Architecture for Agent Context
**Timeline:** Medium-term (3-5 hours)
**Drives:** Clarity, Will
**Removes constraint:** Agents must infer architecture from code

**What:**
- Create ARCHITECTURE.md explaining design decisions
- Document module responsibilities and boundaries
- Add decision records (ADRs) for key choices
- Explain TTS abstraction and state management

**Why this fifth:**
With all feedback loops working, add the context layer. The clarity here is making the *why* explicit, not just the *what*. Will: this enables agents to make aligned changes, not just safe ones.

**Concrete deliverable:**
```markdown
# Architecture

## Core Abstractions
- **Browser**: State machine for navigation
- **TTS**: Speech output abstraction
- **Bindings**: Keyboard → action mapping
- **Config**: User preferences

## Key Decisions
- [ADR-001] State-based navigation over command parsing
- [ADR-002] TTS abstraction for testing
```

---

## Strategic Synthesis

### How They Compound

1. **Basic loop** (Initiative 1) enables experimentation
2. **Type checking** (Initiative 2) catches more errors earlier
3. **TTS mocking** (Initiative 3) enables comprehensive testing
4. **CI** (Initiative 4) enforces quality automatically
5. **Architecture docs** (Initiative 5) enable aligned evolution

Each layer builds on the previous. Without #1, #2 has nothing to integrate with. Without #2 and #3, #4 would just automate incomplete checks. Without #1-4 working, #5 is just documentation.

### The Tension Points

**Energy vs. Structure:** Initiative 1 wants momentum ("just make it work"), but Initiatives 2 and 4 want rigor. Resolution: Get basic momentum first, then add structure.

**Flow vs. Material:** Initiative 3 wants intuitive TTS testing, but TTS hardware is a material constraint. Resolution: Mock the constraint away.

**Will vs. Clarity:** Initiative 5 wants to enable aligned changes (will), which requires making architecture explicit (clarity). They reinforce.

### Success Metrics

**After Initiative 1:**
- Agent can run `make check` and trust the result
- Iteration time: ~30 seconds (edit → verify)

**After Initiative 3:**
- 80%+ test coverage including TTS interactions
- Tests run without hardware dependencies

**After Initiative 4:**
- Every commit auto-verified
- Pre-commit hooks prevent broken commits

**After Initiative 5:**
- Agent can make architectural changes confidently
- New contributors understand design in <30 minutes

### Next Actions

**Immediate:** Start Initiative 1 - add `make check` and CONTRIBUTING.md
**Sequence:** Complete 1 → 2 → 3 → 4 → 5 in order
**Time to full iterability:** ~20-30 hours of focused work

---

## Conclusion

The Tome of Lore is **already iterable** - but these five initiatives transform it from "possible to iterate" to "confident agent-driven development." The foundation is good. The path is clear. The improvements compound.

Start with Initiative 1. Everything else follows.