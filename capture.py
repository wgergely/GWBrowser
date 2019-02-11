# -*- coding: utf-8 -*-
"""A modal widget to capture a section of the screen.

The ScreenGrabber code has been borrowed from the Shotgun Github page, hence I don't
own any of that code. Although, I have modified it to make it work with PySide2, and
removed the platform-specific capture options. Also, the capture functions have been
moved inside the ScreenGrabber class as static and class methods.

Example:

.. code-block:: python
    :linenos:

    ScreenGrabber.screen_capture_file(output_path='C:/temp/screengrab.png')


"""
# pylint: disable=E1101, C0103, R0913, I1101
import tempfile
from PySide2 import QtCore, QtWidgets, QtGui


class ScreenGrabber(QtWidgets.QDialog):
    """
    A transparent tool dialog for selecting an area (QRect) on the screen.

    This tool does not by itself perform a screen capture. The resulting
    capture rect can be used (e.g. with the ScreenGrabber.get_desktop_pixmap function) to
    save the selected portion of the screen into a pixmap.
    """

    def __init__(self, parent=None):
        super(ScreenGrabber, self).__init__(parent=parent)

        self._opacity = 1
        self._click_pos = None
        self._offset_pos = None

        self._capture_rect = QtCore.QRect()

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
            # QtCore.Qt.CustomizeWindowHint |
            # QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setCursor(QtCore.Qt.CrossCursor)
        self.setMouseTracking(True)
        self.installEventFilter(self)

        app = QtCore.QCoreApplication.instance()
        app.desktop().resized.connect(self._fit_screen_geometry)
        app.desktop().screenCountChanged.connect(self._fit_screen_geometry)

    @property
    def capture_rect(self):
        """The resulting QRect from a previous capture operation."""
        return self._capture_rect

    def paintEvent(self, event):
        """
        Paint event.
        """
        # Convert click and current mouse positions to local space.
        mouse_pos = self.mapFromGlobal(QtGui.QCursor.pos())
        click_pos = None
        if self._click_pos is not None:
            click_pos = self.mapFromGlobal(self._click_pos)

        painter = QtGui.QPainter()
        painter.begin(self)

        # Draw background. Aside from aesthetics, this makes the full
        # tool region accept mouse events.
        painter.setBrush(QtGui.QColor(0, 0, 0, self._opacity))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(event.rect())

        # Clear the capture area
        if click_pos is not None:
            capture_rect = QtCore.QRect(click_pos, mouse_pos)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
            painter.drawRect(capture_rect)
            painter.setCompositionMode(
                QtGui.QPainter.CompositionMode_SourceOver)

        pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 64), 1, QtCore.Qt.DotLine)
        painter.setPen(pen)

        # Draw cropping markers at click position
        if click_pos is not None:
            painter.drawLine(event.rect().left(), click_pos.y(),
                             event.rect().right(), click_pos.y())
            painter.drawLine(click_pos.x(), event.rect().top(),
                             click_pos.x(), event.rect().bottom())

        # Draw cropping markers at current mouse position
        painter.drawLine(event.rect().left(), mouse_pos.y(),
                         event.rect().right(), mouse_pos.y())
        painter.drawLine(mouse_pos.x(), event.rect().top(),
                         mouse_pos.x(), event.rect().bottom())

        painter.end()

    def keyPressEvent(self, event):
        """
        Key press event
        """
        if event.key() == QtCore.Qt.Key_Escape:
            self.reject()

    def mousePressEvent(self, event):
        """
        Mouse click event
        """
        if event.button() == QtCore.Qt.LeftButton:
            # Begin click drag operation
            self._click_pos = event.globalPos()
        if event.button() == QtCore.Qt.RightButton:
            # Cancel capture
            self.reject()

    def mouseReleaseEvent(self, event):
        """
        Mouse release event
        """
        if event.button() == QtCore.Qt.LeftButton and self._click_pos is not None:
            # End click drag operation and commit the current capture rect
            self._capture_rect = QtCore.QRect(
                self._click_pos,
                event.globalPos()
            ).normalized()
            self._click_pos = None
            self._offset_pos = None

        self.accept()

    def mouseMoveEvent(self, event):
        """
        Mouse move event
        """

        app = QtGui.QGuiApplication.instance()
        modifiers = app.queryKeyboardModifiers()

        no_modifier = modifiers == QtCore.Qt.NoModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier
        control_modifier = modifiers & QtCore.Qt.ControlModifier
        alt_modifier = modifiers & QtCore.Qt.AltModifier

        if no_modifier:
            self.__click_pos = None
            self._offset_pos = None
            self.repaint()
            return

        if not self._click_pos:
            return

        # Allowing the shifting of the rectagle with the modifier keys
        if (shift_modifier and (control_modifier or alt_modifier)) or control_modifier or alt_modifier:
            if not self._offset_pos:
                self.__click_pos = QtCore.QPoint(self._click_pos)
                self._offset_pos = QtCore.QPoint(event.globalPos())

            cursor_pos = QtGui.QCursor().pos()
            self._click_pos = QtCore.QPoint(
                self.__click_pos.x() - (self._offset_pos.x() - event.globalPos().x()),
                self.__click_pos.y() - (self._offset_pos.y() - event.globalPos().y())
            )
            self.repaint()

        # Shift constrains the rectangle to a square
        if shift_modifier:
            cursor = QtGui.QCursor()
            rect = QtCore.QRect()
            rect.setTopLeft(self._click_pos)
            rect.setBottomRight(event.globalPos())
            rect.setHeight(rect.width())

            cursor.setPos(rect.bottomRight())

            self.repaint()

    @classmethod
    def screen_capture(cls):
        """
        Modally displays the screen capture tool.

        :returns: Captured screen
        :rtype: :class:`~PySide.QtGui.QPixmap`
        """
        tool = cls()
        if tool.exec_():
            return cls.get_desktop_pixmap(tool.capture_rect)
        return None

    def showEvent(self, event):
        """
        Show event
        """
        self._fit_screen_geometry()
        # Start fade in animation
        fade_anim = QtCore.QPropertyAnimation(self, "_opacity_anim_prop", self)
        fade_anim.setStartValue(self._opacity)
        fade_anim.setEndValue(127)
        fade_anim.setDuration(300)
        fade_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        fade_anim.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def _set_opacity(self, value):
        """
        Animation callback for opacity
        """
        self._opacity = value
        self.repaint()

    def _get_opacity(self):
        """
        Animation callback for opacity
        """
        return self._opacity

    _opacity_anim_prop = QtCore.Property(int, _get_opacity, _set_opacity)

    def _fit_screen_geometry(self):
        # Compute the union of all screen geometries, and resize to fit.
        app = QtCore.QCoreApplication.instance()
        workspace_rect = QtCore.QRect()
        for i in range(app.desktop().screenCount()):
            workspace_rect = workspace_rect.united(
                app.desktop().screenGeometry(i))
        self.setGeometry(workspace_rect)

    @classmethod
    def get_desktop_pixmap(cls, rect):
        """
        Performs a screen capture on the specified rectangle.

        :param rect: Rectangle to capture
        :type rect: :class:`~PySide.QtCore.QRect`
        :returns: Captured image
        :rtype: :class:`~PySide.QtGui.QPixmap`
        """
        app = QtCore.QCoreApplication.instance()
        return QtGui.QPixmap.grabWindow(
            app.desktop().winId(),
            rect.x(),
            rect.y(),
            rect.width(),
            rect.height()
        )

    @classmethod
    def capture(cls, output_path=None):
        """
        Modally display the screen capture tool, saving to a file or if no file
        is specified returns the captured pixmap.
        """
        pixmap = cls.screen_capture()

        if not pixmap:
            return None

        if not output_path:
            return pixmap

        pixmap.save(output_path)
        return output_path
