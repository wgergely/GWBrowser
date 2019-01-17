# -*- coding: utf-8 -*-
"""Module defines a ListWidget used to represent the assets found in the root
of the `server/job/assets` folder.

The asset collector expects a asset to contain an identifier file,
in the case of the default implementation, a ``*.mel`` file in the root of the asset folder.
If the identifier file is not found the folder will be ignored!

Assets are based on maya's project structure and ``Browser`` expects a
a ``renders``, ``textures``, ``exports`` and a ``scenes`` folder to be present.

The actual name of these folders can be customized in the ``common.py`` module.

"""
# pylint: disable=E1101, C0103, R0913, I1101

from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common
from mayabrowser.listbase import BaseContextMenu
from mayabrowser.listbase import BaseListWidget
import mayabrowser.editors as editors

import mayabrowser.configparsers as configparser
from mayabrowser.configparsers import local_settings, path_monitor
from mayabrowser.configparsers import AssetSettings
from mayabrowser.collector import AssetCollector
from mayabrowser.delegate import AssetWidgetDelegate


class AssetWidgetContextMenu(BaseContextMenu):
    """Context menu associated with the AssetWidget."""
    def __init__(self, index, parent=None):
        super(AssetWidgetContextMenu, self).__init__(index, parent=parent)
        self.add_thumbnail_menu()
        self.add_refresh_menu()




