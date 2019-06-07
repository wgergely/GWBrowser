# -*- coding: utf-8 -*-
"""The module containing all widgets needed to run GWBrowser in standalone-mode."""

import sys
import functools
from PySide2 import QtWidgets, QtGui, QtCore

from gwbrowser.settings import Active
from gwbrowser.browserwidget import BrowserWidget
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.editors import ClickableLabel
from gwbrowser.basecontextmenu import contextmenu
import gwbrowser.common as common
from gwbrowser.settings import local_settings
from gwbrowser.imagecache import ImageCache


class TrayMenu(BaseContextMenu):
    """The context-menu associated with the BrowserButton."""

    def __init__(self, parent=None):
        super(TrayMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)

        self.stays_on_top = False
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)

        self.add_show_menu()
        self.add_toolbar_menu()
        self.add_visibility_menu()

    def show_window(self):
        """Raises and shows the widget."""
        screen = self.parent().window().windowHandle().screen()
        self.parent().move(screen.geometry().center() - self.parent().rect().center())
        self.parent().showNormal()
        self.parent().activateWindow()

    @contextmenu
    def add_visibility_menu(self, menu_set):
        """Actions associated with the visibility of the widget."""

        def toggle_window_flag():
            """Sets the WindowStaysOnTopHint for the window."""
            flags = self.parent().windowFlags()
            self.hide()
            if flags & QtCore.Qt.WindowStaysOnTopHint:
                flags = flags & ~QtCore.Qt.WindowStaysOnTopHint
            else:
                flags = flags | QtCore.Qt.WindowStaysOnTopHint
            self.parent().setWindowFlags(flags)
            self.parent().showNormal()
            self.parent().activateWindow()

        menu_set['Keep on top of other windows'] = {
            'checkable': True,
            'checked': self.parent().windowFlags() & QtCore.Qt.WindowStaysOnTopHint,
            'action': toggle_window_flag
        }
        menu_set['Restore window...'] = {
            'action': self.show_window
        }
        menu_set['separator1'] = {}
        menu_set['Quit'] = {
            'action': self.parent().shutdown.emit
        }
        return menu_set

    @contextmenu
    def add_show_menu(self, menu_set):
        if not hasattr(self.parent(), 'clicked'):
            return menu_set
        menu_set[u'show'] = {
            u'icon': ImageCache.get_rsc_pixmap(u'custom', None, common.INLINE_ICON_SIZE),
            u'text': u'Open...',
            u'action': self.parent().clicked.emit
        }
        return menu_set

    @contextmenu
    def add_toolbar_menu(self, menu_set):
        active_paths = Active.paths()
        bookmark = (active_paths[u'server'],
                    active_paths[u'job'], active_paths[u'root'])
        asset = bookmark + (active_paths[u'asset'],)
        location = asset + (active_paths[u'location'],)

        if all(bookmark):
            menu_set[u'bookmark'] = {
                u'icon': ImageCache.get_rsc_pixmap('bookmark', common.TEXT, common.INLINE_ICON_SIZE),
                u'disabled': not all(bookmark),
                u'text': u'Show active bookmark in the file manager...',
                u'action': functools.partial(common.reveal, u'/'.join(bookmark))
            }
            if all(asset):
                menu_set[u'asset'] = {
                    u'icon': ImageCache.get_rsc_pixmap(u'assets', common.TEXT, common.INLINE_ICON_SIZE),
                    u'disabled': not all(asset),
                    u'text': u'Show active asset in the file manager...',
                    u'action': functools.partial(common.reveal, '/'.join(asset))
                }
                if all(location):
                    menu_set[u'location'] = {
                        u'icon': ImageCache.get_rsc_pixmap(u'location', common.TEXT, common.INLINE_ICON_SIZE),
                        u'disabled': not all(location),
                        u'text': u'Show current task folder in the file manager...',
                        u'action': functools.partial(common.reveal, '/'.join(location))
                    }

        return menu_set


class CloseButton(ClickableLabel):
    """Button used to close/hide a widget or window."""

    def __init__(self, parent=None):
        super(CloseButton, self).__init__(parent=parent)
        pixmap = ImageCache.get_rsc_pixmap(
            u'close', common.SECONDARY_BACKGROUND, common.ROW_BUTTONS_HEIGHT / 2)
        self.setFixedSize(common.INLINE_ICON_SIZE, common.INLINE_ICON_SIZE)
        self.setPixmap(pixmap)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def enterEvent(self, event):
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter = QtGui.QPainter()
        painter.begin(self)
        if hover:
            pixmap = ImageCache.get_rsc_pixmap(
                u'close', QtGui.QColor(200, 100, 50), common.ROW_BUTTONS_HEIGHT / 2)
        else:
            pixmap = ImageCache.get_rsc_pixmap(
                u'close', common.SECONDARY_BACKGROUND, common.ROW_BUTTONS_HEIGHT / 2)
        painter.drawPixmap(self.rect(), pixmap, pixmap.rect())
        painter.end()


