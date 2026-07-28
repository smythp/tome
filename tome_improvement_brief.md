# Tome Improvement Initiatives - CORRECTED

**Date:** 2026-01-23 (Corrected from 2026-01-11)  
**Source:** Cartographer architecture analysis + Code/Doc mismatch finding  
**Status:** ⚠️ REPLACES PREVIOUS BRIEF - Based on ACTUAL implementation, not aspirational docs

---

## Critical Discovery

**ARCHITECTURE.md describes a different system entirely:**
- Flask web service with REST API
- Redis caching, PostgreSQL persistence
- Vector embeddings with FAISS
- RAG system with query expansion

**Actual tome.py implementation:**
- Modal keyboard-driven TUI (pynput)
- SQLite hierarchical storage
- espeak TTS output
- RSP pattern with 5 primitives

This brief addresses the **ACTUAL system** as documented in ARCHITECTURE_MAP.md.

---

## Executive Summary

Tome is a working modal keyboard listener using the RSP (Relatively Simple Primitives) pattern. Five core modules (Store, Mark, Mode, Listener, Teller) compose cleanly with Protocol-based dependency inversion. However, 3 dragons and missing infrastructure create risk and friction.

This brief presents **5 prioritized initiatives** to improve runnability, safety, and maintainability.

---

## Architecture Context

**Clean Foundation:**
- 4-layer architecture with excellent separation of concerns
- Protocol-based dependency injection enabling testability
- Single SQLite table with hierarchical buffer structure
- Good import graph - no circular dependencies

**The Dragons (complexity hotspots):**
1. **reference.py (79KB)** - Original monolith with global state
2. **Store buffer operations** - Hierarchy management with state cascades
3. **Mode state machine** - Complex context creation and switching
4. **List navigation** - Index management with soft deletes

**What's NOT a dragon:**
- Store CRUD operations (simple, well-tested)
- Teller wrapper (straightforward)
- Individual simple handlers

---

## Initiative 1: Dragon Documentation & Test Coverage
**Priority: HIGHEST** | **Effort: Medium** | **Impact: Risk Reduction**

### Problem
The 4 dragons are high-complexity, high-coupling areas that block confident changes. Developers avoid touching them due to unclear behavior and insufficient test coverage.

### Action
- **Document behavior** for each dragon:
  - reference.py: What still depends on it? What's the migration path?
  - Buffer ops: State invariants, cascade behavior, deletion semantics
  - Mode state machine: State transitions, context lifecycle, hook semantics
  - List navigation: User-facing vs internal indices, soft delete handling

- **Add focused tests:**
  - Buffer hierarchy operations (create/enter/exit/recursive delete)
  - Mode switching with state preservation
  - Index management edge cases

- **Create runbooks:**
  - "How to safely modify buffer operations"
  - "Understanding mode state transitions"
  - "Debugging index mismatches"

### Success Metrics
- Each dragon has documented behavior and invariants
- Test coverage >80% for dragon code paths
- At least 1 runbook per dragon

### Dependencies
None - this enables all other work

---

## Initiative 2: Store Buffer Operation Safety
**Priority: HIGH** | **Effort: Medium** | **Impact: Data Integrity**

### Problem
Buffer hierarchy management (create/enter/exit/delete) involves state cascades through parent_id references. Easy to corrupt, hard to debug.

### Action
- **Add invariant checks:**
  - Parent exists before creating child
  - No orphaned buffers after delete
  - Buffer stack integrity on enter/exit

- **Transaction safety:**
  - Wrap hierarchy operations in transactions
  - Rollback on constraint violations
  - Atomic parent_id updates

- **Detailed logging:**
  - Log all hierarchy state changes
  - Include parent_id chain in errors
  - Track buffer lifecycle events

### Success Metrics
- Zero data corruption incidents
- Hierarchy invariants enforced at runtime
- Clear error messages for constraint violations

### Dependencies
Initiative 1 (documentation helps design invariants)

---

## Initiative 3: Mode State Machine Observability
**Priority: HIGH** | **Effort: Low-Medium** | **Impact: Developer Experience**

### Problem
The mode state machine (context creation, switching, protocol DI) is critical infrastructure. Everything assumes it works perfectly, but it's hard to debug when it doesn't.

### Action
- **State transition logging:**
  - Log every mode switch with before/after context
  - Track handler registration/unregistration
  - Record protocol dependency resolution

- **Mode context inspector:**
  - CLI command to dump current mode state
  - Show active handlers, context data, parent mode
  - Display protocol bindings

- **Better error messages:**
  - "Mode X expected protocol Y but Z was provided"
  - "Context switch failed: state Z invalid for mode transition"
  - Include mode stack trace in errors

### Success Metrics
- Mode state visible during debugging
- Error messages include actionable context
- Developers can inspect mode state without code changes

### Dependencies
None

---

## Initiative 4: Reference.py Deprecation Path
**Priority: MEDIUM-HIGH** | **Effort: High** | **Impact: Technical Debt Elimination**

