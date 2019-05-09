# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, E1120
"""The module containing all widgets needed to run GWBrowser in standalone-mode."""

from PySide2 import QtWidgets, QtGui, QtCore

from gwbrowser.browserwidget import BrowserWidget, SizeGrip
from gwbrowser.listcontrolwidget import BrowserButtonContextMenu
from gwbrowser.editors import ClickableLabel
from gwbrowser.basecontextmenu import contextmenu
import gwbrowser.common as common
from gwbrowser.settings import local_settings
from gwbrowser.imagecache import ImageCache


class TrayMenu(BrowserButtonContextMenu):
    """The context menu associated with the QSystemTrayIcon."""

    def __init__(self, parent=None):
        super(TrayMenu, self).__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)

        self.stays_on_top = False
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
            'action': lambda: self.parent().shutdown.emit()
        }
        return menu_set


class CloseButton(ClickableLabel):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(CloseButton, self).__init__(parent=parent)
        pixmap = ImageCache.get_rsc_pixmap(
            u'close', common.SECONDARY_BACKGROUND, common.ROW_BUTTONS_HEIGHT / 2)
        self.setFixedSize(common.ROW_BUTTONS_HEIGHT / 2,
                          common.ROW_BUTTONS_HEIGHT / 2)
        self.setPixmap(pixmap)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setFocusPolicy(QtCore.Qt.NoFocus)


class MinimizeButton(ClickableLabel):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(MinimizeButton, self).__init__(parent=parent)
        pixmap = ImageCache.get_rsc_pixmap(
            u'minimize', common.SECONDARY_BACKGROUND, common.ROW_BUTTONS_HEIGHT / 2)
        self.setFixedSize(common.ROW_BUTTONS_HEIGHT / 2,
                          common.ROW_BUTTONS_HEIGHT / 2)
        self.setPixmap(pixmap)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setFocusPolicy(QtCore.Qt.NoFocus)


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
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(common.INDICATOR_WIDTH * 2)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT / 2)

        self.layout().addStretch()
        self.layout().addWidget(MinimizeButton(parent=self))
        self.layout().addWidget(CloseButton(parent=self))

    def mousePressEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.move_in_progress = True
        self.move_start_event_pos = event.pos()
        self.move_start_widget_pos = self.mapToGlobal(
            self.geometry().topLeft())

    def mouseMoveEvent(self, event):
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
        widget = TrayMenu(parent=self.window())
        pos = self.window().mapToGlobal(event.pos())
        widget.move(pos)
        common.move_widget_to_available_geo(widget)
        widget.show()


class StandaloneBrowserWidget(BrowserWidget):
    """Browserwidget with added QSystemTrayIcon."""

    def __init__(self, parent=None):
        super(StandaloneBrowserWidget, self).__init__(parent=parent)

        self.tray = QtWidgets.QSystemTrayIcon(parent=self)
        pixmap = ImageCache.get_rsc_pixmap('custom', None, 256)
        icon = QtGui.QIcon(pixmap)

        self.headerwidget = None

        self.tray.setIcon(icon)
        self.tray.setContextMenu(TrayMenu(parent=self))
        self.tray.setToolTip('Browser')
        self.tray.show()
        self.tray.activated.connect(self.trayActivated)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.initialized.connect(self.tweak_ui)
        self.initialized.connect(self.showNormal)
        self.initialized.connect(self.activateWindow)

    @QtCore.Slot()
    def tweak_ui(self):
        """UI modifications to apply when the tool is started in standalone-mode."""
        self.headerwidget = HeaderWidget(parent=self)
        self.layout().insertWidget(0, self.headerwidget)

        grip = self.statusbar.findChild(SizeGrip)
        grip.show()

        shadow_offset = 0
        self.layout().setContentsMargins(
            common.INDICATOR_WIDTH + shadow_offset, common.INDICATOR_WIDTH + shadow_offset,
            common.INDICATOR_WIDTH + shadow_offset, common.INDICATOR_WIDTH + shadow_offset)

        self.findChild(MinimizeButton).clicked.connect(self.showMinimized)
        self.findChild(CloseButton).clicked.connect(self.close)

        self.fileswidget.activated.connect(common.execute)
        self.favouriteswidget.activated.connect(common.execute)
        app = QtWidgets.QApplication.instance().aboutToQuit.connect(
            self.save_widget_settings)

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
        cls = self.__class__.__name__
        local_settings.setValue(u'widget/{}/width'.format(cls), self.width())
        local_settings.setValue(u'widget/{}/height'.format(cls), self.height())

        pos = self.mapToGlobal(self.rect().topLeft())
        local_settings.setValue(u'widget/{}/x'.format(cls), pos.x())
        local_settings.setValue(u'widget/{}/y'.format(cls), pos.y())

    def hideEvent(self, event):
        cls = self.__class__.__name__
        local_settings.setValue(u'widget/{}/width'.format(cls), self.width())
        local_settings.setValue(u'widget/{}/height'.format(cls), self.height())

        pos = self.mapToGlobal(self.rect().topLeft())
        # pos = QtCore.QPoint(pos)
        local_settings.setValue(u'widget/{}/x'.format(cls), pos.x())
        local_settings.setValue(u'widget/{}/y'.format(cls), pos.y())

        super(StandaloneBrowserWidget, self).hideEvent(event)

    def showEvent(self, event):
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
            'Browser',
            'Browser will continue running in the background, you can use this icon to restore it\'s visibility.',
            QtWidgets.QSystemTrayIcon.Information,
            3000
        )


class StandaloneApp(QtWidgets.QApplication):
    """This is the app used to run the browser as a standalone widget."""
    MODEL_ID = u'browser_standalone'

    def __init__(self, args):
        super(StandaloneApp, self).__init__(args)
        self.setApplicationName(u'Browser')

        import gwbrowser
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
