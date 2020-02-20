# -*- coding: utf-8 -*-

"""SQLite based database used to store file information associated with
a bookmark.

The database stores it's values in
"""

import hashlib
from contextlib import contextmanager
import gwbrowser.common as common
from PySide2 import QtCore
import time
import platform
import sqlite3
from sqlite3 import Error


SERVER_TABLE_KEYS = (u'server', u'job', u'root', u'user', u'host')
DATA_TABLE_KEYS = (u'description', u'notes', u'flags',
                   u'thumbnail_stamp', u'user')

_DB_CONNECTIONS = {}
"""We will store our db connection instances here. They will be created per thread."""


def get_db(index, server=None, job=None, asset=None):
    """Helper function to return the bookmark database connection associated
    with an index. We will create the connection if it doesn't exists yet.
    Connection instances cannot be shared between threads hence we will
    create each instance _per thread_.

    Args:
        index (QModelIndex): A valid QModelIndex()

    Returns:
        BookmarkDB: A BookmarkDB instance that lives in the current thread.

    """
    global _DB_CONNECTIONS
    thread_id = unicode(QtCore.QThread.currentThread())

    if not index.isValid():
        if not all((server, job, root)):
            raise ValueError(u'Must provide valid server, job, and root')
        args = (server, job, root)
    else:
        args = index.data(common.ParentPathRole)[0:3]

    k = u'/'.join(args).lower() + thread_id
    if k not in _DB_CONNECTIONS:
        try:
            _DB_CONNECTIONS[k] = BookmarkDB(*args)
        except RuntimeError:
            return None
    return _DB_CONNECTIONS[k]


def reset():
    global _DB_CONNECTIONS
    for v in _DB_CONNECTIONS.itervalues():
        v.deleteLater()
    _DB_CONNECTIONS = {}


