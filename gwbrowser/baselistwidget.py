# -*- coding: utf-8 -*-
"""GWBrowser is built around the three main lists - **bookmarks**, **assets**
and **files**. Each of these lists has a *view*, *model* and *context menus*
stemming from the *BaseModel*, *BaseView* and *BaseContextMenu* classes defined
in ``baselistwidget.py`` and ``basecontextmenu.py`` modules.

The *BaseListWidget* subclasses are then added to the layout of **StackedWidget**,
the widget used to switch between the lists.

"""

import re
import sys
import traceback
from functools import wraps

from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser.common as common
import gwbrowser.editors as editors
from gwbrowser.basecontextmenu import BaseContextMenu
import gwbrowser.delegate as delegate
from gwbrowser.settings import local_settings, AssetSettings
from gwbrowser.imagecache import ImageCache


def validate_index(func):
    """Decorator to validate an index"""
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        """This wrapper will make sure the passed parameters are ok to pass onto
        OpenImageIO. We will also update the index value here."""
        if not args[0].isValid():
            return None
        if not args[0].data(QtCore.Qt.StatusTipRole):
            return None
        if not args[0].data(common.ParentPathRole):
            return None
        if isinstance(args[0].model(), FilterProxyModel):
            args = [f for f in args]
            index = args.pop(0)
            args.insert(0, index.model().mapToSource(index))
            args = tuple(args)
        return func(*args, **kwargs)
    return func_wrapper


def initdata(func):
    """Decorator function to make sure ``endResetModel()`` is always called
    after the function finished running.

    """
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        try:
            res = func(self, *args, **kwargs)
        except:
            res = None
            sys.stderr.write(u'{}\n'.format(traceback.format_exc()))
        finally:
            self.endResetModel()

            # We won't be able to sort our model before the size and modified
            # dates are loaded by the Worker threads
            if self.sortRole()  == common.SortByName:
                self.sort_data()

        return res
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


class DisabledOverlayWidget(ProgressWidget):
    """Static overlay widget shown when there's a blocking window placed
    on top of the main widget.

    """

    def paintEvent(self, event):
        """Custom message painted here."""
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        color = QtGui.QColor(common.SEPARATOR)
        color.setAlpha(150)
        painter.setBrush(color)
        painter.drawRect(self.rect())
        painter.end()


class FilterOnOverlayWidget(ProgressWidget):
    """Static overlay widget shown when there's a blocking window placed
    on top of the main widget.

    """

    def paintEvent(self, event):
        """Custom message painted here."""
        if self.parent().model().rowCount() == self.parent().model().sourceModel().rowCount():
            return
        painter = QtGui.QPainter()
        painter.begin(self)
        rect = self.rect()
        rect.setHeight(1)
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
        self._filter_text = local_settings.value(
            u'widget/{}/{}/filtertext'.format(cls, data_key))

        self._filterflags = {
            common.MarkedAsActive: local_settings.value(
                u'widget/{}/filterflag{}'.format(cls, common.MarkedAsActive)),
            common.MarkedAsArchived: local_settings.value(
                u'widget/{}/filterflag{}'.format(cls, common.MarkedAsArchived)),
            common.MarkedAsFavourite: local_settings.value(
                u'widget/{}/filterflag{}'.format(cls, common.MarkedAsFavourite)),
        }

        if self._filterflags[common.MarkedAsActive] is None:
            self._filterflags[common.MarkedAsActive] = False
        if self._filterflags[common.MarkedAsArchived] is None:
            self._filterflags[common.MarkedAsArchived] = False
        if self._filterflags[common.MarkedAsFavourite] is None:
            self._filterflags[common.MarkedAsFavourite] = False

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
        local_val = local_settings.value(k)
        if val == self._filter_text == local_val:
            return

        self._filter_text = val
        local_settings.setValue(k, val)

    def filterFlag(self, flag):
        """Returns the current flag-filter."""
        return self._filterflags[flag]

    @QtCore.Slot(int, bool)
    def set_filter_flag(self, flag, val):
        if self._filterflags[flag] == val:
            return

        self._filterflags[flag] = val

        cls = self.sourceModel().__class__.__name__
        local_settings.setValue(
            u'widget/{}/filterflag{}'.format(cls, flag), val)

    def filterAcceptsColumn(self, source_column, parent=QtCore.QModelIndex()):
        return True

    def filterAcceptsRow(self, source_row, parent=None):
        """The main method responsible for filtering rows in the proxy model.
        Most filtering happens via the user-inputted filter string."""

        data = self.sourceModel().model_data()
        if source_row not in data:
            return False

        flags = data[source_row][common.FlagsRole]
        archived = flags & common.MarkedAsArchived
        favourite = flags & common.MarkedAsFavourite
        active = flags & common.MarkedAsActive

        filtertext = self.filter_text()
        if filtertext:
            filtertext = filtertext.lower()
            searchable = u'{} {} {}'.format(
                data[source_row][QtCore.Qt.StatusTipRole],
                data[source_row][common.DescriptionRole],
                data[source_row][common.FileDetailsRole]
            ).lower()

            if not self.filter_includes_row(filtertext, searchable):
                return False
            if self.filter_excludes_row(filtertext, searchable):
                return False

        if self.filterFlag(common.MarkedAsActive) and active:
            return True
        if self.filterFlag(common.MarkedAsActive) and not active:
            return False
        if archived and not self.filterFlag(common.MarkedAsArchived):
            return False
        if not favourite and self.filterFlag(common.MarkedAsFavourite):
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


