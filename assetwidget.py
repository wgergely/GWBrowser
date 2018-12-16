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

import os
from collections import OrderedDict
from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common
from mayabrowser.listbase import BaseContextMenu
from mayabrowser.listbase import BaseListWidget

import mayabrowser.configparsers as configparser
from mayabrowser.configparsers import local_settings
from mayabrowser.configparsers import AssetSettings
from mayabrowser.collector import AssetCollector
from mayabrowser.delegate import AssetWidgetDelegate
from mayabrowser.popover import PopupCanvas


class AssetWidgetContextMenu(BaseContextMenu):
    """Context menu associated with the AssetWidget.

    Methods:
        set_as_active_asset:      Sets the current item as the *`active item`*
        show_asset_in_explorer:   Shows current item in the explorer.
        show_textures:              Shows the asset's ``textures`` folder.
        show_scenes:                Shows the asset's ``scenes`` folder.
        show_renders:               Shows the asset's ``renders`` folder.
        show_exports:               Shows the asset's ``exports`` folder.
        refresh:                    Refreshes the collector and repopulates the widget.

    """

    def add_actions(self):
        self.add_action_set(self.ACTION_SET)

    @property
    def ACTION_SET(self):
        """A custom set of actions to display."""
        items = OrderedDict()
        if self.index.isValid():
            file_info = self.index.data(QtCore.Qt.PathRole)
            settings = AssetSettings(file_info.filePath())

            items[file_info.filePath()] = {'disabled': True}
            items['Activate'] = {}
            items['<separator>.'] = {}
            items['Capture thumbnail'] = {}
            items['<separator>..'] = {}

            favourites = local_settings.value('favourites')
            favourites = favourites if favourites else []
            items['Favourite'] = {
                'checkable': True,
                'checked': True if file_info.filePath() in favourites else False
            }
            items['Isolate favourites'] = {
                'checkable': True,
                'checked': self.parent().show_favourites_mode
            }
            items['<separator>...'] = {}
            items['Show asset in explorer'] = {}
            items['Show exports'] = {}
            items['Show scenes'] = {}
            items['Show renders'] = {}
            items['Show textures'] = {}
            items['<separator>....'] = {}

            archived = settings.value('flags/archived')
            archived = archived if archived else False
            items['Archived'] = {
                'checkable': True,
                'checked': archived
            }
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

    def show_asset_in_explorer(self):
        self.parent().reveal_asset()

    def show_textures(self):
        self.parent().reveal_asset_textures()

    def show_scenes(self):
        self.parent().reveal_asset_scenes()

    def show_renders(self):
        self.parent().reveal_asset_renders()

    def show_exports(self):
        self.parent().reveal_asset_exports()

    def refresh(self):
        self.parent().refresh()


