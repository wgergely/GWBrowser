# -*- coding: utf-8 -*-
"""PySide2 dependent base-class for querring folders and files.

The values used to initialize the ``AssetCollector`` and the ``FileCollector.get()``
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
        scenes = collector.get(
            sort_order=0,
            reverse=False,
            filter='/subfolder/'
        )

"""
# pylint: disable=E1101, C0103, R0913, I1101

import re
from PySide2 import QtCore
import mayabrowser.common as common


class AssetCollector(object):
    """Convenience class to collect ``assets`` from a specified path.

    Arguments:
        path (str):             Path to an ``asset`` folder as a string.

    """

    def __init__(self, path):
        self._path = path
        self._count = 0

        err_one = 'The specified path ({}) could not be found.'
        err_two = 'The specified path ({}) could not be read.\nCheck persmissions.'

        file_info = QtCore.QFileInfo(self._path)
        if not file_info.exists():
            raise IOError(err_one.format(file_info.filePath()))
        elif not file_info.isReadable():
            raise IOError(err_two.format(file_info.filePath()))

    @property
    def count(self):
        """The number of assets found."""
        return self._count

    def _generator(self):
        """Generator expression. Collects files from the ``path`` and the subdirectories
        within.

        Yields: A QFileInfo instance.
        """
        self._count = 0
        it = QtCore.QDirIterator(
            self._path,
            flags=QtCore.QDir.NoSymLinks |
            QtCore.QDir.NoDotAndDotDot |
            QtCore.QDir.Dirs
        )
        while it.hasNext():
            path = it.next()
            item = QtCore.QFileInfo(path)

            if item.fileName() == '.' or item.fileName() == '..':
                continue
            if not item.isDir():
                continue

            # Validate assets and skip folders without the identifier
            identifier = QtCore.QDir(path).entryList(
                (common.ASSET_IDENTIFIER, ),
                filters=QtCore.QDir.Files |
                QtCore.QDir.NoDotAndDotDot |
                QtCore.QDir.NoSymLinks
            )

            if not identifier:
                continue

            self._count += 1
            yield item

    def get(self, sort_order=0, reverse=False, filter=None):
        """Main method to return the collected files as QFileInfo instances.

        Arguments:
            sort_order (int):   0 = Alphabetical
                                1 = Modified
                                2 = Created
                                3 = Size
            reversed (bool):     Reverses the list order.
            filter (str):       Returns only items containing this string.

        Returns:                List of QFileInfo instances.
        """

        def _convert(text): return int(text) if text.isdigit() else text

        def _alphanum_key(key): return [_convert(c)
                                        for c in re.split('([0-9]+)', key.filePath())]

        def _last_modified_key(key):
            return key.lastModified().toMSecsSinceEpoch()

        def _created_key(key):
            return key.created().toMSecsSinceEpoch()

        def _size_key(key):
            return key.size()

        if filter:
            files = [k for k in self._generator() if filter in k.filePath()]
        else:
            files = list(self._generator())

        if sort_order == 0:
            res = sorted(files, key=_alphanum_key)
        elif sort_order == 1:
            res = sorted(files, key=_last_modified_key)
            if res:
                res = list(reversed(res))
        elif sort_order == 2:
            res = sorted(files, key=_created_key)
        elif sort_order == 3:
            res = sorted(files, key=_size_key)

        if reverse:
            if res:
                return list(reversed(res))
        return res


class FileCollector(object):
    """This is a convenience class to collect files from a given path.

    Arguments:
        path (str):             Path to an ``asset`` folder as a string.
        asset_folder (str):     Subfolder inside the ``asset`` folder. Eg. `'scenes'`
                                See ``common.ASSET_FOLDERS`` for accepted values.
        name_filter ([str,]):   Returns only items containing any of the given strings.

    Methods:
        set_name_filter(str):   Sets the file mask.
                                Default value is ``('*.*')``, returning all found files.
                                To return only Maya scene files you can use ``('*.mb', '*.ma')``
        get (sort_order, reversed, filter): Returns all found files as QFileInfo instances.


    """

    DEFAULT_NAME_FILTER = [
        '*.psd',
        '*.ma',
        '*.mb',
        '*.aep',
    ]

    def __init__(self, path, name_filter=DEFAULT_NAME_FILTER):
        self._path = path
        self._name_filter = name_filter

        file_info = QtCore.QFileInfo(path)

        err_one = 'The specified path ({}) could not be found.'
        err_two = 'The specified path ({}) could not be read.\nCheck persmissions.'

        if not file_info.exists():
            raise IOError(err_one.format(file_info.filePath()))
        elif not file_info.isReadable():
            raise IOError(err_two.format(file_info.filePath()))

    def set_name_filter(self, val):
        """Sets the name filters to the given value."""
        self._name_filter = val

    def _generator(self):
        """Generator expression. Collects files from the ``path`` and the subdirectories
        within.

        Yields: A QFileInfo instance.
        """
        it = QtCore.QDirIterator(
            self._path,
            self._name_filter,
            flags=QtCore.QDir.NoSymLinks |
            QtCore.QDir.NoDotAndDotDot |
            QtCore.QDirIterator.Subdirectories
        )

        while it.hasNext():
            item = QtCore.QFileInfo(it.next())
            if item.fileName() == '.' or item.fileName() == '..':
                continue
            if item.isDir():
                continue
            yield item

    def get(self, sort_order=0, reverse=False, filter=None):
        """Main method to return the collected files as QFileInfo instances.

        Arguments:
            sort_order (int):   0 = Alphabetical
                                1 = Modified
                                2 = Created
                                3 = Size
            reversed (bool):    Reverses the list order.
            filter (str):       Returns only items containing this string.

        Returns:                List of QFileInfo instances.
        """

        def _convert(text): return int(text) if text.isdigit() else text

        def _alphanum_key(key): return [_convert(c)
                                        for c in re.split('([0-9]+)', key.filePath())]

        def _last_modified_key(key):
            return key.lastModified().toMSecsSinceEpoch()

        def _created_key(key):
            return key.created().toMSecsSinceEpoch()

        def _size_key(key):
            return key.size()

        if filter:
            files = [k for k in self._generator() if filter in k.filePath()]
        else:
            files = list(self._generator())

        if sort_order == 0:
            res = sorted(files, key=_alphanum_key)
        elif sort_order == 1:
            res = sorted(files, key=_last_modified_key)
            if res:
                res = list(reversed(res))
        elif sort_order == 2:
            res = sorted(files, key=_created_key)
        elif sort_order == 3:
            res = sorted(files, key=_size_key)

        if reverse:
            if res:
                return list(reversed(res))
        return res


if __name__ == '__main__':
    # collector = FileCollector(r'Z:\tkwwbk_8077\build\knight', 'scenes', name_filter=('*',))
    # for f in collector.get(reverse=True, filter='temp.ma'):
    #     print f.fileName()
    collector = AssetCollector(r'Z:\tkwwbk_8077\build')
    for f in collector.get(reverse=True):
        print f
