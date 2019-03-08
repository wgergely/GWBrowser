# -*- coding: utf-8 -*-
"""Module defines the QListWidget items used to browse the assets and the files
found by the collector classes.

"""
# pylint: disable=E1101, C0103, R0913, I1101

import math
import sys
import functools
from PySide2 import QtWidgets, QtCore, QtGui

from browser.baselistwidget import BaseContextMenu
from browser.baselistwidget import BaseInlineIconWidget
from browser.baselistwidget import BaseModel

import browser.common as common
from browser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite
from browser.settings import AssetSettings
from browser.settings import local_settings, Active
from browser.delegate import FilesWidgetDelegate
import browser.editors as editors
from browser.imagecache import ImageCache


mutex = QtCore.QMutex()

class FileInfoThread(QtCore.QThread):
    def __init__(self, idx, parent=None):
        super(FileInfoThread, self).__init__(parent=parent)
        self.idx = idx

class FileInfoWorker(QtCore.QObject):
    """Generic QRunnable, taking an index as it's first argument."""
    finished = QtCore.Signal()
    error = QtCore.Signal(basestring)

    def __init__(self, model, parent=None):
        super(FileInfoWorker, self).__init__(parent=parent)
        self.model = model

    def process_data(self):
        indexes = []
        nth = 100
        for n in xrange(self.model.rowCount()):
            if n % nth == 0:
            index = self.model.index(n, 0)
            settings = AssetSettings(index)
            self.model.model_data[index.row()][common.FileDetailsRole] = 'Updated!'
            self.

        self.finished.emit()



class FilesWidgetContextMenu(BaseContextMenu):
    """Context menu associated with FilesWidget."""

    def __init__(self, index, parent=None):
        super(FilesWidgetContextMenu, self).__init__(index, parent=parent)
        # Adding persistent actions
        self.add_location_toggles_menu()

        self.add_separator()

        if index.isValid():
            self.add_mode_toggles_menu()
            self.add_thumbnail_menu()

        self.add_separator()

        if index.isValid():
            self.add_reveal_folder_menu()
            self.add_copy_menu()

        self.add_separator()

        self.add_sort_menu()
        self.add_collapse_sequence_menu()
        self.add_display_toggles_menu()

        self.add_separator()

        self.add_refresh_menu()


