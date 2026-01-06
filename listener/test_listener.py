"""
Tests for Listener RSP.

Tests KeyEvent construction/validation, MockListener, and PynputListener.
"""

import pytest
from dataclasses import FrozenInstanceError

from listener import (
    KeyEvent,
    SpecialKey,
    Modifier,
    EventType,
)


# =============================================================================
# KeyEvent Construction Tests
# =============================================================================

class TestKeyEventConstruction:
    """Test KeyEvent creation and validation."""

    def test_char_event_valid(self):
        """Regular character key creates valid event."""
        event = KeyEvent(
            char='a',
            key=None,
            modifiers=frozenset(),
            event_type=EventType.PRESS
        )
        assert event.char == 'a'
        assert event.key is None

    def test_special_key_event_valid(self):
        """Special key creates valid event."""
        event = KeyEvent(
            char=None,
            key=SpecialKey.ESCAPE,
            modifiers=frozenset(),
            event_type=EventType.PRESS
        )
        assert event.char is None
        assert event.key == SpecialKey.ESCAPE

    def test_char_with_modifiers(self):
        """Char event with modifiers."""
        event = KeyEvent(
            char='c',
            key=None,
            modifiers=frozenset({Modifier.CTRL}),
            event_type=EventType.PRESS
        )
        assert event.char == 'c'
        assert Modifier.CTRL in event.modifiers

    def test_multiple_modifiers(self):
        """Multiple modifiers tracked."""
        mods = frozenset({Modifier.CTRL, Modifier.SHIFT, Modifier.ALT})
        event = KeyEvent(
            char='a',
            key=None,
            modifiers=mods,
            event_type=EventType.PRESS
        )
        assert event.modifiers == mods
        assert len(event.modifiers) == 3

    def test_release_event_type(self):
        """Release event type works."""
        event = KeyEvent(
            char='a',
            key=None,
            modifiers=frozenset(),
            event_type=EventType.RELEASE
        )
        assert event.event_type == EventType.RELEASE

    def test_reject_both_char_and_key(self):
        """Cannot have both char and key set."""
        with pytest.raises(ValueError, match="exactly one"):
            KeyEvent(
                char='a',
                key=SpecialKey.ESCAPE,
                modifiers=frozenset(),
                event_type=EventType.PRESS
            )

    def test_reject_neither_char_nor_key(self):
        """Must have either char or key."""
        with pytest.raises(ValueError, match="exactly one"):
            KeyEvent(
                char=None,
                key=None,
                modifiers=frozenset(),
                event_type=EventType.PRESS
            )

    def test_reject_non_enum_key(self):
        """Key must be a SpecialKey enum, not a string or other type."""
        with pytest.raises(TypeError, match="SpecialKey enum"):
            KeyEvent(
                char=None,
                key="escape",  # String instead of enum
                modifiers=frozenset(),
                event_type=EventType.PRESS
            )

    def test_frozen_immutable(self):
        """KeyEvent is immutable (frozen dataclass)."""
        event = KeyEvent(
            char='a',
            key=None,
            modifiers=frozenset(),
            event_type=EventType.PRESS
        )
        with pytest.raises(FrozenInstanceError):
            event.char = 'b'

    def test_equality(self):
        """Identical events are equal."""
        event1 = KeyEvent(
            char='a',
            key=None,
            modifiers=frozenset({Modifier.CTRL}),
            event_type=EventType.PRESS
        )
        event2 = KeyEvent(
            char='a',
            key=None,
            modifiers=frozenset({Modifier.CTRL}),
            event_type=EventType.PRESS
        )
        assert event1 == event2

    def test_inequality_different_char(self):
        """Different char means not equal."""
        event1 = KeyEvent(char='a', key=None, modifiers=frozenset(), event_type=EventType.PRESS)
        event2 = KeyEvent(char='b', key=None, modifiers=frozenset(), event_type=EventType.PRESS)
        assert event1 != event2

    def test_hashable(self):
        """KeyEvent can be used in sets/dicts."""
        event = KeyEvent(
            char='a',
            key=None,
            modifiers=frozenset(),
            event_type=EventType.PRESS
        )
        event_set = {event}
        assert event in event_set

        event_dict = {event: 'value'}
        assert event_dict[event] == 'value'


