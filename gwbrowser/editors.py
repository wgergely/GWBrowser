# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, W0613, R0201

"""Widgets used to edit data in the list widgets."""


from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser.common as common
from gwbrowser.settings import AssetSettings
from gwbrowser.imagecache import ImageCache


class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super(ClickableLabel, self).__init__(parent=parent)
        self.setFixedSize(QtCore.QSize(
            common.ROW_BUTTONS_HEIGHT, common.ROW_BUTTONS_HEIGHT))
        self.setAlignment(QtCore.Qt.AlignCenter)

    def mouseReleaseEvent(self, event):
        """Only triggered when the left buttons is pressed."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()


class ThumbnailViewer(QtWidgets.QLabel):
    """Widget used to view a thumbnail."""

    def __init__(self, index, parent=None):
        super(ThumbnailViewer, self).__init__(parent=parent)
        self.setWindowFlags(
            QtCore.Qt.Dialog |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.setAlignment(QtCore.Qt.AlignCenter)

        # self.setFocusProxy(self.parent())
        self.reset_pixmap()
        self.show()

    def reset_pixmap(self):
        self.setStyleSheet(
            u'QLabel {background-color: rgba(50,50,50,50); color:rgba(200,200,200,255);}')
        index = self.parent().selectionModel().currentIndex()
        settings = AssetSettings(index)
        file_info = QtCore.QFileInfo(settings.thumbnail_path())

        if not index.isValid():
            self.clear()
            self.setText('Invalid selection.')
            return

        if not file_info.exists():
            self.clear()
            self.setText('No thumbnail found.')
            return

        pixmap = QtGui.QPixmap(settings.thumbnail_path())
        if pixmap.isNull():
            self.clear()
            self.setText('Unable to load pixmap.')
            return

        self.clear()
        self.setPixmap(pixmap)

    def paintEvent(self, event):
        """Custom paint event"""
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        painter.setBrush(QtGui.QColor(0, 0, 0, 170))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(self.rect())

        # Let's paint extra information:
        index = self.parent().selectionModel().currentIndex()
        if index.isValid():
            font = QtGui.QFont(common.PrimaryFont)
            metrics = QtGui.QFontMetrics(font)
            if self.pixmap():
                rect = self.rect()
                center = rect.center()
                rect.setHeight(metrics.height())
                rect.setWidth(rect.width() - (common.MARGIN * 4))
                rect.moveCenter(center)

                # Aligned to the bottom of the pixmap
                rect.moveTop(
                    rect.top() + self.pixmap().rect().height() / 2.0 + common.MARGIN)
                # Filename
                common.draw_aliased_text(painter, font, rect, index.data(
                    QtCore.Qt.StatusTipRole), QtCore.Qt.AlignCenter, common.TEXT)
                rect.moveTop(rect.center().y() + metrics.height())

                common.draw_aliased_text(painter, font, rect, index.data(
                    common.DescriptionRole), QtCore.Qt.AlignCenter, common.FAVOURITE)

        painter.end()
        super(ThumbnailViewer, self).paintEvent(event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Down:
            self.parent().key_down()
            self.reset_pixmap()
        elif event.key() == QtCore.Qt.Key_Up:
            self.parent().key_up()
            self.reset_pixmap()
        else:
            self.close()

    def _fit_screen_geometry(self):
        # Compute the union of all screen geometries, and resize to fit.
        app = QtCore.QCoreApplication.instance()
        rect = app.desktop().availableGeometry(self.parent())
        self.setGeometry(rect)

    def showEvent(self, event):
        self.setFocus()
        self.parent()._thumbnailvieweropen = self
        self._fit_screen_geometry()

    def hideEvent(self, event):
        self.parent()._thumbnailvieweropen = None

    def mousePressEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.close()

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.close()


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

        self.editor.setText(self.settings.value(u'config/description'))
        self.editor.selectAll()

    def sizeHint(self):
        return QtCore.QSize(
            self.parent().visualRect(self._index).width(),
            self.parent().visualRect(self._index).height()
        )

    def set_size(self, size):
        """Sets the widget size."""
        index = self.parent().model().mapFromSource(self._index)
        rect = QtCore.QRect(self.parent().visualRect(index))
        rect.setLeft(rect.left() + common.INDICATOR_WIDTH +
                     (rect.height() - 2))
        self.move(rect.left(), rect.top())
        self.resize(size.width() - rect.left(), rect.height())

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
            source_index = self.parent().model().mapToSource(self.parent().currentIndex())
            widget = DescriptionEditorWidget(
                source_index, parent=self.parent())
            widget.show()
            return True

        if (shift and tab) or backtab:
            self.action()
            self.parent().key_up()
            self.parent().key_tab()
            source_index = self.parent().model().mapToSource(self.parent().currentIndex())
            widget = DescriptionEditorWidget(
                source_index, parent=self.parent())
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
            font-family: "{}"; font-size: 8pt;\
            color: rgba({},{},{},{});'.format(
                common.SecondaryFont.family(),
                *common.TEXT_NOTE.getRgb()
            ))

        label = QtWidgets.QLabel(u'Edit description')
        label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        label.setStyleSheet(
            'font-family: "{}";\
            font-size: 8pt;\
            color: rgba({},{},{},{});'.format(
                common.PrimaryFont.family(),
                *common.TEXT.getRgb()
            ))

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
        if self.settings.value(u'config/description') == self.editor.text():
            self.close()
            return

        self._index.model().setData(
            self._index,
            self.editor.text(),
            role=common.DescriptionRole
        )
        self.settings.setValue(u'config/description', self.editor.text())
        self.close()


class FilterListButton(ClickableLabel):
    pass


class FilterEditor(QtWidgets.QWidget):
    """Editor widget used to set the filter for the current view."""
    finished = QtCore.Signal(unicode)

    def __init__(self, text, parent=None):
        super(FilterEditor, self).__init__(parent=parent)
        self.editor = None

        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
        self._createUI()
        self._connectSignals()
        self.setFocusProxy(self.editor)

        if text == u'/':
            text = u''
        self.editor.setText(text)
        self.editor.selectAll()
        self.editor.focusOutEvent = self.focusOutEvent

    def _createUI(self):
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(QtCore.Qt.Window |
                            QtCore.Qt.FramelessWindowHint)

        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        self.label = FilterListButton()
        self.label.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
        self.label.setFixedWidth(common.ROW_BUTTONS_HEIGHT)
        pixmap = ImageCache.get_rsc_pixmap(
            u'filter', common.FAVOURITE, common.ROW_BUTTONS_HEIGHT / 1.5)
        self.label.setPixmap(pixmap)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setFocusPolicy(QtCore.Qt.NoFocus)

        self.editor = QtWidgets.QLineEdit()
        self.editor.setAlignment(QtCore.Qt.AlignCenter)
        self.editor.setPlaceholderText('Filter...')
        self.editor.setStyleSheet("""
            QLineEdit {{
                margin: 4px;
                padding: 4px;
                background-color: rgba(38,38,38, 255);
                color: rgba(230,230,230,255);
                font-family: "{}";
                font-size: 10pt;
            	border-width: 0px;
            	border: none;
            	outline: 0;
                border-radius: 4px;
            }}
            QLineEdit:active {{
            	border: none;
            	outline: 0;
            }}
            QLineEdit:focus {{
            	border: none;
            	outline: 0;
            }}
        """.format(common.PrimaryFont.family()))
        self.layout().addWidget(self.label, 0)
        self.layout().addWidget(self.editor, 1)

        self.label.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.label.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

    def _connectSignals(self):
        self.finished.connect(self.close)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        rect = self.rect()
        # center = rect.center()
        # rect.setWidth(rect.width() - 4)
        # rect.setHeight(rect.height() - 4)
        # rect.moveCenter(center)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        painter.setPen(QtCore.Qt.NoPen)
        color = QtGui.QColor(common.SEPARATOR)
        color.setAlpha(150)
        painter.setBrush(common.SEPARATOR)
        painter.drawRect(rect)
        painter.end()

    def keyPressEvent(self, event):
        return_ = event.key() == QtCore.Qt.Key_Return
        enter = event.key() == QtCore.Qt.Key_Enter
        escape = event.key() == QtCore.Qt.Key_Escape

        if escape:
            self.close()
        if return_ or enter:
            self.finished.emit(self.editor.text())

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.close()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = FilterEditor('/')
    widget.show()
    app.exec_()
