# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "pynput",
#     "pyperclip",
# ]
# ///
from subprocess import call, Popen, DEVNULL
import pynput
from pynput import keyboard
from pynput.keyboard import Key, Controller
import os
import webbrowser
import re
from Xlib.error import ConnectionClosedError
import sqlite3
import datetime
from pyperclip import copy, paste
from utilities import dict_factory, get_global_history

# Terminology:
# - Register: Any key-value pair where a key stores some data (e.g., 'a' → "hello world")
# - Buffer: A special type of container that holds its own set of registers
#   When you enter a buffer, you get a clean namespace with a new set of key-value pairs
# - current_buffer_id: The ID of the buffer we're currently in
# - buffer_stack: Navigation history of buffers (for backspace navigation)
# - buffer_path: Path of keys used to navigate to current buffer (for display purposes)

# Data type constants
TYPE_VALUE = "value"  # Normal key-value pair
TYPE_BUFFER = "buffer"  # Nested buffer container
TYPE_LIST = "list"  # List container for multiple values

# Buffer-related state
current_buffer_id = 1  # ID of the buffer we're currently in (1 is the root buffer)
buffer_stack = [1]     # Stack of buffer IDs for navigation (for tracking the path back to root)
buffer_path = []       # Path of keys used to navigate to current buffer (for display purposes)

# Application state
mode = "default"     # Current mode (read, clipboard, options, etc.)
suppress_mode_message = False
strip_input = True
debug_mode = False   # Debug mode toggle (overridden by database setting)
key_presses = {}     # Track key presses for read functionality

# Get absolute paths for more reliable file access
tome_directory = os.path.abspath(os.path.dirname(__file__))
database = os.path.join(tome_directory, 'lore.db')

# This initial print is always shown as it's needed to identify the database location
print(f"Database path: {database}")


pressed = {
    'shift': False,
    'ctrl': False,
    'alt': False,    
    }



def bp():
    pynput.keyboard.Listener.stop()
    breakpoint()



def max_buffer_id():
    """Find the highest created buffer ID."""

    connection, cursor = connect()

    query = "SELECT buffer_id from lore;"
    results = cursor.execute(query)
    results = results.fetchall()

    results = [result['buffer_id'] for result in results if result['buffer_id']]

    if not results:
        return 0  # Return 0 if no buffers exist yet
    
    highest_buffer_id = max(results)
    return highest_buffer_id


def new_buffer_id():
    """Create a new unique buffer ID."""
    return max_buffer_id() + 1


def is_key_a_buffer(key, parent_buffer_id=None):
    """Check if a key contains a buffer in the specified parent buffer.
    
    Args:
        key: The key to check
        parent_buffer_id: The parent buffer ID to check in (uses current_buffer_id if None)
        
    Returns:
        True if the key contains a buffer, False otherwise
    """
    if parent_buffer_id is None:
        parent_buffer_id = current_buffer_id
        
    result = retrieve(key, buffer_id=parent_buffer_id, fetch='last')
    return result and result.get('data_type') == TYPE_BUFFER and result.get('parent_id') == parent_buffer_id


def create_buffer_at_key(key, parent_buffer_id=None):
    """Create a new buffer at the specified key.
    
    Args:
        key: The key where the buffer should be created
        parent_buffer_id: The parent buffer ID (uses current_buffer_id if None)
        
    Returns:
        The new buffer ID
    """
    if parent_buffer_id is None:
        parent_buffer_id = current_buffer_id
        
    # Create a new buffer ID
    buffer_id = new_buffer_id()
    
    # Store the buffer with parent reference
    store(key, buffer_id, label='buffer', data_type=TYPE_BUFFER, 
          buffer_id=parent_buffer_id, parent_id=parent_buffer_id)
    
    return buffer_id


def status(boolean):
    """Return on if true, off if false."""

    return 'on' if boolean else 'off'

def kill_speech():
    """Kill any running espeak processes"""
    try:
        # Try to kill any running espeak processes
        call(["killall", "espeak"], stderr=DEVNULL)
    except:
        # Ignore errors if no processes were killed
        pass

def speak(text_to_speak, speed=270, asynchronous=True):
    # Kill any ongoing speech before starting a new one
    kill_speech()
    
    if asynchronous:
        Popen(["espeak", f"-s{speed} -ven+18 -z", text_to_speak])
    else:
        call(["espeak", f"-s{speed} -ven+18 -z", text_to_speak])



def debug_print(*args, **kwargs):
    """Print only if debug_mode is enabled."""
    global debug_mode
    if debug_mode:
        print(*args, **kwargs)


def get_config(key, default=None):
    """Get a configuration value from the database."""
    try:
        connection, cursor = connect(skip_debug=True)  # Avoid circular reference
        
        # Check if the config table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='config'")
        if not cursor.fetchone():
            # If table doesn't exist, return default
            return default
            
        # Get the config value
        cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
        result = cursor.fetchone()
        
        if result:
            return result['value']
        return default
    except Exception as e:
        print(f"Error getting config {key}: {e}")
        return default


def set_config(key, value, description=None):
    """Set a configuration value in the database."""
    try:
        connection, cursor = connect(skip_debug=True)  # Avoid circular reference
        
        # Check if the config table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='config'")
        if not cursor.fetchone():
            # Create the config table if it doesn't exist
            cursor.execute('''
                CREATE TABLE config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    description TEXT
                )
            ''')
            
        # Get current description if available and none provided
        if description is None:
            cursor.execute("SELECT description FROM config WHERE key = ?", (key,))
            result = cursor.fetchone()
            if result:
                description = result['description']
        
        # Insert or update the config value
        cursor.execute('''
            INSERT OR REPLACE INTO config (key, value, description)
            VALUES (?, ?, ?)
        ''', (key, value, description))
        
        connection.commit()
        return True
    except Exception as e:
        print(f"Error setting config {key}: {e}")
        return False


