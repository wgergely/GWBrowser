# -*- coding: utf-8 -*-
"""BookmarkDB stores all item information Bookmarks needs
to work.

This includes file descriptions, properties like `width`, `height`, asset
configs, etc. The database file itself is stored in the given bookmark's root,
at `//server/job/root/.bookmark/bookmark.db`

The sqlite3 database table definitions are stored in `bookmark_db.json`.

Usage
-----


    Use the thread-safe `bookmark_db.get_db()` to create thread-specific
    connections to a database:

.. code-block:: python

        with bookmark_db.transactions(server, job, root) as db:
            v = db.value(db.source(), bookmark_db.DescriptionColumn)

    To retrive data from a bookmark database, use the higher level
    `bookmark_db.get_property()` method. The method guarantees to never fail,
    regardless of database errors.

The bookmark databases have currently 3 tables. The `data` table is used to
store information about folders and files, eg. assets would store their
visibility flags, cut information and Shotgun data here.
The `info` and `properties` tables are linked to the bookmark.

"""
import contextlib
import time
import platform
import sqlite3
import base64
import json

from PySide2 import QtCore, QtWidgets

from . import log
from . import common


AssetTable = u'AssetData'
BookmarkTable = u'BookmarkData'
InfoTable = u'InfoData'

IdColumn = 'id'
DescriptionColumn = 'description'
NotesColumn = 'notes'

DATABASE = u'bookmark.db'

database_connect_retries = 100


TABLES = {
    AssetTable: {
        IdColumn: {
            'sql': u'TEXT PRIMARY KEY COLLATE NOCASE',
            'type': unicode
        },
        'description': {
            'sql': u'TEXT',
            'type': unicode
        },
        'notes': {
            'sql': u'TEXT',
            'type': dict
        },
        'flags': {
            'sql': u'INT DEFAULT 0',
            'type': int
        },
        'thumbnail_stamp': {
            'sql': u'REAL',
            'type': float
        },
        'user': {
            'sql': u'TEXT',
            'type': unicode
        },
        'shotgun_id': {
            'sql': u'INT',
            'type': int
        },
        'shotgun_name': {
            'sql': u'TEXT',
            'type': unicode
        },
        'shotgun_type': {
            'sql': u'TEXT',
            'type': unicode
        },
        'cut_duration': {
            'sql': u'INT',
            'type': int
        },
        'cut_in': {
            'sql': u'INT',
            'type': int,
        },
        'cut_out': {
            'sql': u'INT',
            'type': int
        },
        'url1': {
            'sql': u'TEXT',
            'type': unicode
        },
        'url2': {
            'sql': u'TEXT',
            'type': unicode

        },
    },
    InfoTable: {
        IdColumn: {
            'sql': u'TEXT PRIMARY KEY COLLATE NOCASE',
            'type': unicode
        },
        'server': {
            'sql': u'TEXT NOT NULL',
            'type': unicode
        },
        'job': {
            'sql': u'TEXT NOT NULL',
            'type': unicode,
        },
        'root': {
            'sql': u'TEXT NOT NULL',
            'type': unicode
        },
        'user': {
            'sql': u'TEXT NOT NULL',
            'type': unicode,
        },
        'host': {
            'sql': u'TEXT NOT NULL',
            'type': unicode
        },
        'created': {
            'sql': u'REAL NOT NULL',
            'type': float
        }
    },
    BookmarkTable: {
        IdColumn: {
            'sql': u'TEXT PRIMARY KEY COLLATE NOCASE',
            'type': unicode
        },
        'description': {
            'sql': u'TEXT',
            'type': unicode
        },
        'width': {
            'sql': u'INT',
            'type': int
        },
        'height': {
            'sql': u'INT',
            'type': int
        },
        'framerate': {
            'sql': u'REAL',
            'type': float
        },
        'prefix': {
            'sql': u'TEXT',
            'type': unicode
        },
        'startframe': {
            'sql': u'INT',
            'type': int
        },
        'duration': {
            'sql': u'INT',
            'type': int
        },
        'identifier': {
            'sql': u'TEXT',
            'type': unicode
        },
        'slacktoken': {
            'sql': u'TEXT',
            'type': unicode
        },
        'shotgun_domain': {
            'sql': u'TEXT',
            'type': unicode
        },
        'shotgun_scriptname': {
            'sql': u'TEXT',
            'type': unicode
        },
        'shotgun_api_key': {
            'sql': u'TEXT',
            'type': unicode
        },
        'shotgun_id': {
            'sql': u'INT',
            'type': int
        },
        'shotgun_name': {
            'sql': u'TEXT',
            'type': unicode
        },
        'shotgun_type': {
            'sql': u'TEXT',
            'type': unicode
        },
        'url1': {
            'sql': u'TEXT',
            'type': unicode,
        },
        'url2': {
            'sql': u'TEXT',
            'type': unicode
        },
        'asset_config': {
            'sql': u'TEXT',
            'type': dict
        }
    }
}

