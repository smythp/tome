"""Comprehensive tests for teller - the pluggable TTS primitive.

Test-first design per RSP playbook. Tests written before implementation.
"""

import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_handlers_dir(tmp_path):
    """Create a temporary handlers directory for discovery tests."""
    handlers_dir = tmp_path / "handlers"
    handlers_dir.mkdir()
    return handlers_dir


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for espeak tests."""
    with patch("subprocess.Popen") as mock_popen, \
         patch("subprocess.call") as mock_call:
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        yield {
            "Popen": mock_popen,
            "call": mock_call,
            "process": mock_process,
        }


# ============================================================================
# Handler Protocol Compliance
# ============================================================================

class TestHandlerProtocol:
    """Every handler must satisfy the protocol."""

    @pytest.fixture(params=["text", "debug", "espeak"])
    def handler(self, request):
        """Parametrized fixture for all handler types."""
        from teller import get_handler
        return get_handler(request.param)

    def test_has_name_property(self, handler):
        """Handler must have a name property."""
        assert hasattr(handler, "name")

    def test_name_is_string(self, handler):
        """Handler name must be a string."""
        assert isinstance(handler.name, str)
        assert len(handler.name) > 0

    def test_has_speak_method(self, handler):
        """Handler must have speak method."""
        assert hasattr(handler, "speak")
        assert callable(handler.speak)

    def test_has_stop_method(self, handler):
        """Handler must have stop method."""
        assert hasattr(handler, "stop")
        assert callable(handler.stop)

    def test_stop_callable_without_args(self, handler):
        """stop() should be callable with no arguments."""
        # Should not raise
        handler.stop()


# ============================================================================
# Auto-Discovery
# ============================================================================

class TestHandlerDiscovery:
    """Drop-in handler loading from directory."""

    def test_discovers_handlers_in_directory(self, temp_handlers_dir):
        """Handlers in directory are discovered and registered."""
        # Create a valid handler file
        handler_code = '''
from teller.base import BaseHandler

class TestHandler(BaseHandler):
    @property
    def name(self):
        return "test_handler"

    def speak(self, text, speed=270, wait=False):
        pass

    def stop(self):
        pass
'''
        (temp_handlers_dir / "test_handler.py").write_text(handler_code)

        from teller.discovery import discover_handlers
        handlers = discover_handlers(temp_handlers_dir)

        assert "test_handler" in handlers

    def test_ignores_init_py(self, temp_handlers_dir):
        """__init__.py is not treated as a handler module."""
        (temp_handlers_dir / "__init__.py").write_text("# init")

        from teller.discovery import discover_handlers
        handlers = discover_handlers(temp_handlers_dir)

        # Should not error, and __init__ shouldn't register as handler
        assert "__init__" not in handlers

    def test_ignores_non_handler_classes(self, temp_handlers_dir):
        """Files without BaseHandler subclass are ignored."""
        non_handler = '''
class NotAHandler:
    pass
'''
        (temp_handlers_dir / "not_a_handler.py").write_text(non_handler)

        from teller.discovery import discover_handlers
        handlers = discover_handlers(temp_handlers_dir)

        assert "not_a_handler" not in handlers
        assert len(handlers) == 0

    def test_handles_import_error_gracefully(self, temp_handlers_dir):
        """Import errors in handler files don't crash discovery."""
        bad_code = "import nonexistent_module_xyz"
        (temp_handlers_dir / "bad_handler.py").write_text(bad_code)

        from teller.discovery import discover_handlers
        # Should not raise
        handlers = discover_handlers(temp_handlers_dir)
        assert "bad_handler" not in handlers

    def test_registers_with_handler_name(self, temp_handlers_dir):
        """Handler is registered under its name property, not filename."""
        handler_code = '''
from teller.base import BaseHandler

class MyHandler(BaseHandler):
    @property
    def name(self):
        return "custom_name"

    def speak(self, text, speed=270, wait=False):
        pass

    def stop(self):
        pass
'''
        (temp_handlers_dir / "some_file.py").write_text(handler_code)

        from teller.discovery import discover_handlers
        handlers = discover_handlers(temp_handlers_dir)

        assert "custom_name" in handlers
        assert "some_file" not in handlers


# ============================================================================
# Text Handler
# ============================================================================

