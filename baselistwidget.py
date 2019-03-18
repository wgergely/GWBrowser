# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101
"""Module defines the QListWidget items used to browse the projects and the files
found by the collector classes.

"""

import re
from functools import wraps

from PySide2 import QtWidgets, QtGui, QtCore

import browser.common as common
import browser.editors as editors
from browser.imagecache import ImageCache
import browser.settings as Settings
from browser.settings import local_settings
from browser.settings import AssetSettings


def flagsmethod(func):
    """Decorator to make sure the ItemFlag values are always correct."""
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        res = func(self, *args, **kwargs)
        if not res:
            res = QtCore.Qt.NoItemFlags
        return res
    return func_wrapper


class FilterProxyModel(QtCore.QSortFilterProxyModel):
    """Proxy model responsible for filtering and sorting source model data.

    We can filter our data based on item flags, and path-segment strings.
    The list can also be arranged by name, size, and modified timestamps."""

    filterTextChanged = QtCore.Signal(unicode)
    filterFlagChanged = QtCore.Signal(int, bool)  # FilterFlag, value
    sortOrderChanged = QtCore.Signal(int, bool)  # (SortKey, SortOrder)

    def __init__(self, parent=None):
        super(FilterProxyModel, self).__init__(parent=parent)
        self.setSortLocaleAware(False)
        self.setDynamicSortFilter(False)
        self.setFilterRole(QtCore.Qt.StatusTipRole)
        self.setSortCaseSensitivity(QtCore.Qt.CaseSensitive)
        self.setFilterCaseSensitivity(QtCore.Qt.CaseSensitive)

        self.parentwidget = parent

        self._sortkey = None  # Alphabetical/Modified...etc.
        self._sortorder = None  # Ascending/descending
        self._filtertext = None  # Ascending/descending

        self._filterflags = {
            Settings.MarkedAsActive: None,
            Settings.MarkedAsArchived: None,
            Settings.MarkedAsFavourite: None,
        }

    def get_filtertext(self):
        """Filters the list of items containing this path segment.

        """
        if self._filtertext is None:
            cls = self.sourceModel().__class__.__name__
            val = local_settings.value(u'widget/{}/filtertext'.format(cls))
            if val is None:
                self._filtertext = u'/'
            else:
                self._filtertext = val
        else:
            val = self._filtertext
        return val if val else u'/'

    def set_filtertext(self, val):
        """Sets the path-segment to use as a filter.
        Emits the ``filterTextChanged`` signal.

        """
        if val == self._filtertext:
            return

        cls = self.sourceModel().__class__.__name__
        if val is None:
            self._filtertext = None
            local_settings.setValue(u'widget/{}/filtertext'.format(cls), None)
        else:
            val = val if val else u'/'
            self._filtertext = val
            local_settings.setValue(u'widget/{}/filtertext'.format(cls), val)

    def get_filterflag(self, flag):
        """Returns the current flag-filter."""
        if self._filterflags[flag] is None:
            cls = self.sourceModel().__class__.__name__
            val = local_settings.value(
                u'widget/{}/filterflag{}'.format(cls, flag))
            if val is None:
                self._filterflags[flag] = False
            else:
                self._filterflags[flag] = val
        else:
            val = self._filterflags[flag]
        return val if val else False

    @QtCore.Slot(int, bool)
    def set_filterflag(self, flag, val):
        if self._filterflags[flag] == val:
            return

        self._filterflags[flag] = val
        cls = self.sourceModel().__class__.__name__
        local_settings.setValue(
            u'widget/{}/filterflag{}'.format(cls, flag), val)

    def get_sortkey(self):
        """The sort-key used to determine the order of the list.

        """
        if self._sortkey is None:
            cls = self.__class__.__name__
            val = local_settings.value(u'widget/{}/sortkey'.format(cls))
            if val is None:
                self._sortkey = common.SortByName
            else:
                self._sortkey = val
        else:
            val = self._sortkey
        if val in (common.SortByName, common.SortByLastModified, common.SortBySize):
            return val
        return common.SortByName

    @QtCore.Slot(int)
    def set_sortkey(self, val):
        """Sets and saves the sort-key."""
        if val == self._sortkey:
            return
        if val not in (common.SortByName, common.SortBySize, common.SortByLastModified):
            raise ValueError('Wrong value type for set_sortkey.')

        self._sortkey = val
        self.setSortRole(val)
        cls = self.__class__.__name__
        local_settings.setValue(u'widget/{}/sortkey'.format(cls), val)

    def get_sortorder(self):
        """The order of the list, eg. ascending/descending."""
        if self._sortorder is None:
            cls = self.__class__.__name__
            val = local_settings.value(
                u'widget/{}/sortorder'.format(cls))
            if val is None:
                self._sortorder = False
            else:
                self._sortorder = val
        else:
            val = self._sortorder
        return int(val) if val else False

    @QtCore.Slot(bool)
    def set_sortorder(self, val):
        if val == self._sortorder:
            return
        self._sortorder = val
        cls = self.__class__.__name__
        local_settings.setValue(u'widget/{}/sortorder'.format(cls), val)

    def filterAcceptsColumn(self, source_column, parent=QtCore.QModelIndex()):
        return True

    def filterAcceptsRow(self, source_row, parent=None):
        """The main method used to filter the elements using the flags and the filter string."""
        # print 'Filtering {}...'.format(source_row)
        data = self.sourceModel().model_data()

        if source_row not in data:
            return False

        flags = data[source_row][common.FlagsRole]
        archived = flags & Settings.MarkedAsArchived
        favourite = flags & Settings.MarkedAsFavourite
        active = flags & Settings.MarkedAsActive

        if self.get_filterflag(Settings.MarkedAsActive) and active:
            return True
        if self.get_filterflag(Settings.MarkedAsActive) and not active:
            return False

        if self.get_filtertext().lower() not in data[source_row][QtCore.Qt.StatusTipRole].lower():
            return False
        if archived and not self.get_filterflag(Settings.MarkedAsArchived):
            return False
        if not favourite and self.get_filterflag(Settings.MarkedAsFavourite):
            return False
        return True

    def lessThan(self, source_left, source_right):
        """The main method responsible for sorting the items."""
        # print 'Sorting {}...'.format(source_left.row())
        k = self.get_sortkey()
        if k == common.SortByName:
            return common.namekey(source_left.data(k)) < common.namekey(source_right.data(k))
        return source_left.data(k) < source_right.data(k)


