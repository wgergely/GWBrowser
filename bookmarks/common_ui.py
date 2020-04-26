# -*- coding: utf-8 -*-
"""Common UI methods used accross the product.

Copyright (C) 2020 Gergely Wootsch

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <https://www.gnu.org/licenses/>.

"""
from PySide2 import QtWidgets, QtGui, QtCore

import bookmarks.common as common
import bookmarks.images as images
import bookmarks.bookmark_db as bookmark_db
import bookmarks.delegate as delegate


_message_box_instance = None


def get_group(parent=None):
    """Utility method for creating a group widget.

    Returns:
        QGroupBox: group widget.

    """
    grp = QtWidgets.QGroupBox(parent=parent)
    grp.setMinimumWidth(common.WIDTH() * 0.3)
    grp.setMaximumWidth(common.WIDTH() * 2.0)

    QtWidgets.QVBoxLayout(grp)
    grp.setSizePolicy(
        QtWidgets.QSizePolicy.Minimum,
        QtWidgets.QSizePolicy.Maximum,
    )

    o = common.INDICATOR_WIDTH()
    grp.layout().setContentsMargins(o, o, o, o)
    grp.layout().setSpacing(o)
    parent.layout().addWidget(grp, 1)
    return grp


def add_row(label, parent=None, padding=common.MARGIN(), height=common.ROW_HEIGHT(), cls=None, vertical=False):
    """Utility method for creating a row widget.

    Returns:
        QWidget: row widget.

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
        l = PaintedLabel(label, size=common.SMALL_FONT_SIZE(),
                         color=common.SECONDARY_TEXT, parent=parent)
        l.setFixedWidth(common.MARGIN() * 6.6667)
        l.setDisabled(True)
        if padding:
            w.layout().addSpacing(padding)
        w.layout().addWidget(l, 0)

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


def add_description(text, label=u' ', padding=common.MARGIN(), parent=None):
    """Utility method for adding a description field.

    Returns:
        QLabel: the added QLabel.

    """
    row = add_row(label, padding=padding, height=None, parent=parent)
    label = QtWidgets.QLabel(text, parent=parent)
    label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
    label.setStyleSheet(
        u'color: rgba({}); font-size: {}px'.format(
            common.rgb(common.SECONDARY_TEXT),
            common.SMALL_FONT_SIZE()
        )
    )
    label.setWordWrap(True)
    row.layout().addWidget(label, 1)
    parent.layout().addWidget(row)

    return label


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

    def __init__(self, text, width=None, parent=None):
        super(PaintedButton, self).__init__(text, parent=parent)
        self.setFixedHeight(common.ROW_HEIGHT() * 0.7)
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
            pen.setWidthF(common.ROW_SEPARATOR())

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(bg_color)
        painter.setPen(pen)
        o = common.ROW_SEPARATOR()
        rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
        o = common.INDICATOR_WIDTH() * 0.7
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
            color
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
        self.setFixedWidth(metrics.width(self._text) * 1.01)

    def paintEvent(self, event):
        """Custom paint event to use the aliased paint method."""
        painter = QtGui.QPainter()
        painter.begin(self)
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(font_size=self._size)[0],
            self.rect(),
            self.text(),
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            self._color
        )
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
    """Informative message box used for notifying the user of an event.

    """
    primary_color = QtGui.QColor(50, 50, 190, 255)
    secondary_color = common.FAVOURITE
    icon = u'icon_bw'

    def __init__(self, short_text, long_text, parent=None):
        global _message_box_instance
        _message_box_instance = self

        super(MessageBox, self).__init__(parent=parent)

        if parent is None:
            common.set_custom_stylesheet(self)

        self.short_text_label = QtWidgets.QLabel(short_text, parent=self)
        self.short_text_label.setWordWrap(True)
        self.long_text_label = QtWidgets.QLabel(long_text, parent=self)
        self.long_text_label.setWordWrap(True)

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
        self._create_UI()

        self.setStyleSheet("""
