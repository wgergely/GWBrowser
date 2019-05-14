# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, E1120

"""Module defines the QListWidget items used to browse the assets and the files
found by the collector classes.

"""

import sys
import traceback

from PySide2 import QtWidgets, QtCore, QtGui

from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.baselistwidget import BaseInlineIconWidget
from gwbrowser.baselistwidget import BaseModel
from gwbrowser.baselistwidget import initdata

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


def qlast_modified(n): return QtCore.QDateTime.fromMSecsSinceEpoch(n * 1000)


class FileInfoWorker(BaseWorker):
    """Thread-worker class responsible for updating the given indexes."""
    queue = Unique(99999)

    @staticmethod
    @QtCore.Slot(QtCore.QModelIndex)
    def process_index(index):
        """This worker is reponsible for populating an index's data
        with the description, file information.

        """
        if not index.isValid():
            return
        if not index.data(QtCore.Qt.StatusTipRole):
            return
        index = index.model().mapToSource(index)
        # To be on the save-side let's skip initiated items
        if index.data(common.FileInfoLoaded):
            return

        # Item description
        settings = AssetSettings(index)
        description = settings.value(u'config/description')
        data = index.model().model_data()[index.row()]
        if description:
            data[common.DescriptionRole] = description

        # For sequence items we will work out the name of the sequence
        # based on the frames contained in the sequence
        # This is a moderately costly operation hence, we're doing this here
        # on the thread...
        if data[common.TypeRole] == common.SequenceItem:
            intframes = [int(f) for f in data[common.FramesRole]]
            padding = len(data[common.FramesRole][0])
            rangestring = common.get_ranges(intframes, padding)

            p = data[common.SequenceRole].expand(
                ur'\1{}\3.\4')
            startpath = p.format(unicode(min(intframes)).zfill(padding))
            endpath = p.format(unicode(max(intframes)).zfill(padding))
            seqpath = p.format(u'[{}]'.format(rangestring))
            seqname = seqpath.split(u'/')[-1]

            # Setting the path names
            data[common.StartpathRole] = startpath
            data[common.EndpathRole] = endpath
            data[QtCore.Qt.StatusTipRole] = seqpath
            data[QtCore.Qt.ToolTipRole] = seqpath
            data[QtCore.Qt.DisplayRole] = seqname
            data[QtCore.Qt.EditRole] = seqname

            # File description string
            mtime = 0
            for entry in data[common.EntryRole]:
                stat = entry.stat()
                mtime = stat.st_mtime if stat.st_mtime > mtime else mtime
                data[common.SortBySize] += stat.st_size
            mtime = qlast_modified(mtime)

            info_string = u'{count} files  |  {day}/{month}/{year} {hour}:{minute}  {size}'.format(
                count=len(intframes),
                day=mtime.toString(u'dd'),
                month=mtime.toString(u'MM'),
                year=mtime.toString(u'yyyy'),
                hour=mtime.toString(u'hh'),
                minute=mtime.toString(u'mm'),
                size=common.byte_to_string(data[common.SortBySize])
            )
        else:
            stat = data[common.EntryRole][0].stat()
            mtime = qlast_modified(stat.st_mtime)
            data[common.SortBySize] = stat.st_size
            info_string = u'{day}/{month}/{year} {hour}:{minute}  {size}'.format(
                day=mtime.toString(u'dd'),
                month=mtime.toString(u'MM'),
                year=mtime.toString(u'yyyy'),
                hour=mtime.toString(u'hh'),
                minute=mtime.toString(u'mm'),
                size=common.byte_to_string(data[common.SortBySize])
            )
        data[common.FileDetailsRole] = info_string

        # Item flags
        flags = index.flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled

        if settings.value(u'config/archived'):
            flags = flags | MarkedAsArchived
        data[common.FlagsRole] = flags

        # Finally, we set the FileInfoLoaded flag to indicate this item
        # has loaded the file data successfully
        data[common.FileInfoLoaded] = True
        index.model().dataChanged.emit(index, index)


class FileInfoThread(BaseThread):
    Worker = FileInfoWorker


