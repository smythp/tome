"""Comprehensive pytest test suite for Mode state machine.

Tests the Mode RSP (Request-State-Present) pattern:
- Mode registration and lifecycle
- Event routing to handlers
- Mode switching and transitions
- ModeContext contract
- State isolation per mode
- Error handling and edge cases
"""

import pytest
from dataclasses import dataclass
from typing import Callable, Any
from unittest.mock import Mock, MagicMock


# Mock classes for testing
class MockStore:
    """Mock Store for testing."""
    def __init__(self):
        self.data = {}
        self.calls = []
    
    def get(self, key: str, default=None):
        self.calls.append(('get', key))
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any):
        self.calls.append(('set', key, value))
        self.data[key] = value


class MockTeller:
    """Mock Teller for testing."""
    def __init__(self):
        self.messages = []
        self.calls = []
    
    def tell(self, message: str):
        self.calls.append(('tell', message))
        self.messages.append(message)
    
    def clear(self):
        self.calls.append(('clear',))
        self.messages.clear()


@dataclass
class KeyEvent:
    """Mock KeyEvent for testing."""
    char: str | None = None
    key: str | None = None
    modifiers: list[str] = None

    def __post_init__(self):
        if self.modifiers is None:
            self.modifiers = []


# Helper functions
def make_key_event(char: str, modifiers: list[str] = None) -> KeyEvent:
    """Create a KeyEvent for testing."""
    return KeyEvent(char=char, key=None, modifiers=modifiers or [])


def make_handler(name: str = None) -> tuple[Callable, Mock]:
    """Create a mock handler that records calls."""
    mock = Mock()
    
    def handler(event: KeyEvent, ctx):
        mock(event, ctx)
    
    if name:
        handler.__name__ = name
    
    return handler, mock


# Fixtures
@pytest.fixture
def store():
    """Provide a fresh MockStore."""
    return MockStore()


@pytest.fixture
def teller():
    """Provide a fresh MockTeller."""
    return MockTeller()


@pytest.fixture
def mode(store, teller):
    """Provide a fresh Mode instance."""
    from mode import Mode  # Adjust import as needed
    return Mode(store=store, teller=teller)


# Construction Tests
class TestConstruction:
    """Test Mode construction and initialization."""
    
    def test_construct_with_store_and_teller(self, store, teller):
        """Mode can be constructed with store and teller."""
        from mode import Mode
        m = Mode(store=store, teller=teller)
        assert m is not None
    
    def test_initial_mode_is_none(self, mode):
        """Mode starts with no current mode."""
        assert mode.current is None
    
    def test_store_reference_maintained(self, mode, store):
        """Mode maintains reference to store."""
        # Verify by using a handler that accesses store
        handler, mock = make_handler()
        mode.register('test', handler)
        mode.switch('test')
        mode.handle(make_key_event('a'))
        
        # Handler should receive context with store
        assert mock.call_count == 1
        ctx = mock.call_args[0][1]
        assert ctx.store is store
    
    def test_teller_reference_maintained(self, mode, teller):
        """Mode maintains reference to teller."""
        handler, mock = make_handler()
        mode.register('test', handler)
        mode.switch('test')
        mode.handle(make_key_event('a'))
        
        # Handler should receive context with teller
        assert mock.call_count == 1
        ctx = mock.call_args[0][1]
        assert ctx.teller is teller


# Registration Tests
class TestRegistration:
    """Test mode registration."""
    
    def test_register_valid_handler(self, mode):
        """Can register a valid mode handler."""
        handler, _ = make_handler('test_handler')
        mode.register('insert', handler)
        # Should not raise
    
    def test_register_multiple_modes(self, mode):
        """Can register multiple different modes."""
        handler1, _ = make_handler('handler1')
        handler2, _ = make_handler('handler2')
        handler3, _ = make_handler('handler3')
        
        mode.register('insert', handler1)
        mode.register('normal', handler2)
        mode.register('visual', handler3)
        # Should not raise
    
    def test_register_duplicate_mode_replaces(self, mode):
        """Registering duplicate mode name replaces handler (design decision)."""
        handler1, calls1 = make_handler('handler1')
        handler2, calls2 = make_handler('handler2')

        mode.register('insert', handler1)
        mode.register('insert', handler2)  # Should replace, not raise

        mode.switch('insert')
        mode.handle(make_key_event('a'))

        # Only handler2 should have been called
        assert calls1.call_count == 0
        assert calls2.call_count == 1
    
    def test_register_invalid_name_empty(self, mode):
        """Registering empty mode name raises error."""
        handler, _ = make_handler()
        
        with pytest.raises((ValueError, TypeError)):
            mode.register('', handler)
    
    def test_register_invalid_name_none(self, mode):
        """Registering None as mode name raises error."""
        handler, _ = make_handler()
        
        with pytest.raises((ValueError, TypeError)):
            mode.register(None, handler)
    
    def test_register_invalid_handler_none(self, mode):
        """Registering None as handler raises error."""
        with pytest.raises((ValueError, TypeError)):
            mode.register('insert', None)
    
    def test_register_invalid_handler_not_callable(self, mode):
        """Registering non-callable as handler raises error."""
        with pytest.raises((ValueError, TypeError)):
            mode.register('insert', "not a function")


