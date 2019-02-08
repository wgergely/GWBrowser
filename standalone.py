# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101
"""Standalone runner."""

import sys
import collections
from PySide2 import QtWidgets, QtGui, QtCore

from browser.browserwidget import BrowserWidget
from browser.baselistwidget import BaseContextMenu
import browser.common as common


class StandaloneBrowserWidget(BrowserWidget):
    def __init__(self, parent=None):
        super(StandaloneBrowserWidget, self).__init__(parent=parent)

        self.tray = QtWidgets.QSystemTrayIcon(parent=self)
        pixmap = common.get_rsc_pixmap('custom', None, 256)
        icon = QtGui.QIcon(pixmap)
        self.tray.setIcon(icon)
        self.tray.setContextMenu(TrayMenu(parent=self))
        self.tray.setToolTip('Glassworks pipeline Browser')
        self.tray.show()
        self.tray.activated.connect(self.trayActivated)


    def trayActivated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Unknown:
            self.show()
            self.raise_()
        if reason == QtWidgets.QSystemTrayIcon.Context:
            return
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self.show()
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

        self.stayontop = False

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
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

        menu_set['Always stays on top'] = {
            'checkable': True,
            'action': set_flag
        }
        menu_set['separator0'] = {}
        menu_set['Show'] = {
            'action': self.parent().showNormal
        }
        menu_set['Hide'] = {
            'action': self.parent().close
        }
        menu_set['Minimize'] = {
            'action': self.parent().showMinimized
        }
        menu_set['separator1'] = {}
        menu_set['Quit'] = {
            'action': lambda: QtWidgets.QApplication.instance().quit()
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
