# -*- coding: utf-8 -*-
"""Widgets required to run Bookmarks in standalone-mode.

"""
from PySide2 import QtWidgets, QtGui, QtCore

import bookmarks.common as common
import bookmarks.mainwidget as mainwidget
import bookmarks.settings as settings
import bookmarks.images as images


QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseOpenGLES, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)


_instance = None


def instance():
    global _instance
    return _instance


class StandaloneMainWidget(mainwidget.MainWidget):
    """Modified ``MainWidget``adapted to run it as a standalone
    application, with or without window borders.

    ``HeaderWidget`` is used to move the window around.

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
                '{} cannot be initialised more than once.'.format(self.__class__.__name__))
        _instance = self

        super(StandaloneMainWidget, self).__init__(parent=None)

        k = u'preferences/frameless_window'
        self._frameless = settings.local_settings.value(k)
        if self._frameless is True:
            self.setWindowFlags(
                QtCore.Qt.Window |
                QtCore.Qt.FramelessWindowHint)
            self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

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

        self.tray = QtWidgets.QSystemTrayIcon(parent=self)
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'icon_bw', None, common.ROW_HEIGHT() * 7.0)
        icon = QtGui.QIcon(pixmap)
        self.tray.setIcon(icon)
        self.tray.setContextMenu(mainwidget.TrayMenu(parent=self))
        self.tray.setToolTip(common.PRODUCT)
        self.tray.show()

        self.tray.activated.connect(self.trayActivated)

        self.installEventFilter(self)
        self.setMouseTracking(True)

        self.initialized.connect(self.connect_extra_signals)
        self.initialized.connect(self.showNormal)
        self.initialized.connect(self.activateWindow)

        def say_hello():
            import bookmarks.common_ui as common_ui
            if self.stackedwidget.widget(0).model().sourceModel().rowCount() == 0:
                common_ui.MessageBox(
                    u'Bookmarks is not set up (yet!).',
                    u'To add a server, create new jobs and bookmark folders, right-click on the main window and select "Manage Bookmarks".',
                    parent=self.stackedwidget.widget(0)
                ).open()

        self.initialized.connect(say_hello)
        self.shutdown.connect(self.hide)

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+Q'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.ApplicationShortcut)
        shortcut.activated.connect(
            self.shutdown, type=QtCore.Qt.QueuedConnection)

        self.adjustSize()

    @QtCore.Slot()
    def save_widget_settings(self):
        """Saves the position and size of thew widget to the local settings."""
        cls = self.__class__.__name__
        settings.local_settings.setValue(
            u'widget/{}/geometry'.format(cls), self.frameGeometry())

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
        self.headerwidget.widgetMoved.connect(self.save_widget_settings)
        self.headerwidget.findChild(
            mainwidget.MinimizeButton).clicked.connect(self.showMinimized)
        self.headerwidget.findChild(mainwidget.CloseButton).clicked.connect(self.close)

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
        self.save_widget_settings()
        super(StandaloneMainWidget, self).hideEvent(event)

    def showEvent(self, event):
        """Custom show event. When showing the widget we will use the saved
        settings to set the widget's size and position.

        """
        super(StandaloneMainWidget, self).showEvent(event)

        cls = self.__class__.__name__
        geo = settings.local_settings.value(
            u'widget/{}/geometry'.format(cls))

        if geo and not self.window().windowFlags() & QtCore.Qt.FramelessWindowHint:
            fw = self.frameGeometry().width() - self.geometry().width()
            fh = self.frameGeometry().height() - self.geometry().height()
            # geo.moveTop(geo.top() - fh)
            geo.setHeight(geo.height() - (fh * 1))
            self.window().setGeometry(geo)
            common.move_widget_to_available_geo(self)

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
        self.save_widget_settings()

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
            self.save_widget_settings()
            if hasattr(self.stackedwidget.currentWidget(), 'reset'):
                self.stackedwidget.currentWidget().reset()

        self.resize_initial_pos = QtCore.QPoint(-1, -1)
        self.resize_initial_rect = None
        self.resize_area = None

        app = QtWidgets.QApplication.instance()
        app.restoreOverrideCursor()


class StandaloneApp(QtWidgets.QApplication):
    """This is the app used to run the browser as a standalone widget."""
    MODEL_ID = u'{}App'.format(common.PRODUCT)

    def __init__(self, args):
        super(StandaloneApp, self).__init__(args)
        import bookmarks

        self.setApplicationVersion(bookmarks.__version__)
        self.setApplicationName(common.PRODUCT)
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
