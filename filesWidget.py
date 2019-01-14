# -*- coding: utf-8 -*-
"""Module defines the QListWidget items used to browse the assets and the files
found by the collector classes.

"""
# pylint: disable=E1101, C0103, R0913, I1101

import os
import functools
from collections import OrderedDict
from PySide2 import QtWidgets, QtGui, QtCore

from mayabrowser.listbase import BaseContextMenu
from mayabrowser.listbase import BaseListWidget

from mayabrowser.common import cmds
import mayabrowser.common as common
import mayabrowser.configparsers as configparser
from mayabrowser.configparsers import local_settings
from mayabrowser.configparsers import FileConfig
from mayabrowser.collector import FileCollector
from mayabrowser.delegate import FilesWidgetDelegate


class MayaFilesWidgetContextMenu(BaseContextMenu):
    """Context menu associated with MayaFilesWidget."""

    def __init__(self, *args, **kwargs):
        super(MayaFilesWidgetContextMenu, self).__init__(*args, **kwargs)
        self.filter_actions = []

    def filter_changed(self, action):
        self.parent().current_filter = action.data()

        for _action in self.filter_actions:
            _action.setChecked(False)
        action.setChecked(True)

        self.refresh()

    def add_mode_filters(self):
        """Adds a menu to set the filter for the collector based on the
        subdirectories found.

        """
        self.filter_actions = []

        submenu = self.addMenu('Filter by type')
        pixmap = QtGui.QPixmap(64, 64)
        pixmap.fill(QtGui.QColor(200, 200, 200))
        submenu.setIcon(QtGui.QIcon(pixmap))

        action = submenu.addAction('Show all items')
        self.filter_actions.append(action)

        action.setCheckable(True)
        action.setData('/')
        action.triggered.connect(
            functools.partial(self.filter_changed, action))

        submenu.addSeparator()
        for label in sorted(common.ASSIGNED_LABELS.keys()):
            pixmap = QtGui.QPixmap(64, 64)
            pixmap.fill(common.ASSIGNED_LABELS[label])
            icon = QtGui.QIcon(pixmap)

            action = submenu.addAction(label.title())
            action.setIcon(icon)
            action.setCheckable(True)
            action.setData(label.lower())
            action.triggered.connect(
                functools.partial(self.filter_changed, action))
            self.filter_actions.append(action)

        # Check the current item
        for _action in self.filter_actions:
            if _action.data() == self.parent().current_filter:
                _action.setChecked(True)

        self.addSeparator()

    def add_actions(self):
        self.add_mode_filters()
        self.add_action_set(self.ActionSet)

    @property
    def ActionSet(self):
        """List of custom actions to show in the context menu."""
        items = OrderedDict()
        if self.index.isValid():
            data = self.index.data(QtCore.Qt.StatusTipRole)
            name = QtCore.QFileInfo(data).fileName()
            config = self.parent().Config(
                self.index.data(QtCore.Qt.StatusTipRole))

            items['Favourite'] = {
                'checkable': True,
                'checked': local_settings.is_favourite(name)
            }
            items['Isolate favourites'] = {
                'checkable': True,
                'checked': self.parent().show_favourites_mode
            }
            items['<separator> 0'] = {}
            items['Capture thumbnail'] = {}
            items['<separator> 1'] = {}
            items['Sort:'] = {'disabled': True}
            items['Alphabetical'] = {
                'checkable': True,
                'checked': (self.parent().sort_mode == 0)
            }
            items['Last modified'] = {
                'checkable': True,
                'checked': (self.parent().sort_mode == 1)
            }
            items['Created'] = {
                'checkable': True,
                'checked': (self.parent().sort_mode == 2)
            }
            items['Size'] = {
                'checkable': True,
                'checked': (self.parent().sort_mode == 3)
            }
            items['Reverse'] = {
                'checkable': True,
                'checked': (self.parent().reverse_mode is True)
            }
            items['<separator> 2'] = {}
            items['Open scene'] = {}
            items['Import as local'] = {}
            items['Import as reference'] = {}
            items['<separator> 3'] = {}
            items['Open in Maya instance'] = {}
            items['<separator> 4'] = {}
            items['Reveal scene in explorer'] = {}
            items['<separator> 5'] = {}
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
        items['<separator> 6'] = {}
        items['Refresh'] = {}
        return items

    def capture_thumbnail(self):
        self.parent().capture_thumbnail()

    def alphabetical(self):
        self.parent().set_sort_mode(0, self.parent().reverse_mode)

    def last_modified(self):
        self.parent().set_sort_mode(1, self.parent().reverse_mode)

    def created(self):
        self.parent().set_sort_mode(2, self.parent().reverse_mode)

    def size(self):
        self.parent().set_sort_mode(3, self.parent().reverse_mode)

    def reverse(self):
        self.parent().set_sort_mode(
            self.parent().sort_mode,
            not self.parent().reverse_mode
        )

    def open_scene(self):
        self.parent().action_on_enter_key()

    def open_in_maya_instance(self):
        item = self.parent().currentItem()
        path = item.data(QtCore.Qt.StatusTipRole)
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def import_as_local(self):
        item = self.parent().currentItem()
        path = item.data(QtCore.Qt.StatusTipRole)
        self.parent().import_scene(path)

    def import_as_reference(self):
        item = self.parent().currentItem()
        path = item.data(QtCore.Qt.StatusTipRole)
        self.parent().import_referenced_scene(path)

    def reveal_scene_in_explorer(self):
        item = self.parent().currentItem()
        info = QtCore.QFileInfo(item.data(QtCore.Qt.StatusTipRole))
        url = QtCore.QUrl.fromLocalFile(info.dir().path())
        QtGui.QDesktopServices.openUrl(url)

    def refresh(self):
        self.parent().refresh()


