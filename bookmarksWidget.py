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

import mayabrowser.configparsers as configparser
from mayabrowser.configparsers import local_settings
from mayabrowser.delegate import BookmarksWidgetDelegate
from mayabrowser.updatewidget import UpdateConfigWidget


class BookmarksWidgetContextMenu(BaseContextMenu):
    """Context menu associated with the BookmarksWidget.

    Methods:
        refresh:                    Refreshes the collector and repopulates the widget.

    """

    def add_actions(self):
        self.add_action_set(self.ACTION_SET)

    @property
    def ACTION_SET(self):
        """A custom set of actions to display."""
        items = OrderedDict()

        if self.index.isValid():
            if self.index.data(QtCore.Qt.DisplayRole) == 'Add location':
                return items

            server, job, root, _ = self.index.data(
                common.DescriptionRole).split(',')

            items['{} - {}'.format(job.upper(), root.upper())
                  ] = {'disabled': True}
            if not self.index.flags() & configparser.MarkedAsActive:
                items['Activate'] = {}
            items['<separator>...'] = {}
            items['Reveal bookmark'] = {}
            items['Reveal server'] = {}
            items['Reveal job'] = {}
            items['<separator>..'] = {}
            if not self.index.flags() & configparser.MarkedAsActive:
                items['Remove'] = {}
            items['<separator>...'] = {}
        items['Refresh'] = {}
        items['<separator>....'] = {}
        items['Remove all'] = {}
        return items

    def activate(self):
        self.parent().set_current_item_as_active()

    def reveal_bookmark(self):
        """Shows the current server folder in the file explorer."""
        file_info = self.index.data(common.PathRole)
        url = QtCore.QUrl.fromLocalFile(file_info.filePath())
        QtGui.QDesktopServices.openUrl(url)

    def reveal_server(self):
        """Shows the current server folder in the file explorer."""
        server, _, _, _ = self.index.data(common.DescriptionRole).split(',')
        file_info = QtCore.QFileInfo('{}'.format(server))
        url = QtCore.QUrl.fromLocalFile(file_info.filePath())
        QtGui.QDesktopServices.openUrl(url)

    def reveal_job(self):
        """Shows the current server folder in the file explorer."""
        server, job, _, _ = self.index.data(common.DescriptionRole).split(',')
        file_info = QtCore.QFileInfo('{}/{}'.format(server, job))
        url = QtCore.QUrl.fromLocalFile(file_info.filePath())
        QtGui.QDesktopServices.openUrl(url)

    def remove(self):
        """Remove the bookmark from the ``local_settings``."""
        k = self.index.data(common.PathRole).filePath()
        bookmarks = local_settings.value('bookmarks')

        k = bookmarks.pop(k, None)
        if not k:
            raise RuntimeError('Failed to remove bookmark.')

        local_settings.setValue('bookmarks', bookmarks)
        self.parent().refresh()

    def remove_all(self):
        """Removes all saved locations from the bookmarks list."""
        local_settings.setValue('bookmarks', None)

        local_settings.setValue('activepath/server', None)
        local_settings.setValue('activepath/job', None)
        local_settings.setValue('activepath/root', None)

        self.parent().refresh()

    def refresh(self):
        self.parent().refresh()


