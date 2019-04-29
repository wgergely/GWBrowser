# -*- coding: utf-8 -*-
"""Module defines the QListWidget items used to browse the assets and the files
found by the collector classes.

"""
# pylint: disable=E1101, C0103, R0913, I1101

import sys
import os
import traceback
import math
import functools
import Queue

from PySide2 import QtWidgets, QtCore, QtGui

from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.baselistwidget import BaseInlineIconWidget
from gwbrowser.baselistwidget import BaseModel

import gwbrowser.common as common
from gwbrowser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite
from gwbrowser.settings import AssetSettings
from gwbrowser.settings import local_settings
from gwbrowser.delegate import FilesWidgetDelegate
import gwbrowser.editors as editors

from gwbrowser.imagecache import ImageCache
from gwbrowser.imagecache import ImageCacheWorker

from gwbrowser.threads import BaseThread
from gwbrowser.threads import BaseWorker
from gwbrowser.threads import Unique


class FileInfoWorker(BaseWorker):
    """Thread-worker class responsible for updating the given indexes."""
    queue = Unique(999999)

    @QtCore.Slot()
    def begin_processing(self):
        """Gets and sets the missing information for each index in a background
        thread.

        """
        try:
            while not self._shutdown:
                index = FileInfoWorker.queue.get(True)
                self.process_index(index)
        except RuntimeError as err:
            errstr = '\nRuntimeError in {}\n{}\n'.format(
                QtCore.QThread.currentThread(), err)
            sys.stderr.write(errstr)
            traceback.print_exc()
        except ValueError as err:
            errstr = '\nValueError in {}\n{}\n'.format(
                QtCore.QThread.currentThread(), err)
            sys.stderr.write(errstr)
            traceback.print_exc()
        except Exception as err:
            errstr = '\nError in {}\n{}\n'.format(
                QtCore.QThread.currentThread(), err)
            sys.stderr.write(errstr)
            traceback.print_exc()
        finally:
            if self._shutdown:
                sys.stdout.write('# {} worker finished processing.\n'.format(
                    self.__class__.__name__))
                self.finished.emit()
                return
            self.begin_processing()

    @staticmethod
    @QtCore.Slot(QtCore.QModelIndex)
    def process_index(index):
        """This static method is reponsible for populating an index's data
        with the description, file information,  thumbnail data.

        This process is automatically called by the `start_processing` method,
        and will push any index in the thread's Queue to this method.

        """
        if not index.isValid():
            return

        if not index.data(QtCore.Qt.StatusTipRole):
            return

        index = index.model().mapToSource(index)
        # To be on the save-side let's skip initiated items
        if index.data(common.StatusRole):
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
                ur'\1{}\3.\4')
            startpath = p.format(
                unicode(min(intframes)).zfill(len(frames[0])))
            endpath = p.format(
                unicode(max(intframes)).zfill(len(frames[0])))
            seqpath = p.format(u'[{}]'.format(rangestring))
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

                if common.osx:
                    stat = os.stat(framepath)
                    size += stat.st_size
                    last_modified = QtCore.QDateTime.fromMSecsSinceEpoch(stat.st_mtime * 1000) if file_info.lastModified(
                    ).toTime_t() > last_modified.toTime_t() else last_modified
                else:
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
            if common.osx:
                file_info = QtCore.QFileInfo(
                    data[QtCore.Qt.StatusTipRole])
                size = file_info.size()
                last_modified = file_info.lastModified()
            else:
                stat = os.stat(data[QtCore.Qt.StatusTipRole])
                size = stat.st_size
                last_modified = QtCore.QDateTime.fromMSecsSinceEpoch(stat.st_mtime * 1000)

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
        data[common.SortByLastModified] = u'{}'.format(
            last_modified.toMSecsSinceEpoch())
        data[common.SortBySize] = u'{}'.format(size)

        # Item flags
        flags = index.flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled
        #
        if settings.value(u'config/archived'):
            flags = flags | MarkedAsArchived
        data[common.FlagsRole] = flags
        data[common.StatusRole] = True

        # Thumbnail
        height = data[QtCore.Qt.SizeHintRole].height() - 2

        def rsc_path(f, n):
            path = u'{}/../rsc/{}.png'.format(f, n)
            path = os.path.normpath(os.path.abspath(path))
            return path
        ext = data[QtCore.Qt.StatusTipRole].split('.')[-1]
        placeholder_color = QtGui.QColor(0, 0, 0, 55)

        if ext in (common._creative_cloud_formats + common._exports_formats + common._scene_formats):
            placeholder_image = ImageCache.instance().get(rsc_path(__file__, ext), height)
        else:
            placeholder_image = ImageCache.instance().get(
                rsc_path(__file__, 'placeholder'), height)

        # THUMBNAILS
        needs_thumbnail = False
        image = None
        if QtCore.QFile(settings.thumbnail_path()).exists():
            image = ImageCache.instance().get(settings.thumbnail_path(), height)
        if not image:  # The item doesn't not have a saved thumbnail...
            ext = data[QtCore.Qt.StatusTipRole].split('.')[-1]
            if ext in common._oiio_formats:
                # ...but we can generate a thumbnail for it
                needs_thumbnail = True

            image = placeholder_image
            color = placeholder_color
        else:
            color = ImageCache.instance().get(settings.thumbnail_path(), 'BackgroundColor')

        data[common.ThumbnailPathRole] = settings.thumbnail_path()
        data[common.DefaultThumbnailRole] = placeholder_image
        data[common.DefaultThumbnailBackgroundRole] = placeholder_color
        data[common.ThumbnailRole] = image
        data[common.ThumbnailBackgroundRole] = color

        # Let's generate the thumbnail
        if needs_thumbnail:
            ImageCacheWorker.add_to_queue((index,))

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

    def __init__(self, threads=4, parent=None):
        super(FilesModel, self).__init__(parent=parent)
        self.threads = {}

        for n in xrange(threads):
            self.threads[n] = FileInfoThread(self)
            self.threads[n].thread_id = n
            self.threads[n].start()

    def __initdata__(self):
        """The method is responsible for getting the bare-bones file and sequence
        definitions by running a recursive QDirIterator from the location-folder.

        Getting all additional information, like description, item flags, thumbnails
        are costly and therefore are populated by secondary thread-workers when
        switch the model dataset.

        Notes:
            Experiencing serious performance issues with the built-in QDirIterator
            on Mac OS X samba shares.
            Querrying the filesystem using the method is magnitudes slower than
            using the same methods on windows.

            A workaround I found was to use the scandir module. On windows I
            found that it is somewhat slower than QDirIterator but on Mac OS X
            it is much faster.

        """
        def rsc_path(f, n):
            path = u'{}/../rsc/{}.png'.format(f, n)
            path = os.path.normpath(os.path.abspath(path))
            return path

        def dflags(): return (
            QtCore.Qt.ItemNeverHasChildren |
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsSelectable
        )

        FileInfoWorker.reset_queue()
        ImageCacheWorker.reset_queue()

        dkey = self.data_key()
        rowsize = QtCore.QSize(common.WIDTH, common.ROW_HEIGHT)
        self._data[dkey] = {
            common.FileItem: {}, common.SequenceItem: {}}
        seqs = {}

        favourites = local_settings.value(u'favourites')
        favourites = favourites if favourites else []
        activefile = local_settings.value('activepath/file')

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

        placeholder_color = QtGui.QColor(0, 0, 0, 55)

        # Iterator
        it = common.file_iterator(location_path)

        __n = 999
        __c = 0
        for filepath in it:
            if location in common.NameFilters:
                if not filepath.split('.')[-1] in common.NameFilters[location]:
                    continue

            fileroot = filepath.replace(location_path, '')
            fileroot = '/'.join(fileroot.split('/')[:-1]).strip('/')

            seq = common.get_sequence(filepath)
            filename = filepath.split('/')[-1]

            if filename.startswith(u'.'):
                continue

            if u'Thumbs.db' in filename:
                continue

            ext = filename.split('.')[-1]
            if ext in (common._creative_cloud_formats + common._exports_formats + common._scene_formats):
                placeholder_image = ImageCache.instance().get(
                    rsc_path(__file__, ext), rowsize.height())
            else:
                placeholder_image = ImageCache.instance().get(
                    rsc_path(__file__, 'placeholder'), rowsize.height())

            flags = dflags()

            if filepath in favourites:
                flags = flags | MarkedAsFavourite

            if activefile:
                if activefile in filepath:
                    flags = flags | MarkedAsActive

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
                try:
                    seqpath = u'{}[0]{}.{}'.format(
                        unicode(seq.group(1), 'utf-8'),
                        unicode(seq.group(3), 'utf-8'),
                        unicode(seq.group(4), 'utf-8'))
                except TypeError:
                    seqpath = u'{}[0]{}.{}'.format(
                        seq.group(1),
                        seq.group(3),
                        seq.group(4))


                if seqpath not in seqs:  # ... and create it if it doesn't exist
                    seqname = seqpath.split(u'/')[-1]
                    flags = dflags()
                    try:
                        key = u'{}{}.{}'.format(
                            unicode(seq.group(1), 'utf-8'),
                            unicode(seq.group(3), 'utf-8'),
                            unicode(seq.group(4), 'utf-8'))
                    except TypeError:
                        key = u'{}{}.{}'.format(
                            seq.group(1),
                            seq.group(3),
                            seq.group(4))

                    if key in favourites:
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
                        common.SortByName: seqpath,
                        common.SortByLastModified: seqpath,
                        common.SortBySize: seqpath,
                    }
                try:
                    seqs[seqpath][common.FramesRole].append(unicode(seq.group(2), 'utf-8'))
                except TypeError:
                    seqs[seqpath][common.FramesRole].append(seq.group(2))
            else:
                seqs[filepath] = self._data[dkey][common.FileItem][idx]

            __c += 1
            if __c % __n == 0:
                QtWidgets.QApplication.instance().processEvents()

        # Casting the sequence data onto the model
        for v in seqs.itervalues():
            idx = len(self._data[dkey][common.SequenceItem])
            # A sequence with only one element is not a sequence!
            if len(v[common.FramesRole]) == 1:
                filepath = v[common.SequenceRole].expand(ur'\1{}\3.\4')
                filepath = filepath.format(v[common.FramesRole][0])
                filename = filepath.split(u'/')[-1]
                v[QtCore.Qt.DisplayRole] = filename
                v[QtCore.Qt.EditRole] = filename
                v[QtCore.Qt.StatusTipRole] = filepath
                v[QtCore.Qt.ToolTipRole] = filepath
                v[common.TypeRole] = common.FileItem
                v[common.SortByName] = filepath
                v[common.SortByLastModified] = filepath
                v[common.SortBySize] = filepath

                flags = dflags()
                if filepath in favourites:
                    flags = flags | MarkedAsFavourite

                if activefile:
                    if activefile in filepath:
                        flags = flags | MarkedAsActive

                v[common.FlagsRole] = flags

            elif len(v[common.FramesRole]) == 0:
                v[common.TypeRole] = common.FileItem
            else:
                if activefile:
                    _firsframe = v[common.SequenceRole].expand(ur'\1{}\3.\4')
                    _firsframe = _firsframe.format(min(v[common.FramesRole]))
                    if activefile in _firsframe:
                        v[common.FlagsRole] = v[common.FlagsRole] | MarkedAsActive
            self._data[dkey][common.SequenceItem][idx] = v
        self.endResetModel()

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
        """The data necessary for supporting drag and drop operations are
        constructed here."""

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

        filepath = QtCore.QFileInfo(filepath).absoluteFilePath()
        filepath = QtCore.QDir.toNativeSeparators(filepath)

        url = QtCore.QUrl.fromLocalFile(filepath)
        mime.setUrls((
            url,
        ))

        mime.setData(
            'application/x-qt-windows-mime;value="FileName"',
            QtCore.QByteArray(str(QtCore.QDir.toNativeSeparators(filepath))))

        mime.setData(
            'application/x-qt-windows-mime;value="FileNameW"',
            QtCore.QByteArray(str(QtCore.QDir.toNativeSeparators(filepath))))

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
        self.setAcceptDrops(False)
        self.setDropIndicatorShown(False)
        self.setWindowTitle(u'Files')
        self.setAutoScroll(True)

        self.setItemDelegate(FilesWidgetDelegate(parent=self))
        self.context_menu_cls = FilesWidgetContextMenu
        self.set_model(FilesModel(parent=self))

        self._index_timer = QtCore.QTimer()
        self._index_timer.setInterval(1000)
        self._index_timer.setSingleShot(False)
        self._index_timer.timeout.connect(self.initialize_visible_indexes)

        self.model().sourceModel().modelAboutToBeReset.connect(
            self.reset_thread_worker_queues)
        self.model().modelAboutToBeReset.connect(self.reset_thread_worker_queues)
        self.model().layoutAboutToBeChanged.connect(self.reset_thread_worker_queues)

        self.model().modelAboutToBeReset.connect(self._index_timer.stop)
        self.model().modelReset.connect(self._index_timer.start)

    @QtCore.Slot()
    def reset_thread_worker_queues(self):
        FileInfoWorker.reset_queue()
        ImageCacheWorker.reset_queue()

    @QtCore.Slot()
    def initialize_visible_indexes(self):
        """The sourceModel() loads it's data in two steps, there's a single-threaded
        data-collections, and a threaded second pass to load thumbnails and
        descriptions.

        To optimize the second pass we will only queue items that are visible
        in the view.

        """
        indexes = []
        _indexes = []

        if self.verticalScrollBar().isSliderDown():
            return

        # First let's remove the queued items
        if FileInfoWorker.queue.qsize() > 99:
            return

        index = self.indexAt(self.rect().topLeft())
        if not index.isValid():
            return

        # Starting from the to we add all the visible, and unititalized indexes
        rect = self.visualRect(index)
        while self.rect().contains(rect):
            _indexes.append(index)
            if not index.data(common.StatusRole):
                indexes.append(index)

            rect.moveTop(rect.top() + rect.height())
            index = self.indexAt(rect.topLeft())
            if not index.isValid():
                break

        if _indexes:
            # Let's make sure the archived items don't creep in when they have
            # their flags updated
            if not self.model().filterFlag(MarkedAsArchived):
                for _index in _indexes:
                    if _index.flags() & MarkedAsArchived:
                        self.model().invalidateFilter()
                        return

        # Here we add the last index of the window
        index = self.indexAt(self.rect().bottomLeft())
        if index.isValid():
            if not index.data(common.StatusRole):
                if index not in indexes:
                    indexes.append(index)

        if indexes:
            FileInfoWorker.add_to_queue(indexes)

    def eventFilter(self, widget, event):
        super(FilesWidget, self).eventFilter(widget, event)
        if widget is not self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            # Let's paint the icon of the current mode
            painter = QtGui.QPainter()
            painter.begin(self)
            pixmap = ImageCache.get_rsc_pixmap(
                'files', QtGui.QColor(0, 0, 0, 10), 128)
            rect = pixmap.rect()
            rect.moveCenter(self.rect().center())
            painter.drawPixmap(rect, pixmap, pixmap.rect())
            painter.end()
            return True
        return False

    def inline_icons_count(self):
        return 3

    def action_on_enter_key(self):
        self.activate(self.selectionModel().currentIndex())

    def save_data_key(self, key):
        local_settings.setValue(u'activepath/location', key)

    def save_activated(self, index):
        """Sets the current item item as ``active`` and
        emits the ``activeLocationChanged`` and ``activeFileChanged`` signals.

        """
        local_settings.setValue(u'activepath/location',
                                index.data(common.ParentRole)[4])

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        filepath = u'{}/{}'.format(  # location/subdir/filename.ext
            index.data(common.ParentRole)[5],
            common.get_sequence_startpath(file_info.fileName()))
        local_settings.setValue(u'activepath/file', filepath)

    def mouseDoubleClickEvent(self, event):
        """Custom double-click event.

        A double click can `activate` an item, or it can trigger an edit event.
        As each item is associated with multiple editors we have to inspect
        the double-click location before deciding what action to take.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
        if index.flags() & MarkedAsArchived:
            return

        rect = self.visualRect(index)

        thumbnail_rect = QtCore.QRect(rect)
        thumbnail_rect.setWidth(rect.height())
        thumbnail_rect.moveLeft(common.INDICATOR_WIDTH)

        name_rect = QtCore.QRect(rect)
        name_rect.setLeft(
            common.INDICATOR_WIDTH
            + name_rect.height()
            + common.MARGIN
        )
        name_rect.setRight(name_rect.right() - common.MARGIN)

        font = QtGui.QFont(common.PrimaryFont)
        metrics = QtGui.QFontMetrics(font)

        description_rect = QtCore.QRect(name_rect)

        name_rect.moveTop(name_rect.top() + (name_rect.height() / 2.0))
        name_rect.setHeight(metrics.height())
        name_rect.moveTop(name_rect.top() - (name_rect.height() / 2.0))

        # Moving the rectangle down one line
        description_rect.moveTop(
            description_rect.top() + (description_rect.height() / 2.0))
        description_rect.setHeight(metrics.height())
        description_rect.moveTop(description_rect.top(
        ) - (description_rect.height() / 2.0) + metrics.lineSpacing())

        source_index = self.model().mapToSource(index)
        if description_rect.contains(event.pos()):
            widget = editors.DescriptionEditorWidget(source_index, parent=self)
            widget.show()
            return
        elif thumbnail_rect.contains(event.pos()):
            ImageCache.instance().pick(source_index)
            return
        self.activate(self.selectionModel().currentIndex())

    def mousePressEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self._index_timer.stop()
        super(FilesWidget, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self._index_timer.start()
        super(FilesWidget, self).mouseReleaseEvent(event)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = FilesWidget()
    widget.show()
    app.exec_()
