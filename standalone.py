# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101
"""Standalone runner."""

import sys
from PySide2 import QtWidgets, QtGui, QtCore

from browser.browserwidget import BrowserWidget
import browser.common as common



class StandaloneApp(QtWidgets.QApplication):
    """This is the app used to run the browser as a standalone widget."""
    MODEL_ID = u'browser_standalone'

    def __init__(self, args):
        super(StandaloneApp, self).__init__(args)
        self.setApplicationName('Browser')
        self.set_model_id()
        pixmap = common.get_rsc_pixmap('custom', None, 64)
        self.setWindowIcon(QtGui.QIcon(pixmap))

    def exec_(self):
        widget = BrowserWidget()
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
    app =StandaloneApp(sys.argv)
    app.exec_()
