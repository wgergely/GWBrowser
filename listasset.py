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
import functools
from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common
from mayabrowser.listbase import BaseContextMenu
from mayabrowser.listbase import BaseListWidget

import mayabrowser.configparsers as configparser
from mayabrowser.configparsers import local_config
from mayabrowser.configparsers import AssetConfig
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

    def location_changed(self, action):
        """Action triggered when the location has changed.

        Args:
            action (QAction):       Instance of the triggered action.

        """
        local_config.server = action.data()[0]
        local_config.job = action.data()[1]
        local_config.root = action.data()[2]
        self.parent().parent().parent().sync_config()

    def add_location(self):
        """Populates the menu with location of asset locations."""
        submenu = self.addMenu('Locations')
        if not local_config.location:
            return

        for item in local_config.location:
            if item[0] == '':
                continue
            action = submenu.addAction('{}/{}/{}'.format(*item))
            action.setData(item)
            action.triggered.connect(
                functools.partial(self.location_changed, action))
            action.setCheckable(True)
            if (
                (item[0] == local_config.server) and
                (item[1] == local_config.job) and
                (item[2] == local_config.root)
            ):
                action.setChecked(True)

    def add_actions(self):
        self.add_location()
        self.add_action_set(self.ACTION_SET)

    @property
    def ACTION_SET(self):
        """A custom set of actions to display."""
        items = OrderedDict()
        if self.index.isValid():
            config = self.parent().Config(self.index.data(QtCore.Qt.StatusTipRole))
            data = self.index.data(QtCore.Qt.StatusTipRole)
            name = QtCore.QFileInfo(data).fileName()

            items['<separator>0'] = {}
            items['Set as active asset'] = {}
            items['<separator>.'] = {}
            items['Capture thumbnail'] = {}
            items['<separator>..'] = {}
            items['Favourite'] = {
            'checkable': True,
            'checked': local_config.is_favourite(name)
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
            items['Archived'] = {
                'checkable': True,
                'checked': config.archived
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

    def set_as_active_asset(self):
        self.parent().active_item = self.parent().currentItem()

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
    """Custom QListWidget containing all the collected maya assets.

    Assets are folders with an identifier file, by default
    the asset collector will look for a file in the root of the asset folder
    called ``workspace.mel``. If this file is not found the folder is ignored.

    """
    Config = AssetConfig
    Delegate = AssetWidgetDelegate
    ContextMenu = AssetWidgetContextMenu

    def __init__(self, parent=None):
        self._collector = AssetCollector(
            server=local_config.server,
            job=local_config.job,
            root=local_config.root
        )
        super(AssetWidget, self).__init__(parent=parent)
        self.setWindowTitle('Assets')

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

    @property
    def collector(self):
        """The collector object associated with the widget."""
        return self._collector

    @property
    def current_filter(self):
        """The current filter - this is not currently  implemented for ``AssetWidget``."""
        return '/'

    @property
    def active_item(self):
        """``active_item`` defines the currently set maya asset.
        The property is querried by FilesWidget to list the available
        Maya scenes.

        Note:
            Setting ``active_item`` emits a ``assetChanged`` signal.

        """
        if not self.collector.active_item:
            return None
        item = self.findItems(
            self.collector.active_item.baseName().upper(),
            QtCore.Qt.MatchEndsWith | QtCore.Qt.MatchStartsWith | QtCore.Qt.MatchContains
        )
        return item[0] if item else None

    @active_item.setter
    def active_item(self, item):
        if isinstance(item, (QtCore.QModelIndex, QtWidgets.QListWidgetItem)):
            data = item.data(QtCore.Qt.StatusTipRole)
            self.collector.set_active_item(QtCore.QFileInfo(data))
            self.viewport().repaint()
            self.assetChanged.emit()
        else:
            self.collector.set_active_item(None)

    @property
    def show_favourites_mode(self):
        """The current show favourites state as saved in the local configuration file."""
        return local_config.show_favourites_asset_mode

    @show_favourites_mode.setter
    def show_favourites_mode(self, val):
        local_config.show_favourites_asset_mode = val

    @property
    def show_archived_mode(self):
        """The current Show archived state as saved in the local configuration file."""
        return local_config.show_archived_asset_mode

    @show_archived_mode.setter
    def show_archived_mode(self, val):
        local_config.show_archived_asset_mode = val

    def refresh(self):
        """Refreshes the list of found assets."""
        # Remove QFileSystemWatcher paths:
        for path in self.fileSystemWatcher.directories():
            self.fileSystemWatcher.removePath(path)

        idx = self.currentIndex()
        self.collector.update(**self.parent().parent()._kwargs)
        self.add_items()  # Adds the file

        self.parent().parent().sync_active_maya_asset()
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

        if self.collector.root_info:
            self.fileSystemWatcher.addPath(
                self.collector.root_info.filePath()
            )

        for f in self.collector.items:
            item = QtWidgets.QListWidgetItem()
            item.setData(
                QtCore.Qt.DisplayRole,
                f.baseName().upper()
            )
            item.setData(
                QtCore.Qt.EditRole,
                f.baseName().upper()
            )
            item.setData(
                QtCore.Qt.StatusTipRole,
                f.filePath()
            )
            item.setData(
                QtCore.Qt.ToolTipRole,
                f.filePath()
            )

            config = self.Config(f.filePath())
            flags = configparser.NoFlag
            if config.archived:
                flags = flags | configparser.MarkedAsArchived
            elif local_config.is_favourite(f.fileName()):
                flags = flags | configparser.MarkedAsFavourite

            item.setData(
                QtCore.Qt.UserRole,
                flags
            )
            item.setSizeHint(QtCore.QSize(common.WIDTH, common.ROW_HEIGHT))
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
            local_config.asset_textures_folder
        )
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def reveal_asset_scenes(self):
        """Opens the ``scenes`` folder."""
        item = self.currentItem()
        path = '{}/{}'.format(
            item.data(QtCore.Qt.StatusTipRole),
            local_config.asset_scenes_folder
        )
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def reveal_asset_renders(self):
        """Opens the ``renders`` folder."""
        item = self.currentItem()
        path = '{}/{}'.format(
            item.data(QtCore.Qt.StatusTipRole),
            local_config.asset_renders_folder
        )
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def reveal_asset_exports(self):
        """Opens the ``exports`` folder."""
        item = self.currentItem()
        path = '{}/{}'.format(
            item.data(QtCore.Qt.StatusTipRole),
            local_config.asset_exports_folder
        )
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def eventFilter(self, widget, event):
        """AssetWidget's custom paint is triggered here.

        I'm using the custom paint event to display a user message when no
        asset or files can be found.

        """
        if event.type() == QtCore.QEvent.Paint:
            self._paint_widget_background()

            if self.count() == 0:
                # Message to show when no assets are found.
                set_text = 'No assets found in \n{}/{}/{}'.format(
                    self.parent().parent()._kwargs['server'],
                    self.parent().parent()._kwargs['job'],
                    self.parent().parent()._kwargs['root'],
                ).strip('/')

                # Message to show when no configuration has been set.
                not_set_text = 'No location has been set.\n'
                not_set_text += 'Right-click on the Browser Toolbar and select \'Configure\' to set the location of your assets.'
                text = set_text if self.parent().parent()._kwargs['server'] else not_set_text

                self.paint_message(text)
            elif self.count() > self.count_visible():
                self.paint_message(
                    '{} items are hidden by filters'.format(self.count() - self.count_visible())
                )

        return False

    def showEvent(self, event):
        """Show event will set the size of the widget."""
        self.parent().parent().sync_active_maya_asset(setActive=False)
