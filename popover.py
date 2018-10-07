from math import cos, sin, pi
from PySide2 import QtCore, QtGui, QtWidgets

from mayabrowser.toolbar import MayaBrowserWidget


class PopupButton(QtWidgets.QPushButton):

    def __init__(self, *args, **kwargs):
        super(PopupButton, self).__init__(*args, **kwargs)
        self._createUI()

    def _createUI(self):
        self.setStyleSheet(MayaBrowserWidget.buttonStyle())
        self.setWindowFlags(
            QtCore.Qt.Widget |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )

        self.setFixedHeight(24)
        self.setFixedWidth(120)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)


class PopupCanvas(QtWidgets.QWidget):

    def __init__(self, origin, parent=None):
        super(PopupCanvas, self).__init__(parent=parent)

        self.origin = origin
        self._createUI()

        self.setWindowOpacity(0.01)
        self.animation = None

        self.timer = QtCore.QTimer()
        self.timer.setInterval(20)
        self.timer.setSingleShot(False)

        self._connectSignals()

    def rotate(self, point, angle):
        angle = angle * (pi / 180.0)
        cos_theta, sin_theta = cos(angle), sin(angle)
        x0, y0 = (self.origin.x(), self.origin.y())

        def xform(point):
            x, y = point[0] - x0, point[1] - y0
            return (x * cos_theta - y * sin_theta + x0,
                    x * sin_theta + y * cos_theta + y0)
        return xform(point)

    def paint_line(self, painter):
        """Draws a line between the two input points."""
        path = QtGui.QPainterPath()
        path.moveTo(self.origin)
        path.lineTo(QtGui.QCursor().pos())

        pen = QtGui.QPen(QtGui.QColor(68, 68, 68))
        pen.setWidth(2)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawPath(path)

    def paint_background(self, painter):
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 30)))
        painter.drawRect(self.rect())

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=True
        )

        self.paint_background(painter)
        self.paint_line(painter)

        painter.end()

    def show(self):
        """Method connected to the clicked() signal."""
        self.set_full_screen()
        self.timer.start()
        self.setFocus()
        self.activateWindow()
        self.raise_()
        self.move_buttons()
        super(PopupCanvas, self).show()
        widget.animate_opacity()

    def animate_opacity(self):
        self.animation = QtCore.QPropertyAnimation(
            self, 'windowOpacity', parent=self)
        self.animation.setEasingCurve(QtCore.QEasingCurve.InQuad)
        self.animation.setDuration(150)
        self.animation.setStartValue(0.01)
        self.animation.setEndValue(1)
        self.animation.start(QtCore.QPropertyAnimation.DeleteWhenStopped)

    def _createUI(self):
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
        )

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_PaintOnScreen)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        self.button1 = PopupButton('Scenes files...', parent=self)
        self.button2 = PopupButton('Textures...', parent=self)
        self.button3 = PopupButton('Exports...', parent=self)
        self.button4 = PopupButton('Renders...', parent=self)
        self.installEventFilter(self)

    def active_button_style(self):
        return """
        QPushButton {
            text-align: left;
            border: 1px solid rgba(0, 100, 255, 255);
            padding-left: 10px;
            padding-right: 10px;
            border-style: solid;
            color: rgb(230, 230, 230);
            background-color: rgb(100, 100, 100);
        }
        """

    def eventFilter(self, widget, event):
        cursor = QtGui.QCursor()
        pos = cursor.pos()
        if event.type() == QtCore.QEvent.MouseMove:
            if self.button1.geometry().contains(pos):
                self.button1.setStyleSheet(self.active_button_style())
            elif self.button2.geometry().contains(pos):
                self.button2.setStyleSheet(self.active_button_style())
            elif self.button3.geometry().contains(pos):
                self.button3.setStyleSheet(self.active_button_style())
            elif self.button4.geometry().contains(pos):
                self.button4.setStyleSheet(self.active_button_style())
            else:
                self.button1.setStyleSheet(MayaBrowserWidget.buttonStyle())
                self.button2.setStyleSheet(MayaBrowserWidget.buttonStyle())
                self.button3.setStyleSheet(MayaBrowserWidget.buttonStyle())
                self.button4.setStyleSheet(MayaBrowserWidget.buttonStyle())
                return True

        if event.type() == QtCore.QEvent.MouseButtonRelease:
            if self.button1.geometry().contains(pos):
                self.button1.clicked.emit()
            elif self.button2.geometry().contains(pos):
                self.button2.clicked.emit()
            elif self.button3.geometry().contains(pos):
                self.button3.clicked.emit()
            elif self.button4.geometry().contains(pos):
                self.button4.clicked.emit()

            self.close()
            return True

        return False

    def move_buttons(self):
        """Moves the popu-up buttons to place."""
        buttons = [self.button1, self.button2, self.button3, self.button4]
        increment = 25.0
        angle = 0 - (increment * float(len(buttons))) / 2.0 + (increment / 2.0)

        for button in reversed(buttons):
            pos = QtCore.QPoint(
                self.origin.x() - 120,
                self.origin.y(),
            )
            pos = self.rotate((pos.x(), pos.y()), angle)
            pos = QtCore.QPoint(*pos)
            button.move(
                pos.x() - (button.width() / 2.0),
                pos.y() - (button.height() / 2.0),
            )
            angle += increment

    def _connectSignals(self):
        # self.button1.clicked.connect(self.close)
        # self.button2.clicked.connect(self.close)
        # self.button3.clicked.connect(self.close)
        self.timer.timeout.connect(self.update)

    def button1Clicked(self):
        self.close()

    def keyPressEvent(self, event):
        if event.modifiers() == QtCore.Qt.NoModifier:
            if event.key() == QtCore.Qt.Key_Escape:
                self.close()

    def set_full_screen(self):
        """Sets the widget to be the size of the current screen."""
        app = QtCore.QCoreApplication.instance()
        idx = app.desktop().screenNumber(self)
        self.setGeometry(app.desktop().screenGeometry(idx))


if __name__ == '__main__':
    a = QtWidgets.QApplication([])

    cursor = QtGui.QCursor()
    origin = cursor.pos()

    widget = PopupCanvas(origin)
    widget.show()
    # w2 = Dot()
    # w2.show()
    # w1 = Dot()
    # w1.show()
    # w3 = Dot()
    # w3.show()
    #
    # pos2 = rotate(origin, QtCore.QPoint(origin.x(), origin.y() - offset), 0)
    # pos3 = rotate(origin, QtCore.QPoint(origin.x(), origin.y() - offset), 90)
    # w1.move(pos1)
    # w2.move(pos2)
    # w3.move(pos3)

    a.exec_()
