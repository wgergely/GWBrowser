'Edit locations'  # -*- coding: utf-8 -*-
"""``MayaBrowserWidget`` is the plug-in's main widget.
When launched from within Maya it inherints from MayaQWidgetDockableMixin baseclass,
otherwise MayaQWidgetDockableMixin is replaced with a ``common.LocalContext``, a dummy class.

Example:

.. code-block:: python
    :linenos:

    from mayabrowser.toolbar import MayaBrowserWidget
    widget = MayaBrowserWidget()
    widget.show()

The asset and the file lists are collected by the ``collector.AssetCollector``
and ```collector.FilesCollector`` classes. The gathered files then are displayed
in the ``listwidgets.AssetsListWidget`` and ``listwidgets.FilesListWidget`` items.

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

from mayabrowser.listlocation import LocationWidget
from mayabrowser.listasset import AssetWidget
from mayabrowser.listmaya import MayaFilesWidget
from mayabrowser.configparsers import local_config
from mayabrowser.configparsers import AssetConfig
from mayabrowser.delegate import ThumbnailEditor
from mayabrowser.actions import Actions



# @staticmethod
# def reveal_server():
#     """Shows the current server folder in the file explorer."""
#     file_info = QtCore.QFileInfo(
#         '{}'.format(local_config.server)
#     )
#     path = file_info.filePath()
#     url = QtCore.QUrl.fromLocalFile(path)
#     QtGui.QDesktopServices.openUrl(url)
#
# @staticmethod
# def reveal_job():
#     """Reveals the current job folder in the file explorer."""
#     file_info = QtCore.QFileInfo(
#         '{}/{}'.format(local_config.server, local_config.job)
#     )
#     path = file_info.filePath()
#     url = QtCore.QUrl.fromLocalFile(path)
#     QtGui.QDesktopServices.openUrl(url)
#
# @staticmethod
# def reveal_assets():
#     """Reveals the current assets folder in the file explorer."""
#     file_info = QtCore.QFileInfo(
#         '{}/{}/{}'.format(local_config.server,
#                           local_config.job, local_config.root)
#     )
#     path = file_info.filePath()
#     url = QtCore.QUrl.fromLocalFile(path)
#     QtGui.QDesktopServices.openUrl(url)



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


class AssetThumbnail(QtWidgets.QLabel):
    """Clickable QLabel."""

    clicked = QtCore.Signal()
    doubleClicked = QtCore.Signal()

    def mousePressEvent(self, event):
        """Custom mouse press event."""
        self.clicked.emit()

    def mouseDoubleClickEvent(self, event):
        """Custom mouse double-clicke event."""
        self.doubleClicked.emit()


class FaderWidget(QtWidgets.QWidget):
    """Overlaywidget responsible for list cross-fade effect."""

    def __init__(self, old_widget, new_widget):
        super(FaderWidget, self).__init__(parent=new_widget)

        self.old_pixmap = QtGui.QPixmap(new_widget.size())
        self.old_pixmap.fill(QtGui.QColor(50, 50, 50))
        # old_widget.render(self.old_pixmap)
        self.pixmap_opacity = 1.0

        self.timeline = QtCore.QTimeLine()
        self.timeline.valueChanged.connect(self.animate)
        self.timeline.finished.connect(self.close)
        self.timeline.setDuration(200)
        self.timeline.start()

        self.resize(new_widget.size())
        self.show()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setOpacity(self.pixmap_opacity)
        painter.drawPixmap(0, 0, self.old_pixmap)
        painter.end()

    def animate(self, value):
        self.pixmap_opacity = 1.0 - value
        self.repaint()

class OverlayWidget(QtWidgets.QWidget):
    """Overlaywidget responsible for list cross-fade effect."""

    def __init__(self, new_widget):
        super(OverlayWidget, self).__init__(parent=new_widget)

        self.old_pixmap = QtGui.QPixmap(new_widget.size())
        self.old_pixmap.fill(QtGui.QColor(50, 50, 50))
        # old_widget.render(self.old_pixmap)
        self.pixmap_opacity = 0.0

        self.timeline = QtCore.QTimeLine()
        self.timeline.valueChanged.connect(self.animate)
        # self.timeline.finished.connect(self.close)
        self.timeline.setDuration(300)
        self.timeline.start()

        self.resize(new_widget.size())
        self.show()

    def animate(self, value):
        self.pixmap_opacity = (0.0 + value) * 0.8
        self.repaint()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setOpacity(self.pixmap_opacity)
        painter.drawPixmap(0, 0, self.old_pixmap)
        painter.end()


class MayaBrowserWidget(MayaQWidgetDockableMixin, QtWidgets.QWidget):  # pylint: disable=E1139
    """Singleton MayaQWidgetDockable widget containing the ``assetWidgetButton``
    and the ``filesWidgetButton`` buttons.

    Attributes:
        instances (dict):               Class instances.
        assetsWidget (QListWidget):   List of the collected Maya assets.
        filesWidget (QListWidget):      List of files found associated with the asset.

        configChanged (QtCore.QSignal): Custom signal emitted when the configuration file changes.

    """

    __metaclass__ = Singleton
    # """Singleton metaclass."""

    instances = {}

    # Signals
    configChanged = QtCore.Signal()
    projectChanged = QtCore.Signal()
    assetChanged = QtCore.Signal()
    fileChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super(MayaBrowserWidget, self).__init__(parent=parent)
        self.instances[self.objectName()] = self
        self._workspacecontrol = None
        self.maya_callbacks = []  # Maya api callbacks
        self.maya_actions = []  # Maya ui

        # Applying the initial config settings.
        local_config.read_ini()
        self._kwargs = {
            'server': None,
            'job': None,
            'root': None
        }
        if local_config.server and local_config.job and local_config.root:
            self._kwargs = {
                'server': local_config.server,
                'job': local_config.job,
                'root': local_config.root
            }

        self._contextMenu = None
        self.fader_widget = None

        # Create layout
        self._createUI()

        pixmap = self.get_thumbnail_pixmap(common.CUSTOM_THUMBNAIL)

        self.locationsWidget = LocationWidget()
        self.locationsWidget.setWindowIcon(QtGui.QIcon(pixmap))
        self.assetsWidget = AssetWidget()
        self.assetsWidget.setWindowIcon(QtGui.QIcon(pixmap))
        self.filesWidget = MayaFilesWidget()
        self.filesWidget.setWindowIcon(QtGui.QIcon(pixmap))

        self.stacked_widget.addWidget(self.locationsWidget)
        self.stacked_widget.addWidget(self.assetsWidget)
        self.stacked_widget.addWidget(self.filesWidget)

        # Setting initial state
        self.stacked_widget.setCurrentIndex(local_config.current_widget)
        self.mode_pick.setCurrentIndex(local_config.current_widget)

        self.config_string = ''
        self.config_watch_timer = QtCore.QTimer()
        self.config_watch_timer.setInterval(2000)
        self.config_watch_timer.start()

        self._connectSignals()

        self.sync_config()
        self.sync_active_maya_asset()


    @property
    def workspacecontrol(self):
        """The workspacecontrol associated with this widget."""
        self._workspacecontrol = self.get_workspace_control()
        return self._workspacecontrol

    @staticmethod
    def get_thumbnail_pixmap(path, opacity=1, size=(common.ROW_BUTTONS_HEIGHT)):
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

    def setThumbnail(self, path, opacity=1, size=common.ROW_BUTTONS_HEIGHT):
        """Sets the given path as the thumbnail of the asset."""
        pixmap = self.get_thumbnail_pixmap(path, opacity=opacity, size=size)
        self.asset_thumbnail.setPixmap(pixmap)

    def addCustomFonts(self):
        """Adds our custom fonts to the application.

        Returns:
            type: Description of returned object.

        """

        d = QtCore.QDir(
            '{}/rsc/fonts'.format(
                QtCore.QFileInfo(__file__).dir().path()
            )
        )
        d.setNameFilters(['*.ttf', ])

        font_families = []
        for f in d.entryInfoList(
            QtCore.QDir.Files |
            QtCore.QDir.NoDotAndDotDot
        ):
            idx = QtGui.QFontDatabase().addApplicationFont(f.filePath())
            font_families.append(
                QtGui.QFontDatabase().applicationFontFamilies(idx)[0])

    def _createUI(self):
        """Creates the layout.

        +-----------------+
        |   row_buttons   |     A row of buttons to toggle filters and views.
        +-----------------+
        |                 |
        |                 |
        | stacked_widget  |     This a the widget containing the lists widgets of `assets`, `assets` and `files`.
        |                 |
        |                 |
        +-----------------+
        |    row_footer   |     Infobar
        +-----------------+

        """
        self.addCustomFonts()

        # Main layout
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.setFixedWidth(common.WIDTH)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred
        )
        pixmap = self.get_thumbnail_pixmap(common.CUSTOM_THUMBNAIL)
        self.setWindowIcon(QtGui.QIcon(pixmap))

        self.row_buttons = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(self.row_buttons)
        self.row_buttons.layout().setContentsMargins(0, 0, 0, 0)
        self.row_buttons.layout().setSpacing(0)
        self.row_buttons.setFixedHeight(common.ROW_BUTTONS_HEIGHT)

        self.stacked_widget = QtWidgets.QStackedWidget()
        self.stacked_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.stacked_widget.layout().setSpacing(0)
        self.stacked_widget.setFixedHeight(common.STACKED_WIDGET_HEIGHT)
        self.stacked_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )

        self.row_footer = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(self.row_footer)
        self.row_footer.layout().setContentsMargins(0, 0, 0, 0)
        self.row_footer.layout().setSpacing(0)
        self.row_footer.setFixedHeight(common.ROW_FOOTER_HEIGHT)
        self.row_footer.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )

        self.layout().addWidget(self.row_buttons)
        self.layout().addWidget(self.stacked_widget)
        self.layout().addWidget(self.row_footer)

        self.asset_thumbnail = AssetThumbnail(parent=self)
        self.asset_thumbnail.setAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.asset_thumbnail.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
        self.asset_thumbnail.setFixedWidth(common.ROW_BUTTONS_HEIGHT)
        self.asset_thumbnail.setStyleSheet(
            """
            QLabel {\
                background-color: rgb(60, 60, 60);\
                margin: 0px;\
                padding: 0px;\
            }\
            """
        )
        self.setThumbnail(common.CUSTOM_THUMBNAIL, opacity=1)
        self.setStyleSheet(
            """
            QWidget {\
                background-color: rgb(80, 80, 80);\
            }
            """
        )

        self.mode_pick = DropdownWidget()
        self.mode_pick.addItem('Projects')
        self.mode_pick.addItem('Assets')
        self.mode_pick.addItem('Files')

        self.row_buttons.layout().addWidget(self.mode_pick, 1)
        self.row_buttons.layout().addWidget(self.asset_thumbnail, 0)

    @staticmethod
    def buttonStyle():
        """Returns a style-string defining our custom button."""
        return (
            """\
            QPushButton {\
                text-align: left;\
                border-left: 1px solid rgba(0, 0, 0, 50);\
                padding-left: 10px;\
                padding-right: 10px;\
                border-style: solid;\
                color: rgb(230, 230, 230);\
                background-color: rgb(110, 110, 110);\
                font-family: "Roboto Black";\
                font-size: 8pt;\
            }
            QPushButton:hover {\
                border-left: 3px solid rgb(87, 163, 202);\
                color: rgb(230, 230, 230);\
                background-color: rgb(100, 100, 100);\
            }\
            QPushButton:pressed {\
                border-left: 4px solid rgb(87, 163, 202);\
                padding-left: 7px;\
                color: rgb(255, 255, 255);\
                background-color: rgb(130, 130, 130);\
            }\
            """
        )

    def contextMenuEvent(self, event):
        """Custom context menu event."""
        pass

    def sync_config(self, *args, **kwargs):
        """Keeps an eye out for configuration file changes and triggers a refresh
        when change is detected.

        """
        if not QtCore.QFileInfo(local_config.getConfigPath(None)).exists():
            self.setWindowTitle('No asset added yet.')
            return

        local_config.read_ini()

        if (
            (self._kwargs['server'] == local_config.server) and
            (self._kwargs['job'] == local_config.job) and
            (self._kwargs['root'] == local_config.root)
        ):
            return

        self._kwargs = {
            'server': local_config.server,
            'job': local_config.job,
            'root': local_config.root
        }

        self.configChanged.emit()
        self.assetChanged.emit()

        self.assetsWidget.refresh()
        self.setWindowTitle(
            '{}:  {}'.format(
            local_config.job, local_config.root).upper()
        )

    def sync_active_maya_asset(self, setActive=True):
        """Selects the active maya asset in the list and sets it as the ``active_item``."""
        if not cmds.workspace(q=True, fn=True):
            return

        file_info = QtCore.QFileInfo(cmds.workspace(q=True, fn=True))
        item = self.assetsWidget.findItems(
            file_info.baseName().upper(),
            QtCore.Qt.MatchContains
        )
        if not item:
            return

        index = self.assetsWidget.indexFromItem(item[0])
        self.assetsWidget.setCurrentItem(item[0])
        self.assetsWidget.scrollTo(index)

        if setActive:
            self.assetsWidget.active_item = item[0]

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
        font = self.files_button.font()
        metrics = QtGui.QFontMetrics(font)
        filename = metrics.elidedText(
            file_info.baseName(),
            QtCore.Qt.ElideMiddle,
            self.files_button.width() - common.MARGIN * 3
        )
        self.files_button.setText(filename)

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
            'height':   common.ROW_HEIGHT * 0.66,
            'minHeight': common.ROW_HEIGHT * 0.66,
            'maxHeight': common.ROW_HEIGHT * 0.66,
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
        self.mode_pick.currentIndexChanged.connect(self.view_changed)
        self.stacked_widget.currentChanged.connect(self.mode_pick.setCurrentIndex)

        self.config_watch_timer.timeout.connect(self.sync_config)

        self.locationsWidget.locationChanged.connect(self.location_changed)
        # self.assetsWidget.assetChanged.connect(self.assetChanged)
        # self.filesWidget.sceneChanged.connect(self.sync_active_maya_scene)

    def location_changed(self, server, job, root):
        self.sync_config()


    def view_changed(self, index):
        """Triggered when a different view is selected."""
        self.activate_widget(self.stacked_widget.widget(index))
        local_config.current_widget = index

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
        self.filesWidget.deleteLater()
        self.assetsWidget.deleteLater()

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
            self.activate_widget(self.filesWidget)

        def _asset_func():
            self.activate_widget(self.assetsWidget)

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
        action.setStatusTip('Show the asset\'s files')

        action.triggered.connect(_files_func)
        menu.insertAction(before, action)
        self.maya_actions.append(action)
        before = action

        action = QtWidgets.QAction('Assets...', menu)
        action.setIcon(icon)
        action.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        action.setShortcut('Ctrl+Shift+P')
        action.setStatusTip('Show the assets')
        action.triggered.connect(_asset_func)
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

    def _assetChanged(self):
        """Signal emitted when the asset has changed."""
        file_info = self.assetsWidget.collector.active_item
        if file_info:
            cmds.workspace(file_info.filePath(), openWorkspace=True)
            path = AssetConfig.getThumbnailPath(file_info.filePath())
            thumb_info = QtCore.QFileInfo(path)

            # Setting the asset's thumbnail as the label thumbnail
            if thumb_info.exists():
                self.setThumbnail(thumb_info.filePath())
            else:
                self.setThumbnail(common.CUSTOM_THUMBNAIL)
        else:
            self.setThumbnail(common.CUSTOM_THUMBNAIL)

        self.filesWidget.update_path(file_info)
        self.filesWidget.refresh()

    def activate_widget(self, widget):
        """Method to change between views."""
        self.fader_widget = FaderWidget(
            self.stacked_widget.currentWidget(), widget)
        self.stacked_widget.setCurrentWidget(widget)

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

        self.setWindowTitle(
            '{}:  {}'.format(
            local_config.job, local_config.root).upper()
        )

        self.config_watch_timer.start()
        self.sync_active_maya_asset()

        if not self.get_workspace_control():
            return

        if not self.is_docked():
            return

        if not self.get_parent_window():
            return

        pixmap = self.get_thumbnail_pixmap(
            common.CUSTOM_THUMBNAIL, opacity=1, size=(common.ROW_HEIGHT * 0.66)
        )
        self.setWindowIcon(QtGui.QIcon(pixmap))

    def keyPressEvent(self, event):
        """Custom key actions."""
        pass

    def hideEvent(self, event):
        """Custom hide event."""
        self.config_watch_timer.stop()


class DropdownWidgetDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super(DropdownWidgetDelegate, self).__init__(parent=parent)

    def sizeHint(self, option, index):
        return QtCore.QSize(common.WIDTH, common.ROW_HEIGHT)

    def paint(self, painter, option, index):
        """The main paint method."""
        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=True
        )
        selected = option.state & QtWidgets.QStyle.State_Selected
        args = (painter, option, index, selected)

        self.paint_background(*args)
        self.paint_thumbnail(*args)
        self.paint_selection_indicator(*args)
        self.paint_name(*args)

    def paint_selection_indicator(self, *args):
        """Paints the blue leading rectangle to indicate the current selection."""
        painter, option, _, selected = args

        if not selected:
            return

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(common.SELECTION))
        rect = QtCore.QRect(option.rect)
        rect.setWidth(4)
        painter.drawRect(rect)

    def paint_name(self, *args):
        painter, option, index, _ = args

        painter.save()

        font = QtGui.QFont('Roboto Black')
        font.setPointSize(9.0)
        font.setBold(True)
        painter.setFont(font)

        rect = QtCore.QRect(option.rect)
        rect.moveLeft(rect.left() + 4 + rect.height() + common.MARGIN)
        rect.setRight(rect.width() - (common.MARGIN * 2))
        painter.setPen(QtGui.QPen(common.TEXT))
        painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            index.data(QtCore.Qt.DisplayRole).upper()
        )

        painter.restore()

    def paint_background(self, *args):
        """Paints the background."""
        painter, option, _, selected = args

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        if selected:
            color = common.BACKGROUND_SELECTED
        else:
            color = common.BACKGROUND
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(option.rect)

    def paint_thumbnail(self, *args):
        """Paints the thumbnail of the item."""
        painter, option, index, selected = args

        painter.save()

        if selected:
            color = common.THUMBNAIL_BACKGROUND_SELECTED
        else:
            color = common.THUMBNAIL_BACKGROUND

        rect = QtCore.QRect(option.rect)
        # Making the aspect ratio of the image 16/9
        rect.setWidth(rect.height())
        rect.moveLeft(rect.left() + 4)  # Accounting for the leading indicator

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(rect)

        # Shadow next to the thumbnail
        shd_rect = QtCore.QRect(option.rect)
        shd_rect.setLeft(rect.left() + rect.width())

        gradient = QtGui.QLinearGradient(
            shd_rect.topLeft(), shd_rect.topRight())
        gradient.setColorAt(0, QtGui.QColor(0, 0, 0, 50))
        gradient.setColorAt(0.2, QtGui.QColor(68, 68, 68, 0))
        painter.setBrush(QtGui.QBrush(gradient))
        painter.drawRect(shd_rect)

        gradient = QtGui.QLinearGradient(
            shd_rect.topLeft(), shd_rect.topRight())
        gradient.setColorAt(0, QtGui.QColor(0, 0, 0, 50))
        gradient.setColorAt(0.02, QtGui.QColor(68, 68, 68, 0))
        painter.setBrush(QtGui.QBrush(gradient))
        painter.drawRect(shd_rect)

        if index.row() == 0:
            path = '{}/rsc/bookmark.png'.format(
                QtCore.QFileInfo(__file__).dir().path()
            )
        if index.row() == 1:
            path = '{}/rsc/package.png'.format(
                QtCore.QFileInfo(__file__).dir().path()
            )
        if index.row() == 2:
            path = '{}/rsc/file.png'.format(
                QtCore.QFileInfo(__file__).dir().path()
            )

        # Thumbnail image
        if path in common.IMAGE_CACHE:
            image = common.IMAGE_CACHE[path]
        else:
            image = QtGui.QImage()
            image.load(path)
            image = ThumbnailEditor.smooth_copy(
                image,
                option.rect.height()
            )
            common.IMAGE_CACHE[path] = image

        # Factoring aspect ratio in
        longer = float(max(image.rect().width(), image.rect().height()))
        factor = float(rect.width() / longer)
        if image.rect().width() < image.rect().height():
            rect.setWidth(float(image.rect().width()) * factor)
        else:
            rect.setHeight(float(image.rect().height()) * factor)

        rect.moveLeft(
            rect.left() + ((option.rect.height() - rect.width()) * 0.5)
        )
        rect.moveTop(
            rect.top() + ((option.rect.height() - rect.height()) * 0.5)
        )

        painter.drawImage(
            rect,
            image,
            image.rect()
        )
        painter.restore()


class DropdownWidget(QtWidgets.QComboBox):
    """Custom dropdown widget."""

    def __init__(self, parent=None):
        super(DropdownWidget, self).__init__(parent=parent)
        self.setItemDelegate(DropdownWidgetDelegate())
        self.view().setStyleSheet(
            """\
            QWidget {\
                margin: 0;
                padding: 0;\
            }\
            """
        )
        self.view().setFixedWidth(common.WIDTH)
        self.setStyleSheet(
            """\
            QComboBox {\
                text-align: left;\
                border-left: 4px solid rgb(110, 110, 110);\
                padding-left: 10px;\
                padding-right: 10px;\
                border-style: solid;\
                color: rgb(230, 230, 230);\
                background-color: rgb(110, 110, 110);\
                font-family: "Roboto Black";\
                font-size: 8pt;\
            }\
            QComboBox:hover {\
                border-left: 4px solid rgb(87, 163, 202);\
                color: rgb(230, 230, 230);\
                background-color: rgb(130, 130, 130);\
            }\
            QComboBox::drop-down {\
                background-color: transparent;\
                width: 0px;\
                height: 0px;\
                padding:0px;\
                margin:0px;\
                border-width: 0px;\
                border-style: none;\
                border-radius: 0px;\
            }\
            """
        )
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )

        self.overlayWidget = None

    def showPopup(self):
        self.overlayWidget = OverlayWidget(self.parent().parent().stacked_widget)
        super(DropdownWidget, self).showPopup()

    def hidePopup(self):
        if self.overlayWidget:
            self.overlayWidget.close()
        super(DropdownWidget, self).hidePopup()

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = MayaBrowserWidget()
    # widget.move(50, 50)
    widget.show()
    app.exec_()
