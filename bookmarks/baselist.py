# -*- coding: utf-8 -*-
"""Core model and view widgets.

BaseModel is the core container for item data. The all data is stored
internally in :const:`.BaseModel.INTERNAL_MODEL_DATA` and is populated by
:func:`.BaseModel.__initdata__`.

Multi-threading:
    Each BaseModel instance can be initiated with threads, used to load secondary
    file information, like custom descriptions and thumbnails.
    See :mod:`.bookmarks.threads` for more information.

Data is filtered with QSortFilterProxyModels but we're not using sorting.
Sorting is implemented for performance reasons in the BaseModel directly.

The main tabs derive from the following custom QListViews:
    :class:`.BaseListWidget`: Defines core list behaviours.
    :class:`.BaseInlineIconWidget`: Adds the methods needed to respond to custom inline button events.
    :class:`.ThreadedBaseWidget`: Implements the methods needed to utilse custom worker threads.

"""
import re
import weakref
from functools import wraps, partial

from PySide2 import QtWidgets, QtGui, QtCore

import bookmarks.log as log
import bookmarks.common as common
import bookmarks.common_ui as common_ui
import bookmarks.bookmark_db as bookmark_db
from bookmarks.basecontextmenu import BaseContextMenu
import bookmarks.delegate as delegate
import bookmarks.settings as settings
import bookmarks.images as images
import bookmarks.alembicpreview as alembicpreview

import bookmarks.threads as threads


BACKGROUND_COLOR = QtGui.QColor(0, 0, 0, 50)


def validate_index(func):
    """Decorator function to ensure `QModelIndexes` passed to worker threads
    are in a valid state.
    """
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        # Checking validity
        if not args[0].isValid():
            return None
        if not args[0].data(QtCore.Qt.StatusTipRole):
            return None
        if not args[0].data(common.ParentPathRole):
            return None

        # Converting the FilterProxyModel indexes to source indexes
        if hasattr(args[0].model(), 'sourceModel'):
            args = [f for f in args]
            index = args.pop(0)
            args.insert(0, index.model().mapToSource(index))
            args = tuple(args)

        return func(*args, **kwargs)
    return func_wrapper


def initdata(func):
    """Wraps `__initdata__` calls.

    The decorator is responsible for emiting the begin- and endResetModel
    signals and sorting resulting data.

    """
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        if not self.task_folder():
            return

        try:
            self.beginResetModel()
            self.reset_model_loaded()

            self._interrupt_requested = False
            log.debug('__initdata__()', self)
            func(self, *args, **kwargs)

            self.blockSignals(True)
            self.sort_data()
            self.blockSignals(False)

            self._interrupt_requested = False
            self.endResetModel()
        except:
            log.error(u'Error loading the model data')

    return func_wrapper


def flagsmethod(func):
    """Decorator to make sure the ItemFlag return values are always correct."""
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        res = func(self, *args, **kwargs)
        if not res:
            res = QtCore.Qt.NoItemFlags
        return res
    return func_wrapper


class ThumbnailsContextMenu(BaseContextMenu):
    def __init__(self, index, parent=None):
        super(ThumbnailsContextMenu, self).__init__(index, parent=parent)
        self.add_thumbnail_menu()


