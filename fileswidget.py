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
from browser.settings import local_settings
from browser.delegate import FilesWidgetDelegate
import browser.editors as editors
from browser.imagecache import ImageCache


mutex = QtCore.QMutex()
"""The mutex reposinble for guarding the model data."""


class FileInfoThread(QtCore.QThread):
    """The thread responsible for updating the file-list with the missing
    information. I can't get threads to work using the documented way -
    depending on conditions I don't understand, the thread sometimes executes
    the worker, sometimes the `started` signal doesn't fire when the Worker is
    created outside the thread.

    The thread.start() is called when the ``FileModel`` is initialized.

    """
    __worker = None

    dataRequested = QtCore.Signal(tuple)

    def __init__(self, model, parent=None):
        super(FileInfoThread, self).__init__(parent=parent)
        self.thread_id = None
        self.worker = None
        self.model = model

        app = QtWidgets.QApplication.instance()
        app.aboutToQuit.connect(self.quit)
        app.aboutToQuit.connect(self.deleteLater)

    def run(self):
        self.worker = FileInfoWorker(self.model)
        self.dataRequested.connect(
            self.worker.processIndexes, type=QtCore.Qt.QueuedConnection)
        ImageCache.instance().thumbnailChanged.connect(
            lambda index: self.worker.processIndexes((index,)), type=QtCore.Qt.QueuedConnection)
        sys.stderr.write(
            'FileInfoThread.run() -> {}\n'.format(QtCore.QThread.currentThread()))
        self.started.emit()
        self.exec_()


