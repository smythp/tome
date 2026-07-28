# Feedback Loops & Agent Iterability Assessment

## Summary

Tests are the ONLY feedback loop in tome, and even that loop is unreliable for agents due to bash approval gates. No linting, no type checking, no CI pipeline exists. An agent working on this codebase is essentially flying blind after making changes.

## Detailed Findings

### 1. Test Infrastructure: EXISTS but PARTIALLY BROKEN for Agents

**What's there:**
- pytest installed in .venv (tested across versions 7.4.3, 8.3.3, 9.0.2)
- ~300KB+ of well-structured test files across all modules
- Hypothesis property-based testing
- Gremlin (adversarial) and Oracle (invariant) test patterns
- MockListener for integration testing without real keyboard
- `docs/agentic-testing.md` documents headless testing approach
- `.claude/settings.local.json` allows `.venv/bin/pytest:*`

**What's broken:**
- **pytest config conflict**: `pytest.ini` sets `testpaths = .` (discovers ALL tests) while `pyproject.toml` sets `testpaths = [store, teller, mark, mode, listener]` (module tests only). pytest.ini wins by precedence, but this is confusing.
- **Bash approval gates block execution**: Both this agent and a previous agent (boffin_11) were blocked by bash sandbox approval when attempting to run pytest. The `.claude/settings.local.json` allowlist includes `.venv/bin/pytest:*` but the sandbox still requires approval.
- Root-level tests (`test_handlers.py`, `test_integration.py`, `test_wire.py`) are only discovered via pytest.ini config, not pyproject.toml.

### 2. Test Quality: HIGH

- Test-first design (comments: "Tests written BEFORE implementation")
- Proper fixtures, class organization, clear naming
- Good mock patterns (MockListener, mock_store, mock_teller)
- Comprehensive coverage: unit, integration, property-based, adversarial, invariant
- `text` teller handler enables testing without espeak

### 3. Linting/Formatting: ABSENT

- No ruff, flake8, pylint, mypy, black, isort, pyright, or bandit installed
- No type hints enforcement
- No formatting standards enforcement
- CLAUDE.md documents style conventions but nothing enforces them

### 4. Build/CI Infrastructure: ABSENT

- No Makefile
- No CI config (GitHub Actions, etc.)
- No build scripts
- README references `setup_tome.sh` and `run_tests.sh` — neither exists
- README lists `test_tome.py` and `utilities.py` — neither exists
- README is significantly stale

### 5. Documentation: MIXED

- `docs/agentic-testing.md`: Excellent, directly useful for agents
- `CLAUDE.md`: Basic but functional
- `README.md`: Stale, references nonexistent files
- `ARCHITECTURE.md` / `ARCHITECTURE_MAP.md`: Exist but not verified for accuracy

## Agent Iterability Scorecard

| Feedback Loop | Status | Notes |
|---|---|---|
| Run tests | 🟡 YELLOW | Tests exist and are good, but approval gates block agents |
| Lint code | 🔴 RED | No tools installed |
| Type check | 🔴 RED | No tools installed |
| Format code | 🔴 RED | No tools installed |
| CI pipeline | 🔴 RED | None exists |
| Build/compile | ⚪ N/A | Pure Python, no build step needed |
| Test docs | 🟢 GREEN | agentic-testing.md is excellent |
| Mockability | 🟢 GREEN | Components designed for testability |

## Recommendations (Priority Order)

1. **Fix bash approval for pytest**: Resolve why `.venv/bin/pytest:*` in allowlist doesn't prevent approval gates. This is the single highest-impact fix.
2. **Install ruff**: One tool covers linting + formatting. Add to `[project.optional-dependencies] dev`.
3. **Resolve pytest config conflict**: Remove `pytest.ini` and consolidate into `pyproject.toml`, or vice versa. Choose one source of truth.
4. **Add a Makefile**: `make test`, `make lint`, `make check` — standard entry points agents and humans both expect.
5. **Update README**: Remove references to nonexistent scripts and files.
6. **Add mypy or pyright**: Type checking would catch many bugs statically.

## Evidence Notes

- Previous agent (boffin_11) also blocked by bash approval gates
- .hypothesis/ directory with 30 constants confirms property-based tests have been run
- .pyc files for pytest 7.4.3, 8.3.3, and 9.0.2 confirm tests run across versions
- tome/ directory contains ~35 assessment files from prior agents, suggesting many have investigated similar questions
