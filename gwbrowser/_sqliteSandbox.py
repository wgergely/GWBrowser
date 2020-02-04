"""Sandbox module for replacing config file file properties with a database.
I'm hoping this will result in some much needed performance increase, especially
querrying file flags and annotations."""

# import hashlib
import gwbrowser.common as common

import sqlite3
from sqlite3 import Error

DATABASE = ur'C:/tmp/sandbox.db'
# DATABASE = ur':memory:'

# path -- This could either be a
# [Hash] -- We no longer need to hash the filenames
# description
# tasks
# Flags
# filepath
# Thumbnail path
# Thumbnail cache path
# Thumbnail cache timestamp
# User


class AssetSettings(object):
    """Test connector class"""

    def __init__(self, database_path):
        self._connection = None
        self._exception = u''

        try:
            self._connection = sqlite3.connect(DATABASE)
        except Error as e:
            self._exception = u'# ERROR: Unable to open connection to the "{}" database file:\n-> "{}"'.format(
                database_path, e.message)

    def connection(self):
        return self._connection

    def isValid(self):
        return True if self._connection else False

    def last_error(self):
        return self._exception

    def cursor(self):
        if not self.isValid():
            return None
        return self.connection().cursor()

    def create_table(self):
        if not self.isValid():
            return

        with self.connection() as conn:
            conn.cursor().execute("""
                CREATE TABLE IF NOT EXISTS data (
                    id TEXT PRIMARY_KEY,
                    filepath TEXT,
                    description TEXT,
                    notes TEXT,
                    flags INTEGER,
                    thumbnail_path TEXT,
                    thumbnail_timestamp REAL,
                    thumbnail_hash TEXT,
                    last_user TEXT
                )""")
            # conn.cursor().execute("""PRAGMA encoding='UTF-8';""")
            # conn.commit()

    @staticmethod
    def hash(server, job, root, filepath):
        # Sequences have their own asset setting and because the sequence frames might
        # change we will use a generic name instead of the current in-out frames
        collapsed = common.is_collapsed(filepath)
        if collapsed:
            filepath = collapsed.expand(ur'\1[0]\3')
        path = filepath.replace(server, u'').strip(u'/')
        path = hashlib.md5(path.encode(u'utf-8')).hexdigest()
        return path


conn=AssetSettings(DATABASE)


if not conn.isValid():
    print conn.last_error()

conn.create_table()
