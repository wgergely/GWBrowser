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
import hashlib
import collections
from PySide2 import QtCore

import browser.common as common


# Flags
MarkedAsArchived = 0b1000000000
MarkedAsFavourite = 0b10000000000
MarkedAsActive = 0b100000000000

COMPANY = u'Glassworks'
PRODUCT = u'Browser'


class Active(QtCore.QObject):
    """Utility class to querry and monitor the active paths.

    Active paths are set by the ``LocalSettings`` module and are stored
    in the registry HKEY_CURRENT_USER/SOFTWARE/COMPANY/PRODUCT.

    The fully set active path is made up of the 'server', 'job', 'root', 'asset',
    'location' and 'file' components.

    """
    # Signals
    activeBookmarkChanged = QtCore.Signal(tuple)
    activeAssetChanged = QtCore.Signal(tuple)
    activeLocationChanged = QtCore.Signal(basestring)
    activeFileChanged = QtCore.Signal(basestring)

    keys = (u'server', u'job', u'root', u'asset', u'location', u'file')

    def __init__(self, parent=None):
        super(Active, self).__init__(parent=parent)
        self._active_paths = self.get_active_paths()

        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self._check_change)

    def update_saved_state(self, k, data):
        self._active_paths[k] = data

    def _check_change(self):
        active_paths = self.get_active_paths()
        if self._active_paths == active_paths:
            return

        serverChanged = self._active_paths[u'server'] != active_paths[u'server']
        jobChanged = self._active_paths[u'job'] != active_paths[u'job']
        rootChanged = self._active_paths[u'root'] != active_paths[u'root']
        assetChanged = self._active_paths[u'asset'] != active_paths[u'asset']
        locationChanged = self._active_paths[u'location'] != active_paths[u'location']
        fileChanged = self._active_paths[u'file'] != active_paths[u'file']

        if serverChanged or jobChanged or rootChanged:
            self.activeBookmarkChanged.emit((
                active_paths[u'server'],
                active_paths[u'job'],
                active_paths[u'root'],
            ))
        if assetChanged:
            self.activeAssetChanged.emit((
                active_paths[u'server'],
                active_paths[u'job'],
                active_paths[u'root'],
                active_paths[u'asset'],
            ))
        if locationChanged:
            self.activeLocationChanged.emit(active_paths[u'location'])
        if fileChanged:
            self.activeFileChanged.emit(active_paths[u'file'])

        self._active_paths = active_paths

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
            d[k] = local_settings.value(u'activepath/{}'.format(k))

        # Checking active-path and unsetting invalid parts
        path = u''
        for idx, k in enumerate(d):
            if d[k]:
                path += u'/{}'.format(common.get_sequence_startpath(d[k]))
                if idx == 0:
                    path = d[k]
            if not QtCore.QFileInfo(path).exists():
                local_settings.setValue(u'activepath/{}'.format(k), None)
                d[k] = None

        return d

    @staticmethod
    def get_active_path():
        """Returns the currently set, existing ``active`` path as a string.

        Returns:
            str or None: The currently set active path.

        """
        paths = []
        active_path = Active.get_active_paths()
        for k in active_path:
            if not active_path[k]:
                break

            paths.append(active_path[k])
            path = u'/'.join(paths)
            path = common.get_sequence_endpath(path)
            if not QtCore.QFileInfo(path).exists():
                break

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
            PRODUCT,
            parent=parent
        )
        self.setDefaultFormat(QtCore.QSettings.NativeFormat)

    def value(self, *args, **kwargs):
        val = super(LocalSettings, self).value(*args, **kwargs)
        if not val:
            return None
        if isinstance(val, basestring):
            if val.lower() == u'true':
                return True
            elif val.lower() == u'false':
                return False
            elif val.lower() == u'none':
                return None
        return val


class AssetSettings(QtCore.QSettings):
    """Wrapper class for QSettings for storing asset and file settings.

    The asset settings will be stored as an ``.conf`` files in the
    ``[asset root]/.browser`` folder.

    """

    def __init__(self, index, parent=None):
        """Primarily expects a QModelIndex but when it's not possible to provide,
        it takes a tuple bookmark tuple of server, job, root and a full filepath.

        """
        if isinstance(index, (QtCore.QModelIndex, QtCore.QPersistentModelIndex)):
            self._root = u'{server}/{job}/{root}'.format(
                server=index.data(common.ParentRole)[0],
                job=index.data(common.ParentRole)[1],
                root=index.data(common.ParentRole)[2],
            )
            self._filepath = index.data(QtCore.Qt.StatusTipRole)
        else:
            self._root = u'{server}/{job}/{root}'.format(
                server=index[0],
                job=index[1],
                root=index[2],
            )
            self._filepath = index[3]

        path = self._filepath.replace(self._root, u'').strip(u'/')
        path = hashlib.md5(path.encode('utf-8')).hexdigest()
        self._conf_path = u'{}/.browser/{}.conf'.format(self._root, path)
        self._thumbnail_path = self._conf_path.replace(u'.conf', u'.png')

        super(AssetSettings, self).__init__(
            self.conf_path(),
            QtCore.QSettings.IniFormat,
            parent=parent
        )

        self.setFallbacksEnabled(False)



    def conf_path(self):
        """The configuration files associated with assets are stored in
        the root folder of the current bookmark.

        For example:
            //server/job/root/.browser/986613d368816aa7e0ae9144c65107ee0a1b10bdba14177f2f35ee0dfd863297.conf

        Returns:
            str: The path to the configuration file as a string.

        """
        return self._conf_path

    def thumbnail_path(self):
        return self._thumbnail_path

    def value(self, *args, **kwargs):
        val = super(AssetSettings, self).value(*args, **kwargs)
        if not val:
            return None
        if isinstance(val, basestring):
            if val.lower() == u'true':
                return True
            elif val.lower() == u'false':
                return False
            elif val.lower() == u'none':
                return None
        return val


local_settings = LocalSettings()
active_monitor = Active()
"""An instance of the local configuration created when loading this module."""
