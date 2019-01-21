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
import mayabrowser.editors as editors


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

    def __init__(self, path, root, parent=None):
        self.path = path # tuple(server,job,root,asset)
        self.root = root

        super(FilesWidget, self).__init__(parent=parent)

        self.setWindowTitle('Files')
        self.setItemDelegate(FilesWidgetDelegate(parent=self))
        self._context_menu_cls = FilesWidgetContextMenu

    def refresh(self):
        """Refreshes the list if files."""
        for path in self.fileSystemWatcher.directories():
            self.fileSystemWatcher.removePath(path)

        super(FilesWidget, self).refresh()

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

        server, job, root, asset = self.path
        if not all(self.path):
            return

        self.fileSystemWatcher.addPath('/'.join(self.path))

        collector = FileCollector('/'.join(self.path), self.root)
        items = collector.get_items(
            key=self.get_item_sort_order(),
            reverse=self.is_item_sort_reversed(),
            path_filter=self.get_item_filter()
        )
        self.collector_count = collector.count
        for file_info in items:
            item = QtWidgets.QListWidgetItem()
            settings = AssetSettings('/'.join(self.path), file_info.filePath())

            self.fileSystemWatcher.addPath(file_info.dir().path())
            path = '{}/{}'.format('/'.join(self.path), self.root)

            # Qt Roles
            item.setData(QtCore.Qt.DisplayRole, file_info.fileName())
            item.setData(QtCore.Qt.EditRole, item.data(QtCore.Qt.DisplayRole))
            item.setData(QtCore.Qt.StatusTipRole, file_info.filePath())

            tooltip = u'{}\n\n'.format(file_info.filePath())
            tooltip += u'{} | {}\n'.format(job.upper(), root.upper())
            item.setData(QtCore.Qt.ToolTipRole, tooltip)
            item.setData(
                QtCore.Qt.SizeHintRole,
                QtCore.QSize(common.WIDTH, common.FILE_ROW_HEIGHT))

            # Custom roles

            # Modes
            mode = file_info.path() # parent folder
            mode = mode.replace('{}/{}/{}/{}/{}'.format(
                server, job, root, asset, self.root
            ), '')
            mode = mode.strip('/').split('/')
            item.setData(common.FileModeRole, mode)


            item.setData(common.PathRole, file_info.filePath())
            item.setData(common.ParentRole, (
                server,
                job,
                root,
                asset)
            )
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

            # File info
            info_string = '{day}/{month}/{year} {hour}:{minute}  {size}'.format(
                day=file_info.lastModified().toString('dd'),
                month=file_info.lastModified().toString('MM'),
                year=file_info.lastModified().toString('yyyy'),
                hour=file_info.lastModified().toString('hh'),
                minute=file_info.lastModified().toString('mm'),
                size=common.byte_to_string(file_info.size())
            )
            item.setData(common.FileDetailsRole, info_string)

            # Flags
            if settings.value('config/archived'):
                item.setFlags(item.flags() | configparser.MarkedAsArchived)
            # Favourite
            favourites = local_settings.value('favourites')
            favourites = favourites if favourites else []
            if file_info.filePath() in favourites:
                item.setFlags(item.flags() | configparser.MarkedAsFavourite)
            # Active
            if file_info.completeBaseName() == local_settings.value('activepath/file'):
                item.setFlags(item.flags() | configparser.MarkedAsActive)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)

            self.addItem(item)

    def _warning_strings(self):
        server, job, root, asset = self.path
        path_err = '{} has not yet been set.'
        if not server:
            return str(path_err).format('Server')
        if not job:
            return str(path_err).format('Job')
        if not root:
            return str(path_err).format('Root')
        if not asset:
            return str(path_err).format('Asset')

        if not self.collector_count:
            path = '/'.join(self.path)
            return '{} contains no valid items.'.format(path)
        if self.count() > self.count_visible():
            return '{} items hidden by filters.'.format(self.count() - self.count_visible())

    def mousePressEvent(self, event):
        """In-line buttons are triggered here."""
        index = self.indexAt(event.pos())
        rect = self.visualRect(index)

        if self.viewport().width() < 360.0:
            return super(FilesWidget, self).mousePressEvent(event)

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

        return super(FilesWidget, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """In-line buttons are triggered here."""
        index = self.indexAt(event.pos())
        rect = self.visualRect(index)
        idx = index.row()

        if self.viewport().width() < 360.0:
            return super(FilesWidget, self).mouseReleaseEvent(event)

        # Cheking the button
        if idx not in self.multi_toggle_items:
            for n in xrange(3):
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
                        path = QtCore.QFileInfo(index.data(common.PathRole))
                        common.reveal(path.dir().path())

        self.multi_toggle_pos = None
        self.multi_toggle_state = None
        self.multi_toggle_idx = None
        self.multi_toggle_item = None
        self.multi_toggle_items = {}

        super(FilesWidget, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """Multi-toggle is handled here."""
        if self.viewport().width() < 360.0:
            return super(FilesWidget, self).mouseMoveEvent(event)

        if self.multi_toggle_pos is None:
            super(FilesWidget, self).mouseMoveEvent(event)
            return

        app_ = QtWidgets.QApplication.instance()
        if (event.pos() - self.multi_toggle_pos).manhattanLength() < app_.startDragDistance():
            super(FilesWidget, self).mouseMoveEvent(event)
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

        name_rect, _, metrics = self.itemDelegate().get_text_area(
            rect, common.PRIMARY_FONT)
        name_rect.moveTop(name_rect.top() + (name_rect.height() / 2.0))
        name_rect.setHeight(metrics.height())
        name_rect.moveTop(name_rect.top() - (name_rect.height() / 2.0))

        description_rect, _, metrics = self.itemDelegate().get_text_area(
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



if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    path = (local_settings.value('activepath/server'),
            local_settings.value('activepath/job'),
            local_settings.value('activepath/root'),
            local_settings.value('activepath/asset'))

    widget = FilesWidget(path, common.ScenesFolder)

    widget.show()
    app.exec_()