QWidget {{
    color: rgba({TEXT});
    background-color: rgba({BG});
    font-family: "{FAMILY}";
    font-size: {SIZE}px;
}}
            """.format(
            SIZE=common.LARGE_FONT_SIZE(),
            FAMILY=common.font_db.primary_font(common.MEDIUM_FONT_SIZE())[0].family(),
            TEXT=common.rgb(self.secondary_color.darker(150)),
            BG=common.rgb(self.secondary_color)))

        self.ok_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))

    def _create_UI(self):
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
            self.icon, self.secondary_color.lighter(150), common.ROW_HEIGHT())
        label = QtWidgets.QLabel(parent=self)
        label.setPixmap(pixmap)
        label.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding,
        )
        label.setStyleSheet(
            u'padding: {}px; background-color: rgba({});'.format(
                common.MEDIUM_FONT_SIZE(),
                common.rgb(self.primary_color)
            )
        )

        main_row.layout().insertWidget(0, label)

        short_text_row.layout().addWidget(self.short_text_label)
        self.short_text_label.setStyleSheet(
            u'padding:{m}px {s}px {m}px {s}px; background-color: rgba({c}); font-size: {s}px;'.format(
                m=common.MARGIN(),
                c=common.rgb(self.secondary_color.lighter(125)),
                s=common.MEDIUM_FONT_SIZE()
            ))
        self.short_text_label.setAlignment(QtCore.Qt.AlignLeft)

        long_text_row.layout().addWidget(self.long_text_label)
        self.long_text_label.setStyleSheet(
            u'padding:{m}px;background-color: rgba({c}); font-size:{s}px;'.format(
                m=common.MARGIN(),
                c=common.rgb(self.secondary_color),
                s=common.SMALL_FONT_SIZE()
            ))
        self.long_text_label.setAlignment(QtCore.Qt.AlignLeft)

        buttons_row = get_row(parent=columns)
        buttons_row.setStyleSheet(
            u'background-color: rgba({});'.format(common.rgb(self.secondary_color)))
        self.ok_button = QtWidgets.QPushButton(u'Ok', parent=self)
        buttons_row.layout().addWidget(self.ok_button)

        self.ok_button.setStyleSheet(
            """
        QPushButton {{
            font-size: {px}px;
            color: rgba(255,255,255,150);
            border-radius: {i}px;
            border: {s}px solid {c};
            margin: {i}px;
            padding: {i}px;
            background-color: rgba({p});
        }}
        QPushButton:hover {{
            color: white;
            background-color: rgba({pl});
        }}
        QPushButton:pressed {{
            color: rgba(255,255,255,150);
            background-color: rgba({pd});
        }}
        """.format(
                px=common.SMALL_FONT_SIZE(),
                i=common.INDICATOR_WIDTH(),
                s=common.ROW_SEPARATOR(),
                c=common.rgb(self.secondary_color.lighter(150)),
                p=common.rgb(self.primary_color),
                pl=common.rgb(self.primary_color.lighter(120)),
                pd=common.rgb(self.primary_color.darker(120))
            )
        )

    def sizeHint(self):
        return QtCore.QSize(common.HEIGHT(), common.HEIGHT() * 0.5)

    def eventFilter(self, widget, event):
        if widget != self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(self.secondary_color)
            o = common.MARGIN() * 0.5
            painter.drawRect(self.rect())
            painter.end()
            return True
        return False


class ErrorBox(MessageBox):
    """Informative message box used for notifying the user of an error.

    """
    primary_color = QtGui.QColor(190, 50, 50, 255)
    secondary_color = common.REMOVE
    icon = u'close'

    def __init__(self, *args, **kwargs):
        super(ErrorBox, self).__init__(*args, **kwargs)


class OkBox(MessageBox):
    """Informative message box used for notifying the user of success.

    """
    primary_color = QtGui.QColor(70, 160, 100, 255)
    secondary_color = QtGui.QColor(70, 180, 130, 255)  # 90, 200, 155)
    icon = u'check'

    def __init__(self, *args, **kwargs):
        super(OkBox, self).__init__(*args, **kwargs)


class DescriptionEditorWidget(LineEdit):
    """The editor used to edit the desciption of items."""

    def __init__(self, parent=None):
        super(DescriptionEditorWidget, self).__init__(parent=parent)
        self._connect_signals()

        self.installEventFilter(self)
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        self.setPlaceholderText(u'Edit description...')
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def _connect_signals(self):
        """Connects signals."""
        self.editingFinished.connect(self.action)
        self.parent().verticalScrollBar().valueChanged.connect(self.hide)
        if self.parent():
            self.parent().resized.connect(self.update_editor)

    def action(self):
        """Save the entered text to the BookmarkDB."""
        index = self.parent().selectionModel().currentIndex()
        text = u'{}'.format(index.data(common.DescriptionRole))
        if text.lower() == self.text().lower():
            self.hide()
            return

        if not index.data(common.ParentPathRole):
            self.hide()
            return

        k = common.proxy_path(index)

        db = bookmark_db.get_db(
            index.data(common.ParentPathRole)[0],
            index.data(common.ParentPathRole)[1],
            index.data(common.ParentPathRole)[2]
        )
        db.setValue(k, u'description', self.text())

        source_index = index.model().mapToSource(index)
        data = source_index.model().model_data()[source_index.row()]
        data[common.DescriptionRole] = self.text()
        self.parent().update(source_index)
        self.hide()

    def update_editor(self):
        """Sets the editor widget's size, position and text contents."""
        index = self.parent().selectionModel().currentIndex()
        if not index.isValid():
            self.hide()
            return

        rect = self.parent().visualRect(index)
        rectangles = delegate.get_rectangles(rect, self.parent().inline_icons_count())
        description_rect = self.parent().itemDelegate(
        ).get_description_rect(rectangles, index)

        # Won't be showing the editor if there's no appropiate description area
        # provided by the delegate (eg. the bookmark items don't have this)
        if not description_rect:
            self.hide()

        # Let's set the size based on the size provided by the delegate but
        # center it instead
        o = common.INDICATOR_WIDTH() * 2.0
        rect = description_rect.marginsAdded(QtCore.QMargins(0, o, 0, o))
        rect.moveCenter(rectangles[delegate.DataRect].center())
        self.setGeometry(rect)

        # Set the text and select it
        self.setText(u'{}'.format(index.data(common.DescriptionRole)))
        self.selectAll()

    def showEvent(self, event):
        index = self.parent().selectionModel().currentIndex()
        if not index.isValid():
            self.hide()
        if not index.data(common.FileInfoLoaded):
            self.hide()
        self.update_editor()
        self.setFocus(QtCore.Qt.PopupFocusReason)

    def eventFilter(self, widget, event):
        """We're filtering the enter key event here, otherwise, the
        list widget would close open finishing editing.

        """
        if not event.type() == QtCore.QEvent.KeyPress:
            return False

        event.accept()

        shift = event.modifiers() == QtCore.Qt.ShiftModifier

        escape = event.key() == QtCore.Qt.Key_Escape

        tab = event.key() == QtCore.Qt.Key_Tab
        backtab = event.key() == QtCore.Qt.Key_Backtab

        return_ = event.key() == QtCore.Qt.Key_Return
        enter = event.key() == QtCore.Qt.Key_Enter

        if escape:
            self.hide()
            return True

        if enter or return_:
            self.action()
            return True

        if not shift and tab:
            self.action()
            self.parent().key_down()
            self.parent().key_tab()
            self.show()

            return True

        if (shift and tab) or backtab:
            self.action()
            self.parent().key_up()
            self.parent().key_tab()
            self.show()
            return True

        return False

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.hide()


