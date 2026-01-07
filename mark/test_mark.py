"""
Tests for Mark RSP - position and session state tracking.

Mark tracks where you are in hierarchical data:
- buffer_id: current position
- stack: navigation history (for back())
- last_retrieved: last entry accessed (opaque storage)
- path: human-readable breadcrumb (requires Store)
"""

import pytest


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_store():
    """Mock store that resolves buffer_ids to names."""
    class MockStore:
        def __init__(self):
            self._entries = {
                1: {'id': 1, 'buffer_id': None, 'content': 'root', 'type': 'buffer'},
                2: {'id': 2, 'buffer_id': 1, 'content': 'projects', 'type': 'buffer'},
                3: {'id': 3, 'buffer_id': 2, 'content': 'tome', 'type': 'buffer'},
            }

        def get(self, entry_id):
            return self._entries.get(entry_id)

    return MockStore()


@pytest.fixture
def mark(mock_store):
    """Fresh Mark at root with mock store."""
    from mark import Mark
    return Mark(store=mock_store)


@pytest.fixture
def mark_at_5(mock_store):
    """Mark starting at buffer_id 5."""
    from mark import Mark
    return Mark(store=mock_store, buffer_id=5)


# =============================================================================
# Construction
# =============================================================================

class TestConstruction:
    """Test Mark creation and defaults."""

    def test_requires_store(self):
        """Mark requires a store argument."""
        from mark import Mark
        with pytest.raises(TypeError):
            Mark()  # Missing store

    def test_default_buffer_id_is_root(self, mark):
        """Default buffer_id is 1 (root)."""
        assert mark.buffer_id == 1

    def test_default_stack_is_empty(self, mark):
        """Default stack is empty list."""
        assert mark.stack == []

    def test_default_last_retrieved_is_none(self, mark):
        """Default last_retrieved is None."""
        assert mark.last_retrieved is None

    def test_custom_initial_buffer_id(self, mock_store):
        """Can set initial buffer_id."""
        from mark import Mark
        m = Mark(store=mock_store, buffer_id=5)
        assert m.buffer_id == 5

    def test_custom_initial_does_not_affect_stack(self, mock_store):
        """Custom initial buffer_id doesn't add to stack."""
        from mark import Mark
        m = Mark(store=mock_store, buffer_id=5)
        assert m.stack == []

    def test_stack_not_shared_between_instances(self, mock_store):
        """Each Mark has its own stack."""
        from mark import Mark
        a = Mark(store=mock_store)
        b = Mark(store=mock_store)
        a.into(2)
        assert a.stack == [1]
        assert b.stack == []


# =============================================================================
# Validation
# =============================================================================

class TestValidation:
    """Test input validation."""

    def test_buffer_id_must_be_int_on_construction(self, mock_store):
        """buffer_id must be int at construction."""
        from mark import Mark
        with pytest.raises(TypeError, match="buffer_id must be int"):
            Mark(store=mock_store, buffer_id="5")

    def test_buffer_id_must_be_int_on_into(self, mark):
        """into() requires int buffer_id."""
        with pytest.raises(TypeError, match="buffer_id must be int"):
            mark.into("5")

    def test_buffer_id_none_rejected(self, mock_store):
        """None is not a valid buffer_id."""
        from mark import Mark
        with pytest.raises(TypeError, match="buffer_id must be int"):
            Mark(store=mock_store, buffer_id=None)

    def test_buffer_id_dict_rejected(self, mark):
        """Dict is not a valid buffer_id."""
        with pytest.raises(TypeError, match="buffer_id must be int"):
            mark.into({"id": 5})


# =============================================================================
# Navigation: into()
# =============================================================================

class TestInto:
    """Test into() - navigate into a buffer."""

    def test_into_updates_buffer_id(self, mark):
        """into() sets new buffer_id."""
        mark.into(5)
        assert mark.buffer_id == 5

    def test_into_pushes_previous_to_stack(self, mark):
        """into() pushes previous buffer_id to stack."""
        mark.into(5)
        assert mark.stack == [1]

    def test_into_multiple_builds_stack(self, mark):
        """Multiple into() calls build up stack."""
        mark.into(5)
        mark.into(10)
        mark.into(20)
        assert mark.buffer_id == 20
        assert mark.stack == [1, 5, 10]

    def test_into_same_buffer_still_pushes(self, mark_at_5):
        """into() same buffer_id still pushes to stack."""
        mark_at_5.into(5)
        assert mark_at_5.buffer_id == 5
        assert mark_at_5.stack == [5]

    def test_into_returns_self(self, mark):
        """into() returns self for chaining."""
        result = mark.into(5)
        assert result is mark

    def test_into_chaining(self, mark):
        """Can chain into() calls."""
        mark.into(5).into(10).into(20)
        assert mark.buffer_id == 20
        assert mark.stack == [1, 5, 10]

    def test_into_preserves_stack_identity(self, mark):
        """into() mutates existing stack list, doesn't replace."""
        stack_before = mark.stack
        mark.into(5)
        assert mark.stack is stack_before


