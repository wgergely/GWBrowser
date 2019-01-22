# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101


"""This modules defines the classes used to gather the item needed to populate
the list widgets. The collector classes can filter and sort the resulting list.

Methods:
    get_items(key=common.SortByName, reverse=False, filter=None)

"""

import functools
import re
from PySide2 import QtCore

import mayabrowser.common as common
from mayabrowser.settings import local_settings


class BaseCollector(QtCore.QObject):
    """Base class for collectors."""

    def __init__(self, parent=None):
        super(BaseCollector, self).__init__(parent=parent)
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
            reverse (bool): If true, returns the list is reversed.
            path_filter (str): Matches a path segment and returns only the appropiate items.

        Returns:
            tuple:  A tuple of QFileInfo instances.

        """
        if not self.parent().is_sequence_collapsed():  # We're collapsing sequence
            items = []
            r = re.compile(r'^(.*?)([0-9]+)\.(.{2,5})$')

            d = {}
            for item in self.item_generator():
                match = r.search(item.fileName())
                if not match:
                    items.append(item)
                    continue
                if match.group(1) not in d:
                    d[match.group(1)] = {
                        'path': item.path(),
                        'frames': [],
                        'size': item.size(),
                        'padding': len(match.group(2)),
                        'modified': item.lastModified(),
                        'ext': match.group(3)
                    }
                d[match.group(1)]['frames'].append(int(match.group(2)))
                # d[match.group(1)]['size'] += item.size()
                # d[match.group(1)]['modified'] = (
                #     d[match.group(1)]['modified'] if item.lastModified() <
                #     d[match.group(1)]['modified'] else item.lastModified())

            for k in d:
                path = '{}/{}[{}].{}'.format(
                    d[k]['path'],
                    k,
                    common.get_ranges(d[k]['frames'], d[k]['padding']),
                    d[k]['ext']
                )
                def _size(item):
                    return item['size']
                def _modified(item):
                    return item['modified']
                file_info = QtCore.QFileInfo(path)
                file_info.size = functools.partial(_size, d[k])
                file_info.lastModified = functools.partial(_modified, d[k])
                items.append(file_info)
        else:
            items = [k for k in self.item_generator(
            ) if path_filter in k.filePath()]
        # items = [k for k in self.item_generator(
        # ) if path_filter in k.filePath()]

        if not items:
            return []
        #
        if not reverse:
            return sorted(items, key=common.sort_keys[key])
        return list(reversed(sorted(items, key=common.sort_keys[key])))


class BookmarksCollector(BaseCollector):
    """Collects the saved ``Bookmarks``. Bookmarks are virtual,
    but the collector can take care of the filtering and sorting them like
    with assets and files."""

    def item_generator(self):
        """Generator expression. Collects all the bookmarks found in the local configuration file."""
        bookmarks = local_settings.value('bookmarks')

        if not bookmarks:
            return

        class Bookmark(object):
            def __init__(self):
                self.server = None
                self.job = None
                self.root = None
                self.size = None
                self.fileName = None
                self.filePath = None
                self.exists = None

        for k in bookmarks:
            bookmark = Bookmark()
            path = u'{}/{}/{}'.format(
                bookmarks[k]['server'],
                bookmarks[k]['job'],
                bookmarks[k]['root']
            )
            bookmark.server = bookmarks[k]['server']
            bookmark.job = bookmarks[k]['job']
            bookmark.root = bookmarks[k]['root']
            bookmark.size = lambda: common.count_assets(path)
            bookmark.fileName = lambda: QtCore.QFileInfo(path).fileName()
            bookmark.filePath = lambda: QtCore.QFileInfo(path).filePath()
            bookmark.exists = lambda: QtCore.QFileInfo(path).exists()
            self._count += 1

            yield bookmark


class AssetCollector(BaseCollector):
    """Collects ``assets`` from a specified path.

    Arguments:
        path (str): A ``bookmark`` path.

    """

    def __init__(self, path, parent=None):
        super(AssetCollector, self).__init__(parent=parent)
        self.path = path

    def item_generator(self):
        """Generator expression. Collects files from the ``path`` and the subdirectories
        within.

        Yields:
            QFileInfo:  The QFileInfo object representing the found folder.

        """
        self._count = 0  # Resetting the count
        it = QtCore.QDirIterator(
            self.path,
            flags=QtCore.QDirIterator.NoIteratorFlags,
            filters=QtCore.QDir.NoDotAndDotDot |
            QtCore.QDir.Dirs |
            QtCore.QDir.NoSymLinks |
            QtCore.QDir.Readable
        )
        while it.hasNext():
            path = it.next()
            file_info = QtCore.QFileInfo(path)

            # Validate assets by skipping folders without the identifier file
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


class FileCollector(BaseCollector):
    """Collects the files needed to populate the Files Widget."""

    def __init__(self, path, root, parent=None):
        super(FileCollector, self).__init__(parent=parent)
        self.path = path
        self.location = root
        self.modes = self._get_modes()

    def _get_modes(self):
        file_info = QtCore.QFileInfo('{}/{}'.format(self.path, self.location))
        if not file_info.exists():
            return []

        dir_ = QtCore.QDir(file_info.filePath())
        return dir_.entryList(
            filters=QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot,
        )

    def item_generator(self):
        """Generator expression. Collects files from the ``path/root`` and the subdirectories
        within.

        Yields: A QFileInfo instance.

        """
        it = QtCore.QDirIterator(
            '{}/{}'.format(self.path, self.location),
            common.NameFilters[self.location],
            filters=QtCore.QDir.NoDotAndDotDot | QtCore.QDir.Files,
            flags=QtCore.QDirIterator.Subdirectories
        )
        self._count = 0  # Resetting the count
        while it.hasNext():
            self._count += 1
            yield QtCore.QFileInfo(it.next())


if __name__ == '__main__':
    # collector = FileCollector(r'Z:\tkwwbk_8077\build\knight', 'scenes', name_filter=('*',))
    # for f in collector.get(reverse=True, filter='temp.ma'):
    #     print f.fileName()
    collector = FileCollector(
        r'\\gordo\jobs\tkwwbk_8077\build2\asset_one',
        common.ScenesFolder
    )
    for item in collector.get_items(reverse=False, path_filter='/'):
        print item
