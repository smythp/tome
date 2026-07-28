"""
Tests for Listener RSP.

Tests KeyEvent construction/validation, MockListener, NoListener, and
PynputListener without starting a live desktop listener.
"""

from dataclasses import FrozenInstanceError

import pytest

from listener import (
    EventType,
    KeyEvent,
    Modifier,
    NoListener,
    PynputListener,
    SpecialKey,
)


class FakeKey:
    """Minimal stand-in for pynput keyboard keys."""

    def __init__(self, name=None, char=None, has_char=True):
        self.name = name
        if has_char:
            self.char = char

    def __str__(self):
        if self.name:
            return f"Key.{self.name}"
        return "Key.unknown"


class FakeKeyboard:
    """Fake pynput.keyboard module."""

    last_listener = None

    class Listener:
        def __init__(self, on_press, on_release, suppress):
            self.on_press = on_press
            self.on_release = on_release
            self.suppress = suppress
            self.started = False
            self.stopped = False
            FakeKeyboard.last_listener = self

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True


@pytest.fixture
def fake_pynput(monkeypatch):
    """Patch PynputListener to use a fake keyboard module."""
    FakeKeyboard.last_listener = None
    monkeypatch.setattr(PynputListener, "_load_keyboard", lambda self: FakeKeyboard)
    return FakeKeyboard


class TestKeyEventConstruction:
    """Test KeyEvent creation and validation."""

    def test_char_event_valid(self):
        event = KeyEvent(
            char="a",
            key=None,
            modifiers=frozenset(),
            event_type=EventType.PRESS,
        )
        assert event.char == "a"
        assert event.key is None

    def test_special_key_event_valid(self):
        event = KeyEvent(
            char=None,
            key=SpecialKey.ESCAPE,
            modifiers=frozenset(),
            event_type=EventType.PRESS,
        )
        assert event.char is None
        assert event.key == SpecialKey.ESCAPE

    def test_char_with_modifiers(self):
        event = KeyEvent(
            char="c",
            key=None,
            modifiers=frozenset({Modifier.CTRL}),
            event_type=EventType.PRESS,
        )
        assert event.char == "c"
        assert Modifier.CTRL in event.modifiers

    def test_multiple_modifiers(self):
        mods = frozenset({Modifier.CTRL, Modifier.SHIFT, Modifier.ALT})
        event = KeyEvent(
            char="a",
            key=None,
            modifiers=mods,
            event_type=EventType.PRESS,
        )
        assert event.modifiers == mods

    def test_release_event_type(self):
        event = KeyEvent(
            char="a",
            key=None,
            modifiers=frozenset(),
            event_type=EventType.RELEASE,
        )
        assert event.event_type == EventType.RELEASE

    def test_reject_both_char_and_key(self):
        with pytest.raises(ValueError, match="exactly one"):
            KeyEvent(
                char="a",
                key=SpecialKey.ESCAPE,
                modifiers=frozenset(),
                event_type=EventType.PRESS,
            )

    def test_reject_neither_char_nor_key(self):
        with pytest.raises(ValueError, match="exactly one"):
            KeyEvent(
                char=None,
                key=None,
                modifiers=frozenset(),
                event_type=EventType.PRESS,
            )

    def test_reject_non_enum_key(self):
        with pytest.raises(TypeError, match="SpecialKey enum"):
            KeyEvent(
                char=None,
                key="escape",
                modifiers=frozenset(),
                event_type=EventType.PRESS,
            )

    def test_frozen_immutable(self):
        event = KeyEvent(
            char="a",
            key=None,
            modifiers=frozenset(),
            event_type=EventType.PRESS,
        )
        with pytest.raises(FrozenInstanceError):
            event.char = "b"

    def test_equality_and_hashable(self):
        event1 = KeyEvent(
            char="a",
            key=None,
            modifiers=frozenset({Modifier.CTRL}),
            event_type=EventType.PRESS,
        )
        event2 = KeyEvent(
            char="a",
            key=None,
            modifiers=frozenset({Modifier.CTRL}),
            event_type=EventType.PRESS,
        )
        assert event1 == event2
        assert {event1} == {event2}