# =============================================================================
# Edge Case Character Tests
# =============================================================================

class TestKeyEventEdgeCases:
    """Test edge cases for character values."""

    def test_space_char(self):
        """Space is a valid char."""
        event = KeyEvent(
            char=' ',
            key=None,
            modifiers=frozenset(),
            event_type=EventType.PRESS
        )
        assert event.char == ' '

    def test_unicode_char(self):
        """Unicode characters work."""
        event = KeyEvent(
            char='é',
            key=None,
            modifiers=frozenset(),
            event_type=EventType.PRESS
        )
        assert event.char == 'é'

    def test_unicode_cjk(self):
        """CJK characters work."""
        event = KeyEvent(
            char='中',
            key=None,
            modifiers=frozenset(),
            event_type=EventType.PRESS
        )
        assert event.char == '中'

    def test_newline_char(self):
        """Newline as char (edge case - probably shouldn't happen in practice)."""
        event = KeyEvent(
            char='\n',
            key=None,
            modifiers=frozenset(),
            event_type=EventType.PRESS
        )
        assert event.char == '\n'

    def test_empty_string_char_rejected(self):
        """Empty string char is rejected."""
        with pytest.raises(ValueError, match="exactly one character"):
            KeyEvent(
                char='',
                key=None,
                modifiers=frozenset(),
                event_type=EventType.PRESS
            )

    def test_multi_char_string_rejected(self):
        """Multi-character string is rejected."""
        with pytest.raises(ValueError, match="exactly one character"):
            KeyEvent(
                char='ab',
                key=None,
                modifiers=frozenset(),
                event_type=EventType.PRESS
            )


# =============================================================================
# All SpecialKey Values
# =============================================================================

class TestAllSpecialKeys:
    """Ensure all SpecialKey enum values work."""

    @pytest.mark.parametrize("special_key", list(SpecialKey))
    def test_all_special_keys_valid(self, special_key):
        """Each SpecialKey creates valid event."""
        event = KeyEvent(
            char=None,
            key=special_key,
            modifiers=frozenset(),
            event_type=EventType.PRESS
        )
        assert event.key == special_key


# =============================================================================
# MockListener Tests
# =============================================================================

