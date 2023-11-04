from inspect import currentframe, getframeinfo
from pathlib import Path
import sqlite3
import pynput
import datetime


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def current_folder():
    filename = getframeinfo(currentframe()).filename
    parent = Path(filename).resolve().parent
    return parent


def database_location():
    tome_directory = str(current_folder())
    database = '/'.join([tome_directory, 'lore.db'])
    return database


def connect():
    """Connect to the database. Returns a tuple containing connection and cursor objects."""

    connection = sqlite3.connect(database_location())
    connection.row_factory = dict_factory

    cursor = connection.cursor()

    return connection, cursor


def retrieve(key, register, fetch='last'):
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


def max_register():
    """Find the highest created register integer."""

    cursor, connection = connect()

    query = "SELECT register from lore;"
    results = cursor.execute(query)



    results = results.fetchall()

    results = [result['register'] for result in results if result['register']]


    highest_register = max(results)

    return highest_register    


def new_register_index():
    return max_register() + 1



def store(key, value, label=None, data_type="key", register=None):

    connection, cursor = connect()

    cursor.execute(
        'INSERT INTO lore (data_type, value, label, key, datetime, register) VALUES (?, ?, ?, ?, ?, ?);',
        (data_type, value, label, key, datetime.datetime.now() , register)
        )
    connection.commit()
