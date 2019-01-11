# -*- coding: utf-8 -*-

"""

"""

import base64

from PySide2 import QtWidgets, QtGui, QtCore

from mayabrowser import common
from mayabrowser.delegate import ThumbnailEditor
from mayabrowser.configparsers import AssetSettings


class TodoItemEditor(QtWidgets.QTextEdit):
    """Custom QTextEdit widget for writing `Todo`'s.

    The editor automatically sets its size to accommodate the contents of the document.
    Some of the code has been lifted and implemented from Cameel's implementation.

    https://github.com/cameel/auto-resizing-text-edit/

    """

    def __init__(self, text=None, checked=False, parent=None):
        super(TodoItemEditor, self).__init__(parent=parent)
        self.setDisabled(checked)
        # self.setBackgroundVisible(False)
        self.document().setDocumentMargin(common.MARGIN)

        metrics = QtGui.QFontMetrics(self.document().defaultFont())
        metrics.width('  ')
        self.setTabStopWidth(common.MARGIN)

        self.setUndoRedoEnabled(True)

        self.setMinimumWidth(200)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Fixed
        )
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAlignment(QtCore.Qt.AlignJustify)

        self.setMouseTracking(True)

        self.document().setPlainText(text)

        self.document().contentsChanged.connect(self._contentChanged)
        self.document().contentsChange.connect(self._contentsChange)

    def _contentsChange(self, position, charsRemoved, charsAdded):
        """Custom formatting options for todo items are applied here."""
        block = None
        i = 0
        while i < self.document().blockCount():
            if not block:
                block = self.document().begin()
            else:
                block = block.next()
            cursor = QtGui.QTextCursor(block)
            textBlockFormat = cursor.blockFormat()
            textBlockFormat.setAlignment(QtCore.Qt.AlignJustify)
            cursor.mergeBlockFormat(textBlockFormat)
            i += 1

    def _contentChanged(self):
        """Sets the height of the editor."""
        self.setFixedHeight(
            self.heightForWidth(self.width())
        )

    def get_minHeight(self):
        """Returns the desired minimum height of the editor."""
        margins = self.contentsMargins()
        metrics = QtGui.QFontMetrics(self.document().defaultFont())
        line_height = metrics.height() + metrics.leading()
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
            height = self.get_minHeight() + 8
        elif height > 300.0:
            height = 300.0

        return height

    def sizeHint(self):
        return QtCore.QSize(200, self.heightForWidth(200))