def connect(skip_debug=False):
    """Connect to the database. Returns a tuple containing connection and cursor objects."""
    try:
        if not skip_debug:  # Skip debug prints when called from get_config to avoid circular reference
            debug_print(f"Connecting to database: {database}")
            debug_print(f"Database exists: {os.path.exists(database)}")
            debug_print(f"Database directory exists: {os.path.exists(os.path.dirname(database))}")
            debug_print(f"Database permissions: {oct(os.stat(database).st_mode & 0o777) if os.path.exists(database) else 'N/A'}")
            debug_print(f"Current working directory: {os.getcwd()}")
        
        # Ensure directory exists for the database
        db_dir = os.path.dirname(database)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        # Use a timeout to handle potential locks and specify URI mode for better diagnostics
        connection = sqlite3.connect(database, timeout=10)
        connection.row_factory = dict_factory

        cursor = connection.cursor()
        
        # Check if the lore table exists, if not create it
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lore'")
        if not cursor.fetchone():
            speak("Initializing database")
            # Create the table
            cursor.execute('''
                CREATE TABLE lore (
                    id INTEGER PRIMARY KEY,
                    key TEXT,
                    value TEXT,
                    label TEXT,
                    data_type TEXT,
                    datetime TEXT,
                    buffer_id INTEGER,
                    parent_id INTEGER,
                    item_index INTEGER
                )
            ''')
            connection.commit()
            
        return connection, cursor
    except sqlite3.Error as e:
        # Provide a helpful error message with diagnostics
        error_msg = f"Database error: {e}"
        print(error_msg)  # Always print errors
        print(f"SQLite version: {sqlite3.sqlite_version}")
        print(f"Python SQLite version: {sqlite3.version}")
        speak(error_msg)
        raise


def retrieve(key, buffer_id=None, fetch='last', parent_id=None):
    """Retrieve item from database.
    
    Args:
        key: The key to retrieve
        buffer_id: The buffer ID to retrieve from (uses current_buffer_id if None)
        fetch: How to fetch - 'last' for most recent entry, 'history' for all entries, 
               'all' for all entries, 'last_value' for just the value, 'list_items' for items in a list
        parent_id: For 'list_items' fetch, the ID of the parent list to retrieve items from
               
    Returns:
        The retrieved entry or entries, or None if not found
    """
    global current_buffer_id
    
    try:
        if buffer_id is None:
            buffer_id = current_buffer_id
            
        connection, cursor = connect()

        # Handle key object in a more robust way
        if hasattr(key, 'char'):  # Check for char attribute instead of isinstance
            key = key.char
            debug_print(f"Retrieved key.char: {key}")

        # Print diagnostic information
        debug_print(f"Retrieving: key={key}, buffer_id={buffer_id}, fetch={fetch}, parent_id={parent_id}")

        if fetch == 'list_items' and parent_id is not None:
            # Special query for list items, ordered by item_index
            query = "SELECT * FROM lore WHERE parent_id=? ORDER BY item_index ASC;"
            results = cursor.execute(query, (parent_id,))
            results = results.fetchall()
            debug_print(f"Fetched {len(results) if results else 0} list items")
            return results
        elif fetch == 'last_value':
            query = "SELECT value FROM lore WHERE buffer_id=? and key=?;"
        else:
            query = "SELECT * FROM lore WHERE buffer_id=? and key=?;"

        if fetch == 'last':
            query = query[:-1] + " ORDER BY id DESC LIMIT 1;"
        elif fetch == 'history':
            query = query[:-1] + " ORDER BY id DESC;"

        # Print the query and parameters for diagnostics
        debug_print(f"SQL Query: {query}")
        debug_print(f"Parameters: buffer_id={buffer_id}, key={str(key)}")
        
        results = cursor.execute(query, (buffer_id, str(key)))

        if not results:
            debug_print("No results returned from query")
            return None

        if fetch == 'all' or fetch == 'history':
            results = results.fetchall()
            debug_print(f"Fetched {len(results)} records")
        else:
            results = results.fetchone()
            debug_print(f"Fetched record: {results}")

        return results
    except Exception as e:
        print(f"Error in retrieve: {e}")  # Always print errors
        speak(f"Error retrieving data: {e}")
        return None


def store(key, value, label=None, data_type=TYPE_VALUE, buffer_id=None, parent_id=None, item_index=None):
    """Store a key-value pair in the database.
    
    Args:
        key: The key to store the value under
        value: The value to store
        label: Optional label for the value
        data_type: Type of data - TYPE_VALUE for normal values, TYPE_BUFFER for nested buffers, TYPE_LIST for lists
        buffer_id: The buffer ID to store in (uses current_buffer_id if None)
        parent_id: The ID of the parent (buffer or list) this entry belongs to
        item_index: For list items, the position in the list (0-based index)
    """
    global current_buffer_id

    if buffer_id is None:
        buffer_id = current_buffer_id
    
    # If creating a buffer and no parent specified, use current buffer as parent
    if parent_id is None and data_type == TYPE_BUFFER:
        parent_id = current_buffer_id

    connection, cursor = connect()

    cursor.execute(
        'INSERT INTO lore (data_type, value, label, key, datetime, buffer_id, parent_id, item_index) VALUES (?, ?, ?, ?, ?, ?, ?, ?);',
        (data_type, value, label, key, datetime.datetime.now(), buffer_id, parent_id, item_index)
    )
    connection.commit()
    
    # Return the ID of the inserted row
    return cursor.lastrowid


def delete_entry(entry_id):
    """Delete an entry from the database by its ID."""
    connection, cursor = connect()
    
    cursor.execute('DELETE FROM lore WHERE id = ?;', (entry_id,))
    connection.commit()
    
    return cursor.rowcount > 0  # Return True if at least one row was deleted


def default(key):
    """Default mode - base state for the application.
    Mode switching is handled at the key_handler level for all modes."""
    try:
        # Default mode doesn't process any regular key presses
        pass
    except AttributeError:
        pass


# Buffer path tracking
buffer_path = []

# Track the last retrieved key info for Control key operations
last_retrieved = {
    'value': None,      # Last retrieved value
    'key': None,        # Key that was pressed
    'buffer_id': None   # Buffer ID from which value was retrieved
}

