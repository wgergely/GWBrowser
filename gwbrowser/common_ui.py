# -*- coding: utf-8 -*-
"""Common ui elements.

"""
from PySide2 import QtWidgets, QtGui, QtCore
import gwbrowser.common as common
from gwbrowser.imagecache import ImageCache


def add_row(label, parent=None, padding=common.MARGIN, height=common.ROW_BUTTONS_HEIGHT, cls=None, vertical=False):
    """macro for adding a new row"""
    if cls:
        w = cls(parent=parent)
    else:
        w = QtWidgets.QWidget(parent=parent)
    if vertical:
        QtWidgets.QVBoxLayout(w)
    else:
        QtWidgets.QHBoxLayout(w)
    w.layout().setContentsMargins(0, 0, 0, 0)
    w.layout().setSpacing(common.INDICATOR_WIDTH)
    w.layout().setAlignment(QtCore.Qt.AlignCenter)

    w.setSizePolicy(
        QtWidgets.QSizePolicy.Expanding,
        QtWidgets.QSizePolicy.Expanding,
    )
    w.setFixedHeight(height)
    w.setAttribute(QtCore.Qt.WA_NoBackground)
    w.setAttribute(QtCore.Qt.WA_TranslucentBackground)

    if label:
        l = PaintedLabel(label, size=common.SMALL_FONT_SIZE,
                         color=common.SECONDARY_TEXT, parent=parent)
        l.setFixedWidth(120)
        l.setDisabled(True)
        if padding:
            w.layout().addSpacing(padding)
        w.layout().addWidget(l, 0)

    if parent:
        parent.layout().addWidget(w, 1)

    return w


def add_label(text, parent=None):
    label = QtWidgets.QLabel(text, parent=parent)
    label.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
    label.setSizePolicy(
        QtWidgets.QSizePolicy.Expanding,
        QtWidgets.QSizePolicy.Expanding
    )
    label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
    parent.layout().addWidget(label, 0)


def add_line_edit(label, parent=None):
    w = QtWidgets.QLineEdit(parent=parent)
    w.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
    w.setPlaceholderText(label)
    parent.layout().addWidget(w, 1)
    return w


class PaintedButton(QtWidgets.QPushButton):
    """Custom button class for used for the Ok and Cancel buttons."""

    def __init__(self, text, width=None, parent=None):
        super(PaintedButton, self).__init__(text, parent=parent)
        if width:
            self.setFixedWidth(width)

    def paintEvent(self, event):
        """Paint event for smooth font display."""
        painter = QtGui.QPainter()
        painter.begin(self)

        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        pressed = option.state & QtWidgets.QStyle.State_Sunken

        color = common.TEXT if self.isEnabled() else common.SECONDARY_TEXT
        color = common.TEXT_SELECTED if hover else color

        bg_color = common.SECONDARY_TEXT if self.isEnabled() else QtGui.QColor(0, 0, 0, 20)
        bg_color = common.TEXT if hover else bg_color
        bg_color = common.SEPARATOR if pressed else bg_color

        painter.setBrush(bg_color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 2, 2)

        rect = QtCore.QRect(self.rect())
        center = rect.center()
        rect.setWidth(rect.width() - (common.INDICATOR_WIDTH * 2))
        rect.moveCenter(center)
        common.draw_aliased_text(
            painter,
            common.PrimaryFont,
            rect,
            self.text(),
            QtCore.Qt.AlignCenter,
            color
        )

        painter.end()


class PaintedLabel(QtWidgets.QLabel):
    """Used for static informative text."""

    def __init__(self, text, color=common.TEXT, size=common.MEDIUM_FONT_SIZE, parent=None):
        super(PaintedLabel, self).__init__(text, parent=parent)
        self._font = QtGui.QFont(common.PrimaryFont)
        self._font.setPointSizeF(size)
        self._color = color
        metrics = QtGui.QFontMetrics(self._font)
        self.setFixedHeight(metrics.height())
        self.setFixedWidth(metrics.width(text) + 2)

    def paintEvent(self, event):
        """Custom paint event to use the aliased paint method."""
        painter = QtGui.QPainter()
        painter.begin(self)
        common.draw_aliased_text(
            painter, self._font, self.rect(), self.text(), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, self._color)
        painter.end()


class ClickableIconButton(QtWidgets.QLabel):
    """A generic icon button used accross the project.

    """
    clicked = QtCore.Signal()
    doubleClicked = QtCore.Signal()
    message = QtCore.Signal(unicode)

    def __init__(self, pixmap, colors, size, description=u'', parent=None):
        super(ClickableIconButton, self).__init__(parent=parent)

        self._pixmap = pixmap
        self._size = size

        on, off = colors
        self._on_color = on
        self._off_color = off

        self.setStatusTip(description)
        self.setToolTip(description)
        self.setFixedSize(QtCore.QSize(size, size))
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setAttribute(QtCore.Qt.WA_NoBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.clicked.connect(self.action)
        self.clicked.connect(self.update)

    @QtCore.Slot()
    def action(self):
        pass

    def mouseReleaseEvent(self, event):
        """Only triggered when the left buttons is pressed."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()

    def mouseDoubleClickEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.doubleClicked.emit()

    def enterEvent(self, event):
        self.message.emit(self.statusTip())
        self.update()

    def leaveEvent(self, event):
        self.update()

    def pixmap(self):
        if not self.isEnabled():
            return ImageCache.get_rsc_pixmap(self._pixmap, self._off_color, self._size)
        if self.state():
            return ImageCache.get_rsc_pixmap(self._pixmap, self._on_color, self._size)
        return ImageCache.get_rsc_pixmap(self._pixmap, self._off_color, self._size)

    def state(self):
        return False

    def contextMenuEvent(self, event):
        pass

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter = QtGui.QPainter()
        painter.begin(self)

        if hover:
            painter.setOpacity(1.0)
        else:
            painter.setOpacity(0.80)

        pixmap = self.pixmap()
        painter.drawPixmap(self.rect(), pixmap, pixmap.rect())
        painter.end()