# Switching Tests
class TestSwitching:
    """Test mode switching."""
    
    def test_switch_to_registered_mode(self, mode):
        """Can switch to a registered mode."""
        handler, _ = make_handler()
        mode.register('insert', handler)
        
        mode.switch('insert')
        assert mode.current == 'insert'
    
    def test_switch_to_unregistered_mode_raises(self, mode):
        """Switching to unregistered mode raises error."""
        with pytest.raises((ValueError, KeyError)):
            mode.switch('nonexistent')
    
    def test_switch_updates_current(self, mode):
        """Switching updates the current mode property."""
        handler1, _ = make_handler()
        handler2, _ = make_handler()
        
        mode.register('normal', handler1)
        mode.register('insert', handler2)
        
        mode.switch('normal')
        assert mode.current == 'normal'
        
        mode.switch('insert')
        assert mode.current == 'insert'
    
    def test_switch_to_same_mode(self, mode):
        """Can switch to the same mode (no-op or re-entry)."""
        handler, _ = make_handler()
        mode.register('insert', handler)
        
        mode.switch('insert')
        assert mode.current == 'insert'
        
        # Switch again
        mode.switch('insert')
        assert mode.current == 'insert'
    
    def test_switch_from_none(self, mode):
        """Can switch from initial None state."""
        handler, _ = make_handler()
        mode.register('insert', handler)
        
        assert mode.current is None
        mode.switch('insert')
        assert mode.current == 'insert'
    
    def test_switch_multiple_transitions(self, mode):
        """Can perform multiple mode transitions."""
        h1, _ = make_handler()
        h2, _ = make_handler()
        h3, _ = make_handler()
        
        mode.register('normal', h1)
        mode.register('insert', h2)
        mode.register('visual', h3)
        
        mode.switch('normal')
        assert mode.current == 'normal'
        
        mode.switch('insert')
        assert mode.current == 'insert'
        
        mode.switch('visual')
        assert mode.current == 'visual'
        
        mode.switch('normal')
        assert mode.current == 'normal'


# Event Routing Tests
class TestEventRouting:
    """Test event routing to mode handlers."""
    
    def test_handle_routes_to_current_mode(self, mode):
        """Events are routed to the current mode handler."""
        handler, mock = make_handler()
        mode.register('insert', handler)
        mode.switch('insert')
        
        event = make_key_event('a')
        mode.handle(event)
        
        assert mock.call_count == 1
        assert mock.call_args[0][0] is event
    
    def test_handle_with_no_current_mode(self, mode):
        """Handling event with no current mode raises or is no-op."""
        event = make_key_event('a')
        
        # Should either raise or be a no-op
        try:
            mode.handle(event)
            # If no error, verify no handlers were called
        except (ValueError, RuntimeError):
            # Expected behavior
            pass
    
    def test_handle_multiple_events(self, mode):
        """Multiple events are routed correctly."""
        handler, mock = make_handler()
        mode.register('insert', handler)
        mode.switch('insert')
        
        event1 = make_key_event('a')
        event2 = make_key_event('b')
        event3 = make_key_event('c')
        
        mode.handle(event1)
        mode.handle(event2)
        mode.handle(event3)
        
        assert mock.call_count == 3
    
    def test_handle_routes_to_correct_mode_after_switch(self, mode):
        """Events route to correct handler after mode switch."""
        handler1, mock1 = make_handler('h1')
        handler2, mock2 = make_handler('h2')
        
        mode.register('normal', handler1)
        mode.register('insert', handler2)
        
        mode.switch('normal')
        mode.handle(make_key_event('a'))
        
        assert mock1.call_count == 1
        assert mock2.call_count == 0
        
        mode.switch('insert')
        mode.handle(make_key_event('b'))
        
        assert mock1.call_count == 1
        assert mock2.call_count == 1
    
    def test_handle_with_modifiers(self, mode):
        """Events with modifiers are passed correctly."""
        handler, mock = make_handler()
        mode.register('normal', handler)
        mode.switch('normal')
        
        event = make_key_event('c', modifiers=['ctrl'])
        mode.handle(event)
        
        assert mock.call_count == 1
        received_event = mock.call_args[0][0]
        assert received_event.char == 'c'
        assert 'ctrl' in received_event.modifiers


