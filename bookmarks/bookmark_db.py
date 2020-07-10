# -*- coding: utf-8 -*-
"""BookmarkDB is used to store all custom item information, like descriptions,
notes and todos, item flags.

The database uses SQLite3. See :const:`.KEYS` and
:func:`.BookmarkDB.init_tables` for table/column definitions. Don't initiate
:class:`.BookmarkDB` directly but use the :func:`.get_db` get a thread-specific
BookmarkDB instance.

.. code-block:: python

    import bookmarks.bookmark_db as bookmark_db
    db = bookmark_db.get_db(
        u'//SERVER',
        u'MYJOB',
        u'DATA/SHOTS'
    )
    source = u'//server/myjob/data/shots/sh0010/scene/myscene.ma'
    value = db.value(source, u'description')

"""
from contextlib import contextmanager
import time
import platform
import sqlite3
from sqlite3 import Error

from PySide2 import QtCore

import bookmarks.log as log
import bookmarks.common as common


KEYS = {
    u'data': (
        u'description',
        u'notes',
        u'flags',
        u'thumbnail_stamp',
        u'user',
        u'shotgun_id',
        u'shotgun_name',
        u'shotgun_type',
        u'cut_duration',
        u'cut_in',
        u'cut_out',
        u'url1',
        u'url2',
    ),
    u'info': (
        u'server',
        u'job',
        u'root',
        u'user',
        u'host',
        u'created'
    ),
    u'properties': (
        u'width',
        u'height',
        u'framerate',
        u'prefix',
        u'startframe',
        u'duration',
        u'identifier',
        u'slacktoken',
        u'shotgun_domain',
        u'shotgun_scriptname',
        u'shotgun_api_key',
        u'shotgun_id',
        u'shotgun_name',
        u'shotgun_type',
        u'url1',
        u'url2',
    ),
}
"""Database table/column structure definition."""


DB_CONNECTIONS = {}


def get_property(key, server=None, job=None, root=None, asset=None, asset_property=False):
    import bookmarks.settings as settings

    if not all((server, root, job)):
        server = settings.ACTIVE['server']
        job = settings.ACTIVE['job']
        root = settings.ACTIVE['root']

    if not all((server, root, job)):
        raise RuntimeError(u'No bookmarks specified.')

    db = get_db(
        server=server,
        job=job,
        root=root
    )

    if not asset_property:
        return db.value(1, key, table=u'properties')

    if not asset:
        asset = settings.ACTIVE['asset']
    if not asset:
        raise RuntimeError(u'Asset not specified.')

    source = u'{}/{}/{}/{}'.format(server, job, root, asset)
    return db.value(source, key, table=u'data')


def get_asset_property(key, server=None, job=None, root=None):
    import bookmarks.settings as settings

    if not all((server, root, job)):
        server = settings.ACTIVE['server']
        job = settings.ACTIVE['job']
        root = settings.ACTIVE['root']

    if not all((server, root, job)):
        raise RuntimeError(u'No bookmarks specified.')

    db = get_db(server, job, root)
    return db.value(1, key, table=u'properties')


def get_db(server, job, root):
    """Creates a saver a database controller associated with a bookmark.

    SQLite cannot share the same connection between different threads, hence we
    will create and cache the controllers per thread.

    Args:
        server (unicode): The name of the `server`.
        job (unicode): The name of the `job`.
        root (unicode): The name of the `root`.

    Returns:
        BookmarkDB: Database controller instance.

    Raises:
        RuntimeError: If the database is locked or impossible to open.

    """
    if not isinstance(server, unicode):
        raise TypeError(
            u'Expected <type \'unicode\'>, got {}'.format(type(server)))
    if not isinstance(job, unicode):
        raise TypeError(
            u'Expected <type \'unicode\'>, got {}'.format(type(job)))
    if not isinstance(root, unicode):
        raise TypeError(
            u'Expected <type \'unicode\'>, got {}'.format(type(root)))

    t = unicode(repr(QtCore.QThread.currentThread()))
    key = (u'/'.join((server, job, root)) + t).lower()

    global DB_CONNECTIONS
    if key in DB_CONNECTIONS:
        return DB_CONNECTIONS[key]

    # The SQLite database can be locked for a brief period of time whilst it is
    # being used by another controller isntance. This normally will raise an
    # exception, but it is safe to wait on this a little and try again.

    n = 0
    while True:
        if n > 100:
            import bookmarks.common_ui as common_ui
            # After 5 seconds we will give up and return `None`
            s = u'Unable to get the database.'
            s2 = u'{}/{}/{} might be locked'.format(server, job, root)
            log.error(s)
            common_ui.ErrorBox(s, s2).open()
            raise RuntimeError(s)

        try:
            # Create and cache the instance
            DB_CONNECTIONS[key] = BookmarkDB(server, job, root)
            return DB_CONNECTIONS[key]
        except RuntimeError:
            # Wait a little and try again
            n += 1
            QtCore.QThread.msleep(50)


