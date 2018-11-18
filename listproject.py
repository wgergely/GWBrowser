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

import os
from collections import OrderedDict
import functools
from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common
from mayabrowser.listbase import BaseContextMenu
from mayabrowser.listbase import BaseListWidget

import mayabrowser.configparsers as configparser
from mayabrowser.configparsers import local_config
from mayabrowser.configparsers import ProjectConfig
from mayabrowser.collector import ProjectCollector
from mayabrowser.delegate import ProjectWidgetDelegate
from mayabrowser.popover import PopupCanvas


class ProjectWidgetContextMenu(BaseContextMenu):
    """Context menu associated with the ProjectWidget.

    Methods:
        set_as_active_project:      Sets the current item as the *`active item`*
        show_project_in_explorer:   Shows current item in the explorer.
        show_textures:              Shows the project's ``textures`` folder.
        show_scenes:                Shows the project's ``scenes`` folder.
        show_renders:               Shows the project's ``renders`` folder.
        show_exports:               Shows the project's ``exports`` folder.
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
        self.parent().hide()
        self.parent().parent_.sync_config()
        self.parent().parent_.projectsButton.clicked.emit()

    def add_location(self):
        """Populates the menu with location of project locations."""
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
            items['Set as active project'] = {}
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
            items['Show project in explorer'] = {}
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

    def set_as_active_project(self):
        self.parent().active_item = self.parent().currentItem()

    def capture_thumbnail(self):
        self.parent().capture_thumbnail()

    def show_project_in_explorer(self):
        self.parent().reveal_project()

    def show_textures(self):
        self.parent().reveal_project_textures()

    def show_scenes(self):
        self.parent().reveal_project_scenes()

    def show_renders(self):
        self.parent().reveal_project_renders()

    def show_exports(self):
        self.parent().reveal_project_exports()

    def refresh(self):
        self.parent().refresh()
        self.parent().parent_.projectsButton.clicked.emit()


class ProjectWidget(BaseListWidget):
    """Custom QListWidget containing all the collected maya projects.

    Projects are folders with an identifier file, by default
    the project collector will look for a file in the root of the project folder
    called ``workspace.mel``. If this file is not found the folder is ignored.

    """
    Config = ProjectConfig
    Delegate = ProjectWidgetDelegate
    ContextMenu = ProjectWidgetContextMenu

    def __init__(self, parent=None):
        self._collector = ProjectCollector(
            server=local_config.server,
            job=local_config.job,
            root=local_config.root
        )
        super(ProjectWidget, self).__init__(parent=parent)
        self.setWindowTitle('Projects')

        # self.long_presstimer = QtCore.QTimer()
        # self.long_presstimer.setInterval(300)
        # self.long_presstimer.setSingleShot(True)
        # self.long_presstimer.timeout.connect(self.show_popover)

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
        """The current filter - this is notcurrently  implemented for ``ProjectWidget``."""
        return '/'

    @property
    def active_item(self):
        """``active_item`` defines the currently set maya project.
        The property is querried by FilesWidget to list the available
        Maya scenes.

        Note:
            Setting ``active_item`` emits a ``projectChanged`` signal.

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
            self.projectChanged.emit()
        else:
            self.collector.set_active_item(None)

    @property
    def show_favourites_mode(self):
        """The current show favourites state as saved in the local configuration file."""
        return local_config.show_favourites_project_mode

    @show_favourites_mode.setter
    def show_favourites_mode(self, val):
        local_config.show_favourites_project_mode = val

    @property
    def show_archived_mode(self):
        """The current Show archived state as saved in the local configuration file."""
        return local_config.show_archived_project_mode

    @show_archived_mode.setter
    def show_archived_mode(self, val):
        local_config.show_archived_project_mode = val

    def refresh(self, **kwargs):
        """Refreshes the list of found projects."""
        # Remove QFileSystemWatcher paths:
        for path in self.fileSystemWatcher.directories():
            self.fileSystemWatcher.removePath(path)

        idx = self.currentIndex()
        self.collector.update(**kwargs)
        self.add_collector_items()  # Adds the file

        self.parent_.sync_active_maya_project()
        self.set_row_visibility()
        self.set_custom_size()
        self.setCurrentIndex(idx)

    def add_collector_items(self):
        """Retrieves the projects found by the ProjectCollector and adds them as
        QListWidgetItems.

        Note:
            The method adds the projects' parent folder to the QFileSystemWatcher to monitor
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
                'Maya project at \n{}\n{}'.format(
                    f.filePath(),
                    'Ctrl+P to reveal'
                )
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
            item.setSizeHint(QtCore.QSize(common.WIDTH, common.ROW_HEIGHT * 1.33334))
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            self.addItem(item)

    def action_on_enter_key(self):
        """Custom enter key action."""
        self.active_item = self.currentItem()
        self.parent_.filesButton.clicked.emit()

    def action_on_custom_keys(self, event):
        """Custom keyboard shortcuts for the ProjectsWidget are defined here.

        **Implemented shortcuts**:
        ::

            Ctrl + C:           Copies the project's path to the clipboard.
            Ctrl + Shift + C:   Copies the files's URI path to the clipboard.
            Ctrl + O:           Sets the current item as the active project and opens shows the filewidget.
            Ctrl + P:           Reveals the project in the explorer.
            Ctrl + T:           Reveals the project's textures folder.
            Ctrl + S:           Reveals the project's scenes folder.
            Ctrl + R:           Reveals the project's renders folder.
            Ctrl + E:           Reveals the project's exports folder.
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
                self.parent_.filesButton.clicked.emit()
            if event.key() == QtCore.Qt.Key_C:
                path = os.path.normpath(data)
                QtGui.QClipboard().setText(path)
            elif event.key() == QtCore.Qt.Key_P:
                self.reveal_project()
                self.hide()
            elif event.key() == QtCore.Qt.Key_T:
                self.reveal_project_textures()
                self.hide()
            elif event.key() == QtCore.Qt.Key_S:
                self.reveal_project_scenes()
                self.hide()
            elif event.key() == QtCore.Qt.Key_R:
                self.reveal_project_renders()
                self.hide()
            elif event.key() == QtCore.Qt.Key_E:
                self.reveal_project_exports()
                self.hide()
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

    def reveal_project(self):
        item = self.currentItem()
        path = item.data(QtCore.Qt.StatusTipRole)
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def reveal_project_textures(self):
        """Opens the ``textures`` folder."""
        item = self.currentItem()
        path = '{}/{}'.format(
            item.data(QtCore.Qt.StatusTipRole),
            local_config.project_textures_folder
        )
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def reveal_project_scenes(self):
        """Opens the ``scenes`` folder."""
        item = self.currentItem()
        path = '{}/{}'.format(
            item.data(QtCore.Qt.StatusTipRole),
            local_config.project_scenes_folder
        )
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def reveal_project_renders(self):
        """Opens the ``renders`` folder."""
        item = self.currentItem()
        path = '{}/{}'.format(
            item.data(QtCore.Qt.StatusTipRole),
            local_config.project_renders_folder
        )
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def reveal_project_exports(self):
        """Opens the ``exports`` folder."""
        item = self.currentItem()
        path = '{}/{}'.format(
            item.data(QtCore.Qt.StatusTipRole),
            local_config.project_exports_folder
        )
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def eventFilter(self, widget, event):
        """ProjectWidget's custom paint is triggered here.

        I'm using the custom paint event to display a user message when no
        project or files can be found.

        """
        if event.type() == QtCore.QEvent.Paint:
            self._paint_widget_background()

            if self.count() == 0:
                # Message to show when no projects are found.
                set_text = 'No projects found in \n{}/{}/{}'.format(
                    self.parent_._kwargs['server'],
                    self.parent_._kwargs['job'],
                    self.parent_._kwargs['root'],
                ).strip('/')

                # Message to show when no configuration has been set.
                not_set_text = 'Browser not yet configured.\n'
                not_set_text += 'Right-click on the Browser Toolbar and select \'Configure\' to set the location of your projects.'
                text = set_text if self.parent_._kwargs['server'] else not_set_text

                self.paint_message(text)
            elif self.count() > self.count_visible():
                self.paint_message(
                    '{} items are hidden.'.format(self.count())
                )

        return False

    def showEvent(self, event):
        """Show event will set the size of the widget."""
        self.set_custom_size()
        self.move(self.x(), self.y())
        self.parent_.sync_active_maya_project(setActive=False)