class BaseModel(QtCore.QAbstractItemModel):
    """The base model for storing bookmarks, assets and files.

    The model stores its data in the **self._data** private dictionary.
    The structure of the data is uniform accross all BaseModel instances but it
    really is built around storing file-data.

    Each folder in the assets folder corresponds to a **data_key**.

    A data-key example:
        .. code-block:: python

            self._data = {}
            # will most of the time return a name of a folder, eg. 'scenes'
            datakey = self.data_key()
            self._data[datakey] = {
                common.FileItem: {}, common.SequenceItem: {}}

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
    dataSorted = QtCore.Signal()  # (SortRole, SortOrder)

    messageChanged = QtCore.Signal(unicode)
    updateIndex = QtCore.Signal(QtCore.QModelIndex)

    # Threads
    InfoThread = None
    SecondaryInfoThread = None
    ThumbnailThread = None

    def __init__(self, thread_count=common.FTHREAD_COUNT, parent=None):
        super(BaseModel, self).__init__(parent=parent)
        self.view = parent
        self.active = QtCore.QModelIndex()

        self.thread_count = thread_count
        self.threads = {}
        self.file_info_loaded = False

        self._proxy_idxs = {}
        self._data = {}
        self._datakey = None
        self._datatype = {}
        self.parent_path = None

        self._sortrole = None
        self._sortorder = None

        # File-system monitor
        self._last_refreshed = {}
        self._last_changed = {}  # a dict of path/timestamp values

        # Generate thumbnails
        cls = self.__class__.__name__
        _generate_thumbnails = local_settings.value(
            u'widget/{}/generate_thumbnails'.format(cls))
        self.generate_thumbnails = True if _generate_thumbnails is None else _generate_thumbnails

        self.initialize_default_sort_values()

        self.__init_threads__()

    def initialize_default_sort_values(self):
        cls = self.__class__.__name__
        k = u'widget/{}/sortrole'.format(cls)
        val = local_settings.value(k)
        if val not in (common.SortByName, common.SortBySize, common.SortByLastModified):
            val = common.SortByName
        self._sortrole = val

        k = u'widget/{}/sortorder'.format(cls)
        val = local_settings.value(k)
        if val not in (True, False):
            val = False
        self._sortorder = val

        if self._sortrole is None:
            self._sortrole = common.SortByName

        if self._sortorder is None:
            self._sortorder = False

    def sortRole(self):
        """Sort role with saved/default value."""
        return self._sortrole

    @QtCore.Slot(int)
    def setSortRole(self, val):
        """Sets and saves the sort-key."""
        if val == self.sortRole():
            return

        self._sortrole = val

        cls = self.__class__.__name__
        local_settings.setValue(u'widget/{}/sortrole'.format(cls), val)

    def sortOrder(self):
        return self._sortorder

    @QtCore.Slot(int)
    def setSortOrder(self, val):
        """Sets and saves the sort-key."""
        if val == self.sortOrder():
            return

        self._sortorder = val

        cls = self.__class__.__name__
        local_settings.setValue(u'widget/{}/sortorder'.format(cls), val)

    def proxy_idxs(self):
        """Returns the id of the proxy."""
        k = self.data_key()
        t = self.data_type()
        if k not in self._proxy_idxs:
            self._proxy_idxs[k] = {}
            self._proxy_idxs[k][t] = {
                common.SortByName: [],
                common.SortBySize: [],
                common.SortByLastModified: [],
            }
        return self._proxy_idxs[k][t][self.sortRole()]

    @QtCore.Slot()
    def sort_data(self):
        """Slot sorts the internal `_data` dictionary.

        It takes the currently set sort order and creates a new
        data dictionary with the new order.

        Emits the `dataSorted` signal when finished.

        """
        data = self.model_data()
        if not data:
            return

        sortrole = self.sortRole()
        if sortrole not in (common.SortByName, common.SortBySize, common.SortByLastModified):
            sortrole = common.SortByName
        sortorder = self.sortOrder()

        sorted_idxs = sorted(
            data,
            key=lambda idx: common.namekey(data[idx][sortrole]) if isinstance(
                data[idx][sortrole], basestring) else data[idx][sortrole],
            reverse=sortorder
        )

        # Copy
        __data = {}
        for n, idx in enumerate(sorted_idxs):
            __data[n] = data[idx]

        k = self.data_key()
        t = self.data_type()
        self._data[k][t] = __data

        self.dataSorted.emit()

    @QtCore.Slot()
    def check_data(self):
        """When setting the model data-key it is necessary to check if the data
        has been initialized. If it hasn't, we will trigger `__initdata__` here.

        """
        if not self.model_data():
            self.beginResetModel()
            self.__initdata__()

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
        self._data = {}
        self.__initdata__()

    def __initdata__(self):
        raise NotImplementedError(
            u'__initdata__ is abstract and has to be defined in the subclass.')

    def __init_threads__(self):
        """Starts the threads associated with this model."""
        if not self.thread_count:
            return
        for n in xrange(self.thread_count):
            self.threads[n] = self.InfoThread(self)
            self.threads[n].thread_id = n
            self.threads[n].start()

            self.threads[n * 2] = self.ThumbnailThread(self)
            self.threads[n * 2].thread_id = n * 2
            self.threads[n * 2].start()

        # The thread responsible for getting file information for all items
        idx = len(self.threads)

        def set_model():
            self.threads[idx].worker.model = self
            self.threads[idx].setPriority(QtCore.QThread.LowPriority)
        self.threads[idx] = self.SecondaryInfoThread()
        self.threads[idx].thread_id = idx
        self.threads[idx].started.connect(set_model)
        self.threads[idx].start()

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
        self.InfoThread.Worker.reset_queue()
        self.SecondaryInfoThread.Worker.reset_queue()
        self.ThumbnailThread.Worker.reset_queue()

    @QtCore.Slot()
    def delete_thread(self, thread):
        del self.threads[thread.thread_id]

    def model_data(self):
        """A pointer to the model's currently set internal data."""
        k = self.data_key()
        t = self.data_type()
        if not k in self._data:
            self._data[k] = {common.FileItem: {}, common.SequenceItem: {}}
        if not k in self._proxy_idxs:
            self._proxy_idxs[k] = {
                common.FileItem: {
                    common.SortByName: [],
                    common.SortBySize: [],
                    common.SortByLastModified: [],
                },
                common.SequenceItem: {
                    common.SortByName: [],
                    common.SortBySize: [],
                    common.SortByLastModified: [],
                },
            }
        return self._data[k][t]

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
        return index.data(common.FlagsRole)

    def parent(self, child):
        """We don't implement parented indexes."""
        return QtCore.QModelIndex()

    def setData(self, index, data, role=QtCore.Qt.DisplayRole):
        """Data setter method."""
        if not index.isValid():
            return
        self.model_data()[index.row()][role] = data
        self.dataChanged.emit(index, index)

    def data_key(self):
        """Current key to the data dictionary."""
        raise NotImplementedError(
            'data_key is abstract and has to be overriden in the subclass')

    def data_type(self):
        """Current key to the data dictionary."""
        data_key = self.data_key()
        if data_key not in self._datatype:
            cls = self.__class__.__name__
            key = u'widget/{}/{}/datatype'.format(cls, data_key)
            val = local_settings.value(key)
            val = val if val else common.SequenceItem
            self._datatype[data_key] = val
        return self._datatype[data_key]

    @QtCore.Slot(int)
    def set_data_type(self, val):
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
        local_settings.setValue(key, val)
        self._datatype[data_key] = val


