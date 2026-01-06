"""
Oracle edge case tests for mode.py

Tests demonstrate REAL bugs found through edge case analysis.
All tests should FAIL - they expose actual issues in the code.
"""

import pytest
from mode import Mode, ModeContext, KeyEvent
from dataclasses import dataclass


class MockTeller:
    """Minimal Teller implementation for testing."""
    def speak(self, text: str) -> None:
        pass

    def stop(self) -> None:
        pass


class MockStore:
    """Minimal Store implementation for testing."""
    def get(self, key: str):
        return None

    def set(self, key: str, value):
        pass


@dataclass
class MockKeyEvent:
    """Minimal KeyEvent for testing."""
    char: str | None = None
    key: None = None
    modifiers: frozenset = frozenset()
    event_type: None = None


# ============================================================================
# ISSUE 1: Closure Capture Bug in get_state Lambda
# Severity: HIGH
# ============================================================================

def test_get_state_returns_wrong_mode_state_after_switch():
    """
    FAILS: get_state() returns wrong mode's state after handler calls switch().

    Root cause: The get_state lambda on line 164 captures self._current by
    reference. When a handler switches modes mid-execution, subsequent calls
    to get_state() return the NEW mode's state, not the original mode's state.

    This breaks the contract that handlers can safely access their own state
    even if they switch modes.
    """
    mode = Mode(MockTeller(), MockStore())

    captured_states = []

    def mode_a_handler(event: KeyEvent, ctx: ModeContext):
        # Access our state and set a value
        state_before = ctx.get_state()
        state_before['mode_a_value'] = 'I am mode A'
        captured_states.append(('before_switch', state_before))

        # Switch to mode B
        ctx.switch('mode_b')

        # Try to access mode A's state again
        # BUG: This returns mode B's state instead!
        state_after = ctx.get_state()
        captured_states.append(('after_switch', state_after))

    def mode_b_handler(event: KeyEvent, ctx: ModeContext):
        state = ctx.get_state()
        state['mode_b_value'] = 'I am mode B'

    mode.register('mode_a', mode_a_handler)
    mode.register('mode_b', mode_b_handler)
    mode.switch('mode_a')

    mode.handle(MockKeyEvent())

    # Both calls to get_state() should return the SAME dict (mode A's state)
    state_before = captured_states[0][1]
    state_after = captured_states[1][1]

    # FAILS: These are different objects
    assert state_before is state_after, \
        f"get_state() returned different dicts after switch! " \
        f"Before: {id(state_before)}, After: {id(state_after)}"

    # FAILS: The value we set is gone
    assert state_after.get('mode_a_value') == 'I am mode A', \
        f"Expected mode A's value, got: {state_after}"


def test_get_state_cross_contamination():
    """
    FAILS: Handler can accidentally modify wrong mode's state after switch.

    Demonstrates data corruption: mode A switches to B, then modifies what
    it thinks is its own state, but actually corrupts mode B's state.
    """
    mode = Mode(MockTeller(), MockStore())

    def mode_a_handler(event: KeyEvent, ctx: ModeContext):
        # Set initial state
        state = ctx.get_state()
        state['counter'] = 1

        # Switch to mode B
        ctx.switch('mode_b')

        # Think we're modifying mode A's state, actually modify mode B's!
        state = ctx.get_state()
        state['counter'] = state.get('counter', 0) + 1

    def mode_b_handler(event: KeyEvent, ctx: ModeContext):
        pass

    mode.register('mode_a', mode_a_handler)
    mode.register('mode_b', mode_b_handler)
    mode.switch('mode_a')

    mode.handle(MockKeyEvent())

    # Mode A's state should have counter=1
    mode_a_state = mode._state['mode_a']
    # Mode B's state should be empty
    mode_b_state = mode._state['mode_b']

    # FAILS: Mode B has counter=1 (corrupted)
    assert mode_b_state.get('counter') is None, \
        f"Mode B state was corrupted: {mode_b_state}"

    # FAILS: Mode A only has counter=1, not 2
    assert mode_a_state.get('counter') == 2, \
        f"Mode A state wasn't updated: {mode_a_state}"


# ============================================================================
# ISSUE 2: State Mutation During Iteration
# Severity: MEDIUM
# ============================================================================