# =============================================================================
# Navigation: back()
# =============================================================================

class TestBack:
    """Test back() - return to previous buffer."""

    def test_back_pops_stack_to_current(self, mark):
        """back() pops stack and sets as current."""
        mark.into(5)
        mark.back()
        assert mark.buffer_id == 1
        assert mark.stack == []

    def test_back_returns_true_on_success(self, mark):
        """back() returns True when stack had items."""
        mark.into(5)
        assert mark.back() is True

    def test_back_returns_false_when_empty(self, mark):
        """back() returns False when stack is empty."""
        assert mark.back() is False

    def test_back_does_not_change_buffer_when_empty(self, mark_at_5):
        """back() doesn't change buffer_id when stack empty."""
        mark_at_5.back()
        assert mark_at_5.buffer_id == 5

    def test_back_is_idempotent_when_empty(self, mark_at_5):
        """Repeated back() on empty stack is stable no-op."""
        mark_at_5.back()
        mark_at_5.back()
        mark_at_5.back()
        assert mark_at_5.buffer_id == 5
        assert mark_at_5.stack == []

    def test_back_multiple_unwinds_stack(self, mark):
        """Multiple back() calls unwind the stack."""
        mark.into(5).into(10).into(20)

        assert mark.back() is True
        assert mark.buffer_id == 10

        assert mark.back() is True
        assert mark.buffer_id == 5

        assert mark.back() is True
        assert mark.buffer_id == 1

        assert mark.back() is False

    def test_back_preserves_stack_identity(self, mark):
        """back() mutates existing stack list, doesn't replace."""
        mark.into(5)
        stack_before = mark.stack
        mark.back()
        assert mark.stack is stack_before


# =============================================================================
# Navigation: reset()
# =============================================================================

class TestReset:
    """Test reset() - return to root."""

    def test_reset_clears_stack(self, mark):
        """reset() empties the stack."""
        mark.into(5).into(10).into(20)
        mark.reset()
        assert mark.stack == []

    def test_reset_returns_to_root(self, mark):
        """reset() sets buffer_id to 1 (root)."""
        mark.into(5).into(10)
        mark.reset()
        assert mark.buffer_id == 1

    def test_reset_from_root_is_noop(self, mark):
        """reset() at root is harmless."""
        mark.reset()
        assert mark.buffer_id == 1
        assert mark.stack == []

    def test_reset_returns_self(self, mark):
        """reset() returns self for chaining."""
        result = mark.reset()
        assert result is mark


# =============================================================================
# Round-trip Invariants
# =============================================================================

class TestRoundTrip:
    """Test navigation invariants."""

    def test_full_unwind_returns_to_start(self, mock_store):
        """After into chain then full back(), return to start."""
        from mark import Mark
        m = Mark(store=mock_store, buffer_id=99)

        m.into(100).into(101).into(102)

        while m.back():
            pass

        assert m.buffer_id == 99
        assert m.stack == []

    def test_back_then_into_pushes_current(self, mark):
        """After back(), next into() pushes the new current."""
        mark.into(2).into(3)  # stack=[1,2], current=3
        mark.back()            # stack=[1], current=2
        mark.into(10)          # should push 2

        assert mark.buffer_id == 10
        assert mark.stack == [1, 2]

    def test_deep_navigation(self, mark):
        """Can handle deep navigation stack."""
        for i in range(100):
            mark.into(i + 2)

        assert len(mark.stack) == 100
        assert mark.buffer_id == 101

        for _ in range(100):
            assert mark.back() is True

        assert mark.buffer_id == 1
        assert mark.back() is False


# =============================================================================
# last_retrieved
# =============================================================================