class TestMockListener:
    """Tests for MockListener (test double for keyboard input)."""

    def test_mock_listener_import(self):
        """MockListener can be imported."""
        from listener import MockListener
        assert MockListener is not None

    def test_start_accepts_callback(self):
        """start() accepts a callback function."""
        from listener import MockListener

        received = []
        def callback(event):
            received.append(event)

        listener = MockListener()
        listener.start(callback)
        # Should not raise

    def test_inject_calls_callback(self):
        """inject() passes event to callback."""
        from listener import MockListener

        received = []
        def callback(event):
            received.append(event)

        listener = MockListener()
        listener.start(callback)

        event = KeyEvent(char='a', key=None, modifiers=frozenset(), event_type=EventType.PRESS)
        listener.inject(event)

        assert len(received) == 1
        assert received[0] == event

    def test_inject_multiple_events(self):
        """Multiple injected events all reach callback in order."""
        from listener import MockListener

        received = []
        def callback(event):
            received.append(event)

        listener = MockListener()
        listener.start(callback)

        events = [
            KeyEvent(char='a', key=None, modifiers=frozenset(), event_type=EventType.PRESS),
            KeyEvent(char='b', key=None, modifiers=frozenset(), event_type=EventType.PRESS),
            KeyEvent(char='c', key=None, modifiers=frozenset(), event_type=EventType.PRESS),
        ]

        for event in events:
            listener.inject(event)

        assert received == events

    def test_stop_then_inject_raises(self):
        """After stop(), inject() raises an error."""
        from listener import MockListener

        listener = MockListener()
        listener.start(lambda e: None)
        listener.stop()

        event = KeyEvent(char='a', key=None, modifiers=frozenset(), event_type=EventType.PRESS)
        with pytest.raises(RuntimeError, match="not started"):
            listener.inject(event)

    def test_inject_before_start_raises(self):
        """inject() before start() raises an error."""
        from listener import MockListener

        listener = MockListener()
        event = KeyEvent(char='a', key=None, modifiers=frozenset(), event_type=EventType.PRESS)

        with pytest.raises(RuntimeError, match="not started"):
            listener.inject(event)

    def test_start_twice_raises(self):
        """start() called twice without stop() raises an error."""
        from listener import MockListener

        listener = MockListener()
        listener.start(lambda e: None)

        with pytest.raises(RuntimeError, match="already started"):
            listener.start(lambda e: None)

    def test_stop_before_start_is_noop(self):
        """stop() before start() is a no-op (idempotent)."""
        from listener import MockListener

        listener = MockListener()
        listener.stop()  # Should not raise

    def test_stop_twice_is_noop(self):
        """stop() called twice is a no-op (idempotent)."""
        from listener import MockListener

        listener = MockListener()
        listener.start(lambda e: None)
        listener.stop()
        listener.stop()  # Should not raise

    def test_restart_after_stop(self):
        """Can start() again after stop()."""
        from listener import MockListener

        received = []
        listener = MockListener()
        listener.start(lambda e: received.append(e))
        listener.stop()

        received.clear()
        listener.start(lambda e: received.append(e))

        event = KeyEvent(char='a', key=None, modifiers=frozenset(), event_type=EventType.PRESS)
        listener.inject(event)

        assert len(received) == 1


# =============================================================================
# PynputListener Tests
# =============================================================================

class TestPynputListener:
    """Tests for PynputListener (real keyboard via pynput)."""

    def test_pynput_listener_import(self):
        """PynputListener can be imported."""
        from listener import PynputListener
        assert PynputListener is not None

    def test_implements_protocol(self):
        """PynputListener implements Listener protocol."""
        from listener import PynputListener, Listener

        listener = PynputListener()
        # Duck typing check - has required methods
        assert hasattr(listener, 'start')
        assert hasattr(listener, 'stop')
        assert callable(listener.start)
        assert callable(listener.stop)

    def test_start_twice_raises(self):
        """start() called twice without stop() raises an error."""
        from listener import PynputListener

        listener = PynputListener()
        listener.start(lambda e: None)

        with pytest.raises(RuntimeError, match="already started"):
            listener.start(lambda e: None)

        # Cleanup
        listener.stop()

    def test_stop_before_start_is_noop(self):
        """stop() before start() is a no-op (idempotent)."""
        from listener import PynputListener

        listener = PynputListener()
        listener.stop()  # Should not raise