class TestTextHandler:
    """Plain text output for testing/CLI use."""

    @pytest.fixture
    def handler(self):
        from teller.handlers.text import TextHandler
        return TextHandler()

    def test_name_is_text(self, handler):
        assert handler.name == "text"

    def test_outputs_to_stdout(self, handler, capsys):
        """speak() prints text to stdout."""
        handler.speak("hello world")
        captured = capsys.readouterr()
        assert "hello world" in captured.out

    def test_empty_string_no_error(self, handler, capsys):
        """Empty string doesn't error."""
        handler.speak("")
        captured = capsys.readouterr()
        # Should complete without error

    def test_unicode_preserved(self, handler, capsys):
        """Unicode characters are preserved in output."""
        handler.speak("Hello ")
        captured = capsys.readouterr()
        assert "" in captured.out

    def test_long_text_not_truncated(self, handler, capsys):
        """Long text is not truncated."""
        long_text = "x" * 10000
        handler.speak(long_text)
        captured = capsys.readouterr()
        assert long_text in captured.out

    def test_speed_parameter_accepted(self, handler):
        """speed parameter is accepted (may be ignored for text)."""
        # Should not raise
        handler.speak("test", speed=100)
        handler.speak("test", speed=500)

    def test_wait_parameter_accepted(self, handler):
        """wait parameter is accepted (no-op for text)."""
        handler.speak("test", wait=True)
        handler.speak("test", wait=False)

    def test_stop_is_noop(self, handler):
        """stop() is safe to call (no-op for text)."""
        handler.stop()


# ============================================================================
# Debug Handler
# ============================================================================

class TestDebugHandler:
    """Text output with timing and metadata."""

    @pytest.fixture
    def handler(self):
        from teller.handlers.debug import DebugHandler
        return DebugHandler()

    def test_name_is_debug(self, handler):
        assert handler.name == "debug"

    def test_includes_spoken_text(self, handler, capsys):
        """Output includes the spoken text."""
        handler.speak("test message")
        captured = capsys.readouterr()
        assert "test message" in captured.out

    def test_includes_timestamp(self, handler, capsys):
        """Output includes a timestamp."""
        handler.speak("test")
        captured = capsys.readouterr()
        # Should have some time indicator - ISO format or similar
        # Check for common patterns
        assert any(x in captured.out for x in [":", "T", "Z", "20"])

    def test_includes_speed_value(self, handler, capsys):
        """Output shows the speed parameter."""
        handler.speak("test", speed=350)
        captured = capsys.readouterr()
        assert "350" in captured.out

    def test_includes_wait_value(self, handler, capsys):
        """Output shows the wait parameter."""
        handler.speak("test", wait=True)
        captured = capsys.readouterr()
        # Should indicate wait=True somehow
        assert "True" in captured.out or "wait" in captured.out.lower()

    def test_includes_handler_name(self, handler, capsys):
        """Output includes handler identifier."""
        handler.speak("test")
        captured = capsys.readouterr()
        assert "debug" in captured.out.lower()


# ============================================================================
# Espeak Handler
# ============================================================================

class TestEspeakHandler:
    """Real TTS via espeak subprocess."""

    @pytest.fixture
    def handler(self):
        from teller.handlers.espeak import EspeakHandler
        return EspeakHandler()

    def test_name_is_espeak(self, handler):
        assert handler.name == "espeak"

    def test_calls_espeak_subprocess(self, handler, mock_subprocess):
        """speak() invokes espeak via subprocess."""
        handler.speak("hello")

        # Either Popen or call should have been used
        assert mock_subprocess["Popen"].called or mock_subprocess["call"].called

    def test_passes_text_to_espeak(self, handler, mock_subprocess):
        """The text is passed to espeak."""
        handler.speak("hello world")

        if mock_subprocess["Popen"].called:
            args = mock_subprocess["Popen"].call_args
        else:
            args = mock_subprocess["call"].call_args

        # Check text is in the command
        cmd = args[0][0] if args[0] else args[1].get("args", [])
        assert "hello world" in str(cmd)

    def test_passes_speed_argument(self, handler, mock_subprocess):
        """Speed is passed to espeak -s flag."""
        handler.speak("test", speed=200)

        if mock_subprocess["Popen"].called:
            args = mock_subprocess["Popen"].call_args
        else:
            args = mock_subprocess["call"].call_args

        cmd = args[0][0] if args[0] else args[1].get("args", [])
        cmd_str = str(cmd)
        assert "200" in cmd_str or "-s200" in cmd_str or "-s 200" in cmd_str

    def test_wait_false_uses_popen(self, handler, mock_subprocess):
        """wait=False uses Popen (non-blocking)."""
        handler.speak("test", wait=False)
        assert mock_subprocess["Popen"].called

    def test_wait_true_uses_call(self, handler, mock_subprocess):
        """wait=True uses call (blocking)."""
        handler.speak("test", wait=True)
        assert mock_subprocess["call"].called

    def test_stop_kills_process(self, handler, mock_subprocess):
        """stop() terminates running espeak process."""
        with patch("subprocess.run") as mock_run:
            handler.stop()
            # Should try to kill espeak processes
            if mock_run.called:
                cmd = str(mock_run.call_args)
                assert "kill" in cmd.lower() or "espeak" in cmd.lower()


