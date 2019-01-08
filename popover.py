from math import cos, sin, pi
from PySide2 import QtCore, QtGui, QtWidgets


class PopupButton(QtWidgets.QPushButton):

    def __init__(self, *args, **kwargs):
        super(PopupButton, self).__init__(*args, **kwargs)
        self._createUI()

    def _createUI(self):
        self.setStyleSheet(self.button_style())
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        # self.setFocusPolicy(QtCore.Qt.NoFocus)

        self.setFixedHeight(24)
        self.setFixedWidth(120)

    @staticmethod
    def button_style():
        """Returns a style-string defining our custom button."""
        return (
            """
            QPushButton {
                text-align: left;
                border-left: 1px solid rgba(0, 0, 0, 50);
                padding-left: 10px;
                padding-right: 10px;
                border-style: solid;
                color: rgb(210, 210, 210);
                background-color: rgb(68, 68, 68);
            }
            """
        )

    @staticmethod
    def active_button_style():
        return (
        """
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
        )


class PopupCanvas(QtWidgets.QWidget):

    def __init__(self, labels, actions, origin, parent=None):
        super(PopupCanvas, self).__init__(parent=parent)

        self.animation = None
        self.origin = origin
        self._labels = labels
        self.actions = actions
        self.buttons = []

        self._createUI()

        self.setWindowOpacity(0.01)

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
        self.move_buttons()

        self.animate_opacity()
        super(PopupCanvas, self).show()
        self.raise_()
        self.activateWindow()

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

        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        for button in self._labels:
            b = PopupButton(button, parent=self)
            self.buttons.append(b)

        self.installEventFilter(self)

    def eventFilter(self, widget, event):
        cursor = QtGui.QCursor()
        pos = cursor.pos()

        if event.type() == QtCore.QEvent.MouseMove:
            self.update()
            for button in self.buttons:
                if button.geometry().contains(pos):
                    button.setStyleSheet(PopupButton.active_button_style())
                else:
                    button.setStyleSheet(PopupButton.button_style())
                    button.setStyleSheet(PopupButton.button_style())
                    button.setStyleSheet(PopupButton.button_style())
                    button.setStyleSheet(PopupButton.button_style())

        if event.type() == QtCore.QEvent.MouseButtonRelease:
            for button in self.buttons:
                if button.geometry().contains(pos):
                    button.clicked.emit()
                    self.close()

        return False

    def move_buttons(self):
        """Moves the popu-up buttons to place."""
        increment = 25.0
        angle = 0 - (increment * float(len(self.buttons))) / 2.0 + (increment / 2.0)

        for button in reversed(self.buttons):
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
        for button, action in zip(self.buttons, self.actions):
            button.clicked.connect(action)

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

    def test():
        print 'click'
    widget = PopupCanvas(('a', 'b'), (test, test), origin)
    widget.show()

    a.exec_()
