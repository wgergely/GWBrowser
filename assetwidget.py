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

from collections import OrderedDict
from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common
from mayabrowser.listbase import BaseContextMenu
from mayabrowser.listbase import BaseListWidget
import mayabrowser.editors as editors

import mayabrowser.configparsers as configparser
from mayabrowser.configparsers import local_settings
from mayabrowser.configparsers import AssetSettings
from mayabrowser.collector import AssetCollector
from mayabrowser.delegate import AssetWidgetDelegate
from mayabrowser.popover import PopupCanvas


class AssetWidgetContextMenu(BaseContextMenu):
    """Context menu associated with the AssetWidget.
    """

    def add_actions(self):
        if self.index.isValid():
            self.add_action_set(self.VALID_ACTION_SET)
            self.add_copy_menu()
        self.add_action_set(self.INVALID_ACTION_SET)

    def add_copy_menu(self):
        import functools

        def cp(s):
            QtGui.QClipboard().setText(s)

        menu = QtWidgets.QMenu(parent=self)
        menu.setTitle('Paths')

        # Url
        file_path = self.index.data(common.PathRole).filePath()
        url = QtCore.QUrl()
        url = url.fromLocalFile(file_path)

        action = menu.addAction('Slack / Web url')
        action.setEnabled(False)
        action = menu.addAction(url.toString())
        action.triggered.connect(functools.partial(cp, url.toString()))

        menu.addSeparator()

        action = menu.addAction('MacOS network path')
        action.setEnabled(False)
        action = menu.addAction(url.toString().replace('file://', 'smb://'))
        action.triggered.connect(functools.partial(
            cp, url.toString().replace('file://', 'smb://')))

        menu.addSeparator()

        action = menu.addAction('Path')
        action.setEnabled(False)
        action = menu.addAction(file_path)
        action.triggered.connect(functools.partial(cp, file_path))

        menu.addSeparator()

        action = menu.addAction('Windows path')
        action.setEnabled(False)
        action = menu.addAction(file_path)
        action.triggered.connect(functools.partial(
            cp, QtCore.QDir.toNativeSeparators(file_path)))

        self.addMenu(menu)
        self.addSeparator()

    @property
    def VALID_ACTION_SET(self):
        """A custom set of actions to display."""
        items = OrderedDict()
        item = self.parent().itemFromIndex(self.index)

        archived = item.flags() & configparser.MarkedAsArchived
        favourite = item.flags() & configparser.MarkedAsFavourite

        items['Activate'] = {}
        items['<separator>.'] = {}
        items['Capture thumbnail'] = {}
        items['Remove thumbnail'] = {}
        items['<separator>..'] = {}
        items['Favourite'] = {
            'checkable': True,
            'checked': bool(favourite)
        }
        items['Archived'] = {
            'checkable': True,
            'checked': bool(archived)
        }
        items['<separator>...'] = {}
        items['Show in explorer'] = {}
        return items

    @property
    def INVALID_ACTION_SET(self):
        items = OrderedDict()
        items['Show archived'] = {
            'checkable': True,
            'checked': self.parent().show_archived_mode
        }
        items['Isolate favourites'] = {
            'checkable': True,
            'checked': self.parent().show_favourites_mode
        }
        items['<separator>.....'] = {}
        items['Refresh'] = {}
        return items

    def activate(self):
        """Sets the current item as ``active``."""
        self.parent().set_current_item_as_active()

    def capture_thumbnail(self):
        self.parent().capture_thumbnail()

    def remove_thumbnail(self):
        self.parent().remove_thumbnail()

    def show_in_explorer(self):
        self.parent().reveal_folder('')

    def refresh(self):
        self.parent().refresh()



