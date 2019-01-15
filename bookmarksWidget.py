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

from mayabrowser.collector import BookmarksCollector

import mayabrowser.configparsers as configparser
from mayabrowser.configparsers import local_settings
from mayabrowser.delegate import BookmarksWidgetDelegate
from mayabrowser.updatewidget import UpdateConfigWidget


class BookmarksWidgetContextMenu(BaseContextMenu):
    """Context menu associated with the BookmarksWidget.

    Methods:
        refresh: Refreshes the collector and repopulates the widget.

    """

    def __init__(self, index, parent=None):
        super(BookmarksWidgetContextMenu, self).__init__(index, parent=parent)
        if not index.isValid():
            return

        server, job, root, count = self.index.data(
            common.DescriptionRole
        ).split(',')

        menu_set = OrderedDict()

        menu_set['separator'] = {}
        menu_set['header'] = {
            'text': '{}: {}'.format(job, root),
            'disabled': True,
            'visible': index.isValid()
        }

        self.create_menu(menu_set)

    # def activate(self):
    #     self.parent().set_current_item_as_active()
    #
    # def remove(self):
    #     """Remove the bookmark from the ``local_settings``."""
    #     k = self.index.data(common.PathRole).filePath()
    #     bookmarks = local_settings.value('bookmarks')
    #
    #     k = bookmarks.pop(k, None)
    #     if not k:
    #         raise RuntimeError('Failed to remove bookmark.')
    #
    #     local_settings.setValue('bookmarks', bookmarks)
    #     self.parent().refresh()
    #
    # def remove_all(self):
    #     """Removes all saved locations from the bookmarks list."""
    #     local_settings.setValue('bookmarks', None)
    #
    #     local_settings.setValue('activepath/server', None)
    #     local_settings.setValue('activepath/job', None)
    #     local_settings.setValue('activepath/root', None)
    #     local_settings.setValue('activepath/asset', None)
    #     local_settings.setValue('activepath/file', None)
    #
    #     self.parent().refresh()
    #
    # def refresh(self):
    #     self.parent().refresh()


