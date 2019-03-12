# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101

"""Definitions for the asset model/view classes.

An asset refers is a folder with a ``workspace.mel`` identifier file present, containing a
`scenes`, `renders`, `textures` and `exports` folders. Both the identifier files
and name of the above folders can be customized in the ``browser.commons`` module.

Each asset can be annoted with a description, thumbnail, and todo items. These
values are stored in the ``bookmark/.browser`` folder.

"""

import time
from PySide2 import QtWidgets, QtCore, QtGui

from browser.imagecache import ImageCache
import browser.common as common
from browser.baselistwidget import BaseContextMenu
from browser.baselistwidget import BaseInlineIconWidget
from browser.baselistwidget import BaseModel
import browser.editors as editors
from browser.delegate import AssetWidgetDelegate

from browser.settings import AssetSettings
from browser.settings import local_settings, Active, active_monitor
from browser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite


class AssetWidgetContextMenu(BaseContextMenu):
    """The context menu associated with the AssetWidget."""

    def __init__(self, index, parent=None):
        super(AssetWidgetContextMenu, self).__init__(index, parent=parent)
        if index.isValid():
            self.add_mode_toggles_menu()
            self.add_thumbnail_menu()

        self.add_separator()

        if index.isValid():
            self.add_reveal_folder_menu()
            self.add_copy_menu()

        self.add_separator()

        self.add_sort_menu()
        self.add_display_toggles_menu()

        self.add_separator()

        self.add_refresh_menu()


class AssetModel(BaseModel):
    """The model associated with the assets views."""

    def __init__(self, parent=None):
        self.bookmark = None
        super(AssetModel, self).__init__(parent=parent)
        self.modelDataResetRequested.connect(self.__resetdata__)

    def __initdata__(self):
        """Querries the bookmark folder and collects the found asset itemsself.

        The model uses `self.model_data (dict)` to read the values needed to
        display the found items. Calling this method will reset / repopulate
        the dictionary.

        """
        self.beginResetModel()
        self.model_data = {}  # reset
        active_paths = Active.get_active_paths()
        favourites = local_settings.value(u'favourites')
        favourites = favourites if favourites else []

        if not self.bookmark:
            self.endResetModel()
            return
        if not all(self.bookmark):
            self.endResetModel()
            return

        rowsize = QtCore.QSize(common.WIDTH, common.ASSET_ROW_HEIGHT)

        server, job, root = self.bookmark
        bookmark_path = '{}/{}/{}'.format(server, job, root)
        itdir = QtCore.QDir(bookmark_path)
        itdir.setFilter(QtCore.QDir.NoDotAndDotDot | QtCore.QDir.Dirs)
        itdir.setSorting(QtCore.QDir.Unsorted)
        it = QtCore.QDirIterator(itdir,
                                 flags=QtCore.QDirIterator.NoIteratorFlags)

        thumbnail_path = '{}/../rsc/placeholder.png'.format(__file__)
        thumbnail_image = ImageCache.instance().get(
            thumbnail_path, rowsize.height() - 2)

        while it.hasNext():
            filepath = it.next()
            filename = it.fileName()

            identifier = QtCore.QDir(it.filePath()).entryList(
                (common.ASSET_IDENTIFIER, ),
                filters=QtCore.QDir.Files |
                QtCore.QDir.NoDotAndDotDot
            )
            if not identifier:
                continue

            tooltip = u'{}\n'.format(filename.upper())
            tooltip += u'{}\n'.format(server.upper())
            tooltip += u'{}\n'.format(job.upper())
            tooltip += u'{}'.format(filepath)

            self.model_data[len(self.model_data)] = {
                QtCore.Qt.DisplayRole: filename,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: it.filePath(),
                QtCore.Qt.ToolTipRole: tooltip,
                QtCore.Qt.SizeHintRole: rowsize,
                common.FlagsRole: QtCore.Qt.NoItemFlags,
                common.ParentRole: (server, job, root, filename),
                common.DescriptionRole: u'',
                common.TodoCountRole: 0,
                common.FileDetailsRole: it.fileInfo().size(),
                common.ThumbnailRole: thumbnail_image,
                common.ThumbnailBackgroundRole: QtGui.QColor(0,0,0,0),
                common.TypeRole: common.AssetItem,
                common.SortByName: filename,
                common.SortByLastModified: it.fileInfo().lastModified().toMSecsSinceEpoch(),
                common.SortBySize: 0,
            }

        for n in xrange(self.rowCount()):
            index = self.index(n, 0, parent=QtCore.QModelIndex())
            settings = AssetSettings(index)
            flags = (
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsEditable
            )
            filename = index.data(QtCore.Qt.DisplayRole)
            filepath = index.data(QtCore.Qt.StatusTipRole)

            if filename == active_paths[u'asset']:
                flags = flags | MarkedAsActive
            if settings.value(u'config/archived'):
                flags = flags | MarkedAsArchived
            if filepath in favourites:
                flags = flags | MarkedAsFavourite
            self.model_data[index.row()][common.FlagsRole] = flags

            # Todos
            todos = settings.value(u'config/todos')
            todocount = 0
            if todos:
                todocount = len([k for k in todos if not todos[k]
                             [u'checked'] and todos[k][u'text']])
            else:
                todocount = 0
            self.model_data[index.row()][common.TodoCountRole] = todocount

            description = settings.value(u'config/description')
            self.model_data[index.row()][common.DescriptionRole] = description
            self.model_data[index.row()][common.SortByName] = '{}{}'.format(filename, todocount)
            self.model_data[index.row()][common.SortBySize] = todocount
            
        # file-monitor timestamp
        self._last_refreshed[None] = time.time()
        self.endResetModel()

    @QtCore.Slot(QtCore.QModelIndex)
    def setBookmark(self, index):
        """Sets a new bookmark for the model and resets the model_data object."""
        if not index.isValid():
            return
        if index.data(common.ParentRole) == self.bookmark:
            return
        self.bookmark = index.data(common.ParentRole)
        self.modelDataResetRequested.emit()


