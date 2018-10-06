# -*- coding: utf-8 -*-
"""``MayaBrowserWidget`` is the plug-in's main widget.
When launched from within Maya it inherints from MayaQWidgetDockableMixin baseclass,
otherwise MayaQWidgetDockableMixin is replaced with a ``common.LocalContext``, a dummy class.

Example:

.. code-block:: python
    :linenos:

    from mayabrowser.toolbar import MayaBrowserWidget
    widget = MayaBrowserWidget()
    widget.show()

The project and the file lists are collected by the ``collector.ProjectCollector``
and ```collector.FilesCollector`` classes. The gathered files then are displayed
in the ``listwidgets.ProjectsListWidget`` and ``listwidgets.FilesListWidget`` items.

"""

# pylint: disable=E1101, C0103, R0913, I1101, R0903, C0330

from collections import OrderedDict
import functools
from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common
from mayabrowser.common import cmds
from mayabrowser.common import OpenMayaUI
from mayabrowser.common import MayaQWidgetDockableMixin
from mayabrowser.common import shiboken2

from mayabrowser.listproject import ProjectWidget
from mayabrowser.listmaya import MayaFilesWidget
from mayabrowser.configparsers import local_config
from mayabrowser.configparsers import ProjectConfig
from mayabrowser.delegate import ThumbnailEditor
from mayabrowser.updatewidget import UpdateConfigWidget
from mayabrowser.actions import Actions


class MayaBrowserContextMenu(Actions):
    """Context menu associated with the MayaBrowserWidget.

    Methods:
        reveal_server:          Shows the server folder in the explorer.
        reveal_job:             Shows the job folder in the explorer.
        reveal_projects:        Shows the location of the projects in the explorer.
        configure:              Opens ``UpdateConfigWidget`` to configure the local settings.

    """

    def __init__(self, parent=None):
        super(MayaBrowserContextMenu, self).__init__(parent=parent)

    def history_changed(self, action):
        """Action triggered when the history has changed."""
        local_config.server = action.data()[0]
        local_config.job = action.data()[1]
        local_config.root = action.data()[2]
        self.parent().sync_config()

    def add_history(self):
        """Populates the menu with history of project locations."""
        submenu = self.addMenu('History')
        if not local_config.history:
            return

        for item in local_config.history:
            if item[0] == '':
                continue
            action = submenu.addAction('{}/{}/{}'.format(*item))
            action.setData(item)
            action.triggered.connect(
                functools.partial(self.history_changed, action))
            action.setCheckable(True)
            if (
                (item[0] == local_config.server) and
                (item[1] == local_config.job) and
                (item[2] == local_config.root)
            ):
                action.setChecked(True)

    def add_actions(self):
        self.add_history()
        self.add_action_set(self.ACTION_SET)

    @property
    def ACTION_SET(self):
        """Custom contextmenu action-list."""
        items = OrderedDict()
        items['Configure'] = {}
        items['<separator>'] = {}
        items['Reveal projects'] = {}
        items['Reveal job'] = {}
        items['Reveal server'] = {}
        return items

    @staticmethod
    def reveal_server():
        """Shows the current server folder in the file explorer."""
        file_info = QtCore.QFileInfo(
            '{}'.format(local_config.server)
        )
        path = file_info.filePath()
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    @staticmethod
    def reveal_job():
        """Reveals the current job folder in the file explorer."""
        file_info = QtCore.QFileInfo(
            '{}/{}'.format(local_config.server, local_config.job)
        )
        path = file_info.filePath()
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    @staticmethod
    def reveal_projects():
        """Reveals the current projects folder in the file explorer."""
        file_info = QtCore.QFileInfo(
            '{}/{}/{}'.format(local_config.server,
                              local_config.job, local_config.root)
        )
        path = file_info.filePath()
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

    def configure(self):
        """Opens a dialog to set the active project folder and writes
        the pick into a local config file.

        """
        local_config.read_ini()

        w = UpdateConfigWidget(
            server=local_config.server,
            job=local_config.job,
            root=local_config.root
        )
        pixmap = self.parent().get_thumbnail_pixmap(common.CUSTOM_THUMBNAIL)
        w.setWindowIcon(QtGui.QIcon(pixmap))

        result = w.exec_()

        if result:
            local_config.server = w.server
            local_config.job = w.job
            local_config.root = w.root
        self.parent().sync_config()

        local_config.append_to_history(w.server, w.job, w.root)


