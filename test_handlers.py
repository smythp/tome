"""
Tests for mode handlers.
"""

import pytest
from unittest.mock import MagicMock, call

from listener import KeyEvent, SpecialKey, EventType
from mode import ModeContext
from listener import Modifier
from handlers import (
    options_handler,
    confirm_handler,
    clipboard_handler,
    browse_handler,
    history_handler,
    list_handler,
    read_handler,
    register_confirm_action,
    CONFIRM_ACTIONS,
    status,
    is_valid_url,
    looks_like_file,
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


def make_event(char=None, key=None, modifiers=None):
    """Helper to create KeyEvent."""
    return KeyEvent(
        char=char,
        key=key,
        modifiers=frozenset(modifiers or []),
        event_type=EventType.PRESS,
    )


def make_ctrl_event(char):
    """Helper to create KeyEvent with Ctrl modifier."""
    return make_event(char=char, modifiers=[Modifier.CTRL])


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


class TestLooksLikeFile:
    """Test file path detection helper."""

    def test_file_uri(self):
        assert looks_like_file("file:///home/user/doc.txt") is True

    def test_absolute_path_exists(self, tmp_path):
        # Create a temp file
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")
        assert looks_like_file(str(test_file)) is True

    def test_absolute_path_not_exists(self):
        assert looks_like_file("/nonexistent/path/file.txt") is False

    def test_relative_path_false(self):
        assert looks_like_file("script.py") is False

    def test_domain_false(self):
        assert looks_like_file("example.com") is False

    def test_url_false(self):
        assert looks_like_file("https://example.com") is False

    def test_tilde_expansion(self):
        # Home directory always exists
        assert looks_like_file("~") is True

    def test_tilde_path_exists(self, tmp_path, monkeypatch):
        # Create file in fake home
        test_file = tmp_path / "testfile.txt"
        test_file.write_text("hello")
        monkeypatch.setenv("HOME", str(tmp_path))
        assert looks_like_file("~/testfile.txt") is True

    def test_tilde_path_not_exists(self):
        assert looks_like_file("~/nonexistent_file_12345.txt") is False


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

        # Mock os._exit to not actually exit (quit_app uses os._exit)
        monkeypatch.setattr("os._exit", lambda code: None)

        ctx = mock_context_with_mark
        ctx.store.get = MagicMock(return_value={"value": "https://example.com"})

        event = make_event(char="u")
        browse_handler(event, ctx)

        assert "https://example.com" in opened_urls
        assert "Opening" in ctx.teller.spoken[0]

    def test_domain_without_protocol_rejected(self, mock_context_with_mark):
        """Domain without protocol is rejected (protocol required)."""
        ctx = mock_context_with_mark
        ctx.store.get = MagicMock(return_value={"value": "example.com"})

        event = make_event(char="d")
        browse_handler(event, ctx)

        # Should speak "Not a valid URL"
        assert any("not a valid" in s.lower() for s in ctx.teller.spoken)

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


# =============================================================================
# History Handler Tests
# =============================================================================

@pytest.fixture
def mock_context_for_history(mock_store, mock_teller):
    """Create context with state for history mode."""
    ctx = MagicMock(spec=ModeContext)
    ctx.store = mock_store
    ctx.teller = mock_teller
    ctx.back = MagicMock()
    ctx.switch = MagicMock()

    # Real state dict with history entries
    state = {
        "entries": [
            {"id": 1, "value": "newest", "deleted": 0, "datetime": "2025-01-01 12:00:00"},
            {"id": 2, "value": "middle", "deleted": 0, "datetime": "2025-01-01 11:00:00"},
            {"id": 3, "value": "oldest", "deleted": 1, "datetime": "2025-01-01 10:00:00"},
        ],
        "current_index": 0,
        "global_mode": False,
        "key": "a",
        "buffer_id": 1,
    }
    ctx.get_state = MagicMock(return_value=state)
    ctx._state = state

    return ctx


class TestHistoryHandler:
    """Test history mode handler."""

    def test_escape_exits(self, mock_context_for_history):
        """Escape clears state and exits."""
        ctx = mock_context_for_history
        event = make_event(key=SpecialKey.ESCAPE)

        history_handler(event, ctx)

        ctx.back.assert_called_once()

    def test_up_navigates_previous(self, mock_context_for_history):
        """Up arrow navigates to older entry."""
        ctx = mock_context_for_history
        event = make_event(key=SpecialKey.UP)

        history_handler(event, ctx)

        assert ctx._state["current_index"] == 1
        assert "middle" in ctx.teller.spoken[0]

    def test_down_at_newest_announces_boundary(self, mock_context_for_history):
        """Down at newest entry announces boundary."""
        ctx = mock_context_for_history
        ctx._state["current_index"] = 0
        event = make_event(key=SpecialKey.DOWN)

        history_handler(event, ctx)

        assert "newest" in ctx.teller.spoken[0].lower()

    def test_ctrl_p_navigates_previous(self, mock_context_for_history):
        """Ctrl+P navigates to older entry."""
        ctx = mock_context_for_history
        event = make_ctrl_event("p")

        history_handler(event, ctx)

        assert ctx._state["current_index"] == 1

    def test_ctrl_n_navigates_next(self, mock_context_for_history):
        """Ctrl+N navigates to newer entry."""
        ctx = mock_context_for_history
        ctx._state["current_index"] = 1
        event = make_ctrl_event("n")

        history_handler(event, ctx)

        assert ctx._state["current_index"] == 0

    def test_delete_marks_entry_deleted(self, mock_context_for_history):
        """Delete key soft-deletes current entry."""
        ctx = mock_context_for_history
        ctx.store.delete_entry = MagicMock(return_value=True)
        event = make_event(key=SpecialKey.DELETE)

        history_handler(event, ctx)

        ctx.store.delete_entry.assert_called_once_with(1)
        assert ctx._state["entries"][0]["deleted"] == 1

    def test_delete_already_deleted_announces(self, mock_context_for_history):
        """Delete on already-deleted entry announces it."""
        ctx = mock_context_for_history
        ctx._state["current_index"] = 2  # The deleted one
        event = make_event(key=SpecialKey.DELETE)

        history_handler(event, ctx)

        assert "already deleted" in ctx.teller.spoken[0].lower()

    def test_ctrl_c_copies_to_clipboard(self, mock_context_for_history, monkeypatch):
        """Ctrl+C copies current entry to clipboard."""
        copied = []
        monkeypatch.setattr("pyperclip.copy", lambda x: copied.append(x))

        ctx = mock_context_for_history
        event = make_ctrl_event("c")

        history_handler(event, ctx)

        assert "newest" in copied
        assert "Copied" in ctx.teller.spoken[0]

    def test_ctrl_t_reads_timestamp(self, mock_context_for_history):
        """Ctrl+T reads timestamp of current entry."""
        ctx = mock_context_for_history
        event = make_ctrl_event("t")

        history_handler(event, ctx)

        assert "2025-01-01" in ctx.teller.spoken[0]

    def test_regular_char_exits(self, mock_context_for_history):
        """Regular character exits history mode."""
        ctx = mock_context_for_history
        event = make_event(char="x")

        history_handler(event, ctx)

        ctx.back.assert_called_once()

    def test_global_mode_formatting(self, mock_context_for_history):
        """Global mode includes buffer/key in output."""
        ctx = mock_context_for_history
        ctx._state["global_mode"] = True
        ctx._state["entries"][0]["key"] = "a"
        ctx._state["entries"][0]["buffer_id"] = 1
        event = make_event(key=SpecialKey.UP)

        history_handler(event, ctx)

        # Should mention buffer in global mode
        spoken = " ".join(ctx.teller.spoken)
        assert "Buffer" in spoken or "buffer" in spoken.lower()


# =============================================================================
# List Handler Tests
# =============================================================================

@pytest.fixture
def mock_context_for_list(mock_store, mock_teller):
    """Create context with state for list mode."""
    ctx = MagicMock(spec=ModeContext)
    ctx.store = mock_store
    ctx.teller = mock_teller
    ctx.back = MagicMock()
    ctx.switch = MagicMock()

    # Real state dict with list items
    # Items ordered by internal index (0=oldest, last=newest/item1)
    state = {
        "list_id": 100,
        "key": "l",
        "buffer_id": 1,
        "items": [
            {"id": 1, "value": "oldest (item 3)"},
            {"id": 2, "value": "middle (item 2)"},
            {"id": 3, "value": "newest (item 1)"},
        ],
        "current_index": 2,  # Start at item 1 (newest)
    }
    ctx.get_state = MagicMock(return_value=state)
    ctx._state = state

    return ctx


class TestListHandler:
    """Test list mode handler."""

    def test_escape_exits(self, mock_context_for_list):
        """Escape exits list mode."""
        ctx = mock_context_for_list
        event = make_event(key=SpecialKey.ESCAPE)

        list_handler(event, ctx)

        ctx.back.assert_called_once()

    def test_backspace_exits(self, mock_context_for_list):
        """Backspace exits list mode."""
        ctx = mock_context_for_list
        event = make_event(key=SpecialKey.BACKSPACE)

        list_handler(event, ctx)

        ctx.back.assert_called_once()

    def test_up_moves_toward_item_1(self, mock_context_for_list):
        """Up arrow moves toward item 1 (lower internal index = older)."""
        ctx = mock_context_for_list
        ctx._state["current_index"] = 1  # At middle
        event = make_event(key=SpecialKey.UP)

        list_handler(event, ctx)

        # Should move toward item 1 (lower internal index)
        assert ctx._state["current_index"] == 0

    def test_down_moves_away_from_item_1(self, mock_context_for_list):
        """Down arrow moves away from item 1 (higher internal index = newer)."""
        ctx = mock_context_for_list
        ctx._state["current_index"] = 0  # At item 1 (oldest)
        event = make_event(key=SpecialKey.DOWN)

        list_handler(event, ctx)

        assert ctx._state["current_index"] == 1

    def test_j_moves_next(self, mock_context_for_list):
        """'j' key moves to next item (toward higher numbers = newer)."""
        ctx = mock_context_for_list
        ctx._state["current_index"] = 0
        event = make_event(char="j")

        list_handler(event, ctx)

        assert ctx._state["current_index"] == 1

    def test_k_moves_previous(self, mock_context_for_list):
        """'k' key moves to previous item (toward lower numbers = older)."""
        ctx = mock_context_for_list
        ctx._state["current_index"] = 1
        event = make_event(char="k")

        list_handler(event, ctx)

        assert ctx._state["current_index"] == 0

    def test_comma_jumps_to_top(self, mock_context_for_list):
        """Comma jumps to item 1 (oldest = internal index 0)."""
        ctx = mock_context_for_list
        ctx._state["current_index"] = 2  # At newest
        event = make_event(char=",")

        list_handler(event, ctx)

        assert ctx._state["current_index"] == 0  # Now at item 1

    def test_period_jumps_to_end(self, mock_context_for_list):
        """Period jumps to last item (newest = highest internal index)."""
        ctx = mock_context_for_list
        ctx._state["current_index"] = 0  # At item 1
        event = make_event(char=".")

        list_handler(event, ctx)

        assert ctx._state["current_index"] == 2  # Now at newest

    def test_enter_reads_current_item(self, mock_context_for_list):
        """Enter reads current item."""
        ctx = mock_context_for_list
        ctx._state["current_index"] = 0  # At item 1
        event = make_event(key=SpecialKey.ENTER)

        list_handler(event, ctx)

        assert "Item 1" in ctx.teller.spoken[0]
        assert "oldest" in ctx.teller.spoken[0]

    def test_delete_removes_item(self, mock_context_for_list):
        """Delete removes current item."""
        ctx = mock_context_for_list
        ctx.store.delete_entry = MagicMock(return_value=True)
        event = make_event(key=SpecialKey.DELETE)

        list_handler(event, ctx)

        ctx.store.delete_entry.assert_called_once_with(3)
        assert len(ctx._state["items"]) == 2
        assert "Deleted" in ctx.teller.spoken[0]

    def test_a_appends_from_clipboard(self, mock_context_for_list, monkeypatch):
        """'a' appends clipboard content to list."""
        monkeypatch.setattr("pyperclip.paste", lambda: "new item")

        ctx = mock_context_for_list
        ctx.store.append_to_list = MagicMock()
        ctx.store.list_items = MagicMock(return_value=[
            {"id": 1, "value": "oldest"},
            {"id": 2, "value": "middle"},
            {"id": 3, "value": "newest"},
            {"id": 4, "value": "new item"},
        ])
        event = make_event(char="a")

        list_handler(event, ctx)

        ctx.store.append_to_list.assert_called_once_with(100, "new item")
        assert "Added" in ctx.teller.spoken[0]

    def test_a_empty_clipboard_announces(self, mock_context_for_list, monkeypatch):
        """'a' with empty clipboard announces error."""
        monkeypatch.setattr("pyperclip.paste", lambda: "")

        ctx = mock_context_for_list
        event = make_event(char="a")

        list_handler(event, ctx)

        assert "empty" in ctx.teller.spoken[0].lower()

    def test_help_shows_commands(self, mock_context_for_list):
        """'?' shows help."""
        ctx = mock_context_for_list
        event = make_event(char="?")

        list_handler(event, ctx)

        assert "add" in ctx.teller.spoken[0].lower()

    def test_ctrl_p_moves_toward_item_1(self, mock_context_for_list):
        """Ctrl+P moves toward item 1 (lower internal index = older)."""
        ctx = mock_context_for_list
        ctx._state["current_index"] = 1
        event = make_ctrl_event("p")

        list_handler(event, ctx)

        assert ctx._state["current_index"] == 0

    def test_ctrl_n_moves_away_from_item_1(self, mock_context_for_list):
        """Ctrl+N moves away from item 1 (higher internal index = newer)."""
        ctx = mock_context_for_list
        ctx._state["current_index"] = 0
        event = make_ctrl_event("n")

        list_handler(event, ctx)

        assert ctx._state["current_index"] == 1

    def test_ctrl_a_enters_all_mode(self, mock_context_for_list):
        """Ctrl+A enters all mode and announces 'All'."""
        ctx = mock_context_for_list
        event = make_ctrl_event("a")

        list_handler(event, ctx)

        assert ctx._state.get("all_mode") is True
        assert "All" in ctx.teller.spoken[0]

    def test_all_mode_c_copies_all_items(self, mock_context_for_list, monkeypatch):
        """In all mode, 'c' copies all items to clipboard."""
        copied = []
        monkeypatch.setattr("pyperclip.copy", lambda x: copied.append(x))

        ctx = mock_context_for_list
        ctx._state["all_mode"] = True  # Already in all mode
        event = make_event(char="c")

        list_handler(event, ctx)

        assert ctx._state.get("all_mode") is False  # Flag cleared
        assert len(copied) == 1
        assert "oldest" in copied[0]
        assert "middle" in copied[0]
        assert "newest" in copied[0]
        assert "Copied 3 items" in ctx.teller.spoken[0]

    def test_all_mode_escape_cancels(self, mock_context_for_list):
        """In all mode, escape cancels but stays in list mode."""
        ctx = mock_context_for_list
        ctx._state["all_mode"] = True
        event = make_event(key=SpecialKey.ESCAPE)

        list_handler(event, ctx)

        assert ctx._state.get("all_mode") is False
        assert "Bulk cancelled" in ctx.teller.spoken[0]
        ctx.back.assert_not_called()  # Stays in list mode

    def test_all_mode_unknown_key_cancels(self, mock_context_for_list):
        """In all mode, unknown key cancels."""
        ctx = mock_context_for_list
        ctx._state["all_mode"] = True
        event = make_event(char="x")

        list_handler(event, ctx)

        assert ctx._state.get("all_mode") is False
        assert "Bulk cancelled" in ctx.teller.spoken[0]

    def test_all_mode_empty_list_announces(self, mock_context_for_list):
        """In all mode with empty list, announces it and clears flag."""
        ctx = mock_context_for_list
        ctx._state["all_mode"] = True
        ctx._state["items"] = []
        event = make_event(char="c")

        list_handler(event, ctx)

        assert ctx._state.get("all_mode") is False  # Flag cleared
        assert "List is empty" in ctx.teller.spoken[0]

    def test_all_mode_b_opens_urls(self, mock_context_for_list, monkeypatch):
        """In all mode, 'b' opens all URLs."""
        opened_urls = []
        monkeypatch.setattr("webbrowser.open", lambda url: opened_urls.append(url))
        monkeypatch.setattr("handlers.quit_app", lambda ctx: None)

        ctx = mock_context_for_list
        ctx._state["all_mode"] = True
        ctx._state["items"] = [
            {"id": 1, "value": "https://example.com"},
            {"id": 2, "value": "https://test.org"},
        ]
        event = make_event(char="b")

        list_handler(event, ctx)

        assert ctx._state.get("all_mode") is False
        assert len(opened_urls) == 2
        assert "Opening 2 items" in ctx.teller.spoken[0]

    def test_all_mode_b_no_urls_announces(self, mock_context_for_list):
        """In all mode, 'b' with no URLs announces it."""
        ctx = mock_context_for_list
        ctx._state["all_mode"] = True
        ctx._state["items"] = [
            {"id": 1, "value": "plain text"},
            {"id": 2, "value": "also not a url"},
        ]
        event = make_event(char="b")

        list_handler(event, ctx)

        assert ctx._state.get("all_mode") is False
        assert "No URLs or files" in ctx.teller.spoken[0]


# =============================================================================
# Read Handler Tests
# =============================================================================

@pytest.fixture
def mock_context_for_read(mock_store, mock_teller):
    """Create context for read mode with mark."""
    ctx = MagicMock(spec=ModeContext)
    ctx.store = mock_store
    ctx.teller = mock_teller
    ctx.back = MagicMock()
    ctx.switch = MagicMock()
    ctx.get_state = MagicMock(return_value={})
    ctx.repeat_count = 1

    # Mock mark
    ctx.mark = MagicMock()
    ctx.mark.buffer_id = 1
    ctx.mark.last_retrieved = {}
    ctx.mark.back = MagicMock(return_value=True)
    ctx.mark.into = MagicMock()

    return ctx


class TestReadHandler:
    """Test read mode handler."""

    def test_backspace_goes_back(self, mock_context_for_read):
        """Backspace navigates back."""
        ctx = mock_context_for_read
        event = make_event(key=SpecialKey.BACKSPACE)

        read_handler(event, ctx)

        ctx.mark.back.assert_called_once()
        assert "Back" in ctx.teller.spoken[0]

    def test_backspace_at_root_announces(self, mock_context_for_read):
        """Backspace at root announces it."""
        ctx = mock_context_for_read
        ctx.mark.back = MagicMock(return_value=False)
        event = make_event(key=SpecialKey.BACKSPACE)

        read_handler(event, ctx)

        assert "root" in ctx.teller.spoken[0].lower()

    def test_delete_no_selection_announces(self, mock_context_for_read):
        """Delete with no selection announces error."""
        ctx = mock_context_for_read
        ctx.mark.last_retrieved = {}
        event = make_event(key=SpecialKey.DELETE)

        read_handler(event, ctx)

        assert "No register" in ctx.teller.spoken[0]

    def test_delete_removes_entry(self, mock_context_for_read):
        """Delete soft-deletes the last retrieved entry."""
        ctx = mock_context_for_read
        ctx.mark.last_retrieved = {"key": "a", "buffer_id": 1, "value": "test"}
        ctx.store.get = MagicMock(return_value={"id": 5, "value": "test", "data_type": "value"})
        ctx.store.delete_entry = MagicMock(return_value=True)
        event = make_event(key=SpecialKey.DELETE)

        read_handler(event, ctx)

        ctx.store.delete_entry.assert_called_once_with(5)
        assert "Deleted" in ctx.teller.spoken[0]

    def test_first_press_reads_value(self, mock_context_for_read):
        """First press of key reads the value."""
        ctx = mock_context_for_read
        ctx.store.get = MagicMock(return_value={"value": "hello world", "data_type": "value"})
        event = make_event(char="a")

        read_handler(event, ctx)

        assert "hello world" in ctx.teller.spoken[0]

    def test_no_data_announces(self, mock_context_for_read):
        """No data at key announces it."""
        ctx = mock_context_for_read
        ctx.store.get = MagicMock(return_value=None)
        event = make_event(char="x")

        read_handler(event, ctx)

        assert "No data" in ctx.teller.spoken[0]

    def test_second_press_copies(self, mock_context_for_read, monkeypatch):
        """Second press copies value."""
        copied = []
        monkeypatch.setattr("pyperclip.copy", lambda x: copied.append(x))
        monkeypatch.setattr("os._exit", lambda x: None)

        ctx = mock_context_for_read
        ctx.repeat_count = 2
        ctx.store.get = MagicMock(return_value={"value": "copy me", "data_type": "value"})
        event = make_event(char="a")

        read_handler(event, ctx)

        assert "copy me" in copied
        assert "Copied" in ctx.teller.spoken[0]

    def test_ctrl_o_switches_to_options(self, mock_context_for_read):
        """Ctrl+O switches to options mode."""
        ctx = mock_context_for_read
        event = make_ctrl_event("o")

        read_handler(event, ctx)

        ctx.switch.assert_called_once_with("options")

    def test_ctrl_j_reads_clipboard(self, mock_context_for_read, monkeypatch):
        """Ctrl+J reads clipboard."""
        monkeypatch.setattr("pyperclip.paste", lambda: "clipboard content")

        ctx = mock_context_for_read
        event = make_ctrl_event("j")

        read_handler(event, ctx)

        assert "clipboard content" in ctx.teller.spoken[0]

    def test_ctrl_c_copies_last_value(self, mock_context_for_read, monkeypatch):
        """Ctrl+C copies last retrieved value."""
        copied = []
        monkeypatch.setattr("pyperclip.copy", lambda x: copied.append(x))
        monkeypatch.setattr("os._exit", lambda x: None)

        ctx = mock_context_for_read
        ctx.mark.last_retrieved = {"key": "a", "buffer_id": 1, "value": "saved value"}
        event = make_ctrl_event("c")

        read_handler(event, ctx)

        assert "saved value" in copied

    def test_ctrl_y_writes_clipboard(self, mock_context_for_read, monkeypatch):
        """Ctrl+Y writes clipboard to last key."""
        monkeypatch.setattr("pyperclip.paste", lambda: "pasted")
        monkeypatch.setattr("os._exit", lambda x: None)

        ctx = mock_context_for_read
        ctx.mark.last_retrieved = {"key": "a", "buffer_id": 1, "value": None}
        event = make_ctrl_event("y")

        read_handler(event, ctx)

        ctx.store.set.assert_called_once()
        assert "Wrote" in ctx.teller.spoken[0]

    def test_buffer_entry_calls_into(self, mock_context_for_read):
        """Pressing key that is a buffer enters it."""
        ctx = mock_context_for_read
        ctx.store.get = MagicMock(return_value={"id": 10, "value": "mybuffer", "data_type": "buffer"})
        event = make_event(char="b")

        read_handler(event, ctx)

        ctx.mark.into.assert_called_once_with(10)
        assert "Entering" in ctx.teller.spoken[0]

    def test_list_first_press_announces(self, mock_context_for_read):
        """First press on list announces info."""
        ctx = mock_context_for_read
        ctx.store.get = MagicMock(return_value={"id": 20, "value": None, "data_type": "list"})
        ctx.store.list_items = MagicMock(return_value=[{"value": "item1"}, {"value": "item2"}])
        event = make_event(char="l")

        read_handler(event, ctx)

        assert "List with 2 items" in ctx.teller.spoken[0]

    def test_list_second_press_enters_mode(self, mock_context_for_read):
        """Second press on list enters list mode."""
        ctx = mock_context_for_read
        ctx.repeat_count = 2
        ctx.store.get = MagicMock(return_value={"id": 20, "value": None, "data_type": "list"})
        ctx.store.list_items = MagicMock(return_value=[{"value": "item1"}])
        event = make_event(char="l")

        read_handler(event, ctx)

        ctx.switch.assert_called_with(
            "list",
            setup={
                "list_id": 20,
                "key": "l",
                "buffer_id": 1,
                "items": [{"value": "item1"}],
                "current_index": 0,
            },
        )

    def test_non_alnum_ignored(self, mock_context_for_read):
        """Non-alphanumeric keys are ignored."""
        ctx = mock_context_for_read
        event = make_event(char="!")

        read_handler(event, ctx)

        ctx.store.get.assert_not_called()

    def test_ctrl_g_creates_buffer(self, mock_context_for_read):
        """Ctrl+G creates buffer at last key."""
        ctx = mock_context_for_read
        ctx.mark.last_retrieved = {"key": "n", "buffer_id": 1, "value": None}
        ctx.store.get = MagicMock(return_value=None)  # No existing entry
        ctx.store.create_buffer = MagicMock(return_value=99)
        event = make_ctrl_event("g")

        read_handler(event, ctx)

        ctx.store.create_buffer.assert_called_once()
        ctx.mark.into.assert_called_once_with(99)
        assert "Created buffer" in ctx.teller.spoken[0]

    def test_auto_action_opens_url(self, mock_context_for_read, monkeypatch):
        """Auto action opens URLs."""
        opened = []
        monkeypatch.setattr("webbrowser.open", lambda x: opened.append(x))
        monkeypatch.setattr("os._exit", lambda x: None)

        ctx = mock_context_for_read
        ctx.repeat_count = 2
        ctx.store._config["default_action"] = "auto"
        ctx.store.get = MagicMock(return_value={"value": "https://example.com", "data_type": "value"})
        event = make_event(char="u")

        read_handler(event, ctx)

        assert "https://example.com" in opened
