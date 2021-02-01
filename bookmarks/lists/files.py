# -*- coding: utf-8 -*-
"""The view and model used to browse files.

"""
import _scandir
from PySide2 import QtWidgets, QtCore, QtGui

from .. import contextmenu
from .. import log
from .. import common
from .. import threads
from .. import settings
from .. import images
from .. import actions
from ..properties import asset_config

from . import base
from . import delegate



FILTER_EXTENSIONS = False


class FilesWidgetContextMenu(contextmenu.BaseContextMenu):
    def setup(self):
        self.window_menu()

        self.separator()
        self.task_toggles_menu()
        self.separator()

        self.title()

        self.services_menu()
        self.add_file_menu()
        self.bookmark_url_menu()
        self.asset_url_menu()
        self.sg_url_menu()
        self.reveal_item_menu()

        self.separator()

        self.sg_link_asset_menu()
        self.edit_active_bookmark_menu()
        self.edit_active_asset_menu()
        self.notes_menu()
        self.toggle_item_flags_menu()

        self.separator()

        self.set_generate_thumbnails_menu()
        self.row_size_menu()
        self.sort_menu()
        self.list_filter_menu()
        self.refresh_menu()

        self.separator()

        self.preferences_menu()

        self.separator()

        self.quit_menu()


class FilesModel(base.BaseModel):
    """Model used to list files in an asset.

    The root of the asset folder is never read, instead, each asset is expected
    to contain a series of subfolders - referred to here as `task folders`.

    The model will load files from one task folder at any given time. The
    current task folder can be retrieved using `self.task()`. Switching
    the task folders is done via the `taskFolderChanged.emit('my_task')`
    signal.

    Files & Sequences
    -----------------
    The model will load the found files into two separate data sets, one
    listing files individually, the other collects files into file sequences
    if they have an incremental number element.

    Switching between the `FileItems` and `SequenceItems` is done by emitting
    the `dataTypeChanged.emit(FileItem)` signal.

    File Format Filtering
    ---------------------

    If the current task folder has a curresponding configuration in the current
    bookmark's asset config, we can determine which file formats should be
    allowed to display in the folder.
    See the `asset_config.py` module for details.

    .. code-block:: python

        data = self.model_data() # the current data set
        data == self.INTERNAL_MODEL_DATA[self.task()][self.data_type()]

    """
    queue_type = threads.FileInfoQueue
    thumbnail_queue_type = threads.FileThumbnailQueue

    @base.initdata
    def __initdata__(self):
        """The method is responsible for getting the bare-bones file and
        sequence definitions by running a file-iterator stemming from
        ``self.parent_path()``.

        Additional information, like description, item flags, thumbnails are
        fetched by addittional thread workers.

        The method will iterate through all files in every subfolder and will
        automatically populate both individual ``FileItems`` and collapsed
        ``SequenceItems`` data sets. Switching between the two datasets is done
        by emitting the ``dataTypeChanged`` signal with the data type.

        Note:
            Experiencing performance issues with the built-in `QDirIterator` on
            Mac OS X Samba shares and the performance isn't great on Windows
            either. The implemented workaround is to use Python 3+'s ``scandir``
            module. Both on Windows and Mac OS X the performance seems to be
            great.

        Internally, the actual files are returned by `self._entry_iterator()`,
        the method where scandir is evoked.

        """
        def dflags():
            """The default flags to apply to the item."""
            return (
                QtCore.Qt.ItemNeverHasChildren |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable)

        task = self.task()
        if not task:
            return


        SEQUENCE_DATA = common.DataDict()
        MODEL_DATA = common.DataDict({
            common.FileItem: common.DataDict(),
            common.SequenceItem: common.DataDict(),
        })

        favourites = settings.local_settings.get_favourites()
        sfavourites = set(favourites)

        parent_path = self.parent_path()
        _parent_path = u'/'.join(parent_path + (task,))
        if not QtCore.QFileInfo(_parent_path).exists():
            return

        # Let' get the asset config instance to check what extensions are
        # currently allowed to be displayed in the task folder
        config = asset_config.get(*parent_path[0:3])
        is_valid_task = config.check_task(task)
        if is_valid_task:
            valid_extensions = config.get_task_extensions(task)
        else:
            valid_extensions = None
        disable_filter = self.disable_filter()

        nth = 987
        c = 0
        for entry in self._entry_iterator(_parent_path):
            if self._interrupt_requested:
                break

            # skipping directories
            if entry.is_dir():
                continue
            filename = entry.name

            # Skipping common hidden files
            if filename[0] == u'.':
                continue
            if u'thumbs.db' in filename:
                continue

            filepath = entry.path.replace(u'\\', u'/')
            ext = filename.split(u'.')[-1]

            # File format filter
            # We'll check against the current file extension against the allowed
            # extensions. If the task folder is not defined in the asset config,
            # we'll allow all extensions
            if not disable_filter and is_valid_task and ext not in valid_extensions:
                continue

            # Progress bar
            c += 1
            if not c % nth:
                self.progressMessage.emit(
                    u'Loading files (found ' + unicode(c) + u' items)...')
                QtWidgets.QApplication.instance().processEvents()

            # Getting the fileroot
            fileroot = filepath.replace(_parent_path, u'')
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
            if (seq and (seqpath in sfavourites or filepath in sfavourites)) or (filepath in sfavourites):
                flags = flags | common.MarkedAsFavourite

            parent_path_role = parent_path + (task, fileroot)

            # Let's limit the maximum number of items we load
            idx = len(MODEL_DATA[common.FileItem])
            if idx >= common.MAXITEMS:
                break
            MODEL_DATA[common.FileItem][idx] = common.DataDict({
                QtCore.Qt.DisplayRole: filename,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.SizeHintRole: self.row_size(),
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
                common.IdRole: idx,  # non-mutable
                #
                common.SGConfiguredRole: False,
            })

            # If the file in question is a sequence, we will also save a reference
            # to it in the sequence data dict
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
                        QtCore.Qt.SizeHintRole: self.row_size(),
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
                        common.IdRole: 0,
                        #
                        common.SGConfiguredRole: False,
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
                if filepath in sfavourites:
                    flags = flags | common.MarkedAsFavourite

                v[common.FlagsRole] = flags

            elif len(v[common.FramesRole]) == 0:
                v[common.TypeRole] = common.FileItem

            MODEL_DATA[common.SequenceItem][idx] = v
            MODEL_DATA[common.SequenceItem][idx][common.IdRole] = idx

        self.INTERNAL_MODEL_DATA[task] = MODEL_DATA

    def disable_filter(self):
        """Overrides the asset config and disables file filters."""
        return False

    def parent_path(self):
        """The model's parent folder path segments.

        Returns:
            tuple: A tuple of path segments.

        """
        return (
            settings.active(settings.ServerKey),
            settings.active(settings.JobKey),
            settings.active(settings.RootKey),
            settings.active(settings.AssetKey)
        )

    def _entry_iterator(self, path):
        """Recursive iterator for retrieving files from all subfolders.

        """
        for entry in _scandir.scandir(path):
            if entry.is_dir():
                for _entry in self._entry_iterator(entry.path):
                    yield _entry
            else:
                yield entry

    def task(self):
        """Current key to the data dictionary."""
        return settings.active(settings.TaskKey)

    @QtCore.Slot(unicode)
    def set_task(self, val):
        """Slot used to set the model's task folder.

        The current task folder is saved in the `local_settings` for future
        retrieval.

        """
        settings.set_active(settings.TaskKey, val)
        if not self.model_data():
            self.__initdata__()
            res = True
        else:
            self.sort_data()
            res = False
        return res

    @common.debug
    @common.error
    def data_type(self):
        """Current key to the data dictionary."""
        task = self.task()
        if task not in self._datatype:
            key = u'{}/{}'.format(
                self.__class__.__name__,
                task
            )
            val = self.get_local_setting(
                settings.CurrentDataType,
                key=key,
                section=settings.UIStateSection
            )
            val = common.SequenceItem if val not in (common.FileItem, common.SequenceItem) else val
            self._datatype[task] = val
        return self._datatype[task]

    @common.debug
    @common.error
    @QtCore.Slot(int)
    def set_data_type(self, val):
        """Sets the data type to `FileItem` or `SequenceItem`.

        """
        if val not in (common.FileItem, common.SequenceItem):
            raise TypeError('Wrong data type.')

        self.beginResetModel()

        try:
            task = self.task()
            if task not in self._datatype:
                self._datatype[task] = val
            if self._datatype[task] == val:
                return

            if val not in (common.FileItem, common.SequenceItem):
                s = u'Invalid value {} ({}) provided for `data_type`'.format(
                    val, type(val))
                log.error(s)
                raise ValueError(s)

            key = u'{}/{}'.format(
                self.__class__.__name__,
                self.task()
            )
            self.set_local_setting(
                settings.CurrentDataType,
                val,
                key=key,
                section=settings.UIStateSection
            )
            self._datatype[task] = val
        finally:
            self.blockSignals(True)
            self.sort_data()
            self.blockSignals(False)
            self.endResetModel()

    def local_settings_key(self):
        if settings.active(settings.TaskKey) is None:
            return None

        keys = (
            settings.JobKey,
            settings.RootKey,
            settings.AssetKey,
            settings.TaskKey,
        )
        v = [settings.active(k) for k in keys]
        if not all(v):
            return None

        return u'/'.join(v)

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


