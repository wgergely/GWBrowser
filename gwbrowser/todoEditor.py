# -*- coding: utf-8 -*-

"""Defines the widgets needed to add and modify notes and todo-type annotions
for an Bookmark or an Asset.

`TodoEditorWidget` is the top widget. It reads the asset configuration file
and loads stored todo items. The todo items support basic HTML elements but
embedding media resources are not supported.

Methods:
    TodoEditorWidget.add_item(): Main function to add a new todo item.

"""

import uuid
import os
import time
import functools
from PySide2 import QtWidgets, QtGui, QtCore

from gwbrowser.imagecache import oiio_make_thumbnail
import gwbrowser.common as common
from gwbrowser.common_ui import add_row, add_label, ClickableIconButton, PaintedLabel, PaintedButton
from gwbrowser.settings import AssetSettings
from gwbrowser.imagecache import ImageCache



class Highlighter(QtGui.QSyntaxHighlighter):
    """Class responsible for highlighting urls"""

    def highlightBlock(self, text):
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
            font = self.document().defaultFont()
            char_format.setFont(font)

            if flags == common.NoHighlightFlag:
                self.setFormat(start, end, char_format)
                break

            if flags & common.HeadingHighlight:
                char_format.setFontWeight(QtGui.QFont.Bold)
                char_format.setFontPointSize(
                    font.pointSize() + 0 + (6 - len(match)))
                char_format.setFontCapitalization(QtGui.QFont.AllUppercase)
                if len(match) > 1:
                    char_format.setUnderlineStyle(
                        QtGui.QTextCharFormat.SingleUnderline)
                    char_format.setFontPointSize(
                        font.pointSize() + 1)
                self.setFormat(0, len(text), char_format)
                break
            # elif flags & common.QuoteHighlight:
            #     char_format.setForeground(QtGui.QColor(100, 100, 100))
            #     char_format.setBackground(QtGui.QColor(230, 230, 230))
            #     self.setFormat(0, len(text), char_format)
            #     break
            #
            # if flags & common.CodeHighlight:
            #     char_format.setFontWeight(QtGui.QFont.Bold)
            #     char_format.setForeground(common.FAVOURITE)
            #     self.setFormat(start, end, char_format)
            # if flags & common.BoldHighlight:
            #     char_format.setFontWeight(QtGui.QFont.Bold)
            #     self.setFormat(start, end, char_format)
            # if flags & common.ItalicHighlight:
            #     char_format.setFontItalic(True)
            #     self.setFormat(start, end, char_format)
        return


