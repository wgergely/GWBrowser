# -*- coding: utf-8 -*-
"""``debug.py`` contains the widget used to display debugging information."""

import sys
from PySide2 import QtCore, QtGui, QtWidgets


class DebugWidget(QtWidgets.QTextEdit):
    def __init__(self, parent=None):
        super(DebugWidget, self).__init__(parent=parent)
        print dir(sys.stdout)
        sys.stdout.write('!')
        for l in sys.stdout.xreadlines():
            print l


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = DebugWidget()
    w.show()
    app.exec_()