# History tracking
history_state = {
    'active': False,    # Whether history mode is active
    'key': None,        # Key for which history is being viewed
    'buffer_id': None,  # Buffer ID in which the key exists
    'entries': [],      # List of history entries
    'current_index': 0, # Current position in history
    'global_mode': False # Whether viewing global history or key-specific history
}

# List tracking
list_state = {
    'active': False,    # Whether list mode is active
    'list_id': None,    # ID of the current list
    'key': None,        # Key associated with the list
    'buffer_id': None,  # Buffer ID containing the list
    'items': [],        # Array of list items
    'current_index': 0  # Current position in the list
}

def create_list(key, buffer_id=None):
    """Create a new list at the specified key.
    
    Args:
        key: The key where the list should be created
        buffer_id: The buffer ID (uses current_buffer_id if None)
        
    Returns:
        The ID of the new list
    """
    if buffer_id is None:
        buffer_id = current_buffer_id
        
    # Check if key exists and convert to list if it does
    entry = retrieve(key, buffer_id)
    
    if entry and entry.get('data_type') == TYPE_LIST:
        # Already a list, just return its ID
        return entry['id']
    
    # Create a new list entry
    list_id = store(key, '', label='list', data_type=TYPE_LIST, buffer_id=buffer_id, 
                   parent_id=buffer_id)
    
    # If there was a value at this key, convert it to the first item in the list
    if entry and entry.get('data_type') == TYPE_VALUE:
        # Add the existing value as first item in the list
        store(None, entry['value'], data_type=TYPE_VALUE, buffer_id=buffer_id,
             parent_id=list_id, item_index=0)
    
    return list_id

def is_key_a_list(key, buffer_id=None):
    """Check if a key contains a list in the specified buffer.
    
    Args:
        key: The key to check
        buffer_id: The buffer ID to check in (uses current_buffer_id if None)
        
    Returns:
        True if the key contains a list, False otherwise
    """
    if buffer_id is None:
        buffer_id = current_buffer_id
        
    result = retrieve(key, buffer_id=buffer_id, fetch='last')
    return result and result.get('data_type') == TYPE_LIST

def get_list_items(list_id):
    """Get all items in a list.
    
    Args:
        list_id: The ID of the list
        
    Returns:
        List of items sorted by index
    """
    return retrieve(None, parent_id=list_id, fetch='list_items')

def append_to_list(list_id, value):
    """Add an item to the end of a list.
    
    Args:
        list_id: The ID of the list
        value: The value to add
        
    Returns:
        The index of the new item
    """
    items = get_list_items(list_id)
    next_index = len(items) if items else 0
    
    # Store the new item with the next available index
    store(None, value, data_type=TYPE_VALUE, parent_id=list_id, item_index=next_index)
    return next_index

def user_index(internal_index, items_list):
    """Convert internal zero-based index to user-facing one-based index (newest = 1).
    
    Args:
        internal_index: The internal zero-based index
        items_list: The list of items
        
    Returns:
        The user-facing one-based index (newest item = 1)
    """
    if not items_list:
        return 0
    return len(items_list) - internal_index
    
def internal_index(user_index, items_list):
    """Convert user-facing one-based index to internal zero-based index.
    
    Args:
        user_index: The user-facing one-based index (newest item = 1)
        items_list: The list of items
        
    Returns:
        The internal zero-based index
    """
    if not items_list:
        return 0
    return len(items_list) - user_index

def navigate_list(direction):
    """Navigate through list entries.
    
    Args:
        direction: 'next' or 'prev' to indicate direction
        
    Returns:
        True if navigation was successful, False otherwise
    """
    global list_state
    
    if not list_state['active'] or not list_state['items']:
        speak("No list active or list is empty")
        return False
    
    items = list_state['items']
    current_index = list_state['current_index']
    
    # Safety check for index being in bounds
    if current_index < 0 or current_index >= len(items):
        # Reset to a valid index if somehow we're out of bounds
        list_state['current_index'] = len(items) - 1
        current_index = list_state['current_index']
        
    if direction == 'next' and current_index < len(items) - 1:
        # Move to next (down the list toward higher numbers)
        list_state['current_index'] += 1
        current_item = items[list_state['current_index']]
        user_idx = user_index(list_state['current_index'], items)
        speak(f"Item {user_idx} of {len(items)}: {current_item['value']}")
        return True
    elif direction == 'prev' and current_index > 0:
        # Move to previous (up the list toward item 1)
        list_state['current_index'] -= 1
        current_item = items[list_state['current_index']]
        user_idx = user_index(list_state['current_index'], items)
        speak(f"Item {user_idx} of {len(items)}: {current_item['value']}")
        return True
    elif direction == 'end':
        # Jump to end of list
        list_state['current_index'] = 0
        current_item = items[list_state['current_index']]
        user_idx = user_index(list_state['current_index'], items)
        speak(f"Last item {user_idx} of {len(items)}: {current_item['value']}")
        return True
    elif direction == 'top':
        # Jump to top of list
        list_state['current_index'] = len(items) - 1
        current_item = items[list_state['current_index']]
        speak(f"First item 1 of {len(items)}: {current_item['value']}")
        return True
    else:
        # Cannot navigate further
        if direction == 'next':
            speak("End of list")
        else:
            speak("Beginning of list")
        return False

def read_timestamp(entry):
    """Read the timestamp of an entry."""
    if not entry or 'datetime' not in entry:
        speak("No timestamp available")
        return
    
    # Format the date for better readability
    date_str = entry['datetime'].split('.')[0]  # Remove milliseconds
    
    # Speak the timestamp
    speak(f"Created on {date_str}")


