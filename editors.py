# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, W0613, R0201


"""Widgets used to edit data in the list widgets."""


from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common
from mayabrowser.settings import AssetSettings

class ThumbnailViewer(QtWidgets.QLabel):
    """Widget used to view a thumbnail."""

    def __init__(self, index, parent=None):
        super(ThumbnailViewer, self).__init__(parent=parent)
        settings = AssetSettings(index)
        file_info = QtCore.QFileInfo(settings.thumbnail_path())

        if not file_info.exists():
            return

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.CustomizeWindowHint |
            QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self.setStyleSheet('background-color: rgba(50,50,50,50)')
        self.setAlignment(QtCore.Qt.AlignCenter)
        # pixmap = common.cache_image(settings.thumbnail_path(), common.THUMBNAIL_IMAGE_SIZE)
        pixmap = QtGui.QPixmap(settings.thumbnail_path())
        self.setPixmap(pixmap)


        # print pixmap.isValid()
        self.show()

    def paintEvent(self, event):
        """Custom paint event"""
        painter = QtGui.QPainter(self)

        # Draw background. Aside from aesthetics, this makes the full
        # tool region accept mouse events.
        painter.setBrush(QtGui.QColor(0, 0, 0, 150))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(event.rect())

        rect = self.pixmap().rect()


        width = 2.0
        rect.moveTop((event.rect().height() / 2.0) - width)
        rect.moveTop(rect.top() - (rect.height() / 2.0))
        rect.moveLeft((event.rect().width() / 2.0) - width)
        rect.moveLeft(rect.left() - (rect.width() / 2.0))
        rect.setWidth(rect.width() + (width * 1.5))
        rect.setHeight(rect.height() + (width * 1.5))

        painter.setBrush(QtCore.Qt.NoBrush)
        pen = QtGui.QPen(common.SELECTION)
        pen.setWidth(2.0)
        painter.setPen(pen)
        painter.drawRect(rect)

        painter.end()
        super(ThumbnailViewer, self).paintEvent(event)

    def _fit_screen_geometry(self):
        # Compute the union of all screen geometries, and resize to fit.
        app = QtCore.QCoreApplication.instance()
        rect = app.desktop().availableGeometry(self.parent())
        self.setGeometry(rect)

    def showEvent(self, event):
        self._fit_screen_geometry()


    def keyPressEvent(self, event):
        self.close()

    def mousePressEvent(self, event):
        self.close()

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.close()

class ThumbnailEditor(QtWidgets.QFileDialog):
    """Editor widget used by the Asset- and FileWidget delegateself.

    The editor is responsible for associating a thumbnail image with
    an Asset- or FileWidget item via a file-browser prompt.

    """

    def __init__(self, index, parent=None):
        super(ThumbnailEditor, self).__init__(parent=parent)
        settings = AssetSettings(index)
        # Opening dialog to select an image file
        self.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        self.setViewMode(QtWidgets.QFileDialog.List)
        self.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        self.setNameFilter('Image files (*.png *.jpg  *.jpeg)')
        self.setDirectory(QtCore.QDir(
            index.data(QtCore.Qt.StatusTipRole)))
        self.setOption(
            QtWidgets.QFileDialog.DontUseCustomDirectoryIcons, True)

        if not self.exec_():
            return
        if not self.selectedFiles():
            return

        # Saving the thumbnail
        image = QtGui.QImage()
        image.load(next(f for f in self.selectedFiles()))
        image = common.resize_image(image, common.THUMBNAIL_IMAGE_SIZE)
        image.save(settings.thumbnail_path())

        # Re-cache
        common.delete_image(settings.thumbnail_path(), delete_file=False)
        height = self.parent().visualRect(index).height() - 2
        common.cache_image(settings.thumbnail_path(), height)


