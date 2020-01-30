"""Sandbox module for replacing config file file properties with a database.
I'm hoping this will result in some much needed performance increase, especially
querrying file flags and annotations."""

import sqlite3
from sqlite3 import Error

DATABASE = ur'C:/tmp/sandbox.db'
# DATABASE = ur':memory:'


# Description
# TaskList
# Flags
# filepath
# Thumbnail path
# Thumbnail cache path
# Thumbnail cache timestamp
# User


class DBConnector(object):
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

conn = DBConnector(DATABASE)
if not conn.isValid():
    print conn.last_error()

print conn.cursor()
# print connector.connection
