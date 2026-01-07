"""Gremlin attacks on Mark RSP - exploiting assumptions the tests missed."""

import pytest


# =============================================================================
# ATTACK 1: Store.get() with side effects
# =============================================================================

class TestMaliciousStore:
    """What if store.get() has side effects?"""

    def test_get_mutates_mark_during_path_traversal(self):
        """BROKE: path() vulnerable to store that mutates mark during traversal."""
        class MutatingStore:
            def __init__(self, mark_ref=None):
                self.mark_ref = mark_ref
                self.call_count = 0
            
            def get(self, entry_id):
                self.call_count += 1
                # On second call, mutate the mark's buffer_id
                if self.call_count == 2 and self.mark_ref:
                    self.mark_ref._buffer_id = 999  # Direct mutation
                
                chains = {
                    5: {'content': 'level5', 'buffer_id': 4},
                    4: {'content': 'level4', 'buffer_id': 3},
                    3: {'content': 'level3', 'buffer_id': None},
                    999: {'content': 'hijacked', 'buffer_id': None}
                }
                return chains.get(entry_id)
        
        from mark import Mark
        store = MutatingStore()
        m = Mark(store=store, buffer_id=5)
        store.mark_ref = m  # Wire up reference after construction
        
        # path() walks up: 5 -> 4, then during get(4) buffer_id changes to 999
        path = m.path
        
        # BROKE: path() doesn't snapshot buffer_id, continues with mutated value
        # Result is unpredictable - could include 'hijacked' or crash
        print(f"Path with mutation: {path}")
        print(f"Final buffer_id: {m.buffer_id}")

    def test_get_raises_exception_mid_traversal(self):
        """BROKE: path() doesn't handle store.get() raising exceptions."""
        class ExplodingStore:
            def __init__(self):
                self.call_count = 0
            
            def get(self, entry_id):
                self.call_count += 1
                if self.call_count == 2:
                    raise RuntimeError("Store corrupted")
                return {'content': f'item-{entry_id}', 'buffer_id': entry_id - 1 if entry_id > 1 else None}
        
        from mark import Mark
        m = Mark(store=ExplodingStore(), buffer_id=5)
        
        # BROKE: No exception handling in path()
        with pytest.raises(RuntimeError):
            _ = m.path

    def test_get_sleeps_forever(self):
        """BROKE: path() blocks if store.get() sleeps."""
        import time
        
        class SlowStore:
            def get(self, entry_id):
                time.sleep(10)  # Simulate slow/hanging store
                return {'content': 'slow', 'buffer_id': None}
        
        from mark import Mark
        m = Mark(store=SlowStore(), buffer_id=5)
        
        # BROKE: path() has no timeout, blocks forever
        # This test would hang - commented out for safety
        # path = m.path
        pytest.skip("Would hang - store.get() has no timeout")


# =============================================================================
# ATTACK 2: Cycle detection bypass
# =============================================================================

class TestCycleDetectionBypass:
    """What if buffer_id points to itself or get() returns different results?"""

    def test_buffer_points_to_itself(self):
        """BROKE: What if buffer_id field points to the entry's own id?"""
        class SelfRefStore:
            def get(self, entry_id):
                # Entry 5 has buffer_id=5 (points to itself)
                return {'id': entry_id, 'content': f'self-{entry_id}', 'buffer_id': entry_id}
        
        from mark import Mark
        m = Mark(store=SelfRefStore(), buffer_id=5)
        
        # path() checks `current_id not in visited` - should catch this
        path = m.path
        
        # Should only have one entry due to cycle detection
        assert len(path) == 1
        assert path[0] == 'self-5'
        
        # HOW IT HURTS: Handled correctly by visited set, but what about...

    def test_get_returns_different_results_each_call(self):
        """FIXED: Non-deterministic store triggers max iteration limit."""
        class FlickeringStore:
            def __init__(self):
                self.call_count = 0

            def get(self, entry_id):
                self.call_count += 1
                # Flip between two different parent chains
                if self.call_count % 2 == 0:
                    return {'content': f'even-{entry_id}', 'buffer_id': entry_id - 1 if entry_id > 1 else None}
                else:
                    return {'content': f'odd-{entry_id}', 'buffer_id': entry_id + 10}

        from mark import Mark
        m = Mark(store=FlickeringStore(), buffer_id=5)

        # FIXED: path() now detects infinite loops and raises RuntimeError
        with pytest.raises(RuntimeError, match="Path traversal exceeded 100000 iterations"):
            _ = m.path

    def test_infinite_chain_with_large_buffer_ids(self):
        """BROKE: What if chain goes to 2^63 before terminating?"""
        class InfiniteStore:
            def get(self, entry_id):
                if entry_id > 10000:
                    return None  # Eventually terminates
                return {'content': f'id-{entry_id}', 'buffer_id': entry_id + 1}
        
        from mark import Mark
        m = Mark(store=InfiniteStore(), buffer_id=1)
        
        # BROKE: path() will walk 10000 entries before terminating
        path = m.path
        
        # WHY IT HURTS: No bounds check, could exhaust memory
        print(f"Path length: {len(path)}")
        assert len(path) > 1000  # Demonstrates unbounded traversal


