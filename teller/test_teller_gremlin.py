"""Gremlin tests - adversarial attacks on teller.

Try to break the implementation with malicious/malformed inputs.
"""

import pytest
from unittest.mock import patch, MagicMock


# ============================================================================
# Type Confusion Attacks
# ============================================================================

class TestTypeConfusion:
    """What happens with wrong types?"""

    def test_speak_with_none(self):
        """None as text - should not crash."""
        from teller import get_handler
        handler = get_handler("text")
        # Should handle gracefully - either skip or convert
        handler.speak(None)  # Should not raise

    def test_speak_with_integer(self):
        """Integer as text - coerces to string or skips."""
        from teller import get_handler
        handler = get_handler("text")
        handler.speak(123)  # Should not crash

    def test_speak_with_list(self):
        """List as text - should handle somehow."""
        from teller import get_handler
        handler = get_handler("text")
        handler.speak(["hello", "world"])  # Should not crash

    def test_speak_with_dict(self):
        """Dict as text - should handle somehow."""
        from teller import get_handler
        handler = get_handler("text")
        handler.speak({"key": "value"})  # Should not crash

    def test_speak_with_bytes(self):
        """Bytes as text - may need decoding."""
        from teller import get_handler
        handler = get_handler("text")
        handler.speak(b"hello bytes")  # Should not crash

    def test_speed_as_string(self):
        """String speed - should handle."""
        from teller import get_handler
        handler = get_handler("text")
        handler.speak("test", speed="fast")  # Should not crash

    def test_speed_as_none(self):
        """None speed - should use default."""
        from teller import get_handler
        handler = get_handler("text")
        handler.speak("test", speed=None)  # Should not crash

    def test_wait_as_string(self):
        """String wait - truthy handling."""
        from teller import get_handler
        handler = get_handler("text")
        handler.speak("test", wait="yes")  # Should not crash


# ============================================================================
# Malformed Input Attacks
# ============================================================================

class TestMalformedInputs:
    """Weird but syntactically valid inputs."""

    def test_null_bytes_in_text(self):
        """Null bytes in text."""
        from teller import get_handler
        handler = get_handler("text")
        handler.speak("hello\x00world")  # Should not crash

    def test_control_characters(self):
        """ASCII control characters."""
        from teller import get_handler
        handler = get_handler("text")
        handler.speak("hello\x07\x08\x1b[31mworld")  # Bell, backspace, ANSI

    def test_only_whitespace(self):
        """Only whitespace - edge case."""
        from teller import get_handler
        handler = get_handler("text")
        handler.speak("   \t\n\r   ")

    def test_mixed_encodings(self):
        """Text that looks like it has encoding issues."""
        from teller import get_handler
        handler = get_handler("text")
        handler.speak("caf\xc3\xa9")  # UTF-8 bytes as string

    def test_surrogate_pairs(self):
        """Unicode surrogate pairs."""
        from teller import get_handler
        handler = get_handler("text")
        handler.speak("emoji: \U0001F600")  # Grinning face

    def test_extremely_long_text(self):
        """Very long text - memory/performance."""
        from teller import get_handler
        handler = get_handler("text")
        long_text = "x" * 1_000_000  # 1MB of text
        handler.speak(long_text)  # Should not crash (may be slow)

    def test_many_newlines(self):
        """Text with thousands of newlines."""
        from teller import get_handler
        handler = get_handler("text")
        handler.speak("\n" * 10000)


# ============================================================================
# Shell Injection Attacks (espeak)
# ============================================================================

class TestShellInjection:
    """Attempt shell injection via espeak handler."""

    def test_semicolon_injection(self):
        """Semicolon command separator."""
        from teller import get_handler
        handler = get_handler("espeak")
        with patch("subprocess.Popen") as mock:
            mock.return_value = MagicMock()
            handler.speak("hello; rm -rf /")
            # Should pass as single argument, not shell-parsed
            call_args = mock.call_args
            if call_args:
                # Should NOT use shell=True
                assert call_args.kwargs.get("shell") != True

    def test_backtick_injection(self):
        """Backtick command substitution."""
        from teller import get_handler
        handler = get_handler("espeak")
        with patch("subprocess.Popen") as mock:
            mock.return_value = MagicMock()
            handler.speak("hello `whoami`")

    def test_dollar_paren_injection(self):
        """$() command substitution."""
        from teller import get_handler
        handler = get_handler("espeak")
        with patch("subprocess.Popen") as mock:
            mock.return_value = MagicMock()
            handler.speak("hello $(cat /etc/passwd)")

    def test_pipe_injection(self):
        """Pipe to another command."""
        from teller import get_handler
        handler = get_handler("espeak")
        with patch("subprocess.Popen") as mock:
            mock.return_value = MagicMock()
            handler.speak("hello | cat /etc/passwd")

    def test_redirect_injection(self):
        """Output redirection."""
        from teller import get_handler
        handler = get_handler("espeak")
        with patch("subprocess.Popen") as mock:
            mock.return_value = MagicMock()
            handler.speak("hello > /tmp/pwned")