class BaseModel(QtCore.QAbstractItemModel):
    """Flat base-model for storing items."""
    # Emit before the model is about to change
    modelDataResetRequested = QtCore.Signal()
    """Signal emited when all the data has to be refreshed."""

    activeChanged = QtCore.Signal(QtCore.QModelIndex)
    dataKeyChanged = QtCore.Signal(unicode)
    dataTypeChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(BaseModel, self).__init__(parent=parent)
        self.view = parent
        self.active = QtCore.QModelIndex()

        self._data = {}
        self._datakey = None
        self._datatype = None
        self._parent_item = None

        # File-system monitor
        self._file_monitor = QtCore.QFileSystemWatcher()
        self._last_refreshed = {}
        self._last_changed = {}  # a dict of path/timestamp values


    @QtCore.Slot(unicode)
    def check_data(self):
        """When setting the model data-key it is necessary to check if the data
        has been initialized. If it hasn't, we will trigger `__initdata__` here.

        """
        if not self.model_data():
            self.beginResetModel()
            self.__initdata__()

    @QtCore.Slot(QtCore.QModelIndex)
    def set_active(self, index):
        """Sets the given index's parent."""
        if not index.isValid():
            self._parent_item = None
            return

        if index.data(common.ParentRole) == self._parent_item:
            return
        self._parent_item = index.data(common.ParentRole)


    def __resetdata__(self):
        """Resets the internal data."""
        monitored = self._file_monitor.directories()
        if monitored:
            self._file_monitor.removePaths(monitored)

        self._data = {}
        self.__initdata__()

    def __initdata__(self):
        raise NotImplementedError(
            u'__initdata__ is abstract and has to be defined in the subclass.')

    def model_data(self):
        """A pointer to the current model dataset."""
        k = self.data_key()
        t = self.data_type()
        if not k in self._data:
            self._data[k] = {common.FileItem: {}, common.SequenceItem: {}}
        return self._data[k][t]

        # return self._model_data[self._]
    def active_index(self):
        """The model's active_index."""
        for n in xrange(self.rowCount()):
            index = self.index(n, 0)
            if index.flags() & Settings.MarkedAsActive:
                return index
        return QtCore.QModelIndex()

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 1

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(list(self.model_data()))

    def index(self, row, column, parent=QtCore.QModelIndex()):
        return self.createIndex(row, 0, parent=parent)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        data = self.model_data()
        if index.row() not in data:
            return None
        if role in data[index.row()]:
            return data[index.row()][role]

    @flagsmethod
    def flags(self, index):
        return index.data(common.FlagsRole)

    def parent(self, child):
        return QtCore.QModelIndex()

    def setData(self, index, data, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return
        self.model_data()[index.row()][role] = data
        self.dataChanged.emit(index, index)

    def data_key(self):
        """Current key to the data dictionary."""
        if self._datakey is None:
            val = None
            cls = self.__class__.__name__
            key = u'widget/{}/datakey'.format(cls)
            savedval = local_settings.value(key)
            return savedval if savedval else val
        return self._datakey

    def data_type(self):
        """Current key to the data dictionary."""
        if self._datatype is None:
            val = common.FileItem
            cls = self.__class__.__name__
            key = u'widget/{}/{}/datatype'.format(cls, self.data_key())
            savedval = local_settings.value(key)
            return savedval if savedval else val
        return self._datatype

    @QtCore.Slot(unicode)
    def set_data_key(self, val):
        """Sets the ``key`` used to access the stored data.

        Each subfolder inside the ``_parent_item`` corresponds to a `key`, hence
        it's important to make sure the key we're about to be set corresponds to
        an existing folder.

        """
        if val == self._datakey:
            return

        cls = self.__class__.__name__
        key = u'widget/{}/datakey'.format(cls)

        if not self._parent_item:
            val = None
            local_settings.setValue(key, val)
            self._datakey = val
            return

        local_settings.setValue(key, val)
        self._datakey = val

    @QtCore.Slot(int)
    def set_data_type(self, val):
        if val == self._datatype:
            return
        if val not in (common.FileItem, common.SequenceItem):
            raise ValueError('Invalid value {} ({}) provided for `data_type`'.format(val, type(val)))
        cls = self.__class__.__name__
        key = u'widget/{}/{}/datatype'.format(cls, self.data_key())
        local_settings.setValue(key, val)
        self._datatype = val

    def validate_key(self):
        if not self._parent_item:
            return
        path = u'/'.join(self._parent_item)
        dir_ = QtCore.QDir(path)
        dir_.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)

        entries = dir_.entryList()
        if not entries:
            return

        key = self.data_key()
        if key not in sorted(entries):
            self.set_data_key(entries[0])

