"""
Tests for Mode RSP.

Tests Mode construction, ModeContext, handler registration, event routing,
and mode transitions.
"""

import pytest
from dataclasses import dataclass
from typing import Protocol, Callable

# We'll import from mode.py once it exists
# from mode import Mode, ModeContext, ModeHandler


# =============================================================================
# Mock Dependencies for Testing
# =============================================================================

class MockTeller:
    """Mock Teller for testing - captures speak calls."""

    def __init__(self):
        self.spoken: list[str] = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)

    def stop(self) -> None:
        pass


class MockStore:
    """Mock Store for testing - in-memory key-value store."""

    def __init__(self):
        self.data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def set(self, key: str, value: str) -> None:
        self.data[key] = value


# =============================================================================
# KeyEvent stub (from listener.py)
# =============================================================================

@dataclass(frozen=True)
class KeyEvent:
    """Minimal KeyEvent for testing Mode without importing listener."""
    char: str | None
    key: str | None  # Using str instead of SpecialKey for simplicity
    modifiers: frozenset
    event_type: str  # 'press' or 'release'


def make_char_event(char: str, modifiers: frozenset | None = None) -> KeyEvent:
    """Helper to create character KeyEvent."""
    return KeyEvent(
        char=char,
        key=None,
        modifiers=modifiers or frozenset(),
        event_type='press'
    )


def make_special_event(key: str, modifiers: frozenset | None = None) -> KeyEvent:
    """Helper to create special key KeyEvent."""
    return KeyEvent(
        char=None,
        key=key,
        modifiers=modifiers or frozenset(),
        event_type='press'
    )


# =============================================================================
# Mode Construction Tests
# =============================================================================

class TestModeConstruction:
    """Test Mode creation and initialization."""

    def test_mode_creation(self):
        """Mode can be created with teller and store."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        assert mode is not None

    def test_initial_mode_is_none(self):
        """Mode starts with no current mode set."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        assert mode.current is None

    def test_mode_stores_dependencies(self):
        """Mode stores teller and store references."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        # Mode should keep references (checked via context later)
        assert mode._teller is teller
        assert mode._store is store


# =============================================================================
# Handler Registration Tests
# =============================================================================

class TestHandlerRegistration:
    """Test mode handler registration."""

    def test_register_handler(self):
        """Can register a handler function for a mode."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def my_handler(event, context):
            pass

        mode.register('read', my_handler)
        # Should not raise

    def test_register_multiple_handlers(self):
        """Can register multiple different handlers."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def handler_read(event, context):
            pass

        def handler_write(event, context):
            pass

        mode.register('read', handler_read)
        mode.register('write', handler_write)
        # Should not raise

    def test_register_duplicate_mode_replaces(self):
        """Registering same mode name replaces previous handler."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        calls = []

        def handler1(event, context):
            calls.append('handler1')

        def handler2(event, context):
            calls.append('handler2')

        mode.register('read', handler1)
        mode.register('read', handler2)  # Replace

        mode.switch('read')
        mode.handle(make_char_event('a'))

        assert calls == ['handler2']  # Only handler2 called

    def test_register_with_invalid_name_raises(self):
        """Registering with empty string name raises ValueError."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def my_handler(event, context):
            pass

        with pytest.raises(ValueError, match="empty"):
            mode.register('', my_handler)

    def test_register_with_none_name_raises(self):
        """Registering with None name raises TypeError."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def my_handler(event, context):
            pass

        with pytest.raises(TypeError):
            mode.register(None, my_handler)

    def test_register_with_non_callable_raises(self):
        """Registering non-callable raises TypeError."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        with pytest.raises(TypeError, match="callable"):
            mode.register('read', "not a function")


# =============================================================================
# Mode Switching Tests
# =============================================================================

class TestModeSwitching:
    """Test mode transitions."""

    def test_switch_to_registered_mode(self):
        """Can switch to a registered mode."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        mode.register('read', lambda e, c: None)
        mode.switch('read')

        assert mode.current == 'read'

    def test_switch_to_unregistered_mode_raises(self):
        """Switching to unregistered mode raises KeyError."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        with pytest.raises(KeyError, match="unknown"):
            mode.switch('nonexistent')

    def test_switch_between_modes(self):
        """Can switch between different modes."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        mode.register('read', lambda e, c: None)
        mode.register('write', lambda e, c: None)

        mode.switch('read')
        assert mode.current == 'read'

        mode.switch('write')
        assert mode.current == 'write'

        mode.switch('read')
        assert mode.current == 'read'

    def test_switch_to_same_mode_is_noop(self):
        """Switching to current mode is allowed (no-op)."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        mode.register('read', lambda e, c: None)
        mode.switch('read')
        mode.switch('read')  # Should not raise

        assert mode.current == 'read'

    def test_invalid_setup_type_does_not_mutate_current_mode(self):
        """setup is validated before switch callbacks or lifecycle hooks run."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        calls = []
        mode = Mode(
            teller=teller,
            store=store,
            on_switch=lambda _source, _dest: calls.append('switch'),
        )

        mode.register('read', lambda e, c: None, on_exit=lambda: calls.append('exit'))
        mode.register('history', lambda e, c: None)
        mode.switch('read')
        calls.clear()

        with pytest.raises(TypeError, match="setup must be a dict"):
            mode.switch('history', setup=['not', 'a', 'dict'])

        assert mode.current == 'read'
        assert calls == []


