from subprocess import call, Popen
import pynput
from pynput.keyboard import Key, Listener
import os
from sys import argv
import socket
from Xlib.error import ConnectionClosedError


listener = None



mode = 'default'


pressed_keys = [[]]


def speak(text_to_speak, speed=270, asynchronous=True):
    if asynchronous:
        Popen(["espeak",f"-s{speed} -ven+18 -z",text_to_speak])
    else:
        call(["espeak",f"-s{speed} -ven+18 -z",text_to_speak])


def default(key):

    try:
        # speak('alphanumeric key {0} pressed'.format(
        #     key.char))
        if key.char == 'r':
            change_mode('record')
        if key.char == 'q':
            speak('Quit')
            exit()
    except AttributeError:
        speak('special key {0} pressed'.format(
            key))


def on_pressx(key):
    if key != Key.enter and key != Key.shift and key != Key.shift_r:
        if key == Key.space:
            pressed_keys.append([])
            
        elif key != Key.backspace:
            os.system("cls")
            
            pressed_keys[-1].append(key)

            print_keys(pressed_keys)
            
        else:
            try:
                if not len(pressed_keys[-1]):
                    pressed_keys.pop()
                    
                pressed_keys[-1].pop()
            except:
                pass

        os.system("cls")

        print_keys(pressed_keys)


def record(key):
    """Handle keys in record mode."""
    try:
        if key.char == 'q':
            speak('Quit')
            exit()

        # Store some shit
        key.char
    except AttributeError:
        speak('special key {0} pressed'.format(
            key), asynchronous=False)


mode_map = {
    'default': {
        "function": default,
        "message": "Tome of Lore",
        },
    'record': {
        "function": record,
        "message": "Record",
        },
}




def start():
    """Start the tome."""

    change_mode('default')


def change_mode(mode_name):
    """Change the mode to mode_name."""
    global listener

    mode_message = mode_map[mode_name]['message']
    speak(mode_message)

    mode_function = mode_map[mode_name]['function']

    try:
        if listener == None:  
            with Listener(on_press=mode_function, suppress=True) as listener:
                listener.join()
    except ConnectionClosedError:
        pass

start()        