class BookmarksWidget(BaseListWidget):
    """Custom QListWidget containing all the active locations.

    Assets are folders with an identifier file, by default
    the asset collector will look for a file in the root of the asset folder
    called ``workspace.mel``. If this file is not found the folder is ignored.

    Signals:
        locationChanged

    """
    Delegate = BookmarksWidgetDelegate
    ContextMenu = BookmarksWidgetContextMenu

    # Signals
    activeChanged = QtCore.Signal(str, str, str)

    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)
        self.setWindowTitle('Bookmarks')
        self._connectSignals()

        # Select the active item
        self.setCurrentItem(self.active_item())

    def _connectSignals(self):
        pass

    def set_current_item_as_active(self):
        """Sets the current item item as ``active``."""
        item = self.currentItem()
        server, job, root, _ = item.data(common.DescriptionRole).split(',')

        # Updating the local config file
        local_settings.setValue('activepath/server', server)
        local_settings.setValue('activepath/job', job)
        local_settings.setValue('activepath/root', root)

        archived = item.flags() & configparser.MarkedAsArchived
        if archived:
            return

        # Set flags
        active_item = self.active_item()
        if active_item:
            active_item.setFlags(active_item.flags() & ~
                                 configparser.MarkedAsActive)
        item.setFlags(item.flags() | configparser.MarkedAsActive)

        # Emiting change a signal upon change
        self.activeChanged.emit(server, job, root)

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

        self.refresh()

        for n in xrange(self.count()):
            if self.item(n).data(common.PathRole).filePath() == key:
                self.setCurrentItem(self.item(n))
                break

    def refresh(self, *args):
        """Refreshes the list of found assets."""
        idx = self.currentIndex()
        self.add_items()
        self.setCurrentIndex(idx)

    def set_row_visibility(self):
        pass

    def add_items(self):
        """Adds the bookmarks saved in the local_settings file to the widget."""
        self.clear()

        if not local_settings.value('bookmarks'):
            item = QtWidgets.QListWidgetItem('Add location')
            self.addItem(item)
            return

        bookmarks = local_settings.value('bookmarks')
        for k in sorted(bookmarks):
            item = QtWidgets.QListWidgetItem()

            path = u'{}/{}/{}'.format(
                bookmarks[k]['server'],
                bookmarks[k]['job'],
                bookmarks[k]['root'])
            count = common.count_assets(path)

            # Data
            item.setData(QtCore.Qt.DisplayRole,
                         u'{}  -  {}'.format(
                             bookmarks[k]['job'],
                             bookmarks[k]['root']))
            item.setData(QtCore.Qt.EditRole,
                         item.data(QtCore.Qt.DisplayRole))
            item.setData(QtCore.Qt.StatusTipRole,
                         u'Bookmark: {}/{}/{}'.format(
                             bookmarks[k]['server'],
                             bookmarks[k]['job'],
                             bookmarks[k]['root']))
            item.setData(QtCore.Qt.ToolTipRole,
                         item.data(QtCore.Qt.StatusTipRole))
            item.setData(common.DescriptionRole,
                         u'{},{},{},{}'.format(
                             bookmarks[k]['server'],
                             bookmarks[k]['job'],
                             bookmarks[k]['root'],
                             count))
            item.setData(common.PathRole,
                         QtCore.QFileInfo('{}/{}/{}'.format(
                             bookmarks[k]['server'],
                             bookmarks[k]['job'],
                             bookmarks[k]['root'])))
            item.setData(
                QtCore.Qt.SizeHintRole,
                QtCore.QSize(common.WIDTH, common.ROW_HEIGHT))

            # Active
            if (
                bookmarks[k]['server'] == local_settings.value('activepath/server') and
                bookmarks[k]['job'] == local_settings.value('activepath/job') and
                bookmarks[k]['root'] == local_settings.value('activepath/root')
            ):
                item.setFlags(item.flags() | configparser.MarkedAsActive)

            # Archived means the server is not reachable
            exists = QtCore.QFileInfo(path).exists()
            if not exists:
                item.setFlags(item.flags() | configparser.MarkedAsArchived)

            # Flags
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            self.addItem(item)

        item = QtWidgets.QListWidgetItem()
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
        index = self.indexAt(event.pos())
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

    def action_on_enter_key(self):
        """Custom enter key action."""
        pass

    def action_on_custom_keys(self, event):
        """Custom keyboard shortcuts for the AssetsWidget are defined here."""
        pass


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    app.w = BookmarksWidget()
    app.w.show()
    app.exec_()
