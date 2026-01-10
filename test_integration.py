#!/usr/bin/env python3
"""Integration test - simulates a user session."""

import sys
import os
sys.stdout.reconfigure(line_buffering=True)  # Flush on newline

# Mock os._exit to prevent actual exit during test
_exit_called = False
def mock_exit(code):
    global _exit_called
    _exit_called = True
    print(f"(os._exit({code}) called - suppressed)")
os._exit = mock_exit

from store import Store
from teller import get_handler
from mark import Mark
from mode import Mode
from listener import KeyEvent, EventType, SpecialKey, Modifier
from handlers import (
    options_handler,
    confirm_handler,
    clipboard_handler,
    browse_handler,
    history_handler,
    list_handler,
    read_handler,
)

print("=== Tome Integration Test ===\n")

# Setup
print("Setting up...")
store = Store("/tmp/test_integration.db")
teller = get_handler("text")
mark = Mark(store)
mode = Mode(teller, store, mark)

# Track repeat count like tome.py does
last_key = None
repeat_count = 0

def track_repeat(event):
    global last_key, repeat_count
    key_id = event.char if event.char else str(event.key)
    if key_id == last_key:
        repeat_count += 1
    else:
        repeat_count = 1
        last_key = key_id
    return repeat_count

def reset_repeat():
    global last_key, repeat_count
    last_key = None
    repeat_count = 0

def press(char=None, key=None, ctrl=False):
    """Simulate a keypress."""
    mods = frozenset({Modifier.CTRL}) if ctrl else frozenset()
    event = KeyEvent(char=char, key=key, modifiers=mods, event_type=EventType.PRESS)
    rc = track_repeat(event)
    mode.handle(event, repeat_count=rc)

def switch_mode(name):
    """Switch mode and reset repeat."""
    reset_repeat()
    mode.switch(name)

# Register handlers
print("Registering handlers...")
mode.register("read", read_handler, message="Read from tome")
mode.register("options", options_handler, message="Options mode")
mode.register("confirm", confirm_handler, message=None)
mode.register("clipboard", clipboard_handler, message="Clipboard mode")
mode.register("browse", browse_handler, message="Browse mode")
mode.register("history", history_handler, message="History mode")
mode.register("list", list_handler, message="List mode")

# Start in read mode
print("\n--- Starting in read mode ---")
switch_mode("read")

# Test 1: Store and read a value
print("\n--- Test 1: Store and read ---")
store.set("a", "hello world")
print("Stored 'hello world' at 'a'")
print("Pressing 'a':")
press(char='a')

# Test 2: Double-tap to copy
print("\n--- Test 2: Double-tap ---")
print("Pressing 'a' again:")
# Note: would normally call sys.exit(), let's see what happens
try:
    press(char='a')
except SystemExit:
    print("(SystemExit caught - copy worked)")

# Test 3: Switch to options
print("\n--- Test 3: Options mode ---")
reset_repeat()
print("Pressing Ctrl+O:")
press(char='o', ctrl=True)
print(f"Current mode: {mode.current}")

# Test 4: Toggle a setting
print("\n--- Test 4: Toggle setting ---")
print("Pressing 's' (toggle strip_input):")
press(char='s')

# Test 5: Back to read mode
print("\n--- Test 5: Back to read ---")
print("Pressing Escape:")
press(key=SpecialKey.ESCAPE)
print(f"Current mode: {mode.current}")

# Test 6: Empty key
print("\n--- Test 6: Empty key ---")
reset_repeat()
print("Pressing 'z' (no data):")
press(char='z')

# Test 7: History mode
print("\n--- Test 7: History mode ---")
reset_repeat()
# Store multiple versions
store.set("h", "version 1")
store.set("h", "version 2")
store.set("h", "version 3")
print("Stored 3 versions at 'h'")

# Read 'h' first to set last_retrieved
print("Pressing 'h':")
press(char='h')

# Now Ctrl+H to enter history
print("Pressing Ctrl+H:")
reset_repeat()
press(char='h', ctrl=True)
print(f"Current mode: {mode.current}")

# Navigate history
print("Pressing Up (older):")
press(key=SpecialKey.UP)

# Exit history
print("Pressing Escape:")
press(key=SpecialKey.ESCAPE)
print(f"Current mode: {mode.current}")

# Test 8: List mode
print("\n--- Test 8: List mode ---")
reset_repeat()
# Create a list at key 'l'
list_id = store.create_list("l", buffer_id=1)
store.append_to_list(list_id, "item one")
store.append_to_list(list_id, "item two")
store.append_to_list(list_id, "item three")
print("Created list with 3 items at key 'l'")

# First press - reads list info
print("Pressing 'l' (first - reads list info):")
press(char='l')

# Second press - enters list mode
print("Pressing 'l' again (enters list mode):")
press(char='l')
print(f"Current mode: {mode.current}")

# Navigate - next item
print("Pressing 'n' (next item):")
press(char='n')

# Navigate - previous item
print("Pressing 'p' (previous item):")
press(char='p')

# Jump to end
print("Pressing '.' (jump to end):")
press(char='.')

# Read current item
print("Pressing Enter (read current):")
press(key=SpecialKey.ENTER)

# Help
print("Pressing '?' (help):")
press(char='?')

# Exit list mode
print("Pressing Backspace (exit list mode):")
press(key=SpecialKey.BACKSPACE)
print(f"Current mode: {mode.current}")

# Test 9: Buffer navigation
print("\n--- Test 9: Buffer navigation ---")
reset_repeat()
# Create a buffer
print("Creating buffer at 'b'...")
buf_id = store.create_buffer("b", buffer_id=1)
print(f"Created buffer with id {buf_id}")

# Store something in the buffer
store.set("x", "inside buffer", buffer_id=buf_id)

# Read 'b' to enter buffer
print("Pressing 'b' (enter buffer):")
press(char='b')
print(f"Mark buffer_id: {mark.buffer_id}")

# Read 'x' inside buffer
print("Pressing 'x':")
reset_repeat()
press(char='x')

# Go back
print("Pressing Backspace (exit buffer):")
press(key=SpecialKey.BACKSPACE)
print(f"Mark buffer_id: {mark.buffer_id}")

print("\n=== All tests complete ===")