def read(key):
    """Read data from a key in the current buffer."""
    global mode
    global key_presses
    global last_retrieved
    global current_buffer_id
    global history_state
    
    try:
        c = key.char
        # Create a key ID for the current key
        current_key_id = f"{current_buffer_id}:{c}"
        
        # Check if this is a Control key press for operating on the last read value
        if pressed['ctrl']:
            # Operations that require a last retrieved value
            if last_retrieved['value']:
                # Control-c: copy to clipboard and exit
                if key.char == 'c':
                    copy(last_retrieved['value'])
                    speak(f"Copied to clipboard")
                    exit()
                    
                # Control-b: browse URL in browser and exit
                elif key.char == 'b':
                    # Check if value is a URL
                    if not is_valid_url(last_retrieved['value']):
                        # If it's just a domain without protocol, add http://
                        if re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}(?:\/.*)?$', last_retrieved['value']):
                            url = "http://" + last_retrieved['value']
                            speak(f"Adding http protocol")
                        else:
                            speak("Not a valid URL")
                            return
                    else:
                        url = last_retrieved['value']
                        
                    # Open URL in browser
                    webbrowser.open(url)
                    speak(f"Opening in browser")
                    exit()
                
                # Control-t: read timestamp of the last accessed value
                elif key.char == 't':
                    # Get the full entry to access timestamp
                    result = retrieve(last_retrieved['key'], buffer_id=last_retrieved['buffer_id'])
                    if result:
                        read_timestamp(result)
                    return
            
            # Operations that require a last retrieved key (even if value is None)
            if last_retrieved['key']:
                # Control-h: view history for the last accessed key
                if key.char == 'h':
                    # Get history entries for this key
                    history_entries = retrieve(last_retrieved['key'], buffer_id=last_retrieved['buffer_id'], fetch='history')
                    
                    if not history_entries or len(history_entries) <= 1:
                        speak(f"No history for key {last_retrieved['key']}")
                        return
                    
                    # Update history state
                    history_state['active'] = True
                    history_state['key'] = last_retrieved['key']
                    history_state['buffer_id'] = last_retrieved['buffer_id']
                    history_state['entries'] = history_entries
                    history_state['current_index'] = 0  # Start with most recent entry (index 0)
                    history_state['global_mode'] = False  # This is key-specific history, not global
                    
                    # Display the current (most recent) entry
                    current_entry = history_entries[0]
                    speak(f"History for {last_retrieved['key']}, {len(history_entries)} entries. Most recent: {current_entry['value']}")
                    
                    # Switch to history mode
                    change_mode('history')
                    return
                
                # Control-y: save clipboard to the last accessed register
                elif key.char == 'y':
                    # Get clipboard data
                    data = str(paste())
                    if strip_input:
                        data = data.strip()
                    
                    # Check if we're overwriting
                    is_overwrite = False
                    if last_retrieved['value'] is not None:
                        is_overwrite = True
                    
                    # Store to the last key we interacted with
                    store(last_retrieved['key'], data, buffer_id=last_retrieved['buffer_id'])
                    
                    if is_overwrite:
                        speak(f"Overwrote key {last_retrieved['key']} with clipboard data")
                    else:
                        speak(f"Wrote clipboard data to key {last_retrieved['key']}")
                    return
                    
                # Control-g: create a buffer at the last accessed key
                elif key.char == 'g':
                    if last_retrieved['key'] is not None:
                        buffer_key = last_retrieved['key']
                        parent_buffer_id = last_retrieved['buffer_id']
                        
                        # Check if a buffer already exists at this key in the current buffer context
                        if is_key_a_buffer(buffer_key, parent_buffer_id):
                            # If a buffer already exists, just enter it
                            speak(f"Buffer already exists at {buffer_key}")
                            
                            # Create a KeyCode-like object to pass to enter_buffer
                            class KeyObj:
                                def __init__(self, char):
                                    self.char = char
                                    
                            key_obj = KeyObj(buffer_key)
                            enter_buffer(key_obj)
                            return
                        
                        # Create a new buffer
                        new_buffer_id = create_buffer_at_key(buffer_key, parent_buffer_id)
                        
                        # Add to buffer path for display
                        buffer_path.append(buffer_key)
                        buffer_name = ''.join(buffer_path)
                        
                        speak(f"Created buffer {buffer_name}")
                        
                        # Enter the new buffer
                        current_buffer_id = new_buffer_id
                        buffer_stack.append(current_buffer_id)
                        
                        return
                    else:
                        speak("Select a key first before creating a buffer")
                    return
            
            # Operations that don't require a last retrieved value or key
            # Control-o: go to options mode
            if key.char == 'o':
                change_mode('options')
                return
                
            # Control-j: read clipboard
            elif key.char == 'j':
                read_clipboard()
                return
                
            # Control-l: enter list mode for the last accessed key
            elif key.char == 'l':
                if last_retrieved['key'] is not None:
                    enter_list_mode(last_retrieved['key'], last_retrieved['buffer_id'])
                else:
                    speak("Select a key first before entering list mode")
                return
                
            return
        
        # Check if we're dealing with a buffer key
        enter = enter_buffer(key)
        if enter:
            # Stay in read mode when entering a buffer
            # Don't use return_to_read_mode here as we've already announced the buffer name
            global suppress_mode_message
            suppress_mode_message = True  # Suppress default mode message
            change_mode('read')
            # Clear key presses when entering a new buffer
            key_presses = {}
            # Reset last retrieved info
            last_retrieved = {'value': None, 'key': None, 'buffer_id': None}
            return
            
        # Get the data for this key
        result = retrieve(key, buffer_id=current_buffer_id)
        
        # Always update the last retrieved key information, even for empty registers
        # This allows writing to empty registers with Control-y
        last_retrieved['key'] = c
        last_retrieved['buffer_id'] = current_buffer_id
        
        # Check if we're switching to a different key than the last one pressed
        # If so, reset all key press counters to prevent copy-on-second behavior 
        # when returning to a previously accessed key
        last_key_pressed = None
        for existing_key_id in list(key_presses.keys()):
            if key_presses[existing_key_id] > 0:
                buf, k = existing_key_id.split(':')
                # If this key is in the current buffer and is not the current key
                if buf == str(current_buffer_id) and k != c:
                    # We've found a different key that was pressed before
                    # Clear all key press counts since we're switching keys
                    key_presses = {key_id: 0 for key_id in key_presses}
                    break
        
        # Now count this key press
        key_presses[current_key_id] = key_presses.get(current_key_id, 0) + 1
        
        if not result:
            # Still update last_retrieved but with a None value
            last_retrieved['value'] = None
            speak(f"No data at key {c}")
            return
            
        value = str(result['value'])
        
        # Update the value in last_retrieved
        last_retrieved['value'] = value
        
        # Handle differently based on data type and number of presses
        if result['data_type'] == TYPE_LIST:
            # Get list items
            items = get_list_items(result['id'])
            
            # First press - announce list info and read the newest item (item 1)
            if key_presses[current_key_id] == 1:
                if items:
                    speak(f"List with {len(items)} items. Item 1: {items[-1]['value']}")
                else:
                    speak(f"Empty list at key {c}")
            # Second consecutive press - enter list mode
            else:
                enter_list_mode(c, current_buffer_id)
        else:
            # Standard value handling
            # First press - read it out loud
            if key_presses[current_key_id] == 1:
                speak(f"{value}")
            # Second consecutive press of same key - copy to clipboard (backward compatibility)
            else:
                copy(value)
                speak(f"Copied to clipboard")
                exit()
            
    except AttributeError:
        pass


