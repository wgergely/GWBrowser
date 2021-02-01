# -*- coding: utf-8 -*-
"""Common UI methods used accross the product.

"""
import base64
from PySide2 import QtWidgets, QtGui, QtCore

from . import common
from . import images
from . import bookmark_db
from .lists import delegate


_message_instance = None




MESSAGE_BOX_STYLESHEET = """
QWidget {{
    color: rgba({TEXT});
    background-color: rgba(0,0,0,0);
    font-family: "{FAMILY}";
    font-size: {SIZE}px;
}}"""

PUSH_BUTTON_STYLESHEET = """
QPushButton {{
    font-size: {px}px;
    color: rgba(255,255,255,220);
    border-radius: {i}px;
    margin: {i}px;
    padding: {i}px;
    background-color: rgba({p});
}}
QPushButton:hover {{
    color: rgba(255,255,255,230);
    background-color: rgba({pl});
}}
QPushButton:pressed {{
    color: rgba(255,255,255,180);
    background-color: rgba({pd});
}}"""


OkButton = u'Ok'
CancelButton = u'Cancel'
YesButton = u'Yes'
NoButton = u'No'
SaveButton = u'Save'

buttons = (
    OkButton,
    CancelButton,
    YesButton,
    NoButton,
    SaveButton,
)


def get_group(parent=None, vertical=True, margin=common.MARGIN()):
    """Utility method for creating a group widget.

    Returns:
        QGroupBox: group widget.

    """
    grp = QtWidgets.QGroupBox(parent=parent)
    grp.setMinimumWidth(common.WIDTH() * 0.3)
    grp.setMaximumWidth(common.WIDTH() * 2.0)

    if vertical:
        QtWidgets.QVBoxLayout(grp)
    else:
        QtWidgets.QHBoxLayout(grp)

    grp.setSizePolicy(
        QtWidgets.QSizePolicy.Minimum,
        QtWidgets.QSizePolicy.Maximum,
    )

    grp.layout().setContentsMargins(margin, margin, margin, margin)
    grp.layout().setSpacing(margin * 0.5)
    parent.layout().addWidget(grp, 1)

    return grp


def add_row(label, color=common.SECONDARY_TEXT, parent=None, padding=common.MARGIN(), height=common.ROW_HEIGHT(), cls=None, vertical=False):
    """Utility method for creating a row widget.

    Returns:
        QWidget:    The newly created row.

    """
    if cls:
        w = cls(parent=parent)
    else:
        w = QtWidgets.QWidget(parent=parent)

    if vertical:
        QtWidgets.QVBoxLayout(w)
    else:
        QtWidgets.QHBoxLayout(w)

    w.layout().setContentsMargins(0, 0, 0, 0)
    w.layout().setSpacing(common.INDICATOR_WIDTH())
    w.layout().setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

    w.setSizePolicy(
        QtWidgets.QSizePolicy.Expanding,
        QtWidgets.QSizePolicy.Expanding,
    )
    if height:
        w.setFixedHeight(height)

    w.setAttribute(QtCore.Qt.WA_NoBackground)
    w.setAttribute(QtCore.Qt.WA_TranslucentBackground)

    if label:
        l = PaintedLabel(
            label,
            size=common.SMALL_FONT_SIZE(),
            color=color,
            parent=parent
        )
        l.setFixedWidth(common.MARGIN() * 8.6667)
        w.layout().addWidget(l, 1)

    if parent:
        parent.layout().addWidget(w, 1)

    return w


def add_label(text, parent=None):
    """Utility method for creating a label.

    Returns:
        QLabel: label widget.

    """
    label = QtWidgets.QLabel(text, parent=parent)
    label.setFixedHeight(common.ROW_HEIGHT())
    label.setSizePolicy(
        QtWidgets.QSizePolicy.Expanding,
        QtWidgets.QSizePolicy.Expanding
    )
    label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
    parent.layout().addWidget(label, 0)


def add_line_edit(label, parent=None):
    """Utility method for adding a line editor.

    Returns:
        QLineEdit: line editor widget.

    """
    w = LineEdit(parent=parent)
    w.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
    w.setPlaceholderText(label)
    parent.layout().addWidget(w, 1)
    return w


