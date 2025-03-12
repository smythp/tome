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


current_register = 1
mode = "default"
suppress_mode_message = False
strip_input = True
debug_mode = False  # Default debug setting, will be overridden by database
register_stack = [1]  # Track register navigation hierarchy
key_presses = {}  # Track key presses for read functionality

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



def max_register():
    """Find the highest created register integer."""

    connection, cursor = connect()

    query = "SELECT register from lore;"
    results = cursor.execute(query)
    results = results.fetchall()

    results = [result['register'] for result in results if result['register']]

    if not results:
        return 0  # Return 0 if no registers exist yet
    
    highest_register = max(results)
    return highest_register


def new_register_index():
    return max_register() + 1


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
                    register INTEGER,
                    parent_register INTEGER
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


def retrieve(key, register=current_register, fetch='last'):
    """Retrieve item from database."""
    try:
        connection, cursor = connect()

        # Handle key object in a more robust way
        if hasattr(key, 'char'):  # Check for char attribute instead of isinstance
            key = key.char
            debug_print(f"Retrieved key.char: {key}")

        # Print diagnostic information
        debug_print(f"Retrieving: key={key}, register={register}, fetch={fetch}")

        if fetch == 'last_value':
            query = "SELECT value FROM lore WHERE register=? and key=?;"
        else:
            query = "SELECT * FROM lore WHERE register=? and key=?;"

        if fetch == 'last':
            query = query[:-1] + " ORDER BY id DESC LIMIT 1;"
        elif fetch == 'history':
            query = query[:-1] + " ORDER BY id DESC;"

        # Print the query and parameters for diagnostics
        debug_print(f"SQL Query: {query}")
        debug_print(f"Parameters: register={register}, key={str(key)}")
        
        results = cursor.execute(query, (register, str(key)))

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


def store(key, value, label=None, data_type="key", register=None, parent_register=None):
    global current_register

    if not register:
        register = current_register
    
    if parent_register is None and data_type == "register":
        parent_register = current_register

    connection, cursor = connect()

    if data_type == "register":
        cursor.execute(
            'INSERT INTO lore (data_type, value, label, key, datetime, register, parent_register) VALUES (?, ?, ?, ?, ?, ?, ?);',
            (data_type, value, label, key, datetime.datetime.now(), register, parent_register)
            )
    else:
        cursor.execute(
            'INSERT INTO lore (data_type, value, label, key, datetime, register, parent_register) VALUES (?, ?, ?, ?, ?, ?, ?);',
            (data_type, value, label, key, datetime.datetime.now(), register, None)
            )
    connection.commit()


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
    'register': None    # Register from which value was retrieved
}

# History tracking
history_state = {
    'active': False,    # Whether history mode is active
    'key': None,        # Key for which history is being viewed
    'register': None,   # Register in which the key exists
    'entries': [],      # List of history entries
    'current_index': 0, # Current position in history
    'global_mode': False # Whether viewing global history or key-specific history
}

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
    """Read data from tome to clipboard."""
    global mode
    global key_presses
    global last_retrieved
    global current_register
    global history_state
    
    try:
        c = key.char
        # Create a key ID for the current key
        current_key_id = f"{current_register}:{c}"
        
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
                    result = retrieve(last_retrieved['key'], register=last_retrieved['register'])
                    if result:
                        read_timestamp(result)
                    return
            
            # Operations that require a last retrieved key (even if value is None)
            if last_retrieved['key']:
                # Control-h: view history for the last accessed key
                if key.char == 'h':
                    # Get history entries for this key
                    history_entries = retrieve(last_retrieved['key'], register=last_retrieved['register'], fetch='history')
                    
                    if not history_entries or len(history_entries) <= 1:
                        speak(f"No history for key {last_retrieved['key']}")
                        return
                    
                    # Update history state
                    history_state['active'] = True
                    history_state['key'] = last_retrieved['key']
                    history_state['register'] = last_retrieved['register']
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
                    store(last_retrieved['key'], data, register=last_retrieved['register'])
                    
                    if is_overwrite:
                        speak(f"Overwrote register {last_retrieved['key']} with clipboard data")
                    else:
                        speak(f"Wrote clipboard data to register {last_retrieved['key']}")
                    return
                    
                # Control-g: create a buffer at the last accessed key
                elif key.char == 'g':
                    if last_retrieved['key'] is not None:
                        # Check if a buffer already exists at this key
                        existing_register = retrieve(last_retrieved['key'], register=last_retrieved['register'])
                        if existing_register and existing_register.get('data_type') == 'register':
                            # If a buffer already exists, just enter it
                            buffer_key = last_retrieved['key']
                            # Reset buffer path (this is for direct creation, not navigation)
                            buffer_path.append(buffer_key)
                            buffer_name = ''.join(buffer_path)
                            speak(f"Buffer already exists at {buffer_key}")
                            enter_register(buffer_key)
                            return
                            
                        # Create a new register/buffer
                        new_buffer_id = new_register_index()
                        
                        # Current path plus the new key
                        new_key = last_retrieved['key']
                        buffer_path.append(new_key)
                        buffer_name = ''.join(buffer_path)
                        
                        # Store buffer with parent reference
                        store(new_key, new_buffer_id, label='buffer', data_type="register", 
                              register=last_retrieved['register'], parent_register=last_retrieved['register'])
                        speak(f"Created buffer {buffer_name}")
                        
                        # Enter the new buffer
                        current_register = new_buffer_id
                        register_stack.append(current_register)
                        
                        return
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
                
            return
        
        # Check if we're dealing with a register key
        enter = enter_register(key)
        if enter:
            # Stay in read mode when entering a register
            # Don't use return_to_read_mode here as we've already announced the buffer name
            global suppress_mode_message
            suppress_mode_message = True  # Suppress default mode message
            change_mode('read')
            # Clear key presses when entering a new register
            key_presses = {}
            # Reset last retrieved info
            last_retrieved = {'value': None, 'key': None, 'register': None}
            return
            
        # Get the data for this key
        result = retrieve(key, register=current_register)
        
        # Always update the last retrieved key information, even for empty registers
        # This allows writing to empty registers with Control-y
        last_retrieved['key'] = c
        last_retrieved['register'] = current_register
        
        # Check if we're switching to a different key than the last one pressed
        # If so, reset all key press counters to prevent copy-on-second behavior 
        # when returning to a previously accessed key
        last_key_pressed = None
        for existing_key_id in list(key_presses.keys()):
            if key_presses[existing_key_id] > 0:
                reg, k = existing_key_id.split(':')
                # If this key is in the current register and is not the current key
                if reg == str(current_register) and k != c:
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
            register = entry_to_delete['register']
            speak(f"Deleted entry from register {register}, key {key}: {entry_to_delete['value']}")
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
        # Get the key and register from the entry itself for global history
        key = current_entry['key']
        register = current_entry['register']
    else:
        # Get the key and register from history state for key-specific history
        key = history_state['key']
        register = history_state['register']
    
    # Store the value from the history entry to create a new entry
    value = current_entry['value']
    store(key, value, register=register)
    
    if history_state['global_mode']:
        speak(f"Restored to register {register}, key {key}: {value}")
    else:
        speak(f"Restored: {value}")
    
    # Exit history mode
    history_state['active'] = False
    history_state['global_mode'] = False
    return_to_read_mode()
    
    # Update last_retrieved with the restored value
    last_retrieved['value'] = value
    last_retrieved['key'] = key
    last_retrieved['register'] = register


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
        
        # Check if we're dealing with a register key
        enter = enter_register(key)
        if enter:
            # Stay in browse mode when entering a register
            change_mode('browse')
            return
            
        # Get the data for this key
        result = retrieve(key, register=current_register)
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


