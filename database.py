import sqlite3
import logging

logger = logging.getLogger(__name__)

conn = sqlite3.connect('toru.db')
cursor = conn.cursor()
logger.info('Database connection established')

# cursor.execute("CREATE TABLE USERS (name TEXT PRIMARY KEY, scannname TEXT)")
# cursor.execute("CREATE TABLE SERIES (sheet_name TEXT, name TEXT PRIMARY KEY)")
# conn.commit()

def add_user(name: str, scannname: str):
    cursor.execute("INSERT OR REPLACE INTO USERS (name, scannname) VALUES (?, ?)", (name, scannname))
    conn.commit()
    logger.info(f'Added/Updated user: {name} -> {scannname}')

def get_user_scannname(name: str) -> str|None:
    cursor.execute("SELECT scannname FROM USERS WHERE name = ?", (name,))
    result = cursor.fetchone()
    scannname = result[0] if result else None
    logger.debug(f'Retrieved scannname for {name}: {scannname}')
    return scannname

def add_series(sheet_name: str, name: str):
    """Map an alias `name` to a worksheet title `sheet_name`."""
    normalized_name = name.strip().title()
    cursor.execute("INSERT OR REPLACE INTO SERIES (sheet_name, name) VALUES (?, ?)", (sheet_name, normalized_name))
    conn.commit()
    logger.info(f'Added/Updated series alias: {normalized_name} -> {sheet_name}')

def get_series_by_name(name: str) -> str|None:
    """Return the worksheet title for the given alias `name`, or None."""
    normalized_name = name.strip().title()
    cursor.execute("SELECT sheet_name FROM SERIES WHERE name = ?", (normalized_name,))
    result = cursor.fetchone()
    sheet_name = result[0] if result else None
    logger.debug(f'Retrieved sheet_name for {normalized_name}: {sheet_name}')
    return sheet_name