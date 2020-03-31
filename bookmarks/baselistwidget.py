# -*- coding: utf-8 -*-
"""Bookmarks is built around the three main lists - **bookmarks**, **assets**
and **files**. Each of these lists has a *view*, *model* and *context menus*
stemming from the *BaseModel*, *BaseView* and *BaseContextMenu* classes defined
in ``baselistwidget.py`` and ``basecontextmenu.py`` modules.

The *BaseListWidget* subclasses are then added to the layout of **StackedWidget**,
the widget used to switch between the lists.

"""
import re
import weakref
from functools import wraps, partial

from PySide2 import QtWidgets, QtGui, QtCore

import bookmarks.bookmark_db as bookmark_db
import bookmarks.common as common
import bookmarks.common_ui as common_ui
import bookmarks.editors as editors
from bookmarks.basecontextmenu import BaseContextMenu
import bookmarks.delegate as delegate
import bookmarks.settings as settings
import bookmarks.images as images
import bookmarks.alembicpreview as alembicpreview

import bookmarks.threads as threads


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
        if not self.parent_path:
            return
        if not all(self.parent_path):
            return
        if not self.data_key():
            return

        try:
            self.beginResetModel()
            self._interrupt_requested = False
            common.Log.debug('__initdata__()', self)
            func(self, *args, **kwargs)
            # sort_data emits the reset signals already
            self.blockSignals(True)
            self.sort_data()
            self.blockSignals(False)
            self._interrupt_requested = False
            self.endResetModel()
        except:
            common.Log.error(u'Error loading the model data')
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
        color = QtGui.QColor(common.SEPARATOR)
        color.setAlpha(150)
        painter.setBrush(color)
        painter.drawRect(self.rect())
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(common.MEDIUM_FONT_SIZE()),
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
        """We're settings the settings saved in the local settings, and optional
        default values if the settings has not yet been saved.

        """
        model = self.sourceModel()
        data_key = model.data_key()
        cls = model.__class__.__name__
        self._filter_text = settings.local_settings.value(
            u'widget/{}/{}/filtertext'.format(cls, data_key))

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

        common.Log.debug('initialize_filter_values()', self)

    def filter_text(self):
        """Filters the list of items containing this path segment."""
        return self._filter_text

    @QtCore.Slot(unicode)
    def set_filter_text(self, val):
        """Sets the path-segment to use as a filter."""
        model = self.sourceModel()
        data_key = model.data_key()
        cls = model.__class__.__name__
        k = u'widget/{}/{}/filtertext'.format(cls, data_key)

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
    """The base model for storing bookmarks, assets and files.

    The model stores its data in the **self.INTERNAL_MODEL_DATA** private dictionary.
    The structure of the data is uniform accross all BaseModel instances but it
    really is built around storing file-data.

    Each folder in the assets folder corresponds to a **data_key**.

    A data-key example:
        .. code-block:: python

            self.INTERNAL_MODEL_DATA = {}
            # will most of the time return a name of a folder, eg. 'scenes'
            datakey = self.data_key()
            self.INTERNAL_MODEL_DATA[datakey] = common.DataDict({
                common.FileItem: common.DataDict(),
                common.SequenceItem: common.DataDict()
            })

    Each data-key can simultaniously hold information about single files (**FileItems**), and
    groupped sequences (**SequenceItem**), eg. a rendered image sequence. The model provides the
    signals and slots for exposing the different private data elements to the model.

    Sorting information is also managed by BaseModel. The user choices are saved in
    the local registry.

    """

    # Emit before the model is about to change
    modelDataResetRequested = QtCore.Signal()
    """Main signal to request a reset and load"""

    activeChanged = QtCore.Signal(QtCore.QModelIndex)
    dataKeyChanged = QtCore.Signal(unicode)
    dataTypeChanged = QtCore.Signal(int)

    sortingChanged = QtCore.Signal(int, bool)  # (SortRole, SortOrder)

    progressMessage = QtCore.Signal(unicode)
    updateIndex = QtCore.Signal(QtCore.QModelIndex)
    updateRow = QtCore.Signal(weakref.ref)

    def __init__(self, parent=None):
        super(BaseModel, self).__init__(parent=parent)
        self.view = parent

        self.INTERNAL_MODEL_DATA = common.DataDict()
        """Custom data type for weakref compatibility """

        self.threads = {
            common.InfoThread: [],  # Threads for getting file-size, description
            common.BackgroundInfoThread: [],  # Thread for iterating the whole model
            common.ThumbnailThread: [],  # Thread for generating thumbnails
        }
        self._interrupt_requested = False
        self._generate_thumbnails_enabled = True
        self.file_info_loaded = False

        self._datakey = None
        self._datatype = {}
        self.parent_path = None

        self._sortrole = None
        self._sortorder = None

        @QtCore.Slot(bool)
        @QtCore.Slot(int)
        def set_sorting(role, order):
            self.set_sort_role(role)
            self.set_sort_order(order)
            self.sort_data()

        self.sortingChanged.connect(
            lambda: common.Log.debug('sortingChanged -> set_sorting', self))
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
        data = self.model_data()
        if row not in data:
            return False
        if not data[row][common.FileInfoLoaded]:
            return False
        if data[row][common.FlagsRole] & common.MarkedAsArchived:
            return False
        return True

    def dropMimeData(self, data, action, row, column, parent=QtCore.QModelIndex()):
        for url in data.urls():
            file_info = QtCore.QFileInfo(url.toLocalFile())
            source = file_info.filePath()
            images.ImageCache.pick(self.index(row, 0), source=source)
            return True
        return False

    def initialize_default_sort_values(self):
        """Loads the saved sorting values from the local preferences.

        """
        common.Log.debug('initialize_default_sort_values()', self)

        cls = self.__class__.__name__
        k = u'widget/{}/sortrole'.format(cls)
        val = settings.local_settings.value(k)
        if val not in (common.SortByName, common.SortBySize, common.SortByLastModified):
            val = common.SortByName
        self._sortrole = val

        k = u'widget/{}/sortorder'.format(cls)
        val = settings.local_settings.value(k)
        if val not in (True, False):
            val = False
        self._sortorder = val

        if self._sortrole is None:
            self._sortrole = common.SortByName

        if self._sortorder is None:
            self._sortorder = False

    def sort_role(self):
        """The item role used to sort the model data, eg. `common.SortByName`"""
        return self._sortrole

    @QtCore.Slot(int)
    def set_sort_role(self, val):
        """Sets and saves the sort-key."""
        common.Log.debug('set_sort_role({})'.format(val), self)

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
        common.Log.debug('set_sort_order({})'.format(val), self)

        if val == self.sort_order():
            return

        self._sortorder = val
        cls = self.__class__.__name__
        settings.local_settings.setValue(
            u'widget/{}/sortorder'.format(cls), val)

    @QtCore.Slot()
    def sort_data(self):
        """Sorts the internal `INTERNAL_MODEL_DATA` dictionary.
        """
        common.Log.debug(u'sort_data()', self)

        self.beginResetModel()

        k = self.data_key()
        t = self.data_type()

        data = self.model_data()
        if not data:
            return

        sortorder = self.sort_order()
        sortrole = self.sort_role()
        k = self.data_key()
        t = self.data_type()

        if sortrole not in (
            common.SortByName,
            common.SortBySize,
            common.SortByLastModified
        ):
            sortrole = common.SortByName

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

    @QtCore.Slot(QtCore.QModelIndex)
    def set_active(self, index):
        """Sets the model's ``self.parent_path``.

        The parent path is used by the model to load it's data. It is saved
        in the `common.ParentPathRole` with the exception of the bookmark
        items - we don't have parents for these as the source data is stored
        in a the local settings.

        """
        if not index.isValid():
            self.parent_path = None
            return
        self.parent_path = index.data(common.ParentPathRole)
        self.modelDataResetRequested.emit()

    def __resetdata__(self):
        """Resets the internal data."""
        common.Log.debug('__resetdata__()', self)

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
    def thread_started(self, thread):
        """Slot connected in initialise_threads().
        Signals the model an item has been updated.

        """
        common.Log.debug(u'thread_started()', self)
        thread.worker.dataReady.connect(
            lambda: common.Log.debug('dataReady -> updateRow', thread.worker))
        thread.worker.dataReady.connect(
            self.updateRow, type=QtCore.Qt.QueuedConnection)

    @QtCore.Slot()
    def model_loaded(self, ref):
        """Slot connected in initialise_threads().
        Slot called by the background file info thread when the thread
        finished loading the model data.

        The model might need re-sorting, and the proxy
        invalidating, when the sorting mode is anything but descending
        alphabetical. Calling sort_data() will emit all signals needed
        to repopulate.

        """
        common.Log.debug(u'model_loaded()', self)
        if not ref():
            return

        if ref() == self.model_data() and (self.sort_order() or self.sort_role() != common.SortByName):
            common.Log.debug(u'>>> Model needs re-sorting', self)
            self.sort_data()

    @QtCore.Slot(QtCore.QThread)
    @QtCore.Slot(weakref.ref)
    def put_in_thumbnail_queue(self, thread, ref):
        """Slot connected in initialise_threads()."""
        common.Log.success('put_in_thumbnail_queue()')
        if not ref():
            return
        if self.generate_thumbnails_enabled():
            thread.put(ref, force=True)

    def initialise_threads(self):
        """Starts and connects the threads."""
        common.Log.debug('initialise_threads()', self)

        info_worker = threads.InfoWorker()
        info_thread = threads.BaseThread(info_worker, interval=40)
        self.threads[common.InfoThread].append(info_thread)

        info_thread.started.connect(
            lambda: common.Log.debug('started -> thread_started', info_thread))
        info_thread.started.connect(partial(self.thread_started, info_thread))

        background_info_worker = threads.BackgroundInfoWorker()

        background_info_worker.modelLoaded.connect(
            lambda: common.Log.debug('modelLoaded -> model_loaded', background_info_worker))
        background_info_worker.modelLoaded.connect(
            self.model_loaded, QtCore.Qt.QueuedConnection)

        background_info_thread = threads.BaseThread(
            background_info_worker, interval=260)
        self.threads[common.BackgroundInfoThread].append(
            background_info_thread)

        background_info_thread.started.connect(
            lambda: common.Log.debug('started -> thread_started', background_info_thread))
        background_info_thread.started.connect(
            partial(self.thread_started, background_info_thread))

        thumbnails_worker = threads.ThumbnailWorker()
        thumbnails_thread = threads.BaseThread(thumbnails_worker, interval=100)
        self.threads[common.ThumbnailThread].append(thumbnails_thread)

        thumbnails_thread.started.connect(
            lambda: common.Log.debug('started -> thread_started', thumbnails_thread))
        thumbnails_thread.started.connect(
            partial(self.thread_started, thumbnails_thread))

        # The condition for loading a thumbnail is that the item must already
        # have its file info loaded. However, it is possible that the thumbnail
        # worker would consume an uninitiated item, leaving the thumbnail
        # unloaded. Hooking the dataReady signal up here means initiated
        # items will be sent to the thumbnail thread's queue to read the thumbnail
        # info_worker.dataReady.connect(
        #     lambda: common.Log.debug())
        info_worker.dataReady.connect(
            partial(self.put_in_thumbnail_queue, thumbnails_thread),
            type=QtCore.Qt.QueuedConnection)

        background_info_thread.start()
        info_thread.start()
        thumbnails_thread.start()

    def init_generate_thumbnails_enabled(self):
        common.Log.debug('init_generate_thumbnails_enabled()', self)

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
    def reset_file_info_loaded(self, *args):
        """Set the file-info-loaded state to ``False``. This property is used
        by the ``SecondaryFileInfoWorker`` to indicate all information has
        been loaded an no more work is necessary.

        """
        self.file_info_loaded = False

    @QtCore.Slot()
    def reset_thread_worker_queues(self):
        """This slot removes all queued items from the respective worker queues.
        Called by the ``modelAboutToBeReset`` signal.

        """
        common.Log.debug('reset_thread_worker_queues()', self)

        for k in self.threads:
            for thread in self.threads[k]:
                thread.worker.resetQueue.emit()

    def model_data(self):
        """A pointer to the model's currently set internal data."""
        k = self.data_key()
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
        """The flag values are stored in the model as a separate role."""
        return self.data(index, role=common.FlagsRole)

    def parent(self, child):
        """We don't implement parented indexes."""
        return QtCore.QModelIndex()

    def setData(self, index, data, role=QtCore.Qt.DisplayRole):
        """Data setter method."""
        if not index.isValid():
            return False
        if index.row() not in self.model_data():
            return False
        self.model_data()[index.row()][role] = data
        self.dataChanged.emit(index, index)
        return True

    def data_key(self):
        """Current key to the data dictionary."""
        raise NotImplementedError(
            'data_key is abstract and must be overriden')

    def data_type(self):
        """Current key to the data dictionary."""
        data_key = self.data_key()
        if data_key not in self._datatype:
            cls = self.__class__.__name__
            key = u'widget/{}/{}/datatype'.format(cls, data_key)
            val = settings.local_settings.value(key)
            val = val if val else common.SequenceItem
            self._datatype[data_key] = val
        return self._datatype[data_key]

    @QtCore.Slot(int)
    def set_data_type(self, val):
        """Sets the data type to `FileItem` or `SequenceItem`."""
        common.Log.debug('set_data_type({})>'.format(val), self)

        self.beginResetModel()

        try:
            data_key = self.data_key()
            if data_key not in self._datatype:
                self._datatype[data_key] = val
            if self._datatype[data_key] == val:
                return

            if val not in (common.FileItem, common.SequenceItem):
                raise ValueError(
                    u'Invalid value {} ({}) provided for `data_type`'.format(val, type(val)))

            cls = self.__class__.__name__
            key = u'widget/{}/{}/datatype'.format(cls, self.data_key())
            settings.local_settings.save_state(u'location', val)
            settings.local_settings.setValue(key, val)
            self._datatype[data_key] = val

        except:
            common.Log.error(u'Error setting data key')
        finally:
            self.blockSignals(True)
            self.sort_data()
            self.blockSignals(False)

            self.endResetModel()

    @QtCore.Slot(unicode)
    def set_data_key(self, val):
        """Settings data keys for asset and bookmarks widgets is not available."""
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

        self._thumbnail_drop = (-1, False)  # row, accepted
        self._background_icon = u'icon_bw'
        self._generate_thumbnails_enabled = True
        self.progress_widget = ProgressWidget(parent=self)
        self.progress_widget.setHidden(True)
        self.filter_active_widget = FilterOnOverlayWidget(parent=self)
        self.filter_editor = editors.FilterEditor(parent=self)
        self.filter_editor.setHidden(True)

        self.description_editor_widget = editors.DescriptionEditorWidget(
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
            lambda: common.Log.debug('<<< modelAboutToBeReset >>>', model))
        model.modelReset.connect(
            lambda: common.Log.debug('<<< modelReset >>>', model))

        model.modelDataResetRequested.connect(
            lambda: common.Log.debug('modelDataResetRequested -> __resetdata__', model))
        model.modelDataResetRequested.connect(model.__resetdata__)

        # Saves the active in the local settings
        model.activeChanged.connect(self.save_state)

        model.activeChanged.connect(
            lambda: common.Log.debug('activeChanged -> save_activated', model))
        model.activeChanged.connect(self.save_activated)

        # Data key, eg. 'scenes'
        model.dataKeyChanged.connect(
            lambda: common.Log.debug('dataKeyChanged -> set_data_key', model))
        model.dataKeyChanged.connect(model.set_data_key)

        model.dataKeyChanged.connect(
            lambda: common.Log.debug('dataKeyChanged -> proxy.invalidate', model))
        model.dataKeyChanged.connect(proxy.invalidate)

        # FileItem/SequenceItem
        model.dataTypeChanged.connect(
            lambda: common.Log.debug('dataTypeChanged -> proxy.invalidate', model))
        model.dataTypeChanged.connect(proxy.invalidate)

        model.dataTypeChanged.connect(
            lambda: common.Log.debug('dataTypeChanged -> set_data_type', model))
        model.dataTypeChanged.connect(model.set_data_type)

        proxy.filterTextChanged.connect(
            lambda: common.Log.debug('filterTextChanged -> set_filter_text', proxy))
        proxy.filterTextChanged.connect(proxy.set_filter_text)

        proxy.filterFlagChanged.connect(
            lambda: common.Log.debug('filterFlagChanged -> set_filter_flag', proxy))
        proxy.filterFlagChanged.connect(proxy.set_filter_flag)

        proxy.filterTextChanged.connect(
            lambda: common.Log.debug('filterTextChanged -> invalidateFilter', proxy))
        proxy.filterTextChanged.connect(proxy.invalidateFilter)

        proxy.filterFlagChanged.connect(
            lambda: common.Log.debug('filterFlagChanged -> invalidateFilter', proxy))
        proxy.filterFlagChanged.connect(proxy.invalidateFilter)

        model.modelAboutToBeReset.connect(
            lambda: common.Log.debug('modelAboutToBeReset -> reset_multitoggle', model))
        model.modelAboutToBeReset.connect(self.reset_multitoggle)

        self.filter_editor.finished.connect(
            lambda: common.Log.debug('finished -> filterTextChanged', self.filter_editor))
        self.filter_editor.finished.connect(proxy.filterTextChanged)

        model.updateIndex.connect(
            lambda: common.Log.debug('updateIndex -> update', model))
        model.updateIndex.connect(
            self.update, type=QtCore.Qt.DirectConnection)

        model.modelReset.connect(
            lambda: common.Log.debug('modelReset -> reselect_previous', model))
        model.modelReset.connect(self.reselect_previous)

        model.updateRow.connect(
            lambda: common.Log.debug('updateRow -> update_row', model))
        model.updateRow.connect(self.update_row)

        model.modelReset.connect(
            lambda: common.Log.debug('modelReset -> scheduleDelayedItemsLayout', model))
        model.modelReset.connect(self.scheduleDelayedItemsLayout)

    @QtCore.Slot(QtCore.QModelIndex)
    def save_state(self, index):
        """Saves the active item to the local settings."""
        common.Log.success('{}'.format(index))
        if not index.isValid():
            return

        try:
            settings.local_settings.save_state(
                u'server', index.data(common.ParentPathRole)[0])
            settings.local_settings.save_state(
                u'job', index.data(common.ParentPathRole)[1])
            settings.local_settings.save_state(
                u'root', index.data(common.ParentPathRole)[2])
        except IndexError:
            pass
        except Exception as e:
            common.Log.error('Could not save the state.')

        try:
            settings.local_settings.save_state(
                u'asset', index.data(common.ParentPathRole)[3])
        except IndexError:
            pass
        except Exception as e:
            common.Log.error('Could not save the state.')

        try:
            settings.local_settings.save_state(
                u'asset', index.data(common.ParentPathRole)[3])
        except IndexError:
            pass
        except Exception as e:
            common.Log.error('Could not save the state.')

        try:
            settings.local_settings.save_state(
                u'location', index.data(common.ParentPathRole)[4])
        except IndexError:
            pass
        except Exception as e:
            common.Log.error('Could not save the state.')

        common.Log.debug('save_state()', self)

    @QtCore.Slot(QtCore.QModelIndex)
    def update(self, index):
        """This slot is used by all threads to repaint/update the given index
        after it's thumbnail or file information has been loaded.

        The actualy repaint will only occure if the index is visible
        in the view currently.

        """
        if not index.isValid():
            return
        if self.isHidden():
            return
        if not hasattr(index.model(), u'sourceModel'):
            index = self.model().mapFromSource(index)
        super(BaseListWidget, self).update(index)

    @QtCore.Slot(weakref.ref)
    def update_row(self, ref):
        """Slot used to update the row associated with the data segment."""
        common.Log.debug('update_row(ref)', self)
        if not ref():
            return

        if self.isHidden():
            return
        model = self.model()
        index = model.sourceModel().index(ref()[common.IdRole], 0)
        index = model.mapFromSource(index)
        super(BaseListWidget, self).update(index)

    def request_visible_fileinfo_load(self):
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
        self.activated.emit(index)

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
        """"`save_activated` is abstract and has to be implemented in the subclass."""
        pass

    @QtCore.Slot()
    def save_selection(self):
        """Saves the currently selected path."""
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        cls = self.__class__.__name__
        k = u'widget/{}/{}/selected_item'.format(
            cls,
            self.model().sourceModel().data_key(),
        )
        v = common.proxy_path(index)
        settings.local_settings.setValue(k, v)

    @QtCore.Slot()
    def reselect_previous(self):
        """Slot called when the model has finished a reset operation.
        The method will try to reselect the previously selected path."""
        cls = self.__class__.__name__
        k = u'widget/{}/{}/selected_item'.format(
            cls,
            self.model().sourceModel().data_key(),
        )
        val = settings.local_settings.value(k)

        if not val:
            return

        proxy = self.model()
        for n in xrange(proxy.rowCount()):
            index = proxy.index(n, 0)
            path = common.proxy_path(index)
            if val.lower() == path.lower():
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

        if not proxy.rowCount():
            return

        index = proxy.index(0, 0)
        self.selectionModel().setCurrentIndex(
            index, QtCore.QItemSelectionModel.ClearAndSelect)
        self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)

    def toggle_item_flag(self, index, flag, state=None):
        """Sets the index's `flag` value based `state`.

        We're using this mark items archived, or favourite and save the changes
        to the database or the local config file.

        Args:
            index (QModelIndex): The index containing the
            flag (type): Description of parameter `flag`.
            state (type): Description of parameter `state`. Defaults to None.

        Returns:
            unicode: The key used to find and match items.

        """
        def _func(mode, data, flag):
            pass

        def save_to_db(k, mode, flag):
            """Save the value to the database."""
            try:
                db = bookmark_db.get_db(index)
            except:
                common.Log.error('Failed to get database')
                raise

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
            func = save_to_db
        elif flag == common.MarkedAsFavourite:
            func = save_to_local_settings
        elif flag == common.MarkedAsActive:
            func = save_active
        else:
            func = _func

        def _set_flag(k, mode, data, flag, commit=False):
            """Sets a single flag value based on the given mode."""
            if mode:
                data[common.FlagsRole] = data[common.FlagsRole] | flag
            else:
                data[common.FlagsRole] = data[common.FlagsRole] & ~flag
            if not commit:
                return
            func(k, mode, flag)

        def _set_flags(it, sequence_key, mode, flag):
            """Sets flags for multiple items."""
            for data in it:
                if not data[common.SequenceRole]:
                    continue
                k = common.proxy_path(data)
                if sequence_key != k:
                    continue
                _set_flag(k, mode, data, flag, commit=False)

        if not index.isValid():
            return None

        if hasattr(index.model(), 'sourceModel'):
            source_index = self.model().mapToSource(index)

        if not index.data(common.FileInfoLoaded):
            return None

        model = self.model().sourceModel()
        dkey = model.data_key()
        data = model.model_data()[source_index.row()]

        FILE_DATA = model.INTERNAL_MODEL_DATA[dkey][common.FileItem]
        SEQ_DATA = model.INTERNAL_MODEL_DATA[dkey][common.SequenceItem]

        applied = data[common.FlagsRole] & flag

        # Determine the mode of operation
        if state is None and applied:
            mode = False
        elif state is None and not applied:
            mode = True
        elif state is not None:
            mode = state

        # Sequence-agnosic key based on the file-name
        if data[common.SequenceRole]:
            k = common.proxy_path(data)
        else:
            k = data[QtCore.Qt.StatusTipRole]

        _set_flag(k, mode, data, flag, commit=True)

        if data[common.SequenceRole]:
            _set_flags(FILE_DATA.itervalues(), k, mode, flag)
            _set_flags(SEQ_DATA.itervalues(), k, mode, flag)

        self.repaint()
        return k

    def key_space(self):
        if not self.selectionModel().hasSelection():
            return
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return
        if not index.data(common.FileInfoLoaded):
            return
        path = index.data(QtCore.Qt.StatusTipRole)
        path = common.get_sequence_startpath(path)
        file_info = QtCore.QFileInfo(path)

        if file_info.suffix().lower() in (u'abc',):
            w = alembicpreview.AlembicView(file_info.filePath(), parent=self)
            self.selectionModel().currentChanged.connect(w.close)
            self.selectionModel().currentChanged.connect(w.deleteLater)
            w.show()
            return

        if not index.data(common.FileThumbnailLoaded):
            return

        if file_info.suffix().lower() in common.oiio_formats:
            w = images.ImageViewer(file_info.filePath(), parent=self)
            self.selectionModel().currentChanged.connect(w.delete_timer.start)
            w.show()
            return

        path = index.data(common.ThumbnailPathRole)
        if QtCore.QFileInfo(path).exists():
            w = images.ImageViewer(path, parent=self)
            self.selectionModel().currentChanged.connect(w.delete_timer.start)
            w.show()
            return

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

        if no_modifier or numpad_modifier:
            if event.key() == QtCore.Qt.Key_Space:
                self.key_space()
            if event.key() == QtCore.Qt.Key_Escape:
                self.selectionModel().setCurrentIndex(
                    QtCore.QModelIndex(), QtCore.QItemSelectionModel.ClearAndSelect)
            elif event.key() == QtCore.Qt.Key_Down:
                self.key_down()
                self.save_selection()
            elif event.key() == QtCore.Qt.Key_Up:
                self.key_up()
                self.save_selection()
            elif (event.key() == QtCore.Qt.Key_Return) or (event.key() == QtCore.Qt.Key_Enter):
                self.action_on_enter_key()
            elif event.key() == QtCore.Qt.Key_Tab:
                if not self.description_editor_widget.isVisible():
                    self.key_tab()
                else:
                    self.key_down()
                    self.key_tab()
                    self.save_selection()
            elif event.key() == QtCore.Qt.Key_Backtab:
                if not self.description_editor_widget.isVisible():
                    self.key_tab()
                else:
                    self.key_up()
                    self.key_tab()
                    self.save_selection()
            elif event.key() == QtCore.Qt.Key_PageDown:
                super(BaseListWidget, self).keyPressEvent(event)
                self.save_selection()
            elif event.key() == QtCore.Qt.Key_PageUp:
                super(BaseListWidget, self).keyPressEvent(event)
                self.save_selection()
            elif event.key() == QtCore.Qt.Key_Home:
                super(BaseListWidget, self).keyPressEvent(event)
                self.save_selection()
            elif event.key() == QtCore.Qt.Key_End:
                super(BaseListWidget, self).keyPressEvent(event)
                self.save_selection()
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
                            break

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
                self.increase_row_size()
                return

            if event.key() == QtCore.Qt.Key_Minus:
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
                self.toggle_item_flag(
                    index,
                    common.MarkedAsFavourite
                )
                self.update(index)
                self.model().invalidateFilter()
                return

            if event.key() == QtCore.Qt.Key_A:
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
            elif event.key() == QtCore.Qt.Key_Backtab:
                self.key_up()
                self.key_tab()

    def wheelEvent(self, event):
        event.accept()
        control_modifier = event.modifiers() & QtCore.Qt.ControlModifier

        if not control_modifier:
            shift_modifier = event.modifiers() & QtCore.Qt.ShiftModifier
            o = 9 if shift_modifier else 0
            v = self.verticalScrollBar().value()
            if event.angleDelta().y() > 0:
                v = self.verticalScrollBar().setValue(v + 1 + o)
            else:
                v = self.verticalScrollBar().setValue(v - 1 + o)
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
            rectangles = self.itemDelegate().get_rectangles(rect)
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
            widget.move(QtGui.QCursor().pos())

        widget.move(widget.x() + common.INDICATOR_WIDTH(), widget.y())
        common.move_widget_to_available_geo(widget)
        widget.exec_()

    def action_on_enter_key(self):
        self.activate(self.selectionModel().currentIndex())

    def mousePressEvent(self, event):
        """Deselecting item when the index is invalid."""
        if not isinstance(event, QtGui.QMouseEvent):
            self.reset_multitoggle()
            return
        cursor_position = self.mapFromGlobal(QtGui.QCursor().pos())
        index = self.indexAt(cursor_position)
        if not index.isValid():
            self.selectionModel().setCurrentIndex(
                QtCore.QModelIndex(),
                QtCore.QItemSelectionModel.ClearAndSelect
            )
        else:
            self.selectionModel().setCurrentIndex(
                index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )
        self.save_selection()
        super(BaseListWidget, self).mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Custom double - click event.

        A double click can `activate` an item, or it can trigger an edit event.
        As each item is associated with multiple editors we have to inspect
        the double - click location before deciding what action to take.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return

        cursor_position = self.mapFromGlobal(QtGui.QCursor().pos())
        index = self.indexAt(cursor_position)
        if not index.isValid():
            return
        if index.flags() & common.MarkedAsArchived:
            return

        rect = self.visualRect(index)
        rectangles = self.itemDelegate().get_rectangles(rect)
        description_rectangle = self.itemDelegate().get_description_rect(rectangles, index)

        if description_rectangle.contains(cursor_position):
            self.description_editor_widget.show()
            return

        if rectangles[delegate.DataRect].contains(cursor_position):
            self.activate(self.selectionModel().currentIndex())
            return

        if rectangles[delegate.ThumbnailRect].contains(cursor_position):
            images.ImageCache.pick(index, parent=self)
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

        _s = self._get_status_string()
        if not _s:
            return

        rect = rect.marginsRemoved(QtCore.QMargins(o * 3, o, o * 3, o))
        painter.setPen(QtCore.Qt.NoPen)
        font = common.font_db.primary_font(font_size=common.SMALL_FONT_SIZE())
        painter.setFont(font)
        painter.setBrush(QtGui.QColor(0, 0, 0, 50))
        painter.setOpacity(0.3)
        painter.drawRoundedRect(rect, o, o)
        painter.setOpacity(1.0)

        painter.setPen(common.TEXT_DISABLED)
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter | QtCore.Qt.TextWordWrap,
            _s,
            boundingRect=rect,
        )
        painter.end()

    def paint_background_icon(self, widget, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        pixmap = images.ImageCache.get_rsc_pixmap(
            self._background_icon, QtGui.QColor(0, 0, 0, 30), common.ROW_HEIGHT() * 3)
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
        self.resized.emit(self.viewport().geometry())

    def increase_row_size(self):
        proxy = self.model()
        model = proxy.sourceModel()
        v = model.ROW_SIZE.height() + common.psize(20)
        if v >= common.ROW_HEIGHT() * 10:
            return
        model.ROW_SIZE.setHeight(int(v))

        settings.local_settings.setValue(
            u'widget/rowheight', int(v))

        # Save selection
        row = self.selectionModel().currentIndex().row()

        model.reset_thumbnails()
        self.scheduleDelayedItemsLayout()
        self.start_requestinfo_timers()

        # Reset selection
        index = proxy.index(row, 0)
        self.selectionModel().setCurrentIndex(
            index, QtCore.QItemSelectionModel.ClearAndSelect)
        self.scrollTo(
            index, QtWidgets.QAbstractItemView.PositionAtCenter)

    def decrease_row_size(self):
        proxy = self.model()
        model = proxy.sourceModel()
        v = model.ROW_SIZE.height() - common.psize(20)
        if v < common.ROW_HEIGHT():
            v = common.ROW_HEIGHT()
        model.ROW_SIZE.setHeight(int(v))

        settings.local_settings.setValue(
            u'widget/rowheight', int(v))

        # Save selection
        row = self.selectionModel().currentIndex().row()

        model.reset_thumbnails()
        self.scheduleDelayedItemsLayout()
        self.start_requestinfo_timers()

        # Reset selection
        index = proxy.index(row, 0)
        self.selectionModel().setCurrentIndex(
            index, QtCore.QItemSelectionModel.ClearAndSelect)
        self.scrollTo(
            index, QtWidgets.QAbstractItemView.PositionAtCenter)

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
        pos = QtGui.QCursor().pos()
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

        pos = QtGui.QCursor().pos()
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

        cursor_position = self.mapFromGlobal(QtGui.QCursor().pos())
        index = self.indexAt(cursor_position)
        if not index.isValid():
            super(BaseInlineIconWidget, self).mousePressEvent(event)
            self.reset_multitoggle()
            return

        self.reset_multitoggle()

        rect = self.visualRect(index)
        rectangles = self.itemDelegate().get_rectangles(rect)

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
        """Finishes `BaseInlineIconWidget`'s multi-item toggle operation, and
        resets the associated variables.

        The inlince icon buttons are also triggered here. We're using the
        delegate's ``get_rectangles`` function to determine which icon was
        clicked.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            self.reset_multitoggle()
            return

        index = self.indexAt(event.pos())

        # Ending multi-toggle
        if self.multi_toggle_items:
            for n in self.multi_toggle_items:
                index = self.model().index(n, 0)

            self.reset_multitoggle()
            self.model().invalidateFilter()

            super(BaseInlineIconWidget, self).mouseReleaseEvent(event)
            return

        if not index.isValid():
            self.reset_multitoggle()
            super(BaseInlineIconWidget, self).mouseReleaseEvent(event)
            return

        # Responding the click-events based on the position:
        rect = self.visualRect(index)
        rectangles = self.itemDelegate().get_rectangles(rect)
        cursor_position = self.mapFromGlobal(QtGui.QCursor().pos())

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

        cursor_position = self.mapFromGlobal(QtGui.QCursor().pos())
        app = QtWidgets.QApplication.instance()
        index = self.indexAt(cursor_position)
        if not index.isValid():
            app.restoreOverrideCursor()
            return

        rectangles = self.itemDelegate().get_rectangles(self.visualRect(index))
        for k in (
                delegate.BookmarkPropertiesRect,
                delegate.AddAssetRect,
                delegate.DataRect,
                delegate.TodoRect,
                delegate.RevealRect,
                delegate.ArchiveRect,
                delegate.FavouriteRect):
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
            common.Log.error(u'Multitoggle failed')
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
        from bookmarks.preferenceswidget import PreferencesWidget
        widget = PreferencesWidget(parent=self)
        self.resized.connect(widget.setGeometry)
        widget.finished.connect(widget.deleteLater)
        widget.open()

    @QtCore.Slot(QtCore.QModelIndex)
    def show_slacker(self, index):
        if not index.isValid():
            return
        try:
            import bookmarks.slacker as slacker
        except ImportError as err:
            common_ui.ErrorBox(
                u'Could not import SlackClient',
                u'The Slack API python module was not loaded:\n{}'.format(err),
                parent=self
            ).open()
            common.Log.error(u'Slack import error.')
            raise

        try:
            db = bookmark_db.get_db(index)
            token = db.value(0, u'slacktoken', table=u'properties')
        except Exception as e:
            common.Log.error(u'Could not open Slacker')
            common.ErrorBox(
                u'Could not open Slacker',
                u'{}'.format(e),
                parent=self
            ).open()
            raise

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
            common.Log.error(u'Invalid token')
            raise

    @QtCore.Slot()
    def start_requestinfo_timers(self):
        pass

    @QtCore.Slot()
    def queue_model_data(self):
        pass

    @QtCore.Slot()
    def request_visible_fileinfo_load(self):
        pass

    @QtCore.Slot()
    def request_visible_thumbnail_load(self):
        pass


class ThreadedBaseWidget(BaseInlineIconWidget):
    """Adds the methods needed to push the indexes to the thread-workers."""

    def __init__(self, parent=None):
        super(ThreadedBaseWidget, self).__init__(parent=parent)

        self.queue_model_timer = QtCore.QTimer(parent=self)
        self.queue_model_timer.setSingleShot(True)
        self.queue_model_timer.setInterval(250)

        self.request_visible_fileinfo_timer = QtCore.QTimer(parent=self)
        self.request_visible_fileinfo_timer.setSingleShot(True)
        self.request_visible_fileinfo_timer.setInterval(100)

        self.request_visible_thumbnail_timer = QtCore.QTimer(parent=self)
        self.request_visible_thumbnail_timer.setSingleShot(True)
        self.request_visible_thumbnail_timer.setInterval(200)

        self.connect_thread_signals()

    def connect_thread_signals(self):
        # Connect signals
        proxy = self.model()
        model = proxy.sourceModel()
        cnx_type = QtCore.Qt.AutoConnection

        # Empty the queue when the data changes
        model.modelAboutToBeReset.connect(
            lambda: common.Log.debug('modelAboutToBeReset -> reset_thread_worker_queues', model))
        model.modelAboutToBeReset.connect(
            model.reset_thread_worker_queues, cnx_type)

        model.modelAboutToBeReset.connect(
            lambda: common.Log.debug('modelAboutToBeReset -> reset_file_info_loaded', model))
        model.modelAboutToBeReset.connect(
            model.reset_file_info_loaded, cnx_type)

        self.request_visible_fileinfo_timer.timeout.connect(
            lambda: common.Log.debug('timeout -> request_visible_fileinfo_load', self.request_visible_fileinfo_timer))
        self.request_visible_fileinfo_timer.timeout.connect(
            self.request_visible_fileinfo_load, cnx_type)

        self.request_visible_thumbnail_timer.timeout.connect(
            lambda: common.Log.debug('timeout -> request_visible_thumbnail_load', self.request_visible_thumbnail_timer))
        self.request_visible_thumbnail_timer.timeout.connect(
            self.request_visible_thumbnail_load, cnx_type)

        # Start / Stop request info timers
        model.modelAboutToBeReset.connect(
            lambda: common.Log.debug('modelAboutToBeReset -> stop_requestinfo_timers', model))
        model.modelAboutToBeReset.connect(
            self.stop_requestinfo_timers, cnx_type)
        model.modelReset.connect(
            lambda: common.Log.debug('modelReset -> start_requestinfo_timers', model))
        model.modelReset.connect(
            self.start_requestinfo_timers, cnx_type)

        # Filter changed
        proxy.filterTextChanged.connect(
            lambda: common.Log.debug('filterTextChanged -> start_requestinfo_timers', proxy))
        proxy.filterTextChanged.connect(
            self.start_requestinfo_timers, cnx_type)
        proxy.filterFlagChanged.connect(
            lambda: common.Log.debug('filterFlagChanged -> start_requestinfo_timers', proxy))
        proxy.filterFlagChanged.connect(
            self.start_requestinfo_timers, cnx_type)

        # Slider - Pressed / Released
        model.modelAboutToBeReset.connect(
            lambda: self.verticalScrollBar().blockSignals(True))
        model.modelReset.connect(
            lambda: self.verticalScrollBar().blockSignals(False))

        self.verticalScrollBar().sliderPressed.connect(
            lambda: common.Log.debug('sliderPressed -> reset_thread_worker_queues', self.verticalScrollBar()))
        self.verticalScrollBar().sliderPressed.connect(
            model.reset_thread_worker_queues)
        self.verticalScrollBar().sliderPressed.connect(
            lambda: common.Log.debug('sliderPressed -> stop_requestinfo_timers', self.verticalScrollBar()))
        self.verticalScrollBar().sliderPressed.connect(
            self.stop_requestinfo_timers)

        self.verticalScrollBar().sliderReleased.connect(
            lambda: common.Log.debug('sliderReleased -> reset_thread_worker_queues', self.verticalScrollBar()))
        self.verticalScrollBar().sliderReleased.connect(
            model.reset_thread_worker_queues)
        self.verticalScrollBar().sliderReleased.connect(
            lambda: common.Log.debug('sliderReleased -> start_requestinfo_timers', self.verticalScrollBar()))
        self.verticalScrollBar().sliderReleased.connect(
            self.start_requestinfo_timers)

        self.verticalScrollBar().valueChanged.connect(
            lambda: common.Log.debug('valueChanged -> start_requestinfo_timers', self.verticalScrollBar()))
        self.verticalScrollBar().valueChanged.connect(
            self.start_requestinfo_timers, cnx_type)

        # Thread update signals
        for k in model.threads:
            for thread in model.threads[k]:
                model.modelAboutToBeReset.connect(
                    lambda: common.Log.debug('modelAboutToBeReset -> stopTimer', model))
                model.modelAboutToBeReset.connect(
                    partial(thread.stopTimer.emit))
                model.modelAboutToBeReset.connect(
                    partial(thread.worker.resetQueue.emit))

                model.modelReset.connect(
                    lambda: common.Log.debug('modelReset -> startTimer', model))
                model.modelReset.connect(partial(thread.startTimer.emit))

        # Queue model data
        self.queue_model_timer.timeout.connect(self.queue_model_data)

        model.modelAboutToBeReset.connect(
            lambda: common.Log.debug('modelAboutToBeReset -> queue_model_timer.stop', model))
        model.modelAboutToBeReset.connect(
            self.queue_model_timer.stop, cnx_type)

        model.modelReset.connect(
            lambda: common.Log.debug('modelReset -> queue_model_timer.start', model))
        model.modelReset.connect(self.queue_model_timer.start)

        model.modelReset.connect(
            lambda: self.verticalScrollBar().valueChanged.emit(self.verticalScrollBar().value()))

    @QtCore.Slot()
    def start_requestinfo_timers(self):
        """Fires the timer responsible for updating the visible model indexes on
        a threaded viewer.

        """
        if self.verticalScrollBar().isSliderDown():
            return

        model = self.model().sourceModel()

        for thread in model.threads[common.InfoThread]:
            thread.startTimer.emit()
        for thread in model.threads[common.ThumbnailThread]:
            thread.startTimer.emit()

        common.Log.debug('start()', self.request_visible_fileinfo_timer)
        self.request_visible_fileinfo_timer.start(
            self.request_visible_fileinfo_timer.interval())

        common.Log.debug('start()', self.request_visible_thumbnail_timer)
        self.request_visible_thumbnail_timer.start(
            self.request_visible_thumbnail_timer.interval())

    @QtCore.Slot()
    def stop_requestinfo_timers(self):
        """Fires the timer responsible for updating the visible model indexes on
        a threaded viewer.

        """
        model = self.model().sourceModel()

        for thread in model.threads[common.InfoThread]:
            thread.stopTimer.emit()
            thread.worker.resetQueue.emit()
        for thread in model.threads[common.ThumbnailThread]:
            thread.stopTimer.emit()
            thread.worker.resetQueue.emit()

        common.Log.debug('stop()', self.request_visible_fileinfo_timer)
        self.request_visible_fileinfo_timer.stop()

        common.Log.debug('stop()', self.request_visible_thumbnail_timer)
        self.request_visible_thumbnail_timer.stop()

    @QtCore.Slot()
    def queue_model_data(self):
        """Queues the model data for the BackgroundInfoThread to process."""
        common.Log.debug('queue_model_data()', self)

        model = self.model().sourceModel()
        threads = model.threads[common.BackgroundInfoThread]
        if not threads:
            return

        k = model.data_key()
        if model.data_type() == common.FileItem:
            ts = (common.FileItem, common.SequenceItem)
        else:
            ts = (common.SequenceItem, common.FileItem)

        if k not in model.INTERNAL_MODEL_DATA:
            common.Log.debug('{} was not in the model'.format(k))
            return

        for _t in ts:
            if _t not in model.INTERNAL_MODEL_DATA[k]:
                continue
            ref = weakref.ref(model.INTERNAL_MODEL_DATA[k][_t])
            threads[0].put(ref)

    @QtCore.Slot()
    def request_visible_fileinfo_load(self):
        """The sourceModel() loads its data in multiples steps: There's a
        single-threaded walk of all sub-directories, and a threaded query for
        image and file information. This method is responsible for passing the
        indexes to the threads so they can update the model accordingly.

        """
        common.Log.debug('request_visible_fileinfo_load()', self)

        if not self.isVisible():
            return

        try:
            proxy = self.model()
            model = proxy.sourceModel()
            data = model.model_data()

            if not proxy.rowCount():
                return

            r = self.viewport().rect()
            index = self.indexAt(r.topLeft())
            if not index.isValid():
                return

            rect = self.visualRect(index)
            i = 0
            icount = len(model.threads[common.InfoThread])
            while r.intersects(rect):
                source_index = proxy.mapToSource(index)
                ref = weakref.ref(data[source_index.row()])

                info_loaded = index.data(common.FileInfoLoaded)
                if icount and not info_loaded:
                    model.threads[common.InfoThread][i % icount].put(ref)
                    i += 1
                rect.moveTop(rect.top() + rect.height())
                index = self.indexAt(rect.topLeft())
                if not index.isValid():
                    break
        except:
            common.Log.error('request_visible_fileinfo_load() failed')
        finally:
            for k in model.threads:
                for thread in model.threads[k]:
                    common.Log.debug('thread.startTimer.emit()', self)
                    thread.startTimer.emit()

    @QtCore.Slot()
    def request_visible_thumbnail_load(self):
        """The sourceModel() loads its data in multiples steps: There's a
        single-threaded walk of all sub-directories, and a threaded query for
        image and file information. This method is responsible for passing the
        indexes to the threads so they can update the model accordingly.

        """
        common.Log.debug('request_visible_thumbnail_load()', self)

        if not self.isVisible():
            return

        try:
            proxy = self.model()
            model = proxy.sourceModel()
            data = model.model_data()
            if not proxy.rowCount():
                return

            r = self.viewport().rect()
            index = self.indexAt(r.topLeft())
            if not index.isValid():
                return

            rect = self.visualRect(index)
            t = 0
            tcount = len(model.threads[common.ThumbnailThread])
            show_archived = proxy.filter_flag(common.MarkedAsArchived)
            # Starting from the top left iterate over valid indexes
            while r.intersects(rect):
                # If the item is archived but the `show_archived` flag is `False`,
                # we'll interrupt and invalidate the proxy filter
                is_archived = index.flags() & common.MarkedAsArchived
                if show_archived is False and is_archived:
                    proxy.invalidateFilter()
                    return

                source_index = proxy.mapToSource(index)
                if source_index.row() not in data:
                    continue

                ref = weakref.ref(data[source_index.row()])

                info_loaded = index.data(common.FileInfoLoaded)
                thumb_loaded = index.data(common.FileThumbnailLoaded)

                if model.generate_thumbnails_enabled():
                    if tcount and info_loaded and not thumb_loaded:
                        model.threads[common.ThumbnailThread][t %
                                                              tcount].put(ref)
                        t += 1

                rect.moveTop(rect.top() + rect.height())
                index = self.indexAt(rect.topLeft())
                if not index.isValid():
                    break
        except:
            common.Log.error('request_visible_thumbnail_load() failed')
        finally:
            # Thread update signals
            for k in model.threads:
                for thread in model.threads[k]:
                    common.Log.debug('thread.startTimer.emit()', self)
                    thread.startTimer.emit()

    def showEvent(self, event):
        super(ThreadedBaseWidget, self).showEvent(event)
        self.request_visible_fileinfo_load()
        self.request_visible_thumbnail_load()


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
