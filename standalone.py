"""Standalone runner."""

import sys
import ctypes
from PySide2 import QtWidgets, QtGui, QtCore
from mayabrowser.toolbar import MayaBrowserWidget


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName('Browser')
    appID = u'glassworks.browser' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appID)

    widget = MayaBrowserWidget()
    widget.move(50, 50)
    widget.show()
    widget.projectsButton.clicked.emit()
    app.exec_()