class MinimizeButton(ClickableLabel):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(MinimizeButton, self).__init__(parent=parent)
        pixmap = ImageCache.get_rsc_pixmap(
            u'minimize', common.SECONDARY_BACKGROUND, common.INLINE_ICON_SIZE)
        self.setFixedSize(common.INLINE_ICON_SIZE, common.INLINE_ICON_SIZE)
        self.setPixmap(pixmap)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def enterEvent(self, event):
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter = QtGui.QPainter()
        painter.begin(self)
        if hover:
            pixmap = ImageCache.get_rsc_pixmap(
                u'minimize', QtGui.QColor(200, 100, 50), common.ROW_BUTTONS_HEIGHT / 2)
        else:
            pixmap = ImageCache.get_rsc_pixmap(
                u'minimize', common.SECONDARY_BACKGROUND, common.ROW_BUTTONS_HEIGHT / 2)
        painter.drawPixmap(self.rect(), pixmap, pixmap.rect())
        painter.end()


class HeaderWidget(QtWidgets.QWidget):
    """Horizontal widget for controlling the position of the widget active window."""
    widgetMoved = QtCore.Signal(QtCore.QPoint)

    def __init__(self, parent=None):
        super(HeaderWidget, self).__init__(parent=parent)
        self.label = None
        self.closebutton = None
        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_widget_pos = None

        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self._createUI()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(common.INDICATOR_WIDTH, common.INDICATOR_WIDTH,
                                         common.INDICATOR_WIDTH, common.INDICATOR_WIDTH)
        self.layout().setSpacing(common.INDICATOR_WIDTH * 2)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedHeight(common.INLINE_ICON_SIZE)

        self.layout().addSpacing(common.INDICATOR_WIDTH)
        self.layout().addStretch()
        self.layout().addWidget(MinimizeButton(parent=self))
        self.layout().addWidget(CloseButton(parent=self))
        self.layout().addSpacing(common.INDICATOR_WIDTH)

    def mousePressEvent(self, event):
        """Custom ``movePressEvent``.
        We're setting the properties needed to moving the main window.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.move_in_progress = True
        self.move_start_event_pos = event.pos()
        self.move_start_widget_pos = self.mapToGlobal(
            self.geometry().topLeft())

    def mouseMoveEvent(self, event):
        """The custom mouse move event responsbiel for moving the parent window.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.buttons() == QtCore.Qt.NoButton:
            return
        if self.move_start_widget_pos:
            margins = self.window().layout().contentsMargins()
            offset = (event.pos() - self.move_start_event_pos)
            pos = self.window().mapToGlobal(self.geometry().topLeft()) + offset
            self.parent().move(
                pos.x() - margins.left(),
                pos.y() - margins.top()
            )
            bl = self.window().rect().bottomLeft()
            bl = self.window().mapToGlobal(bl)
            self.widgetMoved.emit(bl)

    def contextMenuEvent(self, event):
        """Shows the context menu associated with the tray in the header."""
        widget = TrayMenu(parent=self.window())
        pos = self.window().mapToGlobal(event.pos())
        widget.move(pos)
        common.move_widget_to_available_geo(widget)
        widget.show()