class TodoItemEditor(QtWidgets.QTextBrowser):
    """Custom QTextBrowser widget for writing `Todo`'s.

    The editor automatically sets its size to accommodate the contents of the document.
    Some of the code has been lifted and implemented from Cameel's implementation.

    https://github.com/cameel/auto-resizing-text-edit/

    """

    def __init__(self, text=None, checked=False, parent=None):
        super(TodoItemEditor, self).__init__(parent=parent)
        self.setDisabled(checked)
        self.document().setDocumentMargin(8)

        self.highlighter = Highlighter(self.document())
        self.setOpenExternalLinks(True)
        self.setOpenLinks(True)
        self.setReadOnly(False)
        self.setTextInteractionFlags(
            QtCore.Qt.TextBrowserInteraction | QtCore.Qt.TextEditorInteraction)

        metrics = QtGui.QFontMetrics(self.document().defaultFont())
        metrics.width(u'   ')
        self.setTabStopWidth(common.MARGIN)

        self.setUndoRedoEnabled(True)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Fixed
        )
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setMouseTracking(True)

        self.document().contentsChanged.connect(self.contentChanged)
        self.document().setHtml(text)

        self.anchorClicked.connect(self.open_url)

    @QtCore.Slot()
    def contentChanged(self):
        """Sets the height of the editor."""
        self.setFixedHeight(
            self.heightForWidth()
        )

    def get_minHeight(self):
        """Returns the desired minimum height of the editor."""
        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSizeF(11.0)
        metrics = QtGui.QFontMetrics(font)
        line_height = (metrics.lineSpacing()) * 1  # Lines tall
        return line_height

    def get_maxHeight(self):
        """Returns the desired minimum height of the editor."""
        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSizeF(11.0)
        metrics = QtGui.QFontMetrics(font)
        line_height = (metrics.lineSpacing()) * 35  # Lines tall
        return line_height

    def heightForWidth(self):
        """https://raw.githubusercontent.com/cameel/auto-resizing-text-edit/master/auto_resizing_text_edit/auto_resizing_text_edit.py"""
        document = self.document().clone()
        height = document.size().height()

        if height < self.get_minHeight():
            return self.get_minHeight()
        if height > self.get_maxHeight():
            return self.get_maxHeight()
        return height + 4

    def keyPressEvent(self, event):
        """I'm defining custom key events here, the default behaviour is pretty poor.

        In a dream-scenario I would love to implement most of the functions
        of how atom behaves.

        """
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

    def dragEnterEvent(self, event):
        """Checking we can consume the content of the drag data..."""
        if not self.canInsertFromMimeData(event.mimeData()):
            return
        event.accept()

    def dropEvent(self, event):
        """Custom drop event to add content from mime-data."""
        index = self.parent().parent().parent().parent().parent().index
        if not index.isValid():
            return

        if not self.canInsertFromMimeData(event.mimeData()):
            return
        event.accept()

        mimedata = event.mimeData()
        self.insertFromMimeData(mimedata)

    def showEvent(self, event):
        self.setFixedHeight(self.heightForWidth())

    def canInsertFromMimeData(self, mimedata):
        """Checks if we can insert from the given mime-type."""
        if mimedata.hasUrls():
            return True
        if mimedata.hasHtml():
            return True
        if mimedata.hasText():
            return True
        if mimedata.hasImage():
            return True
        return False

    def insertFromMimeData(self, mimedata):
        """We can insert media using our image-cache - eg any image-content from
        the clipboard we will save into our cache folder.

        """
        index = self.parent().parent().parent().parent().parent().index
        if not index.isValid():
            return

        def img(url): return '<p><img src="{url}" width="{width}" alt="{url}"><br><a href="{url}">{url}</a></p>'.format(
            url=url.toLocalFile(),
            width=560)

        def href(url): return '<p><a href="{url}">{url}</a></p>'.format(
            style='align:left;',
            url=url.toLocalFile())

        # We save our image into the cache for safe-keeping
        if mimedata.hasUrls():
            thumbnail_info = QtCore.QFileInfo(
                index.data(common.ThumbnailPathRole))
            for url in mimedata.urls():
                file_info = QtCore.QFileInfo(url.path())
                if file_info.suffix() in common.get_oiio_extensions():
                    dest = u'{}/{}.{}'.format(
                        thumbnail_info.dir().path(),
                        uuid.uuid4(),
                        thumbnail_info.suffix()
                    )
                    oiio_make_thumbnail(
                        QtCore.QModelIndex(),
                        source=url.toLocalFile(),
                        dest=dest
                    )
                    url = QtCore.QUrl.fromLocalFile(dest)
                    self.insertHtml(img(url))
                else:
                    self.insertHtml(href(url))

        if mimedata.hasHtml():
            html = mimedata.html()
            self.insertHtml(u'<br>{}<br>'.format(html))
        elif mimedata.hasText():
            text = mimedata.text()
            self.insertHtml(u'<br>{}<br>'.format(text))

        # If the mime has any image data we will save it as a temp image file
        if mimedata.hasImage():
            image = mimedata.imageData()
            if not image.isNull():
                thumbnail_info = QtCore.QFileInfo(
                    index.data(common.ThumbnailPathRole))
                dest = u'{}/{}.{}'.format(
                    thumbnail_info.dir().path(),
                    uuid.uuid4(),
                    thumbnail_info.suffix()
                )
                if image.save(dest):
                    url = QtCore.QUrl.fromLocalFile(dest)
                    self.insertHtml(img(url))

    def open_url(self, url):
        """We're handling the clicking of anchors here manually."""
        if not url.isValid():
            return
        file_info = QtCore.QFileInfo(url.url())
        if file_info.exists():
            common.reveal(file_info.filePath())
            QtGui.QClipboard().setText(file_info.filePath())
        else:
            QtGui.QDesktopServices.openUrl(url)