def history(key):
    """Navigate through history entries."""
    global history_state
    global mode
    global last_retrieved
    
    try:
        if key.char:
            # Control key combinations
            if pressed['ctrl']:
                # Control-p: Previous entry (older)
                if key.char == 'p':
                    navigate_history('previous')
                    return
                    
                # Control-n: Next entry (newer)
                elif key.char == 'n':
                    navigate_history('next')
                    return
                    
                # Control-z: Restore the currently selected history entry
                elif key.char == 'z':  # Changed from 'r' to 'z' to avoid conflict
                    restore_history_entry()
                    return
                    
                # Control-t: Read timestamp of current history entry
                elif key.char == 't' and history_state['entries']:
                    current_entry = history_state['entries'][history_state['current_index']]
                    read_timestamp(current_entry)
                    return
                    
                # Control-c: Copy current history entry to clipboard
                elif key.char == 'c' and history_state['entries']:
                    current_entry = history_state['entries'][history_state['current_index']]
                    copy(current_entry['value'])
                    speak(f"Copied to clipboard")
                    return
                    
                # Control-b: Browse URL in current history entry
                elif key.char == 'b' and history_state['entries']:
                    current_entry = history_state['entries'][history_state['current_index']]
                    value = current_entry['value']
                    
                    # Check if value is a URL
                    if not is_valid_url(value):
                        # If it's just a domain without protocol, add http://
                        if re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}(?:\/.*)?$', value):
                            url = "http://" + value
                            speak(f"Adding http protocol")
                        else:
                            speak("Not a valid URL")
                            return
                    else:
                        url = value
                        
                    # Open URL in browser
                    webbrowser.open(url)
                    speak(f"Opening in browser")
                    exit()
                    
                # Control-j: Read clipboard content
                elif key.char == 'j':
                    read_clipboard()
                    return
            else:
                # If any other key with character is pressed, exit history mode
                history_state['active'] = False
                history_state['global_mode'] = False
                return_to_read_mode()
                return
                
    except AttributeError:
        # Handle special keys
        if key == keyboard.Key.up:  # Up arrow key for older entries
            navigate_history('previous')
            return
            
        elif key == keyboard.Key.down:  # Down arrow key for newer entries
            navigate_history('next')
            return
            
        elif key == keyboard.Key.delete:  # Delete key to permanently remove an entry
            delete_history_entry()
            return
            
        elif key == keyboard.Key.esc:  # Escape key to exit history mode
            history_state['active'] = False
            history_state['global_mode'] = False
            return_to_read_mode()
            return
            
        # Other special keys are ignored
        if key not in [keyboard.Key.shift, keyboard.Key.ctrl, keyboard.Key.alt]:
            return


def navigate_history(direction):
    """Navigate through history entries."""
    global history_state
    
    entries = history_state['entries']
    current_index = history_state['current_index']
    global_mode = history_state['global_mode']
    
    if not entries:
        speak("No history available")
        return
    
    if direction == 'previous' and current_index < len(entries) - 1:
        # Move to older entry (higher index)
        current_index += 1
    elif direction == 'next' and current_index > 0:
        # Move to newer entry (lower index)
        current_index -= 1
    else:
        if direction == 'previous':
            speak("At oldest entry")
        else:
            speak("At newest entry")
        return
    
    # Update the current index
    history_state['current_index'] = current_index
    
    # Get the current entry
    current_entry = entries[current_index]
    total_entries = len(entries)
    
    # Format differently depending on whether we're in global or key-specific history
    if global_mode:
        speak(f"Entry {current_index + 1} of {total_entries}")
        format_global_history_entry(current_entry)
    else:
        # Speak entry information and value (without timestamp) for key-specific history
        speak(f"Entry {current_index + 1} of {total_entries}: {current_entry['value']}")


def delete_history_entry():
    """Delete the currently selected history entry."""
    global history_state
    
    if not history_state['active'] or not history_state['entries']:
        speak("No history entry to delete")
        return
    
    # Get the current entry from history
    current_index = history_state['current_index']
    entries = history_state['entries']
    global_mode = history_state['global_mode']
    
    if current_index >= len(entries):
        speak("Invalid history entry")
        return
    
    # Get the entry to delete
    entry_to_delete = entries[current_index]
    entry_id = entry_to_delete['id']
    
    # Delete the entry from the database
    success = delete_entry(entry_id)
    
    if success:
        if global_mode:
            key = entry_to_delete['key']
            buffer_id = entry_to_delete['buffer_id']
            speak(f"Deleted entry from buffer {buffer_id}, key {key}: {entry_to_delete['value']}")
        else:
            speak(f"Deleted entry: {entry_to_delete['value']}")
        
        # Remove the entry from the entries list
        entries.pop(current_index)
        
        # Update entries list
        history_state['entries'] = entries
        
        # Check if we need to adjust the current index
        if entries:
            # If we've deleted the last entry in the list, move to the previous entry
            if current_index >= len(entries):
                history_state['current_index'] = len(entries) - 1
                
            # Speak the new current entry
            new_current = entries[history_state['current_index']]
            
            if global_mode:
                speak("Now at entry")
                format_global_history_entry(new_current)
            else:
                speak(f"Now at entry: {new_current['value']}")
        else:
            # No more entries, exit history mode
            speak("No more entries")
            history_state['active'] = False
            history_state['global_mode'] = False
            return_to_read_mode()
    else:
        speak("Failed to delete entry")