__DB_CONNECTIONS = {}


def b64encode(v):
    """base64.b64encode() only takes bytes, not characters, hence We have to
    encode unicode characters before calling the function.

    Args:
        v (unicode):    A string to encode as base64 characters.

    Returns:
        unicode:        A base64 encoded unicode string.

    """
    if not isinstance(v, unicode):
        raise TypeError(
            u'Invalid type. Expected <type \'unicode\'>, got {}'.format(type(v)))
    return base64.b64encode(v.encode('utf-8')).decode('utf-8')



def b64decode(v):
    """base64.b64encode() only takes bytes, not characters, hence We have to
    encode unicode characters before calling the function.

    Args:
        v (unicode):    A string to decode from base64 characters to unicode.

    Returns:
        unicode:        A base64 decoded unicode string.

    """
    if not isinstance(v, (unicode, str)):
        raise TypeError(
            u'Invalid type. Expected <type \'unicode\'> or <type \'str\'>, got {}'.format(type(v)))

    v = base64.b64decode(v)
    try:
        return v.decode('utf-8')
    except Exception as e:
        return v


def close():
    try:
        for k in __DB_CONNECTIONS.keys():
            __DB_CONNECTIONS[k].close()
            __DB_CONNECTIONS[k].deleteLater()
            del __DB_CONNECTIONS[k]
    except Exception:
        log.error('Error closing the database')


def get_property(key, server=None, job=None, root=None, asset=None, asset_property=False):
    """Returns a value from a bookmark database.

    When server, job, or root are not defined, we'll try to look the values up
    of the active bookmark.

    Args:
        key (unicode):          A column.
        server(unicode):        Server name.
        job (unicode):          Job name.
        root (unicode):         Root folder name.
        asset (unicode):        Asset name.
        asset_property (bool):  Specify if the asset is an asset property.

    """
    from . import settings
    if not all((server, root, job)):
        server = settings.active(settings.ServerKey)
        job = settings.active(settings.JobKey)
        root = settings.active(settings.RootKey)
    if not all((server, root, job)):
        raise RuntimeError(u'No bookmarks specified.')

    try:
        with transactions(server, job, root) as db:
            if not asset_property:
                return db.value(db.source(), key, table=BookmarkTable)
            if not asset:
                asset = settings.active(settings.AssetKey)
                if not asset:
                    raise RuntimeError(u'Asset not specified.')
            return db.value(db.source(asset), key, table=AssetTable)
    except Exception as e:
        log.error(e)
        return None


def sleep():
    """Waits a little before trying to open the database.

    """
    app = QtWidgets.QApplication.instance()
    if app and app.thread() == QtCore.QThread.currentThread():
        QtCore.QThread.msleep(25)
        return
    QtCore.QThread.msleep(50)


def set_flag(server, job, root, k, mode, flag):
    """A utility method used by the base view to set an item flag to the database.

    """
    with transactions(server, job, root) as db:
        f = db.value(k, u'flags', table=AssetTable)
        f = 0 if f is None else f
        f = f | flag if mode else f & ~flag
        db.setValue(k, u'flags', f, table=AssetTable)