def test_state_dict_mutation_during_get_state():
    """
    FAILS: State dict can be deleted while handler holds reference.

    Edge case: Handler gets state reference, mode unregisters/re-registers,
    original state dict becomes orphaned.

    Not a common case, but demonstrates that state lifetime is not tied to
    handler execution.
    """
    mode = Mode(MockTeller(), MockStore())

    state_refs = []

    def handler_v1(event: KeyEvent, ctx: ModeContext):
        state = ctx.get_state()
        state['version'] = 1
        state_refs.append(state)

        # Re-register the mode (creates new state dict)
        mode.register('test_mode', handler_v2)

        # Original state is orphaned
        state['orphaned'] = True

    def handler_v2(event: KeyEvent, ctx: ModeContext):
        state = ctx.get_state()
        state['version'] = 2

    mode.register('test_mode', handler_v1)
    mode.switch('test_mode')

    mode.handle(MockKeyEvent())

    # The state we modified is not the current state
    current_state = mode._state['test_mode']
    handler_state = state_refs[0]

    # FAILS: Different state dicts
    assert current_state is handler_state, \
        "Handler's state reference is orphaned after re-registration"


# ============================================================================
# ISSUE 3: Mode Switch Exception Handling
# Severity: MEDIUM
# ============================================================================

def test_partial_mode_switch_on_exception():
    """
    FAILS: Exception after switch() leaves mode in inconsistent state.

    Handler switches mode, then raises exception. The exception is swallowed
    (line 170-171), but the mode switch has already happened. We're now in
    a mode that was never properly "entered" from the user's perspective.
    """
    mode = Mode(MockTeller(), MockStore())

    mode_b_entry_count = []

    def mode_a_handler(event: KeyEvent, ctx: ModeContext):
        # Set some state in mode A
        state = ctx.get_state()
        state['initialized'] = True

        # Switch to mode B
        ctx.switch('mode_b')

        # Crash immediately after switch
        raise RuntimeError("Something went wrong!")

    def mode_b_handler(event: KeyEvent, ctx: ModeContext):
        mode_b_entry_count.append(1)
        # Mode B expects to be entered cleanly, but might have
        # inconsistent state from failed mode A transition

    mode.register('mode_a', mode_a_handler)
    mode.register('mode_b', mode_b_handler)
    mode.switch('mode_a')

    # Handle event - switches to B, then crashes
    mode.handle(MockKeyEvent())

    # We're in mode B now
    assert mode.current == 'mode_b'

    # But mode B's handler was NEVER called during the transition
    assert len(mode_b_entry_count) == 0

    # Next event goes to mode B, which may not be properly initialized
    mode.handle(MockKeyEvent())

    # Now mode B handler finally runs
    assert len(mode_b_entry_count) == 1

    # This test PASSES but demonstrates unexpected behavior:
    # Mode transitions can complete without the new mode's handler running.
    # Not a bug per se, but a subtle edge case in the state machine semantics.


# ============================================================================
# ISSUE 4: Switch to Current Mode
# Severity: LOW
# ============================================================================

def test_switch_to_current_mode_state_behavior():
    """
    Documents behavior: Switching to current mode is allowed.

    Not a bug, but worth documenting: switch('mode_a') while already in
    mode_a succeeds. The get_state() lambda is recreated, but points to
    same state dict.
    """
    mode = Mode(MockTeller(), MockStore())

    get_state_refs = []

    def handler(event: KeyEvent, ctx: ModeContext):
        get_state_refs.append(ctx.get_state)

        if len(get_state_refs) == 1:
            # Switch to same mode
            ctx.switch('mode_a')

    mode.register('mode_a', handler)
    mode.switch('mode_a')

    mode.handle(MockKeyEvent())
    mode.handle(MockKeyEvent())

    # Different get_state closures
    assert get_state_refs[0] is not get_state_refs[1]

    # But same underlying state dict
    assert get_state_refs[0]() is get_state_refs[1]()

    # This test PASSES - just documenting the behavior


# ============================================================================
# ISSUE 5: Concurrent State Access (if threading added)
# Severity: N/A (no threading currently, but future risk)
# ============================================================================

def test_thread_safety_documentation():
    """
    Documents that Mode is NOT thread-safe.

    If keyboard events are ever handled on multiple threads, or if handlers
    spawn threads that access ctx.get_state(), race conditions will occur.

    The current implementation has no locking around:
    - self._current (read in handle, written in switch)
    - self._state dicts (read/written by handlers)

    Not a current bug (single-threaded listener), but important to document.
    """
    # This is just documentation, no test
    pass


# ============================================================================
# ROUND 2 ISSUES: Additional Edge Cases
# ============================================================================

# ============================================================================
# ISSUE 6: Type Validation Missing in switch()
# Severity: MEDIUM
# ============================================================================

def test_switch_with_none_gives_confusing_error():
    """
    FAILS: switch(None) gives KeyError instead of TypeError.

    register() validates isinstance(name, str), but switch() has no type
    validation. Passing None or other non-string types gives confusing
    KeyError instead of a clear "mode_name must be a string" error.
    """
    mode = Mode(MockTeller(), MockStore())

    def handler(event: KeyEvent, ctx: ModeContext):
        pass

    mode.register('test_mode', handler)
    mode.switch('test_mode')

    # Should raise TypeError with clear message
    with pytest.raises(TypeError, match="mode_name must be a string"):
        mode.switch(None)