def enter_register(key):
    """Check if the selected key is a register and enter that buffer if true."""
    global current_register
    global register_stack
    global buffer_path

    try:
        # Print debug info about key
        if hasattr(key, 'char'):
            debug_print(f"Checking if key '{key.char}' is a register")
        else:
            debug_print(f"Checking if key '{key}' is a register")
            
        retrieved = retrieve(key, fetch='last')

        if retrieved and retrieved.get('data_type') and retrieved.get('data_type') == 'register':
            new_register = retrieved['value']
            
            # Track the path to this buffer
            if hasattr(key, 'char'): # Check attr instead of isinstance for more reliable operation
                buffer_path.append(key.char)
            else:
                buffer_path.append(str(key))
                
            # Create buffer name from path
            buffer_name = ''.join(buffer_path)
            
            speak(f"Entering buffer {buffer_name}")
            current_register = new_register
            register_stack.append(current_register)  # Add to navigation stack
            
            return current_register
    except Exception as e:
        # Enhanced error handling
        print(f"Error in enter_register: {e}")  # Always print errors
        speak(f"Error checking register: {e}")

    return False


def exit_register():
    """Exit current buffer and return to parent buffer."""
    global current_register
    global register_stack
    global buffer_path
    
    if len(register_stack) > 1:
        register_stack.pop()  # Remove current register
        current_register = register_stack[-1]  # Set current to parent
        
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
    """Store data from clipboard."""
    global current_register
    debug_print(key)

    try:

        c = key.char
        data = str(paste())

        
        if enter_register(key):
            return

        debug_print(current_register)

        if strip_input:
            data = data.strip()

        store(c, data)
        speak(f"Stored {data} as {c} in register {str(current_register)}")
        
        # Return to read mode after storing instead of exiting
        return_to_read_mode()
        return
        
    except AttributeError as e:
        print(f"Error in clipboard: {e}")  # Always print errors
        pass


def format_global_history_entry(entry):
    """Format and speak a global history entry, including register and key information."""
    key = entry['key']
    register = entry['register']
    value = entry['value']
    
    speak(f"Register {register}, key {key}: {value}")


def access_global_history():
    """Access the global history of all changes across all registers."""
    global history_state
    global mode
    
    # Only accessible from the main register
    if current_register != 1:
        speak("Global History only available from the main buffer")
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
    history_state['register'] = None
    history_state['entries'] = history_entries
    history_state['current_index'] = 0  # Start with most recent entry (index 0)
    history_state['global_mode'] = True
    
    # Announce entering global history with count
    speak(f"Global History: {len(history_entries)} entries")
    
    # Display the current (most recent) entry
    current_entry = history_entries[0]
    
    # Format the entry differently for global history to include register and key
    format_global_history_entry(current_entry)
    
    # Switch to history mode
    change_mode('history')
    return True


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
}



def start():
    """Start the tome."""
    global suppress_mode_message
    global buffer_path
    global debug_mode
    
    # Initialize buffer path to empty list
    buffer_path = []
    
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
            suppress=True
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
        
        # Global history access (Control-h when no key is selected in main register)
        if key.char == "h" and pressed['ctrl'] and mode == "read" and last_retrieved['key'] is None and current_register == 1:
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
            # Only exit register if in read mode
            exit_register()


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




if __name__ == '__main__':
    start()