class BaseListWidget(QtWidgets.QListView):
    """Defines the base of the ``Asset``, ``Bookmark`` and ``File`` list widgets."""

    customContextMenuRequested = QtCore.Signal(
        QtCore.QModelIndex, QtCore.QObject)

    # Signals
    sizeChanged = QtCore.Signal(QtCore.QSize)

    def __init__(self, parent=None):
        super(BaseListWidget, self).__init__(parent=parent)

        self._thumbnailvieweropen = None
        self._current_selection = None
        self._location = None
        self.collector_count = 0
        self.context_menu_cls = None

        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setUniformItemSizes(True)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.installEventFilter(self)

        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        common.set_custom_stylesheet(self)

        # Keyboard search timer and placeholder string.
        self.timer = QtCore.QTimer(parent=self)
        app = QtWidgets.QApplication.instance()
        self.timer.setInterval(app.keyboardInputInterval())
        self.timer.setSingleShot(True)
        self.timed_search_string = u''

    def set_model(self, model):
        """This is the main port of entry for the model.

        The BaseModel subclasses are wrapped in a QSortFilterProxyModel and all
        the needed signal connections are connected here."""

        proxy = FilterProxyModel(parent=self)
        proxy.setSourceModel(model)

        self.setModel(proxy)

        model.modelDataResetRequested.connect(
            model.beginResetModel, type=QtCore.Qt.DirectConnection)
        model.modelDataResetRequested.connect(
            model.__resetdata__, type=QtCore.Qt.DirectConnection)

        # Selection
        model.modelAboutToBeReset.connect(
            lambda: self.save_selection(self.selectionModel().currentIndex()),
            type=QtCore.Qt.DirectConnection)
        model.modelReset.connect(self.reselect_previous,
            type=QtCore.Qt.QueuedConnection)

        proxy.filterFlagChanged.connect(proxy.set_filterflag,
            type=QtCore.Qt.DirectConnection)
        proxy.filterFlagChanged.connect(lambda x, y: proxy.invalidateFilter(),
            type=QtCore.Qt.QueuedConnection)

        # Sort/Filter signalsx
        proxy.filterTextChanged.connect(
            proxy.set_filtertext,
            type=QtCore.Qt.QueuedConnection)
        proxy.filterTextChanged.connect(
            lambda x: proxy.invalidateFilter(),
            type=QtCore.Qt.QueuedConnection)

        # Sorting
        proxy.sortOrderChanged.connect(
            lambda x, y: proxy.set_sortkey(x))
        proxy.sortOrderChanged.connect(
            lambda x, y: proxy.set_sortorder(y))
        proxy.sortOrderChanged.connect(
            lambda x, y: proxy.sort(
                0, QtCore.Qt.AscendingOrder if proxy.get_sortorder() else QtCore.Qt.DescendingOrder),
            type=QtCore.Qt.QueuedConnection)
        model.modelReset.connect(
            lambda: proxy.sort(
                0, QtCore.Qt.AscendingOrder if proxy.get_sortorder() else QtCore.Qt.DescendingOrder),
            type=QtCore.Qt.QueuedConnection)

        model.activeChanged.connect(self.save_activated)

        model.dataKeyChanged.connect(model.set_data_key)
        model.dataKeyChanged.connect(lambda x: model.check_data())
        model.dataKeyChanged.connect(lambda x: proxy.invalidate(),
            type=QtCore.Qt.QueuedConnection)

        model.dataTypeChanged.connect(model.set_data_type)
        model.dataTypeChanged.connect(lambda x: proxy.invalidate(),
            type=QtCore.Qt.QueuedConnection)

        model.modelAboutToBeReset.connect(
            lambda: model.set_data_key(model.data_key()))
        model.modelAboutToBeReset.connect(
            lambda: model.set_data_type(model.data_type()))
        model.modelAboutToBeReset.connect(model.validate_key)

        # def timestamp():
        #     self.model().sourceModel()._last_refreshed[self.model(
        #     ).sourceModel().data_key()] = time.time()
        #     lambda: self.model().blockSignals(False))
        #
        # self.model().sourceModel().modelReset.connect(
        #     timestamp, type=QtCore.Qt.QueuedConnection)

    def active_index(self):
        """Returns the ``active`` item marked by the ``Settings.MarkedAsActive``
        flag. Returns an invalid index if no items is marked as active.

        """
        index = self.model().sourceModel().active_index()
        if not index.isValid():
            return QtCore.QModelIndex()
        return self.model().mapFromSource(index)

    def activate(self, index):
        """Sets the given index as ``active``.

        Note:
            The method doesn't alter the config files or emits signals,
            merely sets the item flags. Make sure to implement that in the subclass.

        """
        if not index.isValid():
            return
        if index.flags() == QtCore.Qt.NoItemFlags:
            return
        if index.flags() & Settings.MarkedAsArchived:
            return

        self.activated.emit(index)
        if index.flags() & Settings.MarkedAsActive:
            return

        self.deactivate(self.active_index())

        source_index = self.model().mapToSource(index)
        source_index.model().setData(
            source_index,
            source_index.flags() | Settings.MarkedAsActive,
            role=common.FlagsRole
        )
        source_index.model().activeChanged.emit(source_index)

    def deactivate(self, index):
        """Unsets the active flag."""
        if not index.isValid():
            return
        source_index = self.model().mapToSource(index)
        source_index.model().setData(
            source_index,
            source_index.flags() & ~Settings.MarkedAsActive,
            role=common.FlagsRole)

    @QtCore.Slot(QtCore.QModelIndex)
    def save_activated(self, index):
        raise NotImplementedError(
            '`save_activated` is abstract and has to be implemented in the subclass.')

    @QtCore.Slot(QtCore.QModelIndex)
    def save_selection(self, current):
        """Saves the currently selected path."""
        if not current.isValid():
            self._current_selection = None
            return
        val = current.data(QtCore.Qt.StatusTipRole)
        self._current_selection = val
        local_settings.setValue(
            u'widget/{}/selected_item'.format(self.__class__.__name__),
            val
        )

    @QtCore.Slot()
    def reselect_previous(self):
        """Slot called when the model has finished a reset operation.
        The method will try to reselect the previously selected path."""

        val = self._current_selection
        if val is None:
            val = local_settings.value(
                u'widget/{}/selected_item'.format(self.__class__.__name__))
        if not val:
            return

        seq = common.get_sequence(val)
        if seq:
            val = seq.expand(r'\1\3.\4')
        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0)
            path = index.data(QtCore.Qt.StatusTipRole)
            seq = common.get_sequence(path)
            if seq:
                path = seq.expand(r'\1\3.\4')
            if path == val:
                self.selectionModel().setCurrentIndex(
                    index, QtCore.QItemSelectionModel.ClearAndSelect)
                self.scrollTo(index)
                return

        if self.model().rowCount():
            index = self.model().index(0, 0)
            self.selectionModel().setCurrentIndex(index, QtCore.QItemSelectionModel.ClearAndSelect)
            self.scrollTo(index)


    def toggle_favourite(self, index, state=None):
        """Toggles the ``favourite`` state of the current item.
        If `item` and/or `state` are set explicity, those values will be used
        instead of the currentItem.

        Args:
            item (QListWidgetItem): The item to change.
            state (None or bool): The state to set.

        """
        if not index.isValid():
            return

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))

        # Favouriting archived items are not allowed
        archived = index.flags() & Settings.MarkedAsArchived
        if archived:
            return

        favourites = local_settings.value(u'favourites')
        favourites = favourites if favourites else []

        if file_info.filePath() in favourites:
            if state is None or state is False:  # clears flag
                self.model().sourceModel().setData(
                    index,
                    index.flags() & ~Settings.MarkedAsFavourite,
                    role=common.FlagsRole
                )
                favourites.remove(file_info.filePath())
        else:
            if state is None or state is True:  # adds flag
                favourites.append(file_info.filePath())
                self.model().sourceModel().setData(
                    index,
                    index.flags() | Settings.MarkedAsFavourite,
                    role=common.FlagsRole
                )

        local_settings.setValue(u'favourites', favourites)

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
        source_index = self.model().mapToSource(index)
        archived = source_index.flags() & Settings.MarkedAsArchived
        file_info = QtCore.QFileInfo(source_index.data(QtCore.Qt.StatusTipRole))

        settings = AssetSettings(source_index)
        favourites = local_settings.value(u'favourites')
        favourites = favourites if favourites else []

        if archived:
            if state is None or state is False:  # clears flag
                source_index.model().setData(
                    source_index,
                    source_index.flags() & ~Settings.MarkedAsArchived,
                    role=common.FlagsRole
                )
                settings.setValue(u'config/archived', False)
                return

        if state is None or state is True:
            settings.setValue(u'config/archived', True)
            source_index.model().setData(
                source_index,
                source_index.flags() | Settings.MarkedAsArchived,
                role=common.FlagsRole
            )
            if file_info.filePath() in favourites:
                source_index.model().setData(
                    source_index,
                    source_index.flags() & ~Settings.MarkedAsFavourite,
                    role=common.FlagsRole
                )
                favourites.remove(file_info.filePath())
                local_settings.setValue(u'favourites', favourites)

    def key_down(self):
        """Custom action tpo perform when the `down` arrow is pressed
        on the keyboard.

        """
        sel = self.selectionModel()
        current_index = self.selectionModel().currentIndex()
        first_index = self.model().index(0, 0, parent=QtCore.QModelIndex())
        last_index = self.model().index(self.model().rowCount() -
                                        1, 0, parent=QtCore.QModelIndex())

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

        """
        sel = self.selectionModel()
        current_index = self.selectionModel().currentIndex()
        first_index = self.model().index(0, 0, parent=QtCore.QModelIndex())
        last_index = self.model().index(self.model().rowCount() -
                                        1, 0, parent=QtCore.QModelIndex())

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

        for n in reversed(xrange(self.model().rowCount())):  # Stepping back
            if current_index.row() <= n:
                continue
            sel.setCurrentIndex(
                self.model().index(n, 0, parent=QtCore.QModelIndex()),
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            break

    def key_tab(self):
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            index = self.model().index(0, 0, parent=QtCore.QModelIndex())

        widget = editors.DescriptionEditorWidget(index, parent=self)
        widget.show()

    def keyPressEvent(self, event):
        """Customized key actions.

        We're defining the default behaviour of the list-items here, including
        defining the actions needed to navigate the list using keyboard presses.

        """
        numpad_modifier = event.modifiers() & QtCore.Qt.KeypadModifier
        no_modifier = event.modifiers() == QtCore.Qt.NoModifier
        if no_modifier or numpad_modifier:
            if event.key() == QtCore.Qt.Key_Space:
                index = self.selectionModel().currentIndex()
                if index.isValid():
                    if not self._thumbnailvieweropen:
                        editors.ThumbnailViewer(index, parent=self)
                    else:
                        self._thumbnailvieweropen.close()
            if event.key() == QtCore.Qt.Key_Escape:
                self.selectionModel().setCurrentIndex(QtCore.QModelIndex(),
                                                      QtCore.QItemSelectionModel.ClearAndSelect)
            elif event.key() == QtCore.Qt.Key_Down:
                self.key_down()
            elif event.key() == QtCore.Qt.Key_Up:
                self.key_up()
            elif (event.key() == QtCore.Qt.Key_Return) or (event.key() == QtCore.Qt.Key_Enter):
                self.action_on_enter_key()
            elif event.key() == QtCore.Qt.Key_Tab:
                self.key_down()
                self.key_tab()
            elif event.key() == QtCore.Qt.Key_Backtab:
                self.key_up()
                self.key_tab()
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
                            break
                    else:
                        match = re.search(
                            self.timed_search_string,
                            index.data(QtCore.Qt.DisplayRole),
                            flags=re.IGNORECASE
                        )
                        if match:
                            sel.setCurrentIndex(
                                index,
                                QtCore.QItemSelectionModel.ClearAndSelect
                            )
                            break

        if event.modifiers() & QtCore.Qt.ControlModifier:
            pass

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

        widget = self.context_menu_cls(index, parent=self)

        if index.isValid():
            rect = self.visualRect(index)
            widget.move(
                self.viewport().mapToGlobal(rect.bottomLeft()).x(),
                self.viewport().mapToGlobal(rect.bottomLeft()).y() + 1,
            )
        else:
            widget.move(QtGui.QCursor().pos())

        widget.setFixedWidth(width)
        widget.move(widget.x() + common.INDICATOR_WIDTH, widget.y())
        common.move_widget_to_available_geo(widget)
        widget.exec_()

    def action_on_enter_key(self):
        self.activate(self.selectionModel().currentIndex())

    def resizeEvent(self, event):
        """Custom resize event will emit the ``sizeChanged`` signal."""
        self.sizeChanged.emit(event.size())
        super(BaseListWidget, self).resizeEvent(event)

    def mousePressEvent(self, event):
        """Deselecting item when the index is invalid."""
        if not isinstance(event, QtGui.QMouseEvent):
            self._reset_multitoggle()
            return None

        index = self.indexAt(event.pos())
        if not index.isValid():
            self.selectionModel().setCurrentIndex(
                QtCore.QModelIndex(),
                QtCore.QItemSelectionModel.ClearAndSelect
            )
        super(BaseListWidget, self).mousePressEvent(event)

    def eventFilter(self, widget, event):
        """Custom paint event used to paint the background of the list."""
        if widget is not self:
            return False

        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)

            sizehint = self.itemDelegate().sizeHint(
                self.viewOptions(), QtCore.QModelIndex())

            rect = QtCore.QRect(
                common.INDICATOR_WIDTH,
                2,
                self.viewport().rect().width() - (common.INDICATOR_WIDTH * 2),
                sizehint.height() - common.INDICATOR_WIDTH
            )

            favourite_mode = self.model().get_filterflag(Settings.MarkedAsFavourite)

            text_rect = QtCore.QRect(rect)
            text_rect.setLeft(rect.left() + rect.height() + common.MARGIN)
            text_rect.setRight(rect.right() - common.MARGIN)

            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

            painter.setPen(QtCore.Qt.NoPen)
            font = QtGui.QFont(common.PrimaryFont)
            font.setPointSize(8)

            align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight
            for n in xrange((self.height() / sizehint.height()) + 1):
                if n >= self.model().rowCount():  # Empty items
                    rect_ = QtCore.QRect(rect)
                    rect_.setWidth(sizehint.height() - 2)
                if n == 0 and not favourite_mode:  # Empty model
                    text = u'No items to show.'
                    common.draw_aliased_text(
                        painter, font, text_rect, text, align, common.TEXT_DISABLED)
                elif n == self.model().rowCount():  # filter mode
                    if favourite_mode:
                        text = u'{} items are hidden'.format(
                            self.model().sourceModel().rowCount() - self.model().rowCount())
                        common.draw_aliased_text(
                            painter, font, text_rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight, common.SECONDARY_TEXT)

                text_rect.moveTop(text_rect.top() + sizehint.height())
                rect.moveTop(rect.top() + sizehint.height())
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

    def _reset_multitoggle(self):
        self.multi_toggle_pos = None
        self.multi_toggle_state = None
        self.multi_toggle_idx = None
        self.multi_toggle_item = None
        self.multi_toggle_items = {}

    def mousePressEvent(self, event):
        """The custom mousePressEvent initiates the multi-toggle operation.
        Only the `favourite` and `archived` buttons are multi-toggle capable."""
        index = self.indexAt(event.pos())
        rect = self.visualRect(index)

        if self.viewport().width() < 360.0:
            return super(BaseInlineIconWidget, self).mousePressEvent(event)

        self._reset_multitoggle()

        for n in xrange(self.inline_icons_count()):
            _, bg_rect = self.itemDelegate().get_inline_icon_rect(
                rect, common.INLINE_ICON_SIZE, n)

            # Beginning multi-toggle operation
            if not bg_rect.contains(event.pos()):
                continue

            self.multi_toggle_pos = event.pos()
            if n == 0:  # Favourite button
                self.multi_toggle_state = not index.flags() & Settings.MarkedAsFavourite
            elif n == 1:  # Archive button
                self.multi_toggle_state = not index.flags() & Settings.MarkedAsArchived
            elif n == 2:  # Reveal button
                continue
            elif n == 3:  # Todo button
                continue

            self.multi_toggle_idx = n
            return True

        return super(BaseInlineIconWidget, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Inline-button methods are triggered here."""
        if not isinstance(event, QtGui.QMouseEvent):
            self._reset_multitoggle()
            return None

        index = self.indexAt(event.pos())
        rect = self.visualRect(index)
        idx = index.row()

        if self.viewport().width() < 360.0:
            return super(BaseInlineIconWidget, self).mouseReleaseEvent(event)

        # Cheking the button
        if idx in self.multi_toggle_items:
            self._reset_multitoggle()
            self.model().invalidate()
            return super(BaseInlineIconWidget, self).mouseReleaseEvent(event)

        for n in xrange(self.inline_icons_count()):
            _, bg_rect = self.itemDelegate().get_inline_icon_rect(
                rect, common.INLINE_ICON_SIZE, n)

            if not bg_rect.contains(event.pos()):
                continue

            if n == 0:
                self.toggle_favourite(index)
                self.save_selection(self.selectionModel().currentIndex())
                self.model().invalidate()
                self.reselect_previous()
                break
            elif n == 1:
                self.toggle_archived(index)
                self.save_selection(self.selectionModel().currentIndex())
                self.model().invalidate()
                self.reselect_previous()
                break
            elif n == 2:
                common.reveal(index.data(QtCore.Qt.StatusTipRole))
                break
            elif n == 3:
                self.show_todos(index)
                break

        self._reset_multitoggle()
        super(BaseInlineIconWidget, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """Multi-toggle is handled here."""
        if not isinstance(event, QtGui.QMouseEvent):
            return None

        if self.viewport().width() < 360.0:
            return super(BaseInlineIconWidget, self).mouseMoveEvent(event)

        if self.multi_toggle_pos is None:
            return super(BaseInlineIconWidget, self).mouseMoveEvent(event)

        pos = event.pos()
        pos.setX(0)
        index = self.indexAt(pos)
        initial_index = self.indexAt(self.multi_toggle_pos)
        idx = index.row()

        favourite = index.flags() & Settings.MarkedAsFavourite
        archived = index.flags() & Settings.MarkedAsArchived

        # Filter the current item
        if index == self.multi_toggle_item:
            return

        self.multi_toggle_item = index

        # Before toggling the item, we're saving it's state

        if idx not in self.multi_toggle_items:
            if self.multi_toggle_idx == 0:  # Favourite button
                # A state
                self.multi_toggle_items[idx] = favourite
                # Apply first state
                self.toggle_favourite(index, state=self.multi_toggle_state)
            if self.multi_toggle_idx == 1:  # Archived button
                # A state
                self.multi_toggle_items[idx] = archived
                # Apply first state
                self.toggle_archived(index, state=self.multi_toggle_state)
        else:  # Reset state
            if index == initial_index:
                return
            if self.multi_toggle_idx == 0:  # Favourite button
                self.toggle_favourite(index, state=self.multi_toggle_items.pop(idx))
            elif self.multi_toggle_idx == 1:  # Favourite button
                self.toggle_archived(index=index, state=self.multi_toggle_items.pop(idx))

    def show_todos(self, index):
        pass


class StackedWidget(QtWidgets.QStackedWidget):
    """Stacked widget to switch between the Bookmark-, Asset - and File lists."""

    def __init__(self, parent=None):
        super(StackedWidget, self).__init__(parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )
        self.setObjectName(u'BrowserStackedWidget')

    def setCurrentIndex(self, idx):
        idx = idx if idx else 0
        idx = idx if idx >= 0 else 0
        local_settings.setValue(u'widget/mode', idx)
        super(StackedWidget, self).setCurrentIndex(idx)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH, common.HEIGHT)
