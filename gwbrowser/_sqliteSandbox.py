"""Sandbox module for replacing config file file properties with a database.
I'm hoping this will result in some much needed performance increase, especially
querrying file flags and annotations."""

import gwbrowser.common as common
from PySide2 import QtCore
import hashlib
import sqlite3
from sqlite3 import Error


class BookmarkDatabase(object):
    def __init__(self, index=QtCore.QModelIndex(), server=None, job=None, root=None, parent=None):
        self._connection = None
        self._exception = u''

        if index.isValid():
            parents = index.data(common.ParentPathRole)
            if not parents:
                raise RuntimeError(
                    u'Index does not contain a valid parent path information')
            server, job, root = parents[0:3]

        self._server = server.lower()
        self._job = job.lower()
        self._root = root.lower()
        self._bookmark = u'{}/{}/{}'.format(server, job, root).lower()

        database_path = u'{server}/{job}/{root}/.browser/bookmark.db'.format(
            server=self._server,
            job=self._job,
            root=self._root
        )

        # Let's make sure the parent folder is created first, otherwise
        # we won't be able to create the database file.
        if not QtCore.QFileInfo(database_path).dir().mkpath('.'):
            self._exception = u'Unable to create database dir\n"{}"'.format(database_path)
            return

        try:
            self._connection = sqlite3.connect(database_path, isolation_level=u'DEFERRED')
        except Error as e:
            self._exception = u'Unable to connect to the database at "{}"\n-> "{}"'.format(
                database_path, e.message)
            return

    def value(self, path, key):
        with self.connection() as conn:
            conn.execute()

    def _get_id(self, filepath):
        collapsed = common.is_collapsed(filepath)
        if collapsed:
            filepath = collapsed.expand(ur'\1[0]\3')
        filepath = filepath.lower().replace(self._server, u'').strip(u'/')
        return filepath

    def setValue(self, path, key, value, commit=False):
        """Sets a value to the database.

        Pass the full the file or folder path including the server, job and root. The database uses the relative path as the row id, which is
        returned by `_get_id()`. The method will update existing row, or create
        a new one if the row id does not exists yet.

        Note:
            The method does NOT commit the transaction by default.

        Args:
            path (unicode): A file path.
            key (unicode): A database column name.
            value (unicode or float): The value to set.

        """
        if not self.isValid():
            return

        self._connection.execute("""
        INSERT INTO data(path, {key}) VALUES('{path}','{value}')
          ON CONFLICT(path) DO UPDATE SET {key}=excluded.{key};
        """.format(
            path=self._get_id(path),
            key=key,
            value=value
        ))
        if commit:
            self._connection.commit()

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
                    path TEXT PRIMARY KEY COLLATE NOCASE,
                    description TEXT,
                    notes TEXT,
                    flags INTEGER,
                    thumbnail_path TEXT,
                    thumbnail_timestamp REAL,
                    thumbnail_hash TEXT,
                    last_user TEXT
                )""")
            conn.commit()



bookmark_db = BookmarkDatabase(
    index=QtCore.QModelIndex(),
    server='C:/tmp',
    job='job',
    root='root',
)

if not bookmark_db.isValid():
    print bookmark_db.last_error()

bookmark_db.create_table()


for n in xrange(200000):
    bookmark_db.setValue(ur'C:/tmp/job/root/testfolder/testfile.ma{}'.format(n * 2), 'description', 'test description!!')
    bookmark_db.setValue(ur'C:/tmp/job/root/testfolder/testfile.ma{}'.format(n * 2), 'notes', 'test note')
bookmark_db.connection().commit()
