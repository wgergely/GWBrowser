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
        menu.setTitle('Copy')

        # Url
        file_path = self.index.data(QtCore.Qt.PathRole).filePath()
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
        action.triggered.connect(functools.partial(cp, url.toString().replace('file://', 'smb://')))

        menu.addSeparator()

        action = menu.addAction('Path')
        action.setEnabled(False)
        action = menu.addAction(file_path)
        action.triggered.connect(functools.partial(cp, file_path))

        menu.addSeparator()

        action = menu.addAction('Windows path')
        action.setEnabled(False)
        action = menu.addAction(file_path)
        action.triggered.connect(functools.partial(cp, QtCore.QDir.toNativeSeparators(file_path)))

        self.addMenu(menu)
        self.addSeparator()

    @property
    def VALID_ACTION_SET(self):
        """A custom set of actions to display."""
        items = OrderedDict()
        file_info = self.index.data(QtCore.Qt.PathRole)
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

    Signals:
        activeChanged (Signal):         Signal emited when the active asset has changed.

    Properties:
        path (tuple[str, str, str]):    Sets the path to search for assets.

    """
    Delegate = AssetWidgetDelegate
    ContextMenu = AssetWidgetContextMenu

    # Signals
    activated = QtCore.Signal(str)

    def __init__(self, server=None, job=None, root=None, parent=None):
        self._path = (server, job, root)
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
        asset = self.currentItem().data(QtCore.Qt.PathRole).baseName()
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

        collector = AssetCollector('/'.join(self.path))
        self.fileSystemWatcher.addPath('/'.join(self.path))

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
        self.set_current_item_as_active()

    def custom_doubleclick_event(self, index):
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
                self.custom_doubleclick_event()
        elif event.modifiers() & QtCore.Qt.AltModifier:
            if event.key() == QtCore.Qt.Key_C:
                url = QtCore.QUrl()
                url = url.fromLocalFile(item.data(QtCore.Qt.PathRole).filePath())
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
        server, job, root = self.path
        if not all(self.path):
            return 'No Bookmark has been set yet.\nAssets will be shown here after you select one in the Bookmarks menu.'
        if not any(self.path):
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

    def select_active_item(self):
        self.setCurrentItem(self.active_item())

    def showEvent(self, event):
        """Show event will set the size of the widget."""
        self.select_active_item()



if __name__ == '__main__':
    app = QtWidgets.QApplication([])

    app.w = AssetWidget(
        local_settings.value('activepath/server'),
        local_settings.value('activepath/job'),
        local_settings.value('activepath/root'),
    )
    # app.w.path = ('//gordo/jobs','tkwwbk_8077', 'build')
    app.w.show()
    app.exec_()
