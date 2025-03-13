# Tome of Lore

A keyboard-driven, hierarchical data storage and retrieval system with an audio-only interface.

## Overview

Tome of Lore saves and retrieves data stored at specific keys. By default, the application exits after a storage and retrieval operation. Designed for quick data storage or retrieval without context switching.


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
- Create a runner script for tests

## Usage

### Running the Application

```
./tome.py
```

or 

```
uv run tome.py
```

## Testing

Run the test suite:
```
./run_tests.sh
```

### Files

- `tome.py`: Main application logic
- `utilities.py`: Helper functions
- `CREATE.sql`: Database schema definition
- `test_tome.py`: Automated tests
