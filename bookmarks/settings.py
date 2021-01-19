# -*- coding: utf-8 -*-
"""Contains :class:`.Settings`, a customized QSettings instance  used to
store active paths, widget and user options.

Also contains the session lock used to `lock` a running Bookmark instance. See
:func:`.get_lockfile_path` and the relevant functions in :class:`.Settings`.

.. code-block:: python

    favourites = local_settings.get_favourites()

"""
import collections
import os
import json
import re
import functools
import psutil

import _scandir

from PySide2 import QtCore

from . import log
from . import common



local_settings = None
ACTIVE = collections.OrderedDict()
LOCAL_SETTINGS_FILE_NAME = u'local_settings.ini'



ActiveSection = u'Active'
ServerKey = u'Server'
JobKey = u'Job'
RootKey = u'Root'
AssetKey = u'Asset'
TaskKey = u'Task'
FileKey = u'File'

CurrentUserPicksSection = u'UserPicks'
ServersKey = u'Servers'
BookmarksKey = u'Bookmarks'
FavouritesKey = u'Favourites'

SettingsSection = u'Settings'
FFMpegKey = u'FFMpegPath'
RVKey = u'RVPath'
UIScaleKey = u'UIScale'
InstanceSyncKey = u'InstanceSync'
WorkspaceSyncKey = u'WorkspaceSync'
WorksapceWarningsKey = u'WorkspaceWarnings'
SaveWarningsKey = u'SaveWarnings'
PushCaptureToRVKey = u'PushCaptureToRV'
RevealCaptureKey = u'RevealCapture'


ListFilterSection = u'ListFilters'
ActiveFlagFilterKey = u'ActiveFilter'
ArchivedFlagFilterKey = u'ArchivedFilter'
FavouriteFlagFilterKey = u'FavouriteFilter'
TextFilterKey = u'TextFilter'

UIStateSection = u'UIState'
WindowGeometryKey = u'WindowGeometry'
WindowStateKey = u'WindowState'
SortByBaseNameKey = u'SortByBaseName'
WindowAlwaysOnTopKey = u'WindowAlwaysOnTop'
WindowFramelessKey = u'WindowFrameless'
InlineButtonsHidden = u'InlineButtonsHidden'
CurrentRowHeight = u'CurrentRowHeight'
CurrentList = u'CurrentListIdx'
CurrentSortRole = u'CurrentSortRole'
CurrentSortOrder = u'CurrentSortOrder'
CurrentDataType = u'CurrentDataType'
GenerateThumbnails = u'GenerateThumbnails'
FileSelectionKey = u'FileSelection'
SequenceSelectionKey = u'FileSequenceSelection'
BookmarkEditorServerKey = u'BookmarkEditorServer'
BookmarkEditorJobKey = u'BookmarkEditorJob'
SlackUserKey = u'SlackUser'

FileSaverSection = u'FileSaver'
CurrentFolderKey = u'CurrentFolder'
CurrentTemplateKey = u'CurrentTemplate'

SGUserKey = u'SGUser'
SGStorageKey = u'SGStorage'
SGTypeKey = u'SGType'




ACTIVE_KEYS = (
    ServerKey,
    JobKey,
    RootKey,
    AssetKey,
    TaskKey,
    FileKey
)


def strip(s):
    return re.sub(
        ur'\\', u'/',
        s,
        flags=re.UNICODE | re.IGNORECASE
    ).strip().rstrip(u'/')


def _bookmark_key(*args):
    k = u'/'.join([strip(f) for f in args]).rstrip(u'/')
    return k


def set_active(k, v):
    if local_settings is None:
        raise RuntimeError(u'Settings is not initialized.')
    if k not in ACTIVE_KEYS:
        raise KeyError(u'"{}" is an invalid key. Expected one of: {}'.format(k, ACTIVE_KEYS))
    local_settings.setValue(ActiveSection, k, v)
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
    @functools.wraps(func)
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