class AssetWidget(BaseListWidget):
    """Custom QListWidget for displaying the found assets inside the set ``path``.

    Arguments:
        server (str):   The server, job and root, making up the path to querry.
        job (str):
        root (str):

    Methods:
        set_path([str, str, str]):  Sets the path.

    """
    Delegate = AssetWidgetDelegate
    ContextMenu = AssetWidgetContextMenu

    # Signals
    activeChanged = QtCore.Signal(str)

    def __init__(self, server=None, job=None, root=None, parent=None):
        self._path = (server, job, root)
        super(AssetWidget, self).__init__(parent=parent)
        self.setWindowTitle('Assets')

    def set_path(self, server, job, root):
        """Sets the path."""
        self._path = (server, job, root)

    def set_current_item_as_active(self):
        """Sets the current item item as ``active``."""
        super(AssetWidget, self).set_current_item_as_active()

        # Updating the local config file
        asset = self.currentItem().data(QtCore.Qt.PathRole).baseName()
        local_settings.setValue('activepath/asset', asset)

        # Emiting change a signal upon change
        self.activeChanged.emit(asset)

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

        if not any(self._path):
            return

        collector = AssetCollector('/'.join(self._path))
        self.fileSystemWatcher.addPath('/'.join(self._path))

        for f in collector.get():
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, f.baseName())
            item.setData(QtCore.Qt.EditRole,
                         item.data(QtCore.Qt.DisplayRole))
            item.setData(QtCore.Qt.StatusTipRole,
                         u'Asset: {}\n{}'.format(
                             f.baseName(), f.filePath()
                         ))
            item.setData(QtCore.Qt.ToolTipRole,
                         item.data(QtCore.Qt.StatusTipRole))

            item.setData(QtCore.Qt.PathRole, f)
            item.setData(
                QtCore.Qt.SizeHintRole,
                QtCore.QSize(common.WIDTH, common.ASSET_ROW_HEIGHT))

            settings = AssetSettings(f.filePath())
            item.setData(QtCore.Qt.UserRole, settings.value(
                'description/description'))  # Notes will be stored here

            # Flags
            if settings.value('flags/archived'):
                item.setFlags(item.flags() | configparser.MarkedAsArchived)
            favourites = local_settings.value('favourites')
            favourites = favourites if favourites else []
            if f.filePath() in favourites:
                item.setFlags(item.flags() | configparser.MarkedAsFavourite)

            if f.baseName() == local_settings.value('activepath/asset'):
                item.setFlags(item.flags() | configparser.MarkedAsActive)

            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)

            self.addItem(item)

    def action_on_enter_key(self):
        """Custom enter key action."""
        self.active_item = self.currentItem()

    def custom_doubleclick_event(self, index):
        self.active_item = index

    def action_on_custom_keys(self, event):
        """Custom keyboard shortcuts for the AssetsWidget are defined here.

        **Implemented shortcuts**:
        ::

            Ctrl + C:           Copies the asset's path to the clipboard.
            Ctrl + Shift + C:   Copies the files's URI path to the clipboard.
            Ctrl + O:           Sets the current item as the active asset and opens shows the filewidget.
            Ctrl + P:           Reveals the asset in the explorer.
            Ctrl + T:           Reveals the asset's textures folder.
            Ctrl + S:           Reveals the asset's scenes folder.
            Ctrl + R:           Reveals the asset's renders folder.
            Ctrl + E:           Reveals the asset's exports folder.
            Ctrl + F:           Toggles favourite.
            Ctrl + Shift + F:   Toggles Isolate favourites.
            Ctrl + A:           Toggles archived.
            Ctrl + Shift + A:   Toggles Show archived.

        """
        item = self.currentItem()
        if not item:
            return
        data = item.data(QtCore.Qt.StatusTipRole)

        if event.modifiers() == QtCore.Qt.ControlModifier:
            if event.key() == QtCore.Qt.Key_O:
                self.active_item = self.currentItem()
            if event.key() == QtCore.Qt.Key_C:
                path = os.path.normpath(data)
                QtGui.QClipboard().setText(path)
            elif event.key() == QtCore.Qt.Key_P:
                self.reveal_asset()
            elif event.key() == QtCore.Qt.Key_T:
                self.reveal_asset_textures()
            elif event.key() == QtCore.Qt.Key_S:
                self.reveal_asset_scenes()
            elif event.key() == QtCore.Qt.Key_R:
                self.reveal_asset_renders()
            elif event.key() == QtCore.Qt.Key_E:
                self.reveal_asset_exports()
            elif event.key() == QtCore.Qt.Key_F:
                self._contextMenu = self.ContextMenu(
                    self.currentIndex(), parent=self)
                self._contextMenu.favourite()
            elif event.key() == QtCore.Qt.Key_A:
                self._contextMenu = self.ContextMenu(
                    self.currentIndex(), parent=self)
                self._contextMenu.archived()
        elif event.modifiers() & QtCore.Qt.ShiftModifier:
            if event.key() == QtCore.Qt.Key_F:
                self._contextMenu = self.ContextMenu(
                    self.currentIndex(), parent=self)
                self._contextMenu.isolate_favourites()
            elif event.key() == QtCore.Qt.Key_A:
                self._contextMenu = self.ContextMenu(
                    self.currentIndex(), parent=self)
                self._contextMenu.show_archived()
            elif event.key() == QtCore.Qt.Key_C:
                url = QtCore.QUrl()
                url = url.fromLocalFile(data)
                QtGui.QClipboard().setText(url.toString())

    def reveal_asset(self):
        item = self.currentItem()
        path = item.data(QtCore.Qt.StatusTipRole)
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def reveal_asset_textures(self):
        """Opens the ``textures`` folder."""
        item = self.currentItem()
        path = '{}/{}'.format(
            item.data(QtCore.Qt.StatusTipRole),
            local_settings.asset_textures_folder
        )
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def reveal_asset_scenes(self):
        """Opens the ``scenes`` folder."""
        item = self.currentItem()
        path = '{}/{}'.format(
            item.data(QtCore.Qt.StatusTipRole),
            local_settings.asset_scenes_folder
        )
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def reveal_asset_renders(self):
        """Opens the ``renders`` folder."""
        item = self.currentItem()
        path = '{}/{}'.format(
            item.data(QtCore.Qt.StatusTipRole),
            local_settings.asset_renders_folder
        )
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def reveal_asset_exports(self):
        """Opens the ``exports`` folder."""
        item = self.currentItem()
        path = '{}/{}'.format(
            item.data(QtCore.Qt.StatusTipRole),
            local_settings.asset_exports_folder
        )
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def _warning_strings(self):
        server, job, root = self._path
        if not all(self._path):
            return 'No Bookmark has been set yet.\nAssets will be shown here after you select one in the Bookmarks menu.'
        if not any(self._path):
            return 'Error: Invalid path set.\nServer: {}\nJob: {}\nRoot: {}'.format(
                server, job, root
            )

    def eventFilter(self, widget, event):
        """AssetWidget's custom paint is triggered here.

        I'm using the custom paint event to display a user message when no
        asset or files can be found.

        """
        if event.type() == QtCore.QEvent.Paint:
            self._paint_widget_background()

            if self.count() == 0:
                self.paint_message(self._warning_strings())
            elif self.count() > self.count_visible():
                self.paint_message(
                    'All {} items are hidden by filters'.format(
                        self.count() - self.count_visible())
                )

        return False

    def showEvent(self, event):
        """Show event will set the size of the widget."""


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    app.w = AssetWidget('//gordo/jobs', 'tkwwbk_8077', 'build')
    # app.w.set_path('//gordo/jobs','tkwwbk_8077', 'build')
    app.w.show()
    app.exec_()