class FileThumbnailWorker(BaseWorker):
    """Thread-worker class responsible for updating the given indexes."""
    queue = Unique(999)

    @staticmethod
    @QtCore.Slot(QtCore.QModelIndex)
    def process_index(index):
        """This worker only considers thumbnails."""
        if not index.isValid():
            return
        if not index.data(QtCore.Qt.StatusTipRole):
            return

        index = index.model().mapToSource(index)
        data = index.model().model_data()[index.row()]

        settings = AssetSettings(index)
        height = data[QtCore.Qt.SizeHintRole].height() - common.ROW_SEPARATOR

        ext = data[QtCore.Qt.StatusTipRole].split('.')[-1]
        placeholder_color = common.THUMBNAIL_BACKGROUND

        if ext in common.all_formats:
            placeholder_image = ImageCache.instance().get(
                common.rsc_path(__file__, ext), height)
        else:
            placeholder_image = ImageCache.instance().get(
                common.rsc_path(__file__, u'placeholder'), height)

        needs_thumbnail = False
        image = None

        if QtCore.QFileInfo(settings.thumbnail_path()).exists():
            image = ImageCache.instance().get(settings.thumbnail_path(), height)

        if not image:  # The item doesn't have a saved thumbnail...
            ext = data[QtCore.Qt.StatusTipRole].split('.')[-1]
            if ext in common.oiio_formats:
                needs_thumbnail = True
                placeholder_image = ImageCache.instance().get(
                    common.rsc_path(__file__, u'spinner'), height)
            image = placeholder_image
            color = placeholder_color
        else:
            color = ImageCache.instance().get(settings.thumbnail_path(), u'BackgroundColor')

        data[common.ThumbnailPathRole] = settings.thumbnail_path()
        data[common.DefaultThumbnailRole] = placeholder_image
        data[common.DefaultThumbnailBackgroundRole] = placeholder_color
        data[common.ThumbnailRole] = image
        data[common.ThumbnailBackgroundRole] = color

        index.model().dataChanged.emit(index, index)

        # Let's generate the thumbnail if auto-generation is turned on
        if index.model().generate_thumbnails and needs_thumbnail:
            ImageCacheWorker.process_index(index)


