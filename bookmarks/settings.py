# -*- coding: utf-8 -*-
"""The local settings file used to store active paths, widget and user options.

Copyright (C) 2020 Gergely Wootsch

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <https://www.gnu.org/licenses/>.

"""

import collections
import os
import re
import psutil
from functools import wraps

from PySide2 import QtCore

import bookmarks.log as log
import bookmarks.common as common
import bookmarks._scandir as _scandir


ACTIVE_KEYS = (u'server', u'job', u'root', u'asset', u'location', u'file')


def _bool(v):
    """Converts True/False/None to their valid values."""
    if isinstance(v, basestring):
        if v.lower() == u'true':
            return True
        elif v.lower() == u'false':
            return False
        elif v.lower() == u'none':
            return None
        try:
            f = float(v)
            if f.is_integer():
                return int(f)
            return f
        except:
            return v
    return v


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
    """An `ini` based `QSettings` object to _get_ and _set_ app settings.

    The current path selection are stored under the ``activepath`` section.
    LocalSettings provides signals that respond to value changes of the
    `activepath` entried. This is used to sync Bookmarks's state with other
    running instances.

    Note:
        The fully set active path is made up of the ``server``, ``job``, ``root``,
        ``asset``, ``location`` and ``file`` components.

    `activepath` keys:
        activepath/server (unicode):    Server, eg. '//server/data'.
        activepath/job (unicode):       Job folder name inside the server.
        activepath/root (unicode):      Job-relative bookmark path, eg. 'seq_010/shots'.
        activepath/asset (unicode):     Job folder name inside the root, eg. 'shot_010'.
        activepath/location (unicode):  A mode folder, 'scenes', 'renders', etc.
        activepath/file (unicode):      Location-relative file path.

    """
    filename = u'settings.ini'
    keys = (u'server', u'job', u'root', u'asset', u'location', u'file')

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
        self._active_paths = self.verify_paths()

        # Simple timer to verify the state of the current changes
        self.server_mount_timer = QtCore.QTimer(parent=self)
        self.server_mount_timer.setInterval(15000)
        self.server_mount_timer.setSingleShot(False)
        self.server_mount_timer.setTimerType(QtCore.Qt.CoarseTimer)
        self.server_mount_timer.timeout.connect(self.verify_paths)

    def value(self, k):
        """An override for the default get value method.

        When solo mode is on we have to disable saving `activepath` values to
        the local settings and redirect querries instead to a temporary proxy
        dictionary.

        """
        if self.current_mode() and k.lower().startswith(u'activepath'):
            if k not in self.INTERNAL_SETTINGS_DATA:
                v = super(LocalSettings, self).value(k)
                self.INTERNAL_SETTINGS_DATA[k] = _bool(v)
            return self.INTERNAL_SETTINGS_DATA[k]
        return _bool(super(LocalSettings, self).value(k))

    def setValue(self, k, v):
        """This is a global override for our preferences to disable the setting
        of the active path settings.

        """
        if self.current_mode() and k.lower().startswith(u'activepath'):
            self.INTERNAL_SETTINGS_DATA[k] = v
            return
        super(LocalSettings, self).setValue(k, v)

    def current_mode(self):
        return self._current_mode

    @QtCore.Slot()
    def verify_paths(self):
        """This slot verifies and returns the saved ``active paths`` wrapped
        in a dictionary.

        If the resulting active path is not an existing file, we will
        progressively unset the invalid path segments until we get a valid file
        path. The slot does not emit any changed signals.

        Returns:
            OrderedDict:    Verified active paths.

        """
        d = collections.OrderedDict()
        for k in ACTIVE_KEYS:
            d[k] = self.value(u'activepath/{}'.format(k))

        # Let's check the path and unset the invalid parts
        path = u''
        for idx, k in enumerate(d):
            if d[k]:
                path += u'/{}'.format(common.get_sequence_startpath(d[k]))
                if idx == 0:
                    path = d[k]
            if not QtCore.QFileInfo(path).exists():
                self.setValue(u'activepath/{}'.format(k), None)
                d[k] = None
        return d

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

    def favourites(self):
        v = self.value(u'favourites')
        if isinstance(v, (str, unicode)):
            v = [v.lower(), ]
        v = [f.strip().lower() for f in v] if v else []
        return v


local_settings = LocalSettings()
