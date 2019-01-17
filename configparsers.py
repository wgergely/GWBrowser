# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101
"""Config file reader for maya assets.

The ConfigParser allows setting comments and custom properties
for individual scene files or assets.

Attributes:
    archived (bool):            The status of the current item.
    description (str):          The description of the current item.

To retrieve the config file path, or the associated thumbnail you can use
getConfigPath() or getThumbnailPath().

"""


import re
import collections
from PySide2 import QtCore


# Flags
MarkedAsArchived = 0b100000000
MarkedAsFavourite = 0b1000000000
MarkedAsActive = 0b10000000000

COMPANY = 'Glassworks'
APPLICATION = 'Browser'


class ActivePathMonitor(QtCore.QObject):
    """Utility class to help monitor active path changes.
    When a path-change is detected, the activeChanged signal is emited.

    """
    # Signals
    activeChanged = QtCore.Signal(collections.OrderedDict)

    def __init__(self, parent=None):
        super(ActivePathMonitor, self).__init__(parent=parent)
        self.timer = QtCore.QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.update_path)

        self.active_path = ActivePathMonitor.get_active_path()

    @staticmethod
    def get_active_paths():
        """Returns the currently set ``active`` paths as a dictionary.
        Before returning the values we validate wheather the
        saved path refers to an existing folder. The invalid items will be unset.

        Note:
            When the path is fully set it is made up of
            `server`/`job`/`root`/`asset`/`file` elements.

        Returns:
            OrderedDict: Object containing the set active path items.

        """
        d = collections.OrderedDict()
        d['server'] = local_settings.value('activepath/server')
        d['job'] = local_settings.value('activepath/job')
        d['root'] = local_settings.value('activepath/root')
        d['asset'] = local_settings.value('activepath/asset')
        d['file'] = local_settings.value('activepath/file')

        # Checking whether the active-path actually exists
        path = ''
        for k in d:
            path += '{}/'.format(d[k])
            if not QtCore.QFileInfo(path).exists():
                local_settings.setValue('activepath/{}'.format(k), None)
                d[k] = None
        return d

    @staticmethod
    def get_active_path():
        """Returns the currently set ``active`` path as a string.

        Returns:
            str or None: The currently set active path.

        """
        path = ''
        active_path = ActivePathMonitor.get_active_paths()
        for k in active_path:
            if not active_path[k]:
                break
            path += '{}/'.format(active_path[k])
        return path if path else None

    def update_path(self):
        active_path = ActivePathMonitor.get_active_paths()
        for k in active_path:
            if self.active_path[k] == active_path[k]:
                continue
            self.active_path = active_path
            self.activeChanged.emit(active_path)
            print '# update_path()'


class LocalSettings(QtCore.QSettings):
    """Used to store all user-specific settings, such as list of favourites,
    widget settings and filter modes.

    The current path settings are stored under the ``activepath`` section.

    Activepath keys:
        activepath/server:  Path of the `active` server.
        activepath/job:     Name of the `active` job folder.
        activepath/root:    The name of the relative location of the active bookmark.
        activepath/asset:   The name of the `active` asset folder
        activepath/file:    The relative path of the `active` file.

    """

    def __init__(self, parent=None):
        super(LocalSettings, self).__init__(
            QtCore.QSettings.UserScope,
            COMPANY,
            APPLICATION,
            parent=parent
        )
        self.setDefaultFormat(QtCore.QSettings.NativeFormat)

    def value(self, *args, **kwargs):
        val = super(LocalSettings, self).value(*args, **kwargs)
        if not val:
            return None
        if isinstance(val, basestring):
            if val.lower() == 'true':
                return True
            elif val.lower() == 'false':
                return False
            elif val.lower() == 'none':
                return None
        return val


class AssetSettings(QtCore.QSettings):
    """Wrapper class for QSettings for storing asset and file settings.

    The asset settings will be stored as an ``.conf`` files in the
    ``[asset root]/.browser`` folder.

    """

    def __init__(self, path, parent=None):
        self._path = path
        super(AssetSettings, self).__init__(
            self.conf_path(),
            QtCore.QSettings.IniFormat,
            parent=parent
        )
        self.setFallbacksEnabled(False)

    def conf_path(self):
        """Returns the path to the Asset's configuration file.
        If the parent folder doesn't exists we will automatically create it here.

        Returns:
            str: The path to the configuration file as a string.

        """
        file_info = QtCore.QFileInfo(self._path)
        file_name = re.sub(r'[\.]+', '_', file_info.fileName())

        conf_path = '{}/.browser/{}.conf'.format(file_info.path(), file_name)
        if file_info.dir().exists():
            dir_ = QtCore.QDir('{}/.browser'.format(file_info.path()))
            if not dir_.exists():
                file_info.dir().mkpath('.browser')
                print '# Asset config root folder created.'
        return conf_path

    def thumbnail_path(self):
        file_info = QtCore.QFileInfo(self._path)
        path = '{}/.browser/{}'.format(file_info.path(),
                                       re.sub(r'[\.]+', '_', file_info.fileName()))
        return r'{}.png'.format(path)

    def value(self, *args, **kwargs):
        val = super(AssetSettings, self).value(*args, **kwargs)
        if not val:
            return None
        if isinstance(val, basestring):
            if val.lower() == 'true':
                return True
            elif val.lower() == 'false':
                return False
            elif val.lower() == 'none':
                return None
        return val


local_settings = LocalSettings()
path_monitor = ActivePathMonitor()
"""An instance of the local configuration created when loading this module."""
