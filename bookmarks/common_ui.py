# -*- coding: utf-8 -*-
"""Common ui elements.

"""
from PySide2 import QtWidgets, QtGui, QtCore
import bookmarks.common as common
import bookmarks.images as images


def get_group(parent=None):
    o = common.INDICATOR_WIDTH
    grp = QtWidgets.QGroupBox(parent=parent)
    QtWidgets.QVBoxLayout(grp)
    grp.layout().setContentsMargins(o, o, o, o)
    grp.layout().setSpacing(o)
    parent.layout().addWidget(grp, 1)
    return grp


class NameBase(QtWidgets.QLineEdit):
    def __init__(self, parent=None, transparent=False):
        super(NameBase, self).__init__(parent=parent)
        if transparent:
            self.set_transparent()

    def set_transparent(self, color=None):
        self.setStyleSheet(
            """
QLineEdit{{
    background-color: rgba(0,0,0,0);
    font-family: "{fontFamily}";
    font-size: {fontSize}pt;
    border-bottom: 2px solid rgba(0,0,0,50);
    border-radius: 0px;
    color: rgba({color});
}}
QLineEdit:!read-only:focus{{
    border-bottom: 2px solid rgba({favourite});
}}
            """.format(
                fontFamily=common.font_db.secondary_font().family(),
                fontSize=common.psize(common.MEDIUM_FONT_SIZE),
                favourite=common.rgb(common.FAVOURITE),
                color='255,255,255,255' if not color else color
            )
        )


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
    common.set_custom_stylesheet(w)
    w.layout().setContentsMargins(0, 0, 0, 0)
    w.layout().setSpacing(common.INDICATOR_WIDTH)
    w.layout().setAlignment(QtCore.Qt.AlignCenter)

    w.setSizePolicy(
        QtWidgets.QSizePolicy.Expanding,
        QtWidgets.QSizePolicy.Expanding,
    )
    if height:
        w.setFixedHeight(height)
    w.setAttribute(QtCore.Qt.WA_NoBackground)
    w.setAttribute(QtCore.Qt.WA_TranslucentBackground)

    if label:
        l = PaintedLabel(label, size=common.SMALL_FONT_SIZE,
                         color=common.SECONDARY_TEXT, parent=parent)
        common.set_custom_stylesheet(l)
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
    common.set_custom_stylesheet(label)
    label.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
    label.setSizePolicy(
        QtWidgets.QSizePolicy.Expanding,
        QtWidgets.QSizePolicy.Expanding
    )
    label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
    parent.layout().addWidget(label, 0)


def add_line_edit(label, parent=None):
    w = NameBase(transparent=True, parent=parent)
    common.set_custom_stylesheet(w)
    w.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
    w.setPlaceholderText(label)
    parent.layout().addWidget(w, 1)
    return w


def add_description(text, label=u' ', padding=common.MARGIN, parent=None):
    row = add_row(label, padding=padding, height=None, parent=parent)
    label = QtWidgets.QLabel(text, parent=parent)
    common.set_custom_stylesheet(label)
    label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
    label.setStyleSheet(
        u'color: rgba({}); font-family: "{}";'.format(
            common.rgb(common.SECONDARY_TEXT),
            common.font_db.secondary_font().family()
        )
    )
    label.setWordWrap(True)
    row.layout().addWidget(label, 1)
    parent.layout().addWidget(row)