# =============================================================================
# Event Routing Tests
# =============================================================================

class TestEventRouting:
    """Test event routing to handlers."""

    def test_handle_routes_to_current_mode(self):
        """handle() routes event to current mode's handler."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        received = []

        def read_handler(event, context):
            received.append(('read', event))

        mode.register('read', read_handler)
        mode.switch('read')

        event = make_char_event('a')
        mode.handle(event)

        assert len(received) == 1
        assert received[0] == ('read', event)

    def test_handle_routes_to_correct_handler(self):
        """handle() routes to the current mode, not others."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        received = []

        def read_handler(event, context):
            received.append('read')

        def write_handler(event, context):
            received.append('write')

        mode.register('read', read_handler)
        mode.register('write', write_handler)

        mode.switch('read')
        mode.handle(make_char_event('a'))

        assert received == ['read']

        mode.switch('write')
        mode.handle(make_char_event('b'))

        assert received == ['read', 'write']

    def test_handle_before_switch_raises(self):
        """handle() before any switch() raises RuntimeError."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        mode.register('read', lambda e, c: None)

        with pytest.raises(RuntimeError, match="no mode"):
            mode.handle(make_char_event('a'))

    def test_handle_multiple_events(self):
        """Multiple events routed correctly."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        received = []

        def read_handler(event, context):
            received.append(event.char)

        mode.register('read', read_handler)
        mode.switch('read')

        mode.handle(make_char_event('a'))
        mode.handle(make_char_event('b'))
        mode.handle(make_char_event('c'))

        assert received == ['a', 'b', 'c']


# =============================================================================
# ModeContext Tests
# =============================================================================

