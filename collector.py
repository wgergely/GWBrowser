# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101


"""This modules defines the classes used to gather the items needed to populate the list
widgets. The collector classes can filter and sort the resulting list.

Methods:
    get_items(key=common.SortByName, reverse=False, filter=None)

"""

import functools
from PySide2 import QtCore

import mayabrowser.common as common
from mayabrowser.configparsers import local_settings


class BaseCollector(object):
    """Base class for collectors."""

    ERR1 = 'The specified path ({}) could not be found.'
    ERR2 = 'The specified path ({}) could not be read.\nCheck persmissions.'

    def __init__(self, path=None):
        self._path = path
        self._count = 0

    @property
    def count(self):
        """The number of assets found."""
        return self._count

    def item_generator(self):
        """Has to be overriden in the subclass."""
        raise NotImplementedError('generator is abstract.')


    def get_items(self, key=common.SortByName, reverse=False, path_filter='/'):
        """Sorts, filters and returns the items collected by the item_generator.

        Args:
            key (int):   The key used to sort the collected list.
            reversed (bool): If true, returns the list is reversed.
            path_filter (str): Matches a path segment and returns only the appropiate items.

        Returns:
            tuple:  A tuple of QFileInfo instances.

        """
        items = [k for k in self.item_generator() if path_filter in k.filePath()]

        if not items:
            return []

        if not reverse:
            return sorted(items, key=common.sort_keys[key])
        return list(reversed(sorted(items, key=common.sort_keys[key])))


class BookmarksCollector(BaseCollector):
    """`Collects` bookmarks. Bookmarks really are only virtual objects,
    but the collector can take care of the filtering and sorting like in the
    Asset- and FileCollect classes."""

    def item_generator(self):
        """Generator expression. Collects all the bookmarks found in the local configuration file."""
        bookmarks = local_settings.value('bookmarks')

        if not bookmarks:
            return

        def size(file_info):
            """Custom size method for bookmarks."""
            return common.count_assets(file_info.filePath())

        for k in bookmarks:
            path = u'{}/{}/{}'.format(
                bookmarks[k]['server'],
                bookmarks[k]['job'],
                bookmarks[k]['root']
            )
            file_info = QtCore.QFileInfo(path)

            # This is a bit hackish
            file_info.server = bookmarks[k]['server']
            file_info.job = bookmarks[k]['job']
            file_info.root = bookmarks[k]['root']

            file_info.size = functools.partial(size, file_info)
            self._count += 1

            yield file_info


class AssetCollector(BaseCollector):
    """Collects ``assets`` from a specified path.

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

    def item_generator(self):
        """Generator expression. Collects files from the ``path`` and the subdirectories
        within.

        Yields:
            QFileInfo:  The QFileInfo object representing the found folder.

        """
        self._count = 0  # Resetting the count
        it = QtCore.QDirIterator(
            self._path,
            flags=QtCore.QDirIterator.NoIteratorFlags,
            filters=QtCore.QDir.NoDotAndDotDot |
            QtCore.QDir.Dirs |
            QtCore.QDir.NoSymLinks |
            QtCore.QDir.Readable
        )
        while it.hasNext():
            path = it.next()
            file_info = QtCore.QFileInfo(path)

            if file_info.fileName() == '.' or file_info.fileName() == '..':
                continue
            if not file_info.isDir():
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
            yield file_info


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

    def item_generator(self):
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
            file_info = QtCore.QFileInfo(it.next())
            if file_info.fileName() == '.' or file_info.fileName() == '..':
                continue
            if file_info.isDir():
                continue
            yield file_info


if __name__ == '__main__':
    # collector = FileCollector(r'Z:\tkwwbk_8077\build\knight', 'scenes', name_filter=('*',))
    # for f in collector.get(reverse=True, filter='temp.ma'):
    #     print f.fileName()
    collector = BookmarksCollector()
    for item in collector.get_items(reverse=True, path_filter='shots'):
        print item
