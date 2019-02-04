# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101

"""Definitions for the asset model/view classes.

An asset refers is a folder with a ``workspace.mel`` identifier file present, containing a
`scenes`, `renders`, `textures` and `exports` folders. Both the identifier files
and name of the above folders can be customized in the ``browser.commons`` module.

Each asset can be annoted with a description, thumbnail, and todo items. These
values are stored in the ``bookmark/.browser`` folder.

"""

from PySide2 import QtWidgets, QtCore

import browser.common as common
from browser.baselistwidget import BaseContextMenu
from browser.baselistwidget import BaseInlineIconWidget
from browser.baselistwidget import BaseModel
import browser.editors as editors
from browser.delegate import AssetWidgetDelegate

from browser.settings import AssetSettings
from browser.settings import local_settings, path_monitor
from browser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite


class AssetWidgetContextMenu(BaseContextMenu):
    """The context menu associated with the AssetWidget."""

    def __init__(self, index, parent=None):
        super(AssetWidgetContextMenu, self).__init__(index, parent=parent)
        # Adding persistent actions
        self.add_sort_menu()
        self.add_display_toggles_menu()
        if index.isValid():
            self.add_reveal_folder_menu()
            self.add_copy_menu()
            self.add_mode_toggles_menu()
            self.add_thumbnail_menu()
        self.add_refresh_menu()


class AssetModel(BaseModel):
    """The model associated with the assets views."""

    def __init__(self, bookmark, parent=None):
        self.bookmark = bookmark
        super(AssetModel, self).__init__(parent=parent)

    def __initdata__(self):
        """Querries the bookmark folder and collects the found asset items.

        The model uses `self.internal_data (dict)` to read the values needed to
        display the found items. Calling this method will reset / repopulate
        the dictionary.

        """
        self.internal_data = {}  # reset
        active_paths = path_monitor.get_active_paths()

        server, job, root = self.bookmark
        if not all((server, job, root)):
            return

        # Creating folders
        config_dir_path = '{}/.browser/'.format(
            '/'.join(self.bookmark))
        config_dir_path = QtCore.QFileInfo(config_dir_path)
        if not config_dir_path.exists():
            QtCore.QDir().mkpath(config_dir_path.filePath())

        dir_ = QtCore.QDir('/'.join(self.bookmark))
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
            if it.fileName() == active_paths['asset']:
                flags = flags | MarkedAsActive

            # Archived
            settings = AssetSettings((server, job, root, it.filePath()))
            if settings.value('config/archived'):
                flags = flags | MarkedAsArchived

            # Favourite
            favourites = local_settings.value('favourites')
            favourites = favourites if favourites else []
            if it.filePath() in favourites:
                flags = flags | MarkedAsFavourite

            # Todos
            todos = settings.value('config/todos')
            if todos:
                count = len([k for k in todos if not todos[k]
                             ['checked'] and todos[k]['text']])
            else:
                count = 0

            tooltip = u'{}\n'.format(it.fileName().upper())
            tooltip += u'{}\n'.format(server.upper())
            tooltip += u'{}\n'.format(job.upper())
            tooltip += u'{}'.format(it.filePath())
            self.internal_data[idx] = {
                QtCore.Qt.DisplayRole: it.fileName(),
                QtCore.Qt.EditRole: it.fileName(),
                QtCore.Qt.StatusTipRole: it.filePath(),
                QtCore.Qt.ToolTipRole: tooltip,
                QtCore.Qt.SizeHintRole: QtCore.QSize(common.WIDTH, common.ASSET_ROW_HEIGHT),
                common.FlagsRole: flags,
                # parent includes the asset
                common.ParentRole: (server, job, root, it.fileName()),
                common.DescriptionRole: settings.value('config/description'),
                common.TodoCountRole: count,
                common.FileDetailsRole: it.fileInfo().size(),
            }

            common.cache_image(
                settings.thumbnail_path(),
                common.ASSET_ROW_HEIGHT - 2)

            idx += 1

    def set_bookmark(self, bookmark):
        """Sets a new bookmark for the model and resets the internal_data object."""
        self.bookmark = bookmark
        self.beginResetModel()
        self.__initdata__()
        self.endResetModel()


class AssetWidget(BaseInlineIconWidget):
    """View for displaying the model items."""

    def __init__(self, bookmark, parent=None):
        super(AssetWidget, self).__init__(AssetModel(bookmark), parent=parent)
        self.setWindowTitle('Assets')
        self.setItemDelegate(AssetWidgetDelegate(parent=self))
        self.context_menu_cls = AssetWidgetContextMenu

        # Select the active item
        self.selectionModel().setCurrentIndex(
            self.active_index(),
            QtCore.QItemSelectionModel.ClearAndSelect
        )

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

        # Activating a new item will require the filesmodel to be updated
        needs_reset = not index.flags() & MarkedAsActive

        if not super(AssetWidget, self).activate_current_index():
            return

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        local_settings.setValue('activepath/asset', file_info.fileName())

        path_monitor.get_active_paths()  # Resetting invalid paths
        self.model().sourceModel().activeAssetChanged.emit(index.data(common.ParentRole))
        if needs_reset:
            self.model().sourceModel().modelResetRequested.emit()  # resetting model

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

        thumbnail_rect = QtCore.QRect(rect)
        thumbnail_rect.setWidth(rect.height())
        thumbnail_rect.moveLeft(common.INDICATOR_WIDTH)

        name_rect, _, metrics = AssetWidgetDelegate.get_text_area(
            rect, common.PRIMARY_FONT)
        name_rect.moveTop(name_rect.top() + (name_rect.height() / 2.0))
        name_rect.setHeight(metrics.height())
        name_rect.moveTop(name_rect.top() - (name_rect.height() / 2.0))

        description_rect, _, metrics = AssetWidgetDelegate.get_text_area(
            rect, common.SECONDARY_FONT)
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
            editors.ThumbnailEditor(index, parent=self)
            return
        else:
            self.activate_current_index()
            return
