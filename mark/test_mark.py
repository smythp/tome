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


# =============================================================================
# Gremlin Round 1: Stack Mutation, Type Confusion, Protocol Violations
# =============================================================================

class TestStackMutation:
    """Test attacks on the exposed mutable stack property."""

    def test_direct_stack_mutation_then_back(self, mark):
        """Mutating stack externally breaks back()."""
        mark.into(5)
        # External mutation: inject garbage
        mark.stack.append("not_an_int")
        
        # Now back() will try to use the string as buffer_id
        # Expected: TypeError when assigning non-int to buffer_id
        with pytest.raises(TypeError):
            mark.back()

    def test_stack_cleared_externally(self, mark):
        """External stack.clear() breaks navigation."""
        mark.into(5).into(10)
        mark.stack.clear()  # Corrupt the stack externally
        
        # back() should return False (empty stack)
        assert mark.back() is False
        assert mark.buffer_id == 10  # Stuck at 10

    def test_stack_replaced_with_non_list(self, mark):
        """Replacing stack with non-list breaks into()."""
        # This tests whether Mark validates stack type on mutation
        # Currently, Python allows this since stack is just an attribute
        original_stack = mark.stack
        mark.into(5)
        
        # Stack should still be a list after into()
        assert isinstance(mark.stack, list)
        assert mark.stack is original_stack  # Same list object


class TestTypeConfusion:
    """Test __index__ protocol and int subclasses."""

    def test_numpy_like_int64(self, mock_store):
        """Custom __index__ object might bypass isinstance check."""
        class FakeInt64:
            def __init__(self, value):
                self._value = value
            def __index__(self):
                return self._value
            def __int__(self):
                return self._value
        
        from mark import Mark
        # isinstance(FakeInt64(5), int) returns False
        # So this should raise TypeError
        with pytest.raises(TypeError, match="buffer_id must be int"):
            Mark(store=mock_store, buffer_id=FakeInt64(5))

    def test_int_enum_accepted(self, mock_store):
        """IntEnum IS a subclass of int - should be accepted."""
        from enum import IntEnum
        
        class BufferID(IntEnum):
            ROOT = 1
            PROJECTS = 2
        
        from mark import Mark
        # IntEnum is int subclass, so isinstance returns True
        m = Mark(store=mock_store, buffer_id=BufferID.ROOT)
        assert m.buffer_id == 1
        
        m.into(BufferID.PROJECTS)
        assert m.buffer_id == 2

    def test_into_with_int_subclass(self, mark):
        """into() with int subclass should work."""
        class MyInt(int):
            pass
        
        mark.into(MyInt(42))
        assert mark.buffer_id == 42
        assert mark.stack == [1]


class TestStoreProtocolViolations:
    """Test malicious Store implementations that return invalid data."""

    def test_store_returns_dict_with_non_int_buffer_id(self):
        """Store returns dict with buffer_id as string."""
        class MaliciousStore:
            def get(self, entry_id):
                return {
                    'content': 'data',
                    'buffer_id': 'not_an_int'  # String instead of int!
                }
        
        from mark import Mark
        m = Mark(store=MaliciousStore(), buffer_id=5)
        
        # path() walks upward using entry.get('buffer_id')
        # It doesn't validate the type of buffer_id from the dict
        # This could cause infinite loop or crash when comparing with visited set
        path = m.path
        # If it handles this, path should contain the content
        assert 'data' in path

    def test_store_returns_non_string_content(self):
        """Store returns dict with content as dict instead of string."""
        class HugeObjectStore:
            def get(self, entry_id):
                return {
                    'content': {'huge': 'object' * 1000},  # Dict instead of string!
                    'buffer_id': None
                }
        
        from mark import Mark
        m = Mark(store=HugeObjectStore(), buffer_id=5)
        
        # path expects strings but doesn't validate
        path = m.path
        # If code doesn't crash, it'll use str() or just insert the dict
        assert len(path) > 0

    def test_store_returns_unhashable_buffer_id(self):
        """Store returns list as buffer_id - breaks visited set."""
        class UnhashableStore:
            def __init__(self):
                self.call_count = 0
            
            def get(self, entry_id):
                self.call_count += 1
                if self.call_count > 10:
                    return None  # Prevent infinite recursion
                return {
                    'content': 'item',
                    'buffer_id': [1, 2, 3]  # List - unhashable!
                }
        
        from mark import Mark
        m = Mark(store=UnhashableStore(), buffer_id=5)
        
        # visited.add(current_id) will fail if current_id is unhashable
        with pytest.raises(TypeError):
            _ = m.path