class FilesWidget(base.ThreadedBaseWidget):
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

        actions.signals.fileValueUpdated.connect(self.update_model_value)
        actions.signals.fileAdded.connect(self.select_list_item)

    def set_model(self, *args, **kwargs):
        """Extends the subclass's signal connections.

        """
        super(FilesWidget, self).set_model(*args, **kwargs)

        model = self.model().sourceModel()
        proxy = self.model()

        # Filter text
        model.modelReset.connect(
            lambda: log.debug('modelReset -> initialize_filter_values', model))
        model.modelReset.connect(proxy.initialize_filter_values)

        # Task folders
        model.taskFolderChanged.connect(
            lambda: log.debug('taskFolderChanged -> set_task', model))
        model.taskFolderChanged.connect(model.set_task)

        model.taskFolderChanged.connect(
            lambda: log.debug('taskFolderChanged -> proxy.invalidate', model))
        model.taskFolderChanged.connect(proxy.invalidate)

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

        settings.set_active(settings.FileKey, filepath)

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
        source = images.get_cached_thumbnail_path(
            index.data(common.ParentPathRole)[0],
            index.data(common.ParentPathRole)[1],
            index.data(common.ParentPathRole)[2],
            path
        )
        pixmap = images.ImageCache.get_pixmap(source, height)
        if not pixmap:
            source = images.get_placeholder_path(source)
            pixmap = images.ImageCache.get_pixmap(source, height)

        bookmark = u'/'.join(index.data(common.ParentPathRole)[0:3])
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
            lc = self.parent().parent().topbar
            lc.drop_overlay.show()
        except:
            log.error(u'Could not show drag overlay')

        drag.exec_(supported_actions)

        try:
            lc.drop_overlay.hide()
        except:
            log.error('')

        self.drag_source_index = QtCore.QModelIndex()

    def get_hint_string(self):
        model = self.model().sourceModel()
        if not model.task():
            return u'No task folder selected. Click the File tab to select one.'
        return u'{} is empty. Right-Click -> Add File to create a new file, or select another task folder.'.format(model.task().upper())

    @QtCore.Slot(unicode)
    @QtCore.Slot(int)
    @QtCore.Slot(object)
    def update_model_value(self, source, role, v):
        model = self.model().sourceModel()
        data = model.model_data()
        for idx in xrange(model.rowCount()):
            if source != common.proxy_path(data[idx][QtCore.Qt.StatusTipRole]):
                continue
            data[idx][role] = v
            self.update_row(idx)
            break

    @QtCore.Slot(unicode)
    def select_list_item(self, v, role=QtCore.Qt.DisplayRole, update=True, limit=10000):
        model = self.model().sourceModel()
        task = model.task()

        if not all(model.parent_path()):
            return
        parent_path = u'/'.join(model.parent_path())

        # We probably saved outside the asset, we won't be looking showing the
        # file...
        if parent_path not in v:
            return

        # Check if we have to change task folders
        _task = v.replace(parent_path, u'').strip(u'/').split(u'/')[0]
        if task != _task:
            update = model.set_task(_task)

        if model.data_type() != common.FileItem:
            model.set_data_type(common.FileItem)


        actions.change_tab(base.FileTab)

        model = self.model()
        if update and model.rowCount() < limit:
            model.sourceModel().modelDataResetRequested.emit()

        for n in xrange(model.rowCount()):
            index = model.index(n, 0)
            if v == index.data(QtCore.Qt.StatusTipRole):
                self.selectionModel().setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect
                )
                self.scrollTo(
                    index, QtWidgets.QAbstractItemView.PositionAtCenter)
                return
