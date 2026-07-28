# Tome of Lore

Tome of Lore is a keyboard-driven, hierarchical data store with an audio-first interface. It stores and retrieves snippets through modal key commands, persists data in SQLite, and speaks responses through espeak by default.

## Requirements

- Python 3.10 or newer
- SQLite support in Python
- `espeak-ng` or `espeak` on `PATH` for the default speech output
- An X11 desktop/session for the real `pynput` keyboard listener on Linux
- A working clipboard backend for `pyperclip` when using clipboard commands

The `--text --no-listener` mode is the supported headless startup path for CI and smoke tests; wrap it in `timeout` when you need the process to return. The real listener captures global keyboard input and requires a live desktop session.

## Installation

Create an environment outside the repository virtualenv and install the tracked project metadata:

```bash
python -m venv /tmp/tome-venv
/tmp/tome-venv/bin/python -m pip install --upgrade pip
/tmp/tome-venv/bin/python -m pip install -e '.[dev]'
```

Runtime dependencies are declared in `pyproject.toml`: `pynput` and `pyperclip`. Development dependencies are declared in the `dev` extra: `pytest` and `hypothesis`. The current test suite uses pytest built-ins plus Hypothesis; no additional pytest plugin is required.

## Running

```bash
/tmp/tome-venv/bin/python tome.py
/tmp/tome-venv/bin/python tome.py --text
timeout 3s /tmp/tome-venv/bin/python tome.py --text --no-listener
timeout 3s /tmp/tome-venv/bin/tome --text --no-listener
```

By default Tome uses `~/.tome/lore.db`. Pass `--db PATH` to use another SQLite database file. The database schema is created automatically by `Store`; `CREATE.sql` is kept as the schema reference and is not required for normal startup.

`/tmp/tome-venv/bin/python tome.py --help` and `/tmp/tome-venv/bin/tome --help` print CLI help without creating `~/.tome` or a database.

## Testing

Run the full suite from the repository root:

```bash
/tmp/tome-venv/bin/python -m pytest
```

`pytest.ini` intentionally keeps `testpaths = .` so root-level integration tests such as `test_handlers.py`, `test_integration.py`, `test_wire.py`, and `test_tome_lifecycle.py` are collected along with package tests.

## Files

- `tome.py`: CLI entry point and application wiring
- `handlers.py`: mode handler implementations
- `store/`: SQLite-backed hierarchical store
- `teller/`: text, debug, and espeak output handlers
- `mark/`: navigation state
- `mode/`: modal state machine
- `listener/`: keyboard listener abstraction and pynput adapter
- `CREATE.sql`: schema reference
- `pytest.ini`: test discovery configuration
