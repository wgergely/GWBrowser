# -*- coding: utf-8 -*-
"""Widgets required to run Bookmarks in standalone-mode.

"""
import functools
import importlib
from PySide2 import QtWidgets, QtGui, QtCore

from . import common
from . import main
from . import settings
from . import images
from . import shortcuts


QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseOpenGLES, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)


_instance = None


@QtCore.Slot()
def show():
    """Shows the main window.

    """
    global _instance
    if not _instance:
        _instance = StandaloneMainWidget()

    state = settings.local_settings.value(
        settings.UIStateSection,
        settings.WindowStateKey,
    )
    state = QtCore.Qt.WindowNoState if state is None else QtCore.Qt.WindowState(state)

    _instance.activateWindow()
    _instance.restore_window()
    if state == QtCore.Qt.WindowNoState:
        _instance.showNormal()
    elif state & QtCore.Qt.WindowMaximized:
        _instance.showMaximized()
    elif state & QtCore.Qt.WindowFullScreen:
        _instance.showFullScreen()
    else:
        _instance.showNormal()


def instance():
    global _instance
    return _instance


class StandaloneMainWidget(main.MainWidget):
    """Modified ``MainWidget``adapted to run as a standalone
    application, with or without window borders.

    When the window mode is 'frameless' the ``HeaderWidget`` is used to move the
    window around.

    """

    def __init__(self, parent=None):
        """Init method.

        Adding the `HeaderWidget` here - this is the widget responsible for
        moving the widget around and providing the close and hide buttons.

        Also, the properties necessary to resize the frameless window are also
        defines here. These properties work in conjunction with the mouse events

        """
        global _instance
        if _instance is not None:
            raise RuntimeError(
                u'{} cannot be initialised more than once.'.format(self.__class__.__name__))
        _instance = self

        super(StandaloneMainWidget, self).__init__(parent=None)

        self.tray = None
        self._frameless = None
        self._ontop = None

        common.set_custom_stylesheet(self)

        self.resize_initial_pos = QtCore.QPoint(-1, -1)
        self.resize_initial_rect = None
        self.resize_area = None
        self.resize_overlay = None
        self.resize_distance = QtWidgets.QApplication.instance().startDragDistance() * 2
        self.resize_override_icons = {
            1: QtCore.Qt.SizeFDiagCursor,
            2: QtCore.Qt.SizeBDiagCursor,
            3: QtCore.Qt.SizeBDiagCursor,
            4: QtCore.Qt.SizeFDiagCursor,
            5: QtCore.Qt.SizeVerCursor,
            6: QtCore.Qt.SizeHorCursor,
            7: QtCore.Qt.SizeVerCursor,
            8: QtCore.Qt.SizeHorCursor,
        }

        self.installEventFilter(self)
        self.setMouseTracking(True)

        self.initialized.connect(self.connect_extra_signals)
        self.adjustSize()

        self.init_window_flags()
        self.init_tray()

    def init_window_flags(self):
        self._frameless = settings.local_settings.value(
            settings.UIStateSection,
            settings.WindowFramelessKey,
        )
        if self._frameless is True:
            self.setWindowFlags(
                self.windowFlags() | QtCore.Qt.FramelessWindowHint)

            self.setAttribute(QtCore.Qt.WA_NoSystemBackground, on=True)
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground, on=True)

        self._ontop = settings.local_settings.value(
            settings.UIStateSection,
            settings.WindowAlwaysOnTopKey
        )
        if self._ontop is True:
            self.setWindowFlags(
                self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

    def init_shortcuts(self):
        super(StandaloneMainWidget, self).init_shortcuts()
        connect = functools.partial(shortcuts.connect, shortcuts.MainWidgetShortcuts)

        connect(shortcuts.Quit, self.shutdown)
        connect(shortcuts.Minimize, self.toggle_minimized)
        connect(shortcuts.Maximize, self.toggle_maximized)
        connect(shortcuts.FullScreen, self.toggle_fullscreen)

    def init_tray(self):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'icon_bw', None, common.ROW_HEIGHT() * 7.0)
        icon = QtGui.QIcon(pixmap)

        self.tray = QtWidgets.QSystemTrayIcon(parent=self)
        self.tray.setIcon(icon)
        self.tray.setContextMenu(main.TrayMenu(parent=self))
        self.tray.setToolTip(common.PRODUCT)

        self.tray.activated.connect(self.trayActivated)

        self.tray.show()

    @QtCore.Slot()
    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    @QtCore.Slot()
    def toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    @QtCore.Slot()
    def toggle_minimized(self):
        if self.isMinimized():
            self.showNormal()
        else:
            self.showMinimized()

    @common.error
    @common.debug
    @QtCore.Slot()
    def save_window(self, *args, **kwargs):
        """Saves window's position to the local settings."""
        settings.local_settings.setValue(
            settings.UIStateSection,
            settings.WindowGeometryKey,
            self.saveGeometry()
        )
        settings.local_settings.setValue(
            settings.UIStateSection,
            settings.WindowStateKey,
            int(self.windowState())
        )

    @common.error
    @common.debug
    def restore_window(self, *args, **kwargs):
        geometry = settings.local_settings.value(
            settings.UIStateSection,
            settings.WindowGeometryKey,
        )
        if geometry is not None:
            self.restoreGeometry(geometry)

    def _get_offset_rect(self, offset):
        """Returns an expanded/contracted edge rectangle based on the widget's
        geomtery. Used to get the valid area for resize-operations."""
        rect = self.rect()
        center = rect.center()
        rect.setHeight(rect.height() + offset)
        rect.setWidth(rect.width() + offset)
        rect.moveCenter(center)
        return rect

    def accept_resize_event(self, event):
        """Returns `True` if the event can be a window resize event."""
        if self._get_offset_rect(self.resize_distance * -1).contains(event.pos()):
            return False
        if not self._get_offset_rect(self.resize_distance).contains(event.pos()):
            return False
        return True

    def set_resize_icon(self, event, clamp=True):
        """Sets an override icon to indicate the draggable area."""
        app = QtWidgets.QApplication.instance()
        k = self.get_resize_hotspot(event, clamp=clamp)
        if k:
            self.grabMouse()
            icon = self.resize_override_icons[k]
            if app.overrideCursor():
                app.changeOverrideCursor(QtGui.QCursor(icon))
                return k
            app.restoreOverrideCursor()
            app.setOverrideCursor(QtGui.QCursor(icon))
            return k
        self.releaseMouse()
        app.restoreOverrideCursor()
        return k

    def get_resize_hotspot(self, event, clamp=True):
        """Returns the resizable area from the event's current position.
        If clamp is True we will only check in near the areas near the edges.

        """
        if clamp:
            if not self.accept_resize_event(event):
                return None

        # First we have to define the 8 areas showing an indicator icon when
        # hovered. Edges:
        rect = self.rect()
        p = event.pos()
        edge_hotspots = {
            5: QtCore.QPoint(p.x(), rect.top()),
            6: QtCore.QPoint(rect.right(), p.y()),
            7: QtCore.QPoint(p.x(), rect.bottom()),
            8: QtCore.QPoint(rect.left(), p.y()),
        }

        # Corners:
        topleft_corner = QtCore.QRect(0, 0,
                                      self.resize_distance, self.resize_distance)
        topright_corner = QtCore.QRect(topleft_corner)
        topright_corner.moveRight(rect.width())
        bottomleft_corner = QtCore.QRect(topleft_corner)
        bottomleft_corner.moveTop(rect.height() - self.resize_distance)
        bottomright_corner = QtCore.QRect(topleft_corner)
        bottomright_corner.moveRight(rect.width())
        bottomright_corner.moveTop(rect.height() - self.resize_distance)

        corner_hotspots = {
            1: topleft_corner,
            2: topright_corner,
            3: bottomleft_corner,
            4: bottomright_corner,
        }

        # We check if the cursor is currently inside one of the corners or edges
        if any([f.contains(p) for f in corner_hotspots.itervalues()]):
            return max(corner_hotspots, key=lambda k: corner_hotspots[k].contains(p))
        return min(edge_hotspots, key=lambda k: (p - edge_hotspots[k]).manhattanLength())

    @QtCore.Slot()
    def connect_extra_signals(self):
        """Modifies layout for display in standalone-mode."""
        self.headerwidget.widgetMoved.connect(self.save_window)
        self.headerwidget.findChild(
            main.MinimizeButton).clicked.connect(self.showMinimized)
        self.headerwidget.findChild(main.CloseButton).clicked.connect(self.close)

        self.fileswidget.activated.connect(common.execute)
        self.favouriteswidget.activated.connect(common.execute)
        self.terminated.connect(QtWidgets.QApplication.instance().quit)

    def trayActivated(self, reason):
        """Slot called by the QSystemTrayIcon when clicked."""
        if reason == QtWidgets.QSystemTrayIcon.Unknown:
            self.show()
            self.activateWindow()
            self.raise_()
        if reason == QtWidgets.QSystemTrayIcon.Context:
            return
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()
            self.raise_()
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            return
        if reason == QtWidgets.QSystemTrayIcon.MiddleClick:
            return

    def hideEvent(self, event):
        """Custom hide event."""
        self.save_window()
        super(StandaloneMainWidget, self).hideEvent(event)

    def closeEvent(self, event):
        """Custom close event will minimize the widget to the tray."""
        event.ignore()
        self.hide()
        self.tray.showMessage(
            u'Bookmarks',
            u'Bookmarks will continue running in the background, you can use this icon to restore it\'s visibility.',
            QtWidgets.QSystemTrayIcon.Information,
            3000
        )
        self.save_window()

    def mousePressEvent(self, event):
        """The mouse press event responsible for setting the properties needed
        by the resize methods.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if not self.window().windowFlags() & QtCore.Qt.FramelessWindowHint:
            event.ignore()
            return

        if self.accept_resize_event(event):
            self.resize_area = self.set_resize_icon(event, clamp=False)
            self.resize_initial_pos = event.pos()
            self.resize_initial_rect = self.rect()
            event.accept()
            return

        self.resize_initial_pos = QtCore.QPoint(-1, -1)
        self.resize_initial_rect = None
        self.resize_area = None
        event.ignore()

    def mouseMoveEvent(self, event):
        """Custom mouse move event - responsible for resizing the frameless
        widget's geometry.
        It identifies the dragable edge area, sets the cursor override.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if not self.window().windowFlags() & QtCore.Qt.FramelessWindowHint:
            return

        if self.resize_initial_pos == QtCore.QPoint(-1, -1):
            self.set_resize_icon(event, clamp=True)
            return

        if self.resize_area is None:
            return

        o = event.pos() - self.resize_initial_pos
        geo = self.geometry()

        g_topleft = self.mapToGlobal(
            self.resize_initial_rect.topLeft())
        g_bottomright = self.mapToGlobal(
            self.resize_initial_rect.bottomRight())

        if self.resize_area in (1, 2, 5):
            geo.setTop(g_topleft.y() + o.y())
        if self.resize_area in (3, 4, 7):
            geo.setBottom(g_bottomright.y() + o.y())
        if self.resize_area in (1, 3, 8):
            geo.setLeft(g_topleft.x() + o.x())
        if self.resize_area in (2, 4, 6):
            geo.setRight(g_bottomright.x() + o.x())

        original_geo = self.geometry()
        self.move(geo.topLeft())
        self.setGeometry(geo)
        if self.geometry().width() > geo.width():
            self.setGeometry(original_geo)

    def mouseReleaseEvent(self, event):
        """Restores the mouse resize properties."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if not self.window().windowFlags() & QtCore.Qt.FramelessWindowHint:
            event.ignore()
            return

        if self.resize_initial_pos != QtCore.QPoint(-1, -1):
            self.save_window()
            if hasattr(self.stackedwidget.currentWidget(), 'reset'):
                self.stackedwidget.currentWidget().reset()

        self.resize_initial_pos = QtCore.QPoint(-1, -1)
        self.resize_initial_rect = None
        self.resize_area = None

        app = QtWidgets.QApplication.instance()
        app.restoreOverrideCursor()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.WindowStateChange:
            self.save_window()


class StandaloneApp(QtWidgets.QApplication):
    """This is the app used to run the browser as a standalone widget."""
    MODEL_ID = u'{}App'.format(common.PRODUCT)

    def __init__(self, args):
        super(StandaloneApp, self).__init__(args)
        mod = importlib.import_module(__name__.split('.')[0])
        self.setApplicationVersion(mod.__version__)
        self.setApplicationName(common.PRODUCT)
        self.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, bool=True)
        self.set_model_id()

        common.font_db = common.FontDatabase()

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'icon', None, common.ROW_HEIGHT() * 7.0)
        icon = QtGui.QIcon(pixmap)
        self.setWindowIcon(icon)

    def set_model_id(self):
        """Setting this is needed to add custom window icons on windows.
        https://github.com/cztomczak/cefpython/issues/395

        """
        if QtCore.QSysInfo().productType() in (u'windows', u'winrt'):
            import ctypes
            from ctypes.wintypes import HRESULT
            PCWSTR = ctypes.c_wchar_p
            AppUserModelID = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
            AppUserModelID.argtypes = [PCWSTR]
            AppUserModelID.restype = HRESULT
            # An identifier that is globally unique for all apps running on Windows
            hresult = AppUserModelID(self.MODEL_ID)
            assert hresult == 0, "SetCurrentProcessExplicitAppUserModelID failed"