class CustomButton(QtWidgets.QLabel):
    """Custom button used to draw the editor control buttons."""
    pressed = QtCore.Signal()
    message = QtCore.Signal(unicode)

    def __init__(self, button, size=32.0, message=None, parent=None):
        super(CustomButton, self).__init__(parent=parent)
        self.button = button
        self._size = size
        self._message = message

        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedHeight(self._size)
        self.setFixedWidth(self._size)
        self.setPixmap(self._pixmap())

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        # Checking if the cursor is over the button when released
        cursor = QtGui.QCursor()
        pos = self.mapFromGlobal(cursor.pos())
        if not self.rect().contains(pos):
            return

        self.pressed.emit()

    def enterEvent(self, event):
        self.setPixmap(self._pixmap(type=event.type()))
        self.update()

        if self._message:
            self.message.emit(self._message)

    def leaveEvent(self, event):
        self.setPixmap(self._pixmap(type=event.type()))
        self.update()

    def _pixmap(self, type=QtCore.QEvent.Leave):
        if self.button is None:
            return QtGui.QPixmap(self._size, self._size)

        if type == QtCore.QEvent.Leave:
            return ImageCache.get_rsc_pixmap(
                self.button, common.SECONDARY_BACKGROUND, self._size)
        if type == QtCore.QEvent.Enter:
            return ImageCache.get_rsc_pixmap(
                self.button, common.FAVOURITE, self._size)

        return QtGui.QPixmap(self._size, self._size)


class RemoveNoteButton(CustomButton):
    def __init__(self, parent=None):
        super(RemoveNoteButton, self).__init__(
            u'remove', size=common.INLINE_ICON_SIZE, parent=parent)
        self.pressed.connect(self.remove_note)

    def remove_note(self):
        self.setUpdatesEnabled(False)

        editors_widget = self.parent().parent()
        idx = editors_widget.items.index(self.parent())
        row = editors_widget.items.pop(idx)
        editors_widget.layout().removeWidget(row)
        row.deleteLater()

        self.setUpdatesEnabled(True)