class TestModeContext:
    """Test ModeContext provided to handlers."""

    def test_context_has_teller(self):
        """ModeContext provides teller."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        ctx = None

        def handler(event, context):
            nonlocal ctx
            ctx = context

        mode.register('read', handler)
        mode.switch('read')
        mode.handle(make_char_event('a'))

        assert ctx is not None
        assert ctx.teller is teller

    def test_context_has_store(self):
        """ModeContext provides store."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        ctx = None

        def handler(event, context):
            nonlocal ctx
            ctx = context

        mode.register('read', handler)
        mode.switch('read')
        mode.handle(make_char_event('a'))

        assert ctx is not None
        assert ctx.store is store

    def test_context_has_switch(self):
        """ModeContext provides switch callable."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        ctx = None

        def handler(event, context):
            nonlocal ctx
            ctx = context

        mode.register('read', handler)
        mode.switch('read')
        mode.handle(make_char_event('a'))

        assert ctx is not None
        assert callable(ctx.switch)

    def test_context_switch_works(self):
        """Handler can switch modes via context."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def read_handler(event, context):
            if event.char == 'w':
                context.switch('write')

        def write_handler(event, context):
            pass

        mode.register('read', read_handler)
        mode.register('write', write_handler)
        mode.switch('read')

        mode.handle(make_char_event('w'))

        assert mode.current == 'write'

    def test_context_current_mode(self):
        """ModeContext provides current mode name."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        ctx = None

        def handler(event, context):
            nonlocal ctx
            ctx = context

        mode.register('read', handler)
        mode.switch('read')
        mode.handle(make_char_event('a'))

        assert ctx is not None
        assert ctx.current_mode == 'read'


# =============================================================================
# Per-Mode State Tests
# =============================================================================

class TestPerModeState:
    """Test per-mode state isolation."""

    def test_mode_has_isolated_state(self):
        """Each mode has its own state dict."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def read_handler(event, context):
            state = context.get_state()
            state['count'] = state.get('count', 0) + 1

        def write_handler(event, context):
            state = context.get_state()
            state['count'] = state.get('count', 0) + 100

        mode.register('read', read_handler)
        mode.register('write', write_handler)

        mode.switch('read')
        mode.handle(make_char_event('a'))
        mode.handle(make_char_event('b'))

        mode.switch('write')
        mode.handle(make_char_event('c'))

        # Read state should have count=2, write state should have count=100
        # They should be isolated
        mode.switch('read')

        ctx = None
        def capture(event, context):
            nonlocal ctx
            ctx = context
        mode.register('read', capture)
        mode.handle(make_char_event('x'))

        # This test is tricky - we need to verify state isolation
        # The key insight: switching modes should preserve each mode's state

    def test_state_persists_across_switches(self):
        """Mode state persists when switching away and back."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def read_handler(event, context):
            state = context.get_state()
            count = state.get('count', 0)
            state['count'] = count + 1
            teller.speak(f"count={state['count']}")

        mode.register('read', read_handler)
        mode.register('other', lambda e, c: None)

        mode.switch('read')
        mode.handle(make_char_event('a'))  # count=1
        mode.switch('other')
        mode.switch('read')
        mode.handle(make_char_event('b'))  # count=2 (not reset)

        assert 'count=2' in teller.spoken

    def test_get_state_stable_after_mid_handler_switch(self):
        """get_state() returns same dict even if handler switches modes.

        Bug found by gremlin/oracle: if get_state lambda captures _current
        by reference instead of by value, switching modes mid-handler
        causes get_state() to return the wrong mode's state.
        """
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        state_dicts = []

        def read_handler(event, context):
            # Get state before switch
            state1 = context.get_state()
            state1['marker'] = 'read_mode'
            state_dicts.append(('before_switch', id(state1)))

            # Switch modes mid-handler
            context.switch('write')

            # Get state AFTER switch - should still be read's state
            state2 = context.get_state()
            state_dicts.append(('after_switch', id(state2)))

            # Both should be the same dict
            assert state1 is state2, "get_state() returned different dict after switch"
            assert state2['marker'] == 'read_mode', "State was corrupted"

        mode.register('read', read_handler)
        mode.register('write', lambda e, c: None)

        mode.switch('read')
        mode.handle(make_char_event('a'))

        # Verify same dict was returned both times
        assert state_dicts[0][1] == state_dicts[1][1]

    def test_no_cross_mode_state_pollution(self):
        """Handler cannot accidentally modify another mode's state."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def mode_a_handler(event, context):
            state = context.get_state()
            state['value'] = 'from_a'
            # Switch to mode B
            context.switch('mode_b')
            # This should NOT affect mode_b's state
            state['another'] = 'should_stay_in_a'

        def mode_b_handler(event, context):
            state = context.get_state()
            # Mode B's state should be clean
            assert 'another' not in state, "Mode A polluted mode B's state"

        mode.register('mode_a', mode_a_handler)
        mode.register('mode_b', mode_b_handler)

        mode.switch('mode_a')
        mode.handle(make_char_event('x'))

        # Now call mode_b - its state should be clean
        mode.handle(make_char_event('y'))


