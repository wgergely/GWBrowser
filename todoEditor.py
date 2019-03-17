# -*- coding: utf-8 -*-

"""Defines the widgets needed to add and modify notes and todo type annotions
for an asset.

`TodoEditorWidget` is the top widget. It reads the asset configuration file
and loads all stored todo items. It currently does no support rich text editing
features but would be nice to implement this in the future.

Methods:
    TodoEditorWidget.add_item(): Main function to add a new todo item.

"""


from PySide2 import QtWidgets, QtGui, QtCore

from browser import common
from browser.settings import AssetSettings
from browser.imagecache import ImageCache

class Highlighter(QtGui.QSyntaxHighlighter):
    """Class responsible for highlighting urls"""

    def highlightBlock(self, text):
        """Custom stlyes are applied here."""
        """The highlighting cases are defined in the common module.
        In general we're tying to replicate the ``Markdown`` syntax rendering.

        Args:
            case (str): HIGHLIGHT_RULES dicy key.
            text (str): The text to assess.

        Returns:
            tuple: int, int, int

        """
        start = 0
        end = len(text)

        flags = common.NoHighlightFlag
        for case in common.HIGHLIGHT_RULES:
            match = u''
            search = common.HIGHLIGHT_RULES[case][u're'].search(text)
            if not search:
                continue

            flags = flags | common.HIGHLIGHT_RULES[case][u'flag']
            for group in search.groups():
                if not group:
                    continue
                group = u'{}'.format(group)
                group.encode(u'utf-8')
                match += group

            if not match:
                continue

            match.rstrip()
            start = text.find(match)
            end = len(match)

            char_format = QtGui.QTextCharFormat()
            char_format.setFont(self.document().defaultFont())

            if flags == common.NoHighlightFlag:
                self.setFormat(start, end, char_format)
                break

            if flags & common.HeadingHighlight:
                char_format.setFontWeight(QtGui.QFont.Bold)
                char_format.setFontPointSize(
                    self.document().defaultFont().pointSizeF() + 0 + (6 - len(match)))
                char_format.setFontCapitalization(QtGui.QFont.AllUppercase)
                if len(match) > 1:
                    char_format.setUnderlineStyle(
                        QtGui.QTextCharFormat.SingleUnderline)
                    char_format.setFontPointSize(
                        self.document().defaultFont().pointSizeF() + 1)
                self.setFormat(0, len(text), char_format)
                break
            elif flags & common.QuoteHighlight:
                char_format.setForeground(QtGui.QColor(100, 100, 100))
                char_format.setBackground(QtGui.QColor(230, 230, 230))
                self.setFormat(0, len(text), char_format)
                break

            if flags & common.CodeHighlight:
                char_format.setFontWeight(QtGui.QFont.Bold)
                char_format.setForeground(common.FAVOURITE)
                self.setFormat(start, end, char_format)
            if flags & common.BoldHighlight:
                char_format.setFontWeight(QtGui.QFont.Bold)
                self.setFormat(start, end, char_format)
            if flags & common.ItalicHighlight:
                char_format.setFontItalic(True)
                self.setFormat(start, end, char_format)

        return


