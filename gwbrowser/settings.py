# -*- coding: utf-8 -*-
"""``settings.py`` contains the classes needed to get and set settings for
the application and the asset and file items.
"""

import hashlib
import collections
from PySide2 import QtCore

import gwbrowser.common as common


class Active(QtCore.QObject):
    """Utility class to querry and monitor the changes to the active paths.

    Active paths are set by the ``LocalSettings`` module and are stored in the
    registry at ``HKEY_CURRENT_USER/SOFTWARE/COMPANY/PRODUCT.``

    The fully set active path is made up of the ``server``, ``job``, ``root``,
    ``asset``, ``location`` and ``file`` components.

    """
    # Signals
    activeBookmarkChanged = QtCore.Signal()
    activeAssetChanged = QtCore.Signal()
    activeLocationChanged = QtCore.Signal(unicode)
    activeFileChanged = QtCore.Signal(unicode)

    keys = (u'server', u'job', u'root', u'asset', u'location', u'file')

    def __init__(self, parent=None):
        super(Active, self).__init__(parent=parent)
        # self.macos_mount_timer = QtCore.QTimer()
        # self.macos_mount_timer.setInterval(2000)
        # self.macos_mount_timer.setSingleShot(False)
        # self.macos_mount_timer.timeout.connect(common.mount)
        # common.mount()

        self._active_paths = self.paths()

    @QtCore.Slot(unicode)
    @QtCore.Slot(unicode)
    def save_state(self, k, d):
        self._active_paths[k] = d

    @QtCore.Slot()
    def check_state(self):
        """This method is called by the timeout slot of the `Active.timer` and
        check the currently set active item. Emits a changed signal if the
        current state differs from the saved state.

        """

        active_paths = self.paths()

        if self._active_paths == active_paths:
            return

        serverChanged = self._active_paths[u'server'] != active_paths[u'server']
        jobChanged = self._active_paths[u'job'] != active_paths[u'job']
        rootChanged = self._active_paths[u'root'] != active_paths[u'root']
        assetChanged = self._active_paths[u'asset'] != active_paths[u'asset']
        locationChanged = self._active_paths[u'location'] != active_paths[u'location']
        fileChanged = self._active_paths[u'file'] != active_paths[u'file']

        if serverChanged or jobChanged or rootChanged:
            self.activeBookmarkChanged.emit()
            self._active_paths = active_paths
            return

        if assetChanged:
            self.activeAssetChanged.emit()
            self._active_paths = active_paths
            return

        if locationChanged:
            self.activeLocationChanged.emit(active_paths[u'location'])

        if fileChanged:
            self.activeFileChanged.emit(active_paths[u'file'])

        self._active_paths = active_paths

    @classmethod
    def paths(cls):
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
        active_path = Active.paths()
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
            common.COMPANY,
            common.PRODUCT,
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

    def __init__(self, index, args=None, parent=None):
        """Primarily expects a QModelIndex but when it's not possible to provide,
        it takes a tuple bookmark tuple of server, job, root and a full filepath.

        """
        if args is None:
            bookmark = u'{}/{}/{}'.format(
                index.data(common.ParentRole)[0],
                index.data(common.ParentRole)[1],
                index.data(common.ParentRole)[2],
            )
            _bookmark = u'{}/{}'.format(
                index.data(common.ParentRole)[1],
                index.data(common.ParentRole)[2],
            )
            filepath = index.data(QtCore.Qt.StatusTipRole)
        else:
            bookmark = u'{}/{}/{}'.format(
                args[0],
                args[1],
                args[2],
            )
            _bookmark = u'{}/{}'.format(
                args[1],
                args[2],
            )
            filepath = args[3]

        collapsed = common.is_collapsed(filepath)
        if collapsed:
            filepath = collapsed.expand(ur'\1[0]\3')

        path = u'{}/{}'.format(
            _bookmark,
            filepath.replace(bookmark, u'').strip(u'/')).strip(u'/')
        path = hashlib.md5(path.encode('utf-8')).hexdigest()

        self._conf_path = u'{}/.browser/{}.conf'.format(bookmark, path)
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
            //server/job/root/.browser/986613d368816aa7e0ae910dfd863297.conf
            //server/job/root/.browser/986613d368816aa7e0ae910dfd863297.png

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
