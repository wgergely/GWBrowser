# -*- coding: utf-8 -*-
"""Module defines the QListWidget items used to browse the assets and the files
found by the collector classes.

"""
# pylint: disable=E1101, C0103, R0913, I1101

import os
import functools
from collections import OrderedDict
from PySide2 import QtWidgets, QtGui, QtCore

from mayabrowser.baselistwidget import BaseContextMenu
from mayabrowser.baselistwidget import BaseListWidget

import mayabrowser.common as common
import mayabrowser.configparsers as configparser
from mayabrowser.configparsers import AssetSettings
from mayabrowser.configparsers import local_settings
from mayabrowser.collector import FileCollector
from mayabrowser.delegate import FilesWidgetDelegate


class FilesWidgetContextMenu(BaseContextMenu):
    """Context menu associated with FilesWidget."""

    def __init__(self, index, parent=None):
        super(FilesWidgetContextMenu, self).__init__(index, parent=parent)
        self.add_thumbnail_menu()
        self.add_refresh_menu()


class FilesWidget(BaseListWidget):
    """Files widget is responsible for listing scene and project files of an asset.

    It relies on a custom collector class to gether the files requested.
    The scene files live in their respective root folder, usually ``scenes``.
    The first subfolder inside this folder will refer to the ``mode`` of the
    asset file.

    Signals:

    """
    # Signals
    fileOpened = QtCore.Signal(str)
    fileSaved = QtCore.Signal(str)
    fileImported = QtCore.Signal(str)
    fileReferenced = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(FilesWidget, self).__init__(
            (local_settings.value('activepath/server'),
             local_settings.value('activepath/job'),
             local_settings.value('activepath/root'),
             local_settings.value('activepath/asset'),
             local_settings.value('activepath/file')),
            parent=parent
        )
        self.setWindowTitle('Files')
        self.setItemDelegate(FilesWidgetDelegate(parent=self))
        self._context_menu_cls = FilesWidgetContextMenu

    def refresh(self):
        """Refreshes the list if files.
        Emits the sceneChanged signal.

        """
        # Remove QFileSystemWatcher paths:
        for path in self.fileSystemWatcher.directories():
            self.fileSystemWatcher.removePath(path)

        super(FilesWidget, self).refresh()

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
                todos = len([k for k in todos if not todos[k]
                             ['checked'] and todos[k]['text']])
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


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = FilesWidget()
    widget.show()
    app.exec_()