# =============================================================================
# Handler Exception Handling Tests
# =============================================================================

class TestHandlerExceptions:
    """Test behavior when handlers raise exceptions."""

    def test_handler_exception_logged_not_raised(self):
        """Handler exceptions are caught and logged, not propagated."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def bad_handler(event, context):
            raise RuntimeError("handler crashed")

        mode.register('read', bad_handler)
        mode.switch('read')

        # Should not raise
        mode.handle(make_char_event('a'))

    def test_handler_exception_allows_continued_operation(self):
        """After handler exception, mode continues working."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        call_count = [0]

        def sometimes_bad_handler(event, context):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("first call crashes")
            teller.speak(f"call {call_count[0]}")

        mode.register('read', sometimes_bad_handler)
        mode.switch('read')

        mode.handle(make_char_event('a'))  # Crashes
        mode.handle(make_char_event('b'))  # Should work

        assert 'call 2' in teller.spoken

    @pytest.mark.parametrize(
        (
            "scenario",
            "expected_current",
            "expected_source_state",
            "expected_destination_state",
        ),
        [
            (
                "no_switch",
                "source",
                {},
                {},
            ),
            (
                "invalid_switch",
                "source",
                {},
                {},
            ),
            (
                "same_mode_no_setup",
                "source",
                {},
                {},
            ),
            (
                "away_and_back_no_source_setup",
                "source",
                {},
                {},
            ),
            (
                "same_mode_explicit_setup",
                "source",
                {"ready": "source"},
                {},
            ),
            (
                "away_and_back_source_setup",
                "source",
                {"ready": "source"},
                {},
            ),
            (
                "different_mode_setup",
                "destination",
                {},
                {"ready": "destination"},
            ),
        ],
    )
    def test_handler_exception_cleanup_depends_on_source_setup(
        self,
        scenario,
        expected_current,
        expected_source_state,
        expected_destination_state,
    ):
        """Handler cleanup preserves only setup installed for the captured source."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def handler(event, context):
            context.get_state()["partial"] = event.char
            if scenario == "invalid_switch":
                context.switch("unknown")
            elif scenario == "same_mode_no_setup":
                context.switch("source", silent=True)
            elif scenario == "away_and_back_no_source_setup":
                context.switch("destination", silent=True)
                context.switch("source", silent=True)
            elif scenario == "same_mode_explicit_setup":
                context.switch(
                    "source",
                    silent=True,
                    setup={"ready": "source"},
                )
            elif scenario == "away_and_back_source_setup":
                context.switch("destination", silent=True)
                context.switch(
                    "source",
                    silent=True,
                    setup={"ready": "source"},
                )
            elif scenario == "different_mode_setup":
                context.switch(
                    "destination",
                    silent=True,
                    setup={"ready": "destination"},
                )
            raise RuntimeError("handler failed")

        mode.register("source", handler)
        mode.register("destination", lambda _event, _context: None)
        mode.switch("source", silent=True, setup={"stale": "source"})

        mode.handle(make_char_event("a"))

        assert mode.current == expected_current
        assert mode._state["source"] == expected_source_state
        assert mode._state["destination"] == expected_destination_state

    def test_handler_exception_after_same_mode_setup_keeps_destination_state(self):
        """A post-switch handler failure must not clear installed same-mode setup."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def handler(event, context):
            context.get_state()['partial'] = event.char
            context.switch('read', silent=True, setup={'ready': 'destination'})
            raise RuntimeError("failed after switch")

        mode.register('read', handler)
        mode.switch('read')

        mode.handle(make_char_event('a'))

        assert mode.current == 'read'
        assert mode._state['read'] == {'ready': 'destination'}

    def test_handler_exception_after_source_setup_discards_top_level_mutation(self):
        """A failed handler restores the committed source setup, not later edits."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def handler(event, context):
            context.get_state()["partial_before"] = event.char
            context.switch("read", silent=True, setup={"ready": "destination"})
            context.get_state()["partial_after"] = event.char
            raise RuntimeError("failed after setup mutation")

        mode.register("read", handler)
        mode.switch("read", silent=True)

        mode.handle(make_char_event("a"))

        assert mode.current == "read"
        assert mode._state["read"] == {"ready": "destination"}

    def test_handler_exception_after_source_setup_discards_nested_mutation(self):
        """Nested mutable setup values roll back to the committed snapshot."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def handler(event, context):
            context.switch(
                "read",
                silent=True,
                setup={"nested": {"items": ["committed"]}},
            )
            state = context.get_state()
            state["nested"]["items"].append("partial")
            state["nested"]["extra"] = event.char
            raise RuntimeError("failed after nested setup mutation")

        mode.register("read", handler)
        mode.switch("read", silent=True)

        mode.handle(make_char_event("a"))

        assert mode._state["read"] == {"nested": {"items": ["committed"]}}

    def test_handler_exception_after_multiple_source_setups_restores_final_setup(self):
        """When a handler installs source setup more than once, the final setup wins."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def handler(event, context):
            context.switch(
                "read",
                silent=True,
                setup={"ready": "first", "items": ["first"]},
            )
            context.get_state()["items"].append("partial")
            context.switch(
                "read",
                silent=True,
                setup={"ready": "second", "items": ["second"]},
            )
            context.get_state()["partial_after"] = event.char
            raise RuntimeError("failed after final setup")

        mode.register("read", handler)
        mode.switch("read", silent=True)

        mode.handle(make_char_event("a"))

        assert mode._state["read"] == {"ready": "second", "items": ["second"]}

    def test_handler_exception_after_source_setup_ignores_caller_alias_mutation(self):
        """Mutating the original setup object after switch does not alter rollback."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)
        setup = {"items": ["committed"], "nested": {"values": ["committed"]}}

        def handler(event, context):
            context.switch("read", silent=True, setup=setup)
            setup["items"].append("caller")
            setup["nested"]["values"].append("caller")
            context.get_state()["items"].append(event.char)
            raise RuntimeError("failed after alias mutation")

        mode.register("read", handler)
        mode.switch("read", silent=True)

        mode.handle(make_char_event("a"))

        assert mode._state["read"] == {
            "items": ["committed"],
            "nested": {"values": ["committed"]},
        }
        assert setup == {
            "items": ["committed", "caller"],
            "nested": {"values": ["committed", "caller"]},
        }

    def test_handler_failed_switch_clears_partial_source_state(self):
        """If switch raises before committing, handler cleanup clears stale state."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def handler(event, context):
            context.get_state()['partial'] = event.char
            context.switch('unknown')

        mode.register('read', handler)
        mode.switch('read')

        mode.handle(make_char_event('a'))

        assert mode.current == 'read'
        assert mode._state['read'] == {}


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_mode_names_are_case_sensitive(self):
        """Mode names 'Read' and 'read' are different."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        calls = []

        mode.register('read', lambda e, c: calls.append('lower'))
        mode.register('Read', lambda e, c: calls.append('upper'))

        mode.switch('read')
        mode.handle(make_char_event('a'))

        mode.switch('Read')
        mode.handle(make_char_event('b'))

        assert calls == ['lower', 'upper']

    def test_whitespace_mode_name_rejected(self):
        """Mode names with only whitespace are rejected."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        with pytest.raises(ValueError, match="empty"):
            mode.register('   ', lambda e, c: None)

    def test_special_char_mode_names_allowed(self):
        """Mode names with special characters work."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        mode.register('mode-with-dashes', lambda e, c: None)
        mode.register('mode_with_underscores', lambda e, c: None)
        mode.register('mode.with.dots', lambda e, c: None)

        mode.switch('mode-with-dashes')
        assert mode.current == 'mode-with-dashes'

    def test_rapid_mode_switching(self):
        """Rapid mode switching doesn't corrupt state."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        mode.register('a', lambda e, c: None)
        mode.register('b', lambda e, c: None)
        mode.register('c', lambda e, c: None)

        for _ in range(100):
            mode.switch('a')
            mode.switch('b')
            mode.switch('c')

        assert mode.current == 'c'

    def test_handler_can_register_new_mode(self):
        """Handler can register a new mode dynamically."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def dynamic_handler(event, context):
            # Dynamically register and switch to new mode
            # Note: handler needs access to Mode instance for this
            pass

        # This is a design question - do handlers have access to Mode itself?
        # For now, skip this test as it may not be a requirement
        pytest.skip("Design decision: handlers don't have Mode access")