def get_db(server, job, root, force=False):
    """Creates a database controller associated with a bookmark.

    SQLite cannot share the same connection between different threads, hence we
    will create and cache controllers per thread. The cached entries are stored
    in `__DB_CONNECTIONS`.

    Args:
        server (unicode): The name of the `server`.
        job (unicode): The name of the `job`.
        root (unicode): The name of the `root`.
        force (bool): Force retry connecting to the database.

    Returns:
        BookmarkDB:     Database controller instance.

    Raises:
        RuntimeError:   If the database is locked
        OSError:        If the database is missing.

    """
    for k in (server, job, root):
        if isinstance(k, unicode):
            continue
        raise TypeError(
            u'Expected {}, got {}'.format(unicode, type(k)))

    key = _get_thread_key(server, job, root)

    global __DB_CONNECTIONS
    if key in __DB_CONNECTIONS:
        if force:
            __DB_CONNECTIONS[key].connect_with_retries()
        return __DB_CONNECTIONS[key]

    db = BookmarkDB(server, job, root)
    __DB_CONNECTIONS[key] = db
    return __DB_CONNECTIONS[key]


def remove_db(server, job, root):
    """Removes and closes a cached a bookmark database connection.

    Args:
        server (unicode):   A server.
        job (unicode):      A job.
        root (unicode):     A root.

    """
    global __DB_CONNECTIONS
    key = u'/'.join((server, job, root))

    for k in __DB_CONNECTIONS.keys():
        if key.lower() not in k.lower():
            continue

        try:
            __DB_CONNECTIONS[k].close()
            __DB_CONNECTIONS[k].deleteLater()
            del __DB_CONNECTIONS[k]
        except:
            log.error('Error removing the database.')


@contextlib.contextmanager
def transactions(server, job, root, force=False):
    """Context manager for controlling transactions.

    We're explicitly calling `BEGIN` before the `execute()`. We also roll
    changes back if an error has been encountered. The transactions are
    commited when the context manager goes out of scope.

    """
    db = get_db(server, job, root, force=force)

    try:
        db.connection().execute(u'BEGIN')
    except Exception as e:
        log.error(e)

    try:
        yield db
    except:
        db.connection().rollback()
        raise
    else:
        try:
            db.connection().commit()
        except sqlite3.Error:
            log.error(u'A database error occured.')


def _get_thread_key(*args):
    t = unicode(repr(QtCore.QThread.currentThread()))
    return u'/'.join(args) + t


