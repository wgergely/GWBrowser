# -*- coding: utf-8 -*-
"""Module defines the QListWidget items used to browse the assets and the files
found by the collector classes.

"""
# pylint: disable=E1101, C0103, R0913, I1101

import sys
import traceback
import math
import functools
import Queue

from PySide2 import QtWidgets, QtCore, QtGui

from browser.basecontextmenu import BaseContextMenu
from browser.baselistwidget import BaseInlineIconWidget
from browser.baselistwidget import BaseModel

import browser.common as common
from browser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite
from browser.settings import AssetSettings
from browser.settings import local_settings
from browser.delegate import FilesWidgetDelegate
import browser.editors as editors

from browser.imagecache import ImageCache
from browser.imagecache import ImageCacheWorker

from browser.threads import BaseThread
from browser.threads import BaseWorker
from browser.threads import Unique



class FileInfoWorker(BaseWorker):
    """Thread-worker class responsible for updating the given indexes."""
    queue = Unique(999999)

    @QtCore.Slot(tuple)
    def begin_processing(self):
        """Gets and sets the missing information for each index in a background
        thread.

        """
        n = 0
        nth = 9
        try:
            while True:
                n += 1
                if FileInfoWorker.queue.qsize():
                    if n % nth == 0:
                        common.ProgressMessage.instance().set_message(
                            'Processing ({} left)...'.format(FileInfoWorker.queue.qsize()))
                else:
                    common.ProgressMessage.instance().clear_message()
                self.process_index(FileInfoWorker.queue.get(True))
        except RuntimeError as err:
            errstr = '\nRuntimeError in {}\n{}\n'.format(
                QtCore.QThread.currentThread(), err)
            sys.stderr.write(errstr)
            traceback.print_exc()
            self.error.emit(errstr)
        except ValueError as err:
            errstr = '\nValueError in {}\n{}\n'.format(
                QtCore.QThread.currentThread(), err)
            sys.stderr.write(errstr)
            traceback.print_exc()
            self.error.emit(errstr)
        except Exception as err:
            errstr = '\nError in {}\n{}\n'.format(
                QtCore.QThread.currentThread(), err)
            sys.stderr.write(errstr)
            traceback.print_exc()
            self.error.emit(errstr)
        finally:
            self.begin_processing()

    @QtCore.Slot(QtCore.QModelIndex)
    def process_index(self, index):
        """The actual processing happens here."""
        if not index.isValid():
            return

        # Item description
        settings = AssetSettings(index)
        description = settings.value(u'config/description')
        data = index.model().model_data()[index.row()]
        if description:
            data[common.DescriptionRole] = description

        # Sequence path and name
        if data[common.TypeRole] == common.SequenceItem:
            frames = sorted(data[common.FramesRole])
            intframes = [int(f) for f in frames]
            rangestring = common.get_ranges(intframes, len(frames[0]))

            p = data[common.SequenceRole].expand(
                r'\1{}\3.\4')
            startpath = p.format(
                unicode(min(intframes)).zfill(len(frames[0])))
            endpath = p.format(
                unicode(max(intframes)).zfill(len(frames[0])))
            seqpath = p.format('[{}]'.format(rangestring))
            seqname = seqpath.split(u'/')[-1]

            data[common.StartpathRole] = startpath
            data[common.EndpathRole] = endpath
            data[QtCore.Qt.StatusTipRole] = seqpath
            data[QtCore.Qt.ToolTipRole] = seqpath
            data[QtCore.Qt.DisplayRole] = seqname
            data[QtCore.Qt.EditRole] = seqname

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
                data[QtCore.Qt.StatusTipRole])
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
        data[common.FileDetailsRole] = info_string

        # Sort values
        # data[common.SortByName] = fileroot
        data[common.SortByLastModified] = last_modified.toMSecsSinceEpoch(
        )
        data[common.SortBySize] = size

        # Thumbnail
        height = data[QtCore.Qt.SizeHintRole].height() - 2
        def rsc_path(f, n): return u'{}/../rsc/{}.png'.format(f, n)
        ext = data[QtCore.Qt.StatusTipRole].split('.')[-1]
        placeholder_color = QtGui.QColor(0, 0, 0, 0)

        if ext in (common._creative_cloud_formats + common._exports_formats + common._scene_formats):
            placeholder_image = ImageCache.instance().get(rsc_path(__file__, ext), height)
        else:
            placeholder_image = ImageCache.instance().get(rsc_path(__file__, 'placeholder'), height)

        image = ImageCache.instance().get(settings.thumbnail_path(), height)
        if not image:
            image = placeholder_image
            color = placeholder_color
        else:
            color = ImageCache.instance().get(settings.thumbnail_path(), 'BackgroundColor')

        data[common.ThumbnailPathRole] = settings.thumbnail_path()
        data[common.DefaultThumbnailRole] = placeholder_image
        data[common.DefaultThumbnailBackgroundRole] = placeholder_color
        data[common.ThumbnailRole] = image
        data[common.ThumbnailBackgroundRole] = color

        # Item flags
        flags = index.flags()
        flags = index.flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled

        if settings.value(u'config/archived'):
            flags = flags | MarkedAsArchived
        data[common.FlagsRole] = flags
        data[common.StatusRole] = True

        index.model().dataChanged.emit(index, index)


