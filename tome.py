from subprocess import call, Popen
import pynput
from pynput.keyboard import Key, Listener
import os
from Xlib.error import ConnectionClosedError
import sqlite3
import datetime
from pyperclip import copy, paste

current_register = 1
mode = "default"
strip_input = True



def max_register():
    """Find the highest created register integer."""

    cursor, connection = connect()

    query = "SELECT register from lore;"
    results = cursor.execute(query)

    results = results.fetchall()
    results = [result[0] for result in results if result[0]]

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

    connection = sqlite3.connect('lore.db')
    cursor = connection.cursor()
    
    return connection, cursor


def retrieve(key, register=current_register, fetch='last'):
    """Retrieve item from database."""

    connection, cursor = connect()

    if isinstance(key, pynput.keyboard._xorg.KeyCode):
        key = key.char


    print(type(key))


    query = "SELECT value FROM lore WHERE register=? and key=?;"
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
      
    if results:
        results = results[0]
        return results


        



def store(key, value, label=None, data_type="key", register=current_register):

    connection, cursor = connect()

    cursor.execute(
        'INSERT INTO lore (data_type, value, label, key, datetime, register) VALUES (?, ?, ?, ?, ?, ?);',
        (data_type, value, label, key, datetime.datetime.now() , current_register)
        )

    connection.commit()


def default(key):

    try:
        default_key_map = {
            "r": "read",
            "o": "options",
            "g": "create_register",
            "c": "clipboard"
            }
        if key.char in default_key_map:
            change_mode(default_key_map[key.char])

    except AttributeError:
        pass


def read(key):
    """Read data from tome to clipboard."""
    try:
        c = key.char
        results = str(retrieve(key))
        print(results)
        copy(results)
        speak(f"Copied {results} to clipboard")
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
    try:
        c = key.char
        highest_register = new_register_index()
        store(c, None, label='register', data_type="register", register=highest_register)
        speak(f"Stored {highest_register} as key {c}")
        
    except AttributeError:
        pass


def clipboard(key):
    """Store data from clipboard."""

    try:
        c = key.char
        data = str(paste())

        if strip_input:
            data = data.strip()

        store(c, data)
        speak(f"Stored {data} as {c} in register {str(current_register)}")
        exit()
    except AttributeError:
        pass



mode_map = {
    "default": {
        "function": default,
        "message": "Tome of Lore",
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
        "message": "Clipboard",
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
        with Listener(on_press=key_handler, suppress=True) as listener:
            listener.join()
    except ConnectionClosedError:
        pass


def key_handler(key):
    mode_function = mode_map[mode]['function']
    try:
        if key.char == "q":
            speak("Quit")
            exit()
        mode_function(key)
    except AttributeError:
        if key.esc:
            change_mode('default')


def change_mode(mode_name):
    """Change the mode to mode_name."""
    
    global mode
    mode_message = mode_map[mode_name]["message"]
    speak(mode_message)

    mode = mode_name




if __name__ == '__main__':
    start()