class PaintedButton(QtWidgets.QPushButton):
    """Custom button class for used for the Ok and Cancel buttons."""

    def __init__(self, text, width=None, parent=None):
        super(PaintedButton, self).__init__(text, parent=parent)
        self.setFixedHeight(24.0)
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
        focus = option.state & QtWidgets.QStyle.State_HasFocus

        color = common.TEXT if self.isEnabled() else common.SECONDARY_TEXT
        color = common.TEXT_SELECTED if hover else color

        bg_color = common.SECONDARY_TEXT if self.isEnabled(
        ) else common.SECONDARY_BACKGROUND.darker(110)
        bg_color = common.TEXT if hover else bg_color
        bg_color = common.SEPARATOR if pressed else bg_color

        if focus:
            pen = QtGui.QPen(common.FAVOURITE)
        else:
            pen = QtGui.QPen(bg_color)
            pen.setWidthF(1.0)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(bg_color)
        painter.setPen(pen)
        rect = self.rect().marginsRemoved(QtCore.QMargins(1, 1, 1, 1))
        painter.drawRoundedRect(rect, 2, 2)

        rect = QtCore.QRect(self.rect())
        center = rect.center()
        rect.setWidth(rect.width() - (common.INDICATOR_WIDTH * 2))
        rect.moveCenter(center)
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(),
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
        self._font = common.font_db.primary_font(point_size=size)
        self._color = color
        metrics = QtGui.QFontMetricsF(self._font)
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
    """A utility class for creating a square icon button.

    Args:
        pixmap (unicode): The name of the resource file without the extension.
        colors (tuple(QColor, QColor)): A tuple of QColors, for enabled and disabled states.
        size (int): The value for width and height.
        description (unicode): A user readable description of the action the button performs.
        parent (QObject): The widget's parent.

    Signals:
        clicked (QtCore.Signal()):
        doubleClicked (QtCore.Signal()):
        message (QtCore.Signal(unicode)):

    Returns:
        type: Description of returned object.

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
            return images.ImageCache.get_rsc_pixmap(self._pixmap, self._off_color, self._size)
        if self.state():
            return images.ImageCache.get_rsc_pixmap(self._pixmap, self._on_color, self._size)
        return images.ImageCache.get_rsc_pixmap(self._pixmap, self._off_color, self._size)

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


class MessageBox(QtWidgets.QDialog):
    primary_color = QtGui.QColor(50, 50, 190, 255)
    secondary_color = common.FAVOURITE
    icon = u'icon_bw'

    def __init__(self, short_text, long_text, parent=None):
        super(MessageBox, self).__init__(parent=parent)

        self.setWindowTitle(u'[{}]: Error'.format(common.PRODUCT))

        self.short_text_label = QtWidgets.QLabel(short_text, parent=self)
        self.short_text_label.setWordWrap(True)
        self.long_text_label = QtWidgets.QLabel(long_text, parent=self)
        self.long_text_label.setWordWrap(True)

        common.set_custom_stylesheet(self)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setWindowFlags(
            QtCore.Qt.Dialog |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.NoDropShadowWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.installEventFilter(self)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred
        )
        self._createUI()

        self.setStyleSheet("""
            QWidget {{
                color: rgba({TEXT});
                background-color: rgba({BG});
                font-family: "{FAMILY}";
            }}
            """.format(
            SIZE=common.LARGE_FONT_SIZE,
            FAMILY=common.font_db.primary_font().family(),
            TEXT=common.rgb(self.secondary_color.darker(150)),
            BG=common.rgb(self.secondary_color)))

        self.ok_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))

    def _createUI(self):
        def get_row(vertical=False, parent=None):
            row = QtWidgets.QWidget(parent=parent)
            if vertical:
                QtWidgets.QVBoxLayout(row)
            else:
                QtWidgets.QHBoxLayout(row)
            row.layout().setContentsMargins(0, 0, 0, 0)
            row.layout().setSpacing(0)
            row.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding,
            )
            parent.layout().addWidget(row)
            return row

        QtWidgets.QHBoxLayout(self)
        o = 0
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        main_row = get_row(parent=self)
        main_row.layout().setContentsMargins(0, 0, 0, 0)
        main_row.layout().setSpacing(0)

        columns = get_row(vertical=True, parent=main_row)
        columns.layout().setContentsMargins(0, 0, 0, 0)
        columns.layout().setSpacing(0)

        short_text_row = get_row(parent=columns)

        columns.layout().addWidget(short_text_row, 1)
        long_text_row = get_row(parent=columns)

        pixmap = images.ImageCache.get_rsc_pixmap(
            self.icon, self.secondary_color.lighter(150), common.ROW_HEIGHT)
        label = QtWidgets.QLabel(parent=self)
        label.setPixmap(pixmap)
        label.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding,
        )
        label.setStyleSheet(
            u'padding:10px;background-color: rgba({});'.format(common.rgb(self.primary_color)))

        main_row.layout().insertWidget(0, label)

        short_text_row.layout().addWidget(self.short_text_label)
        self.short_text_label.setStyleSheet(
            u'padding:20px 10px 20px 10px; background-color: rgba({}); font-size:{}pt'.format(
                common.rgb(self.secondary_color.lighter(125)),
                common.psize(common.MEDIUM_FONT_SIZE)
            ))
        self.short_text_label.setAlignment(QtCore.Qt.AlignLeft)

        long_text_row.layout().addWidget(self.long_text_label)
        self.long_text_label.setStyleSheet(
            u'padding:10px;background-color: rgba({}); font-size:{}pt'.format(
            common.rgb(self.secondary_color),
            common.psize(common.SMALL_FONT_SIZE)
        ))
        self.long_text_label.setAlignment(QtCore.Qt.AlignLeft)

        buttons_row = get_row(parent=columns)
        buttons_row.setStyleSheet(
            u'background-color: rgba({});'.format(common.rgb(self.secondary_color)))
        self.ok_button = QtWidgets.QPushButton('Ok', parent=self)
        buttons_row.layout().addWidget(self.ok_button)

        self.ok_button.setStyleSheet(
            """
        QPushButton {{
            color: rgba(255,255,255,150);
            border-radius: 3px;
            border: 1px solid {};
            margin:5px;
            padding:5px;
            background-color: rgba({});
        }}
        QPushButton:hover {{
            color: white;
            background-color: rgba({});
        }}
        QPushButton:pressed {{
            color: rgba(255,255,255,150);
            background-color: rgba({});
        }}
        """.format(
                common.rgb(self.secondary_color.lighter(150)),
                common.rgb(self.primary_color),
                common.rgb(self.primary_color.lighter(120)),
                common.rgb(self.primary_color.darker(120))
            )
        )

    def sizeHint(self):
        return QtCore.QSize(420, 200)

    def eventFilter(self, widget, event):
        if widget != self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(self.secondary_color)
            o = common.MARGIN * 0.5
            painter.drawRect(self.rect())
            painter.end()
            return True
        return False


class ErrorBox(MessageBox):
    primary_color = QtGui.QColor(190, 50, 50, 255)
    secondary_color = common.REMOVE
    icon = u'close'

    def __init__(self, *args, **kwargs):
        super(ErrorBox, self).__init__(*args, **kwargs)


class OkBox(MessageBox):
    primary_color = QtGui.QColor(70, 160, 100, 255)
    secondary_color = QtGui.QColor(70, 180, 130, 255)  # 90, 200, 155)
    icon = u'check'

    def __init__(self, *args, **kwargs):
        super(OkBox, self).__init__(*args, **kwargs)