# ModeContext Tests
class TestModeContext:
    """Test ModeContext contract and contents."""
    
    def test_context_contains_store(self, mode, store):
        """ModeContext contains the store reference."""
        handler, mock = make_handler()
        mode.register('test', handler)
        mode.switch('test')
        mode.handle(make_key_event('a'))
        
        ctx = mock.call_args[0][1]
        assert ctx.store is store
    
    def test_context_contains_teller(self, mode, teller):
        """ModeContext contains the teller reference."""
        handler, mock = make_handler()
        mode.register('test', handler)
        mode.switch('test')
        mode.handle(make_key_event('a'))
        
        ctx = mock.call_args[0][1]
        assert ctx.teller is teller
    
    def test_context_contains_switch_function(self, mode):
        """ModeContext contains a switch function."""
        handler, mock = make_handler()
        mode.register('test', handler)
        mode.switch('test')
        mode.handle(make_key_event('a'))
        
        ctx = mock.call_args[0][1]
        assert callable(ctx.switch)
    
    def test_context_switch_function_works(self, mode):
        """Context's switch function actually switches modes."""
        handler1_called = []
        handler2_called = []
        
        def handler1(event, ctx):
            handler1_called.append(True)
            # Switch to handler2
            ctx.switch('mode2')
        
        def handler2(event, ctx):
            handler2_called.append(True)
        
        mode.register('mode1', handler1)
        mode.register('mode2', handler2)
        
        mode.switch('mode1')
        mode.handle(make_key_event('a'))
        
        assert len(handler1_called) == 1
        assert mode.current == 'mode2'
    
    def test_context_contains_current_mode(self, mode):
        """ModeContext contains current mode name."""
        handler, mock = make_handler()
        mode.register('insert', handler)
        mode.switch('insert')
        mode.handle(make_key_event('a'))
        
        ctx = mock.call_args[0][1]
        assert ctx.current_mode == 'insert'
    
    def test_context_contains_get_state(self, mode):
        """ModeContext contains get_state function."""
        handler, mock = make_handler()
        mode.register('test', handler)
        mode.switch('test')
        mode.handle(make_key_event('a'))
        
        ctx = mock.call_args[0][1]
        assert callable(ctx.get_state)
    
    def test_context_get_state_returns_dict(self, mode):
        """Context's get_state returns a dictionary."""
        state_result = None
        
        def handler(event, ctx):
            nonlocal state_result
            state_result = ctx.get_state()
        
        mode.register('test', handler)
        mode.switch('test')
        mode.handle(make_key_event('a'))
        
        assert isinstance(state_result, dict)


# State Isolation Tests
class TestStateIsolation:
    """Test that state is isolated per mode."""
    
    def test_modes_have_separate_state(self, mode):
        """Different modes maintain separate state."""
        state1 = None
        state2 = None
        
        def handler1(event, ctx):
            nonlocal state1
            state = ctx.get_state()
            state['count'] = state.get('count', 0) + 1
            state1 = state['count']
        
        def handler2(event, ctx):
            nonlocal state2
            state = ctx.get_state()
            state['count'] = state.get('count', 0) + 10
            state2 = state['count']
        
        mode.register('mode1', handler1)
        mode.register('mode2', handler2)
        
        # Increment mode1 state
        mode.switch('mode1')
        mode.handle(make_key_event('a'))
        mode.handle(make_key_event('b'))
        
        # Mode2 should start fresh
        mode.switch('mode2')
        mode.handle(make_key_event('c'))
        
        # States should be independent
        assert state1 == 2  # mode1 incremented twice
        assert state2 == 10  # mode2 started fresh
    
    def test_state_persists_across_switches(self, mode):
        """Mode state persists when switching away and back."""
        counts = []
        
        def handler(event, ctx):
            state = ctx.get_state()
            state['count'] = state.get('count', 0) + 1
            counts.append(state['count'])
        
        def other_handler(event, ctx):
            pass
        
        mode.register('test', handler)
        mode.register('other', other_handler)
        
        # Increment counter in test mode
        mode.switch('test')
        mode.handle(make_key_event('a'))
        mode.handle(make_key_event('b'))
        
        # Switch away
        mode.switch('other')
        mode.handle(make_key_event('c'))
        
        # Switch back - state should persist
        mode.switch('test')
        mode.handle(make_key_event('d'))
        
        assert counts == [1, 2, 3]  # Counter continued from 2 to 3


