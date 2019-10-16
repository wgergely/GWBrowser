# -*- coding: utf-8 -*-
"""``settings.py`` contains the classes needed to get and set settings for
the application and the asset and file items.
"""

import time
import hashlib
import collections
from PySide2 import QtCore

import gwbrowser.common as common

SOLO = False


def _bool(v):
    """Converts True/False/None to their valid values."""
    if isinstance(v, basestring):
        if v.lower() == u'true':
            return True
        elif v.lower() == u'false':
            return False
        elif v.lower() == u'none':
            return None
        if not v:
            return None
    return v


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
        self.macos_mount_timer = QtCore.QTimer(parent=self)
        self.macos_mount_timer.setInterval(5000)
        self.macos_mount_timer.setSingleShot(False)
        self.macos_mount_timer.timeout.connect(common.mount)
        common.mount()

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
        # When active sync is disabled we won't
        val = local_settings.value(
            'preferences/MayaSettings/disable_active_sync')
        if val is True:
            return

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
        self.internal_settings = {}

    def value(self, k):
        """An override for the default get value method.

        When solo mode is on we have to disable saving `activepath` values to
        the local settings and redirect querries instead to a temporary proxy
        dictionary.

        """
        if SOLO and k.lower().startswith(u'activepath'):
            if k not in self.internal_settings:
                v = super(LocalSettings, self).value(k)
                self.internal_settings[k] = _bool(v)
            return self.internal_settings[k]
        return _bool(super(LocalSettings, self).value(k))

    def setValue(self, k, v):
        """This is a global override for our preferences to disable the setting
        of the active path settings.

        """
        if SOLO and k.lower().startswith(u'activepath'):
            self.internal_settings[k] = v
            return
        super(LocalSettings, self).setValue(k, v)


class AssetSettings(QtCore.QSettings):
    """Provides the file paths and the data of asset's configuration file and
    cached thumbnail.

    The settings are stored in the current bookmark folder, eg:
    `{bookmark}/.browser/986613d368816aa7e0ae910dfd863297.conf`, or
    `{bookmark}/.browser/986613d368816aa7e0ae910dfd863297.png`

    The file-name is generated based on the file or folder's path name relative
    to the current bookmark folder using a md5 hash. For instance,
    `//{server}/{job}/{bookmark}/asset/myfile.ma will take *asset/myfile.ma*
    to generate the hash and will return
    `//{server}/{job}/{bookmark}/.browser/986613d368816aa7e0ae910dfd863297.conf`
    as the configuration file's path.

    The asset settings object takes a ``QModelIndex`` (note: the index should
    contain a valid value for `common.ParentPathRole`), otherwise, the
    server, job, and bookmark folders can be passed manually when a QModelIndex
    is not available.

    Example:

        .. code-block:: python

        index = list_widget.currentIndex() # QtCore.QModelIndex settings =
        AssetSettings(index)
        settings.config_path()
        settings.thumbnail_path()

    """

    def __init__(self, index=QtCore.QModelIndex(), server=None, job=None, root=None, filepath=None, parent=None):
        if index.isValid():
            parents = index.data(common.ParentPathRole)
            if not parents:
                raise RuntimeError('Index does not contain a valid parent path information')
            server, job, root = parents[0:3]
            filepath = index.data(QtCore.Qt.StatusTipRole)

        hash = self.hash(server, job, root, filepath)
        config_path = u'{server}/{job}/{root}/.browser/{hash}.conf'.format(
            server=server,
            job=job,
            root=root,
            hash=hash
        )
        print config_path

        self._file_path = filepath
        self._config_path = config_path
        self._thumbnail_path = config_path.replace(u'.conf', u'.png')

        super(AssetSettings, self).__init__(
            self.config_path(),
            QtCore.QSettings.IniFormat,
            parent=parent
        )
        self.setFallbacksEnabled(False)

    @staticmethod
    def hash(server, job, root, filepath):
        # Sequences have their own asset setting and because the sequence frames might
        # change we will use a generic name instead of the current in-out frames
        collapsed = common.is_collapsed(filepath)
        if collapsed:
            filepath = collapsed.expand(ur'\1[0]\3')
        path = filepath.replace(server, u'').strip(u'/')
        path = hashlib.md5(path.encode(u'utf-8')).hexdigest()
        return path



    def config_path(self):
        """The path of the configuration file associated with the current file.

        For example:
            //server/job/root/.browser/986613d368816aa7e0ae910dfd863297.conf

        Returns:
            unicode: The path to the configuration file as a string.

        """
        return self._config_path

    def thumbnail_path(self):
        """The path of the saved thumbnail associated with the current file."""
        return self._thumbnail_path

    def value(self, k):
        return _bool(super(AssetSettings, self).value(k))

    def setValue(self, k, v):
        """Adding a pointer to the original file and a timestamp as well."""
        super(AssetSettings, self).setValue(u'file', self._file_path)
        super(AssetSettings, self).setValue(u'lastmodified', time.time())
        super(AssetSettings, self).setValue(k, v)


local_settings = LocalSettings()
