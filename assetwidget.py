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
import functools
from PySide2 import QtWidgets, QtCore, QtGui

from browser.utils.utils import ModelWorker

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

    def __init__(self, bookmark, parent=None):
        self.bookmark = bookmark
        super(AssetModel, self).__init__(parent=parent)

    def __initdata__(self):
        """Querries the bookmark folder and collects the found asset items.

        The model uses `self.model_data (dict)` to read the values needed to
        display the found items. Calling this method will reset / repopulate
        the dictionary.

        """
        self.model_data = {}  # reset
        active_paths = Active.get_active_paths()

        server, job, root = self.bookmark
        if not all((server, job, root)):
            return

        # Creating folders
        config_dir_path = u'{}/.browser/'.format(
            u'/'.join(self.bookmark))
        config_dir_path = QtCore.QFileInfo(config_dir_path)
        if not config_dir_path.exists():
            QtCore.QDir().mkpath(config_dir_path.filePath())

        # Resetting the path-monitor
        monitored = self._file_monitor.directories()
        self._file_monitor.removePaths(monitored)
        self._file_monitor.addPath(u'/'.join(self.bookmark))

        dir_ = QtCore.QDir(u'/'.join(self.bookmark))
        dir_.setFilter(QtCore.QDir.NoDotAndDotDot |
                       QtCore.QDir.Dirs |
                       QtCore.QDir.Readable)
        it = QtCore.QDirIterator(
            dir_, flags=QtCore.QDirIterator.NoIteratorFlags)

        idx = 0
        while it.hasNext():
            # Validate assets by skipping folders without the identifier file
            it.next()
            identifier = QtCore.QDir(it.filePath()).entryList(
                (common.ASSET_IDENTIFIER, ),
                filters=QtCore.QDir.Files |
                QtCore.QDir.NoDotAndDotDot
            )
            if not identifier:
                continue

            # Flags
            flags = (
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsEditable
            )

            # Active
            if it.fileName() == active_paths[u'asset']:
                flags = flags | MarkedAsActive

            # Archived
            settings = AssetSettings((server, job, root, it.filePath()))
            if settings.value(u'config/archived'):
                flags = flags | MarkedAsArchived

            # Favourite
            favourites = local_settings.value(u'favourites')
            favourites = favourites if favourites else []
            if it.filePath() in favourites:
                flags = flags | MarkedAsFavourite

            # Todos
            todos = settings.value(u'config/todos')
            if todos:
                count = len([k for k in todos if not todos[k]
                             [u'checked'] and todos[k][u'text']])
            else:
                count = 0

            tooltip = u'{}\n'.format(it.fileName().upper())
            tooltip += u'{}\n'.format(server.upper())
            tooltip += u'{}\n'.format(job.upper())
            tooltip += u'{}'.format(it.filePath())
            self.model_data[idx] = {
                QtCore.Qt.DisplayRole: it.fileName(),
                QtCore.Qt.EditRole: it.fileName(),
                QtCore.Qt.StatusTipRole: it.filePath(),
                QtCore.Qt.ToolTipRole: tooltip,
                QtCore.Qt.SizeHintRole: QtCore.QSize(common.WIDTH, common.ASSET_ROW_HEIGHT),
                common.FlagsRole: flags,
                # parent includes the asset
                common.ParentRole: (server, job, root, it.fileName()),
                common.DescriptionRole: settings.value(u'config/description'),
                common.TodoCountRole: count,
                common.FileDetailsRole: it.fileInfo().size(),
            }

            common.cache_image(
                settings.thumbnail_path(),
                common.ASSET_ROW_HEIGHT - 2)

            idx += 1

        self._last_refreshed[self.get_location()] = time.time() # file-monitor timestamp

    def get_location(self):
        """There is no location associated with the asset widget,
        Needed context menu functionality only."""
        return None

    def set_bookmark(self, bookmark):
        """Sets a new bookmark for the model and resets the model_data object."""
        self.bookmark = bookmark
        self.beginResetModel()
        self.__initdata__()
        self.endResetModel()


class AssetWidget(BaseInlineIconWidget):
    """View for displaying the model items."""

    def __init__(self, bookmark, parent=None):
        super(AssetWidget, self).__init__(parent=parent)
        self.setWindowTitle(u'Assets')
        self.setItemDelegate(AssetWidgetDelegate(parent=self))
        self.context_menu_cls = AssetWidgetContextMenu
        self.set_model(AssetModel(bookmark))

        self.model().sourceModel().refreshRequested.connect(self.refresh)

    def eventFilter(self, widget, event):
        super(AssetWidget, self).eventFilter(widget, event)
        if widget is not self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            #Let's paint the icon of the current mode
            painter = QtGui.QPainter()
            painter.begin(self)
            pixmap = common.get_rsc_pixmap('assets', QtGui.QColor(0,0,0,10), 200)
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
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        reset_needed = not index.flags() & MarkedAsActive

        if not super(AssetWidget, self).activate_current_index():
            return

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        local_settings.setValue(u'activepath/asset', file_info.fileName())
        Active.get_active_paths()  # Resetting invalid paths

        # By updating the saved state we're making sure the active_monit doesn't emit the assetChangedSignal
        # (we don't want to trigger two update model updates)
        active_monitor.update_saved_state(u'asset', file_info.fileName())
        self.model().sourceModel().activeAssetChanged.emit(index.data(common.ParentRole))

        # Activating a new item will require the filesmodel to be updated
        if reset_needed:
            self.model().sourceModel().modelDataResetRequested.emit()  # resetting the fileModel

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
            editors.PickThumbnailDialog(index, parent=self)
            return
        else:
            self.activate_current_index()
            return