class FilesModel(BaseModel):
    """Model with the file-data associated with asset `locations` and
    groupping modes.

    The model stores information in the private `_model_data` dictionary. The items
    returned by the model are read from the `model_data`.

    Example:
        self.model_data = self._model_data[location][grouppingMode]

    """

    def __init__(self, asset, parent=None):
        self.asset = asset
        self.mode = None
        self._isgrouped = None
        self.threads = {}

        super(FilesModel, self).__init__(parent=parent)

        self.grouppingChanged.connect(self.switch_model_data)
        self.activeLocationChanged.connect(self.switch_model_data)
        self.modelDataResetRequested.connect(self.__resetdata__)

        self.mutex = QtCore.QMutex()
        self.switch_model_data()

    def __initdata__(self):
        """The method is responsible for getting the bare-bones file and sequence
        definitions. Later all the additional information is populated by secondary
        thread-workers.

        """
        rowsize = QtCore.QSize(common.WIDTH, common.ROW_HEIGHT)
        flags = (
            QtCore.Qt.ItemNeverHasChildren |
            QtCore.Qt.ItemIsSelectable |
            # QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsEditable |
            QtCore.Qt.ItemIsDragEnabled
        )
        favourites = local_settings.value(u'favourites')
        favourites = favourites if favourites else []

        # Invalid asset, we'll do nothing.
        if not all(self.asset):
            return
        server, job, root, asset = self.asset
        location = self.get_location()

        location_path = ('{}/{}/{}/{}/{}'.format(
            server, job, root, asset, location
        ))

        # Data-containers
        self.beginResetModel()
        self._model_data[location] = {True: {}, False: {}}
        seqs = {}

        # Iterator
        itdir = QtCore.QDir(location_path)
        itdir.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        itdir.setSorting(QtCore.QDir.Unsorted)
        it = QtCore.QDirIterator(
            itdir, flags=QtCore.QDirIterator.Subdirectories)

        while it.hasNext():
            filepath = it.next()

            # File-filter:
            if location in common.NameFilters:
                if not filepath.split('.')[-1] in common.NameFilters[location]:
                    continue

            fileroot = it.path().replace(location_path, '')

            seq = common.get_sequence(filepath)
            filename = it.fileName()

            if filepath in favourites:
                flags = flags | MarkedAsFavourite

            idx = len(self._model_data[location][False])
            self._model_data[location][False][idx] = {
                QtCore.Qt.DisplayRole: filename,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.ToolTipRole: filepath,
                QtCore.Qt.SizeHintRole: rowsize,
                common.FlagsRole: flags,
                common.ParentRole: (server, job, root, asset, location, fileroot),
                common.DescriptionRole: 'Loading...',
                common.TodoCountRole: 0,
                common.FileDetailsRole: 'Loading...',
            }

            # If the file in question is a sequence, we will also save a reference
            # to it in `self._model_data[location][True]` dictionary.
            if seq:
                seqpath = u'{}[0]{}.{}'.format(
                    seq.group(1), seq.group(3), seq.group(4))

                if seqpath not in seqs: #... and create it if it doesn't exist
                    seqname = seqpath.split('/')[-1]
                    if seqname in favourites:
                        flags = flags | MarkedAsFavourite
                    seqs[seqpath] = {
                        QtCore.Qt.DisplayRole: seqname,
                        QtCore.Qt.EditRole: seqname,
                        QtCore.Qt.StatusTipRole: seqpath,
                        QtCore.Qt.ToolTipRole: seqpath,
                        QtCore.Qt.SizeHintRole: rowsize,
                        common.FlagsRole: flags,
                        common.ParentRole: (server, job, root, asset, location, fileroot),
                        common.DescriptionRole: 'Loading...',
                        common.TodoCountRole: 0,
                        common.FileDetailsRole: 'Loading...',
                        u'frames': [] # extra attrib for storing the found frames.
                    }
                seqs[seqpath]['frames'].append(seq.group(2))
            else:
                seqs[filepath] = self._model_data[location][False][idx]
        # Casting the sequence data onto the model
        for v in seqs.itervalues():
            idx = len(self._model_data[location][True])
            self._model_data[location][True][idx] = v

        self.endResetModel()


    def switch_model_data(self):
        """Method responsible for setting

        """
        def chunks(l, n):
            """Yields successive n-sized chunks of the given list."""
            for i in xrange(0, len(l), n):
                yield l[i:i + n]
        # When the dataset is empty, calling __initdata__
        location = self.get_location()
        if location not in self._model_data:
            self._model_data[location] = {True: {}, False: {}, }

        if not self._model_data[location][self.is_grouped()]:
            self.__initdata__()

        self.beginResetModel()
        self.model_data = self._model_data[self.get_location()][self.is_grouped()]
        self.endResetModel()

        # Getting additional information
        app = QtCore.QCoreApplication.instance()
        app.processEvents()

        idtc = QtCore.QThread.idealThreadCount()
        indexes = []
        for n in xrange(self.rowCount()):
            index = self.index(n, 0)
            indexes.append(index)

        chunks = list(chunks(indexes, int(math.ceil(float(len(indexes)) / idtc))))

        print app.thread()
        thread = self.get_thread()
        worker = FileInfoWorker(self)
        worker.moveToThread(thread)

        app.aboutToQuit.connect(thread.quit)
        app.aboutToQuit.connect(thread.deleteLater)

        thread.started.connect(worker.process_data)

        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(functools.partial(self.delete_thread, thread))

        thread.start()

    def get_thread(self):
        idx = len(self.threads)
        self.threads[idx] = FileInfoThread(idx)
        return self.threads[idx]

    def delete_thread(self, thread):
        del self.threads[thread.idx]


    def set_asset(self, asset):
        """Sets a new asset for the model."""
        if self.asset == asset:
            return
        self.asset = asset

    def is_grouped(self):
        """Gathers sequences into a single file."""
        if self._isgrouped is None:
            cls = self.__class__.__name__
            key = u'widget/{}/{}/iscollapsed'.format(cls, self.get_location())
            val = local_settings.value(key)
            if val is None:
                self._isgrouped = False
            else:
                self._isgrouped = val
        return self._isgrouped

    def set_collapsed(self, val):
        """Sets the groupping mode."""
        cls = self.__class__.__name__
        key = u'widget/{}/{}/iscollapsed'.format(cls, self.get_location())
        cval = local_settings.value(key)

        if cval == val:
            return

        self.modelDataAboutToChange.emit()
        self._isgrouped = val
        local_settings.setValue(key, val)
        self.grouppingChanged.emit()

    def get_location(self):
        """Get's the current ``location``."""
        val = local_settings.value(u'activepath/location')
        if not val:
            local_settings.setValue(
                u'activepath/location', common.ScenesFolder)

        return val if val else common.ScenesFolder

    def set_location(self, val):
        """Sets the location and emits the ``activeLocationChanged`` signal."""
        key = u'activepath/location'
        cval = local_settings.value(key)

        if cval == val:
            return

        local_settings.setValue(key, val)
        self.activeLocationChanged.emit(val)

        # Updating the groupping of the files
        cls = self.__class__.__name__
        key = u'widget/{}/{}/iscollapsed'.format(cls, val)
        groupped = True if local_settings.value(key) else False

        if self.is_grouped() == groupped:
            return

        self.modelDataAboutToChange.emit()
        self._isgrouped = groupped
        self.grouppingChanged.emit()

    def canDropMimeData(self, data, action, row, column):
        return False

    def supportedDropActions(self):
        return QtCore.Qt.IgnoreAction

    def supportedDragActions(self):
        return QtCore.Qt.CopyAction

    def mimeData(self, indexes):
        index = next((f for f in indexes), None)
        mime = QtCore.QMimeData()
        location = self.get_location()
        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))

        if location == common.RendersFolder:  # first file
            filepath = common.get_sequence_startpath(file_info.filePath())
        elif location == common.ScenesFolder:  # last file
            filepath = common.get_sequence_endpath(file_info.filePath())
        elif location == common.TexturesFolder:
            filepath = common.get_sequence_endpath(file_info.filePath())
        elif location == common.ExportsFolder:
            filepath = common.get_sequence_endpath(file_info.filePath())
        else:
            filepath = common.get_sequence_endpath(file_info.filePath())

        url = QtCore.QUrl.fromLocalFile(filepath)
        mime.setUrls((url,))
        mime.setData(
            u'application/x-qt-windows-mime;value="FileName"',
            QtCore.QDir.toNativeSeparators(filepath))

        mime.setData(
            u'application/x-qt-windows-mime;value="FileNameW"',
            QtCore.QDir.toNativeSeparators(filepath))
        return mime



