"""Sandbox module for replacing config file file properties with a database.
I'm hoping this will result in some much needed performance increase, especially
querrying file flags and annotations."""

from contextlib import contextmanager
import gwbrowser.common as common
from PySide2 import QtCore
import time
import platform
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
        if not QtCore.QFileInfo(database_path).dir().mkpath(u'.'):
            self._exception = u'Unable to create database dir\n"{}"'.format(
                database_path)
            return

        try:
            self._connection = sqlite3.connect(
                database_path, isolation_level=None)
            self._connection.execute(u'pragma journal_mode=wal;')
            self._connection.execute(u'pragma synchronous=OFF;')
        except Error as e:
            self._exception = u'Unable to connect to the database at "{}"\n-> "{}"'.format(
                database_path, e.message)
            return

    def _get_id(self, filepath):
        collapsed = common.is_collapsed(filepath)
        if collapsed:
            filepath = collapsed.expand(ur'\1[0]\3')
        filepath = filepath.lower().replace(self._server, u'').strip(u'/')
        return filepath

    @contextmanager
    def transaction_contextmanager(self):
        """Simple context manager for controlling transactions.
        We're explicitly calling `BEGIN` before the `execute()`. We also roll
        changes back if an error has been encountered.

        """
        self._connection.execute('BEGIN')
        try:
            yield
        except:
            self._connection.rollback()
            raise
        else:
            self._connection.commit()

    def connection(self):
        return self._connection

    def isValid(self):
        return True if self._connection else False

    def last_error(self):
        return self._exception

    def init_tables(self):
        """Initialises the database with the default tables.

        The  `data` table stores file information of items inside the bookmark,
        whilst `info` contains information about the database itself.

        """
        if not self.isValid():
            return
        with self.transaction_contextmanager():
            # Main ``data`` table
            self._connection.cursor().execute("""
                CREATE TABLE IF NOT EXISTS data (
                    path TEXT PRIMARY KEY COLLATE NOCASE,
                    description TEXT,
                    notes TEXT,
                    flags INTEGER,
                    thumbnail_path TEXT,
                    thumbnail_timestamp REAL,
                    thumbnail_hash TEXT,
                    user TEXT
                )
            """)
            # Single-row ``info`` table
            self._connection.cursor().execute("""
                CREATE TABLE IF NOT EXISTS info (
                    path TEXT PRIMARY KEY COLLATE NOCASE,
                    server TEXT NOT NULL,
                    job TEXT NOT NULL,
                    root TEXT NOT NULL,
                    user TEXT NOT NULL,
                    host TEXT NOT NULL,
                    created REAL NOT NULL
                )
            """)
            # Adding info data to the ``info`` table
            self._connection.execute("""
            INSERT OR IGNORE INTO info
                (path, server, job, root, user, host, created)
            VALUES
                ('{path}', '{server}', '{job}', '{root}', '{user}', '{host}', '{created}')
            """.format(
                path=self._bookmark,
                server=self._server,
                job=self._job,
                root=self._root,
                user=common.get_username(),
                host=platform.node(),
                created=time.time(),
            ))

    def value(self, path, key):
        cursor = self._connection.cursor()
        cursor.execute("""SELECT {key} FROM data WHERE path='{path}'""".format(
            key=key,
            path=self._get_id(path)))
        # cursor.execute("""SELECT description FROM data WHERE path='job/root/testfolder/testfile.ma1'""".format(
        #     key='description'))
        # cursor.execute('BEGIN')
        print cursor.fetchall()

    def setValue(self, path, key, value):
        """Sets a value to the database.

        Pass the full the file or folder path including the server, job and root. The database uses the relative path as the row id, which is
        returned by `_get_id()`. The method will update existing row, or create
        a new one if the row id does not exists yet.

        Note:
            The method does NOT commit the transaction!

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


if __name__ == '__main__':
    bookmark_db = BookmarkDatabase(
        index=QtCore.QModelIndex(),
        server='C:/tmp',
        job='job',
        root='root',
    )
    if not bookmark_db.isValid():
        print bookmark_db.last_error()
    bookmark_db.init_tables()

    with bookmark_db.transaction_contextmanager():
        for n in xrange(1000):
            bookmark_db.setValue(
                ur'C:/tmp/job/root/testfolder/testfile.ma{}'.format(n), u'description', u'test description{}'.format(n))
            bookmark_db.setValue(
                ur'C:/tmp/job/root/testfolder/testfile.ma{}'.format(n), u'notes', u'test note')
    # with bookmark_db.transaction_contextmanager():
    bookmark_db.value(ur'C:/tmp/job/root/testfolder/testfile.ma123', u'description')