# ============================================================================
# Resource Exhaustion Attacks
# ============================================================================

class TestResourceExhaustion:
    """Try to exhaust resources."""

    def test_rapid_speak_calls(self):
        """Many rapid successive calls."""
        from teller import get_handler
        handler = get_handler("text")
        for _ in range(1000):
            handler.speak("rapid fire")

    def test_rapid_stop_calls(self):
        """Many rapid stop calls."""
        from teller import get_handler
        handler = get_handler("text")
        for _ in range(1000):
            handler.stop()

    def test_interleaved_speak_stop(self):
        """Interleaved speak and stop."""
        from teller import get_handler
        handler = get_handler("text")
        for _ in range(500):
            handler.speak("hello")
            handler.stop()

    def test_many_handler_instances(self):
        """Create many handler instances."""
        from teller import get_handler
        handlers = [get_handler("text") for _ in range(1000)]
        assert len(handlers) == 1000


# ============================================================================
# Handler Discovery Attacks
# ============================================================================

class TestDiscoveryAttacks:
    """Attack the handler discovery mechanism."""

    def test_get_handler_with_path_traversal(self):
        """Path traversal in handler name."""
        from teller import get_handler
        with pytest.raises(KeyError):
            get_handler("../../../etc/passwd")

    def test_get_handler_with_special_chars(self):
        """Special characters in handler name."""
        from teller import get_handler
        with pytest.raises(KeyError):
            get_handler("handler;rm")

    def test_get_handler_empty_string(self):
        """Empty string as handler name."""
        from teller import get_handler
        with pytest.raises(KeyError):
            get_handler("")

    def test_get_handler_whitespace(self):
        """Whitespace as handler name."""
        from teller import get_handler
        with pytest.raises(KeyError):
            get_handler("   ")


# ============================================================================
# Espeak-Specific Edge Cases
# ============================================================================

class TestEspeakEdgeCases:
    """Edge cases specific to espeak handler."""

    def test_quotes_in_text(self):
        """Quotes should be passed correctly."""
        from teller import get_handler
        handler = get_handler("espeak")
        with patch("subprocess.Popen") as mock:
            mock.return_value = MagicMock()
            handler.speak('He said "hello"')
            # Should work - list form handles quotes

    def test_single_quotes_in_text(self):
        """Single quotes in text."""
        from teller import get_handler
        handler = get_handler("espeak")
        with patch("subprocess.Popen") as mock:
            mock.return_value = MagicMock()
            handler.speak("It's working")

    def test_backslashes_in_text(self):
        """Backslashes in text."""
        from teller import get_handler
        handler = get_handler("espeak")
        with patch("subprocess.Popen") as mock:
            mock.return_value = MagicMock()
            handler.speak("path\\to\\file")

    def test_unicode_in_espeak(self):
        """Unicode should be passed to espeak."""
        from teller import get_handler
        handler = get_handler("espeak")
        with patch("subprocess.Popen") as mock:
            mock.return_value = MagicMock()
            handler.speak("Héllo wörld")

    def test_espeak_not_found(self):
        """espeak executable missing."""
        from teller import get_handler
        handler = get_handler("espeak")
        with patch("shutil.which", return_value=None):
            # Re-init to trigger _find_espeak
            handler._espeak_cmd = handler._find_espeak()
            # Now speak should fail gracefully
            handler.speak("test")  # Should not raise

    def test_espeak_process_fails(self):
        """espeak process fails to start."""
        from teller import get_handler
        handler = get_handler("espeak")
        with patch("subprocess.Popen") as mock:
            mock.side_effect = OSError("No such file")
            handler.speak("test")  # Should not raise
