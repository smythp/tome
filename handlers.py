"""
Mode handlers for Tome of Lore.

Each handler is a function: (event: KeyEvent, context: ModeContext) -> None
"""

import os
import re
import webbrowser
from typing import Callable, Any

from listener import KeyEvent, SpecialKey
from mode import ModeContext


# =============================================================================
# Helpers
# =============================================================================

def quit_app(ctx: ModeContext) -> None:
    """Exit the application (caller should speak before calling)."""
    os._exit(0)  # Force exit - sys.exit doesn't kill listener thread


def status(value: bool) -> str:
    """Format boolean as 'on' or 'off'."""
    return "on" if value else "off"


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL with protocol."""
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http://, https://, ftp://, ftps://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None


def looks_like_file(value: str) -> bool:
    """Check if value looks like a file path (absolute, ~/, or file:// URI)."""
    if value.startswith("file://"):
        return True
    # Expand ~ and check if exists
    expanded = os.path.expanduser(value)
    if expanded.startswith("/") and os.path.exists(expanded):
        return True
    return False


# =============================================================================
# Action Registry (for confirm mode)
# =============================================================================

# Actions that can be confirmed. Each action is a callable(params, context) -> bool, str
# Returns (success, message)
CONFIRM_ACTIONS: dict[str, Callable[[dict, ModeContext], tuple[bool, str]]] = {}


# =============================================================================
# Options Mode
# =============================================================================

def options_handler(event: KeyEvent, ctx: ModeContext) -> None:
    """
    Handle options mode keypresses.

    Keys:
        s - Toggle strip_input
        d - Toggle debug_mode
        a - Toggle default_action (copy/auto)
        Escape - Return to read mode
    """
    # Handle escape (return to previous mode)
    if event.key == SpecialKey.ESCAPE:
        ctx.back()
        return

    # Handle character keys
    char = event.char
    if not char:
        return

    if char == "s":
        # Toggle strip_input
        current = ctx.store.get_config("strip_input", "on") == "on"
        new_value = not current
        ctx.store.set_config("strip_input", "on" if new_value else "off")
        ctx.teller.speak(f"Strip input {status(new_value)}")

    elif char == "d":
        # Toggle debug_mode
        current = ctx.store.get_config("debug_mode", "off") == "on"
        new_value = not current
        ctx.store.set_config("debug_mode", "on" if new_value else "off")
        ctx.teller.speak(f"Debug mode {status(new_value)}")

    elif char == "a":
        # Toggle default_action between copy and auto
        current = ctx.store.get_config("default_action", "copy")
        new_value = "auto" if current == "copy" else "copy"
        ctx.store.set_config(
            "default_action",
            new_value,
            "Controls what happens on double-press (copy or auto)",
        )
        ctx.teller.speak(f"Default action set to {new_value}")

    elif char == "\x1b":  # Escape character (in case it comes through as char)
        ctx.back()


# =============================================================================
# Confirm Mode
# =============================================================================

def confirm_handler(event: KeyEvent, ctx: ModeContext) -> None:
    """
    Handle confirmation prompts (y/n).

    State (via get_state()):
        action: str - Action name to execute on confirm
        params: dict - Parameters for the action
        prompt: str - Prompt to repeat on unknown keys

    Keys:
        y - Confirm and execute action
        n - Cancel
        Escape - Cancel
        (other) - Repeat prompt
    """
    state = ctx.get_state()

    def cancel():
        """Cancel and return to previous mode."""
        ctx.teller.speak("Cancelled")
        state.clear()
        ctx.back()

    def confirm():
        """Execute the action and return to previous mode."""
        action_name = state.get("action")
        params = state.get("params", {})

        if action_name and action_name in CONFIRM_ACTIONS:
            action_fn = CONFIRM_ACTIONS[action_name]
            success, message = action_fn(params, ctx)
            if message:
                ctx.teller.speak(message)
        else:
            ctx.teller.speak(f"Unknown action: {action_name}")

        state.clear()
        ctx.back()

    # Handle escape
    if event.key == SpecialKey.ESCAPE:
        cancel()
        return

    # Handle character keys
    char = event.char
    if not char:
        return

    if char.lower() == "y":
        confirm()
    elif char.lower() == "n" or char == "\x1b":
        cancel()
    else:
        # Repeat prompt for unknown keys
        prompt = state.get("prompt")
        if prompt:
            ctx.teller.speak(prompt)


def register_confirm_action(name: str, action: Callable[[dict, ModeContext], tuple[bool, str]]) -> None:
    """Register an action that can be confirmed."""
    CONFIRM_ACTIONS[name] = action


# =============================================================================
# Clipboard Mode
# =============================================================================

def clipboard_handler(event: KeyEvent, ctx: ModeContext) -> None:
    """
    Store clipboard content at a key.

    Keys:
        [a-z0-9] - Store clipboard at key, exit to read mode
        Escape - Cancel, return to read mode
    """
    import pyperclip

    # Handle escape
    if event.key == SpecialKey.ESCAPE:
        ctx.back()
        return

    # Need a character key
    char = event.char
    if not char:
        return

    # Only alphanumeric keys
    if not char.isalnum():
        return

    # Get clipboard content
    data = pyperclip.paste()
    if data is None:
        data = ""

    # Strip if configured
    strip_input = ctx.store.get_config("strip_input", "on") == "on"
    if strip_input:
        data = data.strip()

    # Store at key in current buffer
    ctx.store.set(char, data, buffer_id=ctx.mark.buffer_id)

    # Announce and exit
    ctx.teller.speak(f"Stored as {char}")
    ctx.switch("read")


# =============================================================================
# Browse Mode
# =============================================================================

def browse_handler(event: KeyEvent, ctx: ModeContext) -> None:
    """
    Open URL from stored data in browser.

    Keys:
        [a-z0-9] - Get value at key, open as URL, exit app
        Escape - Cancel, return to read mode
    """
    # Handle escape
    if event.key == SpecialKey.ESCAPE:
        ctx.back()
        return

    # Need a character key
    char = event.char
    if not char:
        return

    # Only alphanumeric keys
    if not char.isalnum():
        return

    # Get value at key
    entry = ctx.store.get(char, buffer_id=ctx.mark.buffer_id)
    if not entry:
        ctx.teller.speak(f"No data at key {char}")
        return

    value = str(entry.get("value", ""))

    # Validate URL (must have protocol)
    if not is_valid_url(value):
        ctx.teller.speak("Not a valid URL")
        return

    # Open in browser and exit
    webbrowser.open(value)
    ctx.teller.speak("Opening", wait=True)
    quit_app(ctx)


# =============================================================================
# History Mode
# =============================================================================

def _format_global_history_entry(entry: dict, teller) -> None:
    """Format and speak a global history entry with buffer/key info."""
    key = entry.get("key", "?")
    buffer_id = entry.get("buffer_id", "?")
    value = entry.get("value", "")
    deleted_prefix = "Deleted: " if entry.get("deleted", 0) == 1 else ""
    teller.speak(f"Buffer {buffer_id}, key {key}: {deleted_prefix}{value}")


def _read_timestamp(entry: dict, teller) -> None:
    """Read the timestamp of an entry."""
    if not entry or "datetime" not in entry:
        teller.speak("No timestamp available")
        return
    date_str = entry["datetime"].split(".")[0]  # Remove milliseconds
    teller.speak(f"Created on {date_str}")


def _navigate_history(state: dict, direction: str, teller) -> None:
    """Navigate through history entries."""
    entries = state.get("entries", [])
    current_index = state.get("current_index", 0)
    global_mode = state.get("global_mode", False)

    if not entries:
        teller.speak("No history available")
        return

    if direction == "previous" and current_index < len(entries) - 1:
        current_index += 1
    elif direction == "next" and current_index > 0:
        current_index -= 1
    else:
        if direction == "previous":
            teller.speak("At oldest entry")
        else:
            teller.speak("At newest entry")
        return

    state["current_index"] = current_index
    entry = entries[current_index]
    total = len(entries)
    deleted_prefix = "Deleted: " if entry.get("deleted", 0) == 1 else ""

    if global_mode:
        teller.speak(f"Entry {current_index + 1} of {total}")
        _format_global_history_entry(entry, teller)
    else:
        teller.speak(f"Entry {current_index + 1} of {total}: {deleted_prefix}{entry.get('value', '')}")


def _delete_history_entry(state: dict, ctx: ModeContext) -> None:
    """Soft-delete the currently selected history entry."""
    entries = state.get("entries", [])
    current_index = state.get("current_index", 0)
    global_mode = state.get("global_mode", False)

    if not entries or current_index >= len(entries):
        ctx.teller.speak("No history entry to delete")
        return

    entry = entries[current_index]

    if entry.get("deleted", 0) == 1:
        ctx.teller.speak("Entry is already deleted")
        return

    entry_id = entry.get("id")
    if entry_id is None:
        ctx.teller.speak("Cannot delete entry without ID")
        return

    success = ctx.store.delete_entry(entry_id)

    if success:
        entry["deleted"] = 1
        value = entry.get("value", "")
        if global_mode:
            key = entry.get("key", "?")
            buffer_id = entry.get("buffer_id", "?")
            ctx.teller.speak(f"Deleted entry from buffer {buffer_id}, key {key}")
            _format_global_history_entry(entry, ctx.teller)
        else:
            ctx.teller.speak(f"Entry now marked as deleted: {value}")
    else:
        ctx.teller.speak("Failed to delete entry")


def _restore_history_entry(state: dict, ctx: ModeContext) -> None:
    """Restore the currently selected history entry as the current value."""
    entries = state.get("entries", [])
    current_index = state.get("current_index", 0)
    global_mode = state.get("global_mode", False)

    if not entries or current_index >= len(entries):
        ctx.teller.speak("No history entry to restore")
        return

    entry = entries[current_index]
    value = entry.get("value", "")

    if global_mode:
        key = entry.get("key")
        buffer_id = entry.get("buffer_id")
    else:
        key = state.get("key")
        buffer_id = state.get("buffer_id")

    if key is None or buffer_id is None:
        ctx.teller.speak("Cannot restore: missing key or buffer")
        return

    # Store the value as a new entry
    ctx.store.set(key, value, buffer_id=buffer_id)

    if global_mode:
        ctx.teller.speak(f"Restored to buffer {buffer_id}, key {key}: {value}")
    else:
        ctx.teller.speak(f"Restored: {value}")

    # Update mark's last_retrieved
    ctx.mark.last_retrieved = {"value": value, "key": key, "buffer_id": buffer_id}

    # Exit history mode
    state.clear()
    ctx.back()


def _undelete_history_entry(state: dict, ctx: ModeContext) -> None:
    """Undelete a soft-deleted entry."""
    entries = state.get("entries", [])
    current_index = state.get("current_index", 0)

    if not entries or current_index >= len(entries):
        ctx.teller.speak("No entry to undelete")
        return

    entry = entries[current_index]

    if entry.get("deleted", 0) != 1:
        ctx.teller.speak("Entry is not deleted")
        return

    entry_id = entry.get("id")
    if entry_id is None:
        ctx.teller.speak("Cannot undelete entry without ID")
        return

    success, message = ctx.store.restore(entry_id)
    ctx.teller.speak(message)

    if success:
        entry["deleted"] = 0
        ctx.teller.speak("Entry restored")


def history_handler(event: KeyEvent, ctx: ModeContext) -> None:
    """
    Navigate through history entries.

    State (via get_state()):
        entries: list - History entries
        current_index: int - Current position
        global_mode: bool - True if browsing all history, False if key-specific
        key: str - Key being browsed (if not global)
        buffer_id: int - Buffer being browsed (if not global)

    Keys:
        Up / Ctrl+P - Previous (older) entry
        Down / Ctrl+N - Next (newer) entry
        Ctrl+Z - Restore selected entry as current value
        Ctrl+R - Undelete a soft-deleted entry
        Ctrl+T - Read timestamp
        Ctrl+C - Copy to clipboard
        Ctrl+B - Browse URL
        Ctrl+J - Read clipboard
        Delete - Soft-delete entry
        Escape / other char - Exit to read mode
    """
    import pyperclip

    state = ctx.get_state()

    # Check if we need to initialize from setup data
    last_retrieved = getattr(ctx.mark, 'last_retrieved', None) if hasattr(ctx, 'mark') else None
    setup = last_retrieved.get("_history_setup") if last_retrieved and isinstance(last_retrieved, dict) else None
    if setup and "entries" not in state:
        state["entries"] = setup.get("entries", [])
        state["current_index"] = 0
        state["global_mode"] = False
        state["key"] = setup.get("key")
        state["buffer_id"] = setup.get("buffer_id")
        # Clear setup flag
        if hasattr(ctx, 'mark') and ctx.mark:
            ctx.mark.last_retrieved = {"value": None, "key": setup.get("key"), "buffer_id": setup.get("buffer_id")}

    entries = state.get("entries", [])

    def exit_history():
        state.clear()
        ctx.back()

    # Handle special keys
    if event.key == SpecialKey.ESCAPE:
        exit_history()
        return

    if event.key == SpecialKey.UP:
        _navigate_history(state, "previous", ctx.teller)
        return

    if event.key == SpecialKey.DOWN:
        _navigate_history(state, "next", ctx.teller)
        return

    if event.key == SpecialKey.DELETE:
        _delete_history_entry(state, ctx)
        return

    # Handle character keys
    char = event.char
    if not char:
        return

    # Check for Ctrl modifier
    from listener import Modifier
    has_ctrl = Modifier.CTRL in event.modifiers

    if has_ctrl:
        if char == "p":
            _navigate_history(state, "previous", ctx.teller)
        elif char == "n":
            _navigate_history(state, "next", ctx.teller)
        elif char == "z":
            _restore_history_entry(state, ctx)
        elif char == "r":
            _undelete_history_entry(state, ctx)
        elif char == "t" and entries:
            current_index = state.get("current_index", 0)
            if current_index < len(entries):
                _read_timestamp(entries[current_index], ctx.teller)
        elif char == "c" and entries:
            current_index = state.get("current_index", 0)
            if current_index < len(entries):
                value = entries[current_index].get("value", "")
                pyperclip.copy(value)
                ctx.teller.speak("Copied to clipboard")
        elif char == "b" and entries:
            current_index = state.get("current_index", 0)
            if current_index < len(entries):
                value = entries[current_index].get("value", "")
                if is_valid_url(value):
                    webbrowser.open(value)
                    ctx.teller.speak("Opening", wait=True)
                    quit_app(ctx)
                else:
                    ctx.teller.speak("Not a valid URL")
        elif char == "j":
            clipboard = pyperclip.paste()
            ctx.teller.speak(str(clipboard) if clipboard else "Clipboard is empty")
    else:
        # Any non-ctrl character exits history mode
        exit_history()


# =============================================================================
# List Mode
# =============================================================================

def _user_index(internal_index: int, items: list) -> int:
    """Convert internal zero-based index to user-facing one-based index (oldest = 1, newest = N)."""
    if not items:
        return 0
    return internal_index + 1


def _navigate_list(state: dict, direction: str, teller) -> bool:
    """Navigate through list entries.

    Args:
        state: List state dict
        direction: 'next', 'prev', 'top', or 'end'
        teller: Teller for speech output

    Returns:
        True if navigation successful
    """
    items = state.get("items", [])
    current_index = state.get("current_index", 0)

    if not items:
        teller.speak("List is empty")
        return False

    # Safety check
    if current_index < 0 or current_index >= len(items):
        state["current_index"] = len(items) - 1
        current_index = state["current_index"]

    if direction == "next" and current_index < len(items) - 1:
        # Move toward higher internal index (higher user number = newer)
        state["current_index"] = current_index + 1
    elif direction == "prev" and current_index > 0:
        # Move toward lower internal index (lower user number = older)
        state["current_index"] = current_index - 1
    elif direction == "top":
        # Jump to item 1 (oldest = internal index 0)
        state["current_index"] = 0
    elif direction == "end":
        # Jump to last item (newest = internal index len-1)
        state["current_index"] = len(items) - 1
    else:
        if direction == "next":
            teller.speak("At last item")
        elif direction == "prev":
            teller.speak("At first item")
        return False

    item = items[state["current_index"]]
    user_idx = _user_index(state["current_index"], items)

    if direction in ("top", "end"):
        prefix = "First item" if direction == "top" else "Last item"
        teller.speak(f"{prefix} {user_idx} of {len(items)}: {item.get('value', '')}")
    else:
        teller.speak(f"Item {user_idx} of {len(items)}: {item.get('value', '')}")

    return True


def list_handler(event: KeyEvent, ctx: ModeContext) -> None:
    """
    Navigate and manipulate ordered lists.

    State (via get_state()):
        list_id: int - ID of the list
        items: list - List items (from Store.list_items)
        current_index: int - Current position (internal index)
        key: str - Key where list lives
        buffer_id: int - Buffer containing the list

    Keys:
        Up / Left / p / k / Ctrl+P - Previous (toward item 1, older)
        Down / Right / n / j / Ctrl+N - Next (toward item N, newer)
        , (comma) - Jump to first (item 1, oldest)
        . (period) - Jump to last (item N, newest)
        a - Add clipboard to top (becomes newest item)
        e - Add clipboard to bottom (becomes item 1, oldest)
        i - Insert clipboard at current position
        Ctrl+C - Copy current item to clipboard
        Ctrl+B - Open current item (URL/file)
        Enter - Read current item
        Delete - Delete current item
        Backspace/Esc - Exit to read mode
        ? - Help
    """
    import pyperclip
    from listener import Modifier

    state = ctx.get_state()

    # Check for setup data smuggled via mark.last_retrieved (same pattern as history)
    last_retrieved = ctx.mark.last_retrieved if hasattr(ctx, 'mark') and ctx.mark else None
    setup = last_retrieved.get("_list_setup") if last_retrieved and isinstance(last_retrieved, dict) else None
    if setup and "items" not in state:
        state["list_id"] = setup.get("list_id")
        state["key"] = setup.get("key")
        state["buffer_id"] = setup.get("buffer_id")
        state["items"] = setup.get("items", [])
        state["current_index"] = setup.get("current_index", 0)
        # Clear setup flag
        if hasattr(ctx, 'mark') and ctx.mark:
            ctx.mark.last_retrieved = {"value": None, "key": setup.get("key"), "buffer_id": setup.get("buffer_id")}

    items = state.get("items", [])

    def exit_list():
        state.clear()
        ctx.back()

    def refresh_items():
        """Refresh items from store."""
        list_id = state.get("list_id")
        if list_id:
            state["items"] = ctx.store.list_items(list_id)

    # Handle special keys
    if event.key == SpecialKey.ESCAPE:
        exit_list()
        return

    if event.key == SpecialKey.BACKSPACE:
        exit_list()
        return

    if event.key == SpecialKey.UP or event.key == SpecialKey.LEFT:
        # Toward item 1 (older) = lower internal index
        _navigate_list(state, "prev", ctx.teller)
        return

    if event.key == SpecialKey.DOWN or event.key == SpecialKey.RIGHT:
        # Toward item N (newer) = higher internal index
        _navigate_list(state, "next", ctx.teller)
        return

    if event.key == SpecialKey.ENTER:
        if items and 0 <= state.get("current_index", 0) < len(items):
            item = items[state["current_index"]]
            user_idx = _user_index(state["current_index"], items)
            ctx.teller.speak(f"Item {user_idx} of {len(items)}: {item.get('value', '')}")
        else:
            ctx.teller.speak("List is empty")
        return

    if event.key == SpecialKey.DELETE:
        current_index = state.get("current_index", 0)
        if items and 0 <= current_index < len(items):
            item = items[current_index]
            item_id = item.get("id")
            user_idx = _user_index(current_index, items)

            if item_id:
                success = ctx.store.delete_entry(item_id)
                if success:
                    ctx.teller.speak(f"Deleted item {user_idx}")
                    items.pop(current_index)

                    if items:
                        if current_index >= len(items):
                            state["current_index"] = len(items) - 1
                        new_item = items[state["current_index"]]
                        new_user_idx = _user_index(state["current_index"], items)
                        ctx.teller.speak(f"Now at item {new_user_idx} of {len(items)}: {new_item.get('value', '')}")
                    else:
                        ctx.teller.speak("List is now empty")
                else:
                    ctx.teller.speak("Failed to delete item")
        else:
            ctx.teller.speak("No item to delete")
        return

    # Handle character keys
    char = event.char
    if not char:
        return

    has_ctrl = Modifier.CTRL in event.modifiers

    if has_ctrl:
        if char == "p":
            _navigate_list(state, "prev", ctx.teller)  # Toward item 1 (older)
        elif char == "n":
            _navigate_list(state, "next", ctx.teller)  # Toward item N (newer)
        elif char == "c":
            # Copy current item to clipboard
            current_index = state.get("current_index", 0)
            if items and 0 <= current_index < len(items):
                value = items[current_index].get("value", "")
                pyperclip.copy(value)
                ctx.teller.speak("Copied")
            else:
                ctx.teller.speak("No item to copy")
        elif char == "b":
            # Open current item as URL/file
            current_index = state.get("current_index", 0)
            if items and 0 <= current_index < len(items):
                value = items[current_index].get("value", "")
                content_type = _detect_content_type(value)
                if content_type == "url":
                    webbrowser.open(value)
                    ctx.teller.speak("Opening", wait=True)
                    quit_app(ctx)
                elif content_type == "file":
                    import subprocess
                    path = value[7:] if value.startswith("file://") else value
                    path = os.path.expanduser(path)
                    subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    ctx.teller.speak("Opening", wait=True)
                    quit_app(ctx)
                else:
                    ctx.teller.speak("Not a URL or file")
            else:
                ctx.teller.speak("No item to open")
        return

    # Regular character keys
    if char == "n" or char == "j":
        _navigate_list(state, "next", ctx.teller)  # Next (toward newer)
    elif char == "p" or char == "k":
        _navigate_list(state, "prev", ctx.teller)  # Previous (toward older)
    elif char == ",":
        _navigate_list(state, "top", ctx.teller)
    elif char == ".":
        _navigate_list(state, "end", ctx.teller)
    elif char == "a":
        # Append clipboard content (becomes newest = highest number)
        clipboard = pyperclip.paste()
        if clipboard:
            list_id = state.get("list_id")
            if list_id:
                ctx.store.append_to_list(list_id, clipboard)
                refresh_items()
                items = state.get("items", [])
                # New item is at end of internal list (user index N = newest)
                state["current_index"] = len(items) - 1
                ctx.teller.speak(f"Added item {len(items)}: {clipboard}")
        else:
            ctx.teller.speak("Clipboard is empty")
    elif char == "e":
        # Prepend clipboard content (becomes item 1 = oldest)
        clipboard = pyperclip.paste()
        if clipboard:
            list_id = state.get("list_id")
            if list_id:
                ctx.store.prepend_to_list(list_id, clipboard)
                refresh_items()
                items = state.get("items", [])
                # New item is at start of internal list (user index 1 = oldest)
                state["current_index"] = 0
                ctx.teller.speak(f"Added item 1: {clipboard}")
        else:
            ctx.teller.speak("Clipboard is empty")
    elif char == "i":
        # Insert clipboard at current position
        clipboard = pyperclip.paste()
        if clipboard:
            list_id = state.get("list_id")
            current_index = state.get("current_index", 0)
            if list_id:
                # Insert at current_index + 1 so new item takes current user position
                insert_idx = current_index + 1
                ctx.store.insert_in_list(list_id, clipboard, insert_idx)
                refresh_items()
                items = state.get("items", [])
                # Stay at the new item (which is at insert_idx)
                state["current_index"] = insert_idx
                user_idx = _user_index(insert_idx, items)
                ctx.teller.speak(f"Inserted item {user_idx}: {clipboard}")
        else:
            ctx.teller.speak("Clipboard is empty")
    elif char == "?":
        ctx.teller.speak(
            "List mode: a add to top, e add to end, i insert here, "
            "n next, p previous, ctrl c copy, ctrl b open, backspace exit"
        )


# =============================================================================
# Read Mode (Main Mode)
# =============================================================================

# Data type constants (must match Store)
TYPE_VALUE = "value"
TYPE_BUFFER = "buffer"
TYPE_LIST = "list"


def _detect_content_type(value: str) -> str:
    """Detect the type of content in a string."""
    if is_valid_url(value):
        return "url"
    elif looks_like_file(value):
        return "file"
    else:
        return "text"


def _enter_history_mode(key: str, buffer_id: int, ctx: ModeContext) -> bool:
    """Setup history state and switch to history mode.

    Returns True if successfully entered, False otherwise.
    """
    # Get history entries for this key
    entries = ctx.store.history(key, buffer_id=buffer_id, include_deleted=True)

    if not entries or len(entries) <= 1:
        ctx.teller.speak(f"No history for key {key}")
        return False

    # Setup state
    state = ctx.get_state()  # This gets the current mode's state
    # We need to setup history mode's state, so switch first then setup
    # Actually, Mode.switch will give us a fresh state for history mode

    ctx.teller.speak(f"History for {key}, {len(entries)} entries. Most recent: {entries[0].get('value', '')}")

    # Store setup data in mark for history_handler to pick up
    ctx.mark.last_retrieved = {
        "_history_setup": {
            "key": key,
            "buffer_id": buffer_id,
            "entries": entries,
        }
    }

    ctx.switch("history")

    return True


def _enter_list_mode(key: str, buffer_id: int, ctx: ModeContext) -> bool:
    """Setup list state and switch to list mode.

    Returns True if successfully entered, False otherwise.
    """
    # Check if this key contains a list or can be converted to one
    entry = ctx.store.get(key, buffer_id=buffer_id)

    if not entry:
        # Create a new empty list
        list_id = ctx.store.create_list(key, buffer_id=buffer_id)
        ctx.teller.speak("Created new empty list")
    elif entry.get("data_type") == TYPE_VALUE:
        # Convert existing value to a list
        list_id = ctx.store.create_list(key, buffer_id=buffer_id)
        ctx.teller.speak("Converted to list with 1 item")
    elif entry.get("data_type") == TYPE_LIST:
        # Already a list
        list_id = entry.get("id")
        ctx.teller.speak(f"List mode")
    else:
        ctx.teller.speak("Cannot convert to list")
        return False

    # Get list items
    items = ctx.store.list_items(list_id)

    # Start at newest item (highest number = internal len-1)
    start_index = len(items) - 1 if items else 0

    if items:
        ctx.teller.speak(f"Item {len(items)} of {len(items)}: {items[-1].get('value', '')}")
    else:
        ctx.teller.speak("Empty list")

    # Store setup data in mark for list_handler to pick up (same pattern as history)
    ctx.mark.last_retrieved = {
        "_list_setup": {
            "list_id": list_id,
            "key": key,
            "buffer_id": buffer_id,
            "items": items,
            "current_index": start_index,
        }
    }

    ctx.switch("list")
    return True


def _try_enter_buffer(key: str, ctx: ModeContext) -> bool:
    """Try to enter a buffer at the given key.

    Returns True if key was a buffer and we entered it, False otherwise.
    """
    entry = ctx.store.get(key, buffer_id=ctx.mark.buffer_id)

    if not entry or entry.get("data_type") != TYPE_BUFFER:
        return False

    # It's a buffer - the buffer ID is stored in the value field
    try:
        buffer_id = int(entry.get("value"))
    except (ValueError, TypeError):
        # Fallback to entry ID if value isn't a valid buffer ID
        buffer_id = entry.get("id")
    buffer_name = key  # Use key as name

    ctx.mark.into(buffer_id)
    ctx.teller.speak(f"Entering {buffer_name}")

    # Reset last_retrieved when entering buffer
    ctx.mark.last_retrieved = {"value": None, "key": None, "buffer_id": None}

    return True


def read_handler(event: KeyEvent, ctx: ModeContext) -> None:
    """
    Main read mode - primary interaction with the tome.

    Keys:
        [a-z0-9] - Read value (1st press), copy/action (2nd press)
        Delete - Soft-delete last retrieved entry
        Ctrl+C - Copy last value, exit
        Ctrl+B - Browse URL, exit
        Ctrl+T - Read timestamp
        Ctrl+H - Enter history mode
        Ctrl+Y - Write clipboard to last key, exit
        Ctrl+G - Create buffer at last key
        Ctrl+O - Enter options mode
        Ctrl+J - Read clipboard aloud
        Ctrl+L - Enter list mode
        Backspace - Go back (exit buffer)
    """
    import pyperclip
    from listener import Modifier

    last = ctx.mark.last_retrieved or {}

    # Handle Delete key
    if event.key == SpecialKey.DELETE:
        if not last.get("key"):
            ctx.teller.speak("No register selected")
            return

        # Get the entry to delete
        entry = ctx.store.get(last["key"], buffer_id=last.get("buffer_id", ctx.mark.buffer_id))

        if not entry:
            ctx.teller.speak(f"No data at key {last['key']}")
            return

        if entry.get("data_type") == TYPE_BUFFER:
            ctx.teller.speak("Use delete inside buffer to delete with confirmation")
            return

        # Soft delete
        entry_id = entry.get("id")
        if entry_id and ctx.store.delete_entry(entry_id):
            ctx.teller.speak(f"Deleted register {last['key']}")
            ctx.mark.last_retrieved = {**last, "value": None}
        else:
            ctx.teller.speak(f"Failed to delete register {last['key']}")
        return

    # Handle Backspace - go back/exit buffer
    if event.key == SpecialKey.BACKSPACE:
        if ctx.mark.back():
            ctx.teller.speak("Back")
        else:
            ctx.teller.speak("At root")
        return

    # Handle character keys
    char = event.char
    if not char:
        return

    # Only handle alphanumeric in read mode
    if not char.isalnum() and not (Modifier.CTRL in event.modifiers):
        return

    has_ctrl = Modifier.CTRL in event.modifiers

    if has_ctrl:
        # Ctrl key combinations

        # Operations requiring last_retrieved value
        if last.get("value"):
            if char == "c":
                pyperclip.copy(last["value"])
                ctx.teller.speak("Copied", wait=True)
                quit_app(ctx)

            elif char == "b":
                value = last["value"]
                if is_valid_url(value):
                    webbrowser.open(value)
                    ctx.teller.speak("Opening", wait=True)
                    quit_app(ctx)
                else:
                    ctx.teller.speak("Not a valid URL")
                return

            elif char == "t":
                entry = ctx.store.get(last["key"], buffer_id=last.get("buffer_id", ctx.mark.buffer_id))
                if entry:
                    _read_timestamp(entry, ctx.teller)
                return

        # Operations requiring last_retrieved key
        if last.get("key"):
            if char == "h":
                _enter_history_mode(last["key"], last.get("buffer_id", ctx.mark.buffer_id), ctx)
                return

            elif char == "y":
                data = pyperclip.paste() or ""
                strip_input = ctx.store.get_config("strip_input", "on") == "on"
                if strip_input:
                    data = data.strip()
                # Check if key contains a list - append instead of clobber
                entry = ctx.store.get(last["key"], buffer_id=last.get("buffer_id", ctx.mark.buffer_id))
                if entry and entry.get("data_type") == TYPE_LIST:
                    list_id = entry.get("id")
                    ctx.store.append_to_list(list_id, data)
                    ctx.teller.speak(f"Added to {last['key']}", wait=True)
                else:
                    ctx.store.set(last["key"], data, buffer_id=last.get("buffer_id", ctx.mark.buffer_id))
                    ctx.teller.speak(f"Wrote {last['key']}", wait=True)
                quit_app(ctx)

            elif char == "g":
                # Create buffer at last key
                buffer_id = last.get("buffer_id", ctx.mark.buffer_id)
                key = last["key"]

                # Check if buffer already exists
                entry = ctx.store.get(key, buffer_id=buffer_id)
                if entry and entry.get("data_type") == TYPE_BUFFER:
                    ctx.teller.speak(f"Buffer already exists at {key}")
                    _try_enter_buffer(key, ctx)
                    return

                # Create new buffer
                new_buffer_id = ctx.store.create_buffer(key, buffer_id)
                ctx.mark.into(new_buffer_id)
                ctx.teller.speak(f"Created buffer {key}")
                return

            elif char == "l":
                _enter_list_mode(last["key"], last.get("buffer_id", ctx.mark.buffer_id), ctx)
                return

        # Operations that don't require last_retrieved
        if char == "o":
            ctx.switch("options")
            return

        elif char == "j":
            clipboard = pyperclip.paste()
            ctx.teller.speak(str(clipboard) if clipboard else "Clipboard is empty")
            return

        return  # Ignore other Ctrl combinations

    # Regular key press - read/copy behavior

    # Check if it's a buffer first
    if _try_enter_buffer(char, ctx):
        return

    # Get data at this key
    entry = ctx.store.get(char, buffer_id=ctx.mark.buffer_id)

    # Always update last_retrieved key (even if empty, for Ctrl+Y)
    ctx.mark.last_retrieved = {
        "key": char,
        "buffer_id": ctx.mark.buffer_id,
        "value": entry.get("value") if entry else None,
    }

    if not entry:
        ctx.teller.speak(f"No data at key {char}")
        return

    value = str(entry.get("value", ""))
    data_type = entry.get("data_type", TYPE_VALUE)

    # Handle lists
    if data_type == TYPE_LIST:
        items = ctx.store.list_items(entry.get("id"))
        if ctx.repeat_count == 1:
            if items:
                ctx.teller.speak(f"List with {len(items)} items. Item 1: {items[0].get('value', '')}")
            else:
                ctx.teller.speak(f"Empty list at key {char}")
        else:
            # Second press - enter list mode
            _enter_list_mode(char, ctx.mark.buffer_id, ctx)
        return

    # Standard value handling
    if ctx.repeat_count == 1:
        # First press - read value
        ctx.teller.speak(value)
    else:
        # Second press - smart action based on content type
        content_type = _detect_content_type(value)
        if content_type == "url":
            webbrowser.open(value)
            ctx.teller.speak("Opening", wait=True)
            quit_app(ctx)
        elif content_type == "file":
            # Open file in default app
            import subprocess
            path = value[7:] if value.startswith("file://") else value
            path = os.path.expanduser(path)
            subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ctx.teller.speak("Opening", wait=True)
            quit_app(ctx)
        else:
            pyperclip.copy(value)
            ctx.teller.speak("Copied", wait=True)
            quit_app(ctx)
