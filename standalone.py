"""Standalone runner."""

import sys
from PySide2 import QtWidgets, QtGui, QtCore
from mayabrowser.toolbar import MayaBrowserWidget

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    widget = MayaBrowserWidget()
    widget.move(50, 50)
    widget.show()
    widget.projectsButton.clicked.emit()
    app.exec_()
