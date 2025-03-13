# List Mode Implementation Plan

## Creating/Entering Lists
- In read mode:
  - Select a key then press Control-l to:
    - Create a new list if the key is empty
    - Convert existing text to a list with that text as the first item
    - Enter list mode immediately after creating the list
    - Enter list mode if the key already contains a list
  - Hitting the same key twice in a row:
    - First press: Announce "List x items" and read the end item
    - Second press: Enter list mode for that list
  - Hitting a different key resets this sequence

## Navigation Commands
- `n` / `Control-n`: Move to next item (toward end)
- `p` / `Control-p`: Move to previous item (toward beginning)
- `.` (period) or Shift-Alt-`.`: Jump to end of list
- No wrapping when reaching beginning/end

## List Operations
- `a`: Push (append) item from clipboard to end
- `o`: Pop item from end, copy to clipboard, and exit program
- `right arrow` or `enter`: Peek at last item (non-destructive)
- `i`: Insert at specific index (with prompt)
- `r`: Remove at specific index (with prompt)
- `g`: Get item at specific index
- `y` / `Control-y`: Insert clipboard at current position
- `Control-w`: Clear list
- `?`: Speak available commands
- `backspace`: Return to parent buffer/list

## Behavior Details
- Position tracking does not persist between mode switches
- Current position doesn't reset after operations
- All feedback is spoken, not visual
- If user exits list mode, position resets when re-entering