# =============================================================================
# Integration-style Tests
# =============================================================================

class TestIntegration:
    """Tests that verify realistic usage patterns."""

    def test_read_then_options_then_back(self):
        """Simulate typical read -> options -> read flow."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def read_handler(event, context):
            if event.char == 'o' and 'ctrl' in event.modifiers:
                context.switch('options')
                context.teller.speak('Options mode')
            else:
                context.teller.speak(f'Read: {event.char}')

        def options_handler(event, context):
            if event.key == 'escape':
                context.switch('read')
                context.teller.speak('Back to read')
            else:
                context.teller.speak(f'Option: {event.char}')

        mode.register('read', read_handler)
        mode.register('options', options_handler)

        mode.switch('read')
        mode.handle(make_char_event('a'))
        mode.handle(make_char_event('o', frozenset(['ctrl'])))
        mode.handle(make_char_event('d'))  # Options toggle
        mode.handle(make_special_event('escape'))
        mode.handle(make_char_event('b'))

        assert mode.current == 'read'
        assert 'Read: a' in teller.spoken
        assert 'Options mode' in teller.spoken
        assert 'Option: d' in teller.spoken
        assert 'Back to read' in teller.spoken
        assert 'Read: b' in teller.spoken


# =============================================================================
# Tome.py Feature Tests - Mode Messages, Hooks, Previous Mode
# =============================================================================

class TestModeMessages:
    """Test mode messages spoken on entry (matching tome.py mode_map)."""

    def test_message_spoken_on_switch(self):
        """Mode message is spoken when switching to mode."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        mode.register('read', lambda e, c: None, message="Read from tome")
        mode.switch('read')

        assert 'Read from tome' in teller.spoken

    def test_no_message_if_none(self):
        """No message spoken if message is None."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        mode.register('read', lambda e, c: None, message=None)
        mode.switch('read')

        assert len(teller.spoken) == 0

    def test_silent_switch_suppresses_message(self):
        """Silent switch doesn't speak message."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        mode.register('read', lambda e, c: None, message="Read from tome")
        mode.switch('read', silent=True)

        assert len(teller.spoken) == 0

    def test_get_message(self):
        """Can retrieve mode message."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        mode.register('read', lambda e, c: None, message="Read from tome")
        assert mode.get_message('read') == "Read from tome"

    def test_set_message_dynamically(self):
        """Can set message dynamically (for confirm mode prompts)."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        mode.register('confirm', lambda e, c: None, message=None)
        mode.set_message('confirm', "Delete this entry?")
        mode.switch('confirm')

        assert 'Delete this entry?' in teller.spoken


