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

import mayabrowser.common as common
import mayabrowser.configparsers as configparser
from mayabrowser.configparsers import AssetSettings
from mayabrowser.configparsers import local_settings
from mayabrowser.collector import FileCollector
from mayabrowser.delegate import FilesWidgetDelegate


class FilesWidgetContextMenu(BaseContextMenu):
    """Context menu associated with FilesWidget."""

    def __init__(self, *args, **kwargs):
        super(FilesWidgetContextMenu, self).__init__(*args, **kwargs)
        self.filter_actions = []

    def filter_changed(self, action):
        self.parent().filter = action.data()

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
            if _action.data() == self.parent().filter:
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
                'checked': (self.parent().sort_order == 0)
            }
            items['Last modified'] = {
                'checkable': True,
                'checked': (self.parent().sort_order == 1)
            }
            items['Created'] = {
                'checkable': True,
                'checked': (self.parent().sort_order == 2)
            }
            items['Size'] = {
                'checkable': True,
                'checked': (self.parent().sort_order == 3)
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
        self.parent().set_sort_order(0, self.parent().reverse_mode)

    def last_modified(self):
        self.parent().set_sort_order(1, self.parent().reverse_mode)

    def created(self):
        self.parent().set_sort_order(2, self.parent().reverse_mode)

    def size(self):
        self.parent().set_sort_order(3, self.parent().reverse_mode)

    def reverse(self):
        self.parent().set_sort_order(
            self.parent().sort_order,
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


class FilesWidget(BaseListWidget):
    """Files widget is responsible for listing scene and project files of an asset.

    It relies on a custom collector class to gether the files requested.
    The scene files live in their respective root folder, usually ``scenes``.
    The first subfolder inside this folder will refer to the ``mode`` of the
    asset file.

    Signals:

    """

    Delegate = FilesWidgetDelegate
    ContextMenu = FilesWidgetContextMenu

    # Signals
    fileOpened = QtCore.Signal(str)
    fileSaved = QtCore.Signal(str)
    fileImported = QtCore.Signal(str)
    fileReferenced = QtCore.Signal(str)

    fileChanged = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(FilesWidget, self).__init__(parent=parent)
        self._path = (
            local_settings.value('activepath/server'),
            local_settings.value('activepath/job'),
            local_settings.value('activepath/root'),
            local_settings.value('activepath/asset')
        )
        self.setWindowTitle('Files')

    def set_sort_order(self, sort_order, reverse_mode):
        """Sets the sorting order of the collector.

        Args:
            sort_order (int):        The mode between 0 and 4. See ``FilesCollector``.
            reverse_mode (bool):    Reverse list

        """
        self.sort_order = sort_order
        self.reverse_mode = reverse_mode
        self.add_items()
        self.set_row_visibility()

    def action_on_enter_key(self):
        """Action to perform when the enter key is pressed."""
        self.hide()
        self.active_item = self.currentItem()
        self.open_scene(self.currentItem().data(QtCore.Qt.StatusTipRole))
        self.sceneChanged.emit()

    def mouseDoubleClickEvent(self, event):
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
        self.setCurrentIndex(idx)
        self.set_row_visibility()

        self.sceneChanged.emit()

    def get_modes(self):
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
        dir_ = QtCore.QDir('{}/{}/{}/{}'.format(*self.path))
        dir_ = dir_.entryInfoList(
            sort=QtCore.QDir.Name,
            filters=QtCore.QDir.AllDirs | QtCore.QDir.NoDotAndDotDot
        )

        for file_info in dir_:
            common.get_label(file_info.baseName())

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

        err_one = 'An error occured when trying to collect the files.\n\n{}'

        try:
            path = '{}/{}/{}/{}'.format(*self.path)
            collector = FileCollector(path)
            self.fileSystemWatcher.addPath(path)
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


        for file_info in collector.get(
            sort_order=self.sort_order,
            reverse=self.reverse,
            filter=self.filter
        ):
            self.fileSystemWatcher.addPath(file_info.dir().path())

            item = QtWidgets.QListWidgetItem()
            settings = AssetSettings(file_info.filePath())

            item.setData(QtCore.Qt.DisplayRole, file_info.fileName())
            item.setData(QtCore.Qt.EditRole,
                         item.data(QtCore.Qt.DisplayRole))

            item.setData(QtCore.Qt.StatusTipRole, file_info.filePath())

            tooltip = u'{}\n\n'.format(file_info.fileName().upper())
            tooltip += u'{}\n'.format(self._path[1].upper())
            tooltip += u'{}\n\n'.format(self._path[2].upper())
            tooltip += u'{}'.format(file_info.filePath())
            item.setData(QtCore.Qt.ToolTipRole, tooltip)

            item.setData(common.PathRole, file_info)

            info_string = '{day}/{month}/{year} {hour}:{minute}  {size}'.format(
                day=file_info.lastModified().toString('dd'),
                month=file_info.lastModified().toString('MM'),
                year=file_info.lastModified().toString('yyyy'),
                hour=file_info.lastModified().toString('hh'),
                minute=file_info.lastModified().toString('mm'),
                size=common.byte_to_string(file_info.size())
            )
            item.setData(common.FileDetailsRole, info_string)

            mode = file_info.path()
            mode = mode.replace('{}/{}/{}/{}'.format(*self.path), '')
            mode = mode.strip('/').split('/')
            item.setData(common.FileModeRole, mode)

            item.setData(
                QtCore.Qt.SizeHintRole,
                QtCore.QSize(common.WIDTH, common.FILE_ROW_HEIGHT))

            item.setData(common.DescriptionRole, settings.value(
                'config/description'))

            # Todos
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
            if file_info.filePath() in favourites:
                item.setFlags(item.flags() | configparser.MarkedAsFavourite)

            if file_info.baseName() == local_settings.value('activepath/asset'):
                item.setFlags(item.flags() | configparser.MarkedAsActive)

            self.addItem(item)



    def eventFilter(self, widget, event):
        """FilesWidget's custom paint is triggered here."""
        if event.type() == QtCore.QEvent.Paint:
            self._paint_widget_background()

            if self.count() == 0:
                self.paint_message(
                    'No scene files found ({})'.format(
                        'showing all items' if self.filter == '/' else self.filter
                    )
                )
            elif self.count() > self.count_visible():
                self.paint_message(
                    '{} items are hidden.'.format(self.count()))
        return False



if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = FilesWidget()
    widget.show()
    app.exec_()
