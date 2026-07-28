"""Regression tests for explicit mode-entry state and Mark paths."""

from listener import EventType, KeyEvent, Modifier
from mark import Mark
from mode import Mode
from store import Store
from tome import App
from listener import NoListener
from handlers import history_handler, list_handler, read_handler


class RecordingTeller:
    def __init__(self):
        self.spoken = []
        self.stopped = False

    def speak(self, text, **kwargs):
        self.spoken.append(text)

    def stop(self):
        self.stopped = True


def char_event(char, *, ctrl=False):
    modifiers = frozenset({Modifier.CTRL}) if ctrl else frozenset()
    return KeyEvent(
        char=char,
        key=None,
        modifiers=modifiers,
        event_type=EventType.PRESS,
    )


def make_mode(tmp_path):
    store = Store(tmp_path / "lore.db")
    teller = RecordingTeller()
    mark = Mark(store)
    mode = Mode(teller, store, mark)
    mode.register("read", read_handler, message="Read")
    mode.register("history", history_handler, message="History")
    mode.register("list", list_handler, message="List")
    mode.switch("read", silent=True)
    return mode, store, mark, teller


def test_switch_setup_replaces_destination_state_before_on_enter(tmp_path):
    store = Store(tmp_path / "lore.db")
    teller = RecordingTeller()
    seen_on_enter = []
    mode = Mode(teller, store)

    mode.register("read", lambda _event, _ctx: None)
    mode.register(
        "history",
        lambda _event, _ctx: None,
        on_enter=lambda: seen_on_enter.append(dict(mode._state["history"])),
    )
    mode._state["history"].update({"stale": True})
    mode.switch("read", silent=True)

    mode.switch("history", silent=True, setup={"entries": ["entry"], "key": "h"})

    assert mode._state["history"] == {"entries": ["entry"], "key": "h"}
    assert seen_on_enter == [{"entries": ["entry"], "key": "h"}]


def test_history_entry_uses_explicit_switch_setup_not_last_retrieved(tmp_path):
    mode, store, mark, _teller = make_mode(tmp_path)
    store.set("h", "first")
    store.set("h", "second")

    mode.handle(char_event("h"))
    last_before = dict(mark.last_retrieved)

    mode.handle(char_event("h", ctrl=True))

    assert mode.current == "history"
    assert mark.last_retrieved == last_before
    assert "_history_setup" not in mark.last_retrieved
    assert mode._state["history"]["key"] == "h"
    assert mode._state["history"]["buffer_id"] == 1
    assert mode._state["history"]["current_index"] == 0
    assert [entry["value"] for entry in mode._state["history"]["entries"]] == [
        "second",
        "first",
    ]


def test_list_entry_uses_explicit_switch_setup_not_last_retrieved(tmp_path):
    mode, store, mark, _teller = make_mode(tmp_path)
    list_id = store.create_list("l")
    store.append_to_list(list_id, "oldest")
    store.append_to_list(list_id, "newest")

    mode.handle(char_event("l"), repeat_count=1)
    last_before = dict(mark.last_retrieved)
    mode.handle(char_event("l"), repeat_count=2)

    assert mode.current == "list"
    assert mark.last_retrieved == last_before
    assert "_list_setup" not in mark.last_retrieved
    assert mode._state["list"]["list_id"] == list_id
    assert mode._state["list"]["key"] == "l"
    assert mode._state["list"]["current_index"] == 1
    assert [item["value"] for item in mode._state["list"]["items"]] == [
        "oldest",
        "newest",
    ]


def test_handler_exception_clears_failed_mode_state_and_continues(tmp_path):
    store = Store(tmp_path / "lore.db")
    teller = RecordingTeller()
    mode = Mode(teller, store)
    calls = []

    def handler(event, ctx):
        state = ctx.get_state()
        state["partial"] = event.char
        calls.append(event.char)
        if event.char == "a":
            raise RuntimeError("handler failed after partial state")
        ctx.teller.speak(f"handled {event.char}")

    mode.register("read", handler)
    mode.switch("read", silent=True)

    mode.handle(char_event("a"))

    assert mode.current == "read"
    assert mode._state["read"] == {}

    mode.handle(char_event("b"))

    assert calls == ["a", "b"]
    assert teller.spoken == ["handled b"]
    assert mode._state["read"] == {"partial": "b"}


def test_app_uses_mode_switch_hook_without_runtime_monkeypatch(tmp_path):
    app = App(
        db_path=str(tmp_path / "lore.db"),
        teller_mode="text",
        listener=NoListener(),
    )
    app.mode.register("read", lambda _event, _ctx: None)

    event = char_event("a")
    assert app._track_repeat(event) == 1
    assert app._track_repeat(event) == 2

    app.mode.switch("read", silent=True)

    assert "switch" not in app.mode.__dict__
    assert app._last_key is None
    assert app._repeat_count == 0


def test_mark_path_uses_real_store_buffer_contract(tmp_path):
    store = Store(tmp_path / "lore.db")
    projects_id = store.create_buffer("projects")
    tome_id = store.create_buffer("tome", buffer_id=projects_id)

    mark = Mark(store)
    mark.into(projects_id).into(tome_id)

    assert mark.path == ["root", "projects", "tome"]