class TestLastRetrieved:
    """Test last_retrieved tracking."""

    def test_set_last_retrieved(self, mark):
        """Can set last_retrieved to an entry."""
        entry = {'id': 1, 'content': 'hello'}
        mark.last_retrieved = entry
        assert mark.last_retrieved == entry

    def test_last_retrieved_preserves_identity(self, mark):
        """last_retrieved stores exact object, not copy."""
        entry = {'id': 1, 'content': 'hello'}
        mark.last_retrieved = entry
        assert mark.last_retrieved is entry

    def test_last_retrieved_persists_through_navigation(self, mark):
        """last_retrieved unchanged by into/back."""
        entry = {'id': 1, 'content': 'hello'}
        mark.last_retrieved = entry
        mark.into(5).into(10)
        mark.back()
        assert mark.last_retrieved is entry

    def test_last_retrieved_persists_through_reset(self, mark):
        """last_retrieved unchanged by reset."""
        entry = {'id': 1}
        mark.last_retrieved = entry
        mark.into(5)
        mark.reset()
        assert mark.last_retrieved is entry

    def test_last_retrieved_can_be_cleared(self, mark):
        """Can clear last_retrieved by setting to None."""
        mark.last_retrieved = {'id': 1}
        mark.last_retrieved = None
        assert mark.last_retrieved is None

    def test_last_retrieved_accepts_any_type(self, mark):
        """last_retrieved is opaque storage (Any)."""
        sentinel = object()
        mark.last_retrieved = sentinel
        assert mark.last_retrieved is sentinel


# =============================================================================
# path property
# =============================================================================

class TestPath:
    """Test path property - human-readable breadcrumb."""

    def test_path_at_root(self, mark):
        """Path at root shows root."""
        # Exact format TBD, but should include root
        path = mark.path
        assert isinstance(path, list)
        assert 'root' in path

    def test_path_shows_breadcrumb(self, mark):
        """Path shows navigation breadcrumb."""
        mark.into(2)  # projects
        mark.into(3)  # tome

        path = mark.path
        assert 'root' in path
        assert 'projects' in path
        assert 'tome' in path

    def test_path_order_is_root_to_current(self, mark):
        """Path is ordered from root to current."""
        mark.into(2).into(3)
        path = mark.path

        root_idx = path.index('root')
        projects_idx = path.index('projects')
        tome_idx = path.index('tome')

        assert root_idx < projects_idx < tome_idx

    def test_path_updates_after_back(self, mark):
        """Path reflects current position after back()."""
        mark.into(2).into(3)
        mark.back()

        path = mark.path
        assert 'projects' in path
        assert 'tome' not in path

    def test_path_updates_after_reset(self, mark):
        """Path reflects root after reset()."""
        mark.into(2).into(3)
        mark.reset()

        path = mark.path
        assert path == ['root']


# =============================================================================
# Round 0: Hardening Tests - Adversarial and Edge Cases
# =============================================================================

class TestBooleanSubclassing:
    """Test bool subclass of int edge cases."""

    def test_construction_with_true(self, mock_store):
        """True (1) is accepted as buffer_id."""
        from mark import Mark
        m = Mark(store=mock_store, buffer_id=True)
        assert m.buffer_id == 1

    def test_construction_with_false(self, mock_store):
        """False (0) is accepted as buffer_id."""
        from mark import Mark
        m = Mark(store=mock_store, buffer_id=False)
        assert m.buffer_id == 0

    def test_into_with_true(self, mark):
        """into(True) navigates to buffer_id 1."""
        mark.into(True)
        assert mark.buffer_id == 1
        assert mark.stack == [1]  # Pushed original 1

    def test_into_with_false(self, mark):
        """into(False) navigates to buffer_id 0."""
        mark.into(False)
        assert mark.buffer_id == 0
        assert mark.stack == [1]


class TestExtremeNumericValues:
    """Test extreme numeric buffer_ids."""

    def test_negative_buffer_id_construction(self, mock_store):
        """Negative buffer_ids are accepted."""
        from mark import Mark
        m = Mark(store=mock_store, buffer_id=-1)
        assert m.buffer_id == -1

    def test_zero_buffer_id(self, mock_store):
        """Zero buffer_id is accepted."""
        from mark import Mark
        m = Mark(store=mock_store, buffer_id=0)
        assert m.buffer_id == 0

    def test_large_buffer_id(self, mock_store):
        """Very large buffer_ids are accepted."""
        from mark import Mark
        import sys
        m = Mark(store=mock_store, buffer_id=sys.maxsize)
        assert m.buffer_id == sys.maxsize

    def test_into_negative(self, mark):
        """Can navigate into negative buffer_id."""
        mark.into(-5)
        assert mark.buffer_id == -5

    def test_into_very_large(self, mark):
        """Can navigate into very large buffer_id."""
        import sys
        mark.into(sys.maxsize)
        assert mark.buffer_id == sys.maxsize