class Label(QtWidgets.QLabel):
    def __init__(self, text, color=common.SECONDARY_TEXT, parent=None):
        super(Label, self).__init__(text, parent=parent)
        self.color = color
        self._color = QtGui.QColor(color)
        self._color.setAlpha(230)
        self.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignJustify)
        self.setWordWrap(True)
        self.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.setOpenExternalLinks(True)

    def _set_stylesheet(self, isEnabled):
        if not isEnabled:
            self.setStyleSheet('color: rgba({}); font-size: {}px;'.format(
                common.rgb(self._color), common.SMALL_FONT_SIZE()))
        else:
            self.setStyleSheet('color: rgba({}); font-size: {}px;'.format(
                common.rgb(self.color), common.SMALL_FONT_SIZE()))
        self.update()

    def enterEvent(self, event):
        self._set_stylesheet(True)

    def leaveEvent(self, event):
        self._set_stylesheet(False)

    def showEvent(self, event):
        self._set_stylesheet(False)


def add_description(text, label=u' ', color=common.SECONDARY_TEXT, padding=common.MARGIN(), parent=None):
    """Utility method for adding a description field.

    Returns:
        QLabel: the added QLabel.

    """
    row = add_row(label, padding=padding, height=None, parent=parent)
    row.layout().setSpacing(0)

    label = Label(text, color=color, parent=parent)
    row.layout().addWidget(label, 1)
    parent.layout().addWidget(row, 1)
    return row


class LineEdit(QtWidgets.QLineEdit):
    """Custom line edit widget with a single underline."""

    def __init__(self, parent=None):
        super(LineEdit, self).__init__(parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        self.setAlignment(QtCore.Qt.AlignLeft)


class PaintedButton(QtWidgets.QPushButton):
    """Custom button class."""

    def __init__(self, text, height=common.ROW_HEIGHT(), width=None, parent=None):
        super(PaintedButton, self).__init__(text, parent=parent)
        self.setFixedHeight(height)
        if width:
            self.setFixedWidth(width)

    def paintEvent(self, event):
        """Paint event for smooth font display."""
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        option = QtWidgets.QStyleOption()
        option.initFrom(self)

        hover = option.state & QtWidgets.QStyle.State_MouseOver
        pressed = option.state & QtWidgets.QStyle.State_Sunken
        focus = option.state & QtWidgets.QStyle.State_HasFocus
        disabled = not self.isEnabled()

        o = 1.0 if hover else 0.8
        o = 0.3 if disabled else o
        painter.setOpacity(o)

        painter.setBrush(common.SECONDARY_BACKGROUND)
        _color = QtGui.QColor(common.SEPARATOR)
        _color.setAlpha(150)
        pen = QtGui.QPen(_color)
        pen.setWidthF(common.ROW_SEPARATOR())
        painter.setPen(pen)

        o = common.ROW_SEPARATOR()
        rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))

        o = common.INDICATOR_WIDTH() * 1.5
        painter.drawRoundedRect(rect, o, o)

        if focus:
            painter.setBrush(QtCore.Qt.NoBrush)
            pen = QtGui.QPen(common.FAVOURITE)
            pen.setWidthF(common.ROW_SEPARATOR())
            painter.setPen(pen)
            painter.drawRoundedRect(rect, o, o)

        rect = QtCore.QRect(self.rect())
        center = rect.center()
        rect.setWidth(rect.width() - (common.INDICATOR_WIDTH() * 2))
        rect.moveCenter(center)

        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(common.MEDIUM_FONT_SIZE())[0],
            rect,
            self.text(),
            QtCore.Qt.AlignCenter,
            common.TEXT
        )

        painter.end()


class PaintedLabel(QtWidgets.QLabel):
    """QLabel used for static aliased label."""

    def __init__(self, text, color=common.TEXT, size=common.MEDIUM_FONT_SIZE(), parent=None):
        super(PaintedLabel, self).__init__(text, parent=parent)
        self._size = size
        self._color = color
        self._text = text
        self.update_size()

    def update_size(self):
        font, metrics = common.font_db.primary_font(font_size=self._size)
        self.setFixedHeight(metrics.height())
        self.setFixedWidth(metrics.width(self._text) +
                           common.INDICATOR_WIDTH() * 2)

    def paintEvent(self, event):
        """Custom paint event to use the aliased paint method."""
        option = QtWidgets.QStyleOption()
        option.initFrom(self)

        painter = QtGui.QPainter()
        painter.begin(self)

        hover = option.state & QtWidgets.QStyle.State_MouseOver
        pressed = option.state & QtWidgets.QStyle.State_Sunken
        focus = option.state & QtWidgets.QStyle.State_HasFocus
        disabled = not self.isEnabled()

        o = 1.0 if hover else 0.8
        o = 0.3 if disabled else 1.0
        painter.setOpacity(o)

        rect = self.rect()
        rect.setLeft(rect.left() + common.INDICATOR_WIDTH())
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(font_size=self._size)[0],
            self.rect(),
            self.text(),
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            self._color
        )
        painter.end()

    def leaveEvent(self, event):
        self.update()

    def enterEvent(self, event):
        self.update()


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

        self._on_color = colors[0]
        self._off_color = colors[1]

        self.setStatusTip(description)
        self.setToolTip(description)
        self.setWhatsThis(description)

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

        if not self.state():
            painter.setOpacity(0.5)
        elif hover:
            painter.setOpacity(1.0)
        else:
            painter.setOpacity(0.80)

        pixmap = self.pixmap()
        painter.drawPixmap(self.rect(), pixmap, pixmap.rect())
        painter.end()