class DragIndicatorButton(QtWidgets.QLabel):
    """Dotted button indicating a draggable item.

    The button is responsible for initiating a QDrag operation and setting the
    mime data. The data is populated with the `TodoEditor`'s text and the
    custom MIME_TYPE. The latter is needed to accept the drag operation
    in the target drop widet.
    """

    MIME_TYPE = 'browser/todo-drag'

    def __init__(self, checked=False, parent=None):

        super(DragIndicatorButton, self).__init__(parent=parent)
        self.setDisabled(checked)
        self.set_pixmap()
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.dragStartPosition = None

    def set_pixmap(self):
        icon_path = QtCore.QFileInfo(__file__).dir().path()
        icon_path = '{}/rsc/drag_indicator.png'.format(icon_path)

        image = QtGui.QImage()
        image.load(icon_path)

        if self.isEnabled():
            color = QtGui.QColor(common.SECONDARY_TEXT)
        else:
            color = QtGui.QColor(150, 150, 150, 255)

        for x in xrange(image.width()):
            for y in xrange(image.height()):
                color.setAlpha(image.pixelColor(x, y).alpha())
                image.setPixelColor(x, y, color)
        pixmap = QtGui.QPixmap(
            common.resize_image(image, 24))

        self.setPixmap(pixmap)

    def setDisabled(self, b):
        super(DragIndicatorButton, self).setDisabled(b)
        self.set_pixmap()

    def mousePressEvent(self, event):
        """Setting the starting drag position here."""
        self.dragStartPosition = event.pos()

    def mouseMoveEvent(self, event):
        """The drag operation is initiated here."""
        app = QtCore.QCoreApplication.instance()

        left_button = event.buttons() & QtCore.Qt.LeftButton
        if not left_button:
            return

        # Drag is only going to be valid when the mouse has travelled far enough
        # if ((event.pos() - self.dragStartPosition).manhattanLength() < app.startDragDistance()):
        #     return

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
        drag.setHotSpot(QtCore.QPoint(pixmap.width(), pixmap.height() / 2.0))

        # Drag origin indicator
        pixmap = QtGui.QPixmap(self.parent().size())

        painter = QtGui.QPainter()
        painter.begin(pixmap)
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(200, 200, 200, 255)))
        painter.drawRect(pixmap.rect())
        painter.end()

        # self.parent().render(pixmap)
        overlay = QtWidgets.QLabel(self.parent())
        overlay.setFixedSize(self.parent().size())
        overlay.setPixmap(pixmap)
        overlay.setAttribute(QtCore.Qt.WA_DeleteOnClose)


        # Preparing the drag...
        remove_button = self.parent().parent().parent(
        ).parent().parent().findChild(RemoveButton)
        add_button = self.parent().parent().parent().parent().parent().findChild(AddButton)
        remove_button.setPixmap(remove_button.active_pixmap)
        add_button.setHidden(True)
        self.parent().parent().separator.setHidden(False)
        overlay.show()

        # Starting the drag...
        drag.exec_(QtCore.Qt.MoveAction)

        # Cleanup after drag has finished...
        overlay.close()
        self.parent().parent().separator.setHidden(True)
        remove_button.setPixmap(remove_button.inactive_pixmap)
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
        self._get_images()

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
            self.setPixmap(self._checked_pixmap)
        else:
            self.setPixmap(self._unchecked_pixmap)

    def mouseReleaseEvent(self, event):
        self._checked = not self._checked
        self.clicked.emit(self._checked)

    def _get_images(self):
        icon_path = QtCore.QFileInfo(__file__).dir().path()

        unchecked = '{}/rsc/checkbox_unchecked.png'.format(icon_path)
        checked = '{}/rsc/checkbox_checked.png'.format(icon_path)

        image = QtGui.QImage()

        image.load(unchecked)
        color = QtGui.QColor(common.SEPARATOR)
        for x in xrange(image.width()):
            for y in xrange(image.height()):
                color.setAlpha(image.pixelColor(x, y).alpha())
                image.setPixelColor(x, y, color)
        self._checked_pixmap = QtGui.QPixmap(
            common.resize_image(image, 24))

        image.load(checked)
        color = QtGui.QColor(common.SELECTION)
        for x in xrange(image.width()):
            for y in xrange(image.height()):
                color.setAlpha(image.pixelColor(x, y).alpha())
                image.setPixelColor(x, y, color)

        self._unchecked_pixmap = QtGui.QPixmap(
            common.resize_image(image, 24))