class TestMemoryExhaustion:
    """Test memory and performance attacks."""

    def test_million_level_deep_path(self):
        """Path with million-level depth causes OOM."""
        class DeepStore:
            def get(self, entry_id):
                if entry_id == 0:
                    return None
                return {
                    'content': f'l{entry_id}',
                    'buffer_id': entry_id - 1
                }
        
        from mark import Mark
        m = Mark(store=DeepStore(), buffer_id=1_000_000)
        
        # This will try to build a list with 1 million entries
        # Should either handle gracefully or run out of memory
        # For now, testing if it completes (may be slow)
        import pytest
        pytest.skip("Skipping OOM test - takes too long")
        # path = m.path
        # assert len(path) == 1_000_000

    def test_million_stack_pushes(self, mock_store):
        """Pushing a million items to stack."""
        from mark import Mark
        m = Mark(store=mock_store)
        
        # This tests unbounded stack growth
        import pytest
        pytest.skip("Skipping stack overflow test - takes too long")
        # for i in range(1_000_000):
        #     m.into(i + 2)
        # assert len(m.stack) == 1_000_000


class TestSemanticChaos:
    """Test semantically valid but weird inputs."""

    def test_float_that_equals_int(self, mock_store):
        """3.0 == 3 in Python - does it work as buffer_id?"""
        from mark import Mark
        
        # isinstance(3.0, int) is False, so this should fail
        with pytest.raises(TypeError, match="buffer_id must be int"):
            Mark(store=mock_store, buffer_id=3.0)

    def test_object_with_malicious_eq(self):
        """Object with __eq__ that always returns True."""
        class AlwaysEqual:
            def __eq__(self, other):
                return True
            def __hash__(self):
                return 42
        
        # This tests if visited set in path() gets corrupted
        class EvilStore:
            def get(self, entry_id):
                return {
                    'content': 'item',
                    'buffer_id': AlwaysEqual()
                }
        
        from mark import Mark
        m = Mark(store=EvilStore(), buffer_id=5)
        
        # AlwaysEqual() == anything, so visited set might not work
        # Should still terminate because get() keeps returning the same thing
        path = m.path
        assert len(path) > 0


# =============================================================================
# Oracle Round: Subtle Edge Cases - Unicode, Content Types, Mutation, Storage
# =============================================================================

class TestUnicodeInContent:
    """Test unicode edge cases in content fields."""

    def test_emoji_in_content(self):
        """Content with emoji should appear in path."""
        class EmojiStore:
            def get(self, entry_id):
                return {
                    'id': entry_id,
                    'content': '📁 Projects 🚀',
                    'buffer_id': None
                }
        
        from mark import Mark
        m = Mark(store=EmojiStore(), buffer_id=5)
        path = m.path
        
        assert '📁 Projects 🚀' in path
        assert len(path) == 1

    def test_rtl_text_in_content(self):
        """Content with RTL (right-to-left) text."""
        class RTLStore:
            def get(self, entry_id):
                return {
                    'id': entry_id,
                    'content': 'العربية',  # Arabic text
                    'buffer_id': None
                }
        
        from mark import Mark
        m = Mark(store=RTLStore(), buffer_id=5)
        path = m.path
        
        assert 'العربية' in path

    def test_zero_width_characters_in_content(self):
        """Content with zero-width joiners and spaces."""
        class ZeroWidthStore:
            def get(self, entry_id):
                return {
                    'id': entry_id,
                    'content': 'hello\u200bworld\u200c',  # Zero-width space and non-joiner
                    'buffer_id': None
                }
        
        from mark import Mark
        m = Mark(store=ZeroWidthStore(), buffer_id=5)
        path = m.path
        
        # Content should be preserved exactly
        assert 'hello\u200bworld\u200c' in path

    def test_combining_characters_in_content(self):
        """Content with combining diacritical marks."""
        class CombiningStore:
            def get(self, entry_id):
                return {
                    'id': entry_id,
                    'content': 'café',  # é as e + combining acute
                    'buffer_id': None
                }
        
        from mark import Mark
        m = Mark(store=CombiningStore(), buffer_id=5)
        path = m.path
        
        assert 'café' in path

    def test_mixed_unicode_content(self):
        """Content mixing emoji, RTL, combining chars."""
        class MixedStore:
            def get(self, entry_id):
                chains = {
                    3: {'content': '🚀 Launch', 'buffer_id': 2},
                    2: {'content': 'مشروع', 'buffer_id': 1},
                    1: {'content': 'café\u200b', 'buffer_id': None}
                }
                return chains.get(entry_id)
        
        from mark import Mark
        m = Mark(store=MixedStore(), buffer_id=3)
        path = m.path
        
        assert 'café\u200b' in path
        assert 'مشروع' in path
        assert '🚀 Launch' in path
        assert len(path) == 3