class DescriptionEditorWidget(QtWidgets.QWidget):
    """Note editor baseclass."""

    def __init__(self, index, parent=None):
        super(DescriptionEditorWidget, self).__init__(parent=parent)
        self._index = index

        self.editor = None
        self.settings = AssetSettings(index)
        self._createUI()

        self.editor.focusOutEvent = self.focusOutEvent
        self.editor.installEventFilter(self)
        self.installEventFilter(self)

        self._connectSignals()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self.set_size(self.parent().viewport().size())
        self.setFocusProxy(self.editor)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.editor.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.show()
        self.editor.setFocus()

        self.editor.setText(self.settings.value('config/description'))
        self.editor.selectAll()

    def sizeHint(self):
        return QtCore.QSize(
            self.parent().visualRect(self._index).width(),
            self.parent().visualRect(self._index).height()
        )

    def set_size(self, size):
        """Sets the widget size."""
        rect = QtCore.QRect(self.parent().visualRect(self._index))
        rect.setLeft(rect.left() + 4 + rect.height())
        self.move(rect.left() + 1, rect.top() + 2)
        self.resize(size.width() - rect.left(), rect.height() - 1)

    def eventFilter(self, widget, event):
        """We're filtering the enter key event here, otherwise, the
        list widget would close open finishing editing.

        """
        if not event.type() == QtCore.QEvent.KeyPress:
            return False

        shift = event.modifiers() == QtCore.Qt.ShiftModifier

        escape = event.key() == QtCore.Qt.Key_Escape

        tab = event.key() == QtCore.Qt.Key_Tab
        backtab = event.key() == QtCore.Qt.Key_Backtab

        return_ = event.key() == QtCore.Qt.Key_Return
        enter = event.key() == QtCore.Qt.Key_Enter


        if escape:
            self.close()
            return True

        if enter or return_:
            self.action()
            self.close()
            return True

        if not shift and tab:
            self.action()
            self.parent().key_down()
            self.parent().key_tab()
            widget = DescriptionEditorWidget(self.parent().currentIndex(), parent=self.parent())
            widget.show()
            return True

        if (shift and tab) or backtab:
            self.action()
            self.parent().key_up()
            self.parent().key_tab()
            widget = DescriptionEditorWidget(self.parent().currentIndex(), parent=self.parent())
            widget.show()
            return True

        return False

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.close()

    def _connectSignals(self):
        """Connects signals."""
        self.editor.editingFinished.connect(self.action)
        self.parent().sizeChanged.connect(self.set_size)

    def _createUI(self):
        """Creates the layout."""
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(common.MARGIN * 1.5, 0, common.MARGIN * 0.5, 0)
        self.layout().setSpacing(6)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )

        self.editor = QtWidgets.QLineEdit()
        self.editor.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.editor.setTextMargins(0, 0, 0, 0)

        self.editor.setStyleSheet(
            'background-color: rgb(50,50,50);\
            color: rgba({},{},{},{});\
            font-family: "Roboto Medium"; font-size: 8pt;'.format(*common.TEXT_NOTE.getRgb())
        )

        label = QtWidgets.QLabel('Edit description')
        label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        label.setStyleSheet(
            'font-family: "Roboto Black";\
            font-size: 8pt;\
            color: rgba({},{},{},{});'.format(*common.TEXT.getRgb())
        )

        self.layout().addStretch(1)
        self.layout().addWidget(label, 1)
        self.layout().addWidget(self.editor, 1)
        self.layout().addStretch(1)

    def paintEvent(self, event):
        """Custom paint used to paint the background."""
        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            rect = QtCore.QRect()
            rect.setWidth(self.width())
            rect.setHeight(self.height())

            pen = QtGui.QPen(common.SELECTION)
            pen.setWidth(2)
            painter.setPen(pen)
            color = QtGui.QColor(common.BACKGROUND_SELECTED)
            painter.setBrush(QtGui.QBrush(color))
            painter.drawRect(rect)
            painter.end()

            return
        super(DescriptionEditorWidget, self).paintEvent(event)

    def action(self):
        """Main actions to run when the return key is pressed."""
        if self.settings.value('config/description') == self.editor.text():
            self.close()
            return

        source_index = self.parent().model().mapToSource(self._index)
        self.parent().model().sourceModel().setData(
            source_index,
            self.editor.text(),
            role=common.DescriptionRole
        )
        self.settings.setValue('config/description', self.editor.text())
        self.close()