class StandaloneBrowserWidget(BrowserWidget):
    """This window defines the main windows visible when rtunning the tool in
    standalone-mode.

    We're subclassing ``BrowserWidget`` but modifying it to add an associated
    ``QSystemTrayIcon`` responsible for quick-access, and window-handles for
    resizing.

    """

    def __init__(self, parent=None):
        """Init method.

        Adding the `HeaderWidget` here - this is the widget responsible for
        moving the widget around and providing the close and hide buttons.

        Also, the properties necessary to resize the frameless window are also
        defines here. These properties work in conjunction with the mouse events

        """
        super(StandaloneBrowserWidget, self).__init__(parent=parent)
        self.headerwidget = None
        self.resize_initial_pos = QtCore.QPoint(-1, -1)
        self.resize_initial_rect = None
        self.resize_area = None

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
        pixmap = ImageCache.get_rsc_pixmap(u'custom', None, 256)
        icon = QtGui.QIcon(pixmap)
        self.tray.setIcon(icon)
        self.tray.setContextMenu(TrayMenu(parent=self))
        self.tray.setToolTip(u'GWBrowser')
        self.tray.show()

        self.tray.activated.connect(self.trayActivated)

        self.setMouseTracking(True)
        self.installEventFilter(self)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.initialized.connect(self.tweak_ui)
        self.initialized.connect(self.showNormal)
        self.initialized.connect(self.activateWindow)

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+Q'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.ApplicationShortcut)
        shortcut.activated.connect(
            self.shutdown, type=QtCore.Qt.QueuedConnection)
        self.shutdown_timer.timeout.connect(
            lambda: self.terminate(quit_app=True), type=QtCore.Qt.QueuedConnection)

        self.adjustSize()

    def _get_offset_rect(self, offset):
        """Returns an expanded/contracted rectangle based on the widget's rectangle.
        Used to get the valid area for resize-operations."""
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
    def tweak_ui(self):
        """Modifies layout for display in standalone-mode."""

        self.headerwidget = HeaderWidget(parent=self)
        self.layout().setContentsMargins(2, 2, 2, 2)
        self.layout().insertSpacing(0, common.INDICATOR_WIDTH)
        self.layout().insertWidget(0, self.headerwidget)

        self.findChild(MinimizeButton).clicked.connect(self.showMinimized)
        self.findChild(CloseButton).clicked.connect(self.close)

        self.fileswidget.activated.connect(common.execute)
        self.favouriteswidget.activated.connect(common.execute)
        QtWidgets.QApplication.instance().aboutToQuit.connect(self.save_widget_settings)

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

    def save_widget_settings(self):
        """Saves the position and size of thew widget to the local settings."""
        cls = self.__class__.__name__
        local_settings.setValue(u'widget/{}/width'.format(cls), self.width())
        local_settings.setValue(u'widget/{}/height'.format(cls), self.height())

        pos = self.mapToGlobal(self.rect().topLeft())
        local_settings.setValue(u'widget/{}/x'.format(cls), pos.x())
        local_settings.setValue(u'widget/{}/y'.format(cls), pos.y())

    def hideEvent(self, event):
        """Custom hide event."""
        self.save_widget_settings()
        super(StandaloneBrowserWidget, self).hideEvent(event)

    def showEvent(self, event):
        """Custom show event. When showing the widget we will use the saved
        settings to set the widget's size and position.

        """
        super(StandaloneBrowserWidget, self).showEvent(event)

        cls = self.__class__.__name__
        width = local_settings.value(u'widget/{}/width'.format(cls))
        height = local_settings.value(u'widget/{}/height'.format(cls))
        x = local_settings.value(u'widget/{}/x'.format(cls))
        y = local_settings.value(u'widget/{}/y'.format(cls))

        if not all((width, height, x, y)):  # skip if not saved yet
            return
        size = QtCore.QSize(width, height)
        pos = QtCore.QPoint(x, y)
        # pos = self.mapFromGlobal(pos)
        self.resize(size)
        self.move(pos)
        common.move_widget_to_available_geo(self)

    def closeEvent(self, event):
        """Custom close event will minimize the widget to the tray."""
        event.ignore()
        self.hide()
        self.tray.showMessage(
            u'GWBrowser',
            u'GWBrowser will continue running in the background, you can use this icon to restore it\'s visibility.',
            QtWidgets.QSystemTrayIcon.Information,
            3000
        )

    def mousePressEvent(self, event):
        """The mouse press event responsible for setting the properties needed
        by the resize methods.

        """
        if self.accept_resize_event(event):
            self.resize_area = self.set_resize_icon(event, clamp=False)
            self.resize_initial_pos = event.pos()
            self.resize_initial_rect = self.rect()
        else:
            self.resize_initial_pos = QtCore.QPoint(-1, -1)
            self.resize_initial_rect = None
            self.resize_area = None

    def mouseMoveEvent(self, event):
        """Identify dragable area - vector/distance"""
        if self.resize_initial_pos == QtCore.QPoint(-1, -1):
            self.set_resize_icon(event, clamp=True)
            return

        if self.resize_area is not None:
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
            self.setGeometry(geo)

    def mouseReleaseEvent(self, event):
        """Restores the mouse resize properties."""
        self.resize_initial_pos = QtCore.QPoint(-1, -1)
        self.resize_initial_rect = None
        self.resize_area = None

        app = QtWidgets.QApplication.instance()
        app.restoreOverrideCursor()


class StandaloneApp(QtWidgets.QApplication):
    """This is the app used to run the browser as a standalone widget."""
    MODEL_ID = u'gwbrowser_standalone'

    def __init__(self, args):
        super(StandaloneApp, self).__init__(args)
        self.setApplicationName(u'GWBrowser')

        import gwbrowser
        log_file = open(common.log_path())
        sys.stdout = log_file
        sys.stderr = log_file
        self.setApplicationVersion(gwbrowser.__version__)

        self.set_model_id()
        pixmap = ImageCache.get_rsc_pixmap(u'custom', None, 256)
        self.setWindowIcon(QtGui.QIcon(pixmap))

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
