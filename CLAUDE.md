# Tome of Lore Project Guidelines

## Commands
- Install for development: `python -m venv /tmp/tome-venv && /tmp/tome-venv/bin/python -m pip install -e '.[dev]'`
- Run application: `/tmp/tome-venv/bin/python tome.py`
- Run with text output: `/tmp/tome-venv/bin/python tome.py --text`
- Run headless smoke path: `timeout 3s /tmp/tome-venv/bin/python tome.py --text --no-listener`
- Run installed console smoke path: `timeout 3s /tmp/tome-venv/bin/tome --text --no-listener`
- Run tests: `/tmp/tome-venv/bin/python -m pytest`
- Show help: `/tmp/tome-venv/bin/python tome.py --help` or `/tmp/tome-venv/bin/tome --help`

## Runtime Notes
- Default database path: `~/.tome/lore.db`
- Override database path with `--db PATH`
- `Store` initializes the SQLite schema automatically; `CREATE.sql` is a schema reference, not a required startup step
- `--help` must remain side-effect free and must not create `~/.tome`
- Default speech output requires `espeak-ng` or `espeak` on `PATH`; use `--text` to avoid speech output
- The real pynput listener requires an X11 desktop/session on Linux and captures global keyboard input; use `--no-listener` for headless tests and smoke checks

## Dependencies
- Runtime Python dependencies are declared in `pyproject.toml`: `pynput`, `pyperclip`
- Development dependencies are declared in the `dev` extra: `pytest`, `hypothesis`
- The test suite currently uses pytest built-ins plus Hypothesis; no separate pytest plugin is required

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
- Preserve `pytest.ini` root integration collection with `testpaths = .` unless an equivalent full-suite collection path is proven
- Commit messages should be concise and descriptive without Claude boilerplate
