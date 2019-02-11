# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101


"""Browser - Standalone PySide2 application."""


import sys
import functools

from PySide2 import QtWidgets, QtGui, QtCore

from browser.browserwidget import BrowserWidget
from browser.fileswidget import FilesWidget
from browser.baselistwidget import BaseContextMenu, contextmenu
import browser.common as common
from browser.settings import Active, local_settings


class TrayMenu(BaseContextMenu):
    """The context menu associated with the QSystemTrayIcon."""

    def __init__(self, parent=None):
        super(TrayMenu, self).__init__(QtCore.QModelIndex(), parent=parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)

        self.stays_on_top = False

        self.add_toolbar_menu()
        self.add_visibility_menu()

    def show_(self):
        """Raises and shows the widget."""
        screen = self.parent().window().windowHandle().screen()
        self.parent().move(screen.geometry().center() - self.parent().rect().center())
        self.parent().show()
        self.parent().activateWindow()
        self.parent().raise_()

    @contextmenu
    def add_visibility_menu(self, menu_set):
        """Actions associated with the visibility of the widget."""
        def _set_flag():
            """Sets the WindowStaysOnTopHint for the window."""
            self.parent().hide()
            if self.stays_on_top:
                self.parent().setWindowFlags(
                    QtCore.Qt.Window |
                    QtCore.Qt.FramelessWindowHint)
            else:
                self.parent().setWindowFlags(
                    QtCore.Qt.Window |
                    QtCore.Qt.FramelessWindowHint |
                    QtCore.Qt.WindowStaysOnTopHint |
                    QtCore.Qt.X11BypassWindowManagerHint)
            self.parent().show()
            self.stays_on_top = not self.stays_on_top

        menu_set['Keep on top of other windows'] = {
            'checkable': True,
            'action': _set_flag
        }
        menu_set['Show'] = {
            'action': self.show_
        }
        menu_set['separator1'] = {}
        menu_set['Quit'] = {
            'action': lambda: QtWidgets.QApplication.instance().quit()
        }
        return menu_set

    @contextmenu
    def add_toolbar_menu(self, menu_set):
        """Actions associated with the active paths."""
        active_paths = Active.get_active_paths()
        bookmark = (active_paths[u'server'],
                    active_paths[u'job'], active_paths[u'root'])
        asset = bookmark + (active_paths[u'asset'],)
        file_ = asset + (active_paths[u'location'],)

        menu_set[u'location'] = {
            u'icon': common.get_rsc_pixmap(u'location', common.TEXT, common.INLINE_ICON_SIZE),
            u'disabled': not all(file_),
            u'text': u'Show active location in the file manager...',
            u'action': functools.partial(common.reveal, u'/'.join([f for f in file_ if f]))
        }
        menu_set[u'asset'] = {
            u'icon': common.get_rsc_pixmap(u'assets', common.TEXT, common.INLINE_ICON_SIZE),
            u'disabled': not all(asset),
            u'text': u'Show active asset in the file manager...',
            u'action': functools.partial(common.reveal, u'/'.join([f for f in asset if f]))
        }
        menu_set[u'bookmark'] = {
            u'icon': common.get_rsc_pixmap('bookmarks', common.TEXT, common.INLINE_ICON_SIZE),
            u'disabled': not all(bookmark),
            u'text': u'Show active bookmark in the file manager...',
            u'action': functools.partial(common.reveal, u'/'.join([f for f in bookmark if f]))
        }
        return menu_set


class StandaloneBrowserWidget(BrowserWidget):
    """Browserwidget with added QSystemTrayIcon."""

    def __init__(self, parent=None):
        super(StandaloneBrowserWidget, self).__init__(parent=parent)

        self.tray = QtWidgets.QSystemTrayIcon(parent=self)
        pixmap = common.get_rsc_pixmap('custom', None, 256)
        icon = QtGui.QIcon(pixmap)

        self.tray.setIcon(icon)
        self.tray.setContextMenu(TrayMenu(parent=self))
        self.tray.setToolTip('Browser')
        self.tray.show()
        self.tray.activated.connect(self.trayActivated)
        self.findChild(FilesWidget).itemDoubleClicked.connect(self.itemDoubleClicked)

    def itemDoubleClicked(self, index):
        """When in standalone mode, double-clicking an item will open that item."""
        if not index.isValid():
            return
        location = self.findChild(FilesWidget).model().sourceModel().get_location()

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
        pixmap = common.get_rsc_pixmap(u'custom', None, 256)
        self.setWindowIcon(QtGui.QIcon(pixmap))

    def exec_(self):
        """Shows the ``StandaloneBrowserWidget`` on execution."""
        widget = StandaloneBrowserWidget()
        widget.show()
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
