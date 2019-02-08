# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101
"""Standalone runner."""

import sys
import functools
import collections
from PySide2 import QtWidgets, QtGui, QtCore

from browser.browserwidget import BrowserWidget
from browser.baselistwidget import BaseContextMenu
import browser.common as common
from browser.settings import Active


class StandaloneBrowserWidget(BrowserWidget):
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


    def trayActivated(self, reason):
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

    def closeEvent(self, event):
        """Custom hide event."""
        event.ignore()
        self.hide()
        self.tray.showMessage(
            'Browser',
            'Browser will continue running in the background',
            QtWidgets.QSystemTrayIcon.Information,
            2000
        )

class TrayMenu(BaseContextMenu):
    """This is the tray menu."""
    def __init__(self, parent=None):
        super(TrayMenu, self).__init__(QtCore.QModelIndex(), parent=parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)

        self.stayontop = False
        self.add_toolbar_menu()
        self.add_visibility_menu()

    def add_visibility_menu(self):
        menu_set = collections.OrderedDict()

        def set_flag():
            self.parent().hide()
            if self.stayontop:
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
            self.stayontop = not self.stayontop


        menu_set['separator0'] = {}
        menu_set['Keep on top of other windows'] = {
            'checkable': True,
            'action': set_flag
        }
        menu_set['Show'] = {
            'action': self.show_
        }
        menu_set['separator1'] = {}
        menu_set['Quit'] = {
            'action': lambda: QtWidgets.QApplication.instance().quit()
        }
        self.create_menu(menu_set)

    def show_(self):
        screen = self.parent().window().windowHandle().screen()
        self.parent().move(screen.geometry().center() - self.parent().rect().center())
        self.parent().show()
        self.parent().activateWindow()
        self.parent().raise_()

    def add_toolbar_menu(self):
        active_paths = Active.get_active_paths()
        bookmark = (active_paths[u'server'],
                    active_paths[u'job'], active_paths[u'root'])
        asset = bookmark + (active_paths[u'asset'],)
        file_ = asset + (active_paths[u'location'],)
        menu_set = collections.OrderedDict()

        menu_set[u'separator'] = {}
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



        self.create_menu(menu_set)


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
        widget = StandaloneBrowserWidget()
        widget.show()
        super(StandaloneApp, self).exec_()

    def set_model_id(self):
        """https://github.com/cztomczak/cefpython/issues/395"""
        if "win32" in sys.platform:
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