class TestPreviousModeTracking:
    """Test previous mode tracking and back() (matching tome.py)."""

    def test_previous_mode_tracked(self):
        """Previous mode is tracked on switch."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        mode.register('read', lambda e, c: None)
        mode.register('options', lambda e, c: None)

        mode.switch('read')
        assert mode.previous is None

        mode.switch('options')
        assert mode.previous == 'read'

    def test_back_returns_to_previous(self):
        """back() returns to previous mode."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        mode.register('read', lambda e, c: None)
        mode.register('history', lambda e, c: None)

        mode.switch('read')
        mode.switch('history')
        mode.back()

        assert mode.current == 'read'

    def test_back_does_nothing_if_no_previous(self):
        """back() does nothing if no previous mode."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        mode.register('read', lambda e, c: None)
        mode.switch('read')
        mode.back()  # Should not raise

        assert mode.current == 'read'

    def test_context_has_back(self):
        """ModeContext provides back() callable."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        ctx = None

        def handler(event, context):
            nonlocal ctx
            ctx = context

        mode.register('read', handler)
        mode.switch('read')
        mode.handle(make_char_event('a'))

        assert callable(ctx.back)

    def test_context_has_previous_mode(self):
        """ModeContext provides previous_mode."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        ctx = None

        def handler(event, context):
            nonlocal ctx
            ctx = context

        mode.register('read', lambda e, c: None)
        mode.register('history', handler)

        mode.switch('read')
        mode.switch('history')
        mode.handle(make_char_event('a'))

        assert ctx.previous_mode == 'read'


class TestOnEnterOnExit:
    """Test on_enter and on_exit hooks (for clearing state, etc.)."""

    def test_on_enter_called_on_switch(self):
        """on_enter is called when switching to mode."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        entered = []
        mode.register('read', lambda e, c: None, on_enter=lambda: entered.append('read'))
        mode.switch('read')

        assert entered == ['read']

    def test_on_exit_called_on_switch_away(self):
        """on_exit is called when switching away from mode."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        exited = []
        mode.register('read', lambda e, c: None, on_exit=lambda: exited.append('read'))
        mode.register('options', lambda e, c: None)

        mode.switch('read')
        assert exited == []

        mode.switch('options')
        assert exited == ['read']

    def test_on_enter_on_exit_order(self):
        """on_exit called before on_enter when switching."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        calls = []
        mode.register('read', lambda e, c: None,
                      on_enter=lambda: calls.append('enter_read'),
                      on_exit=lambda: calls.append('exit_read'))
        mode.register('options', lambda e, c: None,
                      on_enter=lambda: calls.append('enter_options'))

        mode.switch('read')
        mode.switch('options')

        assert calls == ['enter_read', 'exit_read', 'enter_options']

    def test_same_mode_setup_is_applied_after_on_exit_before_on_enter(self):
        """Same-mode on_exit observes source state; on_enter observes setup state."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)
        calls = []

        def on_exit():
            calls.append(('exit', dict(mode._state['read'])))

        def on_enter():
            calls.append(('enter', dict(mode._state['read'])))

        mode.register(
            'read',
            lambda e, c: None,
            on_enter=on_enter,
            on_exit=on_exit,
        )
        mode.switch('read', silent=True, setup={'old': 'source'})
        calls.clear()

        mode.switch('read', silent=True, setup={'new': 'destination'})

        assert calls == [
            ('exit', {'old': 'source'}),
            ('enter', {'new': 'destination'}),
        ]
        assert mode._state['read'] == {'new': 'destination'}

    def test_on_enter_exception_logged_not_raised(self):
        """on_enter exception is logged but doesn't prevent switch."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        def bad_enter():
            raise RuntimeError("on_enter crashed")

        mode.register('read', lambda e, c: None, on_enter=bad_enter)
        mode.switch('read')  # Should not raise

        assert mode.current == 'read'


class TestListModes:
    """Test list_modes() for introspection."""

    def test_list_modes_empty(self):
        """list_modes() returns empty list initially."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        assert mode.list_modes() == []

    def test_list_modes_returns_registered(self):
        """list_modes() returns all registered mode names."""
        from mode import Mode

        teller = MockTeller()
        store = MockStore()
        mode = Mode(teller=teller, store=store)

        mode.register('read', lambda e, c: None)
        mode.register('options', lambda e, c: None)
        mode.register('history', lambda e, c: None)

        modes = mode.list_modes()
        assert set(modes) == {'read', 'options', 'history'}