class ProgressWidget(QtWidgets.QWidget):
    """Widget responsible for indicating files are being loaded."""

    def __init__(self, parent=None):
        super(ProgressWidget, self).__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setWindowFlags(QtCore.Qt.Widget)
        self._message = u'Loading...'

    def showEvent(self, event):
        self.setGeometry(self.parent().geometry())

    @QtCore.Slot(unicode)
    def set_message(self, text):
        """Sets the message to be displayed when saving the widget."""
        self._message = text

    def paintEvent(self, event):
        """Custom message painted here."""
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        color = common.SEPARATOR
        painter.setBrush(color)
        painter.drawRect(self.rect())
        painter.setOpacity(0.8)
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(common.MEDIUM_FONT_SIZE())[0],
            self.rect(),
            self._message,
            QtCore.Qt.AlignCenter,
            common.TEXT
        )
        painter.end()

    def mousePressEvent(self, event):
        """``ProgressWidgeqt`` closes on mouse press events."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.hide()


class FilterOnOverlayWidget(ProgressWidget):
    """Static overlay widget shown when there's a blocking window placed
    on top of the main widget.

    """

    def paintEvent(self, event):
        """Custom message painted here."""
        model = self.parent().model()
        if model.rowCount() == model.sourceModel().rowCount():
            return

        painter = QtGui.QPainter()
        painter.begin(self)
        rect = self.rect()
        rect.setHeight(common.ROW_SEPARATOR() * 2.0)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        painter.setOpacity(0.8)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.REMOVE)
        painter.drawRect(rect)
        rect.moveBottom(self.rect().bottom())
        painter.drawRect(rect)
        painter.end()

    def showEvent(self, event):
        self.repaint()


class FilterProxyModel(QtCore.QSortFilterProxyModel):
    """Proxy model responsible for **filtering** data for the view.

    We can filter items based on the data contained in the
    ``QtCore.Qt.StatusTipRole``, ``common.DescriptionRole`` and
    ``common.FileDetailsRole`` roles. Furthermore, based on flag values
    (``MarkedAsArchived``, ``MarkedAsActive``, ``MarkedAsFavourite`` are implemented.)

    Because of perfomarnce snags, sorting function are not implemented in the proxy
    model, rather in the source ``BaseModel``.

    Signals:
        filterFlagChanged (QtCore.Signal):  The signal emitted when the user changes a filter view setting
        filterTextChanged (QtCore.Signal):  The signal emitted when the user changes the filter text.

    """
    filterFlagChanged = QtCore.Signal(int, bool)  # FilterFlag, value
    filterTextChanged = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(FilterProxyModel, self).__init__(parent=parent)
        self.setSortLocaleAware(False)
        self.setDynamicSortFilter(False)

        self.setFilterRole(QtCore.Qt.StatusTipRole)
        self.setSortCaseSensitivity(QtCore.Qt.CaseSensitive)
        self.setFilterCaseSensitivity(QtCore.Qt.CaseSensitive)

        self.parentwidget = parent

        self._filter_text = None
        self._filterflags = {
            common.MarkedAsActive: None,
            common.MarkedAsArchived: None,
            common.MarkedAsFavourite: None,
        }

    def sort(self, column, order=QtCore.Qt.AscendingOrder):
        raise NotImplementedError(
            'Sorting on the proxy model is not implemented.')

    def initialize_filter_values(self):
        """Load the settings stored in the local_settings, or optional
        default values if the settings has not yet been saved.

        """
        model = self.sourceModel()
        task_folder = model.task_folder()
        cls = model.__class__.__name__
        self._filter_text = settings.local_settings.value(
            u'widget/{}/{}/filtertext'.format(cls, task_folder))

        self._filterflags = {
            common.MarkedAsActive: settings.local_settings.value(
                u'widget/{}/filterflag{}'.format(cls, common.MarkedAsActive)),
            common.MarkedAsArchived: settings.local_settings.value(
                u'widget/{}/filterflag{}'.format(cls, common.MarkedAsArchived)),
            common.MarkedAsFavourite: settings.local_settings.value(
                u'widget/{}/filterflag{}'.format(cls, common.MarkedAsFavourite)),
        }

        if self._filterflags[common.MarkedAsActive] is None:
            self._filterflags[common.MarkedAsActive] = False
        if self._filterflags[common.MarkedAsArchived] is None:
            self._filterflags[common.MarkedAsArchived] = False
        if self._filterflags[common.MarkedAsFavourite] is None:
            self._filterflags[common.MarkedAsFavourite] = False

        log.debug('initialize_filter_values()', self)

    def filter_text(self):
        """Filters the list of items containing this path segment."""
        return self._filter_text

    @QtCore.Slot(unicode)
    def set_filter_text(self, val):
        """Sets the path-segment to use as a filter."""
        model = self.sourceModel()
        task_folder = model.task_folder()
        cls = model.__class__.__name__
        k = u'widget/{}/{}/filtertext'.format(cls, task_folder)

        # We're in sync and there's nothing to do
        local_val = settings.local_settings.value(k)
        if val == self._filter_text == local_val:
            return

        self._filter_text = val.strip()
        settings.local_settings.setValue(k, val.strip())

    def filter_flag(self, flag):
        """Returns the current flag-filter."""
        return self._filterflags[flag]

    @QtCore.Slot(int, bool)
    def set_filter_flag(self, flag, val):
        if self._filterflags[flag] == val:
            return

        self._filterflags[flag] = val

        cls = self.sourceModel().__class__.__name__
        settings.local_settings.setValue(
            u'widget/{}/filterflag{}'.format(cls, flag), val)

    def filterAcceptsColumn(self, source_column, parent=QtCore.QModelIndex()):
        return True

    def filterAcceptsRow(self, source_row, parent=None):
        """The main method responsible for filtering rows in the proxy model.
        Most filtering happens via the user-inputted filter string."""

        data = self.sourceModel().model_data()
        if source_row not in data:
            return False
        data = data[source_row]

        flags = data[common.FlagsRole]
        archived = flags & common.MarkedAsArchived
        favourite = flags & common.MarkedAsFavourite
        active = flags & common.MarkedAsActive

        filtertext = self.filter_text()
        if filtertext:
            filtertext = filtertext.strip().lower()
            d = data[common.DescriptionRole]
            d = d.strip().lower() if d else u''
            f = data[common.FileDetailsRole]
            f = f.strip().lower() if f else ''
            searchable = data[QtCore.Qt.StatusTipRole].lower() + u'\n' + \
                d.strip().lower() + u'\n' + \
                f.strip().lower()

            if not self.filter_includes_row(filtertext, searchable):
                return False
            if self.filter_excludes_row(filtertext, searchable):
                return False

        if self.filter_flag(common.MarkedAsActive) and active:
            return True
        if self.filter_flag(common.MarkedAsActive) and not active:
            return False
        if archived and not self.filter_flag(common.MarkedAsArchived):
            return False
        if not favourite and self.filter_flag(common.MarkedAsFavourite):
            return False
        return True

    def filter_includes_row(self, filtertext, searchable):
        _filtertext = filtertext
        it = re.finditer(ur'(--[^\"\'\[\]\*\s]+)',
                         filtertext, flags=re.IGNORECASE | re.MULTILINE)
        it_quoted = re.finditer(ur'(--".*?")', filtertext,
                                flags=re.IGNORECASE | re.MULTILINE)

        for match in it:
            _filtertext = re.sub(match.group(1), u'', _filtertext)
        for match in it_quoted:
            _filtertext = re.sub(match.group(1), u'', _filtertext)

        for text in _filtertext.split():
            text = text.strip(u'"')
            if text not in searchable:
                return False
        return True

    def filter_excludes_row(self, filtertext, searchable):
        it = re.finditer(ur'--([^\"\'\[\]\*\s]+)',
                         filtertext, flags=re.IGNORECASE | re.MULTILINE)
        it_quoted = re.finditer(ur'--"(.*?)"', filtertext,
                                flags=re.IGNORECASE | re.MULTILINE)

        for match in it:
            if match.group(1).lower() in searchable:
                return True
        for match in it_quoted:
            match.group(1)
            if match.group(1).lower() in searchable:
                return True
        return False


class BaseModel(QtCore.QAbstractListModel):
    """The base model for storing bookmark, asset and file information.

    The model stores its internal data in **self.INTERNAL_MODEL_DATA**
    dictionary (a custom dict =that enables weakrefs).

    Data internally is stored per `task folder`. Each task folder keeps
    information about individual files and file sequences, like so:

    .. code-block:: python

        self.INTERNAL_MODEL_DATA = {}
        self.INTERNAL_MODEL_DATA['scene'] = common.DataDict({
            common.FileItem: common.DataDict(),
            common.SequenceItem: common.DataDict()
        })
        self.INTERNAL_MODEL_DATA['export'] = common.DataDict({
            common.FileItem: common.DataDict(),
            common.SequenceItem: common.DataDict()
        })

    `self.INTERNAL_MODEL_DATA` is exposed to the model via `self.model_data()`.
    To get the current task folder use `self.task_folder()` and
    `self.set_task_folder()``.

    Data sorting is also handled by the model, see `self.sort_data()`.

    """
    modelDataResetRequested = QtCore.Signal()  # Main signal to load model data

    activeChanged = QtCore.Signal(QtCore.QModelIndex)
    taskFolderChanged = QtCore.Signal(unicode)
    dataTypeChanged = QtCore.Signal(int)

    sortingChanged = QtCore.Signal(int, bool)  # (SortRole, SortOrder)

    progressMessage = QtCore.Signal(unicode)

    # Update signals
    updateIndex = QtCore.Signal(QtCore.QModelIndex)
    updateRow = QtCore.Signal(int)

    queueModel = QtCore.Signal(str)
    startCheckQueue = QtCore.Signal()
    stopCheckQueue = QtCore.Signal()

    queue_type = None
    thumbnail_queue_type = None

    def __init__(self, has_threads=True, parent=None):
        super(BaseModel, self).__init__(parent=parent)
        self.view = parent
        self._has_threads = has_threads

        self.INTERNAL_MODEL_DATA = common.DataDict()
        """Custom data type for weakref compatibility """

        self.threads = common.DataDict({
            common.InfoThread: [],  # Threads for getting file-size, description
            common.ThumbnailThread: [],  # Thread for generating thumbnails
        })

        self._model_loaded = {
            common.FileItem: False,
            common.SequenceItem: False,
        }
        self._interrupt_requested = False
        self._generate_thumbnails_enabled = True
        self._task_folder = None
        self._datatype = {}
        self._sortrole = None
        self._sortorder = None

        @QtCore.Slot(bool)
        @QtCore.Slot(int)
        def set_sorting(role, order):
            self.set_sort_role(role)
            self.set_sort_order(order)
            self.sort_data()

        self.sortingChanged.connect(
            lambda: log.debug('sortingChanged -> set_sorting', self))
        self.sortingChanged.connect(set_sorting)

        self.initialize_default_sort_values()
        self.init_generate_thumbnails_enabled()
        self.initialise_threads()

    def supportedDropActions(self):
        return QtCore.Qt.CopyAction

    def canDropMimeData(self, data, action, row, column, parent=QtCore.QModelIndex()):
        if not self.supportedDropActions() & action:
            return False
        if row == -1:
            return False

        if not data.hasUrls():
            return False
        else:
            source = data.urls()[0].toLocalFile()
            if not images.oiio_get_buf(source):
                return False

        data = self.model_data()
        if row not in data:
            return False
        if data[row][common.FlagsRole] & common.MarkedAsArchived:
            return False
        return True

    def dropMimeData(self, data, action, row, column, parent=QtCore.QModelIndex()):
        source = data.urls()[0].toLocalFile()
        if not images.oiio_get_buf(source):
            return False
        images.set_from_source(
            self.index(row, 0),
            source
        )
        return True

    def initialize_default_sort_values(self):
        """Loads the saved sorting values from the local preferences.

        """
        log.debug('initialize_default_sort_values()', self)

        cls = self.__class__.__name__
        k = u'widget/{}/sortrole'.format(cls)
        val = settings.local_settings.value(k)
        if val not in (common.SortByNameRole, common.SortBySizeRole, common.SortByLastModifiedRole):
            val = common.SortByNameRole
        self._sortrole = val

        k = u'widget/{}/sortorder'.format(cls)
        val = settings.local_settings.value(k)
        if val not in (True, False):
            val = False
        self._sortorder = val

        if self._sortrole is None:
            self._sortrole = common.SortByNameRole

        if self._sortorder is None:
            self._sortorder = False

    def sort_role(self):
        """The item role used to sort the model data, eg. `common.SortByNameRole`"""
        return self._sortrole

    @QtCore.Slot(int)
    def set_sort_role(self, val):
        """Sets and saves the sort-key."""
        log.debug('set_sort_role({})'.format(val), self)

        if val == self.sort_role():
            return

        self._sortrole = val
        cls = self.__class__.__name__
        settings.local_settings.setValue(
            u'widget/{}/sortrole'.format(cls), val)

    def sort_order(self):
        """The currently set order of the items eg. 'descending'."""
        return self._sortorder

    @QtCore.Slot(int)
    def set_sort_order(self, val):
        """Sets and saves the sort-key."""
        log.debug('set_sort_order({})'.format(val), self)

        if val == self.sort_order():
            return

        self._sortorder = val
        cls = self.__class__.__name__
        settings.local_settings.setValue(
            u'widget/{}/sortorder'.format(cls), val)

    @QtCore.Slot()
    def sort_data(self):
        """Sorts the internal `INTERNAL_MODEL_DATA` by the current
        `sort_role` and `sort_order`.

        The data sorting is wrapped in a begin- & endResetModel sequence.

        """
        log.debug(u'sort_data()', self)

        self.beginResetModel()

        k = self.task_folder()
        t = self.data_type()

        data = self.model_data()
        if not data:
            return

        sortorder = self.sort_order()
        sortrole = self.sort_role()
        k = self.task_folder()
        t = self.data_type()

        if sortrole not in (
            common.SortByNameRole,
            common.SortBySizeRole,
            common.SortByLastModifiedRole
        ):
            sortrole = common.SortByNameRole

        sorted_idxs = sorted(
            data,
            key=lambda i: data[i][sortrole],
            reverse=sortorder
        )

        d = common.DataDict()
        for n, idx in enumerate(sorted_idxs):
            if data[idx][common.IdRole] != n:
                data[idx][common.IdRole] = n
            d[n] = data[idx]

        self.INTERNAL_MODEL_DATA[k][t] = d

        self.endResetModel()

    def __resetdata__(self):
        """Resets the internal data."""
        log.debug('__resetdata__()', self)

        self.INTERNAL_MODEL_DATA = common.DataDict()
        self.__initdata__()

    @QtCore.Slot()
    def set_interrupt_requested(self):
        self._interrupt_requested = True

    @initdata
    def __initdata__(self):
        raise NotImplementedError(
            u'__initdata__ is abstract and must be overriden')

    @QtCore.Slot(QtCore.QThread)
    def thread_started(self, thread, allow_model=False):
        """Slot connected in initialise_threads().
        Signals the model an item has been updated.

        """
        log.debug(u'thread_started()', self)

        cnx = QtCore.Qt.QueuedConnection

        # thread.updateRow.connect(
        #     lambda: log.debug('updateRow -> updateRow', thread))
        thread.updateRow.connect(
            self.updateRow, cnx)

        # queueModel requests a full model data load
        if allow_model:
            self.queueModel.connect(
                lambda: log.debug('queueModel -> worker.queueModel', self))
            self.queueModel.connect(
                thread.queueModel, cnx)

        self.startCheckQueue.connect(
            lambda: log.debug('startCheckQueue -> worker.startCheckQueue', self))
        self.startCheckQueue.connect(
            thread.startCheckQueue, cnx)
        self.stopCheckQueue.connect(
            lambda: log.debug('stopCheckQueue -> worker.stopCheckQueue', self))
        self.stopCheckQueue.connect(
            thread.stopCheckQueue, cnx)

        thread.modelLoaded.connect(self.model_loaded, cnx)

        self.taskFolderChanged.connect(thread.resetQueue, cnx)
        thread.startCheckQueue.emit()

    @QtCore.Slot()
    def reset_model_loaded(self):
        self._model_loaded = {
            common.FileItem: False,
            common.SequenceItem: False,
        }

    @QtCore.Slot(int)
    def set_model_loaded(self, data_type):
        """Mark the model data type loaded.

        """
        self._model_loaded[data_type] = True

    @QtCore.Slot(int)
    def model_loaded(self, data_type):
        """Called when a thread is done loading a data type.

        If proper sorting needs information just loaded by the thread, we will
        re-sort. This will also invalidate the proxy so archived items hopefully
        won't be visible.

        """
        log.debug(u'model_loaded()', self)
        self.set_model_loaded(data_type)
        # The the loaded data is for the current file type we don't have to
        # do anything
        if self.data_type() != data_type:
            return
        if self.sort_order() or self.sort_role() != common.SortByNameRole:
            self.sort_data()

    def initialise_threads(self):
        """Starts and connects the threads."""
        if self.queue_type is None:
            raise RuntimeError(u'`queue_type` cannot be `None`')

        if not self._has_threads:
            return

        log.debug('initialise_threads()', self)

        info_worker = threads.InfoWorker(self.queue_type)
        info_thread = threads.BaseThread(info_worker)
        info_thread.started.connect(
            partial(self.thread_started, info_thread, allow_model=True),
            QtCore.Qt.DirectConnection
        )
        self.threads[common.InfoThread].append(info_thread)

        thumbnails_worker = threads.ThumbnailWorker(self.thumbnail_queue_type)
        thumbnails_thread = threads.BaseThread(thumbnails_worker)
        thumbnails_thread.started.connect(
            partial(self.thread_started, thumbnails_thread, allow_model=False),
            QtCore.Qt.DirectConnection
        )
        self.threads[common.ThumbnailThread].append(thumbnails_thread)

        info_thread.start()
        thumbnails_thread.start()

    def init_generate_thumbnails_enabled(self):
        log.debug('init_generate_thumbnails_enabled()', self)

        cls = self.__class__.__name__
        k = u'widget/{}/generate_thumbnails'.format(cls)
        v = settings.local_settings.value(k)
        v = True if v is None else v
        self._generate_thumbnails_enabled = v

    def generate_thumbnails_enabled(self):
        return self._generate_thumbnails_enabled

    @QtCore.Slot(bool)
    def set_generate_thumbnails_enabled(self, val):
        cls = self.__class__.__name__
        k = u'widget/{}/generate_thumbnails'.format(cls)
        settings.local_settings.setValue(k, val)
        self._generate_thumbnails_enabled = val

    @QtCore.Slot()
    def reset_worker_queues(self, all=False):
        """Request all queued items to be removed from the thread/worker's
        queue.

        """
        if not self._has_threads:
            return

        log.debug('reset_worker_queues()', self)

        for k in self.threads:
            for thread in self.threads[k]:
                thread.resetQueue.emit()

    def model_data(self):
        """A pointer to the model's currently set internal data."""
        k = self.task_folder()
        t = self.data_type()

        if not k in self.INTERNAL_MODEL_DATA:
            self.INTERNAL_MODEL_DATA[k] = common.DataDict({
                common.FileItem: common.DataDict(),
                common.SequenceItem: common.DataDict()
            })
        return self.INTERNAL_MODEL_DATA[k][t]

    def active_index(self):
        """The model's active_index."""
        for n in xrange(self.rowCount()):
            index = self.index(n, 0)
            if index.flags() & common.MarkedAsActive:
                return index
        return QtCore.QModelIndex()

    def columnCount(self, parent=QtCore.QModelIndex()):
        """The number of columns of the model."""
        return 1

    def rowCount(self, parent=QtCore.QModelIndex()):
        """The number of rows in the model."""
        return len(list(self.model_data()))

    def index(self, row, column, parent=QtCore.QModelIndex()):
        """Bog-standard index creator."""
        return self.createIndex(row, 0, parent=parent)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """Custom data-getter."""
        if not index.isValid():
            return None
        data = self.model_data()
        if index.row() not in data:
            return None
        if role in data[index.row()]:
            return data[index.row()][role]

    @flagsmethod
    def flags(self, index):
        return self.data(index, role=common.FlagsRole)

    def parent(self, child):
        return QtCore.QModelIndex()

    def setData(self, index, data, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return False
        if index.row() not in self.model_data():
            return False
        self.model_data()[index.row()][role] = data
        self.dataChanged.emit(index, index)
        return True

    def task_folder(self):
        """Current key to the data dictionary."""
        return u'.'

    def data_type(self):
        """Current key to the data dictionary."""
        return common.FileItem

    @QtCore.Slot(int)
    def set_data_type(self, val):
        """Sets the data type to `FileItem` or `SequenceItem`."""
        log.debug('set_data_type({})>'.format(val), self)

        self.beginResetModel()

        try:
            task_folder = self.task_folder()
            if task_folder not in self._datatype:
                self._datatype[task_folder] = val
            if self._datatype[task_folder] == val:
                return

            if val not in (common.FileItem, common.SequenceItem):
                s = u'Invalid value {} ({}) provided for `data_type`'.format(
                    val, type(val))
                log.error(s)
                raise ValueError(s)

            cls = self.__class__.__name__
            key = u'widget/{}/{}/datatype'.format(cls, self.task_folder())
            settings.local_settings.setValue(key, val)
            self._datatype[task_folder] = val
        except Exception as e:
            s = u'Error setting task folder'
            log.error(s)
            common_ui.ErrorBox(
                u'Error setting task folder',
                u'{}'.format(e),
            ).open()
        finally:
            self.blockSignals(True)
            self.sort_data()
            self.blockSignals(False)

            self.endResetModel()

    @QtCore.Slot(unicode)
    def set_task_folder(self, val):
        """Settings task folders for asset and bookmarks is not available."""
        pass


class BaseListWidget(QtWidgets.QListView):
    """Defines the base of the primary list widgets."""

    customContextMenuRequested = QtCore.Signal(
        QtCore.QModelIndex, QtCore.QObject)
    favouritesChanged = QtCore.Signal()
    interruptRequested = QtCore.Signal()

    resized = QtCore.Signal(QtCore.QRect)
    SourceModel = NotImplementedError

    Delegate = NotImplementedError
    ContextMenu = NotImplementedError

    def __init__(self, parent=None):
        super(BaseListWidget, self).__init__(parent=parent)
        self.setDragDropOverwriteMode(False)
        # self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)

        self._layout_timer = QtCore.QTimer(parent=self)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.setInterval(300)
        self._layout_timer.timeout.connect(self.scheduleDelayedItemsLayout)
        self._layout_timer.timeout.connect(self.repaint_visible_rows)

        self.validate_visible_timer = QtCore.QTimer(parent=self)
        self.validate_visible_timer.setSingleShot(False)
        self.validate_visible_timer.setInterval(250)
        self.validate_visible_timer.timeout.connect(self.validate_visible)

        self._thumbnail_drop = (-1, False)  # row, accepted
        self._background_icon = u'icon_bw'
        self._generate_thumbnails_enabled = True
        self.progress_widget = ProgressWidget(parent=self)
        self.progress_widget.setHidden(True)
        self.filter_active_widget = FilterOnOverlayWidget(parent=self)
        self.filter_editor = common_ui.FilterEditor(parent=self)
        self.filter_editor.setHidden(True)

        self.description_editor_widget = common_ui.DescriptionEditorWidget(
            parent=self)
        self.description_editor_widget.setHidden(True)

        k = u'widget/{}/buttons_hidden'.format(self.__class__.__name__)
        self._buttons_hidden = False if settings.local_settings.value(
            k) is None else settings.local_settings.value(k)

        # Keyboard search timer and placeholder string.
        self.timer = QtCore.QTimer(parent=self)
        self.timer.setInterval(
            QtWidgets.QApplication.instance().keyboardInputInterval())
        self.timer.setSingleShot(True)
        self.timed_search_string = u''

        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setUniformItemSizes(True)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self.setWordWrap(False)
        self.setLayoutMode(QtWidgets.QListView.Batched)
        self.setBatchSize(100)

        self.installEventFilter(self)

        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        self.set_model(self.SourceModel(parent=self))
        self.setItemDelegate(self.Delegate(parent=self))

        self.resized.connect(self.filter_active_widget.setGeometry)
        self.resized.connect(self.progress_widget.setGeometry)
        self.resized.connect(self.filter_editor.setGeometry)

    def buttons_hidden(self):
        """Returns the visibility of the inline icon buttons."""
        if self.width() < common.WIDTH() * 0.66:
            return True
        return self._buttons_hidden

    def set_buttons_hidden(self, val):
        """Sets the visibility of the inline icon buttons."""
        cls = self.__class__.__name__
        k = u'widget/{}/buttons_hidden'.format(cls)
        settings.local_settings.setValue(k, val)
        self._buttons_hidden = val

    def set_model(self, model):
        """This is the main port of entry for the model.

        The BaseModel subclasses are wrapped in a QSortFilterProxyModel. All
        the necessary internal signal-slot connections needed for the proxy, model
        and the view comminicate properly are made here.

        Note:
            The bulk of the signal are connected together in ``MainWidget``'s
            *_connect_signals* method.

        """
        proxy = FilterProxyModel(parent=self)

        self.blockSignals(True)
        proxy.blockSignals(True)

        proxy.setSourceModel(model)
        self.setModel(proxy)
        proxy.initialize_filter_values()

        proxy.blockSignals(False)
        self.blockSignals(False)

        self.interruptRequested.connect(model.set_interrupt_requested)

        model.modelAboutToBeReset.connect(
            lambda: log.debug('<<< modelAboutToBeReset >>>', model))
        model.modelReset.connect(
            lambda: log.debug('<<< modelReset >>>', model))

        model.modelDataResetRequested.connect(
            lambda: log.debug('modelDataResetRequested -> __resetdata__', model))
        model.modelDataResetRequested.connect(model.__resetdata__)

        model.activeChanged.connect(
            lambda: log.debug('activeChanged -> save_activated', model))
        model.activeChanged.connect(self.save_activated)

        # Data key, eg. 'scenes'
        model.taskFolderChanged.connect(
            lambda: log.debug('taskFolderChanged -> set_task_folder', model))
        model.taskFolderChanged.connect(model.set_task_folder)

        model.taskFolderChanged.connect(
            lambda: log.debug('taskFolderChanged -> proxy.invalidate', model))
        model.taskFolderChanged.connect(proxy.invalidate)

        # FileItem/SequenceItem
        model.dataTypeChanged.connect(
            lambda: log.debug('dataTypeChanged -> proxy.invalidate', model))
        model.dataTypeChanged.connect(proxy.invalidate)

        model.dataTypeChanged.connect(
            lambda: log.debug('dataTypeChanged -> set_data_type', model))
        model.dataTypeChanged.connect(model.set_data_type)

        proxy.filterTextChanged.connect(
            lambda: log.debug('filterTextChanged -> set_filter_text', proxy))
        proxy.filterTextChanged.connect(proxy.set_filter_text)

        proxy.filterFlagChanged.connect(
            lambda: log.debug('filterFlagChanged -> set_filter_flag', proxy))
        proxy.filterFlagChanged.connect(proxy.set_filter_flag)

        proxy.filterTextChanged.connect(
            lambda: log.debug('filterTextChanged -> invalidateFilter', proxy))
        proxy.filterTextChanged.connect(proxy.invalidateFilter)

        proxy.filterFlagChanged.connect(
            lambda: log.debug('filterFlagChanged -> invalidateFilter', proxy))
        proxy.filterFlagChanged.connect(proxy.invalidateFilter)

        model.modelAboutToBeReset.connect(
            lambda: log.debug('modelAboutToBeReset -> reset_multitoggle', model))
        model.modelAboutToBeReset.connect(self.reset_multitoggle)

        self.filter_editor.finished.connect(
            lambda: log.debug('finished -> filterTextChanged', self.filter_editor))
        self.filter_editor.finished.connect(proxy.filterTextChanged)

        model.updateIndex.connect(
            lambda: log.debug('updateIndex -> update', model))
        model.updateIndex.connect(
            self.update, type=QtCore.Qt.DirectConnection)

        model.modelReset.connect(
            lambda: log.debug('modelReset -> reselect_previous', model))
        model.modelReset.connect(self.reselect_previous)

        # model.updateRow.connect(
        #     lambda: log.debug('updateRow -> update_row', model))
        model.updateRow.connect(
            self.update_row, type=QtCore.Qt.QueuedConnection)

    @QtCore.Slot(QtCore.QModelIndex)
    def update(self, index):
        """This slot is used by all threads to repaint/update the given index
        after it's thumbnail or file information has been loaded.

        The actualy repaint will only occure if the index is visible
        in the view currently.

        """
        if not index.isValid():
            return
        if not hasattr(index.model(), u'sourceModel'):
            index = self.model().mapFromSource(index)
        super(BaseListWidget, self).update(index)

    @QtCore.Slot(int)
    def update_row(self, idx):
        """Slot used to update the row associated with the data segment."""
        if not self.isVisible():
            return
        if not isinstance(idx, int):
            return
        index = self.model().sourceModel().index(idx, 0)
        self.model().mapFromSource(index)
        # super(BaseListWidget, self).update(index)
        self.update(index)

    @QtCore.Slot()
    def validate_visible(self):
        """Checks the visible items and makes sure that no filtered items
        creep in.

        """
        def _next(rect):
            rect.moveTop(rect.top() + rect.height())
            return self.indexAt(rect.topLeft())

        proxy = self.model()
        if not proxy.rowCount():
            return

        viewport_rect = self.viewport().rect()
        index = self.indexAt(viewport_rect.topLeft())
        if not index.isValid():
            return

        index_rect = self.visualRect(index)
        show_archived = proxy.filter_flag(common.MarkedAsArchived)

        while viewport_rect.intersects(index_rect):
            is_archived = index.flags() & common.MarkedAsArchived
            if show_archived is False and is_archived:
                proxy.invalidateFilter()
                return
            index = _next(index_rect)
            if not index.isValid():
                break

    @QtCore.Slot()
    def queue_visible_indexes(self, *args, **kwargs):
        pass

    def activate(self, index):
        """Marks the given index by adding the ``MarkedAsActive`` flag.

        If the item has already been activated it will emit the activated signal.
        This is used to switch tabs. If the item is not active yet, it will
        apply the active flag and emit the ``activeChanged`` signal.

        Note:
            The method emits the ``activeChanged`` signal but itself does not
            save the change to the settings.local_settings. That is handled by connections
            to the signal.

        """
        if not index.isValid():
            return
        if index.flags() == QtCore.Qt.NoItemFlags:
            return
        if index.flags() & common.MarkedAsArchived:
            return

        self.activated.emit(index)
        if index.flags() & common.MarkedAsActive:
            return

        if isinstance(index.model(), FilterProxyModel):
            source_index = index.model().mapToSource(index)
        else:
            source_index = index

        self.deactivate(self.model().sourceModel().active_index())

        data = source_index.model().model_data()
        idx = source_index.row()

        data[idx][common.FlagsRole] = data[idx][common.FlagsRole] | common.MarkedAsActive

        self.update(index)

        source_index.model().activeChanged.emit(source_index)

    def deactivate(self, index):
        """Unsets the active flag."""
        if not index.isValid():
            return

        if isinstance(index.model(), FilterProxyModel):
            source_index = index.model().mapToSource(index)
        else:
            source_index = index

        data = source_index.model().model_data()
        idx = source_index.row()

        data[idx][common.FlagsRole] = data[idx][common.FlagsRole] & ~common.MarkedAsActive

        self.update(index)

    @QtCore.Slot(QtCore.QModelIndex)
    def save_activated(self, index):
        """`save_activated` is abstract and has to be implemented in the subclass."""
        pass

    @QtCore.Slot()
    def save_selection(self):
        """Saves the current selection."""
        if not self.selectionModel().hasSelection():
            return
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return
        if not index.data(QtCore.Qt.StatusTipRole):
            return

        model = self.model().sourceModel()
        data_type = model.data_type()
        cls = self.__class__.__name__
        file_k = u'widget/{}/{}/selected_fileitem'.format(
            cls, model.task_folder())
        seq_k = u'widget/{}/{}/selected_sequenceitem'.format(
            cls, model.task_folder())
        path = index.data(QtCore.Qt.StatusTipRole)

        if data_type == common.FileItem:
            settings.local_settings.setValue(file_k, path)
            settings.local_settings.setValue(seq_k, common.proxy_path(path))

        if data_type == common.SequenceItem:
            if not path:
                return
            path = common.get_sequence_startpath(path)
            settings.local_settings.setValue(
                file_k, path)
            settings.local_settings.setValue(seq_k, common.proxy_path(path))

    @QtCore.Slot()
    def reselect_previous(self):
        """Slot called to reselect the previously selected item."""
        proxy = self.model()
        if not proxy.rowCount():
            return

        model = proxy.sourceModel()
        data_type = model.data_type()
        cls = self.__class__.__name__
        if data_type == common.FileItem:
            k = u'widget/{}/{}/selected_fileitem'.format(
                cls, model.task_folder())
        if data_type == common.SequenceItem:
            k = u'widget/{}/{}/selected_sequenceitem'.format(
            cls, model.task_folder())

        previous = settings.local_settings.value(k)
        if previous:
            for n in xrange(proxy.rowCount()):
                index = proxy.index(n, 0)
                if data_type == common.SequenceItem:
                    current = common.proxy_path(index.data(QtCore.Qt.StatusTipRole))
                else:
                    current = index.data(QtCore.Qt.StatusTipRole)
                if current == previous:
                    self.selectionModel().setCurrentIndex(
                        index, QtCore.QItemSelectionModel.ClearAndSelect)
                    self.scrollTo(
                        index, QtWidgets.QAbstractItemView.PositionAtCenter)
                    return

        index = proxy.sourceModel().active_index()
        if index.isValid():
            self.selectionModel().setCurrentIndex(
                index, QtCore.QItemSelectionModel.ClearAndSelect)
            self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
            return

        index = proxy.index(0, 0)
        self.selectionModel().setCurrentIndex(
            index, QtCore.QItemSelectionModel.ClearAndSelect)
        self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)

    def toggle_item_flag(self, index, flag, state=None):
        """Sets the index's `flag` value based on `state`.

        We're using the method to mark items archived, or favourite and save the
        changes to the database or the local config file.

        Args:
            index (QModelIndex): The index containing the
            flag (type): Description of parameter `flag`.
            state (type): Description of parameter `state`. Defaults to None.

        Returns:
            unicode: The key used to find and match items.

        """
        def dummy_func(mode, data, flag):
            """Does nothing."""
            pass

        def save_to_db(k, mode, flag):
            """Save the value to the database."""
            db = bookmark_db.get_db(
                index.data(common.ParentPathRole)[0],
                index.data(common.ParentPathRole)[1],
                index.data(common.ParentPathRole)[2],
            )
            with db.transactions():
                f = db.value(k, u'flags')
                f = 0 if f is None else f
                f = f | flag if mode else f & ~flag
                db.setValue(k, u'flags', f)

        def save_to_local_settings(k, mode, flag):
            favourites = settings.local_settings.favourites()
            sfavourites = set(favourites)
            if mode:
                favourites.append(k.strip().lower())
            else:
                if k.lower() in sfavourites:
                    favourites.remove(k.strip().lower())

            v = sorted(list(set(favourites)))
            settings.local_settings.setValue(u'favourites', v)

        def save_active(k, mode, flag):
            pass

        if flag == common.MarkedAsArchived:
            save_func = save_to_db
        elif flag == common.MarkedAsFavourite:
            save_func = save_to_local_settings
        elif flag == common.MarkedAsActive:
            save_func = save_active
        else:
            save_func = dummy_func

        def _set_flag(k, mode, data, flag, commit=False):
            """Sets a single flag value based on the given mode."""
            if mode:
                data[common.FlagsRole] = data[common.FlagsRole] | flag
            else:
                data[common.FlagsRole] = data[common.FlagsRole] & ~flag
            if commit:
                save_func(k, mode, flag)

        def _set_flags(DATA, k, mode, flag, commit=False, proxy=False):
            """Sets flags for multiple items."""
            for item in DATA.itervalues():
                if proxy:
                    _k = common.proxy_path(item[QtCore.Qt.StatusTipRole])
                else:
                    _k = item[QtCore.Qt.StatusTipRole]
                if k == _k:
                    _set_flag(_k, mode, item, flag, commit=commit)

        def can_toggle_flag(k, mode, data, flag):
            seq = common.get_sequence(k)
            if not seq:
                return True
            proxy_k = common.proxy_path(k)
            if flag == common.MarkedAsActive:
                pass
            elif flag == common.MarkedAsArchived:
                db = bookmark_db.get_db(
                    index.data(common.ParentPathRole)[0],
                    index.data(common.ParentPathRole)[1],
                    index.data(common.ParentPathRole)[2],
                )
                flags = db.value(proxy_k, u'flags')
                if not flags:
                    return True
                if flags & common.MarkedAsArchived:
                    return False
                return True
            elif flag == common.MarkedAsFavourite:
                favourites = settings.local_settings.favourites()
                sfavourites = set(favourites)
                if proxy_k.lower() in sfavourites:
                    return False
                return True
            return False

        if not index.isValid():
            return None

        if hasattr(index.model(), 'sourceModel'):
            source_index = self.model().mapToSource(index)

        if not index.data(common.FileInfoLoaded):
            return None

        model = self.model().sourceModel()
        task_folder = model.task_folder()
        data = model.model_data()[source_index.row()]

        FILE_DATA = model.INTERNAL_MODEL_DATA[task_folder][common.FileItem]
        SEQ_DATA = model.INTERNAL_MODEL_DATA[task_folder][common.SequenceItem]

        applied = data[common.FlagsRole] & flag
        collapsed = common.is_collapsed(data[QtCore.Qt.StatusTipRole])

        # Determine the mode of operation
        if state is None and applied:
            mode = False
        elif state is None and not applied:
            mode = True
        elif state is not None:
            mode = state

        if collapsed:
            k = common.proxy_path(data[QtCore.Qt.StatusTipRole])
            _set_flag(k, mode, data, flag, commit=True)
            if self.model().sourceModel().model_data() == FILE_DATA:
                _set_flags(SEQ_DATA, k, mode, flag, commit=False, proxy=True)
            else:
                _set_flags(FILE_DATA, k, mode, flag, commit=False, proxy=True)
        else:
            k = data[QtCore.Qt.StatusTipRole]
            if not can_toggle_flag(k, mode, data, flag):
                common_ui.MessageBox(
                    u'Oops. It looks like this item belongs to a sequence that has a flag set already.',
                    u'To modify individual sequence items, remove the flag from the sequence first and try again.'
                ).open()
                self.reset_multitoggle()
                return
            _set_flag(k, mode, data, flag, commit=True)
            if self.model().sourceModel().model_data() == FILE_DATA:
                _set_flags(SEQ_DATA, k, mode, flag, commit=True, proxy=False)
            else:
                _set_flags(FILE_DATA, k, mode, flag, commit=True, proxy=False)

        self.repaint()
        return k

    def key_space(self):
        self.show_item_preview()

    def show_item_preview(self):
        """Display a preview of the currently selected item.

        For alembic archives, this is the hierarchy of the archive file. For
        image files we'll try to load and display the image itself, and
        for any other case we will fall back to cached or default thumbnail
        images.

        """
        if not self.selectionModel().hasSelection():
            return
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        source = index.data(QtCore.Qt.StatusTipRole)
        source = common.get_sequence_startpath(source)
        ext = source.split(u'.').pop()

        if ext.lower() == u'abc':
            widget = alembicpreview.AlembicView(source)
            self.selectionModel().currentChanged.connect(widget.close)
            self.selectionModel().currentChanged.connect(widget.deleteLater)
            widget.show()
            return

        # Let's try to open the image outright
        # If this fails, we will try and look for a saved thumbnail image,
        # and if that fails too, we will display a general thumbnail.

        # Not a readable image file...
        if not images.oiio_get_buf(source):
            # ...let's look for the thumbnail
            source = images.get_thumbnail_path(
                index.data(common.ParentPathRole)[0],
                index.data(common.ParentPathRole)[1],
                index.data(common.ParentPathRole)[2],
                index.data(QtCore.Qt.StatusTipRole)
            )
            if not images.oiio_get_buf(source):
                # If that fails, we'll display a general placeholder image
                source = images.get_placeholder_path(
                    index.data(QtCore.Qt.StatusTipRole))
                buf = images.oiio_get_buf(source, force=True)
                if not buf:
                    s = u'{} seems invalid.'.format(source)
                    common_ui.ErrorBox(
                        u'Error previewing image.', s).open()
                    log.error(s)
                    raise RuntimeError(s)

        if not source:
            s = u'Invalid source value'
            log.error(s)
            raise RuntimeError(s)

        # Finally, we'll create and show our widget, and destroy it when the
        # selection changes
        widget = images.ImageViewer(source, parent=self)
        self.selectionModel().currentChanged.connect(widget.delete_timer.start)
        widget.open()

    def key_down(self):
        """Custom action on  `down` arrow key-press.

        We're implementing a continous 'scroll' function: reaching the last
        item in the list will automatically jump to the beginning to the list
        and vice-versa.

        """
        sel = self.selectionModel()
        current_index = sel.currentIndex()
        first_index = self.model().index(0, 0)
        last_index = self.model().index(
            self.model().rowCount() - 1, 0)

        if first_index == last_index:
            return
        if not current_index.isValid():  # No selection
            sel.setCurrentIndex(
                first_index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            return

        if current_index == last_index:  # Last item is selected
            sel.setCurrentIndex(
                first_index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            return

        sel.setCurrentIndex(
            self.model().index(current_index.row() + 1, 0),
            QtCore.QItemSelectionModel.ClearAndSelect
        )

    def key_up(self):
        """Custom action to perform when the `up` arrow is pressed
        on the keyboard.

        We're implementing a continous 'scroll' function: reaching the last
        item in the list will automatically jump to the beginning to the list
        and vice-versa.

        """
        sel = self.selectionModel()
        current_index = sel.currentIndex()
        first_index = self.model().index(0, 0)
        last_index = self.model().index(self.model().rowCount() - 1, 0)

        if first_index == last_index:
            return

        if not current_index.isValid():  # No selection
            sel.setCurrentIndex(
                last_index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            return
        if current_index == first_index:  # First item is selected
            sel.setCurrentIndex(
                last_index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            return

        sel.setCurrentIndex(
            self.model().index(current_index.row() - 1, 0),
            QtCore.QItemSelectionModel.ClearAndSelect
        )

    def key_tab(self):
        """Custom `tab` key action."""
        self.description_editor_widget.show()

    def keyPressEvent(self, event):
        """Customized key actions.

        We're defining the default behaviour of the list-items here, including
        defining the actions needed to navigate the list using keyboard presses.

        """
        numpad_modifier = event.modifiers() & QtCore.Qt.KeypadModifier
        no_modifier = event.modifiers() == QtCore.Qt.NoModifier
        index = self.selectionModel().currentIndex()

        if no_modifier:
            if event.key() == QtCore.Qt.Key_Escape:
                self.interruptRequested.emit()
                return

        if no_modifier or numpad_modifier:
            if event.key() == QtCore.Qt.Key_Space:
                self.key_space()
                return
            if event.key() == QtCore.Qt.Key_Escape:
                self.selectionModel().setCurrentIndex(
                    QtCore.QModelIndex(), QtCore.QItemSelectionModel.ClearAndSelect)
                return
            elif event.key() == QtCore.Qt.Key_Down:
                self.key_down()
                self.save_selection()
                self.start_queue_timers()
                return
            elif event.key() == QtCore.Qt.Key_Up:
                self.key_up()
                self.save_selection()
                self.start_queue_timers()
                return
            elif (event.key() == QtCore.Qt.Key_Return) or (event.key() == QtCore.Qt.Key_Enter):
                self.action_on_enter_key()
                self.save_selection()
                return
            elif event.key() == QtCore.Qt.Key_Tab:
                if not self.description_editor_widget.isVisible():
                    self.key_tab()
                    self.save_selection()
                    return
                else:
                    self.key_down()
                    self.key_tab()
                    self.save_selection()
                    self.start_queue_timers()
                    return
            elif event.key() == QtCore.Qt.Key_Backtab:
                if not self.description_editor_widget.isVisible():
                    self.key_tab()
                    self.save_selection()
                    return
                else:
                    self.key_up()
                    self.key_tab()
                    self.save_selection()
                    self.start_queue_timers()
                    return
            elif event.key() == QtCore.Qt.Key_PageDown:
                super(BaseListWidget, self).keyPressEvent(event)
                self.save_selection()
                self.start_queue_timers()
                return
            elif event.key() == QtCore.Qt.Key_PageUp:
                super(BaseListWidget, self).keyPressEvent(event)
                self.save_selection()
                self.start_queue_timers()
                return
            elif event.key() == QtCore.Qt.Key_Home:
                super(BaseListWidget, self).keyPressEvent(event)
                self.save_selection()
                self.start_queue_timers()
                return
            elif event.key() == QtCore.Qt.Key_End:
                super(BaseListWidget, self).keyPressEvent(event)
                self.save_selection()
                self.start_queue_timers()
                return
            else:  # keyboard search and select
                if not self.timer.isActive():
                    self.timed_search_string = u''
                    self.timer.start()

                self.timed_search_string += event.text()
                self.timer.start()  # restarting timer on input

                sel = self.selectionModel()
                for n in xrange(self.model().rowCount()):
                    index = self.model().index(n, 0, parent=QtCore.QModelIndex())
                    # When only one key is pressed we want to cycle through
                    # only items starting with that letter:
                    if len(self.timed_search_string) == 1:
                        if n <= sel.currentIndex().row():
                            continue

                        if index.data(QtCore.Qt.DisplayRole)[0].lower() == self.timed_search_string.lower():
                            sel.setCurrentIndex(
                                index,
                                QtCore.QItemSelectionModel.ClearAndSelect
                            )
                            self.save_selection()
                            break
                    else:
                        try:
                            match = re.search(
                                self.timed_search_string,
                                index.data(QtCore.Qt.DisplayRole),
                                flags=re.IGNORECASE
                            )
                        except:
                            match = None

                        if match:
                            sel.setCurrentIndex(
                                index,
                                QtCore.QItemSelectionModel.ClearAndSelect
                            )
                            self.save_selection()
                            return

        if event.modifiers() & QtCore.Qt.ControlModifier:
            if event.key() == QtCore.Qt.Key_C:
                if index.data(common.FileInfoLoaded):
                    if common.get_platform() == u'mac':
                        mode = common.MacOSPath
                    elif common.get_platform() == u'win':
                        mode = common.WindowsPath
                    else:
                        mode = common.UnixPath
                    path = index.data(QtCore.Qt.StatusTipRole)
                    if event.modifiers() & QtCore.Qt.ShiftModifier:
                        return common.copy_path(path, mode=common.UnixPath, first=True)
                    return common.copy_path(path, mode=mode, first=False)

            if event.key() == QtCore.Qt.Key_Plus:
                self.save_selection()
                self.increase_row_size()
                return

            if event.key() == QtCore.Qt.Key_0:
                self.save_selection()
                self.reset_row_size()
                return

            if event.key() == QtCore.Qt.Key_Minus:
                self.save_selection()
                self.decrease_row_size()
                return

            if event.key() == QtCore.Qt.Key_R:
                self.model().sourceModel().modelDataResetRequested.emit()
                return

            if event.key() == QtCore.Qt.Key_T:
                self.show_todos(index)
                return

            if event.key() == QtCore.Qt.Key_O:
                if index.data(QtCore.Qt.StatusTipRole):
                    common.reveal(index.data(QtCore.Qt.StatusTipRole))
                return

            if event.key() == QtCore.Qt.Key_S:
                self.save_selection()
                self.toggle_item_flag(
                    index,
                    common.MarkedAsFavourite
                )
                self.update(index)
                self.model().invalidateFilter()
                return

            if event.key() == QtCore.Qt.Key_A:
                self.save_selection()
                self.toggle_item_flag(
                    index,
                    common.MarkedAsArchived
                )
                self.update(index)
                self.model().invalidateFilter()
                return

        if event.modifiers() & QtCore.Qt.ShiftModifier:
            if event.key() == QtCore.Qt.Key_Tab:
                self.key_up()
                self.key_tab()
                self.save_selection()
                return
            elif event.key() == QtCore.Qt.Key_Backtab:
                self.key_up()
                self.key_tab()
                self.save_selection()
                return

    def wheelEvent(self, event):
        """Custom wheel event responsible for scrolling the list.

        """
        event.accept()
        control_modifier = event.modifiers() & QtCore.Qt.ControlModifier

        if not control_modifier:
            shift_modifier = event.modifiers() & QtCore.Qt.ShiftModifier
            o = 9 if shift_modifier else 0
            v = self.verticalScrollBar().value()
            if event.angleDelta().y() > 0:
                v = self.verticalScrollBar().setValue(v + 1 + o)
            else:
                v = self.verticalScrollBar().setValue(v - 1 - o)
            return

        if event.angleDelta().y() > 0:
            self.increase_row_size()
        else:
            self.decrease_row_size()

    def contextMenuEvent(self, event):
        """Custom context menu event."""
        index = self.indexAt(event.pos())

        width = self.viewport().geometry().width()
        width = (width * 0.5) if width > common.HEIGHT() else width
        width = width - common.INDICATOR_WIDTH()

        # Custom context menu
        shift_modifier = event.modifiers() & QtCore.Qt.ShiftModifier
        alt_modifier = event.modifiers() & QtCore.Qt.AltModifier
        control_modifier = event.modifiers() & QtCore.Qt.ControlModifier

        if shift_modifier or alt_modifier or control_modifier:
            self.customContextMenuRequested.emit(index, self)
            return

        if not self.ContextMenu:
            return

        if index.isValid():
            rect = self.visualRect(index)
            gpos = self.viewport().mapToGlobal(event.pos())
            rectangles = delegate.get_rectangles(rect, self.inline_icons_count())
            if rectangles[delegate.ThumbnailRect].contains(event.pos()):
                widget = ThumbnailsContextMenu(index, parent=self)
            else:
                widget = self.ContextMenu(index, parent=self)
            widget.move(
                gpos.x(),
                self.viewport().mapToGlobal(rect.bottomLeft()).y(),
            )
        else:
            widget = self.ContextMenu(index, parent=self)
            widget.move(common.cursor.pos())

        widget.move(widget.x() + common.INDICATOR_WIDTH(), widget.y())
        common.move_widget_to_available_geo(widget)
        widget.exec_()

    def action_on_enter_key(self):
        if not self.selectionModel().hasSelection():
            return
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return
        self.activate(index)

    def mousePressEvent(self, event):
        """Deselecting item when the index is invalid."""
        if not isinstance(event, QtGui.QMouseEvent):
            return

        cursor_position = self.mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)
        if not index.isValid():
            self.selectionModel().setCurrentIndex(
                QtCore.QModelIndex(),
                QtCore.QItemSelectionModel.ClearAndSelect
            )
        super(BaseListWidget, self).mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Custom doubleclick event.

        A double click can `activate` an item, or it can trigger an edit event.
        As each item is associated with multiple editors we have to inspect
        the doubleclick location before deciding what action to take.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return

        cursor_position = self.mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)
        if not index.isValid():
            return
        if index.flags() & common.MarkedAsArchived:
            return

        rect = self.visualRect(index)
        rectangles = delegate.get_rectangles(rect, self.inline_icons_count())
        description_rectangle = self.itemDelegate().get_description_rect(rectangles, index)

        if description_rectangle.contains(cursor_position):
            self.description_editor_widget.show()
            return

        if rectangles[delegate.ThumbnailRect].contains(cursor_position):
            images.pick(index)
            return

        clickable_rectangles = self.itemDelegate().get_clickable_rectangles(
            index, rectangles)
        if not self.buttons_hidden() and clickable_rectangles:
            root_dir = []
            for item in clickable_rectangles:
                rect, text = item

                if not text or not rect:
                    continue

                root_dir.append(text)
                if rect.contains(cursor_position):
                    p = index.data(common.ParentPathRole)
                    if len(p) >= 5:
                        p = p[0:5]
                    elif len(p) == 3:
                        p = [p[0], ]

                    path = u'/'.join(p).rstrip(u'/')
                    root_path = u'/'.join(root_dir).strip(u'/')
                    path = path + u'/' + root_path
                    common.reveal(path)
                    return

        if rectangles[delegate.DataRect].contains(cursor_position):
            if not self.selectionModel().hasSelection():
                return
            index = self.selectionModel().currentIndex()
            if not index.isValid():
                return
            self.activate(index)
            return

    def _get_status_string(self):
        proxy = self.model()
        model = proxy.sourceModel()

        # Model is empty
        if not model.rowCount():
            return u'No items to display'

        # All items are visible
        if proxy.rowCount() == model.rowCount():
            return u''

        # Because...
        reason = u''
        if proxy.filter_text():
            reason = u'a search filter is applied'
        elif proxy.filter_flag(common.MarkedAsFavourite):
            reason = u'showing favourites only'
        elif proxy.filter_flag(common.MarkedAsActive):
            reason = u'showing active item only'
        elif not proxy.filter_flag(common.MarkedAsArchived):
            reason = u'archived items are hidden'

        # Items are hidden...
        count = model.rowCount() - proxy.rowCount()
        if count == 1:
            return u'{} item is hidden ({})'.format(count, reason)
        return u'{} items are hidden ({})'.format(count, reason)

    def paint_status_message(self, widget, event):
        proxy = self.model()
        model = proxy.sourceModel()

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        n = 0
        rect = QtCore.QRect(
            0, 0,
            self.viewport().rect().width(),
            model.ROW_SIZE.height()
        )

        while self.rect().intersects(rect):
            if n == proxy.rowCount():
                if n == 0:
                    rect.moveCenter(self.rect().center())
                break
            rect.moveTop(rect.top() + rect.height())
            n += 1

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        o = common.INDICATOR_WIDTH()

        text = self._get_status_string()
        if not text:
            return

        rect = rect.marginsRemoved(QtCore.QMargins(o * 3, o, o * 3, o))
        painter.setOpacity(0.3)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(BACKGROUND_COLOR)
        painter.drawRoundedRect(rect, o, o)

        font, metrics = common.font_db.primary_font(font_size=common.SMALL_FONT_SIZE())
        text = metrics.elidedText(
            text,
            QtCore.Qt.ElideRight,
            rect.width()
        )

        x = rect.center().x() - (metrics.width(text) / 2.0)
        y = rect.center().y() + (metrics.ascent() / 2.0)

        painter.setOpacity(1.0)
        painter.setBrush(common.REMOVE)
        path = delegate.get_painter_path(x, y, font, text)
        painter.drawPath(path)
        painter.end()

    def paint_background_icon(self, widget, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        pixmap = images.ImageCache.get_rsc_pixmap(
            self._background_icon, BACKGROUND_COLOR, common.ROW_HEIGHT() * 3)
        rect = pixmap.rect()
        rect.moveCenter(self.rect().center())
        painter.drawPixmap(rect, pixmap, pixmap.rect())
        painter.end()

    def eventFilter(self, widget, event):
        if widget is not self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            self.paint_background_icon(widget, event)
            self.paint_status_message(widget, event)
            return True
        return False

    def resizeEvent(self, event):
        self._layout_timer.start(self._layout_timer.interval())
        self.resized.emit(self.viewport().geometry())

    @QtCore.Slot()
    def repaint_visible_rows(self):
        def _next(rect):
            rect.moveTop(rect.top() + rect.height())
            return self.indexAt(rect.topLeft())

        proxy = self.model()
        if not proxy.rowCount():
            return

        viewport_rect = self.viewport().rect()
        index = self.indexAt(viewport_rect.topLeft())
        if not index.isValid():
            return

        index_rect = self.visualRect(index)
        n = 0
        while viewport_rect.intersects(index_rect):
            if n > 99:  # manuel limit on how many items we will repaint
                break
            super(BaseListWidget, self).update(index)
            index = _next(index_rect)
            if not index.isValid():
                break
            n += 1

    def _reset_rows(self):
        """Reinitializes the rows to apply size-change."""
        proxy = self.model()
        index = self.selectionModel().currentIndex()
        row = -1
        if self.selectionModel().hasSelection() and index.isValid():
            row = index.row()

        self.scheduleDelayedItemsLayout()
        self.start_queue_timers()
        self.repaint_visible_rows()

        if row >= 0:
            index = proxy.index(row, 0)
            self.selectionModel().setCurrentIndex(
                index, QtCore.QItemSelectionModel.ClearAndSelect)
            self.scrollTo(
                index, QtWidgets.QAbstractItemView.PositionAtCenter)

    def _save_row_size(self, v):
        """Saves the current row size to the local settings."""
        proxy = self.model()
        model = proxy.sourceModel()
        model.ROW_SIZE.setHeight(int(v))

        cls = self.model().sourceModel().__class__.__name__
        k = u'widget/{}/rowheight'.format(cls).lower()
        settings.local_settings.setValue(k, int(v))

    def increase_row_size(self):
        """Makes the row height bigger."""
        proxy = self.model()
        model = proxy.sourceModel()

        v = model.ROW_SIZE.height() + common.psize(20)
        if v > common.ROW_HEIGHT() * 10:
            return

        self._save_row_size(v)
        self._reset_rows()

    def decrease_row_size(self):
        """Makes the row height smaller."""
        proxy = self.model()
        model = proxy.sourceModel()

        v = model.ROW_SIZE.height() - common.psize(20)
        if v <= common.ROW_HEIGHT():
            v = common.ROW_HEIGHT()

        self._save_row_size(v)
        self._reset_rows()

    def reset_row_size(self):
        """Resets the row size to its original size."""
        proxy = self.model()
        model = proxy.sourceModel()
        v = model.DEFAULT_ROW_SIZE.height()
        self._save_row_size(v)
        self._reset_rows()

    def dragEnterEvent(self, event):
        self._thumbnail_drop = (-1, False)
        self.repaint(self.rect())
        if event.source() == self:
            event.ignore()
            return
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        event.accept()

    def dragLeaveEvent(self, event):
        self._thumbnail_drop = (-1, False)
        self.repaint(self.rect())

    def dragMoveEvent(self, event):
        self._thumbnail_drop = (-1, False)
        pos = common.cursor.pos()
        pos = self.mapFromGlobal(pos)

        index = self.indexAt(pos)
        row = index.row()

        if not index.isValid():
            self._thumbnail_drop = (-1, False)
            self.repaint(self.rect())
            event.ignore()
            return

        proxy = self.model()
        model = proxy.sourceModel()
        index = proxy.mapToSource(index)

        if not model.canDropMimeData(event.mimeData(), event.proposedAction(), index.row(), 0):
            self._thumbnail_drop = (-1, False)
            self.repaint(self.rect())
            event.ignore()
            return

        event.accept()
        self._thumbnail_drop = (row, True)
        self.repaint(self.rect())

    def dropEvent(self, event):
        self._thumbnail_drop = (-1, False)

        pos = common.cursor.pos()
        pos = self.mapFromGlobal(pos)

        index = self.indexAt(pos)
        if not index.isValid():
            event.ignore()
            return
        proxy = self.model()
        model = proxy.sourceModel()
        index = proxy.mapToSource(index)

        if not model.canDropMimeData(event.mimeData(), event.proposedAction(), index.row(), 0):
            event.ignore()
            return
        model.dropMimeData(
            event.mimeData(), event.proposedAction(), index.row(), 0)

    def showEvent(self, event):
        self.scheduleDelayedItemsLayout()
        self.validate_visible_timer.start()

    def hideEvent(self, event):
        self.validate_visible_timer.stop()

    def mouseReleaseEvent(self, event):
        super(BaseListWidget, self).mouseReleaseEvent(event)
        self.save_selection()


class BaseInlineIconWidget(BaseListWidget):
    """Multi-toggle capable widget with clickable in-line icons."""

    def __init__(self, parent=None):
        super(BaseInlineIconWidget, self).__init__(parent=parent)

        self.multi_toggle_pos = None
        self.multi_toggle_state = None
        self.multi_toggle_idx = None
        self.multi_toggle_item = None
        self.multi_toggle_items = {}

    def inline_icons_count(self):
        """The numberof inline icons."""
        return 0

    def reset_multitoggle(self):
        self.multi_toggle_pos = None
        self.multi_toggle_state = None
        self.multi_toggle_idx = None
        self.multi_toggle_item = None
        self.multi_toggle_items = {}

    def mousePressEvent(self, event):
        """The `BaseInlineIconWidget`'s mousePressEvent initiates multi-row
        flag toggling.

        This event is responsible for setting ``multi_toggle_pos``, the start
        position of the toggle, ``multi_toggle_state`` & ``multi_toggle_idx``
        the modes of the toggle, based on the state of the state and location of
        the clicked item.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            self.reset_multitoggle()
            return

        cursor_position = self.mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)
        if not index.isValid():
            super(BaseInlineIconWidget, self).mousePressEvent(event)
            self.reset_multitoggle()
            return

        self.reset_multitoggle()

        rect = self.visualRect(index)
        rectangles = delegate.get_rectangles(rect, self.inline_icons_count())

        if rectangles[delegate.FavouriteRect].contains(cursor_position):
            self.multi_toggle_pos = QtCore.QPoint(0, cursor_position.y())
            self.multi_toggle_state = not index.flags() & common.MarkedAsFavourite
            self.multi_toggle_idx = delegate.FavouriteRect

        if rectangles[delegate.ArchiveRect].contains(cursor_position):
            self.multi_toggle_pos = cursor_position
            self.multi_toggle_state = not index.flags() & common.MarkedAsArchived
            self.multi_toggle_idx = delegate.ArchiveRect

        super(BaseInlineIconWidget, self).mousePressEvent(event)

    def enterEvent(self, event):
        QtWidgets.QApplication.instance().restoreOverrideCursor()
        super(BaseInlineIconWidget, self).enterEvent(event)

    def leaveEvent(self, event):
        app = QtWidgets.QApplication.instance()
        app.restoreOverrideCursor()

    def mouseReleaseEvent(self, event):
        """Concludes `BaseInlineIconWidget`'s multi-item toggle operation, and
        resets the associated variables.

        The inlince icon buttons are also triggered here. We're using the
        delegate's ``get_rectangles`` function to determine which icon was
        clicked.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            self.reset_multitoggle()
            return

        # Let's handle the clickable rectangle event first
        self.clickableRectangleEvent(event)

        index = self.indexAt(event.pos())
        if not index.isValid():
            self.reset_multitoggle()
            super(BaseInlineIconWidget, self).mouseReleaseEvent(event)
            return

        if self.multi_toggle_items:
            for n in self.multi_toggle_items:
                index = self.model().index(n, 0)
            self.reset_multitoggle()
            self.model().invalidateFilter()
            super(BaseInlineIconWidget, self).mouseReleaseEvent(event)
            return

        # Responding the click-events based on the position:
        rect = self.visualRect(index)
        rectangles = delegate.get_rectangles(rect, self.inline_icons_count())
        cursor_position = self.mapFromGlobal(common.cursor.pos())

        self.reset_multitoggle()

        if rectangles[delegate.FavouriteRect].contains(cursor_position):
            self.toggle_item_flag(
                index,
                common.MarkedAsFavourite
            )
            self.update(index)
            self.model().invalidateFilter()

        if rectangles[delegate.ArchiveRect].contains(cursor_position):
            self.toggle_item_flag(
                index,
                common.MarkedAsArchived
            )
            self.update(index)
            self.model().invalidateFilter()

        if rectangles[delegate.RevealRect].contains(cursor_position):
            common.reveal(index.data(QtCore.Qt.StatusTipRole))

        if rectangles[delegate.TodoRect].contains(cursor_position):
            self.show_todos(index)

        super(BaseInlineIconWidget, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """``BaseInlineIconWidget``'s mouse move event is responsible for
        handling the multi-toggle operations and repainting the current index
        under the mouse.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return

        cursor_position = self.mapFromGlobal(common.cursor.pos())
        app = QtWidgets.QApplication.instance()
        index = self.indexAt(cursor_position)
        if not index.isValid():
            app.restoreOverrideCursor()
            return

        rectangles = delegate.get_rectangles(self.visualRect(index), self.inline_icons_count())
        for k in (
            delegate.BookmarkPropertiesRect,
            delegate.AddAssetRect,
            delegate.DataRect,
            delegate.TodoRect,
            delegate.RevealRect,
            delegate.ArchiveRect,
            delegate.FavouriteRect
        ):
            if rectangles[k].contains(cursor_position):
                self.update(index)

        rect = self.itemDelegate().get_description_rect(rectangles, index)
        if rect.contains(cursor_position):
            self.update(index)
            if app.overrideCursor():
                app.changeOverrideCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
            else:
                app.restoreOverrideCursor()
                app.setOverrideCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
        else:
            app.restoreOverrideCursor()

        # Start multitoggle
        if self.multi_toggle_pos is None:
            super(BaseInlineIconWidget, self).mouseMoveEvent(event)
            return

        try:

            initial_index = self.indexAt(self.multi_toggle_pos)
            idx = index.row()

            # Exclude the current item
            if index == self.multi_toggle_item:
                return

            self.multi_toggle_item = index

            favourite = index.flags() & common.MarkedAsFavourite
            archived = index.flags() & common.MarkedAsArchived

            if idx not in self.multi_toggle_items:
                if self.multi_toggle_idx == delegate.FavouriteRect:
                    self.multi_toggle_items[idx] = favourite
                    self.toggle_item_flag(
                        index,
                        common.MarkedAsFavourite,
                        state=self.multi_toggle_state
                    )

                if self.multi_toggle_idx == delegate.ArchiveRect:
                    self.multi_toggle_items[idx] = archived
                    self.toggle_item_flag(
                        index,
                        common.MarkedAsArchived,
                        state=self.multi_toggle_state
                    )
                return

            if index == initial_index:
                return

            if self.multi_toggle_idx == delegate.FavouriteRect:
                self.toggle_item_flag(
                    index,
                    common.MarkedAsFavourite,
                    state=self.multi_toggle_items.pop(idx)
                )
            elif self.multi_toggle_idx == delegate.FavouriteRect:
                self.toggle_item_flag(
                    index,
                    common.MarkedAsArchived,
                    state=self.multi_toggle_items.pop(idx)
                )
        except:
            log.error(u'Multitoggle failed')
        finally:
            self.update(index)

    def show_todos(self, index):
        """Shows the ``TodoEditorWidget`` for the current item."""
        if not index.isValid():
            return
        from bookmarks.todo_editor import TodoEditorWidget

        # Let's check if other editors are open and close them if so
        editors = [f for f in self.children() if isinstance(f,
                                                            TodoEditorWidget)]
        if editors:
            for editor in editors:
                editor.done(QtWidgets.QDialog.Rejected)

        source_index = self.model().mapToSource(index)

        widget = TodoEditorWidget(source_index, parent=self)
        self.resized.connect(widget.setGeometry)
        widget.finished.connect(widget.deleteLater)
        widget.open()

    @QtCore.Slot()
    def show_preferences(self):
        import bookmarks.preferenceswidget as preferenceswidget
        widget = preferenceswidget.PreferencesWidget()
        widget.show()

    @QtCore.Slot(QtCore.QModelIndex)
    def show_slacker(self, index):
        if not index.isValid():
            return None
        try:
            import bookmarks.slacker as slacker
        except ImportError as err:
            common_ui.ErrorBox(
                u'Could not import SlackClient',
                u'The Slack API python module was not loaded:\n{}'.format(err),
            ).open()
            log.error(u'Slack import error.')
            raise

        db = bookmark_db.get_db(
            index.data(common.ParentPathRole)[0],
            index.data(common.ParentPathRole)[1],
            index.data(common.ParentPathRole)[2],
        )
        token = db.value(1, u'slacktoken', table=u'properties')

        if slacker.instance is not None:
            source_model = slacker.instance.message_widget.users_widget.model().sourceModel()
            if source_model.client.token == token:
                slacker.instance.setGeometry(self.viewport().geometry())
                slacker.instance.open()
                return slacker.instance

        slacker.instance = slacker.SlackWidget(token, parent=self)
        source_model = slacker.instance.message_widget.users_widget.model().sourceModel()
        self.resized.connect(slacker.instance.setGeometry)
        slacker.instance.setGeometry(self.viewport().geometry())

        try:
            source_model.client.verify_token()
            slacker.instance.open()
            return slacker.instance
        except:
            log.error(u'Invalid token')
            raise

    @QtCore.Slot()
    def start_queue_timers(self):
        pass

    @QtCore.Slot()
    def queue_model_data(self):
        pass

    @QtCore.Slot()
    def queue_visible_indexes(self, *args, **kwargs):
        pass

    def clickableRectangleEvent(self, event):
        """Used to handle a mouse press/release on a clickable element. The
        clickable rectangles define interactive regions on the list widget, and
        are set by the delegate.

        For instance, the files widget has a few addittional clickable inline icons
        that control filtering we set the action for here.

        ``Shift`` modifier will add a "positive" filter and hide all items that
        does not contain the given text.

        The ``alt`` or control modifiers will add a "negative filter" and hide
        the selected subfolder from the view.

        """
        cursor_position = self.mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)

        if not index.isValid():
            return

        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier
        control_modifier = modifiers & QtCore.Qt.ControlModifier

        rect = self.visualRect(index)
        rectangles = delegate.get_rectangles(rect, self.inline_icons_count())
        clickable_rectangles = self.itemDelegate().get_clickable_rectangles(
            index, rectangles)
        if not clickable_rectangles:
            return

        cursor_position = self.mapFromGlobal(common.cursor.pos())

        for idx, item in enumerate(clickable_rectangles):
            if idx == 0:
                continue  # First rectanble is always the description editor

            rect, text = item
            text = text.lower()

            if rect.contains(cursor_position):
                filter_text = self.model().filter_text()
                filter_text = filter_text.lower() if filter_text else u''

                # Shift modifier will add a "positive" filter and hide all items
                # that does not contain the given text.
                if shift_modifier:
                    folder_filter = u'"/' + text + u'/"'

                    if folder_filter in filter_text:
                        filter_text = filter_text.replace(folder_filter, u'')
                    else:
                        filter_text = filter_text + u' ' + folder_filter

                    self.model().filterTextChanged.emit(filter_text)
                    self.repaint(self.rect())
                    return

                # The alt or control modifiers will add a "negative filter"
                # and hide the selected subfolder from the view
                if alt_modifier or control_modifier:
                    folder_filter = u'--"/' + text + u'/"'
                    _folder_filter = u'"/' + text + u'/"'

                    if filter_text:
                        if _folder_filter in filter_text:
                            filter_text = filter_text.replace(
                                _folder_filter, u'')
                        if folder_filter not in filter_text:
                            folder_filter = filter_text + u' ' + folder_filter

                    self.model().filterTextChanged.emit(folder_filter)
                    self.repaint(self.rect())
                    return


class ThreadedBaseWidget(BaseInlineIconWidget):
    """Extends the base-class with the methods used to interface with threads.

    Attributes:
        queue_model_timer (QTimer):     Used to request file information for the
                                        model data.
        queue_visible_timer (QTimer):   Used to request file and thumnbnail
                                        information for individual items.

    """

    def __init__(self, parent=None):
        super(ThreadedBaseWidget, self).__init__(parent=parent)

        self.queue_model_timer = QtCore.QTimer(parent=self)
        self.queue_model_timer.setSingleShot(True)
        self.queue_model_timer.setInterval(250)

        self.queue_visible_timer = QtCore.QTimer(parent=self)
        self.queue_visible_timer.setSingleShot(True)
        self.queue_visible_timer.setInterval(100)

        self.connect_thread_signals()

    def connect_thread_signals(self):
        # Connect signals
        proxy = self.model()
        model = proxy.sourceModel()
        cnx_type = QtCore.Qt.AutoConnection

        # Empty the queue when the data changes
        model.modelAboutToBeReset.connect(
            lambda: log.debug('modelAboutToBeReset -> reset_worker_queues', model))
        model.modelAboutToBeReset.connect(
            model.reset_worker_queues, cnx_type)

        # Visible indexes to threads
        self.queue_visible_timer.timeout.connect(
            lambda: log.debug('timeout -> queue_visible_indexes', self.queue_visible_timer))
        self.queue_visible_timer.timeout.connect(
            partial(
                self.queue_visible_indexes,
                common.FileInfoLoaded,
                common.InfoThread
            ),
            cnx_type
        )
        self.queue_visible_timer.timeout.connect(
            lambda: log.debug('timeout -> queue_visible_indexes', self.queue_visible_timer))
        self.queue_visible_timer.timeout.connect(
            partial(
                self.queue_visible_indexes,
                common.ThumbnailLoaded,
                common.ThumbnailThread
            ),
            cnx_type
        )

        model.modelReset.connect(
            partial(
                self.queue_visible_indexes,
                common.FileInfoLoaded,
                common.InfoThread
            ),
            cnx_type
        )
        model.modelReset.connect(
            partial(
                self.queue_visible_indexes,
                common.ThumbnailLoaded,
                common.ThumbnailThread
            ),
            cnx_type
        )

        # Start / Stop request info timers
        model.modelAboutToBeReset.connect(
            lambda: log.debug('modelAboutToBeReset -> stop_queue_timers', model))
        model.modelAboutToBeReset.connect(
            self.stop_queue_timers, cnx_type)
        model.modelReset.connect(
            lambda: log.debug('modelReset -> start_queue_timers', model))
        model.modelReset.connect(
            self.start_queue_timers, cnx_type)

        # Start / Stop queue timer
        model.modelAboutToBeReset.connect(
            lambda: log.debug('modelAboutToBeReset -> stop_queue_timers', model))
        model.modelAboutToBeReset.connect(
            model.stopCheckQueue, cnx_type)
        model.modelReset.connect(
            lambda: log.debug('modelReset -> start_queue_timers', model))
        model.modelReset.connect(
            model.startCheckQueue, cnx_type)

        # Filter changed
        proxy.filterTextChanged.connect(
            lambda: log.debug('filterTextChanged -> start_queue_timers', proxy))
        proxy.filterTextChanged.connect(
            self.start_queue_timers, cnx_type)
        proxy.filterFlagChanged.connect(
            lambda: log.debug('filterFlagChanged -> start_queue_timers', proxy))
        proxy.filterFlagChanged.connect(
            self.start_queue_timers, cnx_type)

        self.verticalScrollBar().sliderPressed.connect(
            lambda: log.debug('sliderPressed -> stop_queue_timers', self.verticalScrollBar()))
        self.verticalScrollBar().sliderPressed.connect(
            self.stop_queue_timers)

        self.verticalScrollBar().sliderReleased.connect(
            lambda: log.debug('sliderReleased -> start_queue_timers', self.verticalScrollBar()))
        self.verticalScrollBar().sliderReleased.connect(
            self.start_queue_timers)

        # Thread update signals
        model.modelAboutToBeReset.connect(
            lambda: model.reset_worker_queues(all=True))
        # Queue model data
        self.queue_model_timer.timeout.connect(self.queue_model_data)

        model.modelAboutToBeReset.connect(
            lambda: log.debug('modelAboutToBeReset -> queue_model_timer.stop', model))
        model.modelAboutToBeReset.connect(
            self.queue_model_timer.stop, cnx_type)

        model.modelReset.connect(
            lambda: log.debug('modelReset -> queue_model_timer.start', model))
        model.modelReset.connect(self.queue_model_timer.start)

        model.modelReset.connect(
            lambda: self.verticalScrollBar().valueChanged.emit(self.verticalScrollBar().value()))

    @QtCore.Slot()
    def start_queue_timers(self):
        """Start the timers used to load an item's secondary data.

        """
        log.debug('start_queue_timers()', self)
        if not self.queue_visible_timer.isActive():
            self.queue_visible_timer.start(
                self.queue_visible_timer.interval())

    @QtCore.Slot()
    def stop_queue_timers(self):
        """Stop the timers used to load an item's secondary data.

        """
        log.debug('stop_queue_timers()', self)
        self.queue_visible_timer.stop()

    @QtCore.Slot()
    def queue_model_data(self):
        """Queues the model data for the BackgroundInfoThread to process."""
        log.debug('queue_model_data()', self)

        model = self.model().sourceModel()
        if model._model_loaded[model.data_type()]:
            return
        model.queueModel.emit(repr(model))

    @QtCore.Slot(int)
    @QtCore.Slot(int)
    def queue_visible_indexes(self, DataRole, thread_type):
        """Queue previously not loaded and visible indexes for processing.

        Args:
            DataRole (int): The model data role used for checking the state of the index.
            thread_type (int): Use the threads of `thread_type` to process the data.

        """
        def _next(rect):
            rect.moveTop(rect.top() + rect.height())
            return self.indexAt(rect.topLeft())

        if not isinstance(DataRole, (int, long)):
            raise TypeError(
                u'Invalid `DataRole`, expected <type \'int\', got {}'.format(type(DataRole)))
        if not isinstance(thread_type, int):
            raise TypeError(u'Invalid `thread_type`, expected <type \'int\', got {}'.format(
                type(thread_type)))

        log.debug('queue_visible_indexes() - Begin', self)

        proxy = self.model()
        if not proxy.rowCount():
            log.debug('queue_visible_indexes() - No proxy rows', self)
            return

        model = proxy.sourceModel()
        data = model.model_data()

        # Find the first visible index
        viewport_rect = self.viewport().rect()
        index = self.indexAt(viewport_rect.topLeft())
        if not index.isValid():
            return
        index_rect = self.visualRect(index)

        thread_count = len(model.threads[thread_type])
        show_archived = proxy.filter_flag(common.MarkedAsArchived)

        n = 0
        i = 0
        l = []
        while viewport_rect.intersects(index_rect):
            # Don't check more than 999 items
            if i >= 999:
                break
            i += 1

            # If we encounter an archived item, we should to invalidate the
            # proxy to hide it
            is_archived = index.flags() & common.MarkedAsArchived
            if show_archived is False and is_archived:
                proxy.invalidateFilter()
                log.debug('queue_visible_indexes() - invalidateFilter()', self)
                return  # abort

            # Nothing else to do if the threads are not enabled
            if not thread_count:
                index = _next(index_rect)
                continue

            source_index = proxy.mapToSource(index)
            idx = source_index.row()
            if idx not in data:
                index = _next(index_rect)
                continue

            # We will skip the time if it has alrady been loaded
            skip = data[idx][DataRole]
            if skip:
                index = _next(index_rect)
                continue

            # Put the weakref in the thread's queue
            ref = weakref.ref(data[idx])
            l.append(ref)
            n += 1

            index = _next(index_rect)
            if not index.isValid():
                break

        for ref in reversed(l):
            model.threads[thread_type][n % thread_count].add_to_queue(ref)

        log.debug('queue_visible_indexes() - done', self)

    def wheelEvent(self, event):
        super(ThreadedBaseWidget, self).wheelEvent(event)
        self.start_queue_timers()

    def showEvent(self, event):
        super(ThreadedBaseWidget, self).showEvent(event)
        self.start_queue_timers()


class StackedWidget(QtWidgets.QStackedWidget):
    """Stacked widget used to hold and toggle the list widgets containing the
    bookmarks, assets, files and favourites."""

    def __init__(self, parent=None):
        super(StackedWidget, self).__init__(parent=parent)
        self.setObjectName(u'BrowserStackedWidget')

    def setCurrentIndex(self, idx):
        """Sets the current index of the ``StackedWidget``.

        Args:
            idx (int): The index of the widget to set.

        """
        # Converting idx to int
        idx = 0 if idx is None or False else idx
        idx = idx if idx >= 0 else 0

        # No active bookmark
        def active_index(x):
            return self.widget(x).model().sourceModel().active_index()
        if not active_index(0).isValid() and idx in (1, 2):
            idx = 0

        # No active asset
        if active_index(0).isValid() and not active_index(1).isValid() and idx == 2:
            idx = 1

        if idx <= 3:
            k = u'widget/mode'
            settings.local_settings.setValue(k, idx)

        super(StackedWidget, self).setCurrentIndex(idx)

    def _setCurrentIndex(self, idx):
        super(StackedWidget, self).setCurrentIndex(idx)

    def showEvent(self, event):
        if self.currentWidget():
            self.currentWidget().setFocus()