class FileThumbnailThread(BaseThread):
    Worker = FileThumbnailWorker


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

    def __init__(self, threads=common.FTHREAD_COUNT, parent=None):
        super(FilesModel, self).__init__(parent=parent)
        self.threads = {}

        for n in xrange(threads):
            self.threads[n] = FileInfoThread(self)
            self.threads[n].thread_id = n
            self.threads[n].start()

            self.threads[n * 2] = FileThumbnailThread(self)
            self.threads[n * 2].thread_id = n * 2
            self.threads[n * 2].start()

        cls = self.__class__.__name__
        _generate_thumbnails = local_settings.value(
            u'widget/{}/generate_thumbnails'.format(cls))
        self.generate_thumbnails = True if _generate_thumbnails is None else _generate_thumbnails
        
    @initdata
    def __initdata__(self):
        """The method is responsible for getting the bare-bones file and sequence
        definitions by running a file-iterator from the location-folder.

        Getting all additional information, like description, item flags, thumbnails
        are costly and therefore are populated by secondary thread-workers when
        switch the model dataset.

        Notes:
            Experiencing serious performance issues with the built-in QDirIterator
            on Mac OS X samba shares and the performance isn't great on windows either.
            Querrying the filesystem using the method is magnitudes slower than
            using the same methods on windows.

            A workaround I found was to use Python 3+'s scandir module. Both on
            Windows and Mac OS X the performance seems to be adequate.

        """
        def dflags():
            """The default flags to apply to the item."""
            return (
                QtCore.Qt.ItemNeverHasChildren |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable)

        FileInfoWorker.reset_queue()
        FileThumbnailWorker.reset_queue()
        ImageCacheWorker.reset_queue()

        dkey = self.data_key()
        rowsize = QtCore.QSize(common.WIDTH, common.ROW_HEIGHT)

        self._data[dkey] = {
            common.FileItem: {},
            common.SequenceItem: {}
        }

        seqs = {}

        favourites = local_settings.value(u'favourites')
        favourites = favourites if favourites else []
        sfavourites = set(favourites)
        activefile = local_settings.value('activepath/file')

        # Invalid asset, we'll do nothing.
        if not self._parent_item:
            return
        if not all(self._parent_item):
            return

        server, job, root, asset = self._parent_item
        location = self.data_key()
        location_path = (u'{}/{}/{}/{}/{}'.format(
            server, job, root, asset, location
        ))

        default_thumbnail_image = ImageCache.instance().get(
            common.rsc_path(__file__, u'placeholder'),
            rowsize.height() - common.ROW_SEPARATOR)
        default_background_color = common.THUMBNAIL_BACKGROUND

        nth = 987
        c = 0
        for _, _, fileentries in common.walk(location_path):
            for entry in fileentries:
                filepath = entry.path.replace(u'\\', u'/')
                filename = entry.name

                if location in common.NameFilters:
                    if not filepath.split(u'.')[-1] in common.NameFilters[location]:
                        continue

                # Progress bar
                c += 1
                if not c % nth:
                    self.messageChanged.emit(
                        u'Found {} files...'.format(c))
                    QtWidgets.QApplication.instance().processEvents(
                        QtCore.QEventLoop.ExcludeUserInputEvents)

                fileroot = filepath.replace(location_path, u'')
                fileroot = u'/'.join(fileroot.split(u'/')[:-1]).strip(u'/')

                seq = common.get_sequence(filepath)

                # Hidden files we don't care about should probably come from a centralised list...
                if filename.startswith(u'.'):
                    continue
                if u'thumbs.db'.lower() in filename.lower():
                    continue

                ext = filename.split(u'.')[-1].lower()
                if ext in common.all_formats:
                    placeholder_image = ImageCache.instance().get(
                        common.rsc_path(__file__, ext), rowsize.height())
                else:
                    placeholder_image = ImageCache.instance().get(
                        common.rsc_path(__file__, u'placeholder'), rowsize.height())

                flags = dflags()

                if filepath in sfavourites:
                    flags = flags | MarkedAsFavourite

                if activefile:
                    if activefile in filepath:
                        flags = flags | MarkedAsActive

                # stat = entry.stat()
                idx = len(self._data[dkey][common.FileItem])
                self._data[dkey][common.FileItem][idx] = {
                    QtCore.Qt.DisplayRole: filename,
                    QtCore.Qt.EditRole: filename,
                    QtCore.Qt.StatusTipRole: filepath,
                    QtCore.Qt.ToolTipRole: filepath,
                    QtCore.Qt.SizeHintRole: rowsize,
                    common.EntryRole: [entry, ],
                    common.FlagsRole: flags,
                    common.ParentRole: (server, job, root, asset, location, fileroot),
                    common.DescriptionRole: u'',
                    common.TodoCountRole: 0,
                    common.FileDetailsRole: u'',
                    common.SequenceRole: seq,
                    common.FramesRole: [],
                    common.FileInfoLoaded: False,
                    common.FileThumbnailLoaded: False,
                    common.StartpathRole: None,
                    common.EndpathRole: None,
                    #
                    common.DefaultThumbnailRole: default_thumbnail_image,
                    common.DefaultThumbnailBackgroundRole: default_background_color,
                    common.ThumbnailPathRole: None,
                    common.ThumbnailRole: default_thumbnail_image,
                    common.ThumbnailBackgroundRole: default_background_color,
                    #
                    common.TypeRole: common.FileItem,
                    common.SortByName: filepath,
                    common.SortByLastModified: 0,
                    common.SortBySize: 0,
                }

                if fileroot not in self._keywords and len(fileroot.split(u'/')) <= 4:
                    self._keywords[fileroot] = fileroot

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

                    # If the sequence has not yet been added to our dictionary
                    # of seqeunces we add it here
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

                        if key in sfavourites:
                            flags = flags | MarkedAsFavourite

                        seqs[seqpath] = {
                            QtCore.Qt.DisplayRole: seqname,
                            QtCore.Qt.EditRole: seqname,
                            QtCore.Qt.StatusTipRole: seqpath,
                            QtCore.Qt.ToolTipRole: seqpath,
                            QtCore.Qt.SizeHintRole: rowsize,
                            common.EntryRole: [],
                            common.FlagsRole: flags,
                            common.ParentRole: (server, job, root, asset, location, fileroot),
                            common.DescriptionRole: u'',
                            common.TodoCountRole: 0,
                            common.FileDetailsRole: u'',
                            common.SequenceRole: seq,
                            common.FramesRole: [],
                            common.FileInfoLoaded: False,
                            common.FileThumbnailLoaded: False,
                            common.StartpathRole: None,
                            common.EndpathRole: None,
                            #
                            common.DefaultThumbnailRole: default_thumbnail_image,
                            common.DefaultThumbnailBackgroundRole: default_background_color,
                            common.ThumbnailPathRole: None,
                            common.ThumbnailRole: default_thumbnail_image,
                            common.ThumbnailBackgroundRole: default_background_color,
                            #
                            common.TypeRole: common.SequenceItem,
                            common.SortByName: seqpath,
                            common.SortByLastModified: 0,
                            common.SortBySize: 0,  # Initializing with null-size
                        }

                    seqs[seqpath][common.FramesRole].append(seq.group(2))
                    seqs[seqpath][common.EntryRole].append(entry)
                else:
                    seqs[filepath] = self._data[dkey][common.FileItem][idx]

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
                v[common.SortByLastModified] = 0

                flags = dflags()
                if filepath in sfavourites:
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
        constructed here. There are ambiguities in the absence of any good documentation
        regarding what mime types have to be defined exactly for fully supporting
        drag and drop on all platforms.

        On windows, ``application/x-qt-windows-mime;value="FileName"`` and
        ``application/x-qt-windows-mime;value="FileNameW"`` types seems to be necessary,
        but on MacOS a simple uri list seem to suffice.

        """
        def add_path_to_mime(mime, path):
            """Adds the given path to the mime data."""
            path = QtCore.QFileInfo(path).absoluteFilePath()
            path = QtCore.QDir.toNativeSeparators(path)

            mime.setUrls(mime.urls() + [QtCore.QUrl.fromLocalFile(path), ])
            data = common.ubytearray(QtCore.QDir.toNativeSeparators(path))
            mime.setData(
                'application/x-qt-windows-mime;value="FileName"', data)
            mime.setData(
                'application/x-qt-windows-mime;value="FileNameW"', data)

            return mime

        mime = QtCore.QMimeData()
        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        no_modifier = modifiers == QtCore.Qt.NoModifier
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier

        for index in indexes:
            if not index.isValid():
                continue
            path = index.data(QtCore.Qt.StatusTipRole)

            if no_modifier:
                path = common.get_sequence_endpath(path)
                add_path_to_mime(mime, path)
            elif alt_modifier and shift_modifier:
                path = QtCore.QFileInfo(path).dir().path()
                add_path_to_mime(mime, path)
            elif alt_modifier:
                path = common.get_sequence_startpath(path)
                add_path_to_mime(mime, path)
            elif shift_modifier:
                paths = common.get_sequence_paths(index)
                for path in paths:
                    add_path_to_mime(mime, path)
        return mime


class FilesWidget(BaseInlineIconWidget):
    """Files widget is responsible for listing the files items."""
    resized = QtCore.Signal(
        QtCore.QRect)  # Used to update the size of the DataKeyView

    def __init__(self, parent=None):
        """Init method.

        Attributes:
            _index_timer (QTimer): The timer responsible for queuing indexes to update.

        """
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
        self._index_timer.setInterval(common.FTIMER_INTERVAL)
        self._index_timer.setSingleShot(False)
        self._index_timer.timeout.connect(self.initialize_visible_indexes)

        self.model().sourceModel().modelAboutToBeReset.connect(
            self.reset_thread_worker_queues)
        self.model().modelAboutToBeReset.connect(self.reset_thread_worker_queues)
        self.model().layoutAboutToBeChanged.connect(self.reset_thread_worker_queues)

        self.model().modelAboutToBeReset.connect(self._index_timer.stop)
        self.model().modelReset.connect(self._index_timer.start)
        self.model().layoutAboutToBeChanged.connect(self._index_timer.stop)
        self.model().layoutChanged.connect(self._index_timer.start)

        self.verticalScrollBar().valueChanged.connect(FileThumbnailWorker.reset_queue)

    @QtCore.Slot()
    def reset_thread_worker_queues(self):
        FileInfoWorker.reset_queue()
        FileThumbnailWorker.reset_queue()
        ImageCacheWorker.reset_queue()

    @QtCore.Slot()
    def initialize_visible_indexes(self):
        """The sourceModel() loads it's data in two steps, there's a single-threaded
        data-collections, and a threaded second pass to load thumbnails and
        descriptions.

        To optimize the second pass we will only queue items that are visible
        in the view.

        """
        needs_info = []
        needs_thumbnail = []

        if self.verticalScrollBar().isSliderDown():
            return

        index = self.indexAt(self.rect().topLeft())
        if not index.isValid():
            return

        # Starting from the to we add all the visible, and unititalized indexes
        rect = self.visualRect(index)
        while self.rect().contains(rect):
            if not index.data(common.FileInfoLoaded):
                needs_info.append(index)
            if not index.data(common.FileThumbnailLoaded):
                needs_thumbnail.append(index)

            rect.moveTop(rect.top() + rect.height())
            index = self.indexAt(rect.topLeft())
            if not index.isValid():
                break

        # Here we add the last index of the window
        index = self.indexAt(self.rect().bottomLeft())
        if index.isValid():
            if not index.data(common.FileInfoLoaded):
                if index not in needs_info:
                    needs_info.append(index)
            if self.model().sourceModel().generate_thumbnails:
                if not index.data(common.FileThumbnailLoaded):
                    if index not in needs_thumbnail:
                        needs_thumbnail.append(index)

        # We want to make sure we keep archived items hidden. If we detect any
        # archived items, we will invalidate the proxy model.
        if needs_info:
            if not self.model().filterFlag(MarkedAsArchived):
                if [f for f in needs_info if f.flags() & MarkedAsArchived]:
                    self.model().invalidateFilter()
                    return

        FileInfoWorker.add_to_queue(needs_info)
        if self.model().sourceModel().generate_thumbnails:
            FileThumbnailWorker.add_to_queue(needs_thumbnail)

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
        if self.buttons_hidden():
            return 0
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

    def resizeEvent(self, event):
        self.resized.emit(self.geometry())


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = FilesWidget()
    widget.show()
    app.exec_()
