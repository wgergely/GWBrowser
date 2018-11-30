# -*- coding: utf-8 -*-
"""Module defines a ListWidget used to represent the projects found in the root
of the `server/job/projects` folder.

The project collector expects a project to contain an identifier file,
in the case of the default implementation, a ``*.mel`` file in the root of the project folder.
If the identifier file is not found the folder will be ignored!

Projects are based on maya's project structure and ``Browser`` expects a
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
            items['Reveal'] = {}
            items['<separator>.....'] = {}
        items['Refresh'] = {}
        return items

    def reveal(self):
        self.parent().reveal_project_textures()

    def refresh(self):
        self.parent().refresh()


class LocationWidget(BaseListWidget):
    """Custom QListWidget containing all the active locations.

    Projects are folders with an identifier file, by default
    the project collector will look for a file in the root of the project folder
    called ``workspace.mel``. If this file is not found the folder is ignored.

    """
    Delegate = LocationWidgetDelegate
    ContextMenu = LocationWidgetContextMenu

    def __init__(self, parent=None):
        super(LocationWidget, self).__init__(parent=parent)
        self.setWindowTitle('Projects')

    def refresh(self):
        """Refreshes the list of found projects."""
        idx = self.currentIndex()
        self.add_collector_items()
        self.setCurrentIndex(idx)

    def set_row_visibility(self):
        pass
        
    def add_collector_items(self):
        """Retrieves the projects found by the ProjectCollector and adds them as
        QListWidgetItems.

        Note:
            The method adds the projects' parent folder to the QFileSystemWatcher to monitor
            file changes. Any directory change should trigger a refresh. This might
            have some performance implications. Needs testing!

        """
        self.clear()
        if not local_config.location:
            return

        for location in local_config.location:
            if location[0] == '':
                continue

            item = QtWidgets.QListWidgetItem()
            item.setData(
                QtCore.Qt.DisplayRole,
                '{}/{}/{}'.format(*location)
            )
            item.setData(
                QtCore.Qt.EditRole,
                '{}/{}/{}'.format(*location)
            )
            item.setData(
                QtCore.Qt.StatusTipRole,
                '{}/{}/{}'.format(*location)
            )
            item.setData(
                QtCore.Qt.ToolTipRole,
                '{}/{}/{}'.format(*location)
            )

            item.setSizeHint(QtCore.QSize(common.WIDTH, common.ROW_HEIGHT))
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            self.addItem(item)

    def action_on_enter_key(self):
        """Custom enter key action."""
        pass

    def action_on_custom_keys(self, event):
        """Custom keyboard shortcuts for the ProjectsWidget are defined here."""
        pass


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    LocationWidget().show()
    app.exec_()