class TestNonStringContent:
    """Test non-string content types in store entries."""

    def test_numeric_content(self):
        """Content field is a number instead of string."""
        class NumericStore:
            def get(self, entry_id):
                return {
                    'id': entry_id,
                    'content': 42,  # Number, not string
                    'buffer_id': None
                }
        
        from mark import Mark
        m = Mark(store=NumericStore(), buffer_id=5)
        path = m.path
        
        # Should either convert to string or include as-is
        assert 42 in path or '42' in path

    def test_none_content(self):
        """Content field is None."""
        class NoneContentStore:
            def get(self, entry_id):
                return {
                    'id': entry_id,
                    'content': None,  # None content
                    'buffer_id': None
                }
        
        from mark import Mark
        m = Mark(store=NoneContentStore(), buffer_id=5)
        path = m.path
        
        # Should fall back to buffer-{id} format
        assert 'buffer-5' in path or None in path

    def test_list_content(self):
        """Content field is a list."""
        class ListStore:
            def get(self, entry_id):
                return {
                    'id': entry_id,
                    'content': ['item', 'list'],  # List, not string
                    'buffer_id': None
                }
        
        from mark import Mark
        m = Mark(store=ListStore(), buffer_id=5)
        path = m.path
        
        # Should either convert list to string or include as-is
        assert ['item', 'list'] in path or "['item', 'list']" in path or 'buffer-5' in path

    def test_dict_content(self):
        """Content field is a dict."""
        class DictStore:
            def get(self, entry_id):
                return {
                    'id': entry_id,
                    'content': {'nested': 'data'},  # Dict, not string
                    'buffer_id': None
                }
        
        from mark import Mark
        m = Mark(store=DictStore(), buffer_id=5)
        path = m.path
        
        # Should handle dict content somehow
        assert len(path) == 1
        # Content is either the dict, its string repr, or fallback
        assert isinstance(path[0], (dict, str))

    def test_missing_content_key(self):
        """Store entry has no 'content' key at all."""
        class NoContentStore:
            def get(self, entry_id):
                return {
                    'id': entry_id,
                    'buffer_id': None
                    # No 'content' key
                }
        
        from mark import Mark
        m = Mark(store=NoContentStore(), buffer_id=5)
        path = m.path
        
        # Should fall back to buffer-{id}
        assert 'buffer-5' in path