class TestMaliciousStore:
    """Test Mark with pathological Store implementations."""

    def test_store_get_raises_exception(self, mark):
        """path handles Store.get() raising exceptions."""
        class ExplodingStore:
            def get(self, entry_id):
                raise RuntimeError("Store exploded!")

        from mark import Mark
        m = Mark(store=ExplodingStore(), buffer_id=5)

        # path() should handle the exception gracefully
        with pytest.raises(RuntimeError):
            _ = m.path

    def test_store_get_returns_non_dict(self):
        """path handles Store.get() returning non-dict."""
        class BadStore:
            def get(self, entry_id):
                return "not a dict"

        from mark import Mark
        m = Mark(store=BadStore(), buffer_id=5)

        # Should handle gracefully - .get() on string will raise AttributeError
        with pytest.raises(AttributeError):
            _ = m.path

    def test_store_get_returns_dict_without_content(self):
        """path handles dict without 'content' key."""
        class MinimalStore:
            def get(self, entry_id):
                return {'buffer_id': None}  # Missing 'content'

        from mark import Mark
        m = Mark(store=MinimalStore(), buffer_id=5)

        # Should use fallback 'buffer-5'
        path = m.path
        assert path == ['buffer-5']

    def test_store_get_returns_dict_without_buffer_id(self):
        """path handles dict without 'buffer_id' key."""
        class NoParentStore:
            def get(self, entry_id):
                return {'content': 'orphan'}  # Missing 'buffer_id'

        from mark import Mark
        m = Mark(store=NoParentStore(), buffer_id=5)

        # Should terminate walk when buffer_id is None
        path = m.path
        assert path == ['orphan']


class TestCircularPaths:
    """Test circular reference handling in path computation."""

    def test_self_referencing_entry(self):
        """path detects self-referencing entry."""
        class CircularStore:
            def get(self, entry_id):
                return {
                    'content': f'buffer-{entry_id}',
                    'buffer_id': entry_id  # Points to self!
                }

        from mark import Mark
        m = Mark(store=CircularStore(), buffer_id=5)

        # visited set should prevent infinite loop
        path = m.path
        assert path == ['buffer-5']
        assert len(path) == 1

    def test_two_entry_cycle(self):
        """path detects two-entry cycle."""
        class TwoEntryCycle:
            def get(self, entry_id):
                if entry_id == 5:
                    return {'content': 'five', 'buffer_id': 10}
                elif entry_id == 10:
                    return {'content': 'ten', 'buffer_id': 5}  # Points back!
                return None

        from mark import Mark
        m = Mark(store=TwoEntryCycle(), buffer_id=5)

        # Should break cycle
        path = m.path
        assert 'five' in path
        assert len(path) <= 2  # Should terminate

    def test_long_chain_with_eventual_cycle(self):
        """path handles long chain that eventually cycles."""
        class EventualCycle:
            def get(self, entry_id):
                chains = {
                    1: {'content': 'one', 'buffer_id': 2},
                    2: {'content': 'two', 'buffer_id': 3},
                    3: {'content': 'three', 'buffer_id': 1},  # Cycles back to 1
                }
                return chains.get(entry_id)

        from mark import Mark
        m = Mark(store=EventualCycle(), buffer_id=1)

        path = m.path
        # Should collect one, two, three before detecting cycle
        assert 'one' in path
        assert 'two' in path
        assert 'three' in path
        assert len(path) == 3


class TestDeepHierarchies:
    """Test very deep navigation and hierarchies."""

    def test_very_deep_navigation(self, mock_store):
        """Can handle very deep navigation (10000 levels)."""
        from mark import Mark
        m = Mark(store=mock_store)

        # Navigate 10000 levels deep
        for i in range(10000):
            m.into(i + 2)

        assert len(m.stack) == 10000
        assert m.buffer_id == 10001

        # Unwind all the way
        for _ in range(10000):
            assert m.back() is True

        assert m.buffer_id == 1
        assert m.stack == []

    def test_very_deep_path_computation(self):
        """path can handle very deep hierarchies."""
        class DeepStore:
            def get(self, entry_id):
                if entry_id == 0:
                    return None
                return {
                    'content': f'level-{entry_id}',
                    'buffer_id': entry_id - 1
                }

        from mark import Mark
        m = Mark(store=DeepStore(), buffer_id=1000)

        # Should walk 1000 -> 999 -> ... -> 1 -> 0 (None)
        path = m.path
        assert len(path) == 1000
        assert path[0] == 'level-1'
        assert path[-1] == 'level-1000'