SingletonType = type(QtWidgets.QWidget)


class Singleton(SingletonType):
    """Singleton metaclass for the MayaBrowserWidget widget.

    Note:
        We have to supply an appropiate type object as the baseclass,
        'type' won't work. Creating type(QtWidgets.QWidget) seems to function.

    """
    _instances = {}

    def __call__(cls, *args, **kwargs):  # pylint: disable=E0213
        if cls not in cls._instances:
            cls._instances[cls] = super(
                Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ProjectThumbnail(QtWidgets.QLabel):
    """Clickable QLabel."""

    clicked = QtCore.Signal()
    doubleClicked = QtCore.Signal()

    def mousePressEvent(self, event):
        """Custom mouse press event."""
        self.clicked.emit()

    def mouseDoubleClickEvent(self, event):
        """Custom mouse double-clicke event."""
        self.doubleClicked.emit()


class MayaBrowserWidget(MayaQWidgetDockableMixin, QtWidgets.QWidget):  # pylint: disable=E1139
    """Singleton MayaQWidgetDockable widget containing the ``projectWidgetButton``
    and the ``filesWidgetButton`` buttons.

    Attributes:
        instances (dict):               Class instances.
        projectsWidget (QListWidget):   List of the collected Maya projects.
        filesWidget (QListWidget):      List of files found associated with the project.

        configChanged (QtCore.QSignal): Custom signal emitted when the configuration file changes.

    """

    __metaclass__ = Singleton
    # """Singleton metaclass."""

    instances = {}
    configChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super(MayaBrowserWidget, self).__init__(parent=parent)
        self.instances[self.objectName()] = self
        self._workspacecontrol = None
        self.maya_callbacks = []  # Maya api callbacks
        self.maya_actions = []  # Maya ui

        # Saving the initial config settings.
        self._kwargs = {
            'server': None,
            'job': None,
            'root': None
        }
        self._createUI()

        pixmap = self.get_thumbnail_pixmap(common.CUSTOM_THUMBNAIL)

        self._contextMenu = None

        self.projectsWidget = ProjectWidget()
        self.projectsWidget.parent_ = self
        self.projectsWidget.setWindowIcon(QtGui.QIcon(pixmap))

        self.filesWidget = MayaFilesWidget()
        self.filesWidget.parent_ = self
        self.filesWidget.setWindowIcon(QtGui.QIcon(pixmap))

        self.config_string = ''
        self.config_watch_timer = QtCore.QTimer()
        self.config_watch_timer.setInterval(2000)

        self._connectSignals()
        self.sync_config()
        self.sync_active_maya_project()

    @property
    def workspacecontrol(self):
        """The workspacecontrol associated with this widget."""
        self._workspacecontrol = self.get_workspace_control()
        return self._workspacecontrol

    @staticmethod
    def get_thumbnail_pixmap(path, opacity=1, size=(common.ROW_HEIGHT / 2.0)):
        """Returns a pixmap of the input path."""
        image = QtGui.QImage()
        image.load(path)
        image = ThumbnailEditor.smooth_copy(image, size)
        pixmap = QtGui.QPixmap()
        pixmap.convertFromImage(image)
        # Setting transparency
        image = QtGui.QImage(
            pixmap.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
        image.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(image)
        painter.setOpacity(opacity)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        pixmap = QtGui.QPixmap()
        pixmap.convertFromImage(image)
        return pixmap

    def setThumbnail(self, path, opacity=1, size=(common.ROW_HEIGHT / 2.0)):
        """Sets the given path as the thumbnail of the project."""
        pixmap = self.get_thumbnail_pixmap(path, opacity=opacity, size=size)
        self.projectThumbnail.setPixmap(pixmap)

    def _createUI(self):
        """Creates the layout."""
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.projectThumbnail = ProjectThumbnail(parent=self)
        self.projectThumbnail.setAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.projectThumbnail.setFixedWidth(common.ROW_HEIGHT / 2.0)
        self.projectThumbnail.setStyleSheet(
            """
            QLabel {
                background-color: rgb(60, 60, 60);
            }
            """
        )
        self.setThumbnail(common.CUSTOM_THUMBNAIL, opacity=0.5)

        self.projectsButton = QtWidgets.QPushButton('Projects')
        self.projectsButton.setStyleSheet(self.buttonStyle())
        self.projectsButton.setToolTip('Browse, activate Maya projects...')
        self.projectsButton.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.projectsButton.setMinimumHeight(common.ROW_HEIGHT / 2.0)
        self.projectsButton.setMaximumHeight(common.ROW_HEIGHT / 2.0)

        self.filesButton = QtWidgets.QPushButton('Files')
        self.filesButton.setStyleSheet(self.buttonStyle())
        self.filesButton.setToolTip(
            'Browse, open, import or reference scene files...')
        self.filesButton.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.filesButton.setMinimumHeight(common.ROW_HEIGHT / 2.0)
        self.filesButton.setMaximumHeight(common.ROW_HEIGHT / 2.0)

        self.layout().addWidget(self.projectThumbnail, 0)
        self.layout().addWidget(self.projectsButton, 0.2)
        self.layout().addWidget(self.filesButton, 1)

        self.setMinimumHeight(common.ROW_HEIGHT / 2.0)
        self.setMaximumHeight(common.ROW_HEIGHT / 2.0)
        self.setMinimumWidth(common.WIDTH)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred
        )
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        pixmap = self.get_thumbnail_pixmap(common.CUSTOM_THUMBNAIL)
        self.setWindowIcon(QtGui.QIcon(pixmap))

    @staticmethod
    def buttonStyle():
        """Returns a style-string defining our custom button."""
        return (
            """
            QPushButton {
                text-align: left;
                border-left: 1px solid rgba(0, 0, 0, 50);
                padding-left: 10px;
                padding-right: 10px;
                border-style: solid;
                color: rgb(210, 210, 210);
                background-color: rgb(68, 68, 68);
            }
            QPushButton:hover {
                border-left: 1px solid rgb(87, 163, 202);
                color: rgb(230, 230, 230);
                background-color: rgb(100, 100, 100);
            }
            QPushButton:pressed {
                border-left: 4px solid rgb(87, 163, 202);
                padding-left: 7px;
                color: rgb(255, 255, 255);
                background-color: rgb(130, 130, 130);
            }
            QToolTip {
                color: rgba(230, 230, 230, 150);
                border: none;
                outline-radius: 4px;
                background-color: rgb(50, 50, 50);
                opacity: 200;
            }
            """
        )

    def contextMenuEvent(self, event):
        """Custom context menu event."""
        self._contextMenu = MayaBrowserContextMenu(parent=self)
        self._contextMenu.setFixedWidth(self.rect().width())
        self._contextMenu.move(self.mapToGlobal(self.rect().bottomLeft()))
        self._contextMenu.show()
        self.move_widget_to_available_geo(self._contextMenu)

    def sync_config(self, *args, **kwargs):
        """Keeps an eye out for configuration file changes and triggers a refresh
        when change is detected.

        """
        if not QtCore.QFileInfo(local_config.getConfigPath(None)).exists():
            return

        local_config.read_ini()
        if (
            (self._kwargs['server'] == local_config.server) and
            (self._kwargs['job'] == local_config.job) and
            (self._kwargs['root'] == local_config.root)
        ):
            return

        print '# Browser: The configuration file has changed.'

        self._kwargs = {
            'server': local_config.server,
            'job': local_config.job,
            'root': local_config.root
        }

        self.filesWidget.hide()
        self.projectsWidget.refresh(**self._kwargs)
        self.projectChanged()
        self.setWindowTitle('{} > {} > {}'.format(
            local_config.server, local_config.job, local_config.root).lower())

    def sync_active_maya_project(self, setActive=True):
        """Selects the active maya project in the list and sets it as the ``active_item``."""
        if not cmds.workspace(q=True, fn=True):
            return

        file_info = QtCore.QFileInfo(cmds.workspace(q=True, fn=True))
        item = self.projectsWidget.findItems(
            file_info.baseName().upper(),
            QtCore.Qt.MatchContains
        )
        if not item:
            return

        index = self.projectsWidget.indexFromItem(item[0])
        self.projectsWidget.setCurrentItem(item[0])
        self.projectsWidget.scrollTo(index)

        if setActive:
            self.projectsWidget.active_item = item[0]

    def sync_active_maya_scene(self, *args, **kwargs):
        """Selects and scrolls to the current item in the list."""
        if not cmds.file(q=True, expandName=True):
            return

        file_info = QtCore.QFileInfo(cmds.file(q=True, expandName=True))
        item = self.filesWidget.findItems(
            file_info.fileName(),
            QtCore.Qt.MatchContains
        )
        if not item:
            return

        index = self.filesWidget.indexFromItem(item[0])
        self.filesWidget.active_item = item[0]
        self.filesWidget.setCurrentItem(item[0])
        self.filesWidget.scrollTo(index)

        #
        font = self.filesButton.font()
        metrics = QtGui.QFontMetrics(font)
        filename = metrics.elidedText(
            file_info.baseName(),
            QtCore.Qt.ElideMiddle,
            self.filesButton.width() - common.MARGIN * 3
        )
        self.filesButton.setText(filename)

    def get_workspace_control(self):
        """Returns the Maya WorkspaceControl associated with the widget.

        TODO:
            Workspacetcontrols are tricky to control in Maya as they are generated
            automatically, upon showing this widget.

            I would love to be able to save the dock-control's position and dock-area,
            but finding it difficult to find a robost way to get these...

        """
        if MayaQWidgetDockableMixin is common.LocalContext:
            return None

        control_name = '{}WorkspaceControl'.format(
            next((f for f in self.instances.iterkeys()), None))
        control_ptr = OpenMayaUI.MQtUtil.findLayout(control_name)
        if not control_ptr:
            return None  # if not visible the control doesn't exists

        return shiboken2.wrapInstance(long(control_ptr), QtWidgets.QWidget)

    def get_parent_window(self):
        """Returns the parent of the workspacecontrol inside Maya."""
        widget = self.get_workspace_control()
        if not widget:
            return None
        return widget.window()

    def is_docked(self):
        """Returns True if the workspacecontrol is docked."""
        win = self.get_parent_window()
        if not win:
            return False
        return True if win.parent() else False

    def show(self):
        """Custom show event. Calls the DockControls's show method with some
        reasonable defaults.

        """
        kwargs = {
            'dockable': True,
            'floating': True,
            'area': None,
            'allowedArea': None,
            'minWidth': common.WIDTH,
            'maxWidth': common.WIDTH * 1.5,
            'width': common.WIDTH,
            'widthSizingProperty': None,
            'height':   common.ROW_HEIGHT / 2.0,
            'minHeight': common.ROW_HEIGHT / 2.0,
            'maxHeight': common.ROW_HEIGHT / 2.0,
            'heightSizingProperty': None,
            'retain': True,
            'plugins': None,
            'controls': None,
            'uiScript': None,
            'closeCallback': None
        }

        if MayaQWidgetDockableMixin is common.LocalContext:
            super(MayaBrowserWidget, self).show()
            return

        super(MayaBrowserWidget, self).show(**kwargs)

    def move_widget_to_available_geo(self, widget):
        """Moves the widget inside the available screen geomtery, if any of the edges
        falls outside.

        """
        app = QtCore.QCoreApplication.instance()
        screenID = app.desktop().screenNumber(self)
        screen = app.screens()[screenID]
        screen_rect = screen.availableGeometry()

        # Widget's rectangle in the global screen space
        rect = QtCore.QRect()
        topLeft = widget.mapToGlobal(widget.rect().topLeft())
        rect.setTopLeft(topLeft)
        rect.setWidth(widget.rect().width())
        rect.setHeight(widget.rect().height())

        x = rect.x()
        y = rect.y()

        if rect.left() < screen_rect.left():
            x = screen_rect.x()
        if rect.top() < screen_rect.top():
            y = screen_rect.y()
        if rect.right() > screen_rect.right():
            x = screen_rect.right() - rect.width()
        if rect.bottom() > screen_rect.bottom():
            y = screen_rect.bottom() - rect.height()

        widget.move(x, y)

    def _connectSignals(self):
        self.projectsButton.clicked.connect(
            functools.partial(self.activate_widget, self.projectsWidget)
        )
        self.projectThumbnail.clicked.connect(
            functools.partial(self.activate_widget, self.projectsWidget)
        )
        self.projectThumbnail.doubleClicked.connect(
            MayaBrowserContextMenu.reveal_projects
        )

        self.filesButton.clicked.connect(
            functools.partial(self.activate_widget, self.filesWidget)
        )

        self.projectsWidget.projectChanged.connect(self.projectChanged)
        self.filesWidget.sceneChanged.connect(self.sync_active_maya_scene)

        self.config_watch_timer.timeout.connect(self.sync_config)

    def add_maya_callbacks(self):
        """This method is called by the Maya plug-in when initializing."""
        import maya.OpenMaya as api
        callback = api.MSceneMessage.addCallback(
            api.MSceneMessage.kAfterOpen, self.MSceneMessage_kAfterOpen)
        self.maya_callbacks.append(callback)

        # I wanted to implement a loading spinner, but Maya is blocking all signals
        # on fileIO operations, hence unable to make this work...

        # def start_spinner(self, userData):
        #     """Custom maya callback."""
        #     self.spinner = Spinner()
        #     self.spinner.start()
        #
        # def stop_spinner(self, userData):
        #     """Custom maya callback."""
        #     self.spinner.stop()
        #     self.spinner.deleteLater()

    @staticmethod
    def get_mayawindow():
        """Returns the Main maya window.

        Note:
            There's a Maya ui method for getting the main window but this
            seems to be working too.

        """
        app = QtCore.QCoreApplication.instance()
        app.maya_window = next(
            (f for f in app.topLevelWidgets() if f.objectName() == 'MayaWindow'),
            RuntimeError('# Browser: Could not find the "MayaWindow".')
        )
        return app.maya_window

    # def add_shortcuts(self):
    #     """Installs application-wide shortcuts for the widget.
    #
    #     When launched from Maya, the global shortcut to show the `MayaBrowserWidget
    #     is ``'Ctrl+Shift+O'``.
    #
    #     """
    #     self.shortcut = QtWidgets.QShortcut(self.get_mayawindow())
    #     self.shortcut.setAutoRepeat(False)
    #     self.shortcut.setContext(QtCore.Qt.ApplicationShortcut)
    #     self.shortcut.setKey(QtGui.QKeySequence('Ctrl+Shift+O'))
    #     self.shortcut.activated.connect(self.shortcutActived)

    @staticmethod
    def get_global_file_menu():
        """Initilizes and returns the Maya application\'s ``File`` menu."""
        app = QtCore.QCoreApplication.instance()
        app.maya_menubar = MayaBrowserWidget.get_mayawindow().findChild(
            QtWidgets.QMenuBar, options=QtCore.Qt.FindDirectChildrenOnly
        )
        app.maya_file_menu = next(
            (f for f in app.maya_menubar.actions() if f.text() == 'File'),
            RuntimeError('# Browser: Could not find the "File" menu.')
        )
        # Trying to avoid garbage collections
        app.maya_file_menu.setParent(app.maya_menubar)
        # Trying to avoid garbage collections
        app.maya_file_menu.menu().setParent(app.maya_menubar)
        app.maya_file_menu = app.maya_file_menu.menu()

        # Let's initialize the menu by showing it programmatically.
        app.maya_file_menu.popup(app.maya_menubar.mapToGlobal(
            app.maya_menubar.geometry().bottomLeft()))
        app.maya_file_menu.setHidden(True)

        return app.maya_file_menu

    def uninitialize(self):
        """Method called by the plug-in, responsible for deleting the widgets."""
        # self.projectsWidget.close()
        # self.filesWidget.close()

        self.filesWidget.deleteLater()
        self.projectsWidget.deleteLater()

        self.close()

    def add_global_app_actions(self):
        """This method is called by the Maya plug-in when loading and unloading,
        and is responsible for populating the ``Application->File`` menu with
        the custom plug-in actions.

        The actions are added after the second separator.
        In Maya 2018, this should be is after the built-in `Open/Save` menus
        but before the `Archive scene` option.

        """
        pixmap = self.get_thumbnail_pixmap(
            common.CUSTOM_THUMBNAIL, opacity=1, size=24
        )
        icon = QtGui.QIcon(pixmap)
        menu = self.get_global_file_menu()

        def _files_func():
            self.projectsWidget.hide()
            self.activate_widget(self.filesWidget)

        def _project_func():
            self.filesWidget.hide()
            self.activate_widget(self.projectsWidget)

        # We're adding our actions after the second separator.
        count = 0
        before = None
        for item in menu.actions():
            if count == 2:
                before = item
                break
            if item.isSeparator():
                count += 1
                continue

        # Last
        action = QtWidgets.QAction(menu)
        action.setSeparator(True)
        menu.insertAction(before, action)
        self.maya_actions.append(action)
        before = action

        action = QtWidgets.QAction('Files...', menu)
        action.setIcon(icon)
        action.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        action.setShortcut('Ctrl+Shift+F')
        action.setStatusTip('Show the project\'s files')

        action.triggered.connect(_files_func)
        menu.insertAction(before, action)
        self.maya_actions.append(action)
        before = action

        action = QtWidgets.QAction('Projects...', menu)
        action.setIcon(icon)
        action.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        action.setShortcut('Ctrl+Shift+P')
        action.setStatusTip('Show the projects')
        action.triggered.connect(_project_func)
        menu.insertAction(before, action)
        self.maya_actions.append(action)
        before = action

        # Toolbar
        action = QtWidgets.QAction('Toolbar', menu)
        action.setIcon(icon)
        action.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        action.setShortcut('Ctrl+Shift+O')
        action.setStatusTip('Show the dockable browser control')
        action.triggered.connect(self.show)
        menu.insertAction(before, action)
        self.maya_actions.append(action)

    def remove_global_app_actions(self):
        """This method is called by the Maya plug-in when unloading."""
        menu = self.get_global_file_menu()
        for action in self.maya_actions:
            menu.removeAction(action)
            action.deleteLater()

    def remove_maya_callbacks(self):
        """This method is called by the Maya plug-in when unloading."""
        import maya.OpenMaya as api
        for callback in self.maya_callbacks:
            api.MMessage.removeCallback(callback)

    def MSceneMessage_kAfterOpen(self, userData):
        """Custom maya callback called after a scene has been opened."""
        self.sync_active_maya_scene()

    def shortcutActived(self):
        """Called by the installed application shortcut."""
        self.show()

    def projectChanged(self):
        """Signal emitted when the project has changed."""
        file_info = self.projectsWidget.collector.active_item
        if file_info:
            cmds.workspace(file_info.filePath(), openWorkspace=True)
            path = ProjectConfig.getThumbnailPath(file_info.filePath())
            thumb_info = QtCore.QFileInfo(path)

            # Set the button name
            self.projectsButton.setText(
                file_info.fileName().replace('_', ' ').title())

            # Setting the project's thumbnail as the label thumbnail
            if thumb_info.exists():
                self.setThumbnail(thumb_info.filePath())
            else:
                self.setThumbnail(common.CUSTOM_THUMBNAIL)
            self.projectsWidget.hide()
        else:
            self.setThumbnail(common.CUSTOM_THUMBNAIL)
            self.projectsWidget.hide()

        self.filesWidget.update_path(file_info)
        self.filesWidget.refresh()

    def move_widget(self, widget):
        """Moves the given widget to bottomLeft corner of the thumbnail label."""
        if not self.isVisible():
            app = QtCore.QCoreApplication.instance()
            cursor = QtGui.QCursor()
            screenID = app.desktop().screenNumber(cursor.pos())
            screen = app.screens()[screenID]
            screen_rect = screen.availableGeometry()

            qr = widget.frameGeometry()
            cp = screen_rect.center()
            qr.moveCenter(cp)
            widget.move(qr.topLeft())
            return

        pos = self.projectThumbnail.mapToGlobal(
            self.projectThumbnail.rect().bottomLeft())
        widget.move(pos.x(), pos.y())

    def activate_widget(self, widget):
        """Method connected to the clicked() signal."""
        self.move_widget(widget)
        widget.setFocus()
        widget.activateWindow()
        widget.raise_()
        widget.show()
        widget.animate_opacity()
        self.move_widget_to_available_geo(widget)

    def showEvent(self, event):
        """Customized show event.

        Sets the window title and the icon based on the configuration values.

        """
        self._kwargs['server'] = local_config.server
        self._kwargs['job'] = local_config.job
        self._kwargs['root'] = local_config.root

        if (
            (not self._kwargs['server']) or
            (not self._kwargs['job']) or
            (not self._kwargs['root'])
        ):
            self.setWindowTitle('Browser not configured')
            return

        self.setWindowTitle('{} > {} > {}'.format(
            local_config.server, local_config.job, local_config.root).lower())
        self.config_watch_timer.start()
        self.sync_active_maya_project()

        if not self.get_workspace_control():
            return

        if not self.is_docked():
            return

        if not self.get_parent_window():
            return

        self.get_parent_window().setFixedWidth(common.WIDTH)
        self.get_parent_window().setFixedHeight(common.ROW_HEIGHT / 2.0)

        pixmap = self.get_thumbnail_pixmap(
            common.CUSTOM_THUMBNAIL, opacity=1, size=(common.ROW_HEIGHT / 2)
        )
        self.setWindowIcon(QtGui.QIcon(pixmap))
        self.get_parent_window().setWindowIcon(QtGui.QIcon(pixmap))

    def keyPressEvent(self, event):
        """Custom key actions."""
        if event.modifiers() == QtCore.Qt.NoModifier:
            if event.key() == QtCore.Qt.Key_P:
                self.projectsButton.clicked.emit()
            elif event.key() == QtCore.Qt.Key_F:
                self.filesButton.clicked.emit()
            elif event.key() == QtCore.Qt.Key_Escape:
                self.hide()

    def hideEvent(self, event):
        """Custom hide event."""
        if self.projectsWidget.isVisible():
            self.projectsWidget.hide()
        if self.filesWidget.isVisible():
            self.filesWidget.hide()

        self.config_watch_timer.stop()


if __name__ == '__main__':
    a = QtWidgets.QApplication([])
    a.w = MayaBrowserWidget()
    a.w.show()
    # a.w.filesButton.clicked.emit()
    # a.w.projectsButton.clicked.emit()
    # a.w.hide()
    # a.w.show()
    a.exec_()
