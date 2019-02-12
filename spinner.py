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
        spinner = Spinner()
        spinner.start()
        res = func(self, *args, spinner=spinner, **kwargs)
        spinner.stop()
        return res
    return func_wrapper


class Spinner(QtWidgets.QWidget):
    """Custom loading indicator."""

    def __init__(self, parent=None):
        super(Spinner, self).__init__(parent=parent)
        self._createUI()
        self.setText(u'Loading...')

        pixmap = common.get_rsc_pixmap(u'custom', None, 64)
        self.setWindowIcon(QtGui.QIcon(pixmap))

        self.spinner_pixmap = common.get_rsc_pixmap(
            u'spinner', common.TEXT, 24)
        self.setPixmap(self.get_pixmap(0))

        self.setWindowOpacity(1)
        self.setWindowFlags(
            QtCore.Qt.Dialog |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_PaintOnScreen)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.worker = GUIUpdater()
        self._connectSignals()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().setSpacing(12)
        self.layout().setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        self.description = QtWidgets.QLabel(u'')
        self.description.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        self.description.setStyleSheet("""
            QLabel {{
                font-family: "{}";
                font-size: 9pt;
                color: rgba(200,200,200, 255);
                background-color: rgba(50,50,50, 255);
            	border: 0px solid;
            	border-radius: 6px;
                padding: 12px;
            }}
        """.format(common.PrimaryFont.family()))

        self.layout().addWidget(self.label)
        self.layout().addWidget(self.description)

    def setText(self, text):
        self.description.setText(text)

    def setPixmap(self, pixmap):
        self.label.setPixmap(pixmap)

    def start(self):
        """Starts the widget-spin."""
        self.show()
        self.move_to_center()
        self.worker.run()

    def stop(self):
        """Stops the widget-spin."""
        app = QtCore.QCoreApplication.instance()
        app.restoreOverrideCursor()

        self.worker.quit()
        self.worker.deleteLater()
        self.close()

    def refresh(self, degree):
        """Main method to update the spinner called by the waroker class."""
        degree += 14
        # QtCore.QCoreApplication.instance().processEvents(
        #     QtCore.QEventLoop.ExcludeUserInputEvents)
        self.setPixmap(self.get_pixmap(degree * 20))

    def move_to_center(self):
        app = QtWidgets.QApplication.instance()
        widget = next((f for f in app.allWidgets() if f.objectName() == u'BrowserWidget'), None)

        if not widget:
            geo = app.desktop().availableGeometry(0)
        elif not widget.isVisible():
            geo = app.desktop().availableGeometry(widget)
        else:
            geo = widget.geometry()
        self.move(geo.center() - self.rect().center())

    def get_pixmap(self, angle):
        """Paints and rotates the spinner pixmap."""
        rotated_spinner = QtGui.QPixmap(
            self.spinner_pixmap.width(), self.spinner_pixmap.height())

        rotated_spinner.fill(QtGui.QColor(255, 255, 255, 0))

        painter = QtGui.QPainter()
        painter.begin(rotated_spinner)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOut)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        painter.translate(rotated_spinner.width() / 2.0,
                          rotated_spinner.height() / 2.0)
        painter.rotate(angle)
        painter.translate(-rotated_spinner.width() / 2.0, -
                          rotated_spinner.height() / 2.0)
        painter.drawPixmap(self.spinner_pixmap.rect(), self.spinner_pixmap)

        tinted_spinner = QtGui.QPixmap(
            self.spinner_pixmap.width(), self.spinner_pixmap.height())
        tinted_spinner.fill(QtGui.QColor(255, 255, 255, 255))
        painter.end()

        painter = QtGui.QPainter()
        painter.begin(tinted_spinner)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
        painter.setCompositionMode(
            QtGui.QPainter.CompositionMode_DestinationAtop)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        painter.drawPixmap(self.spinner_pixmap.rect(), rotated_spinner)
        painter.end()

        return tinted_spinner

    def _connectSignals(self):
        self.worker.updateLabel.connect(self.refresh)


class GUIUpdater(QtCore.QThread):

    updateLabel = QtCore.Signal(int)

    def increment(self):
        self.degree += 1
        self.updateLabel.emit(self.degree)

    def run(self):
        app = QtCore.QCoreApplication.instance()

        self.degree = 0
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.increment)
        self.timer.timeout.connect(lambda: app.setOverrideCursor(QtCore.Qt.WaitCursor))
        self.timer.setInterval(100)
        self.timer.setSingleShot(False)
        self.timer.start()


# if __name__ == '__main__':
#     app = QtWidgets.QApplication(sys.argv)
#     app.w = Spinner()
#     app.w.start()
#     app.exec_()