class TestKeyEventEdgeCases:
    """Test edge cases for character values."""

    @pytest.mark.parametrize("char", [" ", "e", "\n"])
    def test_single_char_values(self, char):
        event = KeyEvent(
            char=char,
            key=None,
            modifiers=frozenset(),
            event_type=EventType.PRESS,
        )
        assert event.char == char

    def test_empty_string_char_rejected(self):
        with pytest.raises(ValueError, match="exactly one character"):
            KeyEvent(
                char="",
                key=None,
                modifiers=frozenset(),
                event_type=EventType.PRESS,
            )

    def test_multi_char_string_rejected(self):
        with pytest.raises(ValueError, match="exactly one character"):
            KeyEvent(
                char="ab",
                key=None,
                modifiers=frozenset(),
                event_type=EventType.PRESS,
            )


class TestAllSpecialKeys:
    """Ensure all SpecialKey enum values work."""

    @pytest.mark.parametrize("special_key", list(SpecialKey))
    def test_all_special_keys_valid(self, special_key):
        event = KeyEvent(
            char=None,
            key=special_key,
            modifiers=frozenset(),
            event_type=EventType.PRESS,
        )
        assert event.key == special_key


class TestMockListener:
    """Tests for MockListener."""

    def test_mock_listener_import(self):
        from listener import MockListener
        assert MockListener is not None

    def test_inject_calls_callback(self):
        from listener import MockListener

        received = []
        listener = MockListener()
        listener.start(lambda event: received.append(event))

        event = KeyEvent(char="a", key=None, modifiers=frozenset(), event_type=EventType.PRESS)
        listener.inject(event)

        assert received == [event]

    def test_inject_multiple_events_in_order(self):
        from listener import MockListener

        received = []
        listener = MockListener()
        listener.start(lambda event: received.append(event))

        events = [
            KeyEvent(char="a", key=None, modifiers=frozenset(), event_type=EventType.PRESS),
            KeyEvent(char="b", key=None, modifiers=frozenset(), event_type=EventType.PRESS),
            KeyEvent(char="c", key=None, modifiers=frozenset(), event_type=EventType.PRESS),
        ]
        for event in events:
            listener.inject(event)

        assert received == events

    def test_stop_then_inject_raises(self):
        from listener import MockListener

        listener = MockListener()
        listener.start(lambda event: None)
        listener.stop()

        event = KeyEvent(char="a", key=None, modifiers=frozenset(), event_type=EventType.PRESS)
        with pytest.raises(RuntimeError, match="not started"):
            listener.inject(event)

    def test_inject_before_start_raises(self):
        from listener import MockListener

        listener = MockListener()
        event = KeyEvent(char="a", key=None, modifiers=frozenset(), event_type=EventType.PRESS)

        with pytest.raises(RuntimeError, match="not started"):
            listener.inject(event)

    def test_start_twice_raises(self):
        from listener import MockListener

        listener = MockListener()
        listener.start(lambda event: None)

        with pytest.raises(RuntimeError, match="already started"):
            listener.start(lambda event: None)

    def test_stop_before_start_is_noop(self):
        from listener import MockListener

        MockListener().stop()

    def test_restart_after_stop(self):
        from listener import MockListener

        received = []
        listener = MockListener()
        listener.start(lambda event: received.append(event))
        listener.stop()
        listener.start(lambda event: received.append(event))

        event = KeyEvent(char="a", key=None, modifiers=frozenset(), event_type=EventType.PRESS)
        listener.inject(event)

        assert received == [event]


class TestNoListener:
    """Tests for explicit no-listener harness."""

    def test_no_listener_start_stop_are_noops(self):
        listener = NoListener()
        listener.start(lambda event: None)
        listener.stop()
        listener.stop()