class TodoItemEditor(QtWidgets.QTextBrowser):
    """Custom QTextEdit widget for writing `Todo`'s.

    The editor automatically sets its size to accommodate the contents of the document.
    Some of the code has been lifted and implemented from Cameel's implementation.

    https://github.com/cameel/auto-resizing-text-edit/

    """

    def __init__(self, text=None, checked=False, parent=None):
        super(TodoItemEditor, self).__init__(parent=parent)
        self.setDisabled(checked)
        self.document().setDocumentMargin(common.MARGIN * 2)
        # option
        option = QtGui.QTextOption()
        option.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        option.setWrapMode(QtGui.QTextOption.WrapAtWordBoundaryOrAnywhere)
        option.setUseDesignMetrics(True)
        self.document().setDefaultTextOption(option)
        # font
        font = QtGui.QFont(common.SecondaryFont)
        font.setStyleStrategy(QtGui.QFont.PreferAntialias)
        font.setPointSizeF(12.0)
        self.document().setDefaultFont(font)

        self.highlighter = Highlighter(self.document())
        self.setOpenExternalLinks(True)
        self.setOpenLinks(True)
        self.setReadOnly(False)
        self.setTextInteractionFlags(
            QtCore.Qt.TextBrowserInteraction | QtCore.Qt.TextEditorInteraction)

        metrics = QtGui.QFontMetrics(self.document().defaultFont())
        metrics.width(u'  ')
        self.setTabStopWidth(common.MARGIN)

        self.setUndoRedoEnabled(True)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Fixed
        )
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setMouseTracking(True)
        self.document().setPlainText(text)
        # self.setAlignment(QtCore.Qt.AlignJustify | QtCore.Qt.AlignVCenter)

        self.document().contentsChanged.connect(self._contentChanged)
        self.anchorClicked.connect(self._anchorClicked)

    def setDisabled(self, b):
        super(TodoItemEditor, self).setDisabled(b)
        font = QtGui.QFont(common.SecondaryFont)
        font.setStyleStrategy(QtGui.QFont.PreferAntialias)
        font.setPointSizeF(12.0)
        if b:
            font.setStrikeOut(True)
        self.document().setDefaultFont(font)

    def _contentChanged(self):
        """Sets the height of the editor."""
        self.setFixedHeight(
            self.heightForWidth(self.width())
        )

    def get_minHeight(self):
        """Returns the desired minimum height of the editor."""
        margins = self.contentsMargins()
        metrics = QtGui.QFontMetrics(self.document().defaultFont())
        line_height = (metrics.height() + metrics.leading()) * 4  # Lines tall
        return line_height + margins.top() + margins.bottom()

    def get_maxHeight(self):
        """Returns the desired minimum height of the editor."""
        margins = self.contentsMargins()
        metrics = QtGui.QFontMetrics(self.document().defaultFont())
        line_height = (metrics.height() + metrics.leading()) * 48  # Lines tall
        return line_height + margins.top() + margins.bottom()

    def heightForWidth(self, width):
        """https://raw.githubusercontent.com/cameel/auto-resizing-text-edit/master/auto_resizing_text_edit/auto_resizing_text_edit.py"""
        margins = self.contentsMargins()

        if width >= margins.left() + margins.right():
            document_width = width - margins.left() - margins.right()
        else:
            # If specified width can't even fit the margin, there's no space left for the document
            document_width = 0

        document = self.document().clone()
        document.setTextWidth(document_width)
        height = margins.top() + document.size().height() + margins.bottom()

        if height < self.get_minHeight():
            return self.get_minHeight()
        if height > self.get_maxHeight():
            return self.get_maxHeight()
        return height

    def keyPressEvent(self, event):
        """I'm defining custom key events here, the default behaviour is pretty poor."""
        cursor = self.textCursor()
        cursor.setVisualNavigation(True)

        no_modifier = event.modifiers() == QtCore.Qt.NoModifier
        control_modifier = event.modifiers() == QtCore.Qt.ControlModifier
        shift_modifier = event.modifiers() == QtCore.Qt.ShiftModifier

        if event.key() == QtCore.Qt.Key_Backtab:
            cursor.movePosition(
                QtGui.QTextCursor.Start,
                QtGui.QTextCursor.MoveAnchor,
                cursor.position() - 4,
            )
            return
        super(TodoItemEditor, self).keyPressEvent(event)

    def sizeHint(self):
        return QtCore.QSize(200, self.heightForWidth(200))

    def _anchorClicked(self):
        print 'click'


class AddButton(QtWidgets.QLabel):
    """Custom icon button to add a new todo item."""
    pressed = QtCore.Signal()

    def __init__(self, parent=None):
        super(AddButton, self).__init__(parent=parent)
        self.setMouseTracking(True)

        pixmap = ImageCache.get_rsc_pixmap(
            u'todo_add', common.SEPARATOR, common.INLINE_ICON_SIZE)
        self.setPixmap(pixmap)

        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setFixedHeight(common.INLINE_ICON_SIZE)

    def mouseReleaseEvent(self, event):
        self.pressed.emit()