class FileInfoThread(BaseThread):
    Worker = FileInfoWorker



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
            self.add_reveal_item_menu()
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

    The model stores information in the private `_data` dictionary, but the actual
    data is querried from the _data[data_key][data_type] dictionary.

    """

    def __init__(self, parent=None):
        super(FilesModel, self).__init__(parent=parent)

        # Thread-worker reposinble for completing the model data
        self.threads = {}
        for n in xrange(4):
            self.threads[n] = FileInfoThread(self)
            self.threads[n].thread_id = n
            self.threads[n].start()

    def __initdata__(self):
        """The method is responsible for getting the bare-bones file and sequence
        definitions by running a recursive QDirIterator from the location-folder.

        Getting all additional information, like description, item flags, thumbnails
        are costly and therefore are populated by secondary thread-workers when
        switch the model dataset.

        """
        dkey = self.data_key()
        self._data[dkey] = {
            common.FileItem: {}, common.SequenceItem: {}}
        seqs = {}

        rowsize = QtCore.QSize(common.WIDTH, common.ROW_HEIGHT)
        flags = (
            QtCore.Qt.ItemNeverHasChildren |
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsSelectable
        )
        favourites = local_settings.value(u'favourites')
        favourites = favourites if favourites else []

        # Invalid asset, we'll do nothing.
        if not self._parent_item:
            return
        if not all(self._parent_item):
            return

        server, job, root, asset = self._parent_item
        location = self.data_key()
        location_path = ('{}/{}/{}/{}/{}'.format(
            server, job, root, asset, location
        ))

        # Data-containers

        # Iterator
        itdir = QtCore.QDir(location_path)
        if not itdir.exists():
            return
        itdir.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        itdir.setSorting(QtCore.QDir.Unsorted)
        it = QtCore.QDirIterator(
            itdir, flags=QtCore.QDirIterator.Subdirectories)

        nth = 789
        n = 0

        def rsc_path(f, n): return u'{}/../rsc/{}.png'.format(f, n)
        placeholder_color = QtGui.QColor(0,0,0,0)

        while it.hasNext():
            n += 1
            if n % nth == 0:
                common.ProgressMessage.instance().set_message(
                    'Loading {} asset files...'.format(n - 1))

            filepath = it.next()

            # File-filter:
            if location in common.NameFilters:
                if not filepath.split('.')[-1] in common.NameFilters[location]:
                    continue

            fileroot = filepath.replace(location_path, '')
            fileroot = '/'.join(fileroot.split('/')[:-1]).strip('/')

            seq = common.get_sequence(filepath)
            filename = it.fileName()
            ext = filename.split('.')[-1]
            if ext in (common._creative_cloud_formats + common._exports_formats + common._scene_formats):
                placeholder_image = ImageCache.instance().get(rsc_path(__file__, ext), rowsize.height())
            else:
                placeholder_image = ImageCache.instance().get(rsc_path(__file__, 'placeholder'), rowsize.height())


            if filepath in favourites:
                flags = flags | MarkedAsFavourite

            idx = len(self._data[dkey][common.FileItem])
            self._data[dkey][common.FileItem][idx] = {
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
                common.ThumbnailRole: placeholder_image,
                common.ThumbnailBackgroundRole: placeholder_color,
                common.TypeRole: common.FileItem,
                common.SortByName: filepath,
                common.SortByLastModified: filepath,
                common.SortBySize: filepath,
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
                        common.ThumbnailRole: placeholder_image,
                        common.ThumbnailBackgroundRole: placeholder_color,
                        common.TypeRole: common.SequenceItem,
                        common.SortByName: seqname,
                        common.SortByLastModified: seqname,
                        common.SortBySize: seqname,
                    }
                seqs[seqpath][common.FramesRole].append(seq.group(2))
            else:
                seqs[filepath] = self._data[dkey][common.FileItem][idx]

        # Casting the sequence data onto the model
        common.ProgressMessage.instance().set_message(u'Loading...')
        for v in seqs.itervalues():
            idx = len(self._data[dkey][common.SequenceItem])
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

            if len(v[common.FramesRole]) == 0:
                v[common.TypeRole] = common.FileItem

            self._data[dkey][common.SequenceItem][idx] = v

        self.endResetModel()
        common.ProgressMessage.instance().clear_message()

    @QtCore.Slot()
    def delete_thread(self, thread):
        del self.threads[thread.thread_id]

    def canDropMimeData(self, data, action, row, column):
        return False

    def supportedDropActions(self):
        return QtCore.Qt.IgnoreAction

    def supportedDragActions(self):
        return QtCore.Qt.CopyAction

    def mimeData(self, indexes):
        index = next((f for f in indexes), None)
        mime = QtCore.QMimeData()
        location = self.data_key()
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
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(False)
        self.setWindowTitle(u'Files')
        self.setAutoScroll(True)
        # We have to disable tracking, as the valueChanged signals is
        # populating the FileInfoThread's queue
        # self.verticalScrollBar().setTracking(False)

        self.setItemDelegate(FilesWidgetDelegate(parent=self))
        self.context_menu_cls = FilesWidgetContextMenu
        self.set_model(FilesModel(parent=self))


        self.model().modelAboutToBeReset.connect(self.reset_queue)
        self.model().modelReset.connect(
            self.queue_indexes)
        self.model().layoutChanged.connect(
            self.queue_indexes)
        self.verticalScrollBar().valueChanged.connect(
            self.queue_indexes)

    @QtCore.Slot()
    def reset_queue(self):
        FileInfoWorker.reset_queue()

    @QtCore.Slot()
    def queue_indexes(self):
        """The sourceModel() loads it's data in two steps, there's a single-threaded
        data-collections, and a threaded second pass to load thumbnails and
        descriptions.

        To optimize the second pass we will only queue items that are visible
        in the view.

        """
        app = QtWidgets.QApplication.instance()
        app.processEvents()

        indexes = []
        index = self.indexAt(self.rect().topLeft())
        if not index.isValid():
            return

        rect = self.visualRect(index)
        while self.rect().contains(rect):
            source_index = self.model().mapToSource(index)
            indexes.append(source_index)

            rect.moveTop(rect.top() + rect.height())
            index = self.indexAt(rect.topLeft())
            if not index.isValid():
                break
        index = self.indexAt(self.rect().bottomLeft())
        if index.isValid():
            source_index = self.model().mapToSource(index)
            if source_index not in indexes:
                indexes.append(source_index)

        FileInfoWorker.add_to_queue(indexes)


        # indexes = [m.index(f, 0) for f in xrange(len(data))
        #         if not data[f][common.StatusRole]]

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

    def save_activated(self, index):
        """Sets the current item item as ``active`` and
        emits the ``activeLocationChanged`` and ``activeFileChanged`` signals.

        """
        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        fileroot = index.data(common.ParentRole)[5]
        activefilepath = u'{}/{}'.format(fileroot, file_info.fileName())
        local_settings.setValue(u'activepath/file', activefilepath)

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
            common.INDICATOR_WIDTH
            + name_rect.height()
            + common.MARGIN
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

        self.activated.emit(index)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = FilesWidget()
    widget.show()
    app.exec_()
