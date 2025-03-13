# Tome of Lore

A keyboard-driven, hierarchical note storage system with text-to-speech feedback. Store and retrieve data using a purely audio interface.

## Overview

Tome of Lore is an accessibility-focused application that lets you:
- Store and organize text snippets using keyboard shortcuts
- Retrieve information through voice feedback
- Navigate a hierarchical storage system with nested buffers
- Copy/paste content between your clipboard and the application
- Track history of all stored information

## Setup

### Prerequisites
- Python 3.8+
- SQLite3
- espeak (for text-to-speech)

### Installation

1. Clone this repository
2. Run the setup script:
   ```
   ./setup_tome.sh
   ```

This script will:
- Check for and optionally install UV (Python package manager)
- Install required Python dependencies
- Create the SQLite database from CREATE.sql
- Create runner scripts for the application and tests

## Usage

### Running the Application

```
./run_tome.sh
```

### Key Features

- **Read Mode**: Access stored information with voice feedback
- **Clipboard Mode**: Store clipboard content to keys
- **History Mode**: Review and restore previous values
- **Browse Mode**: Open URLs from stored data
- **Options Mode**: Configure application settings

## Testing

Run the test suite:
```
./run_tests.sh
```

This executes the pytest test suite, which verifies application functionality.

## Technical Structure

- **Database**: SQLite with dict_factory for returning dictionaries
- **Keyboard**: Uses pynput for key listening and handling
- **TTS**: Uses espeak for voice feedback
- **State Management**: Modal architecture with buffer navigation

### Files

- `tome.py`: Main application logic
- `utilities.py`: Helper functions
- `CREATE.sql`: Database schema definition
- `test_tome.py`: Automated tests

## Development

See CLAUDE.md for detailed code style guidelines and development practices.

Key principles:
- Follow snake_case naming conventions
- Document functions with triple-quoted docstrings
- Handle keyboard events consistently
- Preserve the modal architecture
- Use parameterized queries for database operations