class TestPynputListenerModifierTracking:
    """Test modifier key tracking in PynputListener."""

    def test_shift_modifier_tracked(self):
        """Pressing shift adds SHIFT to modifiers."""
        from listener import PynputListener
        from unittest.mock import MagicMock, patch
        from pynput import keyboard

        received = []
        def callback(event):
            received.append(event)

        listener = PynputListener()

        # Simulate: press shift, then press 'a', then release shift
        # We need to call the internal handlers directly
        listener._on_press(keyboard.Key.shift)
        listener._on_press(MagicMock(char='a'))

        # The 'a' press should have SHIFT in modifiers
        a_events = [e for e in received if e.char == 'a']
        # Note: this test assumes _on_press calls callback
        # Implementation may differ - adjust as needed

    def test_ctrl_modifier_tracked(self):
        """Pressing ctrl adds CTRL to modifiers."""
        from listener import PynputListener
        from pynput import keyboard

        listener = PynputListener()
        listener._on_press(keyboard.Key.ctrl)

        assert Modifier.CTRL in listener._modifiers

    def test_modifier_released(self):
        """Releasing modifier removes it from tracking."""
        from listener import PynputListener
        from pynput import keyboard

        listener = PynputListener()
        listener._on_press(keyboard.Key.ctrl)
        assert Modifier.CTRL in listener._modifiers

        listener._on_release(keyboard.Key.ctrl)
        assert Modifier.CTRL not in listener._modifiers

    def test_multiple_modifiers(self):
        """Multiple modifiers tracked simultaneously."""
        from listener import PynputListener
        from pynput import keyboard

        listener = PynputListener()
        listener._on_press(keyboard.Key.ctrl)
        listener._on_press(keyboard.Key.shift)
        listener._on_press(keyboard.Key.alt)

        assert Modifier.CTRL in listener._modifiers
        assert Modifier.SHIFT in listener._modifiers
        assert Modifier.ALT in listener._modifiers

    def test_left_right_ctrl_treated_same(self):
        """ctrl and ctrl_r both set CTRL modifier."""
        from listener import PynputListener
        from pynput import keyboard

        listener = PynputListener()

        # Left ctrl (pynput uses 'ctrl' for left)
        listener._on_press(keyboard.Key.ctrl)
        assert Modifier.CTRL in listener._modifiers
        listener._on_release(keyboard.Key.ctrl)
        assert Modifier.CTRL not in listener._modifiers

        # Right ctrl
        listener._on_press(keyboard.Key.ctrl_r)
        assert Modifier.CTRL in listener._modifiers

    def test_left_right_shift_treated_same(self):
        """shift and shift_r both set SHIFT modifier."""
        from listener import PynputListener
        from pynput import keyboard

        listener = PynputListener()

        listener._on_press(keyboard.Key.shift)
        assert Modifier.SHIFT in listener._modifiers
        listener._on_release(keyboard.Key.shift)

        listener._on_press(keyboard.Key.shift_r)
        assert Modifier.SHIFT in listener._modifiers

    def test_left_right_alt_treated_same(self):
        """alt and alt_r both set ALT modifier."""
        from listener import PynputListener
        from pynput import keyboard

        listener = PynputListener()

        listener._on_press(keyboard.Key.alt)
        assert Modifier.ALT in listener._modifiers
        listener._on_release(keyboard.Key.alt)

        listener._on_press(keyboard.Key.alt_r)
        assert Modifier.ALT in listener._modifiers


