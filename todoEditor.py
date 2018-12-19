# -*- coding: utf-8 -*-

"""

"""

from PySide2 import QtWidgets, QtGui, QtCore

from mayabrowser import common
from mayabrowser.delegate import ThumbnailEditor


class TodoItemEditor(QtWidgets.QPlainTextEdit):
    """Custom QPlainTextEdit widget for writing `Todo`'s.

    The editor automatically sets its size to accommodate the contents of the document.
    Some of the code has been lifted and implemented from Cameel's implementation.

    https://github.com/cameel/auto-resizing-text-edit/

    """
    def __init__(self, text=None, checked=False, parent=None):
        super(TodoItemEditor, self).__init__(parent=parent)
        self.setDisabled(checked)
        self.document().setPlainText(text)
        self.setBackgroundVisible(False)
        self.document().setDocumentMargin(common.MARGIN)
        self.setMinimumWidth(200)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Fixed
        )

        metrics = QtGui.QFontMetrics(self.document().defaultFont())
        metrics.width('  ')
        self.setTabStopWidth(common.MARGIN)
        self.document().contentsChanged.connect(self._contentChanged)

        self.setMouseTracking(True)

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

    pressed = QtCore.Signal(QtWidgets.QWidget)
    released = QtCore.Signal(QtWidgets.QWidget)

    def __init__(self, checked=False,parent=None):

        super(DragIndicatorButton, self).__init__(parent=parent)
        self.setDisabled(checked)
        self.set_pixmap()
        
        self.dragStartPosition = None

    def set_pixmap(self):
        icon_path = QtCore.QFileInfo(__file__).dir().path()
        icon_path = '{}/rsc/drag_indicator.png'.format(icon_path)

        image = QtGui.QImage()
        image.load(icon_path)

        if self.isEnabled():
            color = QtGui.QColor(common.SEPARATOR)
        else:
            color = QtGui.QColor(150,150,150,255)

        for x in xrange(image.width()):
            for y in xrange(image.height()):
                color.setAlpha(image.pixelColor(x, y).alpha())
                image.setPixelColor(x, y, color)
        pixmap = QtGui.QPixmap(
            ThumbnailEditor.smooth_copy(image, 24))

        self.setPixmap(pixmap)

    def setDisabled(self, b):
        super(DragIndicatorButton, self).setDisabled(b)
        self.set_pixmap()

    def mouseReleaseEvent(self, event):
        self.released.emit(self.parentWidget())

    def mousePressEvent(self, event):
        """Setting the starting drag position here."""
        self.pressed.emit(self.parentWidget())
        self.dragStartPosition = event.pos()

    def mouseMoveEvent(self, event):
        """After the mousePressEvent, the drag operation is handled here."""
        app = QtCore.QCoreApplication.instance()

        left_button = event.buttons() & QtCore.Qt.LeftButton
        if not left_button:
            return

        if ((event.pos() - self.dragStartPosition).manhattanLength() < app.startDragDistance()):
            return

        drag = QtGui.QDrag(self.parent().parent())
        editor = self.parent().findChild(QtWidgets.QPlainTextEdit)

        mime_data = QtCore.QMimeData()
        mime_data.setText(editor.document().toPlainText())

        data = QtCore.QByteArray()
        data.append(0)
        mime_data.setData(self.MIME_TYPE, data)
        drag.setMimeData(mime_data)

        pixmap = QtGui.QPixmap(editor.size())
        editor.render(pixmap)
        drag.setPixmap(pixmap)

        drag.exec_(QtCore.Qt.CopyAction)

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
            ThumbnailEditor.smooth_copy(image, 24))

        image.load(checked)
        color = QtGui.QColor(common.SELECTION)
        for x in xrange(image.width()):
            for y in xrange(image.height()):
                color.setAlpha(image.pixelColor(x, y).alpha())
                image.setPixelColor(x, y, color)

        self._unchecked_pixmap = QtGui.QPixmap(
            ThumbnailEditor.smooth_copy(image, 24))


class TodoEditors(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(TodoEditors, self).__init__(parent=parent)
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(12, 12, 12, 12)
        self.layout().setSpacing(18)
        self.setMinimumWidth(300)

        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        # Widget used as a separator
        self.separator = QtWidgets.QLabel()
        pixmap = QtGui.QPixmap(QtCore.QSize(self.width(), 5))
        pixmap.fill(common.SELECTION)
        self.separator.setPixmap(pixmap)
        self.separator.setHidden(True)

        self.layout().insertWidget(0, self.separator)

        self.items = []


    def dragEnterEvent(self, event):
        """Accepting the drag operation."""
        if event.mimeData().hasFormat('browser/todo-drag'):
            event.acceptProposedAction()

        self.separator.setHidden(False)

    def dragLeaveEvent(self, event):
        self.separator.setHidden(True)

    def dragMoveEvent(self, event):
        self.get_index(event.pos())

    def get_index(self, pos):
        idx = 0
        for child in self.items:
            if child.rect().contains(pos):
                idx = self.layout().indexOf(child)

                mid_point = child.rect().center()
                print mid_point.y(), pos.y()

                if pos.y() > mid_point.y():
                    idx += 1
                elif pos.y() < mid_point.y():
                    idx += -1

        self.layout().removeWidget(self.separator)
        self.layout().insertWidget(idx, self.separator)
        self.separator.setHidden(False)



class TodoItemsWidget(QtWidgets.QScrollArea):
    """Main widget containing the qlist widget items."""
    def __init__(self, parent=None):
        super(TodoItemsWidget, self).__init__(parent=parent)
        self.setObjectName('todoitemswrapper')
        self.setMouseTracking(True)
        self.setWidgetResizable(True)
        self._createUI()

        common.set_custom_stylesheet(self)
        self.setStyleSheet(
            '{}\n{}'.format(
                self.styleSheet(),
                """QScrollArea#todoitemswrapper {
                    background-color: lightgray;
                }
                """
            )
        )

    def _createUI(self):
        self.editors = TodoEditors()
        self.setMinimumWidth(self.editors.minimumWidth() + 6)
        self.setWidget(self.editors)

    def add_item(self, text=None, checked=False):
        """Adds a new item the layout."""
        row = QtWidgets.QWidget()

        QtWidgets.QHBoxLayout(row)
        row.layout().setContentsMargins(0, 0, 0, 0)
        row.layout().setSpacing(12)

        checkbox = CheckBoxButton(checked=not checked)
        editor = TodoItemEditor(text, checked=not checked)
        drag = DragIndicatorButton(checked=not checked)

        def _bool(b, widget=None):
            widget.setDisabled(not b)

        import functools

        checkbox.clicked.connect(functools.partial(_bool, widget=editor))
        checkbox.clicked.connect(functools.partial(_bool, widget=drag))

        row.layout().addWidget(checkbox)
        row.layout().addWidget(editor, 1)
        row.layout().addWidget(drag)

        self.editors.layout().insertWidget(0, row)
        self.editors.items.append(row)

        checkbox.clicked.emit(checkbox._checked)

    def get_data(self):
        data = {}



if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = TodoItemsWidget()
    widget.add_item('Hello world', checked=True)
    widget.add_item()
    widget.show()
    app.exec_()
