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

import browser.common as common


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

    keys = ('server', 'job', 'root', 'asset', 'location', 'file')

    def __init__(self, parent=None):
        super(ActivePathMonitor, self).__init__(parent=parent)

    @classmethod
    def get_active_paths(cls):
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
        for k in cls.keys:
            d[k] = local_settings.value('activepath/{}'.format(k))

        # Checking active-path and unsetting invalid parts
        path = ''
        for idx, k in enumerate(d):
            if d[k]:
                path += '/{}'.format(common.get_sequence_startpath(d[k]))
                if idx == 0:
                    path = d[k]
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


class LocalSettings(QtCore.QSettings):
    """Used to store all user-specific settings, such as list of favourites,
    widget settings and filter modes.

    The current path settings are stored under the ``activepath`` section.

    Activepath keys:
        activepath/server: `Active` server (eg. '//server/data')
        activepath/job: `Active` job folder inside the server (eg. 'audible_0001')
        activepath/root: `Active` bookmark folder inside the job folder (eg. 'seq_010/shots').
        activepath/asset: `Active` asset folder in side the root folder (eg. 'shot_010').
        activepath/location:  `Active` location inside the asset folder (eg. ``common.RendersFolder``).
        activepath/file:    The relative path to the `active` file (eg. 'subfolder/mayascene_v001.ma').

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

    def __init__(self, index, parent=None):
        """Init accepts either a model index or a tuple."""
        if isinstance(index, QtCore.QModelIndex):
            self._root = '{server}/{job}/{root}'.format(
                server=index.data(common.ParentRole)[0],
                job=index.data(common.ParentRole)[1],
                root=index.data(common.ParentRole)[2],
            )
            self._filepath = index.data(QtCore.Qt.StatusTipRole)
        else:
            self._root = '{server}/{job}/{root}'.format(
                server=index[0],
                job=index[1],
                root=index[2],
            )
            self._filepath = index[3]

        super(AssetSettings, self).__init__(
            self.conf_path(),
            QtCore.QSettings.IniFormat,
            parent=parent
        )

        self.setFallbacksEnabled(False)

    def conf_path(self):
        """Returns the path to the Asset's configuration file.

        Returns:
            str: The path to the configuration file as a string.

        """
        def beautify(text):
            match = re.search(r'(\[.*\])', text)
            if match:
                text = text.replace(match.group(1), 'SEQ')
            return re.sub(r'[^a-zA-Z0-9/]+', '_', text)

        path = self._filepath.replace(self._root, '').strip('/')
        return '{}/.browser/{}.conf'.format(self._root, beautify(path))

    def thumbnail_path(self):
        return self.conf_path().replace('.conf', '.png')

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