class TestPynputListener:
    """Tests for PynputListener using a fake backend."""

    def test_start_uses_suppress_true(self, fake_pynput):
        listener = PynputListener()
        listener.start(lambda event: None)

        assert fake_pynput.last_listener.started is True
        assert fake_pynput.last_listener.suppress is True

    def test_implements_protocol(self):
        from listener import Listener

        listener = PynputListener()
        assert hasattr(listener, "start")
        assert hasattr(listener, "stop")
        assert callable(listener.start)
        assert callable(listener.stop)

    def test_start_twice_raises(self, fake_pynput):
        listener = PynputListener()
        listener.start(lambda event: None)

        with pytest.raises(RuntimeError, match="already started"):
            listener.start(lambda event: None)

    def test_stop_before_start_is_noop(self):
        PynputListener().stop()

    def test_stop_stops_backend(self, fake_pynput):
        listener = PynputListener()
        listener.start(lambda event: None)
        backend_listener = fake_pynput.last_listener

        listener.stop()

        assert backend_listener.stopped is True


class TestPynputListenerModifierTracking:
    """Test modifier key tracking in PynputListener."""

    @pytest.mark.parametrize(
        ("key_name", "modifier"),
        [
            ("shift", Modifier.SHIFT),
            ("shift_r", Modifier.SHIFT),
            ("ctrl", Modifier.CTRL),
            ("ctrl_r", Modifier.CTRL),
            ("alt", Modifier.ALT),
            ("alt_r", Modifier.ALT),
        ],
    )
    def test_modifier_tracked_and_released(self, key_name, modifier):
        listener = PynputListener()
        key = FakeKey(name=key_name, has_char=False)

        listener._on_press(key)
        assert modifier in listener._modifiers

        listener._on_release(key)
        assert modifier not in listener._modifiers

    def test_multiple_modifiers(self):
        listener = PynputListener()
        listener._on_press(FakeKey(name="ctrl", has_char=False))
        listener._on_press(FakeKey(name="shift", has_char=False))
        listener._on_press(FakeKey(name="alt", has_char=False))

        assert listener._modifiers == {Modifier.CTRL, Modifier.SHIFT, Modifier.ALT}


class TestPynputListenerKeyMapping:
    """Test key normalization and mapping."""

    def test_char_key_normalized(self):
        received = []
        listener = PynputListener()
        listener._callback = received.append

        listener._on_press(FakeKey(char="x"))

        assert len(received) == 1
        assert received[0].char == "x"
        assert received[0].key is None

    @pytest.mark.parametrize(
        ("key_name", "expected_special"),
        [
            ("esc", SpecialKey.ESCAPE),
            ("backspace", SpecialKey.BACKSPACE),
            ("delete", SpecialKey.DELETE),
            ("enter", SpecialKey.ENTER),
            ("tab", SpecialKey.TAB),
            ("up", SpecialKey.UP),
            ("down", SpecialKey.DOWN),
            ("left", SpecialKey.LEFT),
            ("right", SpecialKey.RIGHT),
        ],
    )
    def test_special_keys_mapped(self, key_name, expected_special):
        received = []
        listener = PynputListener()
        listener._callback = received.append

        listener._on_press(FakeKey(name=key_name, has_char=False))

        assert len(received) == 1
        assert received[0].key == expected_special

    def test_key_without_char_attribute(self):
        received = []
        listener = PynputListener()
        listener._callback = received.append

        listener._on_press(FakeKey(name="unknown", has_char=False))

        assert received == []

    def test_unknown_special_key_skipped(self):
        received = []
        listener = PynputListener()
        listener._callback = received.append

        listener._on_press(FakeKey(name="f1", has_char=False))

        assert received == []


class TestPynputListenerEventTypes:
    """Test press/release event emission."""

    def test_press_emits_press_event(self):
        received = []
        listener = PynputListener()
        listener._callback = received.append

        listener._on_press(FakeKey(char="a"))

        assert received[0].event_type == EventType.PRESS

    def test_release_emits_release_event(self):
        received = []
        listener = PynputListener()
        listener._callback = received.append

        listener._on_release(FakeKey(char="a"))

        assert received[0].event_type == EventType.RELEASE


class TestPynputListenerEdgeCases:
    """Edge cases for PynputListener."""

    def test_release_without_press(self):
        listener = PynputListener()
        listener._on_release(FakeKey(name="ctrl", has_char=False))

    def test_callback_exception_continues(self):
        call_count = [0]

        def bad_callback(event):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("callback error")

        listener = PynputListener()
        listener._callback = bad_callback

        listener._on_press(FakeKey(char="a"))
        listener._on_press(FakeKey(char="a"))

        assert call_count[0] == 2