class FilterEditor(QtWidgets.QDialog):
    """Editor widget used to set a text filter on the associated model."""
    finished = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(FilterEditor, self).__init__(parent=parent)
        self.editor_widget = None
        self.context_menu_open = False

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.setWindowFlags(QtCore.Qt.Widget)
        self._create_UI()
        self._connect_signals()

        self.setFocusProxy(self.editor_widget)

    def _create_UI(self):
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN() * 2
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        row = add_row(None, parent=self, padding=0, height=common.ROW_HEIGHT())
        icon = ClickableIconButton(
            u'filter',
            (common.REMOVE, common.REMOVE),
            common.ROW_HEIGHT()
        )
        label = u'Search filter'
        label = PaintedLabel(label, parent=self)
        self.editor_widget = LineEdit(parent=self)

        row.layout().addWidget(icon, 0)
        row.layout().addWidget(label, 0)
        row.layout().addWidget(self.editor_widget, 1)
        self.layout().addStretch(1)

    def _connect_signals(self):
        self.editor_widget.returnPressed.connect(
            lambda: self.finished.emit(self.editor_widget.text()))
        self.finished.connect(
            lambda _: self.done(QtWidgets.QDialog.Accepted))

    @QtCore.Slot()
    def adjust_size(self):
        if not self.parent():
            return
        self.resize(
            self.parent().geometry().width(),
            self.parent().geometry().height())

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        pen = QtGui.QPen(common.SEPARATOR)
        pen.setWidthF(common.ROW_SEPARATOR())
        painter.setPen(pen)

        o = common.MARGIN()
        rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
        rect.setHeight(common.ROW_HEIGHT() + (common.MARGIN() * 2))
        painter.setBrush(common.SECONDARY_BACKGROUND)
        painter.setOpacity(0.9)
        painter.drawRoundedRect(
            rect, common.INDICATOR_WIDTH(), common.INDICATOR_WIDTH())
        painter.end()

    def mousePressEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.close()

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            if self.context_menu_open:
                return
            self.close()

    def showEvent(self, event):
        text = self.parent().model().filter_text()
        text = text.lower() if text else u''
        text = u'' if text == u'/' else text

        self.editor_widget.setText(text)
        self.editor_widget.selectAll()
        self.editor_widget.setFocus()
