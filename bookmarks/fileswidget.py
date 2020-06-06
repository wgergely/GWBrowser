# -*- coding: utf-8 -*-
"""The view and model used to browse files.

"""
from PySide2 import QtWidgets, QtCore, QtGui

import bookmarks.basecontextmenu as basecontextmenu
import bookmarks.baselist as baselist
import bookmarks.log as log
import bookmarks.common as common
import bookmarks.threads as threads
import _scandir as _scandir
import bookmarks.settings as settings
import bookmarks.delegate as delegate
import bookmarks.defaultpaths as defaultpaths
import bookmarks.images as images


FILTER_EXTENSIONS = False


class FilesWidgetContextMenu(basecontextmenu.BaseContextMenu):
    """Context menu associated with the `FilesWidget`."""

    def __init__(self, index, parent=None):
        super(FilesWidgetContextMenu, self).__init__(index, parent=parent)
        self.add_location_toggles_menu()
        self.add_separator()
        self.add_add_file_menu()
        self.add_separator()
        self.add_collapse_sequence_menu()
        self.add_separator()
        self.add_rv_menu()
        #
        self.add_separator()
        if index.isValid():
            self.add_mode_toggles_menu()
            self.add_separator()
        self.add_separator()
        self.add_row_size_menu()
        self.add_separator()
        self.add_set_generate_thumbnails_menu()
        self.add_separator()
        if index.isValid():
            self.add_copy_menu()
            self.add_reveal_item_menu()
        self.add_separator()
        self.add_sort_menu()
        self.add_separator()
        self.add_display_toggles_menu()
        self.add_separator()
        self.add_refresh_menu()