class FilesWidget(BaseInlineIconWidget):
    """Files widget is responsible for listing scene and project files of an asset.

    It relies on a custom collector class to gether the files requested.
    The scene files live in their respective root folder, usually ``scenes``.
    The first subfolder inside this folder will refer to the ``mode`` of the
    asset file.

    """

    itemDoubleClicked = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, asset, parent=None):
        super(FilesWidget, self).__init__(parent=parent)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(False)
        self.setAcceptDrops(False)

        self.setWindowTitle(u'Files')
        self.setItemDelegate(FilesWidgetDelegate(parent=self))
        self.context_menu_cls = FilesWidgetContextMenu
        self.set_model(FilesModel(asset))

    def eventFilter(self, widget, event):
        super(FilesWidget, self).eventFilter(widget, event)
        if widget is not self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            # Let's paint the icon of the current mode
            painter = QtGui.QPainter()
            painter.begin(self)
            pixmap = ImageCache.get_rsc_pixmap(
                'files', QtGui.QColor(0, 0, 0, 10), 200)
            rect = pixmap.rect()
            rect.moveCenter(self.rect().center())
            painter.drawPixmap(rect, pixmap, pixmap.rect())
            painter.end()
            return True
        return False

    def inline_icons_count(self):
        return 3

    def action_on_enter_key(self):
        index = self.selectionModel().currentIndex()
        self.itemDoubleClicked.emit(index)

    def activate_current_index(self):
        """Sets the current item item as ``active`` and
        emits the ``activeLocationChanged`` and ``activeFileChanged`` signals.

        """
        if not super(FilesWidget, self).activate_current_index():
            return

        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        fileroot = index.data(common.ParentRole)[5]
        activefilepath = u'{}/{}'.format(fileroot, file_info.fileName())
        local_settings.setValue(u'activepath/file', activefilepath)

        activefilepath = list(index.data(common.ParentRole)
                              ) + [file_info.fileName(), ]
        activefilepath = u'/'.join(activefilepath)
        activefilepath = common.get_sequence_endpath(activefilepath)
        self.model().sourceModel().activeFileChanged.emit(activefilepath)

    def mouseDoubleClickEvent(self, event):
        """Custom double-click event.

        A double click can `activate` an item, or it can trigger an edit event.
        As each item is associated with multiple editors we have to inspect
        the double-click location before deciding what action to take.

        """
        index = self.indexAt(event.pos())
        rect = self.visualRect(index)

        thumbnail_rect = QtCore.QRect(rect)
        thumbnail_rect.setWidth(rect.height())
        thumbnail_rect.moveLeft(common.INDICATOR_WIDTH)

        font = QtGui.QFont(common.PrimaryFont)
        metrics = QtGui.QFontMetrics(font)

        name_rect = QtCore.QRect(rect)
        name_rect.setLeft(
            common.INDICATOR_WIDTH +
            name_rect.height() +
            common.MARGIN
        )
        name_rect.setRight(name_rect.right() - common.MARGIN)
        #
        description_rect = QtCore.QRect(name_rect)
        #
        name_rect.moveTop(name_rect.top() + (name_rect.height() / 2.0))
        name_rect.setHeight(metrics.height())
        name_rect.moveTop(name_rect.top() - (name_rect.height() / 2.0))
        #
        description_rect.moveTop(
            description_rect.top() + (description_rect.height() / 2.0))
        description_rect.setHeight(metrics.height())
        description_rect.moveTop(description_rect.top(
        ) - (description_rect.height() / 2.0) + metrics.lineSpacing())

        if description_rect.contains(event.pos()):
            widget = editors.DescriptionEditorWidget(index, parent=self)
            widget.show()
            return
        elif thumbnail_rect.contains(event.pos()):
            ImageCache.instance().pick(index)
            return

        # self.activate_current_index()
        self.itemDoubleClicked.emit(index)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    active_paths = Active.get_active_paths()
    asset = (active_paths[u'server'],
             active_paths[u'job'],
             active_paths[u'root'],
             active_paths[u'asset'],
             )
    widget = FilesWidget(asset)
    widget.show()
    app.exec_()