def restore_history_entry():
    """Restore the currently selected history entry."""
    global history_state
    global last_retrieved
    
    if not history_state['active'] or not history_state['entries']:
        speak("No history entry to restore")
        return
    
    # Get the current entry from history
    current_index = history_state['current_index']
    entries = history_state['entries']
    
    if current_index >= len(entries):
        speak("Invalid history entry")
        return
    
    current_entry = entries[current_index]
    
    if history_state['global_mode']:
        # Get the key and buffer_id from the entry itself for global history
        key = current_entry['key']
        buffer_id_value = current_entry['buffer_id']
    else:
        # Get the key and buffer_id from history state for key-specific history
        key = history_state['key']
        buffer_id_value = history_state['buffer_id']
    
    # Store the value from the history entry to create a new entry
    value = current_entry['value']
    store(key, value, buffer_id=buffer_id_value)
    
    if history_state['global_mode']:
        speak(f"Restored to buffer {buffer_id_value}, key {key}: {value}")
    else:
        speak(f"Restored: {value}")
    
    # Exit history mode
    history_state['active'] = False
    history_state['global_mode'] = False
    return_to_read_mode()
    
    # Update last_retrieved with the restored value
    last_retrieved['value'] = value
    last_retrieved['key'] = key
    last_retrieved['buffer_id'] = buffer_id_value


def options(key):
    global strip_input
    global debug_mode

    try:
        # Toggle strip input option
        if key.char == "s":
            strip_input = not strip_input
            speak(f"Strip input {status(strip_input)}")
            
        # Toggle debug mode option
        elif key.char == "d":
            debug_mode = not debug_mode
            # Store the setting in the database for persistence
            set_config('debug_mode', 'on' if debug_mode else 'off')
            speak(f"Debug mode {status(debug_mode)}")
            
        # Return to read mode if escape is pressed
        elif key.char == "\x1b":  # Escape character
            return_to_read_mode()
            return

    except AttributeError:
        # Handle special keys
        if key == keyboard.Key.esc:  # Escape key to exit options mode
            return_to_read_mode()
            return
        pass


def read_clipboard():
    """Read the clipboard out loud."""

    speak(str(paste()))


def browse(key):
    """Open URL from stored data in the default browser."""
    
    try:
        c = key.char
        
        # Check if we're dealing with a buffer key
        enter = enter_buffer(key)
        if enter:
            # Stay in browse mode when entering a buffer
            change_mode('browse')
            return
            
        # Get the data for this key
        result = retrieve(key, buffer_id=current_buffer_id)
        if not result:
            speak(f"No data at key {c}")
            return
            
        value = str(result['value'])
        
        # Check if value is a URL
        if not is_valid_url(value):
            # If it's just a domain without protocol, add http://
            if re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}(?:\/.*)?$', value):
                value = "http://" + value
                speak(f"Adding http protocol to {value}")
            else:
                speak("Not a valid URL")
                return
                
        # Open URL in browser
        webbrowser.open(value)
        speak(f"Opening {value}")
        exit()
        
    except AttributeError:
        pass


def is_valid_url(url):
    """Check if a string is a valid URL."""
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http://, https://, ftp://, ftps://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None


def enter_buffer(key):
    """Check if the selected key contains a buffer in the current buffer, and enter it if true.
    
    A buffer is only accessible if it was explicitly created in the current buffer.
    This prevents buffer "leaking" where a buffer created in one parent is accessible from another.
    
    Args:
        key: The key that might contain a buffer
        
    Returns:
        The new buffer ID if successfully entered, False otherwise
    """
    global current_buffer_id
    global buffer_stack
    global buffer_path

    try:
        # Print debug info about key
        if hasattr(key, 'char'):
            debug_print(f"Checking if key '{key.char}' contains a buffer in current buffer {current_buffer_id}")
        else:
            debug_print(f"Checking if key '{key}' contains a buffer in current buffer {current_buffer_id}")
        
        # Check if this key contains a buffer in the current buffer
        # This is the critical check to fix buffer nesting - we need to ensure the buffer's parent
        # matches our current buffer exactly, not just any buffer with this key
        if is_key_a_buffer(key, current_buffer_id):
            # Get the buffer data
            retrieved = retrieve(key, buffer_id=current_buffer_id, fetch='last')
            new_buffer_id = retrieved['value']
            
            # Track the path to this buffer
            if hasattr(key, 'char'):
                buffer_path.append(key.char)
            else:
                buffer_path.append(str(key))
                
            # Create buffer name from path
            buffer_name = ''.join(buffer_path)
            
            speak(f"Entering buffer {buffer_name}")
            current_buffer_id = new_buffer_id
            buffer_stack.append(current_buffer_id)  # Add to navigation stack
            
            return current_buffer_id
        else:
            # Key either doesn't exist or doesn't contain a buffer in the current context
            return False
            
    except Exception as e:
        # Enhanced error handling
        print(f"Error in enter_buffer: {e}")  # Always print errors
        speak(f"Error checking for buffer: {e}")

    return False


def exit_buffer():
    """Exit current buffer and return to parent buffer.
    
    Returns:
        True if successfully exited a buffer, False if already at root buffer
    """
    global current_buffer_id
    global buffer_stack
    global buffer_path
    
    if len(buffer_stack) > 1:
        buffer_stack.pop()  # Remove current buffer from stack
        current_buffer_id = buffer_stack[-1]  # Set current to parent buffer
        
        # Update buffer path
        if buffer_path:
            buffer_path.pop()  # Remove last key from path
            
        # Get buffer name from path
        buffer_name = "root" if not buffer_path else ''.join(buffer_path)
        
        speak(f"Returning to buffer {buffer_name}")
        return True
    else:
        speak("Already at root buffer")
        return False