class FilesModel(baselist.BaseModel):
    """The model used store individual and file sequences found in `parent_path`.

    File data is saved ``self.INTERNAL_MODEL_DATA`` using the **task folder**,
    and **data_type** keys.

    .. code-block:: python

        data = self.model_data() # the currently exposed dataset
        data == self.INTERNAL_MODEL_DATA[self.task_folder()][self.data_type()]

    """
    DEFAULT_ROW_SIZE = QtCore.QSize(1, common.ROW_HEIGHT())
    val = settings.local_settings.value(u'widget/FilesModel/rowheight')
    val = val if val else DEFAULT_ROW_SIZE.height()
    val = DEFAULT_ROW_SIZE.height() if val < DEFAULT_ROW_SIZE.height() else val
    ROW_SIZE = QtCore.QSize(1, val)

    queue_type = threads.FileInfoQueue
    thumbnail_queue_type = threads.FileThumbnailQueue

    @property
    def parent_path(self):
        return (
            settings.ACTIVE['server'],
            settings.ACTIVE['job'],
            settings.ACTIVE['root'],
            settings.ACTIVE['asset'],
        )

    def _entry_iterator(self, path):
        for entry in _scandir.scandir(path):
            if entry.is_dir():
                for _entry in self._entry_iterator(entry.path):
                    yield _entry
            else:
                yield entry

    @baselist.initdata
    def __initdata__(self):
        """The method is responsible for getting the bare-bones file and
        sequence definitions by running a file-iterator stemming from
        ``self.parent_path``.

        Getting all additional information, like description, item flags,
        thumbnails are costly and therefore are populated by thread-workers.

        The method will iterate through all files in every subfolder and will
        automatically save individual ``FileItems`` and collapsed
        ``SequenceItems``.

        Switching between the two datasets is done via emitting the
        ``dataTypeChanged`` signal.

        Note:
            Experiencing serious performance issues with the built-in
            QDirIterator on Mac OS X samba shares and the performance isn't
            great on windows either. Querrying the filesystem using the method
            is magnitudes slower than using the same methods on windows.

            A workaround I found was to use Python 3+'s ``scandir`` module. Both
            on Windows and Mac OS X the performance seems to be good.

        Internally, the actual files are returned by `self._entry_iterator()`,
        this is where scandir is evoked.

        """
        def dflags():
            """The default flags to apply to the item."""
            return (
                QtCore.Qt.ItemNeverHasChildren |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable)

        task_folder = self.task_folder().lower()

        SEQUENCE_DATA = common.DataDict()
        MODEL_DATA = common.DataDict({
            common.FileItem: common.DataDict(),
            common.SequenceItem: common.DataDict(),
        })

        favourites = settings.local_settings.favourites()
        sfavourites = set(favourites)

        server, job, root, asset = self.parent_path
        task_folder_extensions = defaultpaths.get_task_folder_extensions(
            task_folder)
        parent_path = u'/'.join(self.parent_path).lower() + \
            u'/' + task_folder

        nth = 987
        c = 0

        if not QtCore.QFileInfo(parent_path).exists():
            return

        for entry in self._entry_iterator(parent_path):
            if self._interrupt_requested:
                break

            # skipping directories
            if entry.is_dir():
                continue
            filename = entry.name.lower()

            if filename[0] == u'.':
                continue
            if u'thumbs.db' in filename:
                continue

            filepath = entry.path.lower().replace(u'\\', u'/')
            ext = filename.split(u'.')[-1]
            if FILTER_EXTENSIONS and task_folder_extensions and ext not in task_folder_extensions:
                continue

            # Progress bar
            c += 1
            if not c % nth:
                self.progressMessage.emit(
                    u'Loading files (found ' + unicode(c) + u' items)...')
                QtWidgets.QApplication.instance().processEvents()

            # Getting the fileroot
            fileroot = filepath.replace(parent_path, u'')
            fileroot = u'/'.join(fileroot.split(u'/')[:-1]).strip(u'/')

            try:
                seq = common.get_sequence(filepath)
            except RuntimeError:
                log.error(u'"' + filename + u'" named incorrectly. Skipping.')
                continue

            flags = dflags()

            if seq:
                seqpath = seq.group(1) + common.SEQPROXY + \
                    seq.group(3) + u'.' + seq.group(4)
                seqpath = seqpath.lower()
                if seqpath in sfavourites:
                    flags = flags | common.MarkedAsFavourite
            else:
                if filepath in sfavourites:
                    flags = flags | common.MarkedAsFavourite

            parent_path_role = (server, job, root, asset,
                                task_folder, fileroot)

            # Let's limit the maximum number of items we load
            idx = len(MODEL_DATA[common.FileItem])
            if idx >= common.MAXITEMS:
                break

            MODEL_DATA[common.FileItem][idx] = common.DataDict({
                QtCore.Qt.DisplayRole: filename,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.SizeHintRole: self.ROW_SIZE,
                #
                common.EntryRole: [entry, ],
                common.FlagsRole: flags,
                common.ParentPathRole: parent_path_role,
                common.DescriptionRole: u'',
                common.TodoCountRole: 0,
                common.FileDetailsRole: u'',
                common.SequenceRole: seq,
                common.FramesRole: [],
                common.FileInfoLoaded: False,
                common.StartpathRole: None,
                common.EndpathRole: None,
                #
                common.ThumbnailLoaded: False,
                #
                common.TypeRole: common.FileItem,
                #
                common.SortByNameRole: common.namekey(filepath),
                common.SortByLastModifiedRole: 0,
                common.SortBySizeRole: 0,
                #
                common.IdRole: idx  # non-mutable
            })

            # If the file in question is a sequence, we will also save a reference
            # to it in `self._model_data[location][True]` dictionary.
            if seq:
                # If the sequence has not yet been added to our dictionary
                # of seqeunces we add it here
                if seqpath not in SEQUENCE_DATA:  # ... and create it if it doesn't exist
                    seqname = seqpath.split(u'/')[-1]
                    flags = dflags()

                    if seqpath in sfavourites:
                        flags = flags | common.MarkedAsFavourite

                    SEQUENCE_DATA[seqpath] = common.DataDict({
                        QtCore.Qt.DisplayRole: seqname,
                        QtCore.Qt.EditRole: seqname,
                        QtCore.Qt.StatusTipRole: seqpath,
                        QtCore.Qt.SizeHintRole: self.ROW_SIZE,
                        common.EntryRole: [],
                        common.FlagsRole: flags,
                        common.ParentPathRole: parent_path_role,
                        common.DescriptionRole: u'',
                        common.TodoCountRole: 0,
                        common.FileDetailsRole: u'',
                        common.SequenceRole: seq,
                        common.FramesRole: [],
                        common.FileInfoLoaded: False,
                        common.StartpathRole: None,
                        common.EndpathRole: None,
                        #
                        common.ThumbnailLoaded: False,
                        #
                        common.TypeRole: common.SequenceItem,
                        common.SortByNameRole: common.namekey(seqpath),
                        common.SortByLastModifiedRole: 0,
                        common.SortBySizeRole: 0,  # Initializing with null-size
                        #
                        common.IdRole: 0
                    })

                SEQUENCE_DATA[seqpath][common.FramesRole].append(seq.group(2))
                SEQUENCE_DATA[seqpath][common.EntryRole].append(entry)
            else:
                SEQUENCE_DATA[filepath] = MODEL_DATA[common.FileItem][idx]

        # Casting the sequence data back onto the model
        for v in SEQUENCE_DATA.itervalues():
            idx = len(MODEL_DATA[common.SequenceItem])
            if len(v[common.FramesRole]) == 1:
                # A sequence with only one element is not a sequence
                _seq = v[common.SequenceRole]
                filepath = _seq.group(
                    1) + v[common.FramesRole][0] + _seq.group(3) + u'.' + _seq.group(4)
                filename = filepath.split(u'/')[-1]
                v[QtCore.Qt.DisplayRole] = filename
                v[QtCore.Qt.EditRole] = filename
                v[QtCore.Qt.StatusTipRole] = filepath
                v[common.TypeRole] = common.FileItem
                v[common.SortByNameRole] = common.namekey(filepath)
                v[common.SortByLastModifiedRole] = 0

                flags = dflags()
                if filepath.lower() in sfavourites:
                    flags = flags | common.MarkedAsFavourite

                v[common.FlagsRole] = flags

            elif len(v[common.FramesRole]) == 0:
                v[common.TypeRole] = common.FileItem

            MODEL_DATA[common.SequenceItem][idx] = v
            MODEL_DATA[common.SequenceItem][idx][common.IdRole] = idx

        self.INTERNAL_MODEL_DATA[task_folder] = MODEL_DATA

    def task_folder(self):
        """Current key to the data dictionary."""
        return settings.ACTIVE[u'task_folder']

    @QtCore.Slot(unicode)
    def set_task_folder(self, val):
        """Slot used to save task folder to the model instance and the local
        settings.

        Each subfolder inside the root folder, defined by``parent_path``,
        corresponds to a `key`. We use these keys to save model data associated
        with these folders.

        It's important to make sure the key we're about to set corresponds to an
        existing folder. We will use a reasonable default if the folder does not
        exist.

        """
        log.debug('set_task_folder({})'.format(val), self)
        try:
            settings.set_active(u'task_folder', val)
            if settings.ACTIVE['task_folder']:
                return
            path = u'/'.join((
                settings.ACTIVE['server'],
                settings.ACTIVE['job'],
                settings.ACTIVE['root'],
                settings.ACTIVE['asset'],
            ))
            entries = [f.name.lower() for f in _scandir.scandir(path)]

            # And finally, let's try to revert to a fall-back...
            scene = defaultpaths.TASK_FOLDERS['scene']['default'].lower()
            if scene in entries:
                settings.set_active(u'task_folder', scene)
                return
            if entries:
                settings.set_active('task_folder', entries[0].lower())
        except:
            log.error(u'Could not set task folder')
        finally:
            if not self.model_data():
                self.__initdata__()
            else:
                self.sort_data()

    def data_type(self):
        """Current key to the data dictionary."""
        task_folder = self.task_folder()
        if task_folder not in self._datatype:
            cls = self.__class__.__name__
            key = u'widget/{}/{}/datatype'.format(cls, task_folder)
            val = settings.local_settings.value(key)
            val = val if val else common.SequenceItem
            self._datatype[task_folder] = val
        return self._datatype[task_folder]

    def mimeData(self, indexes):
        """The data necessary for supporting drag and drop operations are
        constructed here.

        There is ambiguity in the absence of any good documentation I could find
        regarding what mime types have to be defined exactly for fully
        supporting drag and drop on all platforms.

        Note:
            On windows, ``application/x-qt-windows-mime;value="FileName"`` and
            ``application/x-qt-windows-mime;value="FileNameW"`` types seems to be
            necessary, but on MacOS a simple uri list seem to suffice.

        """
        def add_path_to_mime(mime, path):
            """Adds the given path to the mime data."""
            if not isinstance(path, unicode):
                s = u'Expected <type \'unicode\'>, got {}'.format(type(str))
                log.error(s)
                raise TypeError(s)

            path = QtCore.QFileInfo(path).absoluteFilePath()
            mime.setUrls(mime.urls() + [QtCore.QUrl.fromLocalFile(path), ])

            path = QtCore.QDir.toNativeSeparators(path).encode('utf-8')
            _bytes = QtCore.QByteArray(path)
            mime.setData(
                u'application/x-qt-windows-mime;value="FileName"', _bytes)
            mime.setData(
                u'application/x-qt-windows-mime;value="FileNameW"', _bytes)

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