class BaseListWidget(QtWidgets.QListView):
    """Defines the base of the primary list widgets."""

    customContextMenuRequested = QtCore.Signal(
        QtCore.QModelIndex, QtCore.QObject)
    favouritesChanged = QtCore.Signal()
    SourceModel = None

    Delegate = None
    ContextMenu = None

    def __init__(self, parent=None):
        super(BaseListWidget, self).__init__(parent=parent)
        self.progress_widget = ProgressWidget(parent=self)
        self.progress_widget.setHidden(True)
        self.disabled_overlay_widget = DisabledOverlayWidget(parent=self)
        self.disabled_overlay_widget.setHidden(True)
        self.filter_active_widget = FilterOnOverlayWidget(parent=self)
        self.filter_editor = editors.FilterEditor(parent=self)
        self.filter_editor.setHidden(True)

        self.thumbnail_viewer_widget = None
        self._location = None
        self.collector_count = 0
        self.description_editor_widget = editors.DescriptionEditorWidget(
            parent=self)
        self.description_editor_widget.setHidden(True)

        k = u'widget/{}/buttons_hidden'.format(self.__class__.__name__)
        self._buttons_hidden = False if local_settings.value(
            k) is None else local_settings.value(k)

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

        self.setWordWrap(False)
        self.setLayoutMode(QtWidgets.QListView.Batched)
        self.setBatchSize(100)

        self.installEventFilter(self)

        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        @QtCore.Slot(QtCore.QRect)
        def _resize_subwidgets(rect):
            rect = self.viewport().geometry()
            self.progress_widget.setGeometry(rect)
            self.disabled_overlay_widget.setGeometry(rect)
            self.filter_active_widget.setGeometry(rect)
            self.filter_editor.adjust_size()

        self.parent().resized.connect(_resize_subwidgets)

        # Keyboard search timer and placeholder string.
        self.timer = QtCore.QTimer(parent=self)
        app = QtWidgets.QApplication.instance()
        self.timer.setInterval(app.keyboardInputInterval())
        self.timer.setSingleShot(True)
        self.timed_search_string = u''

        self.set_model(self.SourceModel(parent=self))
        self.setItemDelegate(self.Delegate(parent=self))

    def buttons_hidden(self):
        """Returns the visibility of the inline icon buttons."""
        return self._buttons_hidden

    def set_buttons_hidden(self, val):
        """Sets the visibility of the inline icon buttons."""
        cls = self.__class__.__name__
        k = u'widget/{}/buttons_hidden'.format(cls)
        local_settings.setValue(k, val)
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

        model.beginResetModel()
        proxy.setSourceModel(model)
        model.endResetModel()

        self.setModel(proxy)

        model.modelDataResetRequested.connect(
            model.beginResetModel)
        model.modelDataResetRequested.connect(
            model.__resetdata__)
        model.modelAboutToBeReset.connect(
            lambda: model.set_data_type(model.data_type()))

        model.activeChanged.connect(self.save_activated)

        # Swithing between files and sequences
        model.dataTypeChanged.connect(model.set_data_type)
        model.dataTypeChanged.connect(model.sort_data)
        model.dataTypeChanged.connect(self.reselect_previous)

        proxy.filterTextChanged.connect(proxy.set_filter_text)
        proxy.filterFlagChanged.connect(proxy.set_filter_flag)
        proxy.filterTextChanged.connect(proxy.invalidateFilter)
        proxy.filterFlagChanged.connect(proxy.invalidateFilter)

        model.sortingChanged.connect(lambda x, _: model.setSortRole(x))
        model.sortingChanged.connect(lambda _, y: model.setSortOrder(y))
        model.sortingChanged.connect(lambda x, y: model.sort_data())

        model.dataSorted.connect(proxy.initialize_filter_values)
        model.dataSorted.connect(proxy.invalidateFilter)
        model.dataSorted.connect(self.reselect_previous)

        model.modelAboutToBeReset.connect(self.reset_multitoggle)
        model.modelReset.connect(self.reset_multitoggle)

        self.filter_editor.finished.connect(proxy.filterTextChanged)

        model.updateIndex.connect(
            self.update, type=QtCore.Qt.BlockingQueuedConnection)

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

    def initialize_visible_indexes(self):
        pass

    def activate(self, index):
        """Marks the given index by adding the ``MarkedAsActive`` flag.

        If the item has already been activated it will emit the activated signal.
        This is used to switch tabs. If the item is not active yet, it will
        apply the active flag and emit the ``activeChanged`` signal.

        Note:
            The method emits the ``activeChanged`` signal but itself does not
            save the change to the local_settings. That is handled by connections
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
            v = is_collapsed.expand(ur'\1\3')
        elif is_sequence:
            v = is_sequence.expand(ur'\1\3.\4')
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
        local_settings.setValue(k, v)

    @QtCore.Slot()
    def reselect_previous(self):
        """Slot called when the model has finished a reset operation.
        The method will try to reselect the previously selected path."""
        cls = self.__class__.__name__
        k = u'widget/{}/{}/selected_item'.format(
            cls,
            self.model().sourceModel().data_key(),
        )
        val = local_settings.value(k)

        if not val:
            return

        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0)
            path = self._get_path(index.data(QtCore.Qt.StatusTipRole))
            if val.lower() == path.lower():
                self.selectionModel().setCurrentIndex(
                    index, QtCore.QItemSelectionModel.ClearAndSelect)
                self.scrollTo(
                    index, QtWidgets.QAbstractItemView.PositionAtCenter)
                return

        index = self.model().sourceModel().active_index()
        if index.isValid():
            self.selectionModel().setCurrentIndex(
                index, QtCore.QItemSelectionModel.ClearAndSelect)
            self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
            return

        if not self.model().rowCount():
            return

        index = self.model().index(0, 0)
        self.selectionModel().setCurrentIndex(
            index, QtCore.QItemSelectionModel.ClearAndSelect)
        self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)

    def toggle_favourite(self, index, flag=common.MarkedAsFavourite, state=None):
        """Toggles the ``favourite`` state of the current item.
        If `item` and/or `state` are set explicity, those values will be used
        instead of the current item state.

        Args:
            item (QModelIndex): The item to change.
            flag (int): the flag to toggle
            state (None or bool): The explicit state to set for the flag (on or off).

        """
        if not index.isValid():
            return
        model = self.model()
        if hasattr(model, u'sourceModel'):
            index = model.mapToSource(index)
            model = index.model()

        data = model.model_data()[index.row()]
        data_key = model.data_key()
        data_type = model.data_type()

        state = not data[common.FlagsRole] & flag if state is None else state
        is_file = data[common.TypeRole] == common.FileItem

        flags = data[common.FlagsRole]
        data[common.FlagsRole] = flags | flag if state else flags & ~flag

        # An item can be a sequence, a file, or a sequence with a single file.
        # Eg. a sequence with a single file will refer ONE file only but
        # the data will be stored in BOTH the data[FileItem] and data[SequenceItem]
        # entries and we have to update both dictinaries accordingly.
        # Only exception is non-sequence item: the data dictionary will in this case
        # use the same object in both data[FileItem] and data[SequenceItem]
        if is_file:
            key = data[QtCore.Qt.StatusTipRole].lower()
        else:
            key = common.is_collapsed(data[QtCore.Qt.StatusTipRole])
            key = key.expand(ur'\1\3').lower() if key else key

        if flag == common.MarkedAsFavourite:
            favourites = local_settings.value(u'favourites')
            favourites = [f.lower() for f in favourites] if favourites else []
            sfavourites = set(favourites)

            if state and key not in sfavourites:
                favourites.append(key)
            if not state and key in sfavourites:
                favourites.remove(key)

            sfavourites = set(favourites)

        # For non-sequence items there nothing else to do.
        if not data[common.SequenceRole]:
            if flag == common.MarkedAsFavourite:
                local_settings.setValue(u'favourites', sorted(favourites))
            return

        # Update the data[SequenceItem] model if currently browsing data[FileItems]
        if data_type == common.SequenceItem:
            for data in model._data[data_key][common.FileItem].itervalues():
                seq = data[common.SequenceRole]
                if not seq:
                    continue

                if is_file:
                    fileitem_key = data[QtCore.Qt.StatusTipRole].lower()
                else:
                    fileitem_key = seq.expand(ur'\1\3.\4').lower()

                if fileitem_key != key:
                    continue
                data[common.FlagsRole] = flags | flag if state else flags & ~flag

                if flag == common.MarkedAsFavourite:
                    path = data[QtCore.Qt.StatusTipRole].lower()
                    if state and path not in sfavourites:
                        favourites.append(path)
                    if not state and path in sfavourites:
                        favourites.remove(path)

        # Update the data[FileItems] model if currently browsing data[SequenceItem]
        if data_type == common.FileItem:
            for data in model._data[data_key][common.SequenceItem].itervalues():
                if data[common.TypeRole] != common.FileItem:
                    continue

                fileitem_key = data[QtCore.Qt.StatusTipRole].lower()
                if fileitem_key != key:
                    continue

                data[common.FlagsRole] = flags | flag if state else flags & ~flag

                if flag == common.MarkedAsFavourite:
                    path = data[QtCore.Qt.StatusTipRole].lower()
                    if state and path not in sfavourites:
                        favourites.append(path)
                    if not state and path in sfavourites:
                        favourites.remove(path)

        if flag == common.MarkedAsFavourite:
            local_settings.setValue(u'favourites', sorted(favourites))

        self.update(index)

    def toggle_archived(self, index, state=None):
        """Toggles the ``archived`` state of the current item.
        If `item` and/or `state` are set explicity, those values will be used
        instead of the currentItem.

        Note:
            Archived items are automatically removed from ``favourites``.

        Args:
            item (QListWidgetItem): The explicit item to change.
            state (None or bool): The explicit state to set.

        """
        if not index.isValid():
            return
        if not index.data(common.FileInfoLoaded):
            return

        settings = AssetSettings(index)

        favourites = local_settings.value(u'favourites')
        favourites = [f.lower() for f in favourites] if favourites else []
        sfavourites = set(favourites)

        archived = index.flags() & common.MarkedAsArchived

        source_index = self.model().mapToSource(index)
        data = source_index.model().model_data()[source_index.row()]
        m = self.model().sourceModel()

        key = index.data(QtCore.Qt.StatusTipRole)
        collapsed = common.is_collapsed(key)
        if collapsed:
            key = collapsed.expand(ur'\1\3')  # \2 is the sequence-string

        if archived:
            if state is None or state is False:  # clears flag
                data[common.FlagsRole] = data[common.FlagsRole] & ~common.MarkedAsArchived
                settings.setValue(u'config/archived', False)

                # Removing flags for all subsequent sequence files
                if self.model().sourceModel().data_type() == common.SequenceItem:

                    n = 0
                    c = len(data[common.FramesRole])

                    self.progress_widget.show()
                    for _item in m._data[m.data_key()][common.FileItem].itervalues():
                        _seq = _item[common.SequenceRole]
                        if not _seq:
                            continue
                        if _seq.expand(ur'\1\3.\4').lower() != key.lower():
                            continue
                        _item[common.FlagsRole] = _item[common.FlagsRole] & ~common.MarkedAsArchived

                        # Saving the settings to a file
                        server, job, root = _item[common.ParentPathRole][0:3]
                        settings = AssetSettings(
                            server=server,
                            job=job,
                            root=root,
                            filepath=_item[QtCore.Qt.StatusTipRole]
                        )
                        settings.setValue(u'config/archived', False)

                        # Signalling progress
                        n += 1
                        self.model().sourceModel().messageChanged.emit(
                            u'Saving settings ({} of {})...'.format(n, c)
                        )
                        QtWidgets.QApplication.instance().processEvents(
                            QtCore.QEventLoop.ExcludeUserInputEvents)
                    self.progress_widget.hide()
                return

        if state is None or state is True:
            # Removing favourite flags when the item is to be archived
            if key.lower() in sfavourites:
                if state is None or state is False:  # clears flag
                    favourites.remove(key.lower())
                    data[common.FlagsRole] = data[common.FlagsRole] & ~common.MarkedAsFavourite

                if self.model().sourceModel().data_type() == common.SequenceItem:
                    for _item in m._data[m.data_key()][common.FileItem].itervalues():

                        _seq = _item[common.SequenceRole]
                        if not _seq:
                            continue
                        if _seq.expand(ur'\1\3.\4').lower() != key.lower():
                            continue
                        if _item[QtCore.Qt.StatusTipRole].lower() in sfavourites:
                            favourites.remove(
                                _item[QtCore.Qt.StatusTipRole].lower())
                        _item[common.FlagsRole] = _item[common.FlagsRole] & ~common.MarkedAsFavourite

            data[common.FlagsRole] = data[common.FlagsRole] | common.MarkedAsArchived
            settings.setValue(u'config/archived', True)

            if self.model().sourceModel().data_type() == common.SequenceItem:

                n = 0
                c = len(data[common.FramesRole])

                self.progress_widget.show()
                for _item in m._data[m.data_key()][common.FileItem].itervalues():
                    _seq = _item[common.SequenceRole]
                    if not _seq:
                        continue
                    if _seq.expand(ur'\1\3.\4').lower() != key.lower():
                        continue
                    _item[common.FlagsRole] = _item[common.FlagsRole] | common.MarkedAsArchived

                    # Saving the settings to a file
                    server, job, root = _item[common.ParentPathRole][0:3]
                    settings = AssetSettings(
                        server=server,
                        job=job,
                        root=root,
                        filepath=_item[QtCore.Qt.StatusTipRole]
                    )
                    settings.setValue(u'config/archived', True)

                    # Signalling progress
                    n += 1
                    self.model().sourceModel().messageChanged.emit(
                        u'Saving settings ({} of {})...'.format(n, c)
                    )
                    QtWidgets.QApplication.instance().processEvents(
                        QtCore.QEventLoop.ExcludeUserInputEvents)
                self.progress_widget.hide()

        # Let's save the favourites list
        local_settings.setValue(u'favourites', sorted(list(set(favourites))))

    def key_down(self):
        """Custom action on  `down` arrow key-press.

        We're implementing a continous 'scroll' function: reaching the last
        item in the list will automatically jump to the beginning to the list
        and vice-versa.

        """
        sel = self.selectionModel()
        current_index = self.selectionModel().currentIndex()
        first_index = self.model().index(0, 0, parent=QtCore.QModelIndex())
        last_index = self.model().index(
            self.model().rowCount() - 1, 0, parent=QtCore.QModelIndex())

        if first_index == last_index:
            return

        self.setFocus(QtCore.Qt.OtherFocusReason)

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
        for n in xrange(self.model().rowCount()):
            if current_index.row() >= n:
                continue
            sel.setCurrentIndex(
                self.model().index(n, 0, parent=QtCore.QModelIndex()),
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            break

    def key_up(self):
        """Custom action to perform when the `up` arrow is pressed
        on the keyboard.

        We're implementing a continous 'scroll' function: reaching the last
        item in the list will automatically jump to the beginning to the list
        and vice-versa.

        """
        sel = self.selectionModel()
        current_index = self.selectionModel().currentIndex()
        first_index = self.model().index(0, 0, parent=QtCore.QModelIndex())
        last_index = self.model().index(self.model().rowCount() -
                                        1, 0, parent=QtCore.QModelIndex())

        if first_index == last_index:
            return

        self.setFocus(QtCore.Qt.OtherFocusReason)

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

        for n in reversed(xrange(self.model().rowCount())):  # Stepping back
            if current_index.row() <= n:
                continue
            sel.setCurrentIndex(
                self.model().index(n, 0, parent=QtCore.QModelIndex()),
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            break

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
                self.toggle_favourite(index)
                self.update(index)
                self.model().invalidateFilter()
                return

            if event.key() == QtCore.Qt.Key_A:
                self.toggle_archived(index)
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

        try:
            self.disabled_overlay_widget.show()
            widget.exec_()
        finally:
            self.disabled_overlay_widget.hide()

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

        if not index.isValid():
            return super(AssetsWidget, self).mousePressEvent(event)

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

        model = self.model()
        source_model = model.sourceModel()
        filter_text = model.filter_text()

        sizehint = self.itemDelegate().sizeHint(
            self.viewOptions(), QtCore.QModelIndex())

        rect = self.rect()
        center = rect.center()
        rect.setWidth(rect.width() - common.MARGIN)
        rect.moveCenter(center)

        favourite_mode = model.filterFlag(common.MarkedAsFavourite)
        active_mode = model.filterFlag(common.MarkedAsActive)

        text_rect = QtCore.QRect(rect)
        text_rect.setHeight(sizehint.height())

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        painter.setPen(QtCore.Qt.NoPen)
        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSizeF(common.MEDIUM_FONT_SIZE - 1)
        align = QtCore.Qt.AlignCenter

        text = u''
        if not source_model.parent_path:
            if self.parent().currentIndex() == 0:
                if self.model().sourceModel().rowCount() == 0:
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

        if not source_model.data_key():
            if self.parent().currentIndex() == 2:
                text = u'No task folder selected.'
                common.draw_aliased_text(
                    painter, font, text_rect, text, align, common.TEXT_DISABLED)
                return True

        if source_model.rowCount() == 0:
            text = u'No items to show.'
            common.draw_aliased_text(
                painter, font, text_rect, text, align, common.TEXT_DISABLED)
            return True

        for n in xrange((self.height() / sizehint.height()) + 1):
            if n >= model.rowCount():  # Empty items
                rect_ = QtCore.QRect(rect)
                rect_.setWidth(sizehint.height() - 2)

            if n == model.rowCount():  # filter mode
                hidden_count = source_model.rowCount() - model.rowCount()
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
        raise NotImplementedError(u'method is abstract.')

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
            self.toggle_favourite(index)
            self.update(index)
            self.model().invalidateFilter()

        if rectangles[delegate.ArchiveRect].contains(cursor_position):
            self.toggle_archived(index)
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

        if not self.verticalScrollBar().isSliderDown():
            self.update(index)

        rectangles = self.itemDelegate().get_rectangles(self.visualRect(index))
        rect = self.itemDelegate().get_description_rect(rectangles, index)

        if rect.contains(cursor_position):
            if app.overrideCursor():
                app.changeOverrideCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
            else:
                app.restoreOverrideCursor()
                app.setOverrideCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
        else:
            app.restoreOverrideCursor()

        if self.multi_toggle_pos is None:
            return super(BaseInlineIconWidget, self).mouseMoveEvent(event)

        cursor_position.setX(0)
        index = self.indexAt(cursor_position)

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
                self.toggle_favourite(index, state=self.multi_toggle_state)

            if self.multi_toggle_idx == delegate.ArchiveRect:
                self.multi_toggle_items[idx] = archived
                self.toggle_archived(index, state=self.multi_toggle_state)

            return

        if index == initial_index:
            return

        if self.multi_toggle_idx == delegate.FavouriteRect:
            self.toggle_favourite(
                index, state=self.multi_toggle_items.pop(idx))
        elif self.multi_toggle_idx == delegate.FavouriteRect:
            self.toggle_archived(
                index=index, state=self.multi_toggle_items.pop(idx))

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
        self.parent().parent().resized.connect(widget._updateGeometry)
        widget.show()


class ThreadedBaseWidget(BaseInlineIconWidget):
    """Adds the methods needed to push the indexes to the thread-workers."""

    def __init__(self, parent=None):
        super(ThreadedBaseWidget, self).__init__(parent=parent)

        self.scrollbar_changed_timer = QtCore.QTimer(parent=self)
        self.scrollbar_changed_timer.setSingleShot(True)
        self.scrollbar_changed_timer.setInterval(250)

        self.hide_archived_items_timer = QtCore.QTimer(parent=self)
        self.hide_archived_items_timer.setSingleShot(False)
        self.hide_archived_items_timer.setInterval(500)
        self.hide_archived_items_timer.timeout.connect(
            self.hide_archived_items)

        # Stopping the timer
        self.model().sourceModel().modelAboutToBeReset.connect(
            self.hide_archived_items_timer.stop)
        self.model().sourceModel().modelAboutToBeReset.connect(
            self.scrollbar_changed_timer.stop)

        # Clearing the queues
        self.model().modelAboutToBeReset.connect(
            self.model().sourceModel().reset_thread_worker_queues)
        self.model().sourceModel().dataTypeChanged.connect(
            self.model().sourceModel().reset_thread_worker_queues)
        self.model().sourceModel().dataKeyChanged.connect(
            self.model().sourceModel().reset_thread_worker_queues)
        self.model().sourceModel().modelAboutToBeReset.connect(
            self.model().sourceModel().reset_thread_worker_queues)
        self.model().sourceModel().modelReset.connect(
            self.model().sourceModel().reset_thread_worker_queues)
        self.model().sourceModel().modelReset.connect(
            self.model().sourceModel().reset_file_info_loaded)
        self.model().sourceModel().dataTypeChanged.connect(
            self.model().sourceModel().reset_file_info_loaded)
        self.model().sourceModel().modelReset.connect(
            self.restart_timer)


        self.model().sourceModel().dataSorted.connect(
            self.hide_archived_items_timer.start)
        self.model().sourceModel().dataSorted.connect(
            self.restart_timer)

        # Initializing the indexes
        self.model().sourceModel().dataSorted.connect(self.restart_timer)
        self.model().sourceModel().dataTypeChanged.connect(self.restart_timer)
        self.model().sourceModel().dataKeyChanged.connect(self.restart_timer)
        self.verticalScrollBar().valueChanged.connect(self.restart_timer)
        self.scrollbar_changed_timer.timeout.connect(
            self.initialize_visible_indexes)

    @QtCore.Slot()
    def restart_timer(self):
        """Fires the timer responsible for updating the visible model indexes on
        a threaded viewer.

        """
        self.scrollbar_changed_timer.start(
            self.scrollbar_changed_timer.interval())

    @QtCore.Slot()
    def hide_archived_items(self):
        if not self.isVisible():
            return
        app = QtWidgets.QApplication.instance()
        if app.mouseButtons() != QtCore.Qt.NoButton:
            return
        proxy_model = self.model()
        if not proxy_model.rowCount():
            return

        index = self.indexAt(self.rect().topLeft())
        if not index.isValid():
            return

        show_archived = proxy_model.filterFlag(common.MarkedAsArchived)
        rect = self.visualRect(index)
        while self.viewport().rect().intersects(rect):
            is_archived = index.flags() & common.MarkedAsArchived
            if not show_archived and is_archived:
                proxy_model.invalidateFilter()
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

        proxy_model = self.model()
        if not proxy_model.rowCount():
            return

        r = self.viewport().rect()
        index = self.indexAt(r.topLeft())
        if not index.isValid():
            return

        needs_info = []
        needs_thumbnail = []
        visible = []
        source_model = proxy_model.sourceModel()

        # Starting from the top left we'll get all visible indexes
        rect = self.visualRect(index)
        while r.intersects(rect):
            visible.append(index)

            if not index.data(common.FileInfoLoaded):
                needs_info.append(index)

            if source_model.generate_thumbnails and not index.data(common.FileThumbnailLoaded):
                needs_thumbnail.append(index)
            rect.moveTop(rect.top() + rect.height())

            index = self.indexAt(rect.topLeft())
            if not index.isValid():
                break

        # Here we add the last index of the window
        index = self.indexAt(self.rect().bottomLeft())
        if index.isValid():
            visible.append(index)
            if not index.data(common.FileInfoLoaded):
                if index not in needs_info:
                    needs_info.append(index)

            if source_model.generate_thumbnails:
                if not index.data(common.FileThumbnailLoaded):
                    if index not in needs_thumbnail:
                        needs_thumbnail.append(index)
        if needs_info:
            source_model.InfoThread.Worker.add_to_queue(needs_info)

        if source_model.generate_thumbnails:
            source_model.ThumbnailThread.Worker.add_to_queue(needs_thumbnail)



    def showEvent(self, event):
        self.hide_archived_items_timer.start()

        self.parent().parent().resized.emit(self.viewport().geometry())

        # self.progress_widget.setGeometry(self.viewport().geometry())
        # self.disabled_overlay_widget.setGeometry(self.viewport().geometry())
        # self.filter_active_widget.setGeometry(self.viewport().geometry())

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
            local_settings.setValue(k, idx)

        super(StackedWidget, self).setCurrentIndex(idx)
