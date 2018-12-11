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

from mayabrowser.configparsers import local_config
from mayabrowser.delegate import LocationWidgetDelegate
from mayabrowser.updatewidget import UpdateConfigWidget


class LocationWidgetContextMenu(BaseContextMenu):
    """Context menu associated with the LocationWidget.

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

            server, job, root = self.index.data(QtCore.Qt.StatusTipRole).split(',')

            items['{} - {}'.format(job.upper(), root.upper())] = {'disabled': True}
            items['Reveal bookmark'] = {}
            items['<separator>.'] = {}
            items['Reveal server'] = {}
            items['Reveal job'] = {}
            items['<separator>..'] = {}
            items['Remove bookmark'] = {}
            items['<separator>...'] = {}
        items['Refresh'] = {}
        items['<separator>....'] = {}
        items['Remove all bookmarks'] = {}
        return items

    @staticmethod
    def reveal_bookmark():
        """Shows the current server folder in the file explorer."""
        file_info = QtCore.QFileInfo(
            '{}/{}/{}'.format(
                local_config.server,
                local_config.job,
                local_config.root
            )
        )
        url = QtCore.QUrl.fromLocalFile(file_info.filePath())
        QtGui.QDesktopServices.openUrl(url)

    @staticmethod
    def reveal_server():
        """Shows the current server folder in the file explorer."""
        file_info = QtCore.QFileInfo(
            '{}'.format(
                local_config.server
            )
        )
        url = QtCore.QUrl.fromLocalFile(file_info.filePath())
        QtGui.QDesktopServices.openUrl(url)

    @staticmethod
    def reveal_job():
        """Shows the current server folder in the file explorer."""
        file_info = QtCore.QFileInfo(
            '{}/{}'.format(
                local_config.server,
                local_config.job
            )
        )
        url = QtCore.QUrl.fromLocalFile(file_info.filePath())
        QtGui.QDesktopServices.openUrl(url)


    def add_bookmark(self):
        pass

    def remove_bookmark(self):
        local_config.remove_location(
            *self.index.data(QtCore.Qt.StatusTipRole).split(',')
        )
        self.parent().refresh()

    def remove_all_bookmarks(self):
        """Removes all saved locations from the bookmarks list."""
        local_config.clear_locations()
        self.parent().refresh()

    def refresh(self):
        self.parent().refresh()


class LocationWidget(BaseListWidget):
    """Custom QListWidget containing all the active locations.

    Assets are folders with an identifier file, by default
    the asset collector will look for a file in the root of the asset folder
    called ``workspace.mel``. If this file is not found the folder is ignored.

    Signals:
        locationChanged

    """
    Delegate = LocationWidgetDelegate
    ContextMenu = LocationWidgetContextMenu

    # Signals
    locationChanged = QtCore.Signal(str, str, str)

    def __init__(self, parent=None):
        super(LocationWidget, self).__init__(parent=parent)
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
            data = item.data(QtCore.Qt.StatusTipRole)
            if not data:
                continue

            server, job, root = item.data(QtCore.Qt.StatusTipRole).split(',')

            if (
                server == local_config.server and
                job == local_config.job and
                root == local_config.root
            ):
                return item
        return None


    def add_project(self):
        """Opens a dialog to add a new project to the list of saved locations.
        """
        local_config.read_ini()

        w = UpdateConfigWidget(
            server=local_config.server,
            job=local_config.job,
            root=local_config.root
        )
        pixmap = self.parent().parent().get_thumbnail_pixmap(common.CUSTOM_THUMBNAIL)
        w.setWindowIcon(QtGui.QIcon(pixmap))

        result = w.exec_()

        if result:
            local_config.server = w.server
            local_config.job = w.job
            local_config.root = w.root

        local_config.append_to_location(w.server, w.job, w.root)
        self.locationChanged.emit(w.server, w.job, w.root)


    def refresh(self, *args):
        """Refreshes the list of found assets."""
        idx = self.currentIndex()
        self.add_items()
        self.setCurrentIndex(idx)

    def set_row_visibility(self):
        pass

    def add_items(self):
        """Querries the local_config instance and adds all the saved locations.
        """
        self.clear()
        if not local_config.locations:
            item = QtWidgets.QListWidgetItem('Add location')
            self.addItem(item)
            return

        for location in local_config.locations:
            item = QtWidgets.QListWidgetItem()

            try:
                server, job, root = location
            except ValueError:
                server, job, root = ('', '', '')

            if server == '':
                continue
            elif job == '':
                continue
            elif root == '':
                continue

            item.setData(
                QtCore.Qt.DisplayRole,
                '{}  -  {}'.format(job, root)
            )
            item.setData(
                QtCore.Qt.EditRole,
                '{}  -  {}'.format(job, root)
            )
            item.setData(
                QtCore.Qt.StatusTipRole,
                '{},{},{}'.format(server, job, root)
            )
            item.setData(
                QtCore.Qt.ToolTipRole,
                '{},{},{}'.format(server, job, root)
            )

            item.setSizeHint(QtCore.QSize(common.WIDTH, common.ROW_HEIGHT))
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            self.addItem(item)


        item = QtWidgets.QListWidgetItem('Add location')
        item.setFlags(QtCore.Qt.NoItemFlags)
        self.addItem(item)

    def mouseReleaseEvent(self, event):
        """Custom mouse event handling the add button click."""
        index = self.indexAt(event.pos())
        if index.isValid() and index.row() == (self.count() - 1):
            self.add_project()
            return
        super(LocationWidget, self).mouseReleaseEvent(event)

    def custom_doubleclick_event(self, index):
        """We're emiting a custom signal. Any other widgets that need to
        have their content refreshed should connect to the ``locationChanged`` signal.

        """
        server, job, root = index.data(QtCore.Qt.StatusTipRole).split(',')

        local_config.read_ini()

        # Updating the local config file
        local_config.server = server
        local_config.job = job
        local_config.root = root

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
    LocationWidget().show()
    app.exec_()
