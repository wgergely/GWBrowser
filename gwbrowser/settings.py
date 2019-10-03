# -*- coding: utf-8 -*-
"""``settings.py`` contains the classes needed to get and set settings for
the application and the asset and file items.
"""

import time
import hashlib
import collections
from PySide2 import QtCore

import gwbrowser.common as common

SOLO = True


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
        val = local_settings.value('preferences/MayaSettings/disable_active_sync')
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
        def _bool(v):
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

        if SOLO:
            if k not in self.internal_settings:
                v = super(LocalSettings, self).value(k)
                self.internal_settings[k] = _bool(v)
            return self.internal_settings[k]
        return super(LocalSettings, self).value(k)

    def setValue(self, k, v):
        if SOLO:
            self.internal_settings[k] = v
        else:
            super(LocalSettings, self).setValue(k, v)


class AssetSettings(QtCore.QSettings):
    """This class is intended for reading and writing asset & file associated
    settings.

    Asset settings are stored in the root of the current bookmark in a folder
    called ``.browser``. There are usually two files associated with a folder or
    a file: a **.conf** and a **.png** image file.

    Each config file's name is generated based on the folder or file's path name
    relative to the current bookmark folder.

    For instance, if the file path is ``//server/job/bookmark/asset/myfile.ma``,
    the config name will be generated using ``asset/myfile.ma``.

    The resulting config files will look something like as below:

    .. code-block::

        //server/job/bookmark/.browser/986613d368816aa7e0ae910dfd863297.conf
        //server/job/bookmark/.browser/986613d368816aa7e0ae910dfd863297.png

    Example:

        .. code-block:: python

        index = list_widget.currentIndex() # QtCore.QModelIndex
        settings = AssetSettings(index)

        settings.conf_path()
        settings.thumbnail_path()

    Arguments:

        index (QtCore.QModelIndex): The index the instance will be associated
        args (tuple: server, job, root, filepath): It is not always
        possible to provide a QModelIndex but we can get around this by
        providing the path elements as a tuple.

    """
    def __init__(self, index, args=None, parent=None):
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

        self._file_path = filepath
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

    def setValue(self, *args, **kwargs):
        """Adding a pointer to the original file and a timestamp as well."""
        super(AssetSettings, self).setValue(u'file', self._file_path)
        super(AssetSettings, self).setValue(u'lastmodified', time.time())
        super(AssetSettings, self).setValue(*args, **kwargs)

local_settings = LocalSettings()
