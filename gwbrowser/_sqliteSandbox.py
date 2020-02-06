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


class BookmarkDatabase(QtCore.QObject):
    def __init__(self, index=QtCore.QModelIndex(), server=None, job=None, root=None, parent=None):
        super(BookmarkDatabase, self).__init__(parent=parent)
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
        except Error as e:
            self._exception = u'Unable to connect to the database at "{}"\n-> "{}"'.format(
                database_path, e.message)
            return

    def id(self, val):
        """Returns the database ID based on the given value."""
        if isinstance(val, int):
            return val
        collapsed = common.is_collapsed(val)
        if collapsed:
            val = collapsed.expand(ur'\1[0]\3')
        val = val.replace(self._server, u'').strip(u'/')
        return hash(val)

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
                    id INTEGER PRIMARY KEY NOT NULL,
                    /* File's relative path is used as the ID*/
                    description TEXT,
                    notes TEXT,
                    flags INTEGER,
                    thumbnail_stamp REAL,
                    user TEXT
                )
            """)
            # Single-row ``info`` table
            self._connection.cursor().execute("""
                CREATE TABLE IF NOT EXISTS info (
                    id TEXT PRIMARY KEY COLLATE NOCASE,
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
                (id, server, job, root, user, host, created)
            VALUES
                ('{id}', '{server}', '{job}', '{root}', '{user}', '{host}', '{created}')
            """.format(
                id=self._bookmark,
                server=self._server,
                job=self._job,
                root=self._root,
                user=common.get_username(),
                host=platform.node(),
                created=time.time(),
            ))

    def value(self, id, key, table=u'data'):
        """Returns a single value from the `bookmark.db`.

        Args:
            id (string or int): The database key.
            key (string): The data key to return.
            table (string): Optional table parameter, defaults to 'data'.

        Returns:
            type: Description of returned object.

        """
        _cursor = self._connection.cursor()
        _cursor.execute("""SELECT {key} FROM {table} WHERE id='{id}'""".format(
            table=table,
            key=key,
            id=self.id(id)))

        res = _cursor.fetchone()
        if not res:
            return None
        return res[0]

    def values(self, table=u'data'):
        """Returns all values from the `bookmark.db` of the given table.

        Args:
            table (string): Optional table parameter, defaults to 'data'.

        Returns:
            dict: The structured database data.

        """
        _cursor = self._connection.cursor()
        _cursor.execute("""SELECT * FROM {table}""".format(table=table))

        # Let's wrap the retrevied data into a more pythonic directory
        _data = _cursor.fetchall()
        data = {}
        for v in _data:
            data[v[0]] = {
                u'description': v[1],
                u'notes': v[2],
                u'flags': v[3],
                u'thumbnail_stamp': v[4],
                u'user': v[5],
            }
        return data


    def setValue(self, id, key, value):
        """Sets a value to the database.

        Pass the full the file or folder path including the server, job and root. The database uses the relative path as the row id, which is
        returned by `id()`. The method will update existing row, or create
        a new one if the row id does not exists yet.

        Note:
            The method does NOT commit the transaction!

        Args:
            id (unicode or int): Row id.
            key (unicode): A database column name.
            value (unicode or float): The value to set.

        """
        if not self.isValid():
            return

        self._connection.execute("""
        INSERT INTO data(id, {key}) VALUES('{id}','{value}')
          ON CONFLICT(id) DO UPDATE SET {key}=excluded.{key};
        """.format(
            id=self.id(id),
            key=key,
            value=value
        ))


if __name__ == '__main__':
    bookmark_db = BookmarkDatabase(
        index=QtCore.QModelIndex(),
        server=u'C:/tmp',
        job=u'job',
        root=u'root',
    )
    if not bookmark_db.isValid():
        print bookmark_db.last_error()
    bookmark_db.init_tables()

    x = 1000

    # #####################
    t = time.time()
    with bookmark_db.transaction_contextmanager():
        for n in xrange(x):
            id = bookmark_db.id(ur'job/root/testfolder/testfile.ma{}'.format(n))
            bookmark_db.setValue(id, u'description', u'test description{}'.format(n))
            bookmark_db.setValue(id, u'notes', u'testnote{}'.format(n))
    print '`setValue()` took', time.time() - t, '(x{})'.format(n), '\n'
    # #####################
    t = time.time()
    with bookmark_db.transaction_contextmanager():
        for n in xrange(x):
            id = bookmark_db.id(ur'job/root/testfolder/testfile.ma{}'.format(n))
            v = bookmark_db.value(id, u'description')
    print '`value()` took', time.time() - t, '\n'
    ######################
    t = time.time()
    data = bookmark_db.values()
    for n in xrange(x):
        id = bookmark_db.id(ur'job/root/testfolder/testfile.ma{}'.format(n))
        v = data[id]['description']
    print '`values()` took', time.time() - t, '\n'