def clipboard(key):
    """Store data from clipboard into the currently selected key."""
    global current_buffer_id
    debug_print(key)

    try:
        c = key.char
        data = str(paste())
        
        # Check if key contains a buffer and enter it if so
        if enter_buffer(key):
            return

        debug_print(f"Current buffer ID: {current_buffer_id}")

        if strip_input:
            data = data.strip()

        # Store the clipboard data at this key in the current buffer
        store(c, data)
        speak(f"Stored {data} as {c} in buffer {get_buffer_name()}")
        
        # Return to read mode after storing instead of exiting
        return_to_read_mode()
        return
        
    except AttributeError as e:
        print(f"Error in clipboard: {e}")  # Always print errors
        pass


def format_global_history_entry(entry):
    """Format and speak a global history entry, including buffer and key information."""
    key = entry['key']
    buffer_id = entry['buffer_id']
    value = entry['value']
    
    speak(f"Buffer {buffer_id}, key {key}: {value}")


def access_global_history():
    """Access the global history of all changes across all buffers."""
    global history_state
    global mode
    
    # Only accessible from the root buffer
    if current_buffer_id != 1:
        speak("Global History only available from the root buffer")
        return False
    
    # Get all history entries
    connection, cursor = connect()
    history_entries = get_global_history(connection, cursor)
    
    if not history_entries:
        speak("No history entries available")
        return False
    
    # Update history state
    history_state['active'] = True
    history_state['key'] = None
    history_state['buffer_id'] = None
    history_state['entries'] = history_entries
    history_state['current_index'] = 0  # Start with most recent entry (index 0)
    history_state['global_mode'] = True
    
    # Announce entering global history with count
    speak(f"Global History: {len(history_entries)} entries")
    
    # Display the current (most recent) entry
    current_entry = history_entries[0]
    
    # Format the entry differently for global history to include buffer and key
    format_global_history_entry(current_entry)
    
    # Switch to history mode
    change_mode('history')
    return True


# mode_map moved to the end of file



def start():
    """Start the tome."""
    global suppress_mode_message
    global buffer_path
    global debug_mode
    global current_buffer_id
    global buffer_stack
    
    # Initialize buffer-related state
    current_buffer_id = 1  # Start in the root buffer
    buffer_stack = [1]     # Initialize navigation stack with root buffer
    buffer_path = []       # Empty buffer path (we're at root)
    
    # Load debug setting from database
    debug_setting = get_config('debug_mode', 'off')
    debug_mode = (debug_setting == 'on')
    debug_print(f"Debug mode loaded from database: {debug_mode}")
    
    # Start in read mode - suppress the initial speak since we'll do it manually
    suppress_mode_message = True
    change_mode("read")
    
    # Now speak the welcome message
    speak("Tome of lore")

    try:
        # Initialize the keyboard listener
        listener = keyboard.Listener(
            on_press=key_handler,
            on_release=release_handler,
            suppress=False
        )
        
        # Ensure compatibility with different package managers
        if not hasattr(listener, '_handle'):
            def handle_method(self, display, event, injected):
                return True
            
            from types import MethodType
            listener._handle = MethodType(handle_method, listener)
        
        listener.start()
        listener.join()
    except (ConnectionClosedError, AttributeError) as e:
        print(f"Error in keyboard listener: {e}")
        speak("Error starting keyboard listener. Please check terminal.")


def key_handler(key):
    mode_function = mode_map[mode]['function']
    debug_print(f"Current mode: {mode}")
    debug_print(f"Key pressed: {key}")

    # Handle backspace special cases for non-read modes
    if key == keyboard.Key.backspace:
        if mode == 'options':
            return_to_read_mode()
            return
        elif mode == 'history':
            history_state['active'] = False
            history_state['global_mode'] = False
            return_to_read_mode()
            return
        elif mode == 'list':
            list_state['active'] = False
            return_to_read_mode()
            return
        
    try:
        # Check for Control-Alt-v to kill all speech
        if key.char == "v" and pressed['ctrl'] and pressed['alt']:
            kill_speech()
            speak("Silenced")
            return
            
        # Global quit command
        if key.char == "q":
            speak("Quit")
            exit()
        
        # Global history access (Control-h when no key is selected in root buffer)
        if key.char == "h" and pressed['ctrl'] and mode == "read" and last_retrieved['key'] is None and current_buffer_id == 1:
            if access_global_history():
                return
        
        # All other keypresses are handled by the current mode's function
        mode_function(key)
    except AttributeError:
        debug_print(f"AttributeError handling key: {key}")
        for modifier in ['shift', 'ctrl', 'alt']:
            key_attribute = getattr(keyboard.Key, modifier)
            if key == key_attribute:
                pressed[modifier] = True

        if key == keyboard.Key.esc:
            # Return to read mode with buffer announcement when escaping
            return_to_read_mode()
        elif key == keyboard.Key.backspace and mode == 'read':
            # Only exit buffer if in read mode
            exit_buffer()
        # whitelist special keys to pass through to the mode
        if any([
                key.up,
                key.down,
                key.left,
                key.right,
                key.delete]
                ):
            mode_function(key)
            
def release_handler(key):
    for modifier in ['shift', 'ctrl', 'alt']:
        key_attribute = getattr(keyboard.Key, modifier)
        if key == key_attribute:
            pressed[modifier] = False


def get_buffer_name():
    """Get the current buffer name from buffer path."""
    if not buffer_path:
        return "root"
    return ''.join(buffer_path)


def return_to_read_mode():
    """Helper function to return to read mode with buffer name announcement."""
    buffer_name = get_buffer_name()
    # Temporarily suppress the default mode message
    global suppress_mode_message
    suppress_mode_message = True
    change_mode('read')
    # Speak custom buffer message instead
    speak(f"Returning to buffer {buffer_name}")


def change_mode(mode_name):
    """Change the mode to mode_name."""
    
    global mode
    global suppress_mode_message
    global key_presses
    
    mode_message = mode_map[mode_name]["message"]

    # Clear key presses when changing modes
    if mode_name != mode:
        key_presses = {}
    
    # Speak the new mode if the mode has changed
    if mode_name != mode and mode_message and not suppress_mode_message:
        speak(mode_message)

    suppress_mode_message = False
    mode = mode_name


