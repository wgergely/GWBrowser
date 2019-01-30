# -*- coding: utf-8 -*-
"""Spinner widget.
Displays a pop-up widget with a spinning loding indicator.

Example:
.. code-block:: python

    spinner = Spinner()
    spinner.start() # shows the widget
    spinner.stop() # stops the widget

"""

import sys
from PySide2 import QtWidgets, QtGui, QtCore


class Spinner(QtWidgets.QWidget):
    """Custom loading indicator."""

    def __init__(self, parent=None):
        super(Spinner, self).__init__(parent=parent)
        self.label = None
        self._createUI()

        self.animation = None
        self.setWindowOpacity(0)

        self.spinner_pixmap = QtGui.QImage()
        self.spinner_pixmap.load(self.get_thumbnail_path())
        self.spinner_pixmap = self.spinner_pixmap.smoothScaled(
            self.spinner_pixmap.width() / 3,
            self.spinner_pixmap.height() / 3
        )
        self.spinner_pixmap = QtGui.QPixmap(self.spinner_pixmap)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        app = QtCore.QCoreApplication.instance()
        app.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.animate_opacity()
        self.show()


    def start(self):
        """Starts the widget-spin."""
        self.degree = 0
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.increment)
        self.timer.setInterval(40)
        self.timer.setSingleShot(False)
        self.timer.start()

    def stop(self):
        """Stops the widget-spin."""
        app = QtCore.QCoreApplication.instance()
        app.restoreOverrideCursor()
        self.close()

    def update_label(self, degree):
        """Main method to update the spinner called by the waroker class."""
        self.raise_()
        self.move_to_center()

        mayaWindow = None
        for o in QtWidgets.QApplication.instance().topLevelWidgets():
            if o.objectName() == 'MayaWindow':
                mayaWindow = o
                break

        if mayaWindow:
            mayaWindow.setUpdatesEnabled(True)

        degree += 14
        pixmap = self.get_spinner(degree * 20)
        self.label.setPixmap(pixmap)

        app = QtCore.QCoreApplication.instance()
        app.processEvents()

    def get_spinner(self, angle):
        """Paints and rotates the spinner pixmap."""
        rotated_spinner = QtGui.QPixmap(
            self.spinner_pixmap.width(), self.spinner_pixmap.height())
        rotated_spinner.fill(QtGui.QColor(255, 255, 255, 0))

        painter = QtGui.QPainter(rotated_spinner)
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
        painter.end()

        tinted_spinner = QtGui.QPixmap(
            self.spinner_pixmap.width(), self.spinner_pixmap.height())
        tinted_spinner.fill(QtGui.QColor(255, 255, 255, 255))

        painter = QtGui.QPainter(tinted_spinner)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_DestinationAtop)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        painter.drawPixmap(self.spinner_pixmap.rect(), rotated_spinner)
        painter.end()

        return tinted_spinner

    def _createUI(self):
        """Creates the ui layout of this widget."""
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.label = QtWidgets.QLabel()
        self.layout().addWidget(self.label)

        self.setWindowFlags(
            QtCore.Qt.Widget |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_PaintOnScreen)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

    def animate_opacity(self):
        """Animates the visibility of the widget."""
        self.animation = QtCore.QPropertyAnimation(self, 'windowOpacity')
        self.animation.setEasingCurve(QtCore.QEasingCurve.InQuad)
        self.animation.setDuration(300)
        self.animation.setStartValue(0.01)
        self.animation.setEndValue(1)
        self.animation.start(QtCore.QPropertyAnimation.DeleteWhenStopped)

    @staticmethod
    def get_thumbnail_path():
        """The path to the spinner thumbnail."""
        info = QtCore.QFileInfo(
            '{}/../thumbnails/spinner.png'.format(__file__))
        if info.exists():
            return info.absoluteFilePath()
        return None


    def move_to_center(self):
        """Moves the widget to the center of the dektop."""
        app = QtCore.QCoreApplication.instance()
        geometry = app.desktop().availableGeometry()
        self.move(geometry.center() - self.rect().center())

    def showEvent(self, event):
        """Custom show event."""
        self.move_to_center()

    def increment(self):
        self.degree += 1
        self.update_label(self.degree)



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.w = Spinner()
    app.w.start()
    app.exec_()