class BookmarksWidget(BaseListWidget):
    """Custom QListWidget containing all the active locations.

    Assets are folders with an identifier file, by default
    the asset collector will look for a file in the root of the asset folder
    called ``workspace.mel``. If this file is not found the folder is ignored.

    Signals:
        locationChanged

    """

    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)
        self.setWindowTitle('Bookmarks')
        self.setItemDelegate(BookmarksWidgetDelegate(parent=self))
        self._context_menu_cls = BookmarksWidgetContextMenu

        self._connectSignals()

        # Select the active item
        self.setCurrentItem(self.active_item())

    def _connectSignals(self):
        pass

    def set_current_item_as_active(self):
        """Sets the current item as ``active_item``.

        Emits the ``activeBookmarkChanged``, ``activeAssetChanged`` and
        ``activeFileChanged`` signals.

        """
        item = self.currentItem()
        server, job, root, _ = item.data(common.DescriptionRole).split(',')

        # Updating the local config file
        local_settings.setValue('activepath/server', server)
        local_settings.setValue('activepath/job', job)
        local_settings.setValue('activepath/root', root)
        local_settings.setValue('activepath/asset', None)
        local_settings.setValue('activepath/file', None)

        archived = item.flags() & configparser.MarkedAsArchived
        if archived:
            return

        # Set flags
        active_item = self.active_item()
        if active_item:
            active_item.setFlags(active_item.flags() & ~
                                 configparser.MarkedAsActive)
        item.setFlags(item.flags() | configparser.MarkedAsActive)

        # Emiting active changed signals
        self.activeBookmarkChanged.emit((server, job, root))
        self.activeAssetChanged.emit(None)
        self.activeFileChanged.emit(None)

    def show_add_bookmark_widget(self):
        """Opens a dialog to add a new project to the list of saved locations."""
        bookmarks_widget = UpdateConfigWidget(parent=self)

        top_left = self.viewport().mapToGlobal(self.viewport().rect().topLeft())
        rect = QtCore.QRect(
            top_left.x(),
            top_left.y(),
            self.viewport().geometry().width(),
            self.viewport().geometry().height()
        )
        if self.viewport().width() < 300:
            bookmarks_widget.label.setHidden(True)

        bookmarks_widget.setGeometry(rect)

        pixmap = common.get_thumbnail_pixmap(common.CUSTOM_THUMBNAIL)
        bookmarks_widget.setWindowIcon(QtGui.QIcon(pixmap))

        if not bookmarks_widget.exec_():
            return

        bookmark = bookmarks_widget.get_bookmark()
        key = next((k for k in bookmark), None)
        if not key:
            return

        bookmarks = local_settings.value('bookmarks')
        if not bookmarks:
            local_settings.setValue('bookmarks', bookmark)
            self.refresh()

            for n in xrange(self.count()):
                if self.item(n).data(common.PathRole).filePath() == key:
                    self.setCurrentItem(self.item(n))
                break
            self.set_current_item_as_active()

            return

        if (
            not bookmark[key]['server'] or
            not bookmark[key]['job'] or
            not bookmark[key]['root']
        ):
            raise ValueError('The selected bookmark contains invalid values.')

        bookmarks[key] = bookmark[key]
        local_settings.setValue('bookmarks', bookmarks)

        if self.count() == 1:
            local_settings.setValue(
                'activepath/server', bookmark[key]['server'])
            local_settings.setValue('activepath/job', bookmark[key]['job'])
            local_settings.setValue('activepath/root', bookmark[key]['root'])
            local_settings.setValue('activepath/asset', None)
            local_settings.setValue('activepath/file', None)

        self.refresh()

        for n in xrange(self.count()):
            if self.item(n).data(common.PathRole).filePath() == key:
                self.setCurrentItem(self.item(n))
                break

    def set_row_visibility(self):
        pass

    def add_items(self):
        """Adds the bookmarks saved in the local_settings file to the widget."""
        self.clear()

        # Collecting items
        collector = BookmarksCollector()
        items = collector.get_items(
            key=self.sort_order(),
            reverse=self.is_reversed(),
            path_filter=self.filter()
        )

        for file_info in items:
            item = QtWidgets.QListWidgetItem()

            # Data
            item.setData(
                QtCore.Qt.DisplayRole,
                u'{}  -  {}'.format(file_info.job, file_info.root)
            )
            item.setData(QtCore.Qt.EditRole, item.data(QtCore.Qt.DisplayRole))
            item.setData(QtCore.Qt.StatusTipRole,
                         u'Bookmark: {}/{}/{}'.format(
                             file_info.server,
                             file_info.job,
                             file_info.root))
            item.setData(QtCore.Qt.ToolTipRole,
                         item.data(QtCore.Qt.StatusTipRole))
            item.setData(common.DescriptionRole,
                         u'{},{},{},{}'.format(
                             file_info.server,
                             file_info.job,
                             file_info.root,
                             file_info.size()))
            item.setData(common.PathRole,
                         QtCore.QFileInfo('{}/{}/{}'.format(
                             file_info.server,
                             file_info.job,
                             file_info.root)))
            item.setData(
                QtCore.Qt.SizeHintRole,
                QtCore.QSize(common.WIDTH, common.ROW_HEIGHT))

            # Active
            if (
                file_info.server == local_settings.value('activepath/server') and
                file_info.job == local_settings.value('activepath/job') and
                file_info.root == local_settings.value('activepath/root')
            ):
                item.setFlags(item.flags() | configparser.MarkedAsActive)

            # Archived means the server is not reachable
            if not file_info.exists():
                item.setFlags(item.flags() | configparser.MarkedAsArchived)

            # Flags
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            self.addItem(item)

        # The 'Add location' button at the bottom of the list
        item=QtWidgets.QListWidgetItem()
        item.setFlags(QtCore.Qt.NoItemFlags)
        item.setData(
            QtCore.Qt.DisplayRole,
            'Add location'
        )
        item.setData(
            QtCore.Qt.EditRole,
            'Add location'
        )
        item.setData(
            QtCore.Qt.StatusTipRole,
            'Add a new bookmark'
        )
        item.setData(
            QtCore.Qt.ToolTipRole,
            'Add a new bookmark'
        )
        item.setData(
            common.PathRole,
            None
        )

        self.addItem(item)

    def mouseReleaseEvent(self, event):
        """Custom mouse event handling the add button click."""
        index=self.indexAt(event.pos())
        if index.isValid() and index.row() == (self.count() - 1):
            self.show_add_bookmark_widget()
            return
        super(BookmarksWidget, self).mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """When the bookmark item is double-clicked the the item will be actiaved.
        """
        if self.currentItem() is self.active_item():
            return
        self.set_current_item_as_active()


if __name__ == '__main__':
    app=QtWidgets.QApplication([])
    app.w=BookmarksWidget()
    app.w.show()
    app.exec_()
