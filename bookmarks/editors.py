# -*- coding: utf-8 -*-
"""Widgets used to edit data in the list widgets."""

import os
from PySide2 import QtWidgets, QtGui, QtCore

import bookmarks._scandir as _scandir
import bookmarks.common as common
import bookmarks.bookmark_db as bookmark_db
from bookmarks.common_ui import add_row, PaintedLabel, ClickableIconButton
import bookmarks.images as images
import bookmarks.delegate as delegate
import bookmarks.common_ui as common_ui


class DescriptionEditorWidget(common_ui.NameBase):
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

        if index.data(common.TypeRole) == common.FileItem:
            k = index.data(QtCore.Qt.StatusTipRole)
        elif index.data(common.TypeRole) == common.SequenceItem:
            k = common.proxy_path(index)

        db = bookmark_db.get_db(index)
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
        rectangles = self.parent().itemDelegate().get_rectangles(rect)
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
        self.editor_widget = common_ui.NameBase(parent=self, transparent=True)

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
        painter.drawRoundedRect(rect, common.INDICATOR_WIDTH(), common.INDICATOR_WIDTH())
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


class ThumbnailLabel(QtWidgets.QLabel):
    """Custom QLabel to select a thumbnail."""
    clicked = QtCore.Signal(unicode)

    def __init__(self, path, size, parent=None):
        super(ThumbnailLabel, self).__init__(parent=parent)
        self._path = path

        self.setFixedWidth(size)
        self.setFixedHeight(size)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum)

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.clicked.emit(self._path)

    def paintEvent(self, event):
        super(ThumbnailLabel, self).paintEvent(event)

        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter = QtGui.QPainter()
        painter.begin(self)

        if hover:
            painter.setPen(common.TEXT)
            common.draw_aliased_text(
                painter,
                common.font_db.primary_font(common.MEDIUM_FONT_SIZE()),
                self.rect(),
                self._path.split(
                    u'/').pop().replace(u'thumb_', u'').split(u'_')[0],
                QtCore.Qt.AlignCenter,
                common.TEXT_SELECTED
            )
            painter.end()
            return

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(0, 0, 0, 33))
        painter.drawRect(self.rect())
        painter.end()


class ThumbnailsWidget(QtWidgets.QWidget):
    """The widget used to let the end-user pick a new thumbnail."""
    thumbnailSelected = QtCore.Signal(unicode)
    thumbnail_size = common.ASSET_ROW_HEIGHT()

    def __init__(self, parent=None):
        super(ThumbnailsWidget, self).__init__(parent=parent)
        self.columns = 5
        
        self.setWindowFlags(QtCore.Qt.Widget)
        self.setWindowTitle(u'Select thumbnail')

        self._create_UI()

    def _create_UI(self):
        """Using scandir we will get all the installed thumbnail files from the rsc directory."""
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN()

        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)

        widget = QtWidgets.QWidget()
        widget.setStyleSheet(
            'background-color: rgba({})'.format(common.rgb(common.SECONDARY_BACKGROUND)))
        # widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        # widget.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        QtWidgets.QGridLayout(widget)
        widget.layout().setAlignment(QtCore.Qt.AlignCenter)
        widget.layout().setContentsMargins(
            common.INDICATOR_WIDTH(),
            common.INDICATOR_WIDTH(),
            common.INDICATOR_WIDTH(),
            common.INDICATOR_WIDTH())
        widget.layout().setSpacing(common.INDICATOR_WIDTH())

        scrollarea = QtWidgets.QScrollArea(parent=self)
        scrollarea.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        scrollarea.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        scrollarea.setWidgetResizable(True)
        scrollarea.setWidget(widget)
        self.layout().addWidget(scrollarea, 1)

        row = 0
        path = u'{}/../rsc'.format(__file__)
        path = os.path.normpath(os.path.abspath(path))

        idx = 0
        for entry in _scandir.scandir(path):
            if not entry.name.startswith(u'thumb_'):
                continue

            name = entry.name.replace(u'.png', u'')
            pixmap = images.ImageCache.get_rsc_pixmap(
                name, None, self.thumbnail_size)
            if pixmap.isNull():
                continue

            label = ThumbnailLabel(
                entry.path.replace(u'\\', u'/'),
                self.thumbnail_size,
                parent=self
            )

            label.setPixmap(pixmap)

            column = idx % self.columns
            if column == 0:
                row += 1
            widget.layout().addWidget(label, row, column)
            label.clicked.connect(self.thumbnailSelected)
            label.clicked.connect(self.close)

            idx += 1

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setBrush(common.SECONDARY_BACKGROUND)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        o = common.INDICATOR_WIDTH() * 2.0
        painter.drawRoundedRect(
            self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o)),
            o, o
        )
        painter.end()

    def keyPressEvent(self, event):
        """Closes the widget on any key-press."""
        self.close()

    def showEvent(self, event):
        self.setFocus(QtCore.Qt.PopupFocusReason)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = ThumbnailsWidget()
    widget.show()
    app.exec_()
