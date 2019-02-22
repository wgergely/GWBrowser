# -*- coding: utf-8 -*-
"""Spinner widget.
Displays a pop-up widget with a spinning loding indicator.

Example:
.. code-block:: python

    spinner = Spinner()
    spinner.start() # shows the widget
    spinner.stop() # stops the widget

"""

from functools import wraps
from PySide2 import QtWidgets, QtGui, QtCore
import browser.common as common


def longprocess(func):
    """@Decorator to save the painter state."""
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        app = QtWidgets.QApplication.instance()
        app.setOverrideCursor(QtCore.Qt.WaitCursor)
        spinner = Spinner()
        spinner.start()
        res = func(self, *args, spinner=spinner, **kwargs)
        spinner.stop()
        app.restoreOverrideCursor()
        return res
    return func_wrapper


class Spinner(QtWidgets.QWidget):
    """Custom loading indicator."""

    def __init__(self, parent=None):
        super(Spinner, self).__init__(parent=parent)
        from browser.imagecache import ImageCache

        self._createUI()
        self.setText(u'Loading...')

        pixmap = ImageCache.get_rsc_pixmap(u'custom', None, 64)
        self.setWindowIcon(QtGui.QIcon(pixmap))

        self.setWindowFlags(
            QtCore.Qt.Widget |
            QtCore.Qt.FramelessWindowHint
        )
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        self.description = QtWidgets.QLabel(u'')
        self.description.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        self.description.setStyleSheet("""
            QLabel {{
                font-family: "{}";
                font-size: 9pt;
                color: rgba(230,230,230, 255);
                background-color: rgba(50,50,50, 255);
            	border: 0px solid;
            	border-radius: 6px;
                padding: 6px;
            }}
        """.format(common.PrimaryFont.family()))
        self.layout().addWidget(self.description)

    def setText(self, text):
        self.description.setText(text)

    def setPixmap(self, pixmap):
        self.label.setPixmap(pixmap)

    def start(self):
        """Starts the widget-spin."""
        self.show()

    def stop(self):
        """Stops the widget-spin."""
        self.close()



if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    app.w = Spinner()
    app.w.start()
    app.w.setText('asdsad')
    app.exec_()