### Problem
reference.py (79KB) is the original monolith with global state everywhere. It's the Rosetta Stone for understanding the migration, but also the biggest liability.

### Action
- **Identify remaining dependencies:**
  - Grep for all imports of reference.py
  - Document what still uses it and why
  - Categorize by difficulty to migrate

- **Create migration checklist:**
  - Priority 1: Critical paths still using reference
  - Priority 2: Nice-to-have migrations
  - Priority 3: Can live with forever (mark as legacy)

- **Sunset timeline:**
  - Target date for reference.py removal
  - Milestones for dependency reduction
  - Communication plan for developers

### Success Metrics
- Complete dependency map of reference.py
- Migration checklist with effort estimates
- Sunset timeline with milestones

### Dependencies
Initiative 1 (need to understand reference.py first)

---

## Initiative 5: Architecture Decision Records (ADRs)
**Priority: MEDIUM** | **Effort: Low** | **Impact: Onboarding & Consistency**

### Problem
The architecture is clean and emerging well, but the key decisions aren't documented. This slows onboarding and risks inconsistent future decisions.

### Action
- **Capture key decisions:**
  - Why protocol-based DI?
  - Why single SQLite table vs normalized schema?
  - Why 4-layer architecture?
  - Migration strategy from reference.py

- **Document boundaries:**
  - Layer responsibilities (Listener/Mode/Handlers/Store)
  - What crosses layer boundaries and how
  - Protocol design patterns

- **Record migration rationale:**
  - Why incremental refactor vs rewrite?
  - What gets migrated first and why?
  - How to maintain compatibility during transition

### Success Metrics
- ADRs for 5+ key architectural decisions
- Layer boundaries documented
- Migration strategy captured

### Dependencies
None

---

## Initiative 6: List Navigation Index Management
**Priority: LOW-MEDIUM** | **Effort: Low** | **Impact: Bug Reduction**

### Problem
Index management with soft deletes is tricky. User-facing indices vs internal indices cause confusion. Insertion shifts indices.

### Action
- **Document index semantics:**
  - User-facing index (visible items only)
  - Internal index (all items including soft-deleted)
  - How they map to each other

- **Add validation helpers:**
  - `assert_valid_user_index(index, buffer_id)`
  - `user_to_internal_index(user_index, buffer_id)`
  - Clear error messages for out-of-bounds

- **Example scenarios:**
  - Insert at index 2 when item 1 is soft-deleted
  - Delete item, then reference by index
  - List with sparse soft deletes

### Success Metrics
- Index semantics documented with examples
- Validation helpers available
- Zero index-related bugs in next sprint

### Dependencies
None

---

## Priority Ranking

1. **Dragon Documentation & Test Coverage** (HIGHEST)  
   *Enables everything else. Risk reduction. Developer confidence.*

2. **Store Buffer Operation Safety** (HIGH)  
   *Data integrity. Highest risk area.*

3. **Mode State Machine Observability** (HIGH)  
   *Blocks debugging. Critical infrastructure.*

4. **Reference.py Deprecation Path** (MEDIUM-HIGH)  
   *Strategic debt. Long-term cleanup.*

5. **Architecture Decision Records** (MEDIUM)  
   *Foundation for future decisions. Onboarding.*

6. **List Navigation Index Management** (LOW-MEDIUM)  
   *Quick win. Bug reduction.*

---

## Implementation Notes

### Sequencing
- **Start with Initiative 1** (Dragon Documentation) - it enables all others
- **Run Initiatives 2 & 3 in parallel** (Buffer Safety + Mode Observability)
- **Initiative 5 (ADRs) can run anytime** - independent of others
- **Initiative 4 (Reference.py deprecation)** needs Initiative 1 complete first
- **Initiative 6 (List Navigation)** is a quick win - can run anytime

### Resource Allocation
- Initiatives 1, 2: Senior developer (complexity)
- Initiatives 3, 5, 6: Mid-level developer (lower complexity)
- Initiative 4: Team effort (large scope)

### Quick Wins First?
If you need early momentum:
1. Initiative 6 (List Navigation) - Low effort, visible impact
2. Initiative 5 (ADRs) - Low effort, helps onboarding
3. Then tackle the dragons (Initiatives 1-3)

### Big Impact First?
If you need risk reduction:
1. Initiative 1 (Dragon Documentation) - Foundational
2. Initiative 2 (Buffer Safety) - Data integrity
3. Initiative 3 (Mode Observability) - Debugging

---

## Next Steps

1. **Review & prioritize** these initiatives based on team capacity and goals
2. **Assign owners** for each initiative
3. **Break down Initiative 1** into incremental tasks (one dragon at a time)
4. **Set success metrics** and review cadence
5. **Communicate** the plan to the team

---

**End of Brief**  
*This synthesis represents 5 phases of cartographer analysis: structure, entry points, data flow, import graph, and dragon identification.*