#!/usr/bin/env python3
"""Minimal smoke test for wiring RSPs together."""

print("Step 1: Import RSPs...")
from store import Store
from teller import get_handler
from mark import Mark
from mode import Mode
from listener import KeyEvent, EventType, SpecialKey, Modifier

print("Step 2: Create Store (temp file)...")
import tempfile
import os
db_file = tempfile.mktemp(suffix=".db")
store = Store(db_file)
print(f"  Using: {db_file}")

print("Step 3: Create Teller (text mode)...")
teller = get_handler("text")

print("Step 4: Create Mark...")
mark = Mark(store)

print("Step 5: Create Mode...")
mode = Mode(teller, store, mark, quit_callback=lambda: None)

print("Step 6: Register minimal read handler...")
def minimal_read(event, ctx):
    if event.char:
        ctx.teller.speak(f"Got key: {event.char}")

mode.register("read", minimal_read, message="Read mode")

print("Step 7: Switch to read mode...")
mode.switch("read")

print("Step 8: Fake a keypress 'a'...")
event = KeyEvent(char='a', key=None, modifiers=frozenset(), event_type=EventType.PRESS)
mode.handle(event)

print("Step 9: Check teller output...")
print("  (TextHandler prints to stdout - see 'Got key: a' above)")

print("\n=== Basic wiring works! ===\n")

# Now try the real handlers
print("Step 10: Import real handlers...")
from handlers import options_handler, read_handler

print("Step 11: Register options_handler...")
mode.register(
    "options",
    options_handler,
    message="Options mode"
)

print("Step 12: Test Ctrl+O (switch to options)...")
# First register read with real handler
mode.register("read", read_handler, message="Read mode")
mode.switch("read")

# Simulate Ctrl+O
print("  Sending Ctrl+O...")
ctrl_o = KeyEvent(char='o', key=None, modifiers=frozenset({Modifier.CTRL}), event_type=EventType.PRESS)
mode.handle(ctrl_o)

print(f"  Current mode: {mode.current}")

print("\n=== Handler wiring works! ===\n")

# Test read_handler with actual data
print("Step 13: Store some data...")
store.set("a", "hello world")
print(f"  Stored 'hello world' at key 'a'")

print("Step 14: Switch back to read mode and press 'a'...")
mode.switch("read", silent=True)
a_event = KeyEvent(char='a', key=None, modifiers=frozenset(), event_type=EventType.PRESS)
mode.handle(a_event)
print(f"  (Should have spoken 'hello world' above)")

print("Step 15: Press 'a' again (double-tap should copy)...")
mode.handle(a_event, repeat_count=2)
print(f"  (Should have spoken 'Copied to clipboard' above)")

print("\n=== Read handler works! ===")
