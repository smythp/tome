from subprocess import call, Popen
import pynput
from pynput.keyboard import Key, Listener, Controller
from pynput import keyboard
import os
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

def speak(text_to_speak, speed=270, asynchronous=True):
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

    c = key.char

    try:
        key_map = {
            "r": "read",
            "o": "options",
            "g": "create_register",
            "c": "clipboard",
            "C": "read_clipboard"
            }

        no_input = [
            "read_clipboard",
            ]

        action = key_map.get(c)

        if action in no_input:
            mode_map[action]['function']()
        else:
            choose_mode(key.char, key_map)


    except AttributeError:
        pass


def choose_mode(char, key_map):
    """Given a key and key map, choose a mode and change to it. Handles modifier keys."""

    if pressed['shift']:

        key_map = {key.lower(): key_map[key] for key in key_map if key.isupper()}
    else:
        key_map = {key: key_map[key] for key in key_map if key.islower()}
    char = char.lower()

    if char in key_map:

        change_mode(key_map[char])
        return True
    return False



def read(key):
    """Read data from tome to clipboard."""
    global mode
    global key_presses
    
    try:
        c = key.char
        
        # Check if we're dealing with a register key
        enter = enter_register(key)
        if enter:
            # Stay in read mode when entering a register
            change_mode('read')
            # Clear key presses when entering a new register
            key_presses = {}
            return
            
        # Get the data for this key
        result = retrieve(key, register=current_register)
        if not result:
            speak(f"No data at key {c}")
            return
            
        # Store the key press to recognize repeated presses
        key_id = f"{current_register}:{c}"
        key_presses[key_id] = key_presses.get(key_id, 0) + 1
        
        value = str(result['value'])
        
        # First press - read it out loud
        if key_presses[key_id] == 1:
            speak(f"{value}")
        # Second press - copy to clipboard and exit
        else:
            copy(value)
            speak(f"Copied {value} to clipboard")
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
        change_mode('default')        
        
    except AttributeError:
        pass


def read_clipboard():
    """Read the clipboard out loud."""

    speak(str(paste()))


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
        exit()
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
        "message": "{str(paste())} in clipboard",
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
}



def start():
    """Start the tome."""
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
        if key.char == "q":
            speak("Quit")
            exit()
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
