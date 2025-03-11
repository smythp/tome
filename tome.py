from subprocess import call, Popen, DEVNULL
import pynput
from pynput.keyboard import Key, Listener, Controller
from pynput import keyboard
import os
import webbrowser
import re
from Xlib.error import ConnectionClosedError
import sqlite3
import datetime
from pyperclip import copy, paste
from utilities import dict_factory


current_register = 1
mode = "default"
suppress_mode_message = False
strip_input = True
register_stack = [1]  # Track register navigation hierarchy
key_presses = {}  # Track key presses for read functionality

tome_directory = os.path.dirname(__file__)
database = '/'.join([tome_directory, 'lore.db'])


pressed = {
    'shift': False,
    'ctrl': False,
    'alt': False,    
    }



def bp():
    pynput.keyboard.Listener.stop
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



def connect():
    """Connect to the database. Returns a tuple containing connection and cursor objects."""

    connection = sqlite3.connect(database)
    connection.row_factory = dict_factory

    cursor = connection.cursor()

    return connection, cursor


def retrieve(key, register=current_register, fetch='last'):
    """Retrieve item from database."""

    connection, cursor = connect()

    if isinstance(key, pynput.keyboard._xorg.KeyCode):
        key = key.char

    if fetch == 'last_value':
        query = "SELECT value FROM lore WHERE register=? and key=?;"
    else:
        query = "SELECT * FROM lore WHERE register=? and key=?;"

    if fetch == 'last':
        query = query[:-1] + " ORDER BY id DESC LIMIT 1;"


    results = cursor.execute (query,
                              (register, str(key)))

    if not results:
        return

    if fetch == 'all':
        results = results.fetchall()
    else:
        results = results.fetchone()  

    return results


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


def default(key):
    """Default mode - doesn't handle any key presses except for mode switching.
    Mode switching is now handled at the key_handler level for all modes."""
    try:
        # Default mode doesn't do anything with regular key presses
        # Control key mode switches are now handled in the global key_handler
        pass
    except AttributeError:
        pass


# choose_mode function has been replaced by direct mode switching in key_handler


# Track the last retrieved key info for Control key operations
last_retrieved = {
    'value': None,      # Last retrieved value
    'key': None,        # Key that was pressed
    'register': None    # Register from which value was retrieved
}

def read(key):
    """Read data from tome to clipboard."""
    global mode
    global key_presses
    global last_retrieved
    
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
            
            # Operations that require a last retrieved key (even if value is None)
            if last_retrieved['key']:
                # Control-y: save clipboard to the last accessed register
                if key.char == 'y':
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
            
            # Operations that don't require a last retrieved value or key
            # Control-g: create a register at the current key
            if key.char == 'g':
                # Switch to create_register mode
                change_mode('create_register')
                return
                
            # Control-o: go to options mode
            elif key.char == 'o':
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


def options(key):
    global strip_input

    try:
        if key.char == "s":
            strip_input = not strip_input
            speak(f"Strip input {status(strip_input)}")


    except AttributeError:
        pass


def create_register(key):
    """Create a new register at key location."""
    global current_register
    global register_stack
    global suppress_mode_message

    try:
        c = key.char
        new_register = new_register_index()

        # Check if key is already a register
        if enter_register(key):
            return
    
        # Store new register with parent reference
        store(c, new_register, label='register', data_type="register", 
              register=current_register, parent_register=current_register)
        speak(f"Stored register {new_register} as key {c}")
        
        # Enter the new register
        current_register = new_register
        register_stack.append(current_register)
        
        suppress_mode_message = True
        change_mode('read')  # Return to read mode after creating register
        
    except AttributeError:
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
    """Check if the selected key is a register and enter that register if true."""
    global current_register
    global register_stack

    retrieved = retrieve(key, fetch='last')

    if retrieved and retrieved.get('data_type') and retrieved.get('data_type') == 'register':
        new_register = retrieved['value']
        speak(f"Entering register {new_register}")
        current_register = new_register
        register_stack.append(current_register)  # Add to navigation stack
        
        return current_register

    return False


def exit_register():
    """Exit current register and return to parent register."""
    global current_register
    global register_stack
    
    if len(register_stack) > 1:
        register_stack.pop()  # Remove current register
        current_register = register_stack[-1]  # Set current to parent
        speak(f"Returning to register {current_register}")
        return True
    else:
        speak("Already at root register")
        return False



def clipboard(key):
    """Store data from clipboard."""
    global current_register
    print(key)

    try:

        c = key.char
        data = str(paste())

        
        if enter_register(key):
            return

        print(current_register)

        if strip_input:
            data = data.strip()

        store(c, data)
        speak(f"Stored {data} as {c} in register {str(current_register)}")
        
        # Return to read mode after storing instead of exiting
        change_mode('read')
        return
        
    except AttributeError as e:
        print(e)
        pass



mode_map = {
    "default": {
        "function": default,
        "message": "Tome of Lore",
    },
    "read_clipboard": {
        "function": read_clipboard,
        "message": "Reading clipboard",
    },
    "create_register": {
        "function": create_register,
        "message": "Add register",
    },
    "options": {
        "function": options,
        "message": "Change options",
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
}



def start():
    """Start the tome."""
    global suppress_mode_message
    
    # Start in read mode - suppress the initial speak since we'll do it manually
    suppress_mode_message = True
    change_mode("read")
    
    # Now speak the welcome message
    speak("Tome of lore")

    try:
        with Listener(on_press=key_handler, on_release=release_handler, suppress=True) as listener:
            listener.join()
    except ConnectionClosedError:
        pass


def key_handler(key):
    mode_function = mode_map[mode]['function']
    print(mode)

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
        
        # All other keypresses are handled by the current mode's function
        mode_function(key)
    except AttributeError:
        for modifier in ['shift', 'ctrl', 'alt']:
            key_attribute = getattr(keyboard.Key, modifier)
            if key == key_attribute:
                pressed[modifier] = True

        if key == keyboard.Key.esc:
            change_mode('default')
        elif key == keyboard.Key.backspace:
            exit_register()


def release_handler(key):
    for modifier in ['shift', 'ctrl', 'alt']:
        key_attribute = getattr(keyboard.Key, modifier)
        if key == key_attribute:
            pressed[modifier] = False


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