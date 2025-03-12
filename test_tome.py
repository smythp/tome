import pytest
import sqlite3
import os
import sys
from unittest.mock import patch, MagicMock

# Mock keyboard components
class MockKey:
    """Mock for pynput.keyboard.Key"""
    
    # Create attributes to match pynput.keyboard.Key static attributes
    shift = 'shift'
    ctrl = 'ctrl'
    alt = 'alt'
    esc = 'esc'
    backspace = 'backspace'
    up = 'up'
    down = 'down'
    delete = 'delete'
    
    def __init__(self, name=None):
        self.name = name

class MockKeyCode:
    """Mock for pynput.keyboard._xorg.KeyCode"""
    
    def __init__(self, char):
        self.char = char

# Fixtures for testing
@pytest.fixture
def mock_db():
    """Create in-memory test database with proper schema."""
    conn = sqlite3.connect(':memory:')
    
    # Apply dict_factory from utilities
    from utilities import dict_factory
    conn.row_factory = dict_factory
    
    cursor = conn.cursor()
    
    # Read schema from CREATE.sql
    with open('CREATE.sql', 'r') as f:
        schema = f.read()
    
    # Execute schema creation
    cursor.executescript(schema)
    conn.commit()
    
    # Patch the connect function to return our test db
    with patch('tome.connect', return_value=(conn, cursor)):
        yield conn, cursor
    
    # Clean up
    conn.close()

@pytest.fixture
def mock_speech():
    """Mock the speak function to capture output instead of speaking."""
    with patch('tome.speak') as mock:
        yield mock

@pytest.fixture
def mock_clipboard():
    """Mock clipboard functions."""
    with patch('tome.copy') as copy_mock, patch('tome.paste') as paste_mock:
        paste_mock.return_value = "test clipboard data"
        yield copy_mock, paste_mock

@pytest.fixture
def mock_keyboard_listener():
    """Mock the keyboard listener to prevent actual keyboard monitoring."""
    with patch('tome.keyboard.Listener') as mock:
        listener_instance = MagicMock()
        mock.return_value = listener_instance
        yield mock

@pytest.fixture
def reset_globals():
    """Reset global variables to their default state before each test."""
    import tome
    
    # Save original values
    original_values = {
        'mode': tome.mode,
        'current_register': tome.current_register,
        'suppress_mode_message': tome.suppress_mode_message,
        'strip_input': tome.strip_input,
        'register_stack': tome.register_stack.copy(),
        'buffer_path': tome.buffer_path.copy(),
        'pressed': tome.pressed.copy(),
        'key_presses': tome.key_presses.copy(),
        'last_retrieved': tome.last_retrieved.copy(),
        'history_state': tome.history_state.copy()
    }
    
    # Reset to default for testing
    tome.mode = "default"
    tome.current_register = 1
    tome.suppress_mode_message = False
    tome.strip_input = True
    tome.register_stack = [1]
    tome.buffer_path = []
    tome.pressed = {
        'shift': False,
        'ctrl': False,
        'alt': False,
    }
    tome.key_presses = {}
    tome.last_retrieved = {
        'value': None,
        'key': None,
        'register': None
    }
    tome.history_state = {
        'active': False,
        'key': None,
        'register': None,
        'entries': [],
        'current_index': 0,
        'global_mode': False
    }
    
    yield
    
    # Restore original values
    tome.mode = original_values['mode']
    tome.current_register = original_values['current_register']
    tome.suppress_mode_message = original_values['suppress_mode_message']
    tome.strip_input = original_values['strip_input']
    tome.register_stack = original_values['register_stack'].copy()
    tome.buffer_path = original_values['buffer_path'].copy()
    tome.pressed = original_values['pressed'].copy()
    tome.key_presses = original_values['key_presses'].copy()
    tome.last_retrieved = original_values['last_retrieved'].copy()
    tome.history_state = original_values['history_state'].copy()


# Basic db operation tests
def test_dict_factory():
    """Test the dict_factory function from utilities."""
    from utilities import dict_factory
    
    # Create mock cursor description and row
    mock_cursor = MagicMock()
    mock_cursor.description = [('id', None, None, None, None, None, None), 
                              ('value', None, None, None, None, None, None)]
    row = (1, 'test value')
    
    # Call dict_factory
    result = dict_factory(mock_cursor, row)
    
    # Verify result is a dict with correct values
    assert isinstance(result, dict)
    assert result['id'] == 1
    assert result['value'] == 'test value'


def test_store_and_retrieve(mock_db, reset_globals):
    """Test storing and retrieving a simple key/value pair."""
    from tome import store, retrieve, current_register
    
    # Store a test value
    test_key = 'a'
    test_value = 'test value'
    store(test_key, test_value)
    
    # Retrieve the value
    result = retrieve(test_key, register=current_register)
    
    # Verify the retrieved value matches what was stored
    assert result['value'] == test_value
    assert result['key'] == test_key
    assert result['data_type'] == 'key'
    assert result['register'] == current_register


def test_clipboard_mode(mock_db, mock_speech, mock_clipboard, reset_globals):
    """Test entering clipboard mode and saving clipboard content."""
    from tome import clipboard, change_mode
    
    # First change to clipboard (store) mode
    change_mode('clipboard')
    
    # Create mock key press for 'a'
    mock_key = MockKeyCode(char='a')
    
    # Call the clipboard function directly with the mock key
    clipboard(mock_key)
    
    # Verify something was stored under key 'a'
    from tome import retrieve, current_register
    result = retrieve('a', register=current_register)
    
    assert result is not None
    assert result['value'] == "test clipboard data"
    
    # Verify appropriate speech was triggered
    expected_speech = f"Stored test clipboard data as a in register {current_register}"
    mock_speech.assert_any_call(expected_speech)


def test_read_mode(mock_db, mock_speech, mock_clipboard, reset_globals):
    """Test reading stored content."""
    from tome import store, read, current_register, change_mode
    
    # Store a test value first
    test_key = 'a'
    test_value = 'test value'
    store(test_key, test_value)
    
    # Change to read mode
    change_mode('read')
    
    # Create mock key press for 'a'
    mock_key = MockKeyCode(char='a')
    
    # Call read function as if 'a' was pressed
    read(mock_key)
    
    # Verify the value was spoken
    mock_speech.assert_any_call(test_value)


def test_toggle_strip_input(mock_db, mock_speech, reset_globals):
    """Test toggling the strip_input option."""
    from tome import options, strip_input, change_mode
    
    # Set initial state and change to options mode
    original_strip_input = strip_input
    change_mode('options')
    
    # Create mock key press for 's'
    mock_key = MockKeyCode(char='s')
    
    # Call options function as if 's' was pressed
    options(mock_key)
    
    # Verify strip_input was toggled
    from tome import strip_input
    assert strip_input != original_strip_input
    
    # Verify appropriate message was spoken
    expected_status = "off" if not strip_input else "on"
    mock_speech.assert_any_call(f"Strip input {expected_status}")


def test_key_handler_quit(mock_speech, reset_globals):
    """Test quitting the application via key_handler."""
    from tome import key_handler
    
    # Create mock key press for 'q'
    mock_key = MockKeyCode(char='q')
    
    # Call key_handler with mocked exit to prevent actually exiting the test
    with patch('tome.exit') as mock_exit:
        key_handler(mock_key)
        
        # Verify exit was called and quit message was spoken
        mock_exit.assert_called_once()
        mock_speech.assert_called_with("Quit")