class BookmarkDB(QtCore.QObject):
    def __init__(self, server, job, root, parent=None):
        super(BookmarkDB, self).__init__(parent=parent)
        self._connection = None
        self._server = server.lower().encode(u'utf-8')
        self._job = job.lower().encode(u'utf-8')
        self._root = root.lower().encode(u'utf-8')
        self._bookmark = server + u'/' + job + u'/' + root
        self._database_path = u'{server}/{job}/{root}/.bookmark/bookmark.db'.format(
            server=self._server,
            job=self._job,
            root=self._root
        )

        # Let's make sure the parent folder is created first, otherwise
        # we won't be able to create the database file.
        if not QtCore.QFileInfo(self._database_path).dir().mkpath(u'.'):
            raise RuntimeError(u'Unable to create database dir\n"{}"'.format(
                self._database_path))

        try:
            self._connection = sqlite3.connect(
                self._database_path,
                isolation_level=None,
                check_same_thread=False
            )
            self.init_tables()

            # I don't know if this is needed, but we should try to close the
            # DB connection when the instance is deleted
            self.destroyed.connect(self._connection.close)

        except Error as e:
            raise RuntimeError(u'Unable to connect to the database at "{}"\n-> "{}"'.format(
                self._database_path, e.message))

    def _row_id(self, k):
        """Pass a valid filepath to retrieve database row number of the given
        file. This should be a path wihtout any dynamic sequence numbers as
        these do change over time, for instance when a sequence range increases.

        Args:
            k (unicode or int):  The key to use to store the data, usually filepath.

        Returns:
            int: The hashed value of `val`.

        """
        k = k.lower().encode(u'utf-8')
        k = k.replace(u'\\'.encode(u'utf-8'), u'/'.encode(u'utf-8'))
        if self._server in k:
            k = k[len(self._server):len(k)]
        k = k.strip(u'/'.encode(u'utf-8'))
        return k

    def thumbnail_path(self, path):
        filename = hashlib.md5(self._row_id(path)).hexdigest() + u'.' + common.THUMBNAIL_FORMAT
        p = self._bookmark + u'/.bookmark/' + filename
        return p

    @contextmanager
    def transactions(self):
        """Simple context manager for controlling transactions.
        We're explicitly calling `BEGIN` before the `execute()`. We also roll
        changes back if an error has been encountered. The transactions are
        commited when the context manager goes out of scope.

        """
        self._connection.execute(u'BEGIN')
        try:
            yield
        except:
            self._connection.rollback()
            raise
        else:
            self._connection.commit()

    def connection(self):
        return self._connection

    def init_tables(self):
        """Initialises the database with the default tables. It is safe to call
        this even if the table has alrady been initialised.

        The  `data` table stores file information of items inside the bookmark,
        whilst `info` contains information about the database itself.

        """
        with self.transactions():
            # Main ``data`` table
            self._connection.cursor().execute("""
                CREATE TABLE IF NOT EXISTS data (
                    id TEXT PRIMARY KEY COLLATE NOCASE,
                    description TEXT,
                    notes TEXT,
                    flags INTEGER DEFAULT 0,
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
            self._connection.cursor().execute("""
                CREATE TABLE IF NOT EXISTS properties (
                    width INTEGER,
                    height INTEGER,
                    framerate REAL
                )
            """)

    def value(self, id, key, table=u'data'):
        """Returns a value from the `bookmark.db` using the given filepath as
        the key.

        Args:
            id (unicode): The database row key.
            key (unicode): The data key to return.
            table (unicode): Optional table parameter, defaults to 'data'.

        Returns:
            data: The requested value or None.

        """
        id = self._row_id(id)
        _cursor = self._connection.cursor()
        _cursor.execute(u'SELECT {key} FROM {table} WHERE id=\'{id}\''.encode('utf-8').format(
            table=table.encode('utf-8'),
            key=key.encode('utf-8'),
            id=id
        ))

        res = _cursor.fetchone()
        if not res:
            return None
        return res[0]

    def values(self, column=u'*', table=u'data'):
        """Returns all values from the `bookmark.db` of the given table.

        Args:
            table (string): Optional table parameter, defaults to 'data'.

        Returns:
            dict: The structured database data.

        """
        _cursor = self._connection.cursor()
        if column != u'*':
            _column = u'id,' + column
        else:
            _column = column
        _cursor.execute("""SELECT {column} FROM {table}""".format(
                column=_column,
                table=table
            ))

        # Let's wrap the retrevied data into a more pythonic directory
        _data = _cursor.fetchall()
        data = {}
        if column == u'*':
            for v in _data:
                data[v[0].strip()] = {
                    u'description': v[1],
                    u'notes': v[2],
                    u'flags': v[3],
                    u'thumbnail_stamp': v[4],
                    u'user': v[5],
                }
        else:
            for v in _data:
                data[v[0].strip()] = {
                    column: v[1],
                }
        return data

    def setValue(self, id, key, value, table=u'data'):
        """Sets a value to the database.

        Pass the full file or folder path including the server, job and root.
        The database uses the relative path as the row id, which is returned by
        `_row_id()`. The method will update existing row, or create a new one if the
        row `id` does not exists yet.

        Note:
            The method does NOT commit the transaction! Use the
            ``transactions`` to issue a BEGIN statement. The
            transactions will be commited once the context manager goes out of
            scope.

        Args:
            id (unicode or int): Row id.
            key (unicode): A database column name.
            value (unicode or float): The value to set.

        """
        id = self._row_id(id)
        self._connection.execute("""
        INSERT INTO {table} (id, {key})
        VALUES('{id}','{value}')
        ON CONFLICT(id) DO UPDATE SET {key}=excluded.{key};
        """.format(
            id=id,
            key=key,
            value=value,
            table=table
        ))


if __name__ == '__main__':
    def run_benchmark():
        """The main takeaaway seems to be that `value()` is quicker on smaller
        databases, but once I have more than 100k+ items values seems to be
        performaing quicker.

        """

        # bookmark_db.setValue(ur'job/root/testfolder/testfile.ma', u'description', u'test')
        return
        x = 100000
        # #####################
        t = time.time()
        with bookmark_db.transactions():
            for n in xrange(x):
                id = bookmark_db._row_id(
                    ur'job/root/testfolder/testfile.ma{}'.format(n))
                bookmark_db.setValue(id, u'description',
                                     u'test description' + unicode(n))
                bookmark_db.setValue(id, u'notes', u'testnote{}' + unicode(n))
        print '`setValue()` took', time.time() - t, '(x{})'.format(n), '\n'
        # #####################
        t = time.time()
        with bookmark_db.transactions():
            for n in xrange(x):
                id = bookmark_db._row_id(
                    ur'job/root/testfolder/testfile.ma{}' + unicode(n))
                v = bookmark_db.value(id, u'description')
        print '`value()` took', time.time() - t, '\n'
        ######################
        t = time.time()
        data = bookmark_db.values()
        for n in xrange(x):
            id = bookmark_db._row_id(ur'job/root/testfolder/testfile.ma' + unicode(n))
            v = data[id]['description']
        print '`values()` took', time.time() - t, '\n'


    db = BookmarkDB(
        server=u'C:/temp',
        job=u'dir1',
        root=u'added_bookmark',
    )
    print db.values()
    print db.values('notes')

    # run_benchmark()
    # bookmark_db.setValue(ur'job/root/testfolder/testfile.ma', u'description', u'test')
