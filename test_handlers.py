"""
Tests for mode handlers.
"""

import pytest
from unittest.mock import MagicMock, call

from listener import KeyEvent, SpecialKey, EventType
from mode import ModeContext
from handlers import options_handler, status


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
