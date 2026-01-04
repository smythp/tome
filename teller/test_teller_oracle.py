"""Oracle tests - property-based verification of teller invariants.

Uses Hypothesis to verify properties hold for ALL inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck


# Shared settings for property tests
property_settings = settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)


# Strategies
texts = st.text(min_size=0, max_size=1000)
speeds = st.integers(min_value=1, max_value=1000)
waits = st.booleans()


# ============================================================================
# Text Handler Invariants
# ============================================================================

class TestTextHandlerInvariants:
    """Properties that must hold for TextHandler."""

    @pytest.fixture
    def handler(self):
        from teller.handlers.text import TextHandler
        return TextHandler()

    @given(text=texts)
    @property_settings
    def test_speak_never_crashes(self, handler, text):
        """speak() should never crash regardless of input."""
        # Should complete without exception
        handler.speak(text)

    @given(text=texts, speed=speeds, wait=waits)
    @property_settings
    def test_all_params_accepted(self, handler, text, speed, wait):
        """All parameter combinations should be accepted."""
        handler.speak(text, speed=speed, wait=wait)

    @given(text=st.text(min_size=1, max_size=100))
    @property_settings
    def test_output_contains_text(self, handler, text, capsys):
        """Non-empty text appears in output."""
        handler.speak(text)
        captured = capsys.readouterr()
        assert text in captured.out

    @property_settings
    @given(n=st.integers(min_value=0, max_value=100))
    def test_stop_idempotent(self, handler, n):
        """Calling stop() any number of times is safe."""
        for _ in range(n):
            handler.stop()


# ============================================================================
# Debug Handler Invariants
# ============================================================================

class TestDebugHandlerInvariants:
    """Properties that must hold for DebugHandler."""

    @pytest.fixture
    def handler(self):
        from teller.handlers.debug import DebugHandler
        return DebugHandler()

    @given(text=texts)
    @property_settings
    def test_speak_never_crashes(self, handler, text):
        """speak() should never crash."""
        handler.speak(text)

    @given(text=texts, speed=speeds)
    @property_settings
    def test_speed_in_output(self, handler, text, speed, capsys):
        """Speed value appears in debug output."""
        handler.speak(text, speed=speed)
        captured = capsys.readouterr()
        assert str(speed) in captured.out

    @given(text=texts, wait=waits)
    @property_settings
    def test_wait_in_output(self, handler, text, wait, capsys):
        """Wait value appears in debug output."""
        handler.speak(text, wait=wait)
        captured = capsys.readouterr()
        assert str(wait) in captured.out


# ============================================================================
# Module API Invariants
# ============================================================================

class TestModuleAPIInvariants:
    """Properties for module-level functions."""

    @given(text=texts)
    @property_settings
    def test_speak_never_crashes(self, text):
        """Module speak() never crashes."""
        import teller
        # Use text handler to avoid audio
        original = teller._default_handler
        try:
            teller.set_default_handler("text")
            teller.speak(text)
        finally:
            teller._default_handler = original

    @given(text=texts)
    @property_settings
    def test_announce_never_crashes(self, text):
        """Module announce() never crashes."""
        import teller
        original = teller._default_handler
        try:
            teller.set_default_handler("text")
            teller.announce(text)
        finally:
            teller._default_handler = original

    def test_list_handlers_returns_list(self):
        """list_handlers() always returns a list."""
        from teller import list_handlers
        result = list_handlers()
        assert isinstance(result, list)

    def test_list_handlers_contains_builtins(self):
        """list_handlers() contains the built-in handlers."""
        from teller import list_handlers
        handlers = list_handlers()
        assert "text" in handlers
        assert "debug" in handlers
        # espeak may or may not be available

    @given(name=st.text(min_size=1, max_size=20).filter(
        lambda x: x not in ["text", "debug", "espeak"]
    ))
    @property_settings
    def test_get_unknown_handler_raises(self, name):
        """get_handler() raises KeyError for unknown names."""
        from teller import get_handler
        with pytest.raises(KeyError):
            get_handler(name)


# ============================================================================
# Handler Registration Invariants
# ============================================================================

class TestRegistrationInvariants:
    """Properties about handler registration."""

    def test_all_registered_handlers_have_name(self):
        """Every registered handler has a name property."""
        from teller import list_handlers, get_handler
        for name in list_handlers():
            handler = get_handler(name)
            assert hasattr(handler, "name")
            assert handler.name == name

    def test_all_registered_handlers_have_speak(self):
        """Every registered handler has speak method."""
        from teller import list_handlers, get_handler
        for name in list_handlers():
            handler = get_handler(name)
            assert hasattr(handler, "speak")
            assert callable(handler.speak)

    def test_all_registered_handlers_have_stop(self):
        """Every registered handler has stop method."""
        from teller import list_handlers, get_handler
        for name in list_handlers():
            handler = get_handler(name)
            assert hasattr(handler, "stop")
            assert callable(handler.stop)


# ============================================================================
# Consistency Invariants
# ============================================================================

class TestConsistencyInvariants:
    """Properties about system consistency."""

    @given(handler_name=st.sampled_from(["text", "debug"]))
    @property_settings
    def test_get_handler_consistent(self, handler_name):
        """get_handler() returns same instance for same name."""
        from teller import get_handler
        h1 = get_handler(handler_name)
        h2 = get_handler(handler_name)
        assert h1 is h2

    @given(handler_name=st.sampled_from(["text", "debug"]))
    @property_settings
    def test_set_then_get_default(self, handler_name):
        """After set_default_handler(x), default is x."""
        import teller
        original = teller._default_handler
        try:
            teller.set_default_handler(handler_name)
            assert teller._default_handler.name == handler_name
        finally:
            teller._default_handler = original

    def test_handlers_list_matches_registry(self):
        """list_handlers() matches internal registry."""
        import teller
        listed = set(teller.list_handlers())
        registered = set(teller._handlers.keys())
        assert listed == registered
