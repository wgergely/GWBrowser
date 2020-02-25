# -*- coding: utf-8 -*-
"""GWBrowser is built around the three main lists - **bookmarks**, **assets**
and **files**. Each of these lists has a *view*, *model* and *context menus*
stemming from the *BaseModel*, *BaseView* and *BaseContextMenu* classes defined
in ``baselistwidget.py`` and ``basecontextmenu.py`` modules.

The *BaseListWidget* subclasses are then added to the layout of **StackedWidget**,
the widget used to switch between the lists.

"""
import re
import time
import sys
import traceback
import weakref
from functools import wraps, partial

from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser.bookmark_db as bookmark_db
import gwbrowser.common as common
from gwbrowser.common import Log
import gwbrowser.editors as editors
from gwbrowser.basecontextmenu import BaseContextMenu
import gwbrowser.delegate as delegate
import gwbrowser.settings as settings_
from gwbrowser.imagecache import ImageCache
import gwbrowser.threads as threads


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
            func(self, *args, **kwargs)
            # sort_data emits the reset signals already
            self.blockSignals(True)
            self.sort_data()
            self.blockSignals(False)
            self.endResetModel()
            Log.success('__initdata__ finished')
        except:
            Log.error(u'Error loading the model data')
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
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )
        self._message = u'!!!Loading...'

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
            common.PrimaryFont,
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
        rect.setHeight(2)
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

        Log.success('FilterProxyModel initiated.')

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
        self._filter_text = settings_.local_settings.value(
            u'widget/{}/{}/filtertext'.format(cls, data_key))

        self._filterflags = {
            common.MarkedAsActive: settings_.local_settings.value(
                u'widget/{}/filterflag{}'.format(cls, common.MarkedAsActive)),
            common.MarkedAsArchived: settings_.local_settings.value(
                u'widget/{}/filterflag{}'.format(cls, common.MarkedAsArchived)),
            common.MarkedAsFavourite: settings_.local_settings.value(
                u'widget/{}/filterflag{}'.format(cls, common.MarkedAsFavourite)),
        }

        if self._filterflags[common.MarkedAsActive] is None:
            self._filterflags[common.MarkedAsActive] = False
        if self._filterflags[common.MarkedAsArchived] is None:
            self._filterflags[common.MarkedAsArchived] = False
        if self._filterflags[common.MarkedAsFavourite] is None:
            self._filterflags[common.MarkedAsFavourite] = False

        Log.debug('initialize_filter_values()', self)

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
        local_val = settings_.local_settings.value(k)
        if val == self._filter_text == local_val:
            return

        self._filter_text = val
        settings_.local_settings.setValue(k, val)

    def filter_flag(self, flag):
        """Returns the current flag-filter."""
        return self._filterflags[flag]

    @QtCore.Slot(int, bool)
    def set_filter_flag(self, flag, val):
        if self._filterflags[flag] == val:
            return

        self._filterflags[flag] = val

        cls = self.sourceModel().__class__.__name__
        settings_.local_settings.setValue(
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
            filtertext = filtertext.lower()
            searchable = data[QtCore.Qt.StatusTipRole] + u' ' + \
                data[common.DescriptionRole] + u' ' + \
                data[common.FileDetailsRole]

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
        _filtertext = unicode(filtertext)
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

    messageChanged = QtCore.Signal(unicode)
    # updateIndex = QtCore.Signal(QtCore.QModelIndex)
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

        self.sortingChanged.connect(set_sorting)
        self.sortingChanged.connect(
            lambda: Log.debug('sortingChanged -> set_sorting', self))

        self.initialize_default_sort_values()
        self.__init_threads__()

    def initialize_default_sort_values(self):
        """Loads the saved sorting values from the local preferences.

        """
        cls = self.__class__.__name__
        k = u'widget/{}/sortrole'.format(cls)
        val = settings_.local_settings.value(k)
        if val not in (common.SortByName, common.SortBySize, common.SortByLastModified):
            val = common.SortByName
        self._sortrole = val

        k = u'widget/{}/sortorder'.format(cls)
        val = settings_.local_settings.value(k)
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
        Log.success('Sort role saved <{}>'.format(val))
        if val == self.sort_role():
            return

        self._sortrole = val
        cls = self.__class__.__name__
        settings_.local_settings.setValue(
            u'widget/{}/sortrole'.format(cls), val)

    def sort_order(self):
        """The currently set order of the items eg. 'descending'."""
        return self._sortorder

    @QtCore.Slot(int)
    def set_sort_order(self, val):
        """Sets and saves the sort-key."""
        Log.success('Sort order saved <{}>'.format(val))
        if val == self.sort_order():
            return

        self._sortorder = val
        cls = self.__class__.__name__
        settings_.local_settings.setValue(
            u'widget/{}/sortorder'.format(cls), val)

    @QtCore.Slot()
    def sort_data(self):
        """Sorts the internal `INTERNAL_MODEL_DATA`. Emits

        """
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

        self.beginResetModel()
        self.INTERNAL_MODEL_DATA[k][t] = d
        self.endResetModel()
        Log.success(u'sort_data()')

    @QtCore.Slot(QtCore.QModelIndex)
    def set_active(self, index):
        """This is a slot, setting the parent of the model.

        Parent refers to the search path the model will get it's data from. It
        us usually contained in the `common.ParentPathRole` data with the exception
        of the bookmark items - we don't have parent for these.

        """
        if not index.isValid():
            self.parent_path = None
            return

        self.parent_path = index.data(common.ParentPathRole)

    def __resetdata__(self):
        """Resets the internal data."""
        self.INTERNAL_MODEL_DATA = common.DataDict()
        Log.success('__resetdata__')
        self.__initdata__()

    def __initdata__(self):
        raise NotImplementedError(
            u'__initdata__ is abstract and must be overriden')

    def __init_threads__(self):
        """Starts and connects the threads."""
        @QtCore.Slot(QtCore.QThread)
        def thread_started(thread):
            """Signals the model an item has been updated."""
            thread.worker.dataReady.connect(self.updateRow, QtCore.Qt.QueuedConnection)

        worker = threads.InfoWorker()
        thread = threads.BaseThread(worker, interval=40)
        self.threads[common.InfoThread].append(thread)
        thread.started.connect(partial(thread_started, thread))
        thread.start()

        worker = threads.BackgroundInfoWorker()
        thread = threads.BaseThread(worker, interval=260)
        self.threads[common.BackgroundInfoThread].append(thread)
        thread.started.connect(partial(thread_started, thread))
        thread.start()

        worker = threads.ThumbnailWorker()
        thread = threads.BaseThread(worker, interval=40)
        self.threads[common.ThumbnailThread].append(thread)
        thread.started.connect(partial(thread_started, thread))
        thread.start()


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
        for k in self.threads:
            for thread in self.threads[k]:
                thread.worker.resetQueue.emit()
        Log.info('reset_thread_worker_queues')

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
            return
        if index.row() not in self.model_data():
            return None
        self.model_data()[index.row()][role] = data
        self.dataChanged.emit(index, index)

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
            val = settings_.local_settings.value(key)
            val = val if val else common.SequenceItem
            self._datatype[data_key] = val
        return self._datatype[data_key]

    @QtCore.Slot(int)
    def set_data_type(self, val):
        """Sets the data type to `FileItem` or `SequenceItem`."""
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
            settings_.local_settings.save_state(u'location', val)
            settings_.local_settings.setValue(key, val)
            self._datatype[data_key] = val

            Log.success('Data type set <"{}">'.format(val))
        except:
            Log.error('Error setting data key')
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
    resized = QtCore.Signal(QtCore.QRect)
    SourceModel = None

    Delegate = None
    ContextMenu = None

    def __init__(self, parent=None):
        super(BaseListWidget, self).__init__(parent=parent)
        self.progress_widget = ProgressWidget(parent=self)
        self.progress_widget.setHidden(True)
        self.filter_active_widget = FilterOnOverlayWidget(parent=self)
        self.filter_editor = editors.FilterEditor(parent=self)
        self.filter_editor.setHidden(True)

        self.thumbnail_viewer_widget = None
        self.description_editor_widget = editors.DescriptionEditorWidget(
            parent=self)
        self.description_editor_widget.setHidden(True)

        k = u'widget/{}/buttons_hidden'.format(self.__class__.__name__)
        self._buttons_hidden = False if settings_.local_settings.value(
            k) is None else settings_.local_settings.value(k)

        # Keyboard search timer and placeholder string.
        self.timer = QtCore.QTimer(parent=self)
        self.timer.setInterval(
            QtWidgets.QApplication.instance().keyboardInputInterval())
        self.timer.setSingleShot(True)
        self.timed_search_string = u''

        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setUniformItemSizes(True)
        self.setTextElideMode(QtCore.Qt.ElideNone)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
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

        self.set_model(self.SourceModel(parent=self))
        self.setItemDelegate(self.Delegate(parent=self))

        self.resized.connect(self.filter_active_widget.setGeometry)
        self.resized.connect(self.progress_widget.setGeometry)

    def buttons_hidden(self):
        """Returns the visibility of the inline icon buttons."""
        return self._buttons_hidden

    def set_buttons_hidden(self, val):
        """Sets the visibility of the inline icon buttons."""
        cls = self.__class__.__name__
        k = u'widget/{}/buttons_hidden'.format(cls)
        settings_.local_settings.setValue(k, val)
        self._buttons_hidden = val

    def set_model(self, model):
        """This is the main port of entry for the model.

        The BaseModel subclasses are wrapped in a QSortFilterProxyModel. All
        the necessary internal signal-slot connections needed for the proxy, model
        and the view comminicate properly are made here.

        Note:
            The bulk of the signal are connected together in ``BrowserWidget``'s
            *_connectSignals* method.

        """
        proxy = FilterProxyModel(parent=self)
        proxy.setSourceModel(model)

        self.blockSignals(True)
        self.setModel(proxy)
        self.blockSignals(False)

        model.modelAboutToBeReset.connect(
            lambda: Log.debug('<<< modelAboutToBeReset >>>', model))
        model.modelReset.connect(
            lambda: Log.debug('<<< modelReset >>>', model))

        model.modelDataResetRequested.connect(model.__resetdata__)
        model.modelDataResetRequested.connect(
            lambda: Log.debug('modelDataResetRequested -> __resetdata__', model))

        model.activeChanged.connect(self.save_activated)
        model.activeChanged.connect(
            lambda: Log.debug('activeChanged -> save_activated', model))

        # Data key, eg. 'scenes'
        model.dataKeyChanged.connect(model.set_data_key)
        model.dataKeyChanged.connect(proxy.invalidate)
        model.dataKeyChanged.connect(
            lambda: Log.debug('dataKeyChanged -> set_data_key', model))
        # FileItem/SequenceItem
        model.dataTypeChanged.connect(model.set_data_type)
        model.dataTypeChanged.connect(proxy.invalidate)
        model.dataTypeChanged.connect(
            lambda: Log.debug('dataTypeChanged -> set_data_type', model))

        proxy.filterTextChanged.connect(proxy.set_filter_text)
        proxy.filterTextChanged.connect(
            lambda: Log.debug('filterTextChanged -> set_filter_text', proxy))
        proxy.filterFlagChanged.connect(proxy.set_filter_flag)
        proxy.filterFlagChanged.connect(
            lambda: Log.debug('filterFlagChanged -> set_filter_flag', proxy))
        proxy.filterTextChanged.connect(proxy.invalidateFilter)
        proxy.filterTextChanged.connect(
            lambda: Log.debug('filterTextChanged -> invalidateFilter', proxy))
        proxy.filterFlagChanged.connect(proxy.invalidateFilter)
        proxy.filterFlagChanged.connect(
            lambda: Log.debug('filterFlagChanged -> invalidateFilter', proxy))

        model.modelAboutToBeReset.connect(self.reset_multitoggle)
        model.modelAboutToBeReset.connect(
            lambda: Log.debug('modelAboutToBeReset -> reset_multitoggle', model))

        self.filter_editor.finished.connect(proxy.filterTextChanged)
        self.filter_editor.finished.connect(
            lambda: Log.debug('finished -> filterTextChanged', self.filter_editor))

        # model.updateIndex.connect(
        #     self.update, type=QtCore.Qt.QueuedConnection)
        # model.updateIndex.connect(
        #     lambda: Log.debug('updateIndex -> update', model))

        # model.modelReset.connect(proxy.invalidateFilter)
        model.modelReset.connect(
            lambda: Log.debug('modelReset -> proxy.invalidateFilter', model))
        model.modelReset.connect(self.reselect_previous)
        model.modelReset.connect(
            lambda: Log.debug('modelReset -> reselect_previous', model))

        model.updateRow.connect(self.update_row)
        proxy.initialize_filter_values()

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
        if not ref():
            return
        if self.isHidden():
            return
        model = self.model()
        index = model.sourceModel().index(ref()[common.IdRole], 0)
        index = model.mapFromSource(index)
        super(BaseListWidget, self).update(index)
        common.Log.debug('Row {} repainted'.format(index.row()))

    def initialize_visible_indexes(self):
        pass

    def activate(self, index):
        """Marks the given index by adding the ``MarkedAsActive`` flag.

        If the item has already been activated it will emit the activated signal.
        This is used to switch tabs. If the item is not active yet, it will
        apply the active flag and emit the ``activeChanged`` signal.

        Note:
            The method emits the ``activeChanged`` signal but itself does not
            save the change to the settings_.local_settings. That is handled by connections
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

        source_index.model().activeChanged.emit(source_index)
        self.update(index)

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

    @staticmethod
    def _get_path(v):
        is_collapsed = common.is_collapsed(v)
        is_sequence = common.get_sequence(v)

        if is_collapsed:
            v = is_collapsed.group(1) + u'[0]' + is_collapsed.group(3)
        elif is_sequence:
            v = is_sequence.group(1) + u'[0]' + is_sequence.group(3) + u'.' + is_sequence.group(4)
        return v

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
        v = self._get_path(index.data(QtCore.Qt.StatusTipRole))
        settings_.local_settings.setValue(k, v)

    @QtCore.Slot()
    def reselect_previous(self):
        """Slot called when the model has finished a reset operation.
        The method will try to reselect the previously selected path."""
        cls = self.__class__.__name__
        k = u'widget/{}/{}/selected_item'.format(
            cls,
            self.model().sourceModel().data_key(),
        )
        val = settings_.local_settings.value(k)

        if not val:
            return


        proxy = self.model()
        for n in xrange(proxy.rowCount()):
            index = proxy.index(n, 0)
            path = self._get_path(index.data(QtCore.Qt.StatusTipRole))
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

    def toggle_item_flag(self, index, flag, state=None, repaint=False):
        """Sets the index's `flag` value based `state`.

        We're using this mark items archived, or favourite and save the changes
        to the database or the local config file.

        Args:
            index (QModelIndex): The index containing the
            flag (type): Description of parameter `flag`.
            state (type): Description of parameter `state`. Defaults to None.
            repaint (type): Description of parameter `repaint`. Defaults to False.

        Returns:
            unicode: The key used to find and match items.

        """
        def _func(mode, data, flag):
            pass

        def save_to_db(k, mode, flag):
            """Save the value to the database."""
            db = bookmark_db.get_db(index)
            if not db:
                raise RuntimeError(u'Could not open database.')
            with db.transactions():
                f = db.value(k, u'flags')
                f = 0 if f is None else f
                f = f | flag if mode else f & ~flag
                db.setValue(k, u'flags', f)

        def save_to_local_settings(k, mode, flag):
            favourites = settings_.local_settings.favourites()
            sfavourites = set(favourites)
            if mode:
                favourites.append(k)
            else:
                if k.lower() in sfavourites:
                    favourites.remove(k)

            v = sorted(list(set(favourites)))
            settings_.local_settings.setValue(u'favourites', v)

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
                k = data[common.SequenceRole]
                if not k:
                    continue
                k = k.group(1) + u'[0]' + k.group(3) + u'.' + k.group(4)
                if sequence_key != k:
                    continue
                _set_flag(k, mode, data, flag, commit=False)

        if not index.isValid():
            return

        if hasattr(index.model(), 'sourceModel'):
            source_index = self.model().mapToSource(index)

        if not index.data(common.FileInfoLoaded):
            return

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
            k = data[common.SequenceRole]
            k = k.group(1) + u'[0]' + k.group(3) + u'.' + k.group(4)
        else:
            k = data[QtCore.Qt.StatusTipRole]

        _set_flag(k, mode, data, flag, commit=True)

        if data[common.SequenceRole]:
            _set_flags(FILE_DATA.itervalues(), k, mode, flag)
            _set_flags(SEQ_DATA.itervalues(), k, mode, flag)

        self.repaint()
        return k

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

        if no_modifier or numpad_modifier:
            if event.key() == QtCore.Qt.Key_Space:
                if index.isValid():
                    if not self.thumbnail_viewer_widget:
                        editors.ThumbnailViewer(parent=self)
                    else:
                        self.thumbnail_viewer_widget.close()
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
                    if event.modifiers() & QtCore.Qt.ShiftModifier:
                        return common.copy_path(index, mode=common.UnixPath, first=True)
                    return common.copy_path(index, mode=mode, first=False)

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

    def contextMenuEvent(self, event):
        """Custom context menu event."""
        index = self.indexAt(event.pos())

        width = self.viewport().geometry().width()
        width = (width * 0.5) if width > 400 else width
        width = width - common.INDICATOR_WIDTH

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

        widget.move(widget.x() + common.INDICATOR_WIDTH, widget.y())
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
            return self.description_editor_widget.show()

        if rectangles[delegate.DataRect].contains(cursor_position):
            return self.activate(self.selectionModel().currentIndex())

        if rectangles[delegate.ThumbnailRect].contains(cursor_position):
            return ImageCache.pick(index)

    def paint_status_message(self, widget, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        proxy = self.model()
        model = proxy.sourceModel()
        filter_text = proxy.filter_text()

        sizehint = self.itemDelegate().sizeHint(
            self.viewOptions(), QtCore.QModelIndex())

        rect = self.rect()
        center = rect.center()
        rect.setWidth(rect.width() - common.MARGIN)
        rect.moveCenter(center)

        favourite_mode = proxy.filter_flag(common.MarkedAsFavourite)
        active_mode = proxy.filter_flag(common.MarkedAsActive)

        text_rect = QtCore.QRect(rect)
        text_rect.setHeight(sizehint.height())

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        painter.setPen(QtCore.Qt.NoPen)
        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSizeF(common.MEDIUM_FONT_SIZE - 1)
        align = QtCore.Qt.AlignCenter

        text = u''
        if not model.parent_path and self.parent():
            if self.parent().currentIndex() == 0:
                if model.rowCount() == 0:
                    text = u'No bookmarks added yet. Click the plus icon above to get started.'
            elif self.parent().currentIndex() == 1:
                text = u'Assets will be shown here once a bookmark is activated.'
            elif self.parent().currentIndex() == 2:
                text = u'Files will be shown here once an asset is activated.'
            elif self.parent().currentIndex() == 3:
                text = u'You don\'t have any favourites yet.'

            common.draw_aliased_text(
                painter, font, rect, text, align, common.TEXT_DISABLED)
            return True

        if not model.data_key() and self.parent():
            if self.parent().currentIndex() == 2:
                text = u'No task folder selected.'
                common.draw_aliased_text(
                    painter, font, text_rect, text, align, common.TEXT_DISABLED)
                return True

        if model.rowCount() == 0:
            text = u'No items to show.'
            common.draw_aliased_text(
                painter, font, text_rect, text, align, common.TEXT_DISABLED)
            return True

        for n in xrange((self.height() / sizehint.height()) + 1):
            if n >= model.rowCount():  # Empty items
                rect_ = QtCore.QRect(rect)
                rect_.setWidth(sizehint.height() - 2)

            if n == model.rowCount():  # filter mode
                hidden_count = model.rowCount() - model.rowCount()
                filtext = u''
                favtext = u''
                acttext = u''
                hidtext = u''

                if filter_text:
                    filtext = filter_text.upper()
                if favourite_mode:
                    favtext = u'Showing favourites only'
                if active_mode:
                    acttext = u'Showing active item only'
                if hidden_count:
                    hidtext = u'{} items are hidden'.format(hidden_count)
                text = [f for f in (
                    filtext, favtext, acttext, hidtext) if f]
                text = u'  |  '.join(text)
                common.draw_aliased_text(
                    painter, font, text_rect, text, align, common.SECONDARY_TEXT)

            text_rect.moveTop(text_rect.top() + sizehint.height())
            rect.moveTop(rect.top() + sizehint.height())

    def eventFilter(self, widget, event):
        if widget is not self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            self.paint_status_message(widget, event)
            return True
        return False

    def resizeEvent(self, event):
        self.resized.emit(self.viewport().geometry())


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
        raise NotImplementedError(
            u'inline_icons_count is abstract and must be overriden')

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
            self.multi_toggle_pos = cursor_position
            self.multi_toggle_state = not index.flags() & common.MarkedAsFavourite
            self.multi_toggle_idx = delegate.FavouriteRect

        if rectangles[delegate.ArchiveRect].contains(cursor_position):
            self.multi_toggle_pos = cursor_position
            self.multi_toggle_state = not index.flags() & common.MarkedAsArchived
            self.multi_toggle_idx = delegate.ArchiveRect

        super(BaseInlineIconWidget, self).mousePressEvent(event)

    def enterEvent(self, event):
        app = QtWidgets.QApplication.instance()
        app.restoreOverrideCursor()

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
            return None

        cursor_position = self.mapFromGlobal(QtGui.QCursor().pos())
        app = QtWidgets.QApplication.instance()
        index = self.indexAt(cursor_position)
        if not index.isValid():
            app.restoreOverrideCursor()
            return

        # if not self.verticalScrollBar().isSliderDown():
        #     self.update(index)

        rectangles = self.itemDelegate().get_rectangles(self.visualRect(index))
        for k in (delegate.BookmarkCountRect,
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
            return super(BaseInlineIconWidget, self).mouseMoveEvent(event)

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
            common.Log.error('Multitoggle failed')
        finally:
            self.update(index)

    def show_todos(self, index):
        """Shows the ``TodoEditorWidget`` for the current item."""
        from gwbrowser.todoEditor import TodoEditorWidget

        # Let's check if other editors are open and close them if so
        editors = [f for f in self.children() if isinstance(f,
                                                            TodoEditorWidget)]
        if editors:
            for editor in editors:
                editor.close()

        source_index = self.model().mapToSource(index)
        widget = TodoEditorWidget(source_index, parent=self)
        widget.show()


class ThreadedBaseWidget(BaseInlineIconWidget):
    """Adds the methods needed to push the indexes to the thread-workers."""

    def __init__(self, parent=None):
        super(ThreadedBaseWidget, self).__init__(parent=parent)
        self._generate_thumbnails_enabled = True

        self.scrollbar_changed_timer = QtCore.QTimer(parent=self)
        self.scrollbar_changed_timer.setSingleShot(True)
        self.scrollbar_changed_timer.setInterval(250)

        self.hide_archived_items_timer = QtCore.QTimer(parent=self)
        self.hide_archived_items_timer.setSingleShot(False)
        self.hide_archived_items_timer.setInterval(500)

        # Connect signals
        proxy = self.model()
        model = proxy.sourceModel()
        cnx_type = QtCore.Qt.AutoConnection

        # Empty the queue when the data changes
        model.modelAboutToBeReset.connect(
            model.reset_thread_worker_queues, cnx_type)
        model.modelAboutToBeReset.connect(
            lambda: Log.debug('modelAboutToBeReset -> reset_thread_worker_queues', model))

        model.modelReset.connect(
            model.reset_file_info_loaded, cnx_type)
        model.modelReset.connect(
            lambda: Log.debug('modelReset -> reset_file_info_loaded', model))

        self.hide_archived_items_timer.timeout.connect(
            self.hide_archived_items)
        # self.hide_archived_items_timer.timeout.connect(
        #     lambda: Log.debug('hide_archived_items_timer -> hide_archived_items', self))

        self.scrollbar_changed_timer.timeout.connect(
            self.initialize_visible_indexes, cnx_type)
        self.scrollbar_changed_timer.timeout.connect(
            lambda: Log.debug('timeout -> initialize_visible_indexes', self.scrollbar_changed_timer))

        self.verticalScrollBar().valueChanged.connect(
            self.restart_scrollbar_timer, cnx_type)
        self.verticalScrollBar().valueChanged.connect(
            lambda: Log.debug('valueChanged -> restart_scrollbar_timer', self.verticalScrollBar()))

        @QtCore.Slot()
        def stop_timers():
            self.hide_archived_items_timer.stop()
            self.scrollbar_changed_timer.stop()

        model.modelAboutToBeReset.connect(stop_timers, cnx_type)
        model.modelAboutToBeReset.connect(
            lambda: Log.debug('modelAboutToBeReset -> stop_timers', model))

        model.modelReset.connect(
            self.hide_archived_items_timer.start, cnx_type)
        model.modelReset.connect(
            lambda: Log.debug('modelReset -> hide_archived_items_timer.start', model))

        model.modelReset.connect(self.restart_scrollbar_timer, cnx_type)
        model.modelReset.connect(
            lambda: Log.debug('modelReset -> restart_scrollbar_timer', model))

        proxy.filterTextChanged.connect(self.restart_scrollbar_timer, cnx_type)
        proxy.filterTextChanged.connect(
            lambda: Log.debug('filterTextChanged -> restart_scrollbar_timer', proxy))
        proxy.filterFlagChanged.connect(self.restart_scrollbar_timer, cnx_type)
        proxy.filterFlagChanged.connect(
            lambda: Log.debug('filterFlagChanged -> restart_scrollbar_timer', proxy))

        self.scrollbar_changed_timer.timeout.connect(
            self.initialize_visible_indexes, cnx_type)
        self.scrollbar_changed_timer.timeout.connect(
            lambda: Log.debug('timeout -> initialize_visible_indexes', self.scrollbar_changed_timer))

        # Thread update signals
        for k in model.threads:
            for thread in model.threads[k]:
                model.modelAboutToBeReset.connect(thread.stopTimer)
                model.modelAboutToBeReset.connect(
                    lambda: Log.debug('modelAboutToBeReset -> thread.stopTimer', model))

                model.modelReset.connect(thread.startTimer)
                model.modelReset.connect(
                    lambda: Log.debug('modelAboutToBeReset -> thread.startTimer', model))

        model.modelReset.connect(self.queue_model_data)

        self.init_generate_thumbnails_enabled()

    def __init_threads__(self):
        """Starts and connects the threads."""
        @QtCore.Slot(QtCore.QThread)
        def thread_started(thread):
            """Signals the model an item has been updated."""
            thread.worker.dataReady.connect(self.updateRow, QtCore.Qt.QueuedConnection)

        worker = threads.InfoWorker()
        thread = threads.BaseThread(worker, interval=40)
        self.threads[common.InfoThread].append(thread)
        thread.started.connect(partial(thread_started, thread))
        thread.start()

        worker = threads.BackgroundInfoWorker()
        thread = threads.BaseThread(worker, interval=260)
        self.threads[common.BackgroundInfoThread].append(thread)
        thread.started.connect(partial(thread_started, thread))
        thread.start()

        worker = threads.ThumbnailWorker()
        thread = threads.BaseThread(worker, interval=40)
        self.threads[common.ThumbnailThread].append(thread)
        thread.started.connect(partial(thread_started, thread))
        thread.start()

    def init_generate_thumbnails_enabled(self):
        cls = self.__class__.__name__
        k = u'widget/{}/generate_thumbnails'.format(cls)
        v = settings_.local_settings.value(k)
        v = True if v is None else v
        self._generate_thumbnails_enabled = v

    def generate_thumbnails_enabled(self):
        return self._generate_thumbnails_enabled

    @QtCore.Slot(bool)
    def set_generate_thumbnails_enabled(self, val):
        cls = self.__class__.__name__
        k = u'widget/{}/generate_thumbnails'.format(cls)
        settings_.local_settings.setValue(k, val)
        self._generate_thumbnails_enabled = val

    @QtCore.Slot()
    def restart_scrollbar_timer(self):
        """Fires the timer responsible for updating the visible model indexes on
        a threaded viewer.

        """
        self.scrollbar_changed_timer.start(
            self.scrollbar_changed_timer.interval())

    @QtCore.Slot()
    def queue_model_data(self):
        """Queues the model data for the BackgroundInfoThread to process."""
        model = self.model().sourceModel()
        threads = model.threads[common.BackgroundInfoThread]
        if not threads:
            return

        k = model.data_key()
        if model.data_type() == common.FileItem:
            ts = (common.FileItem, common.SequenceItem)
        else:
            ts = (common.SequenceItem, common.FileItem)

        for _t in ts:
            ref = weakref.ref(model.INTERNAL_MODEL_DATA[k][_t])
            t = common.SequenceItem
            threads[0].put(ref)

    @QtCore.Slot()
    def hide_archived_items(self):
        if not self.isVisible():
            return
        app = QtWidgets.QApplication.instance()
        if app.mouseButtons() != QtCore.Qt.NoButton:
            return
        proxy = self.model()
        if not proxy.rowCount():
            return

        index = self.indexAt(self.rect().topLeft())
        if not index.isValid():
            return

        show_archived = proxy.filter_flag(common.MarkedAsArchived)
        rect = self.visualRect(index)
        while self.viewport().rect().intersects(rect):
            is_archived = index.flags() & common.MarkedAsArchived
            if not show_archived and is_archived:
                proxy.invalidateFilter()
                return

            rect.moveTop(rect.top() + rect.height())
            index = self.indexAt(rect.topLeft())

        # Here we add the last index of the window
        index = self.indexAt(self.rect().bottomLeft())
        if not index.isValid():
            return

        is_archived = index.flags() & common.MarkedAsArchived
        if not show_archived and is_archived:
            self.model().invalidateFilter()

    @QtCore.Slot()
    def initialize_visible_indexes(self):
        """The sourceModel() loads its data in multiples steps: There's a
        single-threaded walk of all sub-directories, and a threaded query for
        image and file information. This method is responsible for passing the
        indexes to the threads so they can update the model accordingly.

        """
        if not self.isVisible():
            return
        app = QtWidgets.QApplication.instance()
        if app.mouseButtons() != QtCore.Qt.NoButton:
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

            # Starting from the top left we'll get all visible indexes
            rect = self.visualRect(index)
            i = 0
            t = 0
            icount = len(model.threads[common.InfoThread])
            tcount = len(model.threads[common.ThumbnailThread])
            while r.intersects(rect):
                source_index = proxy.mapToSource(index)
                ref = weakref.ref(data[source_index.row()])

                if icount and not index.data(common.FileInfoLoaded):
                    model.threads[common.InfoThread][i % icount].put(ref)
                    i += 1
                if self.generate_thumbnails_enabled():
                    if tcount and not index.data(common.FileThumbnailLoaded):
                        model.threads[common.ThumbnailThread][t % tcount].put(ref)
                        t += 1

                rect.moveTop(rect.top() + rect.height())

                index = self.indexAt(rect.topLeft())
                if not index.isValid():
                    break

            # Here we add the last index of the window
            index = self.indexAt(self.rect().bottomLeft())
            if index.isValid():
                source_index = proxy.mapToSource(index)
                ref = weakref.ref(data[source_index.row()])
                if icount and not index.data(common.FileInfoLoaded):
                    model.threads[common.InfoThread][0].put(ref)
                if self.generate_thumbnails_enabled():
                    if tcount and not index.data(common.FileThumbnailLoaded):
                        model.threads[common.ThumbnailThread][t % tcount].put(ref)
        except:
            Log.error('initialize_visible_indexes failed')
        finally:
            common.Log.success('initialize_visible_indexes()')

    def showEvent(self, event):
        self.hide_archived_items_timer.start()
        super(ThreadedBaseWidget, self).showEvent(event)

    def hideEvent(self, event):
        self.hide_archived_items_timer.stop()
        super(ThreadedBaseWidget, self).hideEvent(event)


class StackedWidget(QtWidgets.QStackedWidget):
    """Stacked widget used to hold and toggle the list widgets containing the
    bookmarks, assets, files and favourites."""

    def __init__(self, parent=None):
        super(StackedWidget, self).__init__(parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
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
        def active_index(x): return self.widget(
            x).model().sourceModel().active_index()
        if not active_index(0).isValid() and idx in (1, 2):
            idx = 0

        # No active asset
        if active_index(0).isValid() and not active_index(1).isValid() and idx == 2:
            idx = 1

        if idx <= 3:
            k = u'widget/mode'
            settings_.local_settings.setValue(k, idx)

        super(StackedWidget, self).setCurrentIndex(idx)