def remove_db(index, server=None, job=None, root=None):
    """Helper function to remove a bookmark database instance

    Args:
        index (QModelIndex): A valid QModelIndex()

    """
    try:
        global DB_CONNECTIONS
        thread_id = repr(QtCore.QThread.currentThread())

        if not index.isValid():
            if not all((server, job, root)):
                raise ValueError(u'Must provide valid server, job, and root')
            args = (server, job, root)
        else:
            args = index.data(common.ParentPathRole)[0:3]

        k = u'/'.join(args).lower() + thread_id
        if k in DB_CONNECTIONS:
            DB_CONNECTIONS[k].connection().close()
            DB_CONNECTIONS[k].deleteLater()
            del DB_CONNECTIONS[k]
    except:
        log.error(u'Failed to remove BookmarkDB')


def reset():
    global DB_CONNECTIONS
    for v in DB_CONNECTIONS.itervalues():
        v.deleteLater()
    DB_CONNECTIONS = {}


class BookmarkDB(QtCore.QObject):
    """Database connector used to interface with the SQLite database.

    Use `BookmarkDB.value()` and `BookmarkDB.setValue()` to get and set data.

    """

    def __init__(self, server, job, root, parent=None):
        super(BookmarkDB, self).__init__(parent=parent)

        self._connection = None
        self._server = server.lower().encode(u'utf-8')
        self._server_u = server.lower()
        self._job = job.lower().encode(u'utf-8')
        self._job_u = job.lower()
        self._root = root.lower().encode(u'utf-8')
        self._root_u = root.lower()
        self._bookmark = server + u'/' + job + u'/' + root
        self._database_path = u'{server}/{job}/{root}/.bookmark/bookmark.db'.format(
            server=server,
            job=job,
            root=root
        )

        # Let's make sure the parent folder exists before connecting
        _p = u'{}/.bookmark'.format(self._bookmark)
        if not QtCore.QFileInfo(_p).exists():
            if not QtCore.QDir(self._bookmark).mkpath(u'.bookmark'):
                s = u'Unable to create folder "{}"'.format(_p)
                log.error(s)
                raise OSError(s)

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
        _cursor = self._connection.cursor()
        with self.transactions():
            # Main ``data`` table
            _cursor.execute("""
CREATE TABLE IF NOT EXISTS data (
    id TEXT PRIMARY KEY COLLATE NOCASE,
    description TEXT,
    notes TEXT,
    flags INTEGER DEFAULT 0,
    thumbnail_stamp REAL,
    user TEXT,
    shotgun_id INTEGER,
    shotgun_name TEXT,
    shotgun_type TEXT,
    cut_duration INT,
    cut_in INT,
    cut_out INT,
    url1 TEXT,
    url2 TEXT
);
            """)
            self._patch_database(_cursor, u'data')

            # Single-row ``info`` table
            _cursor.execute("""
CREATE TABLE IF NOT EXISTS info (
    id TEXT PRIMARY KEY COLLATE NOCASE,
    server TEXT NOT NULL,
    job TEXT NOT NULL,
    root TEXT NOT NULL,
    user TEXT NOT NULL,
    host TEXT NOT NULL,
    created REAL NOT NULL
);
            """)
            self._patch_database(_cursor, u'info')

            # Adding info data to the ``info`` table
            _cursor.execute("""
            INSERT OR IGNORE INTO info
                (id, server, job, root, user, host, created)
            VALUES
                ('{id}', '{server}', '{job}', '{root}', '{user}', '{host}', '{created}');
            """.format(
                id=self._bookmark,
                server=self._server,
                job=self._job,
                root=self._root,
                user=common.get_username(),
                host=platform.node(),
                created=time.time(),
            ))

            _cursor.execute("""
                CREATE TABLE IF NOT EXISTS properties (
                    id INTEGER PRIMARY KEY,
                    width REAL,
                    height REAL,
                    framerate REAL,
                    prefix TEXT,
                    startframe REAL,
                    duration REAL,
                    identifier TEXT,
                    slacktoken TEXT,
                    shotgun_domain TEXT,
                    shotgun_scriptname TEXT,
                    shotgun_api_key TEXT,
                    shotgun_id INTEGER,
                    shotgun_name TEXT,
                    shotgun_type TEXT,
                    url1 TEXT,
                    url2 TEXT
                );
            """)
            self._patch_database(_cursor, u'properties')
        _cursor.close()

    def _patch_database(self, _cursor, table):
        """For backwards compatibility, we will ALTER the database any of the
        required columns that are missing. This might happen if we have added new
        columns to the table definition but the database on the server is
        based on an older version of Bookmarks.

        """
        info = _cursor.execute("""PRAGMA table_info('{}');""".format(table)).fetchall()
        columns = [c[1] for c in info]
        missing = list(set(KEYS[table]) - set(columns))
        for column in missing:
            try:
                _cursor.execute('ALTER TABLE {} ADD COLUMN {};'.format(table, column))
                log.success(u'Added missing column {}'.format(missing))
            except:
                log.error(u'Failed to add missing column {}'.format(column))
                pass # handle the error

    def value(self, source, key, table=u'data'):
        """Returns a value from the `bookmark.db`.

        Example:

            .. code-block:: python

                source = u'server/job/my/file.txt'
                v = db.value(source, u'description')

        Args:
            source (unicode): Path to a file or a row id.
            key (unicode): A column name.
            table (unicode): Optional table parameter, defaults to 'data'.

        Returns:
            data: The requested value or None.

        """
        if not isinstance(source, (unicode, int)):
            raise TypeError(
                u'Invalid type. Expected <type \'unicode or int\', got {}'.format(type(source)))

        if key not in KEYS[table]:
            raise ValueError(u'Key "{}" is invalid. Expected one of "{}"'.format(
                key, u'", "'.join(KEYS[table])))

        hash = common.get_hash(source)

        _cursor = self._connection.cursor()
        kw = {u'table': table, u'key': key, u'id': hash}
        sql = u'SELECT {key} FROM {table} WHERE id=\'{id}\''.format(**kw)
        _cursor.execute(sql.encode('utf-8'))
        res = _cursor.fetchone()
        _cursor.close()

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
        _cursor.execute("""SELECT {column} FROM {table};""".format(
            column=_column,
            table=table
        ))

        # Let's wrap the retrevied data into a more pythonic directory
        _data = _cursor.fetchall()
        _cursor.close()

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

    def setValue(self, source, key, value, table=u'data'):
        """Sets a value in the database.

        The method does NOT commit the transaction! Use ``transactions`` context
        manager to issue a BEGIN statement. The transactions will be commited
        once the context manager goes out of scope.

        Example:

            .. code-block:: python

                with db.transactions:
                    source = u'server/job/my/file.txt'
                    db.setValue(source, u'description', u'hello world')

        Args:
            source (unicode or int): A row id.
            key (unicode): A database column name.
            value (unicode or float): The value to set.

        """
        if not isinstance(source, (unicode, int)):
            raise TypeError(u'Invalid type.')

        if key not in KEYS[table]:
            raise ValueError(u'Key "{}" is invalid. Expected one of {}'.format(
                key, u', '.join(KEYS[table])))

        hash = common.get_hash(source)
        values = []

        # Earlier versions of the SQLITE library lack `UPSERT` or `WITH`
        # A workaround is found here:
        # https://stackoverflow.com/questions/418898/sqlite-upsert-not-insert-or-replace
        for k in KEYS[table]:
            if k == key:
                v = u'\n \'' + unicode(value) + u'\''
            else:
                v = u'\n(SELECT ' + k + u' FROM ' + table + \
                    u' WHERE id =\'' + unicode(hash) + u'\')'
            values.append(v)

        kw = {
            'hash': hash,
            'allkeys': u', '.join(KEYS[table]),
            'values': u','.join(values),
            'table': table
        }
        sql = u'INSERT OR REPLACE INTO {table} (id, {allkeys}) VALUES (\'{hash}\', {values});'.format(
            **kw)
        _cursor = self._connection.cursor()
        _cursor.execute(sql.encode('utf-8'))
        _cursor.close()
