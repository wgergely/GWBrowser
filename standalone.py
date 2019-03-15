# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101


"""Browser - Standalone PySide2 application."""

import sys
import browser.modules
from PySide2 import QtWidgets, QtGui, QtCore

from browser.browserwidget import BrowserWidget, SizeGrip
from browser.listcontrolwidget import BrowserButtonContextMenu
from browser.fileswidget import FilesWidget
from browser.editors import ClickableLabel
from browser.baselistwidget import contextmenu
import browser.common as common
from browser.settings import local_settings
from browser.imagecache import ImageCache


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
        def _set_flag():
            """Sets the WindowStaysOnTopHint for the window."""
            self.parent().hide()
            if self.stays_on_top:
                self.parent().setWindowFlags(
                    QtCore.Qt.Window
                    | QtCore.Qt.FramelessWindowHint)
            else:
                self.parent().setWindowFlags(
                    QtCore.Qt.Window
                    | QtCore.Qt.FramelessWindowHint
                    | QtCore.Qt.WindowStaysOnTopHint
                    | QtCore.Qt.X11BypassWindowManagerHint)
            self.parent().show()
            self.stays_on_top = not self.stays_on_top

        menu_set['Keep on top of other windows'] = {
            'checkable': True,
            'action': _set_flag
        }
        menu_set['Show window...'] = {
            'action': self.show_window
        }
        menu_set['separator1'] = {}
        menu_set['Quit'] = {
            'action': lambda: QtWidgets.QApplication.instance().quit()
        }
        return menu_set


class CloseButton(ClickableLabel):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(CloseButton, self).__init__(parent=parent)
        pixmap = ImageCache.get_rsc_pixmap(
            u'close', common.SECONDARY_BACKGROUND, common.ROW_BUTTONS_HEIGHT / 1.5)
        self.setFixedSize(common.ROW_BUTTONS_HEIGHT / 1.5,
                          common.ROW_BUTTONS_HEIGHT / 1.5)
        self.setPixmap(pixmap)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)


class MinimizeButton(ClickableLabel):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(MinimizeButton, self).__init__(parent=parent)
        pixmap = ImageCache.get_rsc_pixmap(
            u'minimize', common.SECONDARY_BACKGROUND, common.ROW_BUTTONS_HEIGHT / 1.5)
        self.setFixedSize(common.ROW_BUTTONS_HEIGHT / 1.5,
                          common.ROW_BUTTONS_HEIGHT / 1.5)
        self.setPixmap(pixmap)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)


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
        self._createUI()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(common.INDICATOR_WIDTH * 2)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT / 1.5)

        self.layout().addStretch()
        self.layout().addWidget(MinimizeButton(parent=self))
        self.layout().addWidget(CloseButton(parent=self))

    def mousePressEvent(self, event):
        self.move_in_progress = True
        self.move_start_event_pos = event.pos()
        self.move_start_widget_pos = self.mapToGlobal(
            self.geometry().topLeft())

    def mouseMoveEvent(self, event):
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


class StandaloneBrowserWidget(BrowserWidget):
    """Browserwidget with added QSystemTrayIcon."""

    def __init__(self, parent=None):
        super(StandaloneBrowserWidget, self).__init__(parent=parent)

        self.tray = QtWidgets.QSystemTrayIcon(parent=self)
        pixmap = ImageCache.get_rsc_pixmap('custom', None, 256)
        icon = QtGui.QIcon(pixmap)

        self.tray.setIcon(icon)
        self.tray.setContextMenu(TrayMenu(parent=self))
        self.tray.setToolTip('Browser')
        self.tray.show()
        self.tray.activated.connect(self.trayActivated)
        self.findChild(FilesWidget).activated.connect(
            self.index_activated)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        shadow_offset = common.INDICATOR_WIDTH * 2
        self.layout().setContentsMargins(common.INDICATOR_WIDTH + shadow_offset, common.INDICATOR_WIDTH + shadow_offset,
                                         common.INDICATOR_WIDTH + shadow_offset, common.INDICATOR_WIDTH + shadow_offset)

        self.effect = QtWidgets.QGraphicsDropShadowEffect(self)
        self.effect.setBlurRadius(shadow_offset)
        self.effect.setXOffset(0)
        self.effect.setYOffset(0)
        self.effect.setColor(QtGui.QColor(0, 0, 0, 80))
        self.setGraphicsEffect(self.effect)

    def _createUI(self):
        super(StandaloneBrowserWidget, self)._createUI()
        self.headerwidget = HeaderWidget(parent=self)
        self.layout().insertWidget(0, self.headerwidget)
        grip = self.statusbar.findChild(SizeGrip)
        grip.show()

    def _connectSignals(self):
        super(StandaloneBrowserWidget, self)._connectSignals()

        minimizebutton = self.findChild(MinimizeButton)
        closebutton = self.findChild(CloseButton)
        minimizebutton.clicked.connect(self.showMinimized)
        closebutton.clicked.connect(self.close)

    def paintEvent(self, event):
        """Drawing a rounded background help to identify that the widget
        is in standalone mode."""
        rect = QtCore.QRect(self.rect())
        center = rect.center()
        rect.setWidth(rect.width() - common.MARGIN)
        rect.setHeight(rect.height() - common.MARGIN)
        rect.moveCenter(center)

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.SEPARATOR)
        painter.drawRoundedRect(rect, 4, 4)
        painter.end()

    def index_activated(self, index):
        """When in standalone mode, double-clicking an item will open that item."""
        if not index.isValid():
            return
        location = self.findChild(
            FilesWidget).model().sourceModel().data_key()

        data = index.data(QtCore.Qt.StatusTipRole)
        if location == common.RendersFolder:
            path = common.get_sequence_startpath(data)
        else:
            path = common.get_sequence_endpath(data)
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)

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
        cls = self.__class__.__name__
        local_settings.setValue(u'widget/{}/width'.format(cls), self.width())
        local_settings.setValue(u'widget/{}/height'.format(cls), self.height())

        pos = self.mapToGlobal(self.rect().topLeft())
        local_settings.setValue(u'widget/{}/x'.format(cls), pos.x())
        local_settings.setValue(u'widget/{}/y'.format(cls), pos.y())

        super(BrowserWidget, self).hideEvent(event)

    def showEvent(self, event):
        super(BrowserWidget, self).showEvent(event)
        cls = self.__class__.__name__

        width = local_settings.value(u'widget/{}/width'.format(cls))
        height = local_settings.value(u'widget/{}/height'.format(cls))
        x = local_settings.value(u'widget/{}/x'.format(cls))
        y = local_settings.value(u'widget/{}/y'.format(cls))

        if not all((width, height, x, y)):  # skip if not saved yet
            return
        size = QtCore.QSize(width, height)
        pos = QtCore.QPoint(x, y)

        self.resize(size)
        self.move(pos)

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
        self.setApplicationVersion(u'0.2.0')
        self.set_model_id()
        pixmap = ImageCache.get_rsc_pixmap(u'custom', None, 256)
        self.setWindowIcon(QtGui.QIcon(pixmap))

    def exec_(self):
        """Shows the ``StandaloneBrowserWidget`` on execution."""
        widget = StandaloneBrowserWidget()
        widget.showNormal()
        widget.activateWindow()
        widget.raise_()
        super(StandaloneApp, self).exec_()

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


if __name__ == '__main__':
    app = StandaloneApp(sys.argv)
    app.exec_()
