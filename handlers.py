"""
Mode handlers for Tome of Lore.

Each handler is a function: (event: KeyEvent, context: ModeContext) -> None
"""

import re
import sys
import webbrowser
from typing import Callable, Any

from listener import KeyEvent, SpecialKey
from mode import ModeContext


# =============================================================================
# Helpers
# =============================================================================

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


def looks_like_domain(value: str) -> bool:
    """Check if value looks like a domain without protocol."""
    return bool(re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}(?:\/.*)?$', value))


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

    # Validate/fix URL
    if is_valid_url(value):
        url = value
    elif looks_like_domain(value):
        url = "http://" + value
        ctx.teller.speak(f"Adding http protocol")
    else:
        ctx.teller.speak("Not a valid URL")
        return

    # Open in browser and exit
    webbrowser.open(url)
    ctx.teller.speak(f"Opening {value}")
    sys.exit(0)