# Exception Handling Tests
class TestExceptionHandling:
    """Test exception handling in handlers."""
    
    def test_handler_exception_caught_not_propagated(self, mode):
        """Exceptions in handlers are caught and logged (design decision).

        For Tome's blind user, robustness is critical - a crashing handler
        should not bring down the whole application.
        """
        def bad_handler(event, ctx):
            raise ValueError("Handler error")

        mode.register('test', bad_handler)
        mode.switch('test')

        # Should NOT raise - exceptions are caught and logged
        mode.handle(make_key_event('a'))  # No exception
    
    def test_mode_remains_functional_after_handler_error(self, mode):
        """Mode remains functional after a handler error."""
        error_count = [0]
        success_count = [0]
        
        def sometimes_fails(event, ctx):
            if event.char == 'x':
                error_count[0] += 1
                raise ValueError("Error on x")
            success_count[0] += 1
        
        mode.register('test', sometimes_fails)
        mode.switch('test')
        
        mode.handle(make_key_event('a'))
        
        try:
            mode.handle(make_key_event('x'))
        except ValueError:
            pass
        
        mode.handle(make_key_event('b'))
        
        assert success_count[0] == 2
        assert error_count[0] == 1


# Edge Cases
class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_switch_during_event_handling(self, mode):
        """Can switch modes during event handling."""
        def handler1(event, ctx):
            ctx.switch('mode2')
        
        def handler2(event, ctx):
            pass
        
        mode.register('mode1', handler1)
        mode.register('mode2', handler2)
        
        mode.switch('mode1')
        mode.handle(make_key_event('a'))
        
        assert mode.current == 'mode2'
    
    def test_mode_names_with_special_characters(self, mode):
        """Mode names with special characters work."""
        handler, _ = make_handler()
        
        mode.register('mode-with-dash', handler)
        mode.register('mode_with_underscore', handler)
        mode.register('mode.with.dot', handler)
        
        mode.switch('mode-with-dash')
        assert mode.current == 'mode-with-dash'
    
    def test_empty_event_key(self, mode):
        """Handler receives events with empty key."""
        handler, mock = make_handler()
        mode.register('test', handler)
        mode.switch('test')
        
        event = make_key_event('')
        mode.handle(event)
        
        assert mock.call_count == 1
        assert mock.call_args[0][0].char == ''
    
    def test_many_registered_modes(self, mode):
        """Can register many modes."""
        for i in range(100):
            handler, _ = make_handler()
            mode.register(f'mode{i}', handler)
        
        mode.switch('mode50')
        assert mode.current == 'mode50'
    
    def test_handler_can_access_store(self, mode, store):
        """Handler can read/write store through context."""
        def handler(event, ctx):
            ctx.store.set('test_key', 'test_value')
            value = ctx.store.get('test_key')
            ctx.store.set('retrieved', value)
        
        mode.register('test', handler)
        mode.switch('test')
        mode.handle(make_key_event('a'))
        
        assert store.data['test_key'] == 'test_value'
        assert store.data['retrieved'] == 'test_value'
    
    def test_handler_can_use_teller(self, mode, teller):
        """Handler can send messages through teller."""
        def handler(event, ctx):
            ctx.teller.tell('Hello from handler')
        
        mode.register('test', handler)
        mode.switch('test')
        mode.handle(make_key_event('a'))
        
        assert 'Hello from handler' in teller.messages
    
    def test_rapid_mode_switching(self, mode):
        """Rapid mode switches work correctly."""
        h1, _ = make_handler()
        h2, _ = make_handler()
        
        mode.register('mode1', h1)
        mode.register('mode2', h2)
        
        for i in range(100):
            mode.switch('mode1' if i % 2 == 0 else 'mode2')
        
        assert mode.current in ['mode1', 'mode2']
    
    def test_current_property_is_readonly(self, mode):
        """The current property cannot be set directly."""
        handler, _ = make_handler()
        mode.register('test', handler)
        mode.switch('test')
        
        # Attempt to set should fail (property has no setter)
        with pytest.raises(AttributeError):
            mode.current = 'some_other_mode'
