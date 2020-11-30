# -*- coding: utf-8 -*-
"""Contains :class:`.LocalSettings`, a customized QSettings instance  used to
store active paths, widget and user options.

Also contains the session lock used to `lock` a running Bookmark instance. See
:func:`.get_lockfile_path` and the relevant functions in :class:`.LocalSettings`.

.. code-block:: python

    favourites = settings.local_settings.favourites()

"""
import collections
import os
import json
import re
from functools import wraps

import psutil
import _scandir

from PySide2 import QtCore

from . import log
from . import common


ACTIVE = collections.OrderedDict()
ACTIVE_KEYS = (u'server', u'job', u'root', u'asset', u'task_folder', u'file')
"""The list of keys used to store currently activated paths segments."""


local_settings = None


def set_active(k, v):
    if local_settings is None:
        raise RuntimeError('LocalSettings is not initialized.')
    if k not in ACTIVE_KEYS:
        raise ValueError('{} is invalid, expected one of {}'.format(k, ACTIVE_KEYS))
    local_settings.setValue(u'activepath/{}'.format(k), v)
    local_settings.load_and_verify_stored_paths()



def get_lockfile_path():
    """The path to this session's lock-file."""
    path = u'{}/{}/session_{}.lock'.format(
        QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation),
        common.PRODUCT,
        os.getpid()
    )
    file_info = QtCore.QFileInfo(path)
    if not file_info.exists():
        file_info.dir().mkpath(u'.')
    return file_info.filePath()


def prune_lockfile(func):
    """Decorator removes stale lock-files from the Bookmarks's temp folder."""
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        lockfile_info = QtCore.QFileInfo(get_lockfile_path())
        for entry in _scandir.scandir(lockfile_info.path()):
            if entry.is_dir():
                continue

            match = re.match(ur'session_[0-9]+\.lock', entry.name.lower())
            if not match:
                continue

            path = entry.path.replace(u'\\', u'/')
            pid = path.strip(u'.lock').split(u'_').pop()
            pid = int(pid)
            if pid not in psutil.pids():
                QtCore.QFile(path).remove()
        return func(*args, **kwargs)
    return func_wrapper


