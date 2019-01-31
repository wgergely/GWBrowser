from PySide2 import QtCore, QtWidgets
import time
import re
from browser.collector import FileCollector
import browser.common as common

class Iterator(QtCore.QObject):
    # path = r'\\gordo\jobs\audible_8100\build\gergely_test\renders\forPS\glasses'

    def __init__(self, path, parent=None):
        super(Iterator, self).__init__(parent=parent)
        self.path = path
        self.count = 0

    def item_generator(self):
        it = QtCore.QDirIterator(
            self.path,
            ('*.*',),
            filters=QtCore.QDir.NoDotAndDotDot | QtCore.QDir.Files,
            flags=QtCore.QDirIterator.Subdirectories
        )
        self.count = 0
        while it.hasNext():
            self.count += 1
            yield QtCore.QFileInfo(it.next())

    def get_items(self, key=common.SortByName, reverse=False, path_filter='/'):
        """Sorts, filters and returns the items collected by the item_generator.

        Args:
            key (int):   The key used to sort the collected list.
            reverse (bool): If true, returns the list is reversed.
            path_filter (str): Matches a path segment and returns only the appropiate items.

        Returns:
            tuple:  A tuple of QFileInfo instances.

        """
        if True: # We're collapsing sequence
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
                        'frames': [],
                        'padding': len(match.group(2)),
                        'ext': match.group(3)
                    }
                d[match.group(1)]['frames'].append(int(match.group(2)))

            for k in d:
                path = '{}/{}[{}].{}'.format(
                    item.path(),
                    k,
                    common.get_ranges(d[k]['frames'], d[k]['padding']),
                    d[k]['ext']
                )
                items.append(QtCore.QFileInfo(path))
        else:
            items = [k for k in self.item_generator() if path_filter in k.filePath()]

        if not items:
            return []
        #
        if not reverse:
            return sorted(items, key=common.sort_keys[key])
        return list(reversed(sorted(items, key=common.sort_keys[key])))



if __name__ == '__main__':
    app = QtWidgets.QApplication([])


    path = r'\\gordo\jobs\audible_8100\films\vignettes\shots\AU_podcast\renders'
    start = time.time()
    it = Iterator(path)
    items = it.get_items()
    end = time.time()
    print '# Found {} items in {} seconds'.format(it.count, end - start)

    #
    path = r'\\gordo\jobs\audible_8100\films\vignettes\shots\AU_podcast'
    start = time.time()
    it = FileCollector(path, common.RendersFolder)
    it.get_items(reverse=True)
    end = time.time()
    print '# Found {} items in {} milliseconds'.format(it.count, end - start)