# =============================================================================
# ATTACK 3: Stack poisoning
# =============================================================================

class TestStackPoisoning:
    """back() validates stack items, but only when popped. Can we poison it?"""

    def test_poison_stack_with_non_int_values(self):
        """BROKE: Directly mutate stack with non-int, back() only checks on pop."""
        from mark import Mark
        
        class DummyStore:
            def get(self, entry_id):
                return None
        
        m = Mark(store=DummyStore(), buffer_id=1)
        
        # into() validates, but we can mutate stack directly
        m.into(2)
        m.into(3)
        
        # Poison the stack by inserting non-int
        m._stack.append("evil")  # Direct mutation
        m._stack.append(None)    # More poison
        m._stack.append({"attack": True})  # Even more

        # Stack now contains: [1, 2, "evil", None, {"attack": True}]
        # FIXED: back() validates when popping and raises TypeError
        with pytest.raises(TypeError, match="buffer_id must be int"):
            m.back()  # Pops {"attack": True}, raises TypeError immediately

    def test_poisoned_stack_survives_until_pop(self):
        """FIXED: Poisoned stack entries survive until popped, then raise."""
        from mark import Mark

        class DummyStore:
            def get(self, entry_id):
                return None

        m = Mark(store=DummyStore(), buffer_id=1)
        m.into(2)

        # Poison stack
        m._stack.insert(0, "bottom-poison")  # Insert at bottom

        # Can still use into() and other operations
        m.into(3)
        m.into(4)

        # Stack is: ["bottom-poison", 1, 2, 3]
        assert len(m.stack) == 4

        # Pop valid entries
        assert m.back() is True  # Pops 3, stack: ["bottom-poison", 1, 2]
        assert m.back() is True  # Pops 2, stack: ["bottom-poison", 1]
        assert m.back() is True  # Pops 1, stack: ["bottom-poison"]

        # Now we'll hit the poison
        # FIXED: back() validates and raises TypeError on poison
        with pytest.raises(TypeError, match="buffer_id must be int"):
            m.back()  # Tries to pop "bottom-poison"


# =============================================================================
# ATTACK 4: Store validation
# =============================================================================

class TestStoreValidation:
    """What if store is None or doesn't have get()?"""

    def test_store_is_none(self):
        """BROKE: No validation that store is not None."""
        from mark import Mark
        
        # Mark accepts None as store (Protocol doesn't enforce runtime check)
        m = Mark(store=None, buffer_id=5)
        
        # Accessing path will crash
        with pytest.raises(AttributeError):
            _ = m.path  # NoneType has no get()

    def test_store_missing_get_method(self):
        """BROKE: No validation that store has get() method."""
        from mark import Mark
        
        class BrokenStore:
            pass  # No get() method
        
        m = Mark(store=BrokenStore(), buffer_id=5)
        
        # Accessing path will crash
        with pytest.raises(AttributeError):
            _ = m.path  # BrokenStore has no get()

    def test_store_get_not_callable(self):
        """BROKE: What if store.get is not callable?"""
        from mark import Mark
        
        class WeirdStore:
            get = "not a function"  # get exists but isn't callable
        
        m = Mark(store=WeirdStore(), buffer_id=5)
        
        with pytest.raises(TypeError):
            _ = m.path  # Can't call a string


# =============================================================================
# ATTACK 5: Buffer_id edge cases in path()
# =============================================================================