def enter_list_mode(key, buffer_id=None):
    """Enter list mode for a specific key.

    Args:
        key: The key of the list to enter
        buffer_id: The buffer ID containing the list (uses current_buffer_id if None)
        
    Returns:
        True if successfully entered list mode, False otherwise
    """
    global list_state
    
    if buffer_id is None:
        buffer_id = current_buffer_id
    
    # Handle key object
    if hasattr(key, 'char'):
        key = key.char
    
    # Check if this key contains a list or can be converted to one
    entry = retrieve(key, buffer_id)
    
    if not entry:
        # Create a new empty list
        list_id = create_list(key, buffer_id)
        speak("Created new empty list")
    elif entry['data_type'] == TYPE_VALUE:
        # Convert existing value to a list
        list_id = create_list(key, buffer_id)
        items = get_list_items(list_id)
        speak(f"Converted to list with 1 item")
    elif entry['data_type'] == TYPE_LIST:
        # Already a list
        list_id = entry['id']
        items = get_list_items(list_id)
        speak(f"List with {len(items)} items")
    else:
        # Not a valid target for list mode
        speak("Cannot convert to list")
        return False
    
    # Get the list items
    items = get_list_items(list_id)
    
    # Initialize list state
    list_state['active'] = True
    list_state['list_id'] = list_id
    list_state['key'] = key
    list_state['buffer_id'] = buffer_id
    list_state['items'] = items
    
    # Start at the end of the list (most recently added item = item 1)
    last_index = len(items) - 1 if items else 0
    list_state['current_index'] = last_index
    
    # If the list has items, announce the newest item as item 1
    if items:
        speak(f"Item 1 of {len(items)}: {items[last_index]['value']}")
    else:
        speak("Empty list")
    
    # Switch to list mode
    change_mode('list')
    return True

def list_mode(key):
    """Handle keyboard input in list mode.
    
    Args:
        key: The pressed key
        
    Returns:
        True if the key was handled, False otherwise
    """

    global list_state
    
    if not list_state['active']:
        speak("List mode inactive")
        return_to_read_mode()
        return True
    
    # Handle special keys with direct comparison
    if isinstance(key, keyboard.Key):

        # Add debugging to see the key value
        debug_print(f"Special key in list mode: {key}")
        
        # Up arrow - move up toward item 1
        if key == keyboard.Key.up:
            navigate_list('next')
            return True
            
        # Down arrow - move down toward higher numbers
        if key == keyboard.Key.down:
            navigate_list('prev')
            return True
            
        # Left arrow - same as up
        if key == keyboard.Key.left:
            navigate_list('next')
            return True
            
        # Right arrow - same as down
        if key == keyboard.Key.right:
            navigate_list('prev')
            return True
        # Backspace handling
        if key == keyboard.Key.backspace:

            # Exit list mode
            list_state['active'] = False
            return_to_read_mode()
            return True
            
        # Enter key handling
        if key == keyboard.Key.enter:
            # Read current item
            if list_state['items'] and 0 <= list_state['current_index'] < len(list_state['items']):
                current_item = list_state['items'][list_state['current_index']]
                user_idx = user_index(list_state['current_index'], list_state['items'])
                speak(f"Item {user_idx} of {len(list_state['items'])}: {current_item['value']}")
            else:
                speak("List is empty")
            return True
            
        # Delete key handling
        if key == keyboard.Key.delete:
            # Not implementing delete in this first pass
            speak("Delete not implemented yet")
            return True
        return False
    
    # Handle character keys
    try:
        char = key.char
        
        # Check for Control key combinations first
        if pressed['ctrl']:
            # In Emacs, Control+n means "next line" (down)
            if char == 'n':
                # Move down (away from item 1)
                navigate_list('prev')
                return True
            # In Emacs, Control+p means "previous line" (up)
            elif char == 'p':
                # Move up (toward item 1)
                navigate_list('next')
                return True
            
        # Regular character keys
        if char == 'a':
            # Append clipboard content to end of list
            clipboard_content = paste()
            if clipboard_content:
                # Add item to end of list (which becomes the new item 1)
                append_to_list(list_state['list_id'], clipboard_content)
                
                # Update list items in state
                list_state['items'] = get_list_items(list_state['list_id'])
                
                # Move to the new item (which is at the end = item 1)
                list_state['current_index'] = len(list_state['items']) - 1
                
                speak(f"Added new item 1: {clipboard_content}")
            else:
                speak("Clipboard is empty")
            return True
        elif char == 'n' or char == 'j':
            # Next item (down the list)
            navigate_list('prev')
            return True
        elif char == 'p' or char == 'k':
            # Previous item (up the list)
            navigate_list('next')
            return True
        elif char == '.':
            # Jump to end of list (highest number)
            navigate_list('end')
            return True
        elif char == ',':
            # Jump to top of list (item 1)
            navigate_list('top')
            return True
        elif char == '?':
            # Help
            speak("List mode commands: a to add new item at top, n or j or Control-n for next (down), p or k or Control-p for previous (up), period to jump to last item, comma to jump to first item, backspace to exit")
            return True
        
    except AttributeError:
        # Key doesn't have a char attribute
        print('special')
    
    return False


# Define mode_map after all functions are defined
mode_map = {
    "default": {
        "function": default,
        "message": "Tome of Lore",
    },
    "read_clipboard": {
        "function": read_clipboard,
        "message": "Reading clipboard",
    },
    "options": {
        "function": options,
        "message": "Options: Press s for strip input, d for debug mode",
    },
    "clipboard": {
        "function": clipboard,
        "message": "Store from clipboard",
    },
    "read": {
        "function": read,
        "message": "Read from tome",
    },
    "browse": {
        "function": browse,
        "message": "Browse URL",
    },
    "history": {
        "function": history,
        "message": "Viewing history",
    },
    "list": {
        "function": list_mode,
        "message": "List mode",
    },
}


if __name__ == '__main__':
    start()
