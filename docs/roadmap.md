# Tome Roadmap

Future directions and big ideas consolidated from historical planning docs.

## Unimplemented Features

### Buffer Overview (Ctrl+I)
Press Ctrl+I to get a spoken overview of the current buffer's contents:
- Categorized by type: buffers, URLs, lists, text
- Counts per category
- Navigate through items with up/down arrows
- Full content on navigation, truncated in overview

### Command Execution
Store and execute shell commands from registers:
- Detect command patterns (pipes, `&&`, `;`, `!` prefix)
- Config option to enable/disable (off by default)
- Double-press register key to execute
- Output spoken, copied to clipboard
- Backtick (`) to recall last command output

### Open URLs by Default
When double-pressing a URL register, open it instead of copying.
Current behavior requires Ctrl+B explicitly.

### Lock Data
Ability to lock/protect certain registers from modification.
Prevent accidental overwrites of important data.

### Undo
Undo last destructive operation (delete, overwrite).
Could leverage existing history/soft-delete infrastructure.

## Implemented (Archive)

These were planned and have been implemented:

- **List Mode** - Ctrl+L to create/enter lists, navigation, append/prepend/insert
- **History Mode** - Ctrl+H to navigate historical values
- **Ctrl+A Bulk Operations** - Copy all / open all in list mode