class LocalSettings(QtCore.QSettings):
    """An `ini` config file.

    A fully set active path is made up of the following key/values:

    * activepath/server (unicode):    Server, eg. '//server/data'.
    * activepath/job (unicode):       Job folder name inside the server.
    * activepath/root (unicode):      Job-relative bookmark path, eg. 'seq_010/shots'.
    * activepath/asset (unicode):     Job folder name inside the root, eg. 'shot_010'.
    * activepath/task_folder (unicode):  A folder, eg. 'scenes', 'renders', etc.
    * activepath/file (unicode):      A relative file path.

    """
    filename = u'settings.ini'
    keys = (u'server', u'job', u'root', u'asset', u'task_folder', u'file')

    def __init__(self, parent=None):
        self.config_path = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation)
        self.config_path = u'{}/{}/{}'.format(
            self.config_path,
            common.PRODUCT,
            self.filename
        )

        super(LocalSettings, self).__init__(
            self.config_path,
            QtCore.QSettings.IniFormat,
            parent=parent
        )

        self.INTERNAL_SETTINGS_DATA = {}  # Internal data storage
        self._current_mode = self.get_mode()

        # Simple timer to verify the state of the current changes
        self.server_mount_timer = QtCore.QTimer(parent=self)
        self.server_mount_timer.setInterval(15000)
        self.server_mount_timer.setSingleShot(False)
        self.server_mount_timer.setTimerType(QtCore.Qt.CoarseTimer)
        self.server_mount_timer.timeout.connect(self.load_and_verify_stored_paths)

        self.load_and_verify_stored_paths()
        self.load_saved_servers()

    def load_saved_servers(self):
        """Loads and returns a list of saved servers from the ini config file.

        The results are cached to `common.SERVERS`.

        """
        def sep(s):
            return re.sub(
                ur'[\\]', u'/', s, flags=re.UNICODE | re.IGNORECASE)

        self.sync()

        val = self.value(u'servers')
        if not val:
            common.SERVERS = []
            return common.SERVERS

        # Will return a string if only one server is stored in the settings
        if isinstance(val, (str, unicode)):
            common.SERVERS = [val, ]
            return common.SERVERS

        common.SERVERS = sorted(list(set([sep(f) for f in val])))
        return common.SERVERS

    def value(self, k):
        """An override for the default get value method.

        When solo mode is on we disable saving `activepath` values to
        the local settings and redirect instead to an in-memory
        dictionary.

        """
        activepath = k.lower().startswith(u'activepath')
        if self.current_mode() and activepath:
            if k not in self.INTERNAL_SETTINGS_DATA:
                v = super(LocalSettings, self).value(k)
                self.INTERNAL_SETTINGS_DATA[k] = v
            return self.INTERNAL_SETTINGS_DATA[k]

        t = super(LocalSettings, self).value(k  + u'_type')
        v = super(LocalSettings, self).value(k)
        if v is None:
            return

        if t == u'NoneType':
            v = None
        elif t == u'bool':
            if not isinstance(v, bool):
                if v.lower() in [u'true', u'1']:
                    v = True
                elif v.lower() in [u'false', u'0', 'none']:
                    v = False
        elif t == u'str':
            v = unicode(v)
        elif t == u'unicode':
            v = unicode(v)
        elif t == u'int':
            v = int(v)
        elif t == u'float':
            v = float(v)
        return v


    def setValue(self, k, v):
        """Override to allow redirecting `activepath` keys to be saved in memory
        when solo mode is on.

        """
        if self.current_mode() and k.lower().startswith(u'activepath'):
            self.INTERNAL_SETTINGS_DATA[k] = v
            return
        super(LocalSettings, self).setValue(k, v)
        super(LocalSettings, self).setValue(k + u'_type', type(v).__name__)

    def current_mode(self):
        return self._current_mode

    @QtCore.Slot()
    def load_and_verify_stored_paths(self):
        """This slot verifies and returns the saved ``active paths`` wrapped in
        a dictionary.

        If the resulting active path is not an existing file, we will
        progressively unset the invalid path segments until we get a valid file
        path.

        Returns:
            OrderedDict:    Path segments of an existing file.

        """
        self.sync() # load any changes from the config file

        for k in ACTIVE_KEYS:
            ACTIVE[k] = self.value(u'activepath/{}'.format(k))

        # Let's check the path and unset any invalid parts
        path = u''
        for k in ACTIVE:
            if ACTIVE[k]:
                path += ACTIVE[k]
            if not QtCore.QFileInfo(path).exists():
                ACTIVE[k] = None
                self.setValue(u'activepath/{}'.format(k), None)
            path += u'/'
        return ACTIVE

    @prune_lockfile
    def touch_mode_lockfile(self):
        """Creates a lockfile based on the current process' PID."""
        path = get_lockfile_path()
        lockfile_info = QtCore.QFileInfo()
        lockfile_info.dir().mkpath(u'.')
        with open(path, 'w+'):
            pass

    @prune_lockfile
    def save_mode_lockfile(self):
        """Saves the current solo mode to the lockfile.

        This is to inform any new instances of Bookmarks that they need to start in
        solo mode if the a instance with a non-solo mode is already running.

        """
        path = get_lockfile_path()
        lockfile_info = QtCore.QFileInfo(path)
        lockfile_info.dir().mkpath(u'.')
        with open(path, 'w+') as f:
            f.write(u'{}'.format(int(self.current_mode())))

    @prune_lockfile
    def get_mode(self):
        """Return the current application mode."""
        lockfile_info = QtCore.QFileInfo(get_lockfile_path())
        for entry in _scandir.scandir(lockfile_info.path()):
            if entry.is_dir():
                continue
            path = entry.path
            if not path.endswith(u'.lock'):
                continue
            with open(path, 'r') as f:
                data = f.read()
            try:
                data = int(data.strip())
                if data == common.SynchronisedMode:
                    log.debug(u'Current application mode is `SoloMode`')
                    return common.SoloMode
            except:
                log.error(u'Error getting the current application mode.')

        log.debug(u'Current application mode is `SynchronisedMode`')
        return common.SynchronisedMode

    def set_mode(self, val):
        self._current_mode = val

    def _load_persistent_bookmarks(self):
        """Loads any preconfigured bookmarks from the json config file.

        Returns:
            dict: The parsed data.

        """
        s = os.path.sep

        config = __file__ + s + os.pardir + s + u'rsc' + s + u'persistent_bookmarks.json'
        config = os.path.abspath(os.path.normpath(config))
        if not os.path.isfile(config):
            log.error(u'persistent_bookmarks.json not found.')
            return {}

        data = {}
        try:
            with open(config, 'r') as f:
                data = json.load(f)
        except (ValueError, TypeError):
            log.error(u'Could not decode `persistent_bookmarks.json`')
        except RuntimeError:
            log.error(u'Error opening `persistent_bookmarks.json`')
        finally:
            return data

    def bookmarks(self):
        """Returns available bookmarks.

        The list of bookmarks is made up of a list of persistent bookmarks, kept
        in the `persistent_bookmarks.json`, and bookmarks added manually by the
        user (stored in the `local_settings`).

        Each bookmark is represented as a dictionary entry:

        .. code-block:: python

            {
                'myserver/myjob/myroot': {
                    'server': 'myserver',
                    'job': 'myjob',
                    'root': 'myroot'
                }
            }

        Returns:
            dict:   A dictionary containing all currently available bookmarks.

        """
        _persistent = self._load_persistent_bookmarks()
        _persistent = _persistent if _persistent else {}
        _custom = self.value(u'bookmarks')
        _custom = _custom if _custom else {}

        bookmarks = _persistent.copy()   # start with x's keys and values
        bookmarks.update(_custom)    # modifies z with y's keys and values & returns None
        return bookmarks

    def prune_bookmarks(self):
        """Removes all invalid bookmarks from the current list."""
        bookmarks = self.value(u'bookmarks')
        bookmarks = bookmarks if bookmarks else {}

        if not bookmarks:
            return

        _valid = {}
        _invalid = []
        for k, v in bookmarks.iteritems():
            if not QtCore.QFileInfo(k).exists():
                _invalid.append(k)
                continue
            _valid[k] = v

        self.setValue(u'bookmarks', _valid)
        s = u'Bookmarks pruned:\n{}'.format(u'\n'.join(_invalid))

        from . import common_ui
        common_ui.OkBox(u'Bookmarks pruned. Refresh the list to see the changes.', s).open()
        log.success(s)


    def favourites(self):
        """Get all saved favourites as a list

        Returns:
            list: A list opf file paths the user marked favourite.

        """
        v = self.value(u'favourites')
        if isinstance(v, (str, unicode)):
            v = [v, ]
        v = [f.strip() for f in v] if v else []
        return v


local_settings = LocalSettings()
# local_settings.prune_bookmarks()
"""Global local settings instance."""