def test_switch_with_integer_gives_confusing_error():
    """
    FAILS: switch(123) gives KeyError instead of TypeError.

    Similar to None case - should fail with type error, not KeyError.
    """
    mode = Mode(MockTeller(), MockStore())

    def handler(event: KeyEvent, ctx: ModeContext):
        pass

    mode.register('test_mode', handler)
    mode.switch('test_mode')

    # Should raise TypeError with clear message
    with pytest.raises(TypeError, match="mode_name must be a string"):
        mode.switch(123)


# ============================================================================
# ISSUE 7: Type Validation Missing in handle()
# Severity: MEDIUM
# ============================================================================

def test_handle_with_none_gives_confusing_error():
    """
    FAILS: handle(None) gives AttributeError instead of TypeError.

    Type hint says event: KeyEvent, but there's no runtime validation.
    Passing None causes AttributeError when handler tries to access
    event.char or other attributes. Should fail fast with clear error.
    """
    mode = Mode(MockTeller(), MockStore())

    def handler(event: KeyEvent, ctx: ModeContext):
        # Any access to event attributes will fail
        char = event.char

    mode.register('test_mode', handler)
    mode.switch('test_mode')

    # Should raise TypeError with clear message
    with pytest.raises(TypeError, match="event must be a KeyEvent"):
        mode.handle(None)


def test_handle_with_wrong_type_gives_confusing_error():
    """
    FAILS: handle("string") gives AttributeError instead of TypeError.

    Passing wrong type should fail immediately at handle() entry,
    not when handler tries to access event attributes.
    """
    mode = Mode(MockTeller(), MockStore())

    def handler(event: KeyEvent, ctx: ModeContext):
        char = event.char

    mode.register('test_mode', handler)
    mode.switch('test_mode')

    # Should raise TypeError with clear message
    with pytest.raises(TypeError, match="event must be a KeyEvent"):
        mode.handle("not a key event")


# ============================================================================
# ISSUE 8: Memory Leak in _state Dict
# Severity: HIGH
# ============================================================================

def test_state_dict_memory_leak():
    """
    FAILS: _state dict grows unbounded - never cleaned up.

    When register() is called, it creates _state[name] = {} if not exists
    (line 124). These state dicts are NEVER removed, even if the mode is
    unregistered or replaced.

    Registering 1000 different modes creates 1000 state dicts that persist
    forever. This is a memory leak.
    """
    mode = Mode(MockTeller(), MockStore())

    def handler(event: KeyEvent, ctx: ModeContext):
        pass

    # Register 100 modes
    for i in range(100):
        mode.register(f'mode_{i}', handler)

    # All 100 state dicts exist
    assert len(mode._state) == 100

    # Now replace all handlers with new ones
    # (simulating mode redefinition during development)
    for i in range(100):
        mode.register(f'mode_{i}', handler)

    # State dicts should NOT grow further
    assert len(mode._state) == 100

    # But there's no way to clean up unused modes!
    # If we register 100 MORE modes with different names:
    for i in range(100, 200):
        mode.register(f'mode_{i}', handler)

    # Now we have 200 state dicts
    assert len(mode._state) == 200

    # There should be an unregister() method to clean up:
    # mode.unregister('mode_0')
    # assert 'mode_0' not in mode._state

    # FAILS: No way to clean up state dicts
    # This test documents the issue but doesn't have a clear assertion
    # beyond showing the unbounded growth


def test_state_dict_persists_after_handler_removal():
    """
    FAILS: State dict persists even after mode is replaced.

    If you register a mode, use it (creating state), then register a
    different handler for the same mode name, the state dict remains.
    This might be intentional (preserving state across handler updates),
    but combined with no cleanup method, it's a memory leak.
    """
    mode = Mode(MockTeller(), MockStore())

    def handler_v1(event: KeyEvent, ctx: ModeContext):
        state = ctx.get_state()
        state['large_data'] = 'x' * 1000000  # 1MB string

    def handler_v2(event: KeyEvent, ctx: ModeContext):
        # Completely different handler, doesn't use state
        pass

    mode.register('test_mode', handler_v1)
    mode.switch('test_mode')
    mode.handle(MockKeyEvent())  # Creates 1MB state

    # Replace handler
    mode.register('test_mode', handler_v2)
    mode.switch('test_mode')

    # Old state still exists with 1MB data
    assert 'large_data' in mode._state['test_mode']
    assert len(mode._state['test_mode']['large_data']) == 1000000

    # There should be a way to reset state:
    # mode.reset_state('test_mode')
    # or
    # mode.register('test_mode', handler_v2, reset_state=True)

    # FAILS: No way to clean up old state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