class BookmarkDB(QtCore.QObject):
    """Database connector used to interface with the SQLite database.

    Use `BookmarkDB.value()` and `BookmarkDB.setValue()` to get and set data.

    """

    def __init__(self, server, job, root, parent=None):
        super(BookmarkDB, self).__init__(parent=parent)
        self._is_valid = False
        self._connection = None

        self._server = server.encode(u'utf-8')
        self._server_u = server
        self._job = job.encode(u'utf-8')
        self._job_u = job
        self._root = root.encode(u'utf-8')
        self._root_u = root

        self._bookmark = u'/'.join((server, job, root))
        self._bookmark_root = u'{}/{}'.format(self._bookmark, common.BOOKMARK_ROOT_DIR)
        self._bookmark_db_path = u'{}/{}'.format(self._bookmark_root, DATABASE)

        if self._create_bookmark_dir():
            self.connect_with_retries()
        else:
            self._connect_to_memory_db()

        self.init_tables()
        self.destroyed.connect(self.close)

    def _connect_to_memory_db(self):
        """Creates in-memory database used, when we're unable to connect to the
        bookmark database.

        """
        self._connection = sqlite3.connect(
            ':memory:',
            isolation_level=None,
            check_same_thread=False
        )
        self._is_valid = False
        return self._connection

    def connect_with_retries(self):
        """Connects to the database file.

        The database can be locked for a brief period of time whilst it is being
        used by another controller instance in another thread. This normally will raise an
        exception, but it is safe to wait on this a little and try a few times
        before deeming it permanently unopenable.

        When a database is unopenable, we'll create an in-memory database, and
        mark the instance invalid (`self.is_valid()` returns `False`).

        """
        n = 0
        while True:
            try:
                self._connection = sqlite3.connect(
                    self._bookmark_db_path,
                    isolation_level=None,
                    check_same_thread=False
                )
                self._is_valid = True
                return self._connection
            except sqlite3.Error as e:
                if n == database_connect_retries:
                    self._connect_to_memory_db()
                    return self._connection
                sleep()
                n += 1
            except (RuntimeError, ValueError, TypeError, OSError):
                log.error(u'Error.')
                raise

    def close(self):
        try:
            self._connection.commit()
            self._connection.close()
        except sqlite3.Error:
            log.error('Database error.')
        finally:
            self._connection = None

    def _create_bookmark_dir(self):
        """Creates the `BOOKMARK_ROOT_DIR` if does not yet exist.

        Returns:
            bool:   `True` if the folder already exists, or successfully created.
                    `False` if can't create the folder.

        """
        file_info = QtCore.QFileInfo(self.root())
        if file_info.exists():
            return True
        _dir = file_info.dir()
        if _dir.exists() and _dir.mkdir(common.BOOKMARK_ROOT_DIR):
            return True
        return False

    def root(self):
        return self._bookmark_root

    def is_valid(self):
        if not self._connection:
            return False
        return self._is_valid

    def connection(self):
        return self._connection

    def source(self, *args):
        if args:
            return self._bookmark + u'/' + u'/'.join(args)
        return self._bookmark

    def _create_table(self, table):
        """Creates a table based on the TABLES definition.

        """
        args = []

        for k, v in TABLES[table].iteritems():
            args.append(u'{} {}'.format(k, v['sql']))

        sql = u'CREATE TABLE IF NOT EXISTS {table} ({args})'.format(
            table=table,
            args=u','.join(args)
        )

        _cursor = self._connection.cursor()
        try:
            _cursor.execute(sql.encode('utf-8'))
        except Exception as e:
            log.error(u'Failed create table "{}"\n{}'.format(table, e))
            raise
        finally:
            _cursor.close()

    def _patch_table(self, table):
        """For backwards compatibility, we will ALTER the database if any of the
        required columns are missing.

        """
        sql = u'PRAGMA table_info(\'{}\');'.format(table)

        _cursor = self._connection.cursor()
        try:
            table_info = _cursor.execute(sql.encode('utf-8')).fetchall()
        except Exception as e:
            log.error(u'Failed to fetch table info.\n{}'.format(e))
            _cursor.close()
            raise

        columns = [c[1] for c in table_info]
        missing = list(set(TABLES[table]) - set(columns))

        for column in missing:
            cmd = 'ALTER TABLE {} ADD COLUMN {};'.format(table, column)
            try:
                _cursor.execute(cmd)
                log.success(u'Added missing column {}'.format(missing))
            except Exception as e:
                log.error(
                    u'Failed to add missing column {}\n{}'.format(column, e))
                _cursor.close()
                raise
        _cursor.close()

    def _add_info(self):
        """Adds information about who and when created the database.

        """
        sql = u'INSERT OR IGNORE INTO {table} ({args}) VALUES ({kwargs});'.format(
            table=InfoTable,
            args=u','.join(sorted(TABLES[InfoTable])),
            kwargs=u'\'{{{}}}\''.format(
                u'}\', \'{'.join(
                    sorted(TABLES[InfoTable])
                )
            )
        ).format(
            id=common.get_hash(self._bookmark),
            server=b64encode(self._server_u),
            job=b64encode(self._job_u),
            root=b64encode(self._root_u),
            user=b64encode(common.get_username()),
            host=b64encode(platform.node().decode('utf-8')),
            created=time.time(),
        )

        _cursor = self._connection.cursor()
        try:
            _cursor.execute(sql.encode('utf-8'))
        except Exception as e:
            log.error(u'Could not add bookmark info: {}'.format(e))
            raise
        finally:
            _cursor.close()

    def init_tables(self):
        """Initialises the database with the default tables.

        If the database is new or empty, we will create the tables.
        If the database has tables already, we'll check the columns against
        the table definitions and add any missing ones.

        """
        for table in TABLES:
            self._create_table(table)
            self._patch_table(table)
        self._add_info()

    def value(self, source, key, table=AssetTable):
        """Returns a value from the `bookmark_db`.

        Example:

            .. code-block:: python

                source = u'server/job/my/file.txt'
                v = db.value(source, u'description')

        Args:
            source (unicode):       Path to a file or folder.
            key (unicode):          A column name.
            table (unicode):        Optional table parameter, defaults to `AssetTable`.

        Returns:
            data:                   The requested value or `None`.

        """
        if not self.is_valid():
            return None

        self._verify_args(source, key, table)

        _hash = common.get_hash(source).encode('utf-8')
        sql = u'SELECT {key} FROM {table} WHERE id=\'{id}\''.format(
            table=table,
            key=key,
            id=_hash
        )


        _cursor = self._connection.cursor()
        try:
            _cursor.execute(sql.encode('utf-8'))
            row = _cursor.fetchone()
        except Exception as e:
            log.error(u'Failed to get value from database.\n{}'.format(e))
            raise
        finally:
            _cursor.close()

        if not row:
            return None

        value = row[0]
        if value is None:
            return None

        # Type conversion
        _type = TABLES[table][key]['type']
        if _type is dict:
            try:
                value = b64decode(value)
                value = json.loads(value, 'utf-8')
            except Exception as e:
                value = None
        elif _type is unicode:
            try:
                value = b64decode(value)
            except Exception as e:
                value = None
        elif _type is float:
            try:
                value = float(value)
            except Exception as e:
                value = None
        elif _type is int:
            try:
                value = int(value)
            except Exception as e:
                value = None
        return value

    def _verify_args(self, source, key, table, value=None):
        if not isinstance(source, unicode):
            raise TypeError(
                u'Invalid source type. Got {}, expected <type \'unicode\'>'.format(type(source)))
        if key not in TABLES[table]:
            raise ValueError(u'Key "{}" is invalid. Expected one of {}'.format(
                key, u', '.join(TABLES[table])))
        if value and not isinstance(value, TABLES[table][key]['type']):
            raise TypeError(u'Invalid data type. Expected {}, got {}'.format(
                TABLES[table][key]['type'],
                type(value)
            ))

    def setValue(self, source, key, value, table=AssetTable):
        """Sets a value in the database.

        The method does NOT commit the transaction! Use ``transactions`` context
        manager to issue a BEGIN statement. The transactions will be commited
        once the context manager goes out of scope.

        Example:

            .. code-block:: python

                with db.transactions:
                    source = u'//SERVER/MY_JOB/shots/sh0010/scenes/my_scene.ma'
                    db.setValue(source, u'description', u'hello world')

        Args:
            source (unicode):       A row id, usually a file or folder path.
            key (unicode):          A database column name.
            value (*):              The value to set.

        """
        if not self.is_valid():
            return

        self._verify_args(source, key, table, value=value)

        if isinstance(value, dict):
            try:
                value = json.dumps(value, ensure_ascii=False, encoding='utf-8')
                if isinstance(value, str):
                    value = value.decode('utf-8')
                value = b64encode(value)
            except Exception as e:
                log.error(e)
                value = None
        elif isinstance(value, unicode):
            try:
                value = b64encode(value)
            except Exception as e:
                log.error(e)
                value = None
        elif isinstance(value, (float, int, str)):
            try:
                value = unicode(value)
            except Exception as e:
                log.error(e)
                value = None

        _hash = common.get_hash(source).decode('utf-8')
        values = []

        # Earlier versions of the SQLITE library lack `UPSERT` or `WITH`
        # A workaround is found here:
        # https://stackoverflow.com/questions/418898/sqlite-upsert-not-insert-or-replace
        for k in TABLES[table]:
            if k == key:
                v = u'\n null' if value is None else u'\n \'' + value + u'\''
                values.append(v)
                continue

            v = u'\n(SELECT ' + k + u' FROM ' + table + \
                u' WHERE id =\'' + _hash + u'\')'
            values.append(v)

        sql = u'INSERT OR REPLACE INTO {table} (id, {allkeys}) VALUES (\'{hash}\', {values});'.format(
            hash=_hash,
            allkeys=u', '.join(TABLES[table]),
            values=u','.join(values),
            table=table
        )

        _cursor = self._connection.cursor()
        try:
            _cursor.execute(sql.encode('utf-8'))
        except Exception as e:
            log.error(u'Failed to set value.\n{}'.format(e))
        finally:
            _cursor.close()