class Settings(QtCore.QSettings):
    """An `ini` config file to store all local user settings.

    This is where the current bookmarks, saved favourites, active bookmark,
    assets and files and other widget states are kept.

    Active Path:
        The active path is saved in the following segments:

        * ActiveSection/ServerKey (unicode):    Server, eg. '//server/data'.
        * ActiveSection/JobKey (unicode):       Job folder name inside the server.
        * ActiveSection/RootKey (unicode):      Job-relative bookmark path, eg. 'seq_010/shots'.
        * ActiveSection/AssetKey (unicode):     Job folder name inside the root, eg. 'shot_010'.
        * ActiveSection/TaskKey (unicode):      A folder, eg. 'scenes', 'renders', etc.
        * ActiveSection/FileKey (unicode):      A relative file path.

    """
    serversChanged = QtCore.Signal()
    favouritesChanged = QtCore.Signal()
    bookmarksChanged = QtCore.Signal()

    def __init__(self, parent=None):
        self.config_path = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation)
        self.config_path = u'{}/{}/{}'.format(
            self.config_path,
            common.PRODUCT,
            LOCAL_SETTINGS_FILE_NAME
        )

        super(Settings, self).__init__(
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
        self.get_servers()

    def get_servers(self):
        """Loads and returns a list of saved servers from the ini config file.

        The results are cached to `common.SERVERS`.

        """
        self.sync()

        val = self.value(CurrentUserPicksSection, ServersKey)
        if not val:
            common.SERVERS = []
            return common.SERVERS

        # Will return a string if only one server is stored in the settings
        if isinstance(val, (str, unicode)):
            common.SERVERS = [strip(val), ]
            return common.SERVERS

        common.SERVERS = sorted(set([strip(f) for f in val]))
        return common.SERVERS

    def set_servers(self, v):
        if not isinstance(v, (tuple, list)):
            raise TypeError(u'Expect a list, got "{}"'.format(type(v)))

        common.SERVERS = sorted(set([strip(f) for f in v]))
        self.setValue(CurrentUserPicksSection, ServersKey, common.SERVERS)

        self.serversChanged.emit()
        return common.SERVERS

    def value(self, section, key):
        """Used to retrieve a values from the local settings object.

        Overrides the default `value()` method to provide type checking.
        Types are saved in `{key}_type`.

        Args:
            section (unicode):  A section name.
            key (unicode): A key name.

        Returns:
            The value stored in `local_settings` or `None` if not found.

        """
        k = u'{}/{}'.format(section, key)
        if self.current_mode() and section == ActiveSection:
            if k not in self.INTERNAL_SETTINGS_DATA:
                v = super(Settings, self).value(k)
                self.INTERNAL_SETTINGS_DATA[k] = v
            return self.INTERNAL_SETTINGS_DATA[k]

        t = super(Settings, self).value(k  + u'_type')
        v = super(Settings, self).value(k)
        if v is None:
            return

        try:
            if t == u'NoneType':
                v = None
            elif t == u'bool':
                # Convert any loose representation back to `bool()`
                if not isinstance(v, bool):
                    if v.lower() in [u'true', u'1']:
                        v = True
                    elif v.lower() in [u'false', u'0', 'none']:
                        v = False
            elif t == u'str' and not isinstance(v, unicode):
                v = v.encode('utf-8')
            elif t == u'unicode' and not isinstance(v, unicode):
                try:
                    v = unicode(v, 'utf-8')
                except:
                    pass
            elif t == u'int' and not isinstance(v, int):
                v = int(v)
            elif t == u'float' and not isinstance(v, float):
                v = float(v)
        except:
            log.error('Type converion failed')

        return v

    def setValue(self, section, key, v):
        """Override to allow redirecting `ActiveSection` keys to be saved in memory
        when solo mode is on.

        """
        k = u'{}/{}'.format(section, key)
        if self.current_mode() and section == ActiveSection:
            self.INTERNAL_SETTINGS_DATA[k] = v
            return
        super(Settings, self).setValue(k, v)
        super(Settings, self).setValue(k + u'_type', type(v).__name__)

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
        self.sync()

        for k in ACTIVE_KEYS:
            ACTIVE[k] = self.value(ActiveSection, k)

        # Let's check the path and unset any invalid parts
        path = u''
        for k in ACTIVE:
            if ACTIVE[k]:
                path += ACTIVE[k]
            if not QtCore.QFileInfo(path).exists():
                ACTIVE[k] = None
                self.setValue(ActiveSection, k, None)
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

    def get_favourites(self):
        """Get all saved favourites.

        Returns:
            list: A list of file paths the user marked favourite.

        """
        self.sync()

        v = self.value(CurrentUserPicksSection, FavouritesKey)

        if isinstance(v, (str, unicode)):
            v = [v, ]
        elif isinstance(v, (list, tuple)):
            v = [f.strip() for f in v] if v else []
        else:
            v = []

        return v

    def add_favourites(self, v):
        """Adds the given list to the currently saved favourites.

        """
        if not isinstance(v, (tuple, list)):
            raise TypeError(u'Expect a list, got "{}"'.format(type(v)))

        v = sorted(set(v) | set(self.get_favourites()))
        self.setValue(CurrentUserPicksSection, FavouritesKey, v)
        self.favouritesChanged.emit()

    def remove_favourites(self, v):
        """Removes the given list from the currently saved favourites.

        """
        if not isinstance(v, (tuple, list)):
            raise TypeError(u'Expect a list, got "{}"'.format(type(v)))

        v = sorted(set(self.get_favourites()) - set(v))
        self.setValue(CurrentUserPicksSection, FavouritesKey, v)
        self.favouritesChanged.emit()

    def clear_favourites(self):
        """Removes the given list from the currently saved favourites.

        """
        self.sync()
        self.setValue(CurrentUserPicksSection, FavouritesKey, [])
        self.favouritesChanged.emit()

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

    def get_bookmarks(self):
        """Returns available bookmarks.

        The list of bookmarks is made up of a list of persistent bookmarks, defined
        in `persistent_bookmarks.json`, and bookmarks added manually by the
        user, stored in the `local_settings`.

        Each bookmark is represented as a dictionary entry:

        .. code-block:: python

            v = {
                u'//my_server/my_job/path/to/my_root_folder': {
                    ServerKey: u'//my_server',
                    JobKey: u'my_job',
                    RootKey: u'path/to/my_root_folder'
                }
            }

        Returns:
            dict:   A dictionary containing all currently available bookmarks.

        """
        self.sync()

        _persistent = self._load_persistent_bookmarks()
        _persistent = _persistent if _persistent else {}

        _custom = self.value(CurrentUserPicksSection, BookmarksKey)
        _custom = _custom if _custom else {}

        bookmarks = _persistent.copy()
        bookmarks.update(_custom)

        return bookmarks

    def prune_bookmarks(self):
        """Removes all invalid bookmarks from the current list."""
        bookmarks = self.value(CurrentUserPicksSection, BookmarksKey)

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

        self.setValue(CurrentUserPicksSection, BookmarksKey, _valid)
        self.bookmarksChanged.emit()

    @QtCore.Slot(unicode)
    @QtCore.Slot(unicode)
    @QtCore.Slot(unicode)
    def save_bookmark(self, server, job, root):
        """Save a bookmark to `local_settings`.

        """
        v = self.get_bookmarks()
        v = v if isinstance(v, dict) else {}

        k = _bookmark_key(server, job, root)
        if k in v:
            return

        v[k] = {
            ServerKey: server,
            JobKey:  job,
            RootKey:  root
        }
        self.setValue(CurrentUserPicksSection, BookmarksKey, v)
        self.bookmarksChanged.emit()

    @QtCore.Slot(unicode)
    @QtCore.Slot(unicode)
    @QtCore.Slot(unicode)
    def remove_bookmark(self, server, job, root):
        """Remove a bookmark from `local_settings`.

        """
        # If the item is currently active, we'll have to unset it.
        if (
            ACTIVE[ServerKey] == server and
            ACTIVE[JobKey] == job and
            ACTIVE[RootKey] == root
        ):
            set_active(ServerKey, None)

        # Just in case there's a BookmarkDB instance already open:
        from . import bookmark_db
        bookmark_db.remove_db(server, job, root)

        self.sync()
        v = self.value(CurrentUserPicksSection, BookmarksKey)
        if not v:
            return

        k = _bookmark_key(server, job, root)
        if k not in v:
            return

        del v[k]
        self.setValue(CurrentUserPicksSection, BookmarksKey, v)
        self.bookmarksChanged.emit()



local_settings = Settings()
"""Global local settings instance."""
