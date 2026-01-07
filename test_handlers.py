"""
Tests for mode handlers.
"""

import pytest
from unittest.mock import MagicMock, call

from listener import KeyEvent, SpecialKey, EventType
from mode import ModeContext
from handlers import (
    options_handler,
    confirm_handler,
    clipboard_handler,
    browse_handler,
    register_confirm_action,
    CONFIRM_ACTIONS,
    status,
    is_valid_url,
    looks_like_domain,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_store():
    """Create a mock Store with config methods."""
    store = MagicMock()
    store._config = {}

    def get_config(key, default=None):
        return store._config.get(key, default)

    def set_config(key, value, description=None):
        store._config[key] = value

    store.get_config = MagicMock(side_effect=get_config)
    store.set_config = MagicMock(side_effect=set_config)
    return store


@pytest.fixture
def mock_teller():
    """Create a mock Teller."""
    teller = MagicMock()
    teller.spoken = []

    def speak(text, **kwargs):
        teller.spoken.append(text)

    teller.speak = MagicMock(side_effect=speak)
    return teller


@pytest.fixture
def mock_context(mock_store, mock_teller):
    """Create a mock ModeContext."""
    ctx = MagicMock(spec=ModeContext)
    ctx.store = mock_store
    ctx.teller = mock_teller
    ctx.back = MagicMock()
    ctx.switch = MagicMock()
    return ctx


def make_event(char=None, key=None):
    """Helper to create KeyEvent."""
    return KeyEvent(
        char=char,
        key=key,
        modifiers=frozenset(),
        event_type=EventType.PRESS,
    )


# =============================================================================
# Status Helper Tests
# =============================================================================

class TestStatusHelper:
    def test_true_returns_on(self):
        assert status(True) == "on"

    def test_false_returns_off(self):
        assert status(False) == "off"


# =============================================================================
# Options Handler Tests
# =============================================================================

class TestOptionsHandler:
    """Test options mode handler."""

    def test_escape_calls_back(self, mock_context):
        """Escape key returns to previous mode."""
        event = make_event(key=SpecialKey.ESCAPE)
        options_handler(event, mock_context)
        mock_context.back.assert_called_once()

    def test_s_toggles_strip_input_on(self, mock_context):
        """Pressing 's' toggles strip_input from off to on."""
        mock_context.store._config["strip_input"] = "off"

        event = make_event(char="s")
        options_handler(event, mock_context)

        mock_context.store.set_config.assert_called_with("strip_input", "on")
        assert "on" in mock_context.teller.spoken[0]

    def test_s_toggles_strip_input_off(self, mock_context):
        """Pressing 's' toggles strip_input from on to off."""
        mock_context.store._config["strip_input"] = "on"

        event = make_event(char="s")
        options_handler(event, mock_context)

        mock_context.store.set_config.assert_called_with("strip_input", "off")
        assert "off" in mock_context.teller.spoken[0]

    def test_d_toggles_debug_mode_on(self, mock_context):
        """Pressing 'd' toggles debug_mode from off to on."""
        mock_context.store._config["debug_mode"] = "off"

        event = make_event(char="d")
        options_handler(event, mock_context)

        mock_context.store.set_config.assert_called_with("debug_mode", "on")
        assert "on" in mock_context.teller.spoken[0]

    def test_d_toggles_debug_mode_off(self, mock_context):
        """Pressing 'd' toggles debug_mode from on to off."""
        mock_context.store._config["debug_mode"] = "on"

        event = make_event(char="d")
        options_handler(event, mock_context)

        mock_context.store.set_config.assert_called_with("debug_mode", "off")
        assert "off" in mock_context.teller.spoken[0]

    def test_a_toggles_default_action_to_auto(self, mock_context):
        """Pressing 'a' toggles default_action from copy to auto."""
        mock_context.store._config["default_action"] = "copy"

        event = make_event(char="a")
        options_handler(event, mock_context)

        # Check that set_config was called with auto
        calls = mock_context.store.set_config.call_args_list
        assert any("auto" in str(c) for c in calls)
        assert "auto" in mock_context.teller.spoken[0]

    def test_a_toggles_default_action_to_copy(self, mock_context):
        """Pressing 'a' toggles default_action from auto to copy."""
        mock_context.store._config["default_action"] = "auto"

        event = make_event(char="a")
        options_handler(event, mock_context)

        calls = mock_context.store.set_config.call_args_list
        assert any("copy" in str(c) for c in calls)
        assert "copy" in mock_context.teller.spoken[0]

    def test_unknown_key_ignored(self, mock_context):
        """Unknown keys are ignored (no error, no action)."""
        event = make_event(char="x")
        options_handler(event, mock_context)

        # Should not call speak or back
        mock_context.teller.speak.assert_not_called()
        mock_context.back.assert_not_called()

    def test_special_key_without_handler_ignored(self, mock_context):
        """Special keys without handlers are ignored."""
        event = make_event(key=SpecialKey.UP)
        options_handler(event, mock_context)

        mock_context.teller.speak.assert_not_called()
        mock_context.back.assert_not_called()

    def test_default_strip_input_is_on(self, mock_context):
        """Default strip_input is 'on' when not set."""
        # Config is empty
        event = make_event(char="s")
        options_handler(event, mock_context)

        # Should toggle from default "on" to "off"
        mock_context.store.set_config.assert_called_with("strip_input", "off")

    def test_default_debug_mode_is_off(self, mock_context):
        """Default debug_mode is 'off' when not set."""
        # Config is empty
        event = make_event(char="d")
        options_handler(event, mock_context)

        # Should toggle from default "off" to "on"
        mock_context.store.set_config.assert_called_with("debug_mode", "on")

    def test_default_default_action_is_copy(self, mock_context):
        """Default default_action is 'copy' when not set."""
        # Config is empty
        event = make_event(char="a")
        options_handler(event, mock_context)

        # Should toggle from default "copy" to "auto"
        calls = mock_context.store.set_config.call_args_list
        assert any("auto" in str(c) for c in calls)


# =============================================================================
# Confirm Handler Tests
# =============================================================================

@pytest.fixture
def mock_context_with_state(mock_store, mock_teller):
    """Create a mock ModeContext with working get_state()."""
    ctx = MagicMock(spec=ModeContext)
    ctx.store = mock_store
    ctx.teller = mock_teller
    ctx.back = MagicMock()
    ctx.switch = MagicMock()

    # Real state dict
    state = {}
    ctx.get_state = MagicMock(return_value=state)
    ctx._state = state  # For test access

    return ctx


class TestConfirmHandler:
    """Test confirm mode handler."""

    def test_escape_cancels(self, mock_context_with_state):
        """Escape key cancels and returns to previous mode."""
        ctx = mock_context_with_state
        event = make_event(key=SpecialKey.ESCAPE)

        confirm_handler(event, ctx)

        ctx.back.assert_called_once()
        assert "Cancelled" in ctx.teller.spoken[0]

    def test_n_cancels(self, mock_context_with_state):
        """'n' key cancels and returns to previous mode."""
        ctx = mock_context_with_state
        event = make_event(char="n")

        confirm_handler(event, ctx)

        ctx.back.assert_called_once()
        assert "Cancelled" in ctx.teller.spoken[0]

    def test_n_uppercase_cancels(self, mock_context_with_state):
        """'N' key (uppercase) cancels."""
        ctx = mock_context_with_state
        event = make_event(char="N")

        confirm_handler(event, ctx)

        ctx.back.assert_called_once()

    def test_y_confirms_and_executes_action(self, mock_context_with_state):
        """'y' key confirms and executes registered action."""
        ctx = mock_context_with_state

        # Register a test action
        action_called = []
        def test_action(params, context):
            action_called.append(params)
            return True, "Action done"

        register_confirm_action("test_action", test_action)

        # Set up state
        ctx._state["action"] = "test_action"
        ctx._state["params"] = {"foo": "bar"}

        event = make_event(char="y")
        confirm_handler(event, ctx)

        # Action should have been called
        assert len(action_called) == 1
        assert action_called[0] == {"foo": "bar"}

        # Should speak message and return
        assert "Action done" in ctx.teller.spoken[0]
        ctx.back.assert_called_once()

        # Cleanup
        del CONFIRM_ACTIONS["test_action"]

    def test_y_uppercase_confirms(self, mock_context_with_state):
        """'Y' key (uppercase) confirms."""
        ctx = mock_context_with_state

        action_called = []
        def test_action(params, context):
            action_called.append(True)
            return True, "Done"

        register_confirm_action("test_action2", test_action)
        ctx._state["action"] = "test_action2"

        event = make_event(char="Y")
        confirm_handler(event, ctx)

        assert len(action_called) == 1
        ctx.back.assert_called_once()

        del CONFIRM_ACTIONS["test_action2"]

    def test_unknown_action_speaks_error(self, mock_context_with_state):
        """Unknown action name speaks error message."""
        ctx = mock_context_with_state
        ctx._state["action"] = "nonexistent_action"

        event = make_event(char="y")
        confirm_handler(event, ctx)

        assert "Unknown action" in ctx.teller.spoken[0]
        ctx.back.assert_called_once()

    def test_other_key_repeats_prompt(self, mock_context_with_state):
        """Other keys repeat the prompt."""
        ctx = mock_context_with_state
        ctx._state["prompt"] = "Delete buffer? y/n"

        event = make_event(char="x")
        confirm_handler(event, ctx)

        assert "Delete buffer? y/n" in ctx.teller.spoken[0]
        ctx.back.assert_not_called()

    def test_other_key_no_prompt_silent(self, mock_context_with_state):
        """Other keys with no prompt are silent."""
        ctx = mock_context_with_state
        # No prompt set

        event = make_event(char="x")
        confirm_handler(event, ctx)

        ctx.teller.speak.assert_not_called()
        ctx.back.assert_not_called()

    def test_state_cleared_on_confirm(self, mock_context_with_state):
        """State is cleared after confirm."""
        ctx = mock_context_with_state

        def test_action(params, context):
            return True, "Done"

        register_confirm_action("clear_test", test_action)
        ctx._state["action"] = "clear_test"
        ctx._state["params"] = {"x": 1}
        ctx._state["prompt"] = "Test?"

        event = make_event(char="y")
        confirm_handler(event, ctx)

        # State should be cleared
        assert ctx._state == {}

        del CONFIRM_ACTIONS["clear_test"]

    def test_state_cleared_on_cancel(self, mock_context_with_state):
        """State is cleared after cancel."""
        ctx = mock_context_with_state
        ctx._state["action"] = "some_action"
        ctx._state["params"] = {"x": 1}

        event = make_event(char="n")
        confirm_handler(event, ctx)

        # State should be cleared
        assert ctx._state == {}

    def test_special_key_ignored(self, mock_context_with_state):
        """Non-escape special keys are ignored."""
        ctx = mock_context_with_state
        ctx._state["prompt"] = "Test?"

        event = make_event(key=SpecialKey.UP)
        confirm_handler(event, ctx)

        # Should not cancel, should not repeat prompt (no char)
        ctx.back.assert_not_called()
        ctx.teller.speak.assert_not_called()


# =============================================================================
# Clipboard Handler Tests
# =============================================================================

@pytest.fixture
def mock_context_with_mark(mock_store, mock_teller):
    """Create a mock ModeContext with mark."""
    ctx = MagicMock(spec=ModeContext)
    ctx.store = mock_store
    ctx.teller = mock_teller
    ctx.back = MagicMock()
    ctx.switch = MagicMock()

    # Mock mark
    ctx.mark = MagicMock()
    ctx.mark.buffer_id = 1

    return ctx


class TestClipboardHandler:
    """Test clipboard mode handler."""

    def test_escape_returns_to_previous(self, mock_context_with_mark, monkeypatch):
        """Escape key returns to previous mode."""
        ctx = mock_context_with_mark
        event = make_event(key=SpecialKey.ESCAPE)

        clipboard_handler(event, ctx)

        ctx.back.assert_called_once()

    def test_stores_clipboard_at_key(self, mock_context_with_mark, monkeypatch):
        """Alphanumeric key stores clipboard content."""
        import pyperclip
        monkeypatch.setattr(pyperclip, "paste", lambda: "test content")

        ctx = mock_context_with_mark
        event = make_event(char="a")

        clipboard_handler(event, ctx)

        # Should store content
        ctx.store.set.assert_called_once_with("a", "test content", buffer_id=1)

        # Should speak and switch to read
        assert len(ctx.teller.spoken) == 1
        assert "Stored" in ctx.teller.spoken[0]
        ctx.switch.assert_called_with("read")

    def test_strips_content_when_enabled(self, mock_context_with_mark, monkeypatch):
        """Content is stripped when strip_input is on."""
        import pyperclip
        monkeypatch.setattr(pyperclip, "paste", lambda: "  spaced content  ")

        ctx = mock_context_with_mark
        ctx.store._config["strip_input"] = "on"

        event = make_event(char="b")
        clipboard_handler(event, ctx)

        ctx.store.set.assert_called_once_with("b", "spaced content", buffer_id=1)

    def test_no_strip_when_disabled(self, mock_context_with_mark, monkeypatch):
        """Content is not stripped when strip_input is off."""
        import pyperclip
        monkeypatch.setattr(pyperclip, "paste", lambda: "  spaced content  ")

        ctx = mock_context_with_mark
        ctx.store._config["strip_input"] = "off"

        event = make_event(char="c")
        clipboard_handler(event, ctx)

        ctx.store.set.assert_called_once_with("c", "  spaced content  ", buffer_id=1)

    def test_non_alnum_key_ignored(self, mock_context_with_mark, monkeypatch):
        """Non-alphanumeric keys are ignored."""
        import pyperclip
        monkeypatch.setattr(pyperclip, "paste", lambda: "content")

        ctx = mock_context_with_mark
        event = make_event(char="!")

        clipboard_handler(event, ctx)

        ctx.store.set.assert_not_called()
        ctx.switch.assert_not_called()

    def test_special_key_ignored(self, mock_context_with_mark):
        """Non-escape special keys are ignored."""
        ctx = mock_context_with_mark
        event = make_event(key=SpecialKey.UP)

        clipboard_handler(event, ctx)

        ctx.store.set.assert_not_called()
        ctx.back.assert_not_called()

    def test_numeric_key_works(self, mock_context_with_mark, monkeypatch):
        """Numeric keys also store content."""
        import pyperclip
        monkeypatch.setattr(pyperclip, "paste", lambda: "numeric content")

        ctx = mock_context_with_mark
        event = make_event(char="5")

        clipboard_handler(event, ctx)

        ctx.store.set.assert_called_once_with("5", "numeric content", buffer_id=1)

    def test_uses_current_buffer_id(self, mock_context_with_mark, monkeypatch):
        """Stores in the current buffer from mark."""
        import pyperclip
        monkeypatch.setattr(pyperclip, "paste", lambda: "content")

        ctx = mock_context_with_mark
        ctx.mark.buffer_id = 42

        event = make_event(char="x")
        clipboard_handler(event, ctx)

        ctx.store.set.assert_called_once_with("x", "content", buffer_id=42)

    def test_empty_clipboard_stores_empty(self, mock_context_with_mark, monkeypatch):
        """Empty clipboard stores empty string."""
        import pyperclip
        monkeypatch.setattr(pyperclip, "paste", lambda: "")

        ctx = mock_context_with_mark
        event = make_event(char="e")

        clipboard_handler(event, ctx)

        ctx.store.set.assert_called_once_with("e", "", buffer_id=1)


# =============================================================================
# URL Helper Tests
# =============================================================================

class TestIsValidUrl:
    """Test URL validation helper."""

    def test_http_url(self):
        assert is_valid_url("http://example.com") is True

    def test_https_url(self):
        assert is_valid_url("https://example.com") is True

    def test_url_with_path(self):
        assert is_valid_url("https://example.com/path/to/page") is True

    def test_url_with_port(self):
        assert is_valid_url("http://localhost:8080") is True

    def test_ip_url(self):
        assert is_valid_url("http://192.168.1.1") is True

    def test_no_protocol_invalid(self):
        assert is_valid_url("example.com") is False

    def test_plain_text_invalid(self):
        assert is_valid_url("hello world") is False


class TestLooksLikeDomain:
    """Test domain detection helper."""

    def test_simple_domain(self):
        assert looks_like_domain("example.com") is True

    def test_subdomain(self):
        assert looks_like_domain("www.example.com") is True

    def test_domain_with_path(self):
        assert looks_like_domain("example.com/path") is True

    def test_url_with_protocol_false(self):
        # Already has protocol - not just a domain
        assert looks_like_domain("http://example.com") is False

    def test_plain_word_false(self):
        assert looks_like_domain("hello") is False

    def test_ip_false(self):
        assert looks_like_domain("192.168.1.1") is False


# =============================================================================
# Browse Handler Tests
# =============================================================================

class TestBrowseHandler:
    """Test browse mode handler."""

    def test_escape_returns_to_previous(self, mock_context_with_mark):
        """Escape key returns to previous mode."""
        ctx = mock_context_with_mark
        event = make_event(key=SpecialKey.ESCAPE)

        browse_handler(event, ctx)

        ctx.back.assert_called_once()

    def test_no_data_speaks_error(self, mock_context_with_mark):
        """No data at key speaks error."""
        ctx = mock_context_with_mark
        ctx.store.get = MagicMock(return_value=None)

        event = make_event(char="a")
        browse_handler(event, ctx)

        assert "No data" in ctx.teller.spoken[0]

    def test_opens_valid_url(self, mock_context_with_mark, monkeypatch):
        """Valid URL is opened in browser."""
        import webbrowser
        opened_urls = []
        monkeypatch.setattr(webbrowser, "open", lambda url: opened_urls.append(url))

        # Mock sys.exit to not actually exit
        monkeypatch.setattr("sys.exit", lambda code: None)

        ctx = mock_context_with_mark
        ctx.store.get = MagicMock(return_value={"value": "https://example.com"})

        event = make_event(char="u")
        browse_handler(event, ctx)

        assert "https://example.com" in opened_urls
        assert "Opening" in ctx.teller.spoken[0]

    def test_adds_http_to_domain(self, mock_context_with_mark, monkeypatch):
        """Domain without protocol gets http:// added."""
        import webbrowser
        opened_urls = []
        monkeypatch.setattr(webbrowser, "open", lambda url: opened_urls.append(url))
        monkeypatch.setattr("sys.exit", lambda code: None)

        ctx = mock_context_with_mark
        ctx.store.get = MagicMock(return_value={"value": "example.com"})

        event = make_event(char="d")
        browse_handler(event, ctx)

        assert "http://example.com" in opened_urls
        # Should mention adding protocol
        assert any("http" in s.lower() for s in ctx.teller.spoken)

    def test_invalid_url_speaks_error(self, mock_context_with_mark):
        """Invalid URL speaks error and doesn't open."""
        ctx = mock_context_with_mark
        ctx.store.get = MagicMock(return_value={"value": "not a url"})

        event = make_event(char="x")
        browse_handler(event, ctx)

        assert "Not a valid URL" in ctx.teller.spoken[0]

    def test_non_alnum_key_ignored(self, mock_context_with_mark):
        """Non-alphanumeric keys are ignored."""
        ctx = mock_context_with_mark
        event = make_event(char="!")

        browse_handler(event, ctx)

        ctx.store.get.assert_not_called()

    def test_special_key_ignored(self, mock_context_with_mark):
        """Non-escape special keys are ignored."""
        ctx = mock_context_with_mark
        event = make_event(key=SpecialKey.UP)

        browse_handler(event, ctx)

        ctx.store.get.assert_not_called()
        ctx.back.assert_not_called()
