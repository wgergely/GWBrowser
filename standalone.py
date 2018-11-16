"""Standalone runner."""

import sys
import ctypes
from PySide2 import QtWidgets, QtGui, QtCore

from mayabrowser.toolbar import MayaBrowserWidget

class StandaloneApp(QtWidgets.QApplication):
    def __init__(self, args):
        super(StandaloneApp, self).__init__(args)
        self.setApplicationName('Browser')


if __name__ == '__main__':
    app = StandaloneApp(sys.argv)
    appID = u'glassworks.browser' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appID)

    widget = MayaBrowserWidget()
    widget.move(50, 50)
    widget.show()
    widget.projectsButton.clicked.emit()
    app.exec_()
