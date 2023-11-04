import pynput
from pynput.keyboard import Key, Listener, Controller
from pynput import keyboard
import os
from Xlib.error import ConnectionClosedError
import sqlite3
import datetime
from pyperclip import copy, paste
from utilities import dict_factory, current_folder, connect, retrieve, new_register_index, store
from speech import speak
from data import Lore


current_register = 1
mode = "default"
suppress_mode_message = False
strip_input = True

pressed = {
    'shift': False,
    'ctrl': False,
    'alt': False,    
    }


def bp():
    pynput.keyboard.Listener.stop
    breakpoint()


def status(boolean):
    """Return on if true, off if false."""
    return 'on' if boolean else 'off'


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
    try:
        c = key.char

        enter = enter_register(key)
        print(enter)
        if enter:
            return

        results = str(retrieve(key, register=current_register)['value'])
        
        if not results:
            return


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
    global current_register
    global suppress_mode_message
    print('again')

    try:
        c = key.char
        new_register = new_register_index()

        if enter_register(key):
            print('before return')
            return
    

        print('after return')
        store(c, new_register, label='register', data_type="register", register=current_register)
        speak(f"Stored {new_register} as key {c}")
        current_register = new_register
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

    lore = Lore(key, current_register)

    if lore and lore.register:
        new_register = lore.value
        speak(f"Entering register {new_register}")
        current_register = new_register

        return current_register

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

        store(c, data, register=current_register)
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

        if getattr(keyboard.Key, 'esc') == key:
            change_mode('default')


def release_handler(key):
    for modifier in ['shift', 'ctrl', 'alt']:
        key_attribute = getattr(keyboard.Key, modifier)
        if key == key_attribute:
            pressed[modifier] = False


def change_mode(mode_name):
    """Change the mode to mode_name."""
    
    global mode
    global suppress_mode_message
    mode_message = mode_map[mode_name]["message"]

    # Speak the new mode if the mode has changed
    if mode_name != mode and mode_message and not suppress_mode_message:
        speak(mode_message)

    suppress_mode_message = False
    

    mode = mode_name




if __name__ == '__main__':
    start()
