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
import os
from PySide2 import QtWidgets, QtCore, QtGui

import gwbrowser.gwscandir as gwscandir
from gwbrowser.imagecache import ImageCache
import gwbrowser.common as common
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.baselistwidget import BaseInlineIconWidget
from gwbrowser.baselistwidget import BaseModel
import gwbrowser.editors as editors
from gwbrowser.delegate import AssetsWidgetDelegate

from gwbrowser.settings import AssetSettings
from gwbrowser.settings import local_settings, Active, active_monitor
from gwbrowser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite


class AssetsWidgetContextMenu(BaseContextMenu):
    """The context menu associated with the AssetsWidget."""

    def __init__(self, index, parent=None):
        super(AssetsWidgetContextMenu, self).__init__(index, parent=parent)
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
        bookmark_path = u'{}/{}/{}'.format(server, job, root)

        default_thumbnail_image = ImageCache.instance().get(
            common.rsc_path(__file__, u'placeholder'),
            rowsize.height() - 2)
        default_background_color = QtGui.QColor(0, 0, 0, 55)

        nth = 1
        c = 0
        for entry in gwscandir.scandir(bookmark_path):
            if entry.name.startswith(u'.'):
                continue
            if not entry.is_dir():
                continue

            if common.ASSET_IDENTIFIER not in [f.name for f in gwscandir.scandir(entry.path)]:
                continue

            # Progress bar
            c += 1
            if not c % nth:
                m = self.messageChanged.emit(u'Found {} assets...'.format(c))
                QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

            tooltip = u'{}\n'.format(entry.name.upper())
            tooltip += u'{}\n'.format(server.upper())
            tooltip += u'{}\n'.format(job.upper())
            tooltip += u'{}'.format(entry.path.replace(u'\\', u'/'))

            data = self.model_data()
            idx = len(data)
            data[idx] = {
                QtCore.Qt.DisplayRole: entry.name,
                QtCore.Qt.EditRole: entry.name,
                QtCore.Qt.StatusTipRole: entry.path.replace(u'\\', u'/'),
                QtCore.Qt.ToolTipRole: tooltip,
                QtCore.Qt.SizeHintRole: rowsize,
                #
                common.FlagsRole: QtCore.Qt.NoItemFlags,
                common.ParentRole: (server, job, root, entry.name),
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
                common.SortByName: entry.path.replace(u'\\', u'/'),
                common.SortByLastModified: entry.path.replace(u'\\', u'/'),
                common.SortBySize: entry.path.replace(u'\\', u'/'),
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

            if entry.name == active_paths[u'asset']:
                flags = flags | MarkedAsActive
            if settings.value(u'config/archived'):
                flags = flags | MarkedAsArchived
            if entry.path.replace(u'\\', u'/') in favourites:
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
            data[idx][common.SortBySize] = todocount

            # Only including this for compatibility with the methods used by the file-items
            data[idx][common.StatusRole] = True

        self.endResetModel()


class AssetsWidget(BaseInlineIconWidget):
    """View for displaying the model items."""

    def __init__(self, parent=None):
        super(AssetsWidget, self).__init__(parent=parent)
        self.setWindowTitle(u'Assets')
        self.setItemDelegate(AssetsWidgetDelegate(parent=self))
        self.context_menu_cls = AssetsWidgetContextMenu

        self.set_model(AssetModel(parent=self))

    def eventFilter(self, widget, event):
        super(AssetsWidget, self).eventFilter(widget, event)
        if widget is not self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            # Let's paint the icon of the current mode
            painter = QtGui.QPainter()
            painter.begin(self)
            pixmap = ImageCache.get_rsc_pixmap(
                'assets', QtGui.QColor(0, 0, 0, 10), 128)
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
        local_settings.setValue(u'activepath/asset', index.data(common.ParentRole)[-1])
        Active.paths()  # Resetting invalid paths

    def mouseDoubleClickEvent(self, event):
        """Custom double-click event.

        A double click can `activate` an item, or it can trigger an edit event.
        As each item is associated with multiple editors we have to inspect
        the double-click location before deciding what action to take.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
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