class AssetWidget(BaseInlineIconWidget):
    """View for displaying the model items."""

    def __init__(self, parent=None):
        super(AssetWidget, self).__init__(parent=parent)
        self.setWindowTitle(u'Assets')
        self.setItemDelegate(AssetWidgetDelegate(parent=self))
        self.context_menu_cls = AssetWidgetContextMenu

        self.set_model(AssetModel(parent=self))

    def eventFilter(self, widget, event):
        super(AssetWidget, self).eventFilter(widget, event)
        if widget is not self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            # Let's paint the icon of the current mode
            painter = QtGui.QPainter()
            painter.begin(self)
            pixmap = ImageCache.get_rsc_pixmap(
                'assets', QtGui.QColor(0, 0, 0, 10), 200)
            rect = pixmap.rect()
            rect.moveCenter(self.rect().center())
            painter.drawPixmap(rect, pixmap, pixmap.rect())
            painter.end()
            return True
        return False

    def inline_icons_count(self):
        """The number of icons on the right-hand side."""
        return 4

    def activate_current_index(self):
        """Sets the current item item as ``active`` and
        emits the ``activeAssetChanged`` and ``activeFileChanged`` signals.

        """
        if not super(AssetWidget, self).activate_current_index():
            return
        index = self.selectionModel().currentIndex()

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        local_settings.setValue(u'activepath/asset', file_info.fileName())
        Active.get_active_paths()  # Resetting invalid paths

        # By updating the saved state we're making sure the active_monit doesn't emit the assetChangedSignal
        # (we don't want to trigger two update model updates)
        active_monitor.update_saved_state(u'asset', file_info.fileName())
        self.model().sourceModel().activeAssetChanged.emit(index)

    def show_todos(self):
        """Shows the ``TodoEditorWidget`` for the current item."""
        from browser.todoEditor import TodoEditorWidget
        widget = TodoEditorWidget(self.currentIndex(), parent=self)
        widget.show()

    def mouseDoubleClickEvent(self, event):
        """Custom double-click event.

        A double click can `activate` an item, or it can trigger an edit event.
        As each item is associated with multiple editors we have to inspect
        the double-click location before deciding what action to take.

        """
        index = self.indexAt(event.pos())
        rect = self.visualRect(index)
        #
        thumbnail_rect = QtCore.QRect(rect)
        thumbnail_rect.setWidth(rect.height())
        thumbnail_rect.moveLeft(common.INDICATOR_WIDTH)
        #
        name_rect = QtCore.QRect(rect)
        name_rect.setLeft(
            common.INDICATOR_WIDTH +
            name_rect.height() +
            common.MARGIN
        )
        name_rect.setRight(name_rect.right() - common.MARGIN)

        font = QtGui.QFont(common.PrimaryFont)
        metrics = QtGui.QFontMetrics(font)

        name_rect.moveTop(name_rect.top() + (name_rect.height() / 2.0))
        name_rect.setHeight(metrics.height())
        name_rect.moveTop(name_rect.top() - (name_rect.height() / 2.0))
        #
        description_rect = QtCore.QRect(rect)
        font = QtGui.QFont(common.SecondaryFont)
        metrics = QtGui.QFontMetrics(font)

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
        else:
            self.activate_current_index()
            return
