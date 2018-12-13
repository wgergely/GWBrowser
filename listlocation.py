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

            server, job, root = self.index.data(
                QtCore.Qt.UserRole).split(',')

            items['{} - {}'.format(job.upper(), root.upper())
                  ] = {'disabled': True}
            items['Reveal bookmark'] = {}
            items['Reveal server'] = {}
            items['Reveal job'] = {}
            items['<separator>..'] = {}
            items['Remove bookmark'] = {}
            items['<separator>...'] = {}
        items['Refresh'] = {}
        items['<separator>....'] = {}
        items['Remove all bookmarks'] = {}
        return items

    def reveal_bookmark(self):
        """Shows the current server folder in the file explorer."""
        file_info = self.index.data(QtCore.Qt.PathRole)
        print file_info

        url = QtCore.QUrl.fromLocalFile(file_info.filePath())
        QtGui.QDesktopServices.openUrl(url)

    @staticmethod
    def reveal_server():
        """Shows the current server folder in the file explorer."""
        file_info = QtCore.QFileInfo(
            '{}'.format(
                local_settings.server
            )
        )
        url = QtCore.QUrl.fromLocalFile(file_info.filePath())
        QtGui.QDesktopServices.openUrl(url)

    @staticmethod
    def reveal_job():
        """Shows the current server folder in the file explorer."""
        file_info = QtCore.QFileInfo(
            '{}/{}'.format(
                local_settings.server,
                local_settings.job
            )
        )
        url = QtCore.QUrl.fromLocalFile(file_info.filePath())
        QtGui.QDesktopServices.openUrl(url)

    def add_bookmark(self):
        pass

    def remove_bookmark(self):
        local_settings.remove_location(
            *self.index.data(QtCore.Qt.UserRole).split(',')
        )
        self.parent().refresh()

    def remove_all_bookmarks(self):
        """Removes all saved locations from the bookmarks list."""
        local_settings.clear_locations()
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
    locationChanged = QtCore.Signal(str, str, str)

    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)
        self.setWindowTitle('Projects')
        self._connectSignals()

    def _connectSignals(self):
        self.locationChanged.connect(self.refresh)

    @property
    def activeItem(self):
        """The QListWidgetItem associated with the saved active location.

        Returns:
            QListWidgetItem or None

        """
        for n in xrange(self.count()):
            item = self.item(n)
            data = item.data(QtCore.Qt.UserRole)
            if not data:
                continue

            try:
                server, job, root = item.data(
                    QtCore.Qt.UserRole).split(',')
            except ValueError:
                continue

            if (
                server == local_settings.server and
                job == local_settings.job and
                root == local_settings.root
            ):
                return item
        return None

    def add_project(self):
        """Opens a dialog to add a new project to the list of saved locations."""
        w = UpdateConfigWidget()
        pixmap = self.parent().parent().get_thumbnail_pixmap(common.CUSTOM_THUMBNAIL)
        w.setWindowIcon(QtGui.QIcon(pixmap))

        result = w.exec_()

        # if result:
        #     local_settings.server = w.server
        #     local_settings.job = w.job
        #     local_settings.root = w.root
        #
        # local_settings.append_to_location(w.server, w.job, w.root)
        # self.locationChanged.emit(w.server, w.job, w.root)

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

        if not local_settings.locations:
            item = QtWidgets.QListWidgetItem('Add location')
            self.addItem(item)
            return

        for location in local_settings.locations:
            item = QtWidgets.QListWidgetItem()

            try:
                server, job, root = location
            except ValueError:
                server, job, root = ('', '', '')

            if (server or job or root) == '':
                continue

            # Data
            item.setData(QtCore.Qt.DisplayRole,
                         '{}  -  {}'.format(job, root))
            item.setData(QtCore.Qt.EditRole,
                         item.data(QtCore.Qt.DisplayRole))
            item.setData(QtCore.Qt.StatusTipRole,
                         'Bookmark: {}/{}/{}'.format(server, job, root))
            item.setData(QtCore.Qt.ToolTipRole,
                         item.data(QtCore.Qt.StatusTipRole))
            item.setData(QtCore.Qt.UserRole,
                         '{},{},{}'.format(server, job, root))
            item.setData(QtCore.Qt.PathRole,
                         QtCore.QFileInfo('{}/{}/{}'.format(server, job, root)))
            item.setData(
                QtCore.Qt.SizeHintRole,
                QtCore.QSize(common.WIDTH, common.ROW_HEIGHT))

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
            QtCore.Qt.PathRole,
            None
        )

        self.addItem(item)

    def mouseReleaseEvent(self, event):
        """Custom mouse event handling the add button click."""
        index = self.indexAt(event.pos())
        if index.isValid() and index.row() == (self.count() - 1):
            self.add_project()
            return
        super(BookmarksWidget, self).mouseReleaseEvent(event)

    def custom_doubleclick_event(self, index):
        """We're emiting a custom signal. Any other widgets that need to
        have their content refreshed should connect to the ``locationChanged`` signal.

        """
        server, job, root = index.data(QtCore.Qt.UserRole).split(',')

        local_settings.read_ini()

        # Updating the local config file
        local_settings.server = server
        local_settings.job = job
        local_settings.root = root

        # Emiting a signal upon change
        self.locationChanged.emit(server, job, root)

        self.parent().parent().activate_widget(self.parent().parent().assetsWidget)

    def action_on_enter_key(self):
        """Custom enter key action."""
        pass

    def action_on_custom_keys(self, event):
        """Custom keyboard shortcuts for the AssetsWidget are defined here."""
        pass


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    BookmarksWidget().show()
    app.exec_()