class MayaFilesWidget(BaseListWidget):
    """Custom QListWidget containing all the collected files."""

    Config = FileConfig
    Delegate = FilesWidgetDelegate
    ContextMenu = MayaFilesWidgetContextMenu

    def __init__(self, root_info=None, parent=None):
        self.collector = FileCollector(root_info)
        super(MayaFilesWidget, self).__init__(parent=parent)
        self.setWindowTitle('Files')

    @property
    def show_favourites_mode(self):
        return local_settings.show_favourites_file_mode

    @show_favourites_mode.setter
    def show_favourites_mode(self, val):
        local_settings.show_favourites_file_mode = val

    @property
    def show_archived_mode(self):
        return local_settings.show_archived_file_mode

    @show_archived_mode.setter
    def show_archived_mode(self, val):
        local_settings.show_archived_file_mode = val

    @property
    def sort_mode(self):
        return local_settings.sort_file_mode

    @sort_mode.setter
    def sort_mode(self, val):
        local_settings.sort_file_mode = val

    @property
    def reverse_mode(self):
        return local_settings.reverse_file_mode

    @reverse_mode.setter
    def reverse_mode(self, val):
        local_settings.reverse_file_mode = val

    @property
    def current_filter(self):
        return local_settings.current_filter

    @current_filter.setter
    def current_filter(self, val):
        local_settings.current_filter = val

    def set_sort_mode(self, sort_mode, reverse_mode):
        """Sets the sorting order of the collector.

        Args:
            sort_mode (int):        The mode between 0 and 4. See ``FilesCollector``.
            reverse_mode (bool):    Reverse list

        """
        self.sort_mode = sort_mode
        self.reverse_mode = reverse_mode
        self.add_items()
        self.get_scene_modes()
        self.set_row_visibility()

    def open_scene(self, path):
        """Opens the given scene."""
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            return

        result = self.save_scene()
        if result == QtWidgets.QMessageBox.Cancel:
            return

        cmds.file(file_info.filePath(), open=True, force=True)

    def import_scene(self, path):
        """Imports the given scene locally."""
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            return

        result = self.save_scene()
        if result == QtWidgets.QMessageBox.Cancel:
            return

        cmds.file(
            file_info.filePath(),
            i=True,
            ns='REF_{}#'.format(file_info.baseName()),
        )

    def import_referenced_scene(self, path):
        """Imports the given scene as a reference."""
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            return

        result = self.save_scene()
        if result == QtWidgets.QMessageBox.Cancel:
            return

        cmds.file(
            file_info.filePath(),
            reference=True,
            ns='Ref_{}#'.format(file_info.baseName()),
            rfn='Ref_{}RN'.format(file_info.baseName()),
        )

    @staticmethod
    def save_scene():
        """If the current scene needs changing prompts the user with
        a pop-up message to save the scene.

        """
        if cmds.file(q=True, modified=True):
            mbox = QtWidgets.QMessageBox()
            mbox.setText(
                'Current scene has unsaved changes.'
            )
            mbox.setInformativeText('Save the scene now?')
            mbox.setStandardButtons(
                QtWidgets.QMessageBox.Save |
                QtWidgets.QMessageBox.Discard |
                QtWidgets.QMessageBox.Cancel
            )
            mbox.setDefaultButton(QtWidgets.QMessageBox.Save)
            result = mbox.exec_()

            if result == QtWidgets.QMessageBox.Cancel:
                return result
            elif result == QtWidgets.QMessageBox.Save:
                cmds.SaveScene()
                return result
            return result

    def action_on_enter_key(self):
        """Action to perform when the enter key is pressed."""
        self.hide()
        self.active_item = self.currentItem()
        self.open_scene(self.currentItem().data(QtCore.Qt.StatusTipRole))
        self.sceneChanged.emit()

    def custom_doubleclick_event(self, index):
        """Opens the scene on double-click."""
        self.action_on_enter_key()

    def action_on_custom_keys(self, event):
        """Custom keyboard shortcuts for the AssetsWidget are defined here.

        **Implemented shortcuts**:
        ::

            Ctrl + C:           Copies the files's path to the clipboard.
            Ctrl + Shift + C:   Copies the files's URI path to the clipboard.
            Ctrl + O:           Opens the file.
            Ctrl + I:           Imports the item locally.
            Ctrl + R:           Imports the item as a reference.
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
            if event.key() == QtCore.Qt.Key_C:
                path = os.path.normpath(data)
                QtGui.QClipboard().setText(path)
            elif event.key() == QtCore.Qt.Key_O:
                self.action_on_enter_key()
            elif event.key() == QtCore.Qt.Key_I:
                self.import_scene(data)
            elif event.key() == QtCore.Qt.Key_R:
                self.import_referenced_scene(data)
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

    def update_path(self, path):
        """Updates the collector path querried."""
        file_info = QtCore.QFileInfo(path)
        self.collector.root_info = file_info

    def refresh(self):
        """Refreshes the list if files.
        Emits the sceneChanged signal.

        """
        # Remove QFileSystemWatcher paths:
        for path in self.fileSystemWatcher.directories():
            self.fileSystemWatcher.removePath(path)

        idx = self.currentIndex()
        self.add_items()
        self.get_scene_modes()
        self.setCurrentIndex(idx)
        self.set_row_visibility()

        self.sceneChanged.emit()

    def get_scene_modes(self):
        """`Modes` are subfolders inside the `scene` folder.

        For example:
            . / [asset_root] / [scene_root] / `animation` /
            . / [asset_root] / [asset_scenes_root] / `layout` /
            . / [asset_root] / [asset_scenes_root] / `render` /

        We're using these modes to compartmentalize different elements of the
        asset and as filters for our list.  Each mode gets it's own color-label
        assigned and are stored in the `common` module.

        """
        common.revert_labels()

        # Let's querry all the subfolders from the scenes_root dir
        if not self.collector.root_info:
            return

        if not self.collector.root_info.exists():
            return

        modes = QtCore.QDir(
            '{}/{}'.format(
                self.collector.root_info.filePath(),
                local_settings.asset_scenes_folder
            )
        )
        modes = modes.entryInfoList(
            sort=QtCore.QDir.Name,
            filters=QtCore.QDir.AllDirs | QtCore.QDir.NoDotAndDotDot
        )

        for mode in modes:
            common.get_label(mode.baseName())

    def add_items(self):
        """Retrieves the files found by the ``FilesCollector`` and adds them as
        QListWidgetItems.

        Note:
            The method adds the files' parent folder to the QFileSystemWatcher to monitor
            file changes. Any directory change should trigger a refresh. This might
            have some performance implications. Needs testing!

        """
        self.clear()
        for path in self.fileSystemWatcher.directories():
            self.fileSystemWatcher.removePath(path)

        for f in self.collector.get_files(
            sort_order=self.sort_mode,
            reverse=self.reverse_mode,
            filter=self.current_filter
        ):
            self.fileSystemWatcher.addPath(f.dir().path())

            # Getting the base directories
            basedirs = f.dir().path()
            basedirs = basedirs.replace(
                self.collector.root_info.filePath(), ''
            ).replace(
                local_settings.asset_scenes_folder, ''
            ).lstrip('/').rstrip('/')

            item = QtWidgets.QListWidgetItem()
            item.setData(
                QtCore.Qt.DisplayRole,
                '{}/{}'.format(basedirs, f.fileName())
            )
            item.setData(
                QtCore.Qt.EditRole,
                '{}/{}'.format(basedirs, f.fileName())
            )
            item.setData(
                QtCore.Qt.StatusTipRole,
                f.filePath()
            )
            item.setData(
                QtCore.Qt.ToolTipRole,
                'Maya scene: "{}"'.format(f.filePath())
            )

            config = self.Config(f.filePath())
            flags = configparser.NoFlag
            if config.archived:
                flags = flags | configparser.MarkedAsArchived
            elif local_settings.is_favourite(f.fileName()):
                flags = flags | configparser.MarkedAsFavourite
            item.setData(
                common.DescriptionRole,
                flags
            )
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            self.addItem(item)

    def eventFilter(self, widget, event):
        """MayaFilesWidget's custom paint is triggered here."""
        if event.type() == QtCore.QEvent.Paint:
            self._paint_widget_background()

            if self.count() == 0:
                self.paint_message('{}:  No scene files found.'.format(
                    'Show all items' if self.current_filter == '/' else self.current_filter
                )
                )
            elif self.count() > self.count_visible():
                self.paint_message(
                    '{} items are hidden.'.format(self.count()))
        return False

    def showEvent(self, event):
        """Show event will set the size of the widget."""
        self.sceneChanged.emit()