class RemoveButton(CustomButton):
    """Custom icon button to remove an item or close the editor."""

    def __init__(self, size=32.0, parent=None):
        super(RemoveButton, self).__init__(u'remove', size=size, parent=parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        """Accepting the drag operation."""
        if event.mimeData().hasFormat(u'gwbrowser/todo-drag'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Drop event responsible for deleting an item from the todo list."""
        self.setUpdatesEnabled(False)

        editors_widget = self.parent().parent().todoeditors_widget
        idx = editors_widget.items.index(event.source())
        row = editors_widget.items.pop(idx)
        editors_widget.layout().removeWidget(row)
        row.deleteLater()

        self.setUpdatesEnabled(True)


class DragIndicatorButton(QtWidgets.QLabel):
    """Dotted button indicating a draggable item.

    The button is responsible for initiating a QDrag operation and setting the
    mime data. The data is populated with the `TodoEditor`'s text and the
    custom mime type (u'gwbrowser/todo-drag'). The latter is needed to accept the drag operation
    in the target drop widet.
    """

    def __init__(self, checked=False, parent=None):
        super(DragIndicatorButton, self).__init__(parent=parent)
        self.dragStartPosition = None

        self.setDisabled(checked)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setDisabled(self.isEnabled())

    def setDisabled(self, b):
        """Custom disabled function."""
        if b:
            pixmap = ImageCache.get_rsc_pixmap(
                u'drag_indicator', common.FAVOURITE, common.INLINE_ICON_SIZE)
        else:
            pixmap = ImageCache.get_rsc_pixmap(
                u'drag_indicator', common.SECONDARY_BACKGROUND, common.INLINE_ICON_SIZE)

        self.setPixmap(pixmap)

    def mousePressEvent(self, event):
        """Setting the starting drag position here."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.dragStartPosition = event.pos()

    def mouseMoveEvent(self, event):
        """The drag operation is initiated here."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        app = QtWidgets.QApplication.instance()
        left_button = event.buttons() & QtCore.Qt.LeftButton
        if not left_button:
            return

        parent_widget = self.parent()
        editor = parent_widget.findChild(TodoItemEditor)
        drag = QtGui.QDrag(parent_widget)

        # Setting Mime Data
        mime_data = QtCore.QMimeData()
        mime_data.setData(u'gwbrowser/todo-drag', QtCore.QByteArray(''))
        drag.setMimeData(mime_data)

        # Drag pixmap
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
        pixmap = QtGui.QPixmap(parent_widget.size())

        painter = QtGui.QPainter()
        painter.begin(pixmap)
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(200, 200, 200, 255)))
        painter.drawRect(pixmap.rect())
        painter.end()

        overlay_widget = QtWidgets.QLabel(parent=parent_widget)
        overlay_widget.setFixedSize(parent_widget.size())
        overlay_widget.setPixmap(pixmap)

        # Preparing the drag...
        remove_button = parent_widget.parent().parent(
        ).parent().parent().findChild(RemoveButton)
        pixmap = ImageCache.get_rsc_pixmap(
            u'remove', common.REMOVE, 32)
        remove_button.setPixmap(pixmap)
        parent_widget.parent().separator.setHidden(False)
        overlay_widget.show()

        # Starting the drag...
        drag.exec_(QtCore.Qt.CopyAction)

        # Cleanup after drag has finished...
        overlay_widget.close()
        overlay_widget.deleteLater()
        parent_widget.parent().separator.setHidden(True)
        pixmap = ImageCache.get_rsc_pixmap(
            u'remove', common.FAVOURITE, 32)
        remove_button.setPixmap(pixmap)


class CheckBoxButton(QtWidgets.QLabel):
    """Custom checkbox used for Todo Items."""

    clicked = QtCore.Signal(bool)

    def __init__(self, checked=False, parent=None):
        super(CheckBoxButton, self).__init__(parent=parent)
        self._checked = checked
        self._checked_pixmap = None
        self._unchecked_pixmap = None

        self.setAttribute(QtCore.Qt.WA_Hover, True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.set_pixmap(self._checked)

        self._connectSignals()

    @property
    def checked(self):
        return self._checked

    def _connectSignals(self):
        self.clicked.connect(self.set_pixmap)

    def set_pixmap(self, checked):
        if checked:
            pixmap = ImageCache.get_rsc_pixmap(
                u'checkbox_unchecked', common.SECONDARY_BACKGROUND, 18)
            self.setPixmap(pixmap)
        else:
            pixmap = ImageCache.get_rsc_pixmap(
                u'checkbox_checked', common.FAVOURITE, 18)
            self.setPixmap(pixmap)

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self._checked = not self._checked
        self.clicked.emit(self._checked)


class Separator(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super(Separator, self).__init__(parent=parent)
        pixmap = QtGui.QPixmap(QtCore.QSize(4096, 1))
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
        if event.mimeData().hasFormat(u'gwbrowser/todo-drag'):
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
        o = 0
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        self.separator = Separator(parent=self)
        self.drop_target_index = -1

        self.items = []

        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def dragEnterEvent(self, event):
        """Accepting the drag operation."""
        if event.mimeData().hasFormat(u'gwbrowser/todo-drag'):
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
            text = event.source().findChild(TodoItemEditor).document().toHtml()
            self.parent().parent().parent().add_item(idx=0, text=text, checked=False)
            self.separator.setHidden(True)
            return

        # Change internal order
        self.setUpdatesEnabled(False)

        self.items.insert(
            self.drop_target_index,
            self.items.pop(self.items.index(event.source()))
        )
        self.layout().removeWidget(event.source())
        self.layout().insertWidget(self.drop_target_index, event.source(), 0)

        self.setUpdatesEnabled(True)

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


class TodoItemWidget(QtWidgets.QWidget):
    """The item-wrapper widget holding the checkbox, drag indicator and editor widgets."""

    def __init__(self, parent=None):
        super(TodoItemWidget, self).__init__(parent=parent)
        self.editor = None
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self._createUI()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(12, 12, 12, 12)
        self.layout().setSpacing(6)


class TodoEditorWidget(QtWidgets.QWidget):
    """Main widget used to view and edit and add Notes and Tasks."""

    def __init__(self, index, parent=None):
        super(TodoEditorWidget, self).__init__(parent=parent)
        self.todoeditors_widget = None
        self._index = index
        self.read_only = False

        self.lockstamp = int(round(time.time() * 1000))
        self.save_timer = QtCore.QTimer(parent=self)
        self.save_timer.setInterval(2000)
        self.save_timer.setSingleShot(False)
        self.save_timer.timeout.connect(self.save_settings)

        self.setWindowTitle(u'Notes and Comments')
        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self._createUI()
        self.refresh()
        self.installEventFilter(self)

        self.create_lockfile()



    def _updateGeometry(self, *args, **kwargs):
        geo = self.parent().viewport().rect()
        self.resize(geo.width(), geo.height())

    def _createUI(self):
        """Creates the ui layout."""
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(o, o, o, o)

        # Top row
        height = common.ROW_BUTTONS_HEIGHT * 0.8
        row = add_row('', height=height, parent=self)
        row.layout().setSpacing(8)

        # Thumbnail
        thumbnail = QtWidgets.QLabel(parent=self)
        thumbnail.setScaledContents(True)
        thumbnail.setFixedHeight(height)
        thumbnail.setFixedWidth(height)
        if self.parent() and self.index.isValid():
            pixmap = QtGui.QPixmap()
            pixmap.convertFromImage(self.index.data(common.ThumbnailRole))
        else:
            pixmap = ImageCache.get_rsc_pixmap(u'todo', common.SECONDARY_BACKGROUND, height, opacity=0.5)
        thumbnail.setPixmap(pixmap)

        # Name label
        if self.index.isValid():
            p = self.index.data(common.ParentRole)
            text = u' {} - {} '.format(p[-1], p[-2]).upper()
        else:
            text = u'Notes and Tasksd'
        if len(text) >= 48:
            text = u'{}...{}'.format(text[0:22], text[-22:])
        label = PaintedLabel(text, color=common.SECONDARY_BACKGROUND, size=common.LARGE_FONT_SIZE, parent=self)

        row.layout().addWidget(thumbnail, 0)
        row.layout().addWidget(label, 1)
        row.layout().addStretch(1)

        # Add button
        self.add_button = CustomButton(u'add', size=height, parent=self)
        self.add_button.pressed.connect(self.add_new_item)
        row.layout().addWidget(self.add_button, 0)

        self.refresh_button = CustomButton(u'refresh', size=height, parent=self)
        self.refresh_button.pressed.connect(self.refresh)
        row.layout().addWidget(self.refresh_button, 0)

        self.remove_button = RemoveButton(size=height, parent=self)
        self.remove_button.pressed.connect(self.close)
        row.layout().addWidget(self.remove_button, 0)

        self.todoeditors_widget = TodoEditors(parent=self)
        self.setMinimumWidth(self.todoeditors_widget.minimumWidth() + 6)
        self.setMinimumHeight(100)

        self.scrollarea = QtWidgets.QScrollArea()
        self.scrollarea.setWidgetResizable(True)
        self.scrollarea.setWidget(self.todoeditors_widget)
        # self.scrollarea.setFocusPolicy(QtCore.Qt.NoFocus)

        self.scrollarea.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.scrollarea.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.layout().addWidget(row)
        self.layout().addWidget(self.scrollarea)

        common.set_custom_stylesheet(self)

    def refresh(self):
        """Populates the list based on the saved configuration file."""
        if not self.index.isValid():
            return

        # First we will delete the existing items and re-populate the list
        # from the configuration file.
        for idx in reversed(xrange(len(list(self.todoeditors_widget.items)))):
            row = self.todoeditors_widget.items.pop(idx)
            self.todoeditors_widget.layout().removeWidget(row)
            row.deleteLater()

        settings = AssetSettings(self.index)
        items = settings.value(u'config/todos')
        if not items:
            return

        for k in items:
            self.add_item(
                text=items[k][u'text'],
                checked=items[k][u'checked']
            )

    @property
    def index(self):
        """The path used to initialize the widget."""
        return self._index

    def eventFilter(self, widget, event):
        """Using  the custom event filter to paint the background."""
        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            font = QtGui.QFont(common.SecondaryFont)
            font.setPointSize(common.MEDIUM_FONT_SIZE)
            painter.setFont(font)

            rect = QtCore.QRect(self.rect())

            painter.setBrush(common.TEXT)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRect(rect)

            center = rect.center()
            rect.setWidth(rect.width() - common.MARGIN)
            rect.setHeight(rect.height() - common.MARGIN)
            rect.moveCenter(center)

            text = u'You can add a new note by clicking the pencil icon on the top.'
            text = text if not len(self.todoeditors_widget.items) else u''
            common.draw_aliased_text(
                painter, font, rect, text, QtCore.Qt.AlignCenter, common.FAVOURITE)
            painter.end()
        return False

    def _get_next_enabled(self, n):
        hasEnabled = False
        for i in xrange(len(self.todoeditors_widget.items)):
            item = self.todoeditors_widget.items[i]
            editor = item.findChild(TodoItemEditor)
            if editor.isEnabled():
                hasEnabled = True
                break

        if not hasEnabled:
            return -1

        # Finding the next enabled editor
        for _ in xrange(len(self.todoeditors_widget.items) - n):
            n += 1
            if n >= len(self.todoeditors_widget.items):
                return self._get_next_enabled(-1)
            item = self.todoeditors_widget.items[n]
            editor = item.findChild(TodoItemEditor)
            if editor.isEnabled():
                return n

    def key_tab(self):
        """Defining tabbing forward between items."""
        if not self.todoeditors_widget.items:
            return

        n = 0
        for n, item in enumerate(self.todoeditors_widget.items):
            editor = item.findChild(TodoItemEditor)
            if editor.hasFocus():
                break

        n = self._get_next_enabled(n)
        if n > -1:
            item = self.todoeditors_widget.items[n]
            editor = item.findChild(TodoItemEditor)
            editor.setFocus()
            self.scrollarea.ensureWidgetVisible(
                editor, ymargin=editor.height())

    def key_return(self,):
        """Control enter toggles the state of the checkbox."""
        for item in self.todoeditors_widget.items:
            editor = item.findChild(TodoItemEditor)
            checkbox = item.findChild(CheckBoxButton)
            if editor.hasFocus():
                if not editor.document().toPlainText():
                    idx = self.todoeditors_widget.items.index(editor.parent())
                    row = self.todoeditors_widget.items.pop(idx)
                    self.todoeditors_widget.layout().removeWidget(row)
                    row.deleteLater()
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

    def add_item(self, idx=None, text=None, checked=False):
        """Creates a new widget containing the checkbox, editor and drag widgets.

        The method is responsible for adding the item the EditorsWidget layout
        and the EditorsWidget.items property.

        """
        def toggle_disabled(b, widget=None):
            widget.setDisabled(not b)

        item = TodoItemWidget(parent=self)

        checkbox = CheckBoxButton(checked=not checked, parent=item)
        checkbox.setFocusPolicy(QtCore.Qt.NoFocus)
        editor = TodoItemEditor(text, checked=not checked, parent=item)
        editor.setFocusPolicy(QtCore.Qt.StrongFocus)
        drag = DragIndicatorButton(checked=False, parent=item)
        drag.setFocusPolicy(QtCore.Qt.NoFocus)
        remove = RemoveNoteButton(parent=item)
        remove.setFocusPolicy(QtCore.Qt.NoFocus)

        checkbox.clicked.connect(
            functools.partial(toggle_disabled, widget=editor))
        checkbox.clicked.connect(
            functools.partial(toggle_disabled, widget=drag))

        item.layout().addWidget(checkbox)
        item.layout().addWidget(drag)
        item.layout().addWidget(editor, 1)
        item.layout().addWidget(remove)

        if idx is None:
            self.todoeditors_widget.layout().addWidget(item, 0)
            self.todoeditors_widget.items.append(item)
        else:
            self.todoeditors_widget.layout().insertWidget(idx, item, 0)
            self.todoeditors_widget.items.insert(idx, item)

        checkbox.clicked.emit(checkbox._checked)
        editor.setFocus()
        item.editor = editor
        return item

    @QtCore.Slot()
    def save_settings(self):
        """Saves the current list of todo items to the assets configuration file."""
        if not self.index.isValid():
            return
        data = self._collect_data()
        settings = AssetSettings(self.index)
        settings.setValue(u'config/todos', data)
        model = self.index.model()
        model.setData(self.index, len(data), role=common.TodoCountRole)


    @QtCore.Slot()
    def add_new_item(self, html=u'', idx=0):
        """Adds a new item with some default styling."""
        self.add_item(text=html, idx=idx)

    def _collect_data(self):
        """Returns all the items found in the todo widget."""
        data = {}
        for n in xrange(len(self.todoeditors_widget.items)):
            item = self.todoeditors_widget.items[n]
            editor = item.findChild(TodoItemEditor)
            checkbox = item.findChild(CheckBoxButton)
            if not editor.document().toPlainText():
                continue
            data[n] = {
                u'checked': not checkbox.checked,
                u'text': editor.document().toHtml(),
            }
        return data

    def create_lockfile(self):
        """Creates a lock on the current file so it can't be edited by other users.
        It will also start the auto-save timer.
        """
        if not self.parent():
            return

        if not self.index.isValid():
            return

        settings = AssetSettings(self.index)

        if settings.value(u'config/todo_open'):
            self.add_button.hide()
            self.todoeditors_widget.setDisabled(True)
            return

        settings.setValue(u'config/todo_open', True)
        settings.setValue(u'config/todo_lockstamp', int(self.lockstamp))
        self.refresh_button.hide()
        self.save_timer.start()

        print u'# Lock created.'

    def remove_lockfile(self):
        """Saving the contents on close/hide."""
        if self.index.isValid():
            settings = AssetSettings(self.index)
            if not settings.value(u'config/todo_open'):
                return
            val = settings.value(u'config/todo_lockstamp')
            if val is None:
                return
            if int(val) != self.lockstamp:
                return
            settings.setValue(u'config/todo_lockstamp', None)
            settings.setValue(u'config/todo_open', False)
            print '# Lock removed'

    def showEvent(self, event):
        self.setFocus(QtCore.Qt.OtherFocusReason)

    def hideEvent(self, event):
        self.remove_lockfile()

    def sizeHint(self):
        """Custom size."""
        if not self.parent():
            return QtCore.QSize(800, 600)
        return self.parent().viewport().rect().size()



if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    index = QtCore.QModelIndex()
    widget = TodoEditorWidget(index)
    item = widget.add_item(
        text=u'This is a test link:\n\n\n\nClick this: file://gordo/jobs')
    widget.show()
    app.exec_()
