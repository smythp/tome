# Tome of Lore Project Guidelines

## Commands
- Run application: `python tome.py`
- Initialize database: `sqlite3 lore.db < CREATE.sql`
- Manual testing: Use keyboard shortcuts while the app is running

## Code Style
- **Indentation**: 4 spaces
- **Naming**: snake_case for functions and variables
- **Docstrings**: Triple quotes for function documentation
- **Imports**: Group at top of file, local modules last
- **Error handling**: Try/except blocks, particularly for AttributeError
- **Global state**: Use `global` keyword when modifying module-level variables

## Structure
- **Database**: SQLite with dict_factory for returning dictionaries
- **Keyboard**: Uses pynput for key listening and handling
- **TTS**: Uses espeak for voice feedback
- **State management**: Uses global variables for application state

## Development Practices
- Keep consistent with existing modal architecture
- Maintain function naming conventions
- When adding new modes, update the mode_map dictionary
- Always handle potential AttributeError when accessing key.char
- Use parameterized queries for database operations
- Preserve current error handling patterns
- Commit messages should be concise and descriptive without Claude boilerplate