class AssetWidget(BaseListWidget):
    """Custom QListWidget for displaying the found assets inside the set ``path``.

    Signals:
        activated (Signal):         Signal emited when the active asset has changed.

    Properties:
        path (tuple[str, str, str]):    Sets the path to search for assets.

    """
    def __init__(self, parent=None):
        super(AssetWidget, self).__init__(
            (local_settings.value('activepath/server'),
             local_settings.value('activepath/job'),
             local_settings.value('activepath/root')),
            parent=parent
        )
        self.setWindowTitle('Assets')
        self.setItemDelegate(AssetWidgetDelegate(parent=self))
        self._context_menu_cls = AssetWidgetContextMenu
        # Select the active item
        self.setCurrentItem(self.active_item())

    def set_current_item_as_active(self):
        """Sets the current item item as ``active`` and
        emits the ``activeAssetChanged`` and ``activeFileChanged`` signals.

        """
        super(AssetWidget, self).set_current_item_as_active()
        file_info = QtCore.QFileInfo(self.currentItem().data(common.PathRole))
        local_settings.setValue('activepath/asset', file_info.baseName())
        local_settings.setValue('activepath/file', None)

        self.activeAssetChanged.emit(file_info.baseName())
        self.activeFileChanged.emit(None)

    def add_items(self):
        """Retrieves the assets found by the AssetCollector and adds them as
        QListWidgetItems.

        Note:
            The method adds the assets' parent folder to the QFileSystemWatcher to monitor
            file changes. Any directory change should trigger a refresh. This might
            have some performance implications. Needs testing!

        """
        for path in self.fileSystemWatcher.directories():
            self.fileSystemWatcher.removePath(path)
        self.clear()

        active_paths = path_monitor.get_active_paths()
        if not any((active_paths['server'], active_paths['job'], active_paths['root'])):
            return

        path = '/'.join((active_paths['server'], active_paths['job'], active_paths['root']))

        self.fileSystemWatcher.addPath(path)
        collector = AssetCollector(path, parent=self)
        items = collector.get_items(
            key=self.get_item_sort_order(),
            reverse=self.is_item_sort_reversed(),
            path_filter=self.get_item_filter()
        )

        for file_info in items:
            item = QtWidgets.QListWidgetItem()
            settings = AssetSettings(file_info.filePath())

            # Qt Roles
            item.setData(QtCore.Qt.DisplayRole, file_info.baseName())
            item.setData(QtCore.Qt.EditRole, item.data(QtCore.Qt.DisplayRole))
            item.setData(QtCore.Qt.StatusTipRole, file_info.filePath())

            tooltip = u'{}\n\n'.format(file_info.baseName().upper())
            tooltip += u'{}\n'.format(active_paths['server'].upper())
            tooltip += u'{}\n\n'.format(active_paths['job'].upper())
            tooltip += u'{}'.format(file_info.filePath())
            item.setData(QtCore.Qt.ToolTipRole, tooltip)
            item.setData(
                QtCore.Qt.SizeHintRole,
                QtCore.QSize(common.WIDTH, common.ASSET_ROW_HEIGHT))

            # Custom roles
            item.setData(common.PathRole, file_info.filePath())
            item.setData(common.ParentRole, (
                active_paths['server'],
                active_paths['job'],
                active_paths['root'],
                file_info.baseName(),
                None))
            item.setData(common.DescriptionRole, settings.value(
                'config/description'))

            # Todos
            todos = settings.value('config/todos')
            if todos:
                count = len([k for k in todos if not todos[k]
                             ['checked'] and todos[k]['text']])
            else:
                count = 0
            item.setData(common.TodoCountRole, count)
            item.setData(common.FileDetailsRole, file_info.size())
            item.setData(common.FileModeRole, None)

            # Flags
            if settings.value('config/archived'):
                item.setFlags(item.flags() | configparser.MarkedAsArchived)
            # Favourite
            favourites = local_settings.value('favourites')
            favourites = favourites if favourites else []
            if file_info.filePath() in favourites:
                item.setFlags(item.flags() | configparser.MarkedAsFavourite)

            if file_info.baseName() == local_settings.value('activepath/asset'):
                item.setFlags(item.flags() | configparser.MarkedAsActive)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)

            self.addItem(item)

    def mousePressEvent(self, event):
        """In-line buttons are triggered here."""
        index = self.indexAt(event.pos())
        rect = self.visualRect(index)
        if self.viewport().width() < 360.0:
            return super(AssetWidget, self).mousePressEvent(event)

        for n in xrange(2):
            _, bg_rect = self.itemDelegate().get_inline_icon_rect(
                rect, common.INLINE_ICON_SIZE, n)
            # Beginning multi-toggle operation
            if bg_rect.contains(event.pos()):
                self.multi_toggle_pos = event.pos()
                if n == 0:
                    self.multi_toggle_state = not index.flags() & configparser.MarkedAsFavourite
                elif n == 1:
                    self.multi_toggle_state = not index.flags() & configparser.MarkedAsArchived
                self.multi_toggle_idx = n
                return True

        return super(AssetWidget, self).mousePressEvent(event)

    def show_todos(self):
        """Shows the ``TodoEditorWidget`` for the current item."""
        from mayabrowser.todoEditor import TodoEditorWidget
        index = self.currentIndex()
        rect = self.visualRect(index)
        widget = TodoEditorWidget(index, parent=self)
        pos = self.mapToGlobal(self.rect().topLeft())
        widget.move(pos.x() + common.MARGIN, pos.y() + common.MARGIN)
        widget.setMinimumWidth(640)
        widget.setMinimumHeight(800)
        # widget.resize(self.width(), self.height())
        common.move_widget_to_available_geo(widget)
        widget.show()

    def mouseReleaseEvent(self, event):
        """In-line buttons are triggered here."""
        index = self.indexAt(event.pos())
        rect = self.visualRect(index)
        idx = index.row()

        if self.viewport().width() < 360.0:
            return super(AssetWidget, self).mouseReleaseEvent(event)

        # Cheking the button
        if idx not in self.multi_toggle_items:
            for n in xrange(4):
                _, bg_rect = self.itemDelegate().get_inline_icon_rect(
                    rect, common.INLINE_ICON_SIZE, n)
                if bg_rect.contains(event.pos()):
                    if n == 0:
                        self.toggle_favourite(item=self.itemFromIndex(index))
                        break
                    elif n == 1:
                        self.toggle_archived(item=self.itemFromIndex(index))
                        break
                    elif n == 2:
                        self.reveal_folder('')
                    elif n == 3:
                        self.show_todos()

        super(AssetWidget, self).mouseReleaseEvent(event)

        self.multi_toggle_pos = None
        self.multi_toggle_state = None
        self.multi_toggle_idx = None
        self.multi_toggle_item = None
        self.multi_toggle_items = {}

    def mouseMoveEvent(self, event):
        """Multi-toggle is handled here."""
        if self.viewport().width() < 360.0:
            return super(AssetWidget, self).mouseMoveEvent(event)

        if self.multi_toggle_pos is None:
            super(AssetWidget, self).mouseMoveEvent(event)
            return

        app_ = QtWidgets.QApplication.instance()
        if (event.pos() - self.multi_toggle_pos).manhattanLength() < app_.startDragDistance():
            super(AssetWidget, self).mouseMoveEvent(event)
            return

        pos = event.pos()
        pos.setX(0)
        index = self.indexAt(pos)
        initial_index = self.indexAt(self.multi_toggle_pos)
        idx = index.row()

        favourite = index.flags() & configparser.MarkedAsFavourite
        archived = index.flags() & configparser.MarkedAsArchived

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
                self.toggle_favourite(
                    item=self.itemFromIndex(index),
                    state=self.multi_toggle_state
                )
            if self.multi_toggle_idx == 1:  # Archived button
                # A state
                self.multi_toggle_items[idx] = archived
                # Apply first state
                self.toggle_archived(
                    item=self.itemFromIndex(index),
                    state=self.multi_toggle_state
                )
        else:  # Reset state
            if index == initial_index:
                return
            if self.multi_toggle_idx == 0:  # Favourite button
                self.toggle_favourite(
                    item=self.itemFromIndex(index),
                    state=self.multi_toggle_items.pop(idx)
                )
            elif self.multi_toggle_idx == 1:  # Favourite button
                self.toggle_archived(
                    item=self.itemFromIndex(index),
                    state=self.multi_toggle_items.pop(idx)
                )

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
            editors.ThumbnailEditor(index)
            return
        else:
            self.set_current_item_as_active()
            return

    def action_on_enter_key(self):
        """Custom enter key action."""
        self.set_current_item_as_active()

    def action_on_custom_keys(self, event):
        """Custom keyboard shortcuts for the AssetsWidget are defined here.
        """
        item = self.currentItem()
        if not item:
            return

        data = item.data(QtCore.Qt.StatusTipRole)

        if event.modifiers() & QtCore.Qt.NoModifier:
            if event.key() == QtCore.Qt.Key_Enter:
                self.set_current_item_as_active()
        elif event.modifiers() & QtCore.Qt.AltModifier:
            if event.key() == QtCore.Qt.Key_C:
                url = QtCore.QUrl()
                url = url.fromLocalFile(
                    item.data(common.PathRole))
                QtGui.QClipboard().setText(url.toString())

    def reveal_folder(self, name):
        """Reveals the specified folder in the file explorer.

        Args:
            name (str): A relative path or the folder's name.

        """
        item = self.currentItem()
        path = '{}/{}'.format(
            item.data(QtCore.Qt.StatusTipRole),
            name
        )
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def _warning_strings(self):
        """Custom warning strings to paint."""
        active_paths = path_monitor.get_active_paths()
        file_info = QtCore.QFileInfo('{}/{}/{}'.format(active_paths['server'], active_paths['job'], active_paths['root']))

        warning_one = 'No Bookmark has been set yet.\nAssets will be shown here after activating a Bookmark.'
        warning_two = 'Invalid Bookmark set.\nServer: {}\nJob: {}\nRoot: {}'
        warning_three = 'The active bookmark does not exist.\nBookmark: {}'
        warning_four = 'The active bookmark ({}/{}/{}) does not contain any assets...yet.'
        warning_five = '{} items are hidden by filters'

        if not all((active_paths['server'], active_paths['job'], active_paths['root'])):
            return warning_one
        if not any((active_paths['server'], active_paths['job'], active_paths['root'])):
            return warning_two.format(
                active_paths['server'], active_paths['job'], active_paths['root']
            )
        if not file_info.exists():
            return warning_three.format('/'.join((active_paths['server'], active_paths['job'], active_paths['root'])))

        if not self.count():
            return warning_four.format(active_paths['server'], active_paths['job'], active_paths['root'])

        if self.count() > self.count_visible():
            return warning_five.format(
                self.count() - self.count_visible())

        return ''

    def eventFilter(self, widget, event):
        """AssetWidget's custom paint is triggered here.

        I'm using the custom paint event to display a user message when no
        asset or files can be found.

        """
        if event.type() == QtCore.QEvent.Paint:
            self.paint_message(self._warning_strings())
        return False


if __name__ == '__main__':
    app = QtWidgets.QApplication([])

    app.w = AssetWidget()
    app.w.show()
    app.exec_()