class DragPixmap(QtWidgets.QWidget):
    """Widget used to define the appearance of an item being dragged."""

    def __init__(self, pixmap, text, parent=None):
        super(DragPixmap, self).__init__(parent=parent)
        self._pixmap = pixmap
        self._text = text

        font, metrics = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())
        self._text_width = metrics.width(text)

        width = self._text_width + common.MARGIN()
        width = common.WIDTH() + common.MARGIN() if width > common.WIDTH() else width

        self.setFixedHeight(pixmap.height())
        self.setFixedWidth(
            pixmap.width() + common.INDICATOR_WIDTH() + width + common.INDICATOR_WIDTH())

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.adjustSize()

    @classmethod
    def pixmap(cls, pixmap, text):
        """Returns the widget as a rendered pixmap."""
        w = cls(pixmap, text)
        pixmap = QtGui.QPixmap(w.size())
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        w.render(painter, QtCore.QPoint(), QtGui.QRegion())
        return pixmap

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.SECONDARY_BACKGROUND)
        painter.setOpacity(0.6)
        painter.drawRoundedRect(self.rect(), 4, 4)
        painter.setOpacity(1.0)

        pixmap_rect = QtCore.QRect(0, 0, self.height(), self.height())
        painter.drawPixmap(pixmap_rect, self._pixmap, self._pixmap.rect())

        width = self._text_width + common.INDICATOR_WIDTH()
        width = 640 if width > 640 else width
        rect = QtCore.QRect(
            self._pixmap.rect().width() + common.INDICATOR_WIDTH(),
            0,
            width,
            self.height()
        )
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(common.MEDIUM_FONT_SIZE())[0],
            rect,
            self._text,
            QtCore.Qt.AlignCenter,
            common.TEXT_SELECTED
        )
        painter.end()