class Separator(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super(Separator, self).__init__(parent=parent)
        pixmap = QtGui.QPixmap(QtCore.QSize(4096, 8))
        pixmap.fill(common.SELECTION)
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
        if event.mimeData().hasFormat('browser/todo-drag'):
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
        self.layout().setContentsMargins(8, 8, 8, 8)
        self.layout().setSpacing(8)
        self.setMinimumWidth(300)

        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        self.separator = Separator(parent=self)
        self.drop_target_index = -1

        self.items = []

        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def dragEnterEvent(self, event):
        """Accepting the drag operation."""
        if event.mimeData().hasFormat('browser/todo-drag'):
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

        # Change internal order
        self.items.insert(
            self.drop_target_index,
            self.items.pop(self.items.index(event.source()))
        )

        self.layout().removeWidget(event.source())
        self.layout().insertWidget(self.drop_target_index, event.source(), 1)

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

        # Index of the drop destination
        idx = dis.index(min(dis, key=abs))  # The selected line
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


class TodoItemsWidget(QtWidgets.QWidget):
    """Main widget containing the Todo items."""

    def __init__(self, path, parent=None):
        super(TodoItemsWidget, self).__init__(parent=parent)

        self.editors = None

        self.setObjectName('todoitemswrapper')
        self.setMouseTracking(True)

        self._createUI()

        # Populating widget with the saved settings
        settings = AssetSettings(path)
        items = settings.value('description/todos')
        if not items:
            return
        for k in items:
            self.add_item(
                text=items[k]['text'],
                checked=items[k]['checked']
            )

        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def _createUI(self):
        QtWidgets.QVBoxLayout(self)
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)

        def _pressed():
            self.add_item(text='...', idx=0)

        self.add_button = AddButton()
        self.add_button.pressed.connect(_pressed)
        self.add_button.setFocusPolicy(QtCore.Qt.NoFocus)

        self.remove_button = RemoveButton()
        self.remove_button.setFocusPolicy(QtCore.Qt.NoFocus)

        row = QtWidgets.QWidget()
        row.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
        )
        row.setFocusPolicy(QtCore.Qt.NoFocus)

        QtWidgets.QHBoxLayout(row)
        row.layout().addWidget(self.add_button, 0)
        row.layout().addStretch(1)
        row.layout().addWidget(self.remove_button, 0)
        self.layout().addWidget(row)

        self.editors = TodoEditors()
        self.setMinimumWidth(self.editors.minimumWidth() + 6)

        scrollarea = QtWidgets.QScrollArea()
        scrollarea.setWidgetResizable(True)
        scrollarea.setWidget(self.editors)
        scrollarea.setFocusPolicy(QtCore.Qt.NoFocus)

        self.layout().addWidget(scrollarea)

        common.set_custom_stylesheet(self)

        scrollarea.setObjectName('todoitemswrapper')
        scrollarea.setStyleSheet(
            '{}\n{}'.format(
                self.styleSheet(),
                """QScrollArea#todoitemswrapper {
                    background-color: lightgray;
                }
                """
            )
        )

    def add_item(self, idx=None, text=None, checked=False):
        """Creates a new widget containing the checkbox, editor and drag widgets.

        The method is responsible for adding the item the EditorsWidget layout
        and the EditorsWidget.items property.

        """
        row = QtWidgets.QWidget()

        QtWidgets.QHBoxLayout(row)
        row.layout().setContentsMargins(0, 0, 0, 0)
        row.layout().setSpacing(12)
        row.setFocusPolicy(QtCore.Qt.NoFocus)

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

        row.layout().addWidget(checkbox)
        row.layout().addWidget(editor, 1)
        row.layout().addWidget(drag)


        row.effect = QtWidgets.QGraphicsOpacityEffect(row)
        row.effect.setOpacity(1.0)
        row.animation = QtCore.QPropertyAnimation(row.effect, 'opacity')
        row.animation.setDuration(1500)
        row.animation.setKeyValueAt(0, 0)
        row.animation.setKeyValueAt(0.5, 0.8)
        row.animation.setKeyValueAt(1, 1.0)
        # row.animation.setLoopCount(-1)
        row.setGraphicsEffect(row.effect)
        row.setAutoFillBackground(True)

        if idx is None:
            self.editors.layout().addWidget(row, 1)
            self.editors.items.append(row)
        else:
            self.editors.layout().insertWidget(idx, row, 1)
            self.editors.items.insert(idx, row)
            # editor.selectAll()

        row.animation.start()
        checkbox.clicked.emit(checkbox._checked)

        editor.setFocus()

    def _collect_data(self):
        """Returns all the items found in the todo widget."""
        data = {}
        for n in xrange(len(self.editors.items)):
            item = self.editors.items[n]
            editor = item.findChild(TodoItemEditor)
            checkbox = item.findChild(CheckBoxButton)
            data[n] = {
                'checked': not checkbox.checked,
                'text': editor.document().toPlainText(),
            }
        return data

    def hideEvent(self, event):
        """Saving the contents on close/hide."""
        self.save_settings()

    def save_settings(self):
        settings = AssetSettings('C:/temp/temp')
        settings.setValue('description/todos', self._collect_data())


class AddButton(QtWidgets.QLabel):
    pressed = QtCore.Signal()

    def __init__(self, parent=None):
        super(AddButton, self).__init__(parent=parent)
        self.setMouseTracking(True)

        path = '{}/rsc/todo_add.png'.format(
            QtCore.QFileInfo(__file__).dir().path()
        )

        image = QtGui.QImage(path)
        image = common.resize_image(image, 24)
        pixmap = QtGui.QPixmap()
        pixmap = pixmap.fromImage(image)
        self.setPixmap(pixmap)

        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT)

    def mouseReleaseEvent(self, event):
        self.pressed.emit()


class RemoveButton(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super(RemoveButton, self).__init__(parent=parent)

        self.inactive_pixmap = self._pixmap('todo_remove')
        self.active_pixmap = self._pixmap('todo_remove_activated')

        self.setPixmap(self.inactive_pixmap)

        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        """Accepting the drag operation."""
        if event.mimeData().hasFormat('browser/todo-drag'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Drop event responsible for deleting an item from the todo list."""
        editors = self.parent().parent().editors
        idx = editors.items.index(event.source())
        row = editors.items.pop(idx)
        editors.layout().removeWidget(row)
        row.deleteLater()


    def _pixmap(self, name):
        path = '{}/rsc/{}.png'.format(
            QtCore.QFileInfo(__file__).dir().path(),
            name
        )
        image = QtGui.QImage(path)
        image = common.resize_image(image, 24)
        pixmap = QtGui.QPixmap()
        return pixmap.fromImage(image)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = TodoItemsWidget('C:/temp/temp')
    widget.show()
    app.exec_()