class AssetWidget(BaseListWidget):
    """Custom QListWidget for displaying the found assets inside the set ``path``.

    Signals:
        activeChanged (Signal):         Signal emited when the active asset has changed.

    Properties:
        path (tuple[str, str, str]):    Sets the path to search for assets.

    """
    Delegate = AssetWidgetDelegate
    ContextMenu = AssetWidgetContextMenu

    # Signals
    activated = QtCore.Signal(str)

    def __init__(self, root=None, parent=None):
        self._path = (
            local_settings.value('activepath/server'),
            local_settings.value('activepath/job'),
            local_settings.value('activepath/root')
        )
        super(AssetWidget, self).__init__(parent=parent)
        self.setWindowTitle('Assets')

    @property
    def path(self):
        """The path to the folder where the assets are located as a tuple of strings"""
        return self._path

    @path.setter
    def path(self, *args):
        self._path = args

    def set_current_item_as_active(self):
        """Sets the current item item as ``active``."""
        super(AssetWidget, self).set_current_item_as_active()

        # Updating the local config file
        asset = self.currentItem().data(common.PathRole).baseName()
        local_settings.setValue('activepath/asset', asset)

        # Emiting change a signal upon change
        self.activated.emit(asset)

    def show_popover(self):
        """Popup widget show on long-mouse-press."""
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        cursor = QtGui.QCursor()
        self.popover = PopupCanvas(cursor.pos())
        self.popover.show()

        click = QtGui.QMouseEvent(
            QtCore.QEvent.MouseButtonRelease, cursor.pos(),
            QtCore.Qt.LeftButton, 0,
            QtCore.Qt.NoModifier
        )
        QtCore.QCoreApplication.instance().sendEvent(self.popover, click)
        QtCore.QCoreApplication.instance().postEvent(self.popover, click)

    def refresh(self):
        """Refreshes the list of found assets."""
        # Remove QFileSystemWatcher paths:
        for path in self.fileSystemWatcher.directories():
            self.fileSystemWatcher.removePath(path)

        idx = self.currentIndex()
        self.add_items()
        self.set_row_visibility()
        self.setCurrentIndex(idx)

    def add_items(self):
        """Retrieves the assets found by the AssetCollector and adds them as
        QListWidgetItems.

        Note:
            The method adds the assets' parent folder to the QFileSystemWatcher to monitor
            file changes. Any directory change should trigger a refresh. This might
            have some performance implications. Needs testing!

        """
        self.clear()
        for path in self.fileSystemWatcher.directories():
            self.fileSystemWatcher.removePath(path)

        if not any(self.path):
            return

        err_one = 'An error occured when trying to collect the assets.\n\n{}'

        try:
            collector = AssetCollector('/'.join(self.path))
            self.fileSystemWatcher.addPath('/'.join(self.path))
        except IOError as err:
            return QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Warning,
                'Error',
                err_one.format(err.message)
            ).exec_()
        except Exception as err:
            return QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Warning,
                'Error',
                err_one.format(err.message)
            ).exec_()

        for f in collector.get():
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, f.baseName())
            item.setData(QtCore.Qt.EditRole,
                         item.data(QtCore.Qt.DisplayRole))
            item.setData(QtCore.Qt.StatusTipRole, f.filePath())
            tooltip = u'{}\n\n'.format(f.baseName().upper())
            tooltip += u'{}\n'.format(self._path[1].upper())
            tooltip += u'{}\n\n'.format(self._path[2].upper())
            tooltip += u'{}'.format(f.filePath())
            item.setData(QtCore.Qt.ToolTipRole, tooltip)
            item.setData(common.PathRole, f)
            item.setData(
                QtCore.Qt.SizeHintRole,
                QtCore.QSize(common.WIDTH, common.ASSET_ROW_HEIGHT))

            settings = AssetSettings(f.filePath())

            item.setData(common.DescriptionRole, settings.value(
                'config/description'))

            todos = settings.value('config/todos')
            if todos:
                todos = len([k for k in todos if not todos[k]['checked'] and todos[k]['text']])
                item.setData(common.TodoCountRole, todos)
            else:
                item.setData(common.TodoCountRole, 0)


            # Archived
            if settings.value('config/archived'):
                item.setFlags(item.flags() | configparser.MarkedAsArchived)

            # Favourite
            favourites = local_settings.value('favourites')
            favourites = favourites if favourites else []
            if f.filePath() in favourites:
                item.setFlags(item.flags() | configparser.MarkedAsFavourite)

            if f.baseName() == local_settings.value('activepath/asset'):
                item.setFlags(item.flags() | configparser.MarkedAsActive)

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
        widget.resize(self.width(), self.height())
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

        favourite = not not index.flags() & configparser.MarkedAsFavourite
        archived = not not index.flags() & configparser.MarkedAsArchived

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
                    item.data(common.PathRole).filePath())
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
        server, job, root = self.path
        file_info = QtCore.QFileInfo('{}/{}/{}'.format(*self.path))

        warning_one = 'No Bookmark has been set yet.\nAssets will be shown here after activating a Bookmark.'
        warning_two = 'Invalid Bookmark set.\nServer: {}\nJob: {}\nRoot: {}'
        warning_three = 'An error occured when trying to collect the assets.\n\n{}'
        warning_four = 'The active bookmark ({}/{}/{}) does not contain any assets...yet.'
        warning_five = '{} items are hidden by filters'

        if not all(self.path):
            return warning_one
        if not any(self.path):
            return warning_two.format(
                server, job, root
            )
        if not file_info.exists():
            return warning_three

        if not self.count():
            return warning_four.format(*self.path)

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
            self._paint_widget_background()
            self.paint_message(self._warning_strings())
        return False

    def select_active_item(self):
        self.setCurrentItem(self.active_item())

    def showEvent(self, event):
        """Show event will set the size of the widget."""
        self.select_active_item()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])

    app.w = AssetWidget()
    app.w.show()
    app.exec_()