class FilesWidget(baselist.ThreadedBaseWidget):
    """The view used to display the contents of a ``FilesModel`` instance.
    """
    SourceModel = FilesModel
    Delegate = delegate.FilesWidgetDelegate
    ContextMenu = FilesWidgetContextMenu

    def __init__(self, parent=None):
        super(FilesWidget, self).__init__(parent=parent)
        self.setWindowTitle(u'Files')
        self._background_icon = u'files'
        self.drag_source_index = QtCore.QModelIndex()
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setDragEnabled(True)
        self.viewport().setAcceptDrops(True)

    @QtCore.Slot(unicode)
    @QtCore.Slot(unicode)
    def new_file_added(self, task_folder, file_path):
        """Slot to be called when a new file has been added and
        we want to show.

        """
        if not task_folder:
            return

        # Setting the task folder
        self.model().sourceModel().taskFolderChanged.emit(task_folder)
        # And reloading the model...
        self.model().sourceModel().modelDataResetRequested.emit()

        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0)
            path = index.data(QtCore.Qt.StatusTipRole)
            path = common.get_sequence_endpath(path)
            if path.lower() == file_path:
                self.scrollTo(
                    index,
                    QtWidgets.QAbstractItemView.PositionAtCenter)
                self.selectionModel().setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect)
                break

    def set_model(self, *args, **kwargs):
        super(FilesWidget, self).set_model(*args, **kwargs)
        model = self.model().sourceModel()
        model.modelReset.connect(
            lambda: log.debug('modelReset -> load_saved_filter_text', model))
        model.modelReset.connect(self.load_saved_filter_text)

    @QtCore.Slot(unicode)
    def load_saved_filter_text(self):
        log.debug('load_saved_filter_text()', self)

        model = self.model().sourceModel()
        task_folder = model.task_folder()
        if not task_folder:
            log.error('load_saved_filter_text(): Data key not yet set')
            return

        cls = model.__class__.__name__
        k = u'widget/{}/{}/filtertext'.format(cls, task_folder)
        v = settings.local_settings.value(k)
        v = v if v else u''

        self.model().set_filter_text(v)

    def inline_icons_count(self):
        if self.buttons_hidden():
            return 0
        return 3

    def action_on_enter_key(self):
        self.activate(self.selectionModel().currentIndex())

    @QtCore.Slot(QtCore.QModelIndex)
    def save_activated(self, index):
        """Sets the current file as the ``active`` file."""
        parent_role = index.data(common.ParentPathRole)
        if not parent_role:
            return
        if len(parent_role) < 5:
            return

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        filepath = parent_role[5] + u'/' + \
            common.get_sequence_startpath(file_info.fileName())
            
        settings.save_active('file', filepath)

    def startDrag(self, supported_actions):
        """Creating a custom drag object here for displaying setting hotspots."""
        index = self.selectionModel().currentIndex()
        model = self.model().sourceModel()

        if not index.isValid():
            return
        if not index.data(QtCore.Qt.StatusTipRole):
            return
        if not index.data(common.ParentPathRole):
            return

        self.drag_source_index = index
        drag = QtGui.QDrag(self)
        # Getting the data from the source model
        drag.setMimeData(model.mimeData([index, ]))

        # Setting our custom cursor icons
        height = index.data(QtCore.Qt.SizeHintRole).height()

        def px(s):
            return images.ImageCache.get_rsc_pixmap(s, None, common.MARGIN())

        # Set drag icon
        drag.setDragCursor(px('CopyAction'), QtCore.Qt.CopyAction)
        drag.setDragCursor(px('MoveAction'), QtCore.Qt.MoveAction)
        # drag.setDragCursor(px('LinkAction'), QtCore.Qt.LinkAction)
        drag.setDragCursor(px('IgnoreAction'), QtCore.Qt.ActionMask)
        drag.setDragCursor(px('IgnoreAction'), QtCore.Qt.IgnoreAction)
        # drag.setDragCursor(px('TargetMoveAction'), QtCore.Qt.TargetMoveAction)

        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        no_modifier = modifiers == QtCore.Qt.NoModifier
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier

        # Set pixmap
        path = index.data(QtCore.Qt.StatusTipRole)
        source = images.get_thumbnail_path(
            index.data(common.ParentPathRole)[0],
            index.data(common.ParentPathRole)[1],
            index.data(common.ParentPathRole)[2],
            path
        )
        pixmap = images.ImageCache.get_pixmap(source, height)
        if not pixmap:
            source = images.get_placeholder_path(source)
            pixmap = images.ImageCache.get_pixmap(source, height)

        bookmark = u'/'.join(index.data(common.ParentPathRole)[:3])
        path = path.replace(bookmark, u'')
        path = path.strip(u'/')
        if no_modifier:
            path = common.get_sequence_endpath(path)
        elif alt_modifier and shift_modifier:
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'folder', common.SECONDARY_TEXT, height)
            path = QtCore.QFileInfo(path).dir().path()
        elif alt_modifier:
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'files', common.SECONDARY_TEXT, height)
            path = common.get_sequence_startpath(path)
        elif shift_modifier:
            path = common.get_sequence_startpath(path) + u', ++'
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'multiples_files', common.SECONDARY_TEXT, height)
        else:
            return

        self.update(index)
        if pixmap and not pixmap.isNull():
            pixmap = DragPixmap.pixmap(pixmap, path)
            drag.setPixmap(pixmap)

        try:
            lc = self.parent().parent().listcontrolwidget
            lc.drop_overlay.show()
        except:
            log.error(u'Could not show drag overlay')

        drag.exec_(supported_actions)

        try:
            lc.drop_overlay.hide()
        except:
            log.error('')

        self.drag_source_index = QtCore.QModelIndex()