class FileInfoWorker(QtCore.QObject):
    """Thread-worker class responsible for updating the given indexes."""
    mutex = QtCore.QMutex()
    queue = []
    queue = []

    indexUpdated = QtCore.Signal(QtCore.QModelIndex)
    finished = QtCore.Signal()
    error = QtCore.Signal(basestring)

    def __init__(self, model, parent=None):
        super(FileInfoWorker, self).__init__(parent=parent)
        self.model = model

    @classmethod
    def queue_count(cls):
        return len(cls.queue)

    @classmethod
    def add_to_queue(cls, items):
        cls.mutex.lock()
        cls.queue += items
        cls.mutex.unlock()

    @classmethod
    def remove_from_queue(cls, idx):
        cls.mutex.lock()
        del cls.queue[cls.queue.index(idx)]
        cls.mutex.unlock()

    @QtCore.Slot(tuple)
    def processIndexes(self, datachunk):
        """Gets and sets the missing information for each index in a background
        thread.

        """
        try:
            self._process_data(datachunk)
        except RuntimeError as err:
            errstr = '\nRuntimeError in {}\n{}\n'.format(
                QtCore.QThread.currentThread(), err)
            sys.stderr.write(errstr)
            self.error.emit(errstr)
        except ValueError as err:
            errstr = '\nValueError in {}\n{}\n'.format(
                QtCore.QThread.currentThread(), err)
            sys.stderr.write(errstr)
            self.error.emit(errstr)
        except Exception as err:
            errstr = '\nError in {}\n{}\n'.format(
                QtCore.QThread.currentThread(), err)
            sys.stderr.write(errstr)
            self.error.emit(errstr)
        finally:
            common.ProgressMessage.instance().clear_message()
            self.finished.emit()

    def _process_data(self, datachunk):
        """The actual processing happens here."""
        nth = 789
        n = 0
        for idx in datachunk:
            n += 1
            if n % nth == 0:
                common.ProgressMessage.instance().set_message(
                    'Processing items ({} left)...'.format(FileInfoWorker.queue_count()))

            index = self.model.index(idx, 0)
            if not index.isValid():
                continue

            settings = AssetSettings(index)

            # Item description
            description = settings.value(u'config/description')
            if description:
                self.model.model_data[idx][common.DescriptionRole] = description

            # Sequence path and name
            if self.model.model_data[idx][common.TypeRole] == common.SequenceItem:
                frames = sorted(self.model.model_data[idx][common.FramesRole])
                intframes = [int(f) for f in frames]
                rangestring = common.get_ranges(intframes, len(frames[0]))

                p = self.model.model_data[idx][common.SequenceRole].expand(
                    r'\1{}\3.\4')
                startpath = p.format(
                    unicode(min(intframes)).zfill(len(frames[0])))
                endpath = p.format(
                    unicode(max(intframes)).zfill(len(frames[0])))
                seqpath = p.format('[{}]'.format(rangestring))
                seqname = seqpath.split(u'/')[-1]

                self.model.model_data[idx][common.StartpathRole] = startpath
                self.model.model_data[idx][common.EndpathRole] = endpath
                self.model.model_data[idx][QtCore.Qt.StatusTipRole] = seqpath
                self.model.model_data[idx][QtCore.Qt.ToolTipRole] = seqpath
                self.model.model_data[idx][QtCore.Qt.DisplayRole] = seqname
                self.model.model_data[idx][QtCore.Qt.EditRole] = seqname

                # File description string
                size = 0
                last_modified = QtCore.QDateTime(QtCore.QDate(1985, 8, 30))
                for frame in frames:
                    framepath = p.format(frame)
                    file_info = QtCore.QFileInfo(framepath)
                    size += file_info.size()
                    last_modified = file_info.lastModified() if file_info.lastModified(
                    ).toTime_t() > last_modified.toTime_t() else last_modified

                info_string = u'{count} files  |  {day}/{month}/{year} {hour}:{minute}  {size}'.format(
                    count=len(frames),
                    day=last_modified.toString(u'dd'),
                    month=last_modified.toString(u'MM'),
                    year=last_modified.toString(u'yyyy'),
                    hour=last_modified.toString(u'hh'),
                    minute=last_modified.toString(u'mm'),
                    size=common.byte_to_string(size)
                )
            else:
                file_info = QtCore.QFileInfo(
                    self.model.model_data[idx][QtCore.Qt.StatusTipRole])
                size = file_info.size()
                last_modified = file_info.lastModified()
                info_string = u'{day}/{month}/{year} {hour}:{minute}  {size}'.format(
                    day=last_modified.toString(u'dd'),
                    month=last_modified.toString(u'MM'),
                    year=last_modified.toString(u'yyyy'),
                    hour=last_modified.toString(u'hh'),
                    minute=last_modified.toString(u'mm'),
                    size=common.byte_to_string(size)
                )
            self.model.model_data[idx][common.FileDetailsRole] = info_string

            # Sort values
            # self.model.model_data[idx][common.SortByName] = fileroot
            self.model.model_data[idx][common.SortByLastModified] = last_modified.toMSecsSinceEpoch(
            )
            self.model.model_data[idx][common.SortBySize] = size

            # Thumbnail
            height = self.model.model_data[idx][QtCore.Qt.SizeHintRole].height(
            ) - 2
            image = ImageCache.instance().get(settings.thumbnail_path(), height)
            if not image:
                def rsc_path(f, n): return u'{}/../rsc/{}.png'.format(f, n)
                ext = self.model.model_data[idx][QtCore.Qt.StatusTipRole].split(
                    '.')[-1]
                color = QtGui.QColor(0, 0, 0, 0)

                if ext in (common._creative_cloud_formats + common._exports_formats + common._scene_formats):
                    image = ImageCache.instance().get(rsc_path(__file__, ext), height)
                else:
                    image = ImageCache.instance().get(rsc_path(__file__, 'placeholder'), height)
            else:

                color = ImageCache.instance().get(settings.thumbnail_path(), 'BackgroundColor')

            self.model.model_data[idx][common.ThumbnailRole] = image
            self.model.model_data[idx][common.ThumbnailBackgroundRole] = color

            # Item flags
            flags = index.flags()
            flags = (flags |
                     QtCore.Qt.ItemIsSelectable |
                     QtCore.Qt.ItemIsEnabled |
                     QtCore.Qt.ItemIsEditable |
                     QtCore.Qt.ItemIsDragEnabled)

            if settings.value(u'config/archived'):
                flags = flags | MarkedAsArchived
            self.model.model_data[idx][common.FlagsRole] = flags
            self.model.model_data[idx][common.StatusRole] = True

            FileInfoWorker.remove_from_queue(idx)
            # self.indexUpdated.emit(index)


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

    def __init__(self, parent=None):
        super(FilesModel, self).__init__(parent=parent)

        self.asset = None
        self.mode = None
        self._isgrouped = None

        # Thread-worker reposinble for completing the model data
        self.threads = {}
        self.threads[0] = FileInfoThread(self)
        self.threads[0].thread_id = 0
        self.threads[1] = FileInfoThread(self)
        self.threads[1].thread_id = 1
        self.threads[2] = FileInfoThread(self)
        self.threads[2].thread_id = 2
        self.threads[3] = FileInfoThread(self)
        self.threads[3].thread_id = 3

        self.grouppingChanged.connect(self.switch_model_data)
        self.activeLocationChanged.connect(self.switch_model_data)

    def __initdata__(self):
        """The method is responsible for getting the bare-bones file and sequence
        definitions by running a recursive QDirIterator from the location-folder.

        Getting all additional information, like description, item flags, thumbnails
        are costly and therefore are populated by secondary thread-workers when
        switch the model dataset.

        """
        rowsize = QtCore.QSize(common.WIDTH, common.ROW_HEIGHT)
        flags = (QtCore.Qt.ItemNeverHasChildren)
        favourites = local_settings.value(u'favourites')
        favourites = favourites if favourites else []

        # Invalid asset, we'll do nothing.
        if not self.asset:
            return
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

        nth = 789
        n = 0

        while it.hasNext():
            n += 1
            if n % nth == 0:
                common.ProgressMessage.instance().set_message('{} files found...'.format(n - 1))

            filepath = it.next()

            # File-filter:
            if location in common.NameFilters:
                if not filepath.split('.')[-1] in common.NameFilters[location]:
                    continue

            fileroot = filepath.replace(location_path, '')
            fileroot = '/'.join(fileroot.split('/')[:-1]).strip('/')

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
                common.DescriptionRole: u'',
                common.TodoCountRole: 0,
                common.FileDetailsRole: u'',
                common.SequenceRole: seq,
                common.FramesRole: [],
                common.StatusRole: False,
                common.StartpathRole: None,
                common.EndpathRole: None,
                common.ThumbnailRole: None,
                common.ThumbnailBackgroundRole: None,
                common.TypeRole: common.FileItem,
                common.SortByName: filename,
                common.SortByLastModified: filename,
                common.SortBySize: filename,
            }

            # If the file in question is a sequence, we will also save a reference
            # to it in `self._model_data[location][True]` dictionary.
            if seq:
                seqpath = u'{}[0]{}.{}'.format(
                    seq.group(1), seq.group(3), seq.group(4))

                if seqpath not in seqs:  # ... and create it if it doesn't exist
                    seqname = seqpath.split(u'/')[-1]
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
                        common.DescriptionRole: u'',
                        common.TodoCountRole: 0,
                        common.FileDetailsRole: u'',
                        common.SequenceRole: seq,
                        common.FramesRole: [],
                        common.StatusRole: False,
                        common.StartpathRole: None,
                        common.EndpathRole: None,
                        common.ThumbnailRole: None,
                        common.ThumbnailBackgroundRole: None,
                        common.TypeRole: common.SequenceItem,
                        common.SortByName: seqname,
                        common.SortByLastModified: seqname,
                        common.SortBySize: seqname,
                    }
                seqs[seqpath][common.FramesRole].append(seq.group(2))
            else:
                seqs[filepath] = self._model_data[location][False][idx]

        # Casting the sequence data onto the model
        common.ProgressMessage.instance().set_message(u'Getting sequences...')
        for v in seqs.itervalues():
            idx = len(self._model_data[location][True])
            # A sequence with only one element is not a sequence!
            if len(v[common.FramesRole]) == 1:
                filepath = v[common.SequenceRole].expand(r'\1{}\3.\4')
                filepath = filepath.format(v[common.FramesRole][0])
                filename = filepath.split(u'/')[-1]
                v[QtCore.Qt.DisplayRole] = filename
                v[QtCore.Qt.EditRole] = filename
                v[QtCore.Qt.StatusTipRole] = filepath
                v[QtCore.Qt.ToolTipRole] = filepath
                v[common.TypeRole] = common.FileItem
            self._model_data[location][True][idx] = v

        self.model_data = self._model_data[location][self.is_grouped()]
        self.endResetModel()
        common.ProgressMessage.instance().clear_message()

    def switch_model_data(self):
        """The data is stored is stored in the private ``_model_data`` object.
        This object is not exposed to the model - this method will set the
        ``model_data`` to the appropiate data-point.

        The ``model_data`` is not fully loaded by the default. By switching the
        dataset we will trigger a secondary thread to querry the file-system and
        to load the missing pieces of data.

        """
        def chunks(l, n):
            """Yields successive n-sized chunks of the given list."""
            for i in xrange(0, len(l), n):
                yield l[i:i + n]

        location = self.get_location()
        groupping = self.is_grouped()
        if location not in self._model_data:
            self._model_data[location] = {True: {}, False: {}}

        if not self._model_data[location][groupping]:
            self.__initdata__()
        else:
            self.beginResetModel()
            self.model_data = self._model_data[location][groupping]
            self.endResetModel()

        idxs = [f for f in xrange(len(self.model_data))
                if not self.model_data[f][common.StatusRole]]
        if not idxs:
            return

        for idx, chunk in enumerate(chunks(idxs, int(math.ceil(len(idxs) / float(len(self.threads)))))):
            FileInfoWorker.add_to_queue(chunk)
            self.threads[idx].dataRequested.emit(chunk)

    @QtCore.Slot()
    def delete_thread(self, thread):
        del self.threads[thread.thread_id]

    @QtCore.Slot(QtCore.QModelIndex)
    def setAsset(self, index):
        """Sets a new asset for the model."""
        if index.data(common.ParentRole) == self.asset:
            return
        self.asset = index.data(common.ParentRole)
        self._model_data = {}
        self.modelDataResetRequested.emit()

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
        if val is None:
            return

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

    def __init__(self, parent=None):
        super(FilesWidget, self).__init__(parent=parent)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(False)
        self.setAcceptDrops(False)

        self.setWindowTitle(u'Files')
        self.setItemDelegate(FilesWidgetDelegate(parent=self))
        self.context_menu_cls = FilesWidgetContextMenu
        self.set_model(FilesModel(parent=self))

        def connectSignal(thread):
            thread.worker.indexUpdated.connect(self.update)
            thread.worker.finished.connect(self.repaint)

        for thread in self.model().sourceModel().threads.itervalues():
            thread.started.connect(functools.partial(connectSignal, thread))
            thread.start()

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
        self.activated.emit(index)

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
        self.activated.emit(index)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = FilesWidget()
    widget.show()
    app.exec_()
