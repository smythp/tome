"""
Mode handlers for Tome of Lore.

Each handler is a function: (event: KeyEvent, context: ModeContext) -> None
"""

from listener import KeyEvent, SpecialKey
from mode import ModeContext


# =============================================================================
# Helpers
# =============================================================================

def status(value: bool) -> str:
    """Format boolean as 'on' or 'off'."""
    return "on" if value else "off"


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