class RemoveButton(QtWidgets.QLabel):
    """Custom icon button to remove an item or close the editor."""

    def __init__(self, parent=None):
        super(RemoveButton, self).__init__(parent=parent)

        pixmap = ImageCache.get_rsc_pixmap(u'todo_remove', common.FAVOURITE, 32)
        self.setPixmap(pixmap)

        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)

    def mouseReleaseEvent(self, event):
        """We're handling the close event here."""
        self.parent().parent().close()

    def dragEnterEvent(self, event):
        """Accepting the drag operation."""
        if event.mimeData().hasFormat(u'browser/todo-drag'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Drop event responsible for deleting an item from the todo list."""
        editors = self.parent().parent().editors
        idx = editors.items.index(event.source())
        row = editors.items.pop(idx)
        editors.layout().removeWidget(row)
        row.deleteLater()


class DragIndicatorButton(QtWidgets.QLabel):
    """Dotted button indicating a draggable item.

    The button is responsible for initiating a QDrag operation and setting the
    mime data. The data is populated with the `TodoEditor`'s text and the
    custom MIME_TYPE. The latter is needed to accept the drag operation
    in the target drop widet.
    """

    MIME_TYPE = u'browser/todo-drag'

    def __init__(self, checked=False, parent=None):

        super(DragIndicatorButton, self).__init__(parent=parent)
        self.setDisabled(checked)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.dragStartPosition = None

        if self.isEnabled():
            pixmap = ImageCache.get_rsc_pixmap(
                u'drag_indicator', common.SEPARATOR, common.INLINE_ICON_SIZE)
        else:
            pixmap = ImageCache.get_rsc_pixmap(
                u'drag_indicator', common.FAVOURITE, common.INLINE_ICON_SIZE)
        self.setPixmap(pixmap)

    def setDisabled(self, b):
        # super(DragIndicatorButton, self).setDisabled(b)
        if b:
            pixmap = ImageCache.get_rsc_pixmap(
                u'drag_indicator', common.FAVOURITE, common.INLINE_ICON_SIZE)
        else:
            pixmap = ImageCache.get_rsc_pixmap(
                u'drag_indicator', common.SEPARATOR, common.INLINE_ICON_SIZE)

        self.setPixmap(pixmap)

    def mousePressEvent(self, event):
        """Setting the starting drag position here."""
        self.dragStartPosition = event.pos()

    def mouseMoveEvent(self, event):
        """The drag operation is initiated here."""
        app = QtCore.QCoreApplication.instance()

        left_button = event.buttons() & QtCore.Qt.LeftButton
        if not left_button:
            return

        drag = QtGui.QDrag(self.parent())

        # Setting Mime Data
        mime_data = QtCore.QMimeData()
        data = QtCore.QByteArray()
        data.append(0)
        mime_data.setData(self.MIME_TYPE, data)
        drag.setMimeData(mime_data)

        # Drag pixmap
        editor = self.parent().findChild(QtWidgets.QTextEdit)

        # Transparent image
        image = QtGui.QImage(editor.size(), QtGui.QImage.Format_ARGB32)
        editor.render(image)
        for x in xrange(image.width()):
            for y in xrange(image.height()):
                color = QtGui.QColor(image.pixel(x, y))
                color.setAlpha(150)
                image.setPixel(x, y, color.rgba())

        pixmap = QtGui.QPixmap()
        pixmap = pixmap.fromImage(image)

        drag.setPixmap(pixmap)
        drag.setHotSpot(QtCore.QPoint(0, pixmap.height() / 2.0))

        # Drag origin indicator
        pixmap = QtGui.QPixmap(self.parent().size())

        painter = QtGui.QPainter()
        painter.begin(pixmap)
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(200, 200, 200, 255)))
        painter.drawRect(pixmap.rect())
        painter.end()

        overlay = QtWidgets.QLabel(self.parent())
        overlay.setFixedSize(self.parent().size())
        overlay.setPixmap(pixmap)
        overlay.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Preparing the drag...
        remove_button = self.parent().parent().parent(
        ).parent().parent().findChild(RemoveButton)
        # Ugh, ugly code...
        add_button = self.parent().parent().parent().parent().parent().findChild(AddButton)
        pixmap = pixmap = ImageCache.get_rsc_pixmap(
            u'todo_remove_activated', QtGui.QColor(255, 0, 0), 24)
        remove_button.setPixmap(pixmap)
        add_button.setHidden(True)
        self.parent().parent().separator.setHidden(False)
        overlay.show()

        # Starting the drag...
        drag.exec_(QtCore.Qt.MoveAction)

        # Cleanup after drag has finished...
        overlay.close()
        self.parent().parent().separator.setHidden(True)
        pixmap = ImageCache.get_rsc_pixmap(u'todo_remove', common.FAVOURITE, 32)
        remove_button.setPixmap(pixmap)
        add_button.setHidden(False)


class CheckBoxButton(QtWidgets.QLabel):
    """Custom checkbox used for Todo Items."""

    clicked = QtCore.Signal(bool)

    def __init__(self, checked=False, parent=None):
        super(CheckBoxButton, self).__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_Hover, True)
        self.setMouseTracking(True)

        self._checked = checked
        self._checked_pixmap = None
        self._unchecked_pixmap = None

        self.set_pixmap(self._checked)
        self._connectSignals()

        self.setFocusPolicy(QtCore.Qt.NoFocus)

    @property
    def checked(self):
        return self._checked

    def _connectSignals(self):
        self.clicked.connect(self.set_pixmap)

    def set_pixmap(self, checked):
        if checked:
            pixmap = ImageCache.get_rsc_pixmap(
                u'checkbox_unchecked', common.SEPARATOR, 24)
            self.setPixmap(pixmap)
        else:
            pixmap = ImageCache.get_rsc_pixmap(
                u'checkbox_checked', common.FAVOURITE, 24)
            self.setPixmap(pixmap)

    def mouseReleaseEvent(self, event):
        self._checked = not self._checked
        self.clicked.emit(self._checked)


class Separator(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super(Separator, self).__init__(parent=parent)
        pixmap = QtGui.QPixmap(QtCore.QSize(4096, 2))
        pixmap.fill(common.FAVOURITE)
        self.setPixmap(pixmap)

        self.setHidden(True)

        self.setFocusPolicy(QtCore.Qt.NoFocus)

        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint
        )
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAcceptDrops(True)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
        )
        self.setFixedWidth(1)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(u'browser/todo-drag'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Calling the parent's drop event, when the drop is on the separator."""
        self.parent().dropEvent(event)


class TodoEditors(QtWidgets.QWidget):
    """This is a convenience widget for storing the added todo items.

    As this is the container widget, it is responsible for handling the dragging
    and setting the order of the contained child widgets.

    Attributes:
        items (list):       The added todo items.

    """

    def __init__(self, parent=None):
        super(TodoEditors, self).__init__(parent=parent)
        QtWidgets.QVBoxLayout(self)
        self.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        self.layout().setContentsMargins(8, 8, 8, 8)
        self.layout().setSpacing(8)

        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        self.separator = Separator(parent=self)
        self.drop_target_index = -1

        self.items = []

        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def dragEnterEvent(self, event):
        """Accepting the drag operation."""
        if event.mimeData().hasFormat(u'browser/todo-drag'):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Custom drag move event responsible for indicating the drop area."""
        # Move indicator
        idx, y = self._separator_pos(event)

        if y == -1:
            self.separator.setHidden(True)
            self.drop_target_index = -1
            event.ignore()
            return

        event.accept()
        self.drop_target_index = idx

        self.separator.setHidden(False)
        pos = self.mapToGlobal(QtCore.QPoint(self.geometry().x(), y))
        self.separator.move(pos)
        self.separator.setFixedWidth(self.width())

    def dropEvent(self, event):
        if self.drop_target_index == -1:
            event.ignore()
            return

        event.accept()

        # Drag from another todo list
        if event.source() not in self.items:
            text = event.source().findChild(TodoItemEditor).document().toPlainText()
            self.parent().parent().parent().add_item(idx=0, text=text, checked=False)
            self.separator.setHidden(True)
            return
        # Change internal order
        self.items.insert(
            self.drop_target_index,
            self.items.pop(self.items.index(event.source()))
        )

        self.layout().removeWidget(event.source())
        self.layout().insertWidget(self.drop_target_index, event.source(), 0)

    def _separator_pos(self, event):
        """Returns the position of"""
        idx = 0
        dis = []

        y = event.pos().y()

        # Collecting the available hot-spots for the drag operation
        lines = []
        for n in xrange(len(self.items)):
            if n == 0:  # first
                line = self.items[n].geometry().top()
                lines.append(line)
                continue

            line = (
                self.items[n - 1].geometry().bottom() +
                self.items[n].geometry().top()
            ) / 2.0
            lines.append(line)

            if n == len(self.items) - 1:  # last
                line = ((
                    self.items[n - 1].geometry().bottom() +
                    self.items[n].geometry().top()
                ) / 2.0)
                lines.append(line)
                line = self.items[n].geometry().bottom()
                lines.append(line)
                break

        # Finding the closest
        for line in lines:
            dis.append(y - line)

        # Cases when items is dragged from another editor instance
        if not dis:
            return 0, 0

        idx = dis.index(min(dis, key=abs))  # The selected line
        if event.source() not in self.items:
            source_idx = idx + 1
        else:
            source_idx = self.items.index(event.source())

        if idx == 0:  # first item
            return (0, lines[idx])
        elif source_idx == idx:  # order remains unchanged
            return (source_idx, lines[idx])
        elif (source_idx + 1) == idx:  # order remains unchanged
            return (source_idx, lines[idx])
        elif source_idx < idx:  # moves up
            return (idx - 1, lines[idx])
        elif source_idx > idx:  # move down
            return (idx, lines[idx])


class MoveWidget(QtWidgets.QWidget):
    """Widget used to move the editor window."""

    def __init__(self, parent=None):
        super(MoveWidget, self).__init__(parent=parent)
        self.setMouseTracking(True)

        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_widget_pos = None

    def mousePressEvent(self, event):
        self.move_in_progress = True
        self.move_start_event_pos = event.pos()
        self.move_start_widget_pos = self.mapToGlobal(
            self.geometry().topLeft())

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.NoButton:
            return
        if self.move_start_widget_pos:
            offset = (event.pos() - self.move_start_event_pos)
            self.parent().move(self.mapToGlobal(self.geometry().topLeft()) + offset)


class ResizeWidget(QtWidgets.QWidget):
    """Widget used to move the editor window."""

    def __init__(self, parent=None):
        super(ResizeWidget, self).__init__(parent=parent)
        self.setMouseTracking(True)
        self.setFixedHeight(12)
        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_geo = None

    def mousePressEvent(self, event):
        self.move_in_progress = True
        self.move_start_event_pos = event.pos()
        self.move_start_geo = self.parent().rect()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.NoButton:
            return

        offset = (event.pos() - self.move_start_event_pos)
        if self.move_start_geo:
            rect = self.parent().geometry()
            rect.setRight(
                rect.left() + self.move_start_geo.width() + offset.x())
            rect.setBottom(rect.bottom() + offset.y())
            self.parent().setGeometry(rect)

    def mouseReleaseEvent(self, event):
        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_geo = None


class TodoEditorWidget(QtWidgets.QWidget):
    """Main widget containing the Todo items."""

    def __init__(self, index, parent=None):
        super(TodoEditorWidget, self).__init__(parent=parent)

        self.editors = None
        self._index = index

        self.setObjectName(u'todoitemswrapper')
        self.setWindowTitle(u'Todo Editor')
        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint
        )
        self.setMinimumWidth(640)
        self.setMinimumHeight(800)

        self._createUI()
        self.installEventFilter(self)

        if not index.isValid():
            return

        settings = AssetSettings(index)
        items = settings.value(u'config/todos')
        if not items:
            return

        for k in items:
            self.add_item(
                text=items[k][u'text'],
                checked=items[k][u'checked']
            )

        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def eventFilter(self, widget, event):
        """Using the custom event filter to paint the background."""
        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setPen(common.FAVOURITE)
            font = QtGui.QFont(common.SecondaryFont)
            font.setPointSize(10.0)
            painter.setFont(font)
            painter.drawText(
                self.rect(),
                QtCore.Qt.AlignCenter,
                u'No todo items in the list. Yet.\nYou can add a new item by clikcing the pencil icon on the top.' if not len(
                    self.editors.items) else u''
            )
            painter.end()
        return False

    def _get_next_enabled(self, n):
        hasEnabled = False
        for i in xrange(len(self.editors.items)):
            item = self.editors.items[i]
            editor = item.findChild(TodoItemEditor)
            if editor.isEnabled():
                hasEnabled = True
                break

        if not hasEnabled:
            return -1

        # Finding the next enabled editor
        for _ in xrange(len(self.editors.items) - n):
            n += 1
            if n >= len(self.editors.items):
                return self._get_next_enabled(-1)
            item = self.editors.items[n]
            editor = item.findChild(TodoItemEditor)
            if editor.isEnabled():
                return n

    def key_tab(self):
        """Defining tabbing forward between items."""
        if not self.editors.items:
            return

        n = 0
        for n, item in enumerate(self.editors.items):
            editor = item.findChild(TodoItemEditor)
            if editor.hasFocus():
                break

        n = self._get_next_enabled(n)
        if n > -1:
            item = self.editors.items[n]
            editor = item.findChild(TodoItemEditor)
            editor.setFocus()
            self.scrollarea.ensureWidgetVisible(
                editor, ymargin=editor.height())

    def key_return(self,):
        """Control enter toggles the state of the checkbox."""
        for item in self.editors.items:
            editor = item.findChild(TodoItemEditor)
            checkbox = item.findChild(CheckBoxButton)
            if editor.hasFocus():
                checkbox.clicked.emit(not checkbox.checked)
                break

    def keyPressEvent(self, event):
        """Custom keypresses."""
        no_modifier = event.modifiers() == QtCore.Qt.NoModifier
        control_modifier = event.modifiers() == QtCore.Qt.ControlModifier
        shift_modifier = event.modifiers() == QtCore.Qt.ShiftModifier

        if event.key() == QtCore.Qt.Key_Escape:
            self.close()

        if shift_modifier:
            if event.key() == QtCore.Qt.Key_Tab:
                return True
            if event.key() == QtCore.Qt.Key_Backtab:
                return True

        if control_modifier:
            if event.key() == QtCore.Qt.Key_S:
                self.save_settings()
                return True
            elif event.key() == QtCore.Qt.Key_N:
                self.add_button.pressed.emit()
                return True
            elif event.key() == QtCore.Qt.Key_Tab:
                self.key_tab()
                return True
            elif event.key() == QtCore.Qt.Key_Return:
                self.key_return()

    @property
    def index(self):
        """The path used to initialize the widget."""
        return self._index

    def add_item(self, idx=None, text=None, checked=False):
        """Creates a new widget containing the checkbox, editor and drag widgets.

        The method is responsible for adding the item the EditorsWidget layout
        and the EditorsWidget.items property.

        """
        item = QtWidgets.QWidget()

        QtWidgets.QHBoxLayout(item)
        item.layout().setContentsMargins(0, 0, 0, 0)
        item.layout().setSpacing(0)
        item.setFocusPolicy(QtCore.Qt.NoFocus)

        checkbox = CheckBoxButton(checked=not checked)
        checkbox.setFocusPolicy(QtCore.Qt.NoFocus)
        editor = TodoItemEditor(text, checked=not checked)
        editor.setFocusPolicy(QtCore.Qt.StrongFocus)
        drag = DragIndicatorButton(checked=False)
        drag.setFocusPolicy(QtCore.Qt.NoFocus)

        def _setDisabled(b, widget=None):
            widget.setDisabled(not b)

        def _hide_separator():
            self.editors.separator.setHidden(False)

        def _show_separator():
            self.editors.separator.setHidden(True)

        import functools

        checkbox.clicked.connect(
            functools.partial(_setDisabled, widget=editor))
        checkbox.clicked.connect(
            functools.partial(_setDisabled, widget=drag))

        item.layout().addWidget(checkbox)
        item.layout().addWidget(drag)
        item.layout().addWidget(editor, 1)

        item.effect = QtWidgets.QGraphicsOpacityEffect(item)
        item.effect.setOpacity(1.0)
        item.animation = QtCore.QPropertyAnimation(item.effect, u'opacity')
        item.animation.setDuration(1500)
        item.animation.setKeyValueAt(0, 0)
        item.animation.setKeyValueAt(0.5, 0.8)
        item.animation.setKeyValueAt(1, 1.0)
        item.setGraphicsEffect(item.effect)
        item.setAutoFillBackground(True)

        if idx is None:
            self.editors.layout().addWidget(item, 0)
            self.editors.items.append(item)
        else:
            self.editors.layout().insertWidget(idx, item, 0)
            self.editors.items.insert(idx, item)

        item.animation.start()
        checkbox.clicked.emit(checkbox._checked)

        editor.setFocus()

        item.editor = editor
        return item

    def save_settings(self):
        """Saves the current list of todo items to the assets configuration file."""
        if not self.index.isValid():
            return
        settings = AssetSettings(self.index)
        todos = self._collect_data()
        settings.setValue(u'config/todos', todos)

        model = self.index.model()
        model.setData(self.index, len(todos), role=common.TodoCountRole)
        # data[self.index.row()][common.TodoCountRole] = len(todos)

    def _createUI(self):
        QtWidgets.QVBoxLayout(self)
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)

        def _pressed():
            self.add_item(text=u'', idx=0)

        self.remove_button = RemoveButton()
        self.remove_button.setFocusPolicy(QtCore.Qt.NoFocus)

        row = MoveWidget()
        row.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
        )
        row.setFocusPolicy(QtCore.Qt.NoFocus)

        QtWidgets.QHBoxLayout(row)
        self.add_button = AddButton()
        self.add_button.pressed.connect(_pressed)
        self.add_button.pressed.connect(self.update)
        self.add_button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.add_button.setFixedWidth(32)
        self.add_button.setFixedHeight(32)
        self.add_button.setAlignment(QtCore.Qt.AlignCenter)
        pixmap = ImageCache.get_rsc_pixmap(u'todo', common.FAVOURITE, 32)
        self.add_button.setPixmap(pixmap)
        row.layout().addWidget(self.add_button, 0)

        if self.index.isValid():
            job = self.index.data(common.ParentRole)[1]
            text = u'{}: {}  |  Notes and Tasks'.format(
                job.upper(),
                self.index.data(QtCore.Qt.DisplayRole).upper()
            )
        else:
            text = u'Notes and Tasks'

        label = QtWidgets.QLabel(text)
        label.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
        )
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setStyleSheet("""
        QLabel {{
            color: rgb(30,30,30);
        	font-family: "{}";
        	font-size: 11pt;
        }}
        """.format(common.SecondaryFont.family()))
        row.layout().addWidget(label, 1)
        row.layout().addWidget(self.remove_button, 0)

        self.editors = TodoEditors()
        self.setMinimumWidth(self.editors.minimumWidth() + 6)
        self.setMinimumHeight(100)

        self.scrollarea = QtWidgets.QScrollArea()
        self.scrollarea.setWidgetResizable(True)
        self.scrollarea.setWidget(self.editors)
        self.scrollarea.setFocusPolicy(QtCore.Qt.NoFocus)

        self.scrollarea.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.scrollarea.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.layout().addWidget(row)
        self.layout().addWidget(self.scrollarea)
        self.layout().addWidget(ResizeWidget())

        common.set_custom_stylesheet(self)

    def _collect_data(self):
        """Returns all the items found in the todo widget."""
        data = {}
        for n in xrange(len(self.editors.items)):
            item = self.editors.items[n]
            editor = item.findChild(TodoItemEditor)
            checkbox = item.findChild(CheckBoxButton)
            if not editor.document().toPlainText():
                continue
            data[n] = {
                u'checked': not checkbox.checked,
                u'text': editor.document().toPlainText(),
            }
        return data

    def hideEvent(self, event):
        """Saving the contents on close/hide."""
        self.save_settings()

    def focusOutEvent(self, event):
        if event.lostFocus():
            self.close()

    def sizeHint(self):
        return QtCore.QSize(800, 600)

    def showEvent(self, event):
        animation = QtCore.QPropertyAnimation(
            self, u'windowOpacity', parent=self)
        animation.setEasingCurve(QtCore.QEasingCurve.InQuad)
        animation.setDuration(150)
        animation.setStartValue(0.01)
        animation.setEndValue(1)
        animation.start(QtCore.QPropertyAnimation.DeleteWhenStopped)

        app = QtWidgets.QApplication.instance()
        geo = app.desktop().availableGeometry(self.parent())
        if geo:
            self.move(
                (geo.width() / 2) - (self.width() / 2),
                (geo.height() / 2) - (self.height() / 2)
            )


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    index = QtCore.QModelIndex()
    widget = TodoEditorWidget(index)
    item = widget.add_item(
        text=u'This is a test link:\nClick this: file://gordo/jobs')
    # print item.editor.document().setPlainText('Hullo')
    widget.show()
    app.exec_()