# ============================================================================
# Module API
# ============================================================================

class TestModuleAPI:
    """Top-level convenience functions."""

    def test_speak_uses_default_handler(self):
        """speak() delegates to the default handler."""
        import teller
        with patch.object(teller, "_default_handler") as mock_handler:
            mock_handler.speak = Mock()
            teller.speak("hello")
            mock_handler.speak.assert_called()

    def test_announce_calls_stop_then_speak(self):
        """announce() stops current speech then speaks."""
        import teller
        with patch.object(teller, "_default_handler") as mock_handler:
            mock_handler.stop = Mock()
            mock_handler.speak = Mock()
            teller.announce("urgent")
            mock_handler.stop.assert_called()
            mock_handler.speak.assert_called()

    def test_stop_delegates_to_handler(self):
        """stop() delegates to current handler."""
        import teller
        with patch.object(teller, "_default_handler") as mock_handler:
            mock_handler.stop = Mock()
            teller.stop()
            mock_handler.stop.assert_called()

    def test_get_handler_returns_by_name(self):
        """get_handler() returns handler instance by name."""
        from teller import get_handler
        handler = get_handler("text")
        assert handler.name == "text"

    def test_get_handler_unknown_raises(self):
        """get_handler() raises for unknown handler name."""
        from teller import get_handler
        with pytest.raises(KeyError):
            get_handler("nonexistent_handler_xyz")

    def test_list_handlers_returns_all(self):
        """list_handlers() returns all registered handler names."""
        from teller import list_handlers
        handlers = list_handlers()
        assert isinstance(handlers, list)
        assert "text" in handlers
        assert "debug" in handlers

    def test_set_default_handler_changes_default(self):
        """set_default_handler() changes which handler speak() uses."""
        import teller
        original = teller._default_handler
        try:
            teller.set_default_handler("text")
            assert teller._default_handler.name == "text"
            teller.set_default_handler("debug")
            assert teller._default_handler.name == "debug"
        finally:
            teller._default_handler = original

    def test_set_default_unknown_raises(self):
        """set_default_handler() raises for unknown handler."""
        from teller import set_default_handler
        with pytest.raises(KeyError):
            set_default_handler("nonexistent_xyz")


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    @pytest.fixture(params=["text", "debug"])
    def handler(self, request):
        """Test edge cases on non-audio handlers."""
        from teller import get_handler
        return get_handler(request.param)

    def test_empty_string(self, handler):
        """Empty string is handled."""
        handler.speak("")

    def test_whitespace_only(self, handler):
        """Whitespace-only string is handled."""
        handler.speak("   \n\t  ")

    def test_very_long_text(self, handler):
        """Very long text (100k chars) is handled."""
        handler.speak("x" * 100000)

    def test_unicode_emoji(self, handler):
        """Emoji are handled."""
        handler.speak("Hello  World ")

    def test_unicode_rtl(self, handler):
        """RTL text is handled."""
        handler.speak("")

    def test_newlines_in_text(self, handler):
        """Newlines in text are handled."""
        handler.speak("line1\nline2\nline3")

    def test_speed_boundary_low(self, handler):
        """Very low speed value."""
        handler.speak("test", speed=1)

    def test_speed_boundary_high(self, handler):
        """Very high speed value."""
        handler.speak("test", speed=1000)

    def test_speed_zero(self, handler):
        """Zero speed - implementation decides behavior."""
        # Should not crash
        try:
            handler.speak("test", speed=0)
        except ValueError:
            pass  # Acceptable to reject

    def test_speed_negative(self, handler):
        """Negative speed - implementation decides behavior."""
        try:
            handler.speak("test", speed=-100)
        except ValueError:
            pass  # Acceptable to reject


# ============================================================================
# Concurrency
# ============================================================================

class TestConcurrency:
    """Multiple calls, interruption behavior."""

    @pytest.fixture
    def handler(self):
        from teller import get_handler
        return get_handler("text")

    def test_rapid_successive_calls(self, handler):
        """Rapid successive calls don't crash."""
        for i in range(100):
            handler.speak(f"message {i}")

    def test_stop_during_noop(self, handler):
        """stop() when nothing is playing is safe."""
        handler.stop()
        handler.stop()
        handler.stop()

    def test_speak_stop_speak(self, handler):
        """speak-stop-speak sequence works."""
        handler.speak("first")
        handler.stop()
        handler.speak("second")