class MessageBox(QtWidgets.QDialog):
    """Informative message box used for notifying the user of an event.

    """
    primary_color = QtGui.QColor(50, 50, 190, 180)
    secondary_color = common.FAVOURITE.lighter(120)
    icon = u'icon_bw'

    okButtonClicked = QtCore.Signal()
    yesButtonClicked = QtCore.Signal()
    saveButtonClicked = QtCore.Signal()

    noButtonClicked = QtCore.Signal()
    cancelButtonClicked = QtCore.Signal()

    def __init__(self, *args, **kwargs):

        global _message_instance
        if _message_instance is not None:
            try:
                _message_instance.close()
                _message_instance.deleteLater()
            except:
                pass
            finally:
                _message_instance = None
        _message_instance = self

        if 'parent' in kwargs:
            parent = kwargs['parent']
        else:
            parent = None

        super(MessageBox, self).__init__(parent=parent)

        if parent is None:
            common.set_custom_stylesheet(self)

        # labels
        self.no_buttons = False
        self.buttons = []
        self.primary_label = None
        self.secondary_label = None

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

        self.set_labels(args)
        self.set_buttons(kwargs)

        self._create_ui()
        self._connect_signals()

    def _get_label(self, parent=None, size=common.SMALL_FONT_SIZE()):
        label = QtWidgets.QLabel(parent=parent)
        label.setOpenExternalLinks(True)
        label.setTextFormat(QtCore.Qt.RichText)
        label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse |
            QtCore.Qt.TextSelectableByKeyboard |
            QtCore.Qt.LinksAccessibleByMouse |
            QtCore.Qt.LinksAccessibleByKeyboard
        )
        label.setStyleSheet('padding: 0px;')
        label.setMargin(0)
        label.setIndent(0)
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        label.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        label.setMinimumWidth(common.WIDTH() * 0.66)
        label.setMaximumWidth(common.WIDTH())
        label.setStyleSheet(u'font-size: {}px;'.format(size))
        return label

    def _get_row(self, vertical=False, parent=None):
        row = QtWidgets.QWidget(parent=parent)
        if vertical:
            QtWidgets.QVBoxLayout(row)
        else:
            QtWidgets.QHBoxLayout(row)
        row.layout().setAlignment(QtCore.Qt.AlignCenter)
        row.layout().setContentsMargins(0, 0, 0, 0)
        row.layout().setSpacing(0)
        parent.layout().addWidget(row, 1)
        return row

    def _create_ui(self):
        stylesheet = MESSAGE_BOX_STYLESHEET.format(
            SIZE=common.LARGE_FONT_SIZE(),
            FAMILY=common.font_db.primary_font(
                common.MEDIUM_FONT_SIZE())[0].family(),
            TEXT=common.rgb(self.secondary_color.darker(255))
        )
        self.setStyleSheet(stylesheet)

        QtWidgets.QHBoxLayout(self)
        o = common.MARGIN()
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        # Main Row
        main_row = self._get_row(parent=self)
        main_row.layout().setSpacing(o)

        label = self._get_label(parent=main_row)
        pixmap = images.ImageCache.get_rsc_pixmap(
            self.icon, self.secondary_color.lighter(150), common.ROW_HEIGHT())
        label.setPixmap(pixmap)
        label.setFixedWidth(common.ROW_HEIGHT())
        label.setFixedHeight(common.ROW_HEIGHT())
        main_row.layout().addWidget(label, 0)

        # Labels and buttons
        columns = self._get_row(vertical=True, parent=main_row)
        columns.layout().setSpacing(o)

        primary_row = self._get_row(parent=columns)
        columns.layout().addWidget(primary_row, 1)

        if self.primary_label:
            primary_row.layout().addWidget(self.primary_label)

        if self.secondary_label:
            secondary_row = self._get_row(parent=columns)
            secondary_row.layout().addWidget(self.secondary_label)

        if self.no_buttons is True:
            return

        if self.buttons:
            buttons_row = self._get_row(parent=columns)
            for idx, button in enumerate(self.buttons):
                if idx == 0:
                    buttons_row.layout().addWidget(button, 2)
                else:
                    buttons_row.layout().addWidget(button, 1)

    def _connect_signals(self):
        self.okButtonClicked.connect(lambda: self.done(QtWidgets.QDialog.Accepted))
        self.yesButtonClicked.connect(lambda: self.done(QtWidgets.QDialog.Accepted))
        self.saveButtonClicked.connect(lambda: self.done(QtWidgets.QDialog.Accepted))

        self.noButtonClicked.connect(lambda: self.done(QtWidgets.QDialog.Rejected))
        self.cancelButtonClicked.connect(lambda: self.done(QtWidgets.QDialog.Rejected))

        for button in buttons:
            k = button.lower() + '_button'
            _k = button.lower() + 'ButtonClicked'
            if hasattr(self, k) and hasattr(self, _k):
                getattr(self, k).clicked.connect(getattr(self, _k))

    def set_labels(self, args):
        if len(args) >= 1 and isinstance(args[0], unicode):
            self.primary_label = self._get_label(parent=self, size=common.LARGE_FONT_SIZE())
            self.primary_label.setText(args[0])
        else:
            raise ValueError(u'Primary Label must be {}'.format(unicode))
        if len(args) >= 2:
            self.secondary_label = self._get_label(parent=self)
            self.secondary_label.setText(args[1])
            self.secondary_label.setTextFormat(QtCore.Qt.PlainText)

    def set_buttons(self, kwargs):
        if 'no_buttons' in kwargs and kwargs['no_buttons'] is True:
            self.no_buttons = kwargs['no_buttons']
            self.buttons = []
            return

        color = QtGui.QColor(self.primary_color)
        color.setAlphaF(0.5)

        stylesheet = PUSH_BUTTON_STYLESHEET.format(
            px=common.SMALL_FONT_SIZE(),
            i=common.INDICATOR_WIDTH(),
            s=common.ROW_SEPARATOR(),
            c=common.rgb(self.secondary_color.lighter(150)),
            p=common.rgb(color),
            pl=common.rgb(self.primary_color.lighter(120)),
            pd=common.rgb(self.primary_color.darker(120))
        )
        if 'buttons' in kwargs and isinstance(kwargs['buttons'], (tuple, list)) and kwargs['buttons']:
            for k in kwargs['buttons']:
                if k not in buttons:
                    raise ValueError('{} is an invalid button'.format(k))
                button = QtWidgets.QPushButton(k, parent=self)
                button.setStyleSheet(stylesheet)
                button.setFixedHeight(common.ROW_HEIGHT())
                self.buttons.append(button)
                setattr(self, k.lower() + '_button', button)
            return

        button = QtWidgets.QPushButton(OkButton, parent=self)
        button.setStyleSheet(stylesheet)
        self.buttons = [button, ]
        setattr(self, OkButton.lower() + '_button', button)

    def sizeHint(self):
        return QtCore.QSize(common.HEIGHT(), common.HEIGHT() * 0.5)

    def eventFilter(self, widget, event):
        if widget != self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            c = QtGui.QColor(self.secondary_color).darker(250)
            # c.setAlpha(255)
            pen = QtGui.QPen(c)
            o = common.INDICATOR_WIDTH()
            pen.setWidth(o * .66)
            painter.setPen(pen)
            painter.setBrush(self.secondary_color)
            painter.drawRoundedRect(self.rect().adjusted(o, o, -o, -o), o, o)
            painter.end()
            return True
        return False


class ErrorBox(MessageBox):
    """Informative message box used for notifying the user of an error.

    """
    primary_color = QtGui.QColor(190, 50, 50, 180)
    secondary_color = common.REMOVE
    icon = u'close'


class OkBox(MessageBox):
    """Informative message box used for notifying the user of success.

    """
    primary_color = QtGui.QColor(80, 150, 100, 180)
    secondary_color = QtGui.QColor(110, 190, 160, 255)  # 90, 200, 155)
    icon = u'check'
