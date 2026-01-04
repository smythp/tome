"""Oracle tests - property-based verification using Hypothesis.

Verify mathematical properties hold for ALL inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import patch, MagicMock


# Shared settings
oracle_settings = settings(max_examples=100, deadline=None)


# ============================================================================
# Handler Protocol Properties
# ============================================================================

class TestHandlerProtocolProperties:
    """Properties that must hold for all handlers."""

    @given(handler_name=st.sampled_from(["text", "debug", "espeak"]))
    @oracle_settings
    def test_name_is_nonempty_string(self, handler_name):
        """Handler name is always a non-empty string."""
        from teller import get_handler
        handler = get_handler(handler_name)
        assert isinstance(handler.name, str)
        assert len(handler.name) > 0

    @given(handler_name=st.sampled_from(["text", "debug", "espeak"]))
    @oracle_settings
    def test_name_is_lowercase(self, handler_name):
        """Handler name is always lowercase."""
        from teller import get_handler
        handler = get_handler(handler_name)
        assert handler.name == handler.name.lower()

    @given(handler_name=st.sampled_from(["text", "debug", "espeak"]))
    @oracle_settings
    def test_stop_never_raises(self, handler_name):
        """stop() never raises, even when nothing playing."""
        from teller import get_handler
        handler = get_handler(handler_name)
        # Should never raise
        handler.stop()
        handler.stop()
        handler.stop()


# ============================================================================
# Speak Properties
# ============================================================================

class TestSpeakProperties:
    """Properties about speak() behavior."""

    @given(text=st.text(max_size=1000))
    @oracle_settings
    def test_text_handler_speak_never_crashes(self, text):
        """text handler speak() handles any string."""
        from teller import get_handler
        handler = get_handler("text")
        # Should not raise
        handler.speak(text)

    @given(text=st.text(max_size=1000))
    @oracle_settings
    def test_debug_handler_speak_never_crashes(self, text):
        """debug handler speak() handles any string."""
        from teller import get_handler
        handler = get_handler("debug")
        # Should not raise
        handler.speak(text)

    @given(
        text=st.text(max_size=100),
        speed=st.integers(min_value=-1000, max_value=10000)
    )
    @oracle_settings
    def test_speed_parameter_doesnt_crash(self, text, speed):
        """Any integer speed value doesn't crash."""
        from teller import get_handler
        handler = get_handler("text")
        handler.speak(text, speed=speed)

    @given(
        text=st.text(max_size=100),
        wait=st.booleans()
    )
    @oracle_settings
    def test_wait_parameter_is_boolean(self, text, wait):
        """Boolean wait values work correctly."""
        from teller import get_handler
        handler = get_handler("text")
        handler.speak(text, wait=wait)


# ============================================================================
# Discovery Properties
# ============================================================================

class TestDiscoveryProperties:
    """Properties about handler discovery."""

    @given(st.data())
    @oracle_settings
    def test_list_handlers_is_stable(self, data):
        """list_handlers() returns same result each time."""
        from teller import list_handlers
        result1 = list_handlers()
        result2 = list_handlers()
        assert set(result1) == set(result2)

    @given(st.data())
    @oracle_settings
    def test_listed_handlers_are_gettable(self, data):
        """Every handler in list_handlers() can be retrieved."""
        from teller import list_handlers, get_handler
        for name in list_handlers():
            handler = get_handler(name)
            assert handler is not None
            assert handler.name == name

    @given(handler_name=st.sampled_from(["text", "debug", "espeak"]))
    @oracle_settings
    def test_get_handler_returns_fresh_instance(self, handler_name):
        """get_handler() returns new instance each call."""
        from teller import get_handler
        h1 = get_handler(handler_name)
        h2 = get_handler(handler_name)
        assert h1 is not h2

    @given(name=st.text(min_size=1, max_size=50).filter(
        lambda x: x not in ["text", "debug", "espeak"]
    ))
    @oracle_settings
    def test_unknown_handler_raises(self, name):
        """Unknown handler names raise KeyError."""
        from teller import get_handler
        assume(name.strip() != "")  # Non-empty after strip
        with pytest.raises(KeyError):
            get_handler(name)


# ============================================================================
# Espeak Properties (with mocking)
# ============================================================================

class TestEspeakProperties:
    """Properties specific to espeak handler."""

    @given(text=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    @oracle_settings
    def test_espeak_calls_subprocess_for_nonempty(self, text):
        """espeak calls subprocess for non-empty text."""
        from teller import get_handler
        handler = get_handler("espeak")

        with patch("subprocess.Popen") as mock_popen, \
             patch("subprocess.run"):  # For stop()
            mock_popen.return_value = MagicMock()
            handler.speak(text)
            # Should have called Popen (async mode)
            mock_popen.assert_called()

    @given(speed=st.integers(min_value=1, max_value=1000))
    @oracle_settings
    def test_espeak_passes_speed_to_command(self, speed):
        """Speed parameter appears in espeak command."""
        from teller import get_handler
        handler = get_handler("espeak")

        with patch("subprocess.Popen") as mock_popen, \
             patch("subprocess.run"):
            mock_popen.return_value = MagicMock()
            handler.speak("test", speed=speed)

            if mock_popen.called:
                call_args = mock_popen.call_args
                cmd = call_args[0][0] if call_args[0] else call_args.kwargs.get("args", [])
                # Speed should be in command
                assert any(str(speed) in str(arg) for arg in cmd)


# ============================================================================
# Consistency Properties
# ============================================================================

class TestConsistencyProperties:
    """Cross-cutting consistency properties."""

    @given(handler_name=st.sampled_from(["text", "debug", "espeak"]))
    @oracle_settings
    def test_handler_name_matches_requested(self, handler_name):
        """Returned handler's name matches request."""
        from teller import get_handler
        handler = get_handler(handler_name)
        assert handler.name == handler_name

    @given(n=st.integers(min_value=1, max_value=10))
    @oracle_settings
    def test_multiple_stops_safe(self, n):
        """Calling stop() N times is safe."""
        from teller import get_handler
        handler = get_handler("text")
        for _ in range(n):
            handler.stop()

    @given(n=st.integers(min_value=1, max_value=10))
    @oracle_settings
    def test_speak_stop_alternation(self, n):
        """Alternating speak/stop is safe."""
        from teller import get_handler
        handler = get_handler("text")
        for _ in range(n):
            handler.speak("hello")
            handler.stop()