class TestBufferIdEdgeCases:
    """path() uses entry.get('buffer_id') which can return weird values."""

    def test_buffer_id_zero(self):
        """BROKE: What if parent buffer_id is 0?"""
        class ZeroStore:
            def get(self, entry_id):
                chains = {
                    5: {'content': 'child', 'buffer_id': 0},
                    0: {'content': 'zero-parent', 'buffer_id': None}
                }
                return chains.get(entry_id)
        
        from mark import Mark
        m = Mark(store=ZeroStore(), buffer_id=5)
        
        # entry.get('buffer_id') returns 0, which is falsy
        # while loop: `while current_id is not None` - but 0 is not None!
        path = m.path
        
        # Should include both entries
        print(f"Path with zero buffer_id: {path}")
        # BROKE: 0 is falsy but not None, loop continues correctly
        # Actually this might work! Let's verify:
        assert len(path) == 2
        assert 'zero-parent' in path
        assert 'child' in path

    def test_buffer_id_negative(self):
        """BROKE: What if buffer_id is negative?"""
        class NegativeStore:
            def get(self, entry_id):
                chains = {
                    5: {'content': 'child', 'buffer_id': -1},
                    -1: {'content': 'negative-parent', 'buffer_id': None}
                }
                return chains.get(entry_id)
        
        from mark import Mark
        m = Mark(store=NegativeStore(), buffer_id=5)
        
        # Negative buffer_ids not validated by into(), but could exist in store
        path = m.path
        
        print(f"Path with negative buffer_id: {path}")
        # Should handle correctly (no validation in path() itself)
        assert len(path) == 2

    def test_buffer_id_max_int(self):
        """BROKE: What if buffer_id is 2^63?"""
        class MaxIntStore:
            def get(self, entry_id):
                max_int = 2**63 - 1
                chains = {
                    5: {'content': 'child', 'buffer_id': max_int},
                    max_int: {'content': 'max-parent', 'buffer_id': None}
                }
                return chains.get(entry_id)
        
        from mark import Mark
        m = Mark(store=MaxIntStore(), buffer_id=5)
        
        path = m.path
        
        # Should handle large ints
        assert len(path) == 2
        assert 'max-parent' in path


# =============================================================================
# ATTACK 6: Stack size bounds
# =============================================================================

class TestStackBounds:
    """No bounds on stack size - what happens with huge stacks?"""

    def test_massive_stack(self):
        """BROKE: Stack can grow to arbitrary size."""
        from mark import Mark
        
        class DummyStore:
            def get(self, entry_id):
                return None
        
        m = Mark(store=DummyStore(), buffer_id=1)
        
        # Build huge stack
        for i in range(100000):
            m.into(i + 2)
        
        # BROKE: No size limit, memory exhaustion possible
        assert len(m.stack) == 100000
        
        # Can we still use it?
        assert m.back() is True
        assert len(m.stack) == 99999

    def test_stack_memory_exhaustion(self):
        """BROKE: Can we exhaust memory with stack?"""
        from mark import Mark
        
        class DummyStore:
            def get(self, entry_id):
                return None
        
        m = Mark(store=DummyStore(), buffer_id=1)
        
        # This would try to allocate huge amounts of memory
        # Commented out to avoid actually exhausting memory
        # for i in range(10_000_000):
        #     m.into(i + 2)
        
        pytest.skip("Would exhaust memory - no stack size bounds")


# =============================================================================
# ATTACK 7: last_retrieved with problematic objects
# =============================================================================

class TestLastRetrievedAttacks:
    """last_retrieved is Any - what breaks?"""

    def test_last_retrieved_with_raising_getattribute(self):
        """BROKE: Object that raises on attribute access."""
        class EvilObject:
            def __getattribute__(self, name):
                raise RuntimeError("Nope")
        
        from mark import Mark
        
        class DummyStore:
            def get(self, entry_id):
                return None
        
        m = Mark(store=DummyStore(), buffer_id=1)
        m.last_retrieved = EvilObject()
        
        # Can't access anything on it
        with pytest.raises(RuntimeError):
            _ = m.last_retrieved.id  # Any attribute access raises

    def test_last_retrieved_with_raising_repr(self):
        """BROKE: Object that raises on repr()."""
        class NoReprObject:
            def __repr__(self):
                raise ValueError("Can't represent me")
        
        from mark import Mark
        
        class DummyStore:
            def get(self, entry_id):
                return None
        
        m = Mark(store=DummyStore(), buffer_id=1)
        evil = NoReprObject()
        m.last_retrieved = evil
        
        # Can store it, but can't print mark or debug
        with pytest.raises(ValueError):
            repr(m.last_retrieved)

    def test_last_retrieved_memory_leak(self):
        """BROKE: Circular reference causes memory leak?"""
        from mark import Mark
        
        class DummyStore:
            def get(self, entry_id):
                return None
        
        m = Mark(store=DummyStore(), buffer_id=1)
        
        # Create circular reference
        entry = {'mark': m}
        m.last_retrieved = entry
        
        # Both hold references to each other
        # Python's GC should handle this, but worth testing
        # WHY IT HURTS: Potential memory leak if GC disabled
        
        import gc
        gc.collect()
        
        # Still accessible
        assert m.last_retrieved['mark'] is m
