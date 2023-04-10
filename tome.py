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


def retreive():
    """Retrieve item from database."""

    connection, cursor = connect()
    



def store(key, value, label=None, data_type="key", register=current_register):

    connection, cursor = connect()

    cursor.execute(
        'INSERT INTO lore (data_type, value, label, key, datetime) VALUES (?, ?, ?, ?, ?);',
        (data_type, value, label, key, datetime.datetime.now())
        )

    connection.commit()


def default(key):

    try:
        if key.char == "r":
            change_mode("read")
        if key.char == "c":
            change_mode("clipboard")
    except AttributeError:
        speak("special key {0} pressed".format(key))


def read(key):
    """Read data from tome to clipbaord."""
    try:
        pass
        
    except AttributeError:
        pass


def clipboard(key):
    """Store data from clipboard."""

    try:
        c = key.char
        data = str(paste())
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

    try:
        with Listener(on_press=key_handler, suppress=True) as listener:
            listener.join()
    except ConnectionClosedError:
        pass


def key_handler(key):
    mode_function = mode_map[mode]['function']

    if key.char == "q":
        speak("Quit")
        exit()    
    mode_function(key)


def change_mode(mode_name):
    """Change the mode to mode_name."""
    
    global mode
    mode_message = mode_map[mode_name]["message"]
    speak(mode_message)

    mode = mode_name



start()