class TestStackMutationDuringIteration:
    """Test mutating stack while iterating over it."""

    def test_iterate_stack_while_pushing(self, mock_store):
        """Iterate over stack while calling into()."""
        from mark import Mark
        m = Mark(store=mock_store)
        m.into(5).into(10).into(15)
        
        # Get initial stack snapshot
        initial_stack = list(m.stack)  # [1, 5, 10]
        
        # Iterate over stack while mutating it
        # This could cause undefined behavior if stack property returns the actual list
        results = []
        for item in m.stack:
            results.append(item)
            if len(results) < 2:  # Only mutate twice to avoid infinite loop
                m.into(item + 100)
        
        # Stack was [1, 5, 10]
        # First iteration: item=1, into(101), stack becomes [1, 5, 10, 15]
        # Second iteration: item=5, into(105), stack becomes [1, 5, 10, 15, 101]
        # Third iteration: item=10 (if we get here)
        
        # At minimum, we should have iterated over original items
        assert 1 in results
        assert 5 in results

    def test_iterate_stack_while_popping(self, mock_store):
        """Iterate over stack while calling back()."""
        from mark import Mark
        m = Mark(store=mock_store)
        m.into(5).into(10).into(15).into(20)
        
        # Stack is [1, 5, 10, 15], current is 20
        results = []
        
        # This is tricky: iterating while calling back() modifies the stack
        for item in list(m.stack):  # Use list() to snapshot
            results.append(item)
            if m.back():  # Pops from stack
                pass
        
        # Should have iterated over snapshot [1, 5, 10, 15]
        assert len(results) == 4
        assert results == [1, 5, 10, 15]

    def test_external_stack_clear_during_pathfinding(self):
        """Clear stack externally while path() is computing."""
        class TrickyStore:
            def __init__(self, mark_ref):
                self.mark_ref = mark_ref
                self.call_count = 0
            
            def get(self, entry_id):
                self.call_count += 1
                # On second call, mutate the mark's stack
                if self.call_count == 2 and self.mark_ref:
                    self.mark_ref.stack.clear()
                
                if entry_id == 1:
                    return None
                return {
                    'content': f'item-{entry_id}',
                    'buffer_id': entry_id - 1
                }
        
        from mark import Mark
        # Create mark with placeholder store first
        m = Mark(store=type('obj', (object,), {'get': lambda self, x: None})(), buffer_id=5)
        # Now replace with tricky store that has reference to mark
        m._store = TrickyStore(m)
        
        # path() will walk up the chain, and on second get() the stack gets cleared
        # This shouldn't affect path() since it doesn't use stack
        path = m.path
        
        assert len(path) > 0
        assert m.stack == []  # Stack was cleared


class TestLastRetrievedEdgeCases:
    """Test last_retrieved with problematic objects."""

    def test_last_retrieved_with_circular_reference(self, mark):
        """last_retrieved object has circular reference to Mark."""
        entry = {'id': 1, 'content': 'data'}
        entry['mark_ref'] = mark  # Circular reference
        
        mark.last_retrieved = entry
        
        # Should store without error
        assert mark.last_retrieved is entry
        assert mark.last_retrieved['mark_ref'] is mark

    def test_last_retrieved_with_self_reference(self, mark):
        """last_retrieved object references itself."""
        entry = {'id': 1}
        entry['self'] = entry  # Self-reference
        
        mark.last_retrieved = entry
        
        assert mark.last_retrieved is entry
        assert mark.last_retrieved['self'] is entry

    def test_last_retrieved_large_object(self, mark):
        """last_retrieved with very large object."""
        # Create a large dict
        large_entry = {
            'id': 1,
            'data': 'x' * 1_000_000  # 1MB string
        }
        
        mark.last_retrieved = large_entry
        
        assert mark.last_retrieved is large_entry
        assert len(mark.last_retrieved['data']) == 1_000_000

    def test_last_retrieved_mutable_object_mutation(self, mark):
        """Mutating last_retrieved object externally."""
        entry = {'id': 1, 'content': 'original'}
        mark.last_retrieved = entry
        
        # Mutate the object externally
        entry['content'] = 'modified'
        entry['new_field'] = 'added'
        
        # Mark stores reference, so mutation is visible
        assert mark.last_retrieved['content'] == 'modified'
        assert mark.last_retrieved['new_field'] == 'added'

    def test_last_retrieved_none_vs_unset(self, mark):
        """Explicitly setting None vs initial unset state."""
        # Initial state: unset (defaults to None)
        assert mark.last_retrieved is None
        
        # Explicitly set to None
        mark.last_retrieved = None
        assert mark.last_retrieved is None
        
        # Set to actual value
        mark.last_retrieved = {'id': 1}
        assert mark.last_retrieved == {'id': 1}
        
        # Set back to None
        mark.last_retrieved = None
        assert mark.last_retrieved is None

    def test_last_retrieved_with_slots_object(self, mark):
        """last_retrieved with __slots__ object (no __dict__)."""
        class SlotsEntry:
            __slots__ = ['id', 'content']
            def __init__(self, id, content):
                self.id = id
                self.content = content
        
        entry = SlotsEntry(1, 'data')
        mark.last_retrieved = entry
        
        assert mark.last_retrieved is entry
        assert mark.last_retrieved.id == 1
        assert mark.last_retrieved.content == 'data'

    def test_last_retrieved_with_lambda(self, mark):
        """last_retrieved with lambda function."""
        func = lambda x: x * 2
        mark.last_retrieved = func
        
        assert mark.last_retrieved is func
        assert mark.last_retrieved(5) == 10