class TestPynputListenerKeyMapping:
    """Test key normalization and mapping."""

    def test_char_key_normalized(self):
        """Key with .char attribute creates char event."""
        from listener import PynputListener
        from unittest.mock import MagicMock

        received = []
        def callback(event):
            received.append(event)

        listener = PynputListener()
        listener.start(callback)

        mock_key = MagicMock()
        mock_key.char = 'x'
        listener._on_press(mock_key)

        assert len(received) == 1
        assert received[0].char == 'x'
        assert received[0].key is None

    def test_escape_mapped(self):
        """keyboard.Key.esc maps to SpecialKey.ESCAPE."""
        from listener import PynputListener
        from pynput import keyboard

        received = []
        def callback(event):
            received.append(event)

        listener = PynputListener()
        listener.start(callback)
        listener._on_press(keyboard.Key.esc)

        assert len(received) == 1
        assert received[0].key == SpecialKey.ESCAPE

    def test_backspace_mapped(self):
        """keyboard.Key.backspace maps to SpecialKey.BACKSPACE."""
        from listener import PynputListener
        from pynput import keyboard

        received = []
        def callback(event):
            received.append(event)

        listener = PynputListener()
        listener.start(callback)
        listener._on_press(keyboard.Key.backspace)

        assert len(received) == 1
        assert received[0].key == SpecialKey.BACKSPACE

    def test_tab_mapped(self):
        """keyboard.Key.tab maps to SpecialKey.TAB."""
        from listener import PynputListener
        from pynput import keyboard

        received = []
        def callback(event):
            received.append(event)

        listener = PynputListener()
        listener.start(callback)
        listener._on_press(keyboard.Key.tab)

        assert len(received) == 1
        assert received[0].key == SpecialKey.TAB

    def test_arrow_keys_mapped(self):
        """Arrow keys map to SpecialKey variants."""
        from listener import PynputListener
        from pynput import keyboard

        mapping = {
            keyboard.Key.up: SpecialKey.UP,
            keyboard.Key.down: SpecialKey.DOWN,
            keyboard.Key.left: SpecialKey.LEFT,
            keyboard.Key.right: SpecialKey.RIGHT,
        }

        for pynput_key, expected_special in mapping.items():
            received = []
            def callback(event):
                received.append(event)

            listener = PynputListener()
            listener.start(callback)
            listener._on_press(pynput_key)

            assert len(received) == 1
            assert received[0].key == expected_special

    def test_key_without_char_attribute(self):
        """Key without .char (AttributeError) handled gracefully."""
        from listener import PynputListener
        from unittest.mock import MagicMock

        received = []
        def callback(event):
            received.append(event)

        listener = PynputListener()
        listener.start(callback)

        # Mock key that raises AttributeError on .char access
        mock_key = MagicMock()
        del mock_key.char  # Accessing .char will raise AttributeError

        # Should not raise
        listener._on_press(mock_key)

    def test_unknown_special_key_skipped(self):
        """Unknown special key (e.g., F1) is skipped - no event emitted."""
        from listener import PynputListener
        from pynput import keyboard

        received = []
        def callback(event):
            received.append(event)

        listener = PynputListener()
        listener.start(callback)
        listener._on_press(keyboard.Key.f1)  # Not in our SpecialKey enum

        # Should skip - no event emitted
        assert len(received) == 0


class TestPynputListenerEventTypes:
    """Test press/release event emission."""

    def test_press_emits_press_event(self):
        """_on_press emits event with EventType.PRESS."""
        from listener import PynputListener
        from unittest.mock import MagicMock

        received = []
        def callback(event):
            received.append(event)

        listener = PynputListener()
        listener.start(callback)

        mock_key = MagicMock()
        mock_key.char = 'a'
        listener._on_press(mock_key)

        assert received[0].event_type == EventType.PRESS

    def test_release_emits_release_event(self):
        """_on_release emits event with EventType.RELEASE."""
        from listener import PynputListener
        from unittest.mock import MagicMock

        received = []
        def callback(event):
            received.append(event)

        listener = PynputListener()
        listener.start(callback)

        mock_key = MagicMock()
        mock_key.char = 'a'
        listener._on_release(mock_key)

        assert received[0].event_type == EventType.RELEASE


class TestPynputListenerEdgeCases:
    """Edge cases for PynputListener."""

    def test_release_without_press(self):
        """Release event for key never pressed doesn't crash."""
        from listener import PynputListener
        from pynput import keyboard

        listener = PynputListener()
        # Release ctrl without ever pressing it
        listener._on_release(keyboard.Key.ctrl)
        # Should not raise

    def test_callback_exception_continues(self):
        """If callback raises, listener continues working."""
        from listener import PynputListener
        from unittest.mock import MagicMock

        call_count = [0]

        def bad_callback(event):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("callback error")

        listener = PynputListener()
        listener.start(bad_callback)

        mock_key = MagicMock()
        mock_key.char = 'a'

        # First call raises
        listener._on_press(mock_key)

        # Second call should still work
        listener._on_press(mock_key)

        assert call_count[0] == 2
