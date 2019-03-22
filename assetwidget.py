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

from gwbrowser.imagecache import ImageCache
import gwbrowser.common as common
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.baselistwidget import BaseInlineIconWidget
from gwbrowser.baselistwidget import BaseModel
import gwbrowser.editors as editors
from gwbrowser.delegate import AssetWidgetDelegate

from gwbrowser.settings import AssetSettings
from gwbrowser.settings import local_settings, Active, active_monitor
from gwbrowser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite


class AssetWidgetContextMenu(BaseContextMenu):
    """The context menu associated with the AssetWidget."""

    def __init__(self, index, parent=None):
        super(AssetWidgetContextMenu, self).__init__(index, parent=parent)
        if index.isValid():
            self.add_mode_toggles_menu()
            self.add_thumbnail_menu()

        self.add_separator()

        if index.isValid():
            self.add_reveal_item_menu()
            self.add_copy_menu()

        self.add_separator()

        self.add_sort_menu()
        self.add_display_toggles_menu()

        self.add_separator()

        self.add_refresh_menu()


class AssetModel(BaseModel):
    """The model associated with the assets views."""

    def __init__(self, parent=None):
        super(AssetModel, self).__init__(parent=parent)

    def __initdata__(self):
        """Querries the bookmark folder and collects the found asset itemsself.

        The model uses `self.model_data (dict)` to read the values needed to
        display the found items. Calling this method will reset / repopulate
        the dictionary.

        """
        self._data[self._datakey] = {
            common.FileItem: {}, common.SequenceItem: {}}

        rowsize = QtCore.QSize(common.WIDTH, common.ASSET_ROW_HEIGHT)
        active_paths = Active.paths()

        favourites = local_settings.value(u'favourites')
        favourites = favourites if favourites else []

        if not self._parent_item:
            self.endResetModel()
            return
        if not all(self._parent_item):
            self.endResetModel()
            return

        server, job, root = self._parent_item
        bookmark_path = '{}/{}/{}'.format(server, job, root)

        itdir = QtCore.QDir(bookmark_path)
        itdir.setFilter(QtCore.QDir.NoDotAndDotDot | QtCore.QDir.Dirs)
        itdir.setSorting(QtCore.QDir.Unsorted)
        it = QtCore.QDirIterator(itdir,
                                 flags=QtCore.QDirIterator.NoIteratorFlags)

        default_thumbnail_path = '{}/../rsc/placeholder.png'.format(__file__)
        default_thumbnail_image = ImageCache.instance().get(
            default_thumbnail_path, rowsize.height() - 2)
        default_background_color = QtGui.QColor(0, 0, 0, 0)

        while it.hasNext():
            filepath = it.next()
            filename = it.fileName()
            filepath = it.filePath()

            identifier = QtCore.QDir(filepath).entryList(
                (common.ASSET_IDENTIFIER, ),
                filters=QtCore.QDir.Files
                | QtCore.QDir.NoDotAndDotDot
            )
            if not identifier:
                continue

            tooltip = u'{}\n'.format(filename.upper())
            tooltip += u'{}\n'.format(server.upper())
            tooltip += u'{}\n'.format(job.upper())
            tooltip += u'{}'.format(filepath)

            data = self.model_data()
            idx = len(data)
            data[idx] = {
                QtCore.Qt.DisplayRole: filename,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.ToolTipRole: tooltip,
                QtCore.Qt.SizeHintRole: rowsize,
                #
                common.FlagsRole: QtCore.Qt.NoItemFlags,
                common.ParentRole: (server, job, root, filename),
                common.DescriptionRole: u'',
                common.TodoCountRole: 0,
                common.FileDetailsRole: None,
                #
                common.DefaultThumbnailRole: default_thumbnail_image,
                common.DefaultThumbnailBackgroundRole: default_background_color,
                common.ThumbnailPathRole: None,
                common.ThumbnailRole: default_thumbnail_image,
                common.ThumbnailBackgroundRole: default_background_color,
                #
                common.TypeRole: common.AssetItem,
                #
                common.SortByName: filename,
                common.SortByLastModified: it.fileInfo().lastModified().toMSecsSinceEpoch(),
                common.SortBySize: None,
            }

            index = self.index(idx, 0)
            settings = AssetSettings(index)
            data[idx][common.ThumbnailPathRole] = settings.thumbnail_path()

            image = ImageCache.instance().get(
                data[idx][common.ThumbnailPathRole],
                rowsize.height() - 2)

            if image:
                if not image.isNull():
                    color = ImageCache.instance().get(
                        data[idx][common.ThumbnailPathRole],
                        'BackgroundColor')

                    data[idx][common.ThumbnailRole] = image
                    data[idx][common.ThumbnailBackgroundRole] = color

            flags = (
                QtCore.Qt.ItemIsSelectable
                | QtCore.Qt.ItemIsEnabled
                | QtCore.Qt.ItemIsEditable
            )

            if filename == active_paths[u'asset']:
                flags = flags | MarkedAsActive
            if settings.value(u'config/archived'):
                flags = flags | MarkedAsArchived
            if filepath in favourites:
                flags = flags | MarkedAsFavourite
            data[idx][common.FlagsRole] = flags

            # Todos
            todos = settings.value(u'config/todos')
            todocount = 0
            if todos:
                todocount = len([k for k in todos if not todos[k]
                                 [u'checked'] and todos[k][u'text']])
            else:
                todocount = 0
            data[idx][common.TodoCountRole] = todocount

            description = settings.value(u'config/description')
            data[idx][common.DescriptionRole] = description
            data[idx][common.SortByName] = '{}{}'.format(
                filename, todocount)
            data[idx][common.SortBySize] = todocount

        self.endResetModel()


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

    def save_activated(self, index):
        """Sets the current item item as ``active`` and
        emits the ``activeChanged`` signal.

        """
        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        local_settings.setValue(u'activepath/asset', file_info.fileName())
        Active.paths()  # Resetting invalid paths

        # By updating the saved state we're making sure the active_monit doesn't emit the assetChangedSignal
        # (we don't want to trigger two update model updates)
        active_monitor.update_saved_state(u'asset', file_info.fileName())

    def show_todos(self, index):
        """Shows the ``TodoEditorWidget`` for the current item."""
        from gwbrowser.todoEditor import TodoEditorWidget
        source_index = self.model().mapToSource(index)
        widget = TodoEditorWidget(source_index, parent=self)
        widget.show()

    def mouseDoubleClickEvent(self, event):
        """Custom double-click event.

        A double click can `activate` an item, or it can trigger an edit event.
        As each item is associated with multiple editors we have to inspect
        the double-click location before deciding what action to take.

        """
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
        if index.flags() & MarkedAsArchived:
            return
            
        rect = self.visualRect(index)

        thumbnail_rect = QtCore.QRect(rect)
        thumbnail_rect.setWidth(rect.height())
        thumbnail_rect.moveLeft(common.INDICATOR_WIDTH)

        name_rect = QtCore.QRect(rect)
        name_rect.setLeft(
            common.INDICATOR_WIDTH
            + name_rect.height()
            + common.MARGIN
        )
        name_rect.setRight(name_rect.right() - common.MARGIN)

        font = QtGui.QFont(common.PrimaryFont)
        metrics = QtGui.QFontMetrics(font)

        name_rect.moveTop(name_rect.top() + (name_rect.height() / 2.0))
        name_rect.setHeight(metrics.height())
        name_rect.moveTop(name_rect.top() - (name_rect.height() / 2.0))

        description_rect = QtCore.QRect(rect)
        font = QtGui.QFont(common.SecondaryFont)
        metrics = QtGui.QFontMetrics(font)

        description_rect.moveTop(
            description_rect.top() + (description_rect.height() / 2.0))
        description_rect.setHeight(metrics.height())
        description_rect.moveTop(description_rect.top(
        ) - (description_rect.height() / 2.0) + metrics.lineSpacing())

        source_index = self.model().mapToSource(index)
        if description_rect.contains(event.pos()):
            widget = editors.DescriptionEditorWidget(source_index, parent=self)
            widget.show()
            return
        elif thumbnail_rect.contains(event.pos()):
            ImageCache.instance().pick(source_index)
            return
        self.activate(self.selectionModel().currentIndex())
