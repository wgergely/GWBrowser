# -*- coding: utf-8 -*-
"""PySide2 dependent base-class for querring folders and files.

The values used to initialize the ``AssetCollector`` and the ``FileCollector.get_files()``
method are stored in a local configuration file. ``LocalSettings`` is used to edit
the stored values.

Example:

    .. code-block:: python
        :linenos:

        collector = AssetCollector(
            server='C:/temp',
            job='superjob',
            root='assets'
        )
        collector.set_active_item(item)

Example:

    .. code-block:: python
        :linenos:

        file_info = QtCore.QFileInfo('//server/job/asset')
        collector = FileCollector(file_info)
        scenes = collector.get_files(
            sort_order=0,
            reverse=False,
            filter='/subfolder/'
        )

"""
# pylint: disable=E1101, C0103, R0913, I1101

import re
from PySide2 import QtCore
from mayabrowser.configparsers import local_settings

class AssetCollector(object):
    """Object to collect folders and files from a specified file location.

    Args:
        server (str):                   Path to server where the jobs are located.
        job (str):                      The name of the current job.
        root (str):                     The job assets root folder name.

    Attributes:
        items (QFileInfo list):         List of the collected folders.
        active_item (QFileInfo):        The active QFileInfo item.
        active_index (int):             The index of ``active_item``.

    Methods:
        update(**kwargs):               Updates the collector with the new job, server and root paths.
        set_active_index (idx):         Sets the given QFileInfo object at `idx` in `items` to be the ``active_item``.
        set_active_item (QFileInfo):    Stores the given QFileInfo item as the ``active_item``.

    """

    def __init__(self, server=None, job=None, root=None):
        self._active_item = None
        self._active_index = None
        self._item_qis = []
        self._server_qi = None
        self._job_qi = None
        self._root_qi = None

        self._kwargs = {
            'server': server,
            'job': job,
            'root': root,
        }

        if not server:
            return
        if not job:
            return
        if not root:
            return

        self._server_qi = QtCore.QFileInfo(server)
        if not self._server_qi.exists():
            return

        self._job_qi = QtCore.QFileInfo(
            '{}/{}'.format(
                self._server_qi.filePath(),
                job
            )
        )
        if not self._job_qi.exists():
            return

        self._root_qi = QtCore.QFileInfo(
            '{}/{}'.format(
                self._job_qi.filePath(),
                root
            )
        )
        if not self._root_qi.exists():
            return

        # All good, ready to collect.
        self.collect_assets()

    @property
    def root_info(self):
        """The current QFileInfo object of the asset root."""
        return self._root_qi

    @property
    def active_item(self):
        """The active QFileInfo item."""
        try:
            return self.items[self._active_index]
        except TypeError:
            return None

    @property
    def active_index(self):
        """The index of the active item."""
        try:
            return self.items.index(self._active_item)
        except ValueError:
            return -1

    @property
    def items(self):
        """List of QFileInfo instances of the found folders/files."""
        if not self._server_qi or not self._job_qi or not self._root_qi:
            return []
        return self._item_qis

    def update(self, **kwargs):
        if kwargs:
            self._kwargs = kwargs
        self.__init__(**self._kwargs)

    def set_active_index(self, idx):
        self._active_item = self.items[idx]
        self._active_index = idx

    def set_active_item(self, item):
        """Sets the active item and the active index."""
        if item not in self.items:
            self._active_index = None
            self._active_item = None
            return

        self._active_index = self.items.index(item)
        self._active_item = self.items[self._active_index]

    def collect_assets(self):
        """Collects all maya assets."""
        if not self.root_info:
            return

        self._item_qis = []

        d = QtCore.QDir(
            self.root_info.filePath(),
            '',
            filter=QtCore.QDir.NoDotAndDotDot | QtCore.QDir.Dirs
        )
        for i in d.entryInfoList():
            valid = QtCore.QDir(
                i.filePath(),
                '*.mel',
                filter=QtCore.QDir.NoDotAndDotDot | QtCore.QDir.Files,
                sort=QtCore.QDir.Name
            ).entryList()
            if valid:
                self._item_qis.append(i)


class FileCollector(object):
    """Collects all scene files.

    Args:
        root_info (QFileInfo):     The directory to querry.

    """
    FILE_EXTENSION_MASK = ['*.mb', '*.ma']

    def __init__(self, root_info):
        """Init method.

        Args:
            root_info (QtCore.QFileInfo):       The path the get the files from.
        """
        self._root_qi = root_info

    @property
    def root_info(self):
        """The current QFileInfo object of the asset root."""
        return self._root_qi

    @root_info.setter
    def root_info(self, val):
        self._root_qi = val

    @property
    def files_generator(self):
        """Generator expression. Collects files from the root and it's subdirectories.

        Yields:
            QFileInfo instance

        """
        if not isinstance(self.root_info, QtCore.QFileInfo):
            return
            yield

        # Returning nothing when the root is invalid
        if not self.root_info.exists():
            return
            yield

        it = QtCore.QDirIterator(
            '{}/{}'.format(
                self.root_info.filePath(),
                local_settings.asset_scenes_folder
            ),
            self.FILE_EXTENSION_MASK,
            flags=QtCore.QDir.Dirs | QtCore.QDir.NoSymLinks |
            QtCore.QDir.NoDotAndDotDot | QtCore.QDirIterator.Subdirectories
        )
        while it.hasNext():
            yield QtCore.QFileInfo(it.next())

    def get_files(self, sort_order=0, reverse=False, filter=None):
        """A list QFileInfo instances referring to the found files.

        Arguments:
            sort_order (int):   0 = Alphabetical
                                1 = Modified
                                2 = Created
                                3 = Size
        Returns:
            List of QFileInfo instances.

        """

        convert = lambda text: int(text) if text.isdigit() else text
        alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key.filePath()) ]

        def last_modified_key(key):
            return key.lastModified().toMSecsSinceEpoch()

        def created_key(key):
            return key.created().toMSecsSinceEpoch()

        def size_key(key):
            return key.size()

        if filter:
            files = [f for f in self.files_generator if filter in f.path()]
        else:
            files = list(self.files_generator)

        if sort_order == 0:
            res = sorted(files, key=alphanum_key)
        elif sort_order == 1:
            res = sorted(files, key=last_modified_key)
            if res:
                res = list(reversed(res))
        elif sort_order == 2:
            res = sorted(files, key=created_key)
        elif sort_order == 3:
            res = sorted(files, key=size_key)

        if reverse:
            if res:
                return list(reversed(res))
        return res
