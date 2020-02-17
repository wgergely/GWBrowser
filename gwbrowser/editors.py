# -*- coding: utf-8 -*-
"""Widgets used to edit data in the list widgets."""

import os
import functools
from PySide2 import QtWidgets, QtGui, QtCore
import OpenImageIO
import gwbrowser.gwscandir as gwscandir
import gwbrowser.common as common
from gwbrowser.common_ui import add_row, PaintedLabel, ClickableIconButton
from gwbrowser.settings import AssetSettings
from gwbrowser.imagecache import ImageCache
from gwbrowser.alembicpreview import get_alembic_thumbnail
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.basecontextmenu import contextmenu
import gwbrowser.delegate as delegate


class ThumbnailViewer(QtWidgets.QLabel):
    """Widget used to view a thumbnail."""

    def __init__(self, parent=None):
        super(ThumbnailViewer, self).__init__(parent=parent)
        self.alembic_preview_widget = None

        self.setWindowFlags(
            QtCore.Qt.Dialog |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setAlignment(QtCore.Qt.AlignCenter)

        self.show()
        self.reset_pixmap()

    def reset_pixmap(self):
        self.setStyleSheet(
            u'QLabel {background-color: rgba(50,50,50,50); color:rgba(200,200,200,255);}')
        index = self.parent().selectionModel().currentIndex()
        path = index.data(QtCore.Qt.StatusTipRole)
        path = common.get_sequence_endpath(path)

        if self.alembic_preview_widget:
            self.alembic_preview_widget.deleteLater()
            self.alembic_preview_widget = None

        # We're showing the contents of the alembic file
        if path.lower().endswith('.abc'):
            self.clear()

            file_info = QtCore.QFileInfo(path)
            if not file_info.exists():
                self.clear()
                self.setText(u'Alembic not found.')
                return

            alembicwidget = get_alembic_thumbnail(path)
            alembicwidget.setParent(self)
            alembicwidget.show()
            alembicwidget.setFocusPolicy(QtCore.Qt.NoFocus)
            alembicwidget.move(
                self.rect().center().x() - (alembicwidget.width() / 2),
                self.rect().center().y() - (alembicwidget.height() / 2)
            )

            self.alembic_preview_widget = alembicwidget
            alembicwidget.show()
            return

        settings = AssetSettings(index)
        file_info = QtCore.QFileInfo(settings.thumbnail_path())

        if not index.isValid():
            self.clear()
            self.setText(u'Invalid selection.')
            return

        # The item does not have a discreet thumbnail
        if not file_info.exists():
            self.clear()
            if index.data(common.ThumbnailRole):
                self.setPixmap(index.data(common.ThumbnailRole))
            return

        pixmap = QtGui.QPixmap(settings.thumbnail_path())
        if pixmap.isNull():
            self.clear()
            self.setText(u'Unable to load pixmap.')
            return

        self.clear()
        if pixmap.width() > common.THUMBNAIL_IMAGE_SIZE or pixmap.height() > common.THUMBNAIL_IMAGE_SIZE:
            pixmap = ImageCache.resize_image(
                pixmap.toImage(), common.THUMBNAIL_IMAGE_SIZE)
        self.setPixmap(pixmap)

    def paintEvent(self, event):
        """Custom paint event"""
        index = self.parent().selectionModel().currentIndex()
        if not index.isValid():
            return

        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        painter.setBrush(QtGui.QColor(15, 15, 15, 230))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(self.rect())

        # Let's paint extra information:
        rect = self.rect()

        font = QtGui.QFont(common.PrimaryFont)
        metrics = QtGui.QFontMetricsF(font)

        if self.pixmap():
            bg_rect = self.pixmap().rect()
            size = max((bg_rect.width(), bg_rect.height()))
            bg_rect.setWidth(size)
            bg_rect.setHeight(size)
            bg_rect.moveCenter(self.rect().center())
            painter.setBrush(QtGui.QColor(0, 0, 0, 60))
            painter.drawRect(bg_rect)

            center = rect.center()
            rect.setHeight(metrics.lineSpacing())
            rect.setWidth(rect.width() - (common.MARGIN * 4))
            rect.moveCenter(center)

            # Aligned to the bottom of the pixmap
            rect.moveTop(
                rect.top() + bg_rect.height() / 2.0 + common.MARGIN)

            # Filename

            text = index.data(QtCore.Qt.StatusTipRole)
            if text:
                text = u' / '.join(text.split(u'/'))
                common.draw_aliased_text(painter, font, QtCore.QRect(
                    rect), text, QtCore.Qt.AlignCenter, common.TEXT)
                rect.moveTop(rect.center().y() + metrics.lineSpacing())

            text = index.data(common.DescriptionRole)
            if text:
                text = text if text else u''
                common.draw_aliased_text(painter, font, QtCore.QRect(
                    rect), text, QtCore.Qt.AlignCenter, common.FAVOURITE)
                rect.moveTop(rect.center().y() + metrics.lineSpacing())
            text = index.data(common.FileDetailsRole)
            if text:
                text = u'{}'.format(text)
                text = u'   |   '.join(text.split(u';')) if text else u'-'
                common.draw_aliased_text(painter, font, QtCore.QRect(
                    rect), text, QtCore.Qt.AlignCenter, common.TEXT)
                rect.moveTop(rect.center().y() + metrics.lineSpacing())

        # Image info
        ext = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole)).suffix()
        if ext.lower() in common.get_oiio_extensions():
            metrics = QtGui.QFontMetricsF(common.SecondaryFont)

            path = index.data(QtCore.Qt.StatusTipRole)
            path = common.get_sequence_endpath(path)
            img = OpenImageIO.ImageBuf(path)
            image_info = img.spec().serialize().split('\n')
            image_info = [f.strip() for f in image_info if f]
            for n, text in enumerate(image_info):
                if n > 2:
                    break
                common.draw_aliased_text(painter, common.SecondaryFont, QtCore.QRect(
                    rect), text, QtCore.Qt.AlignCenter, common.SECONDARY_TEXT)
                rect.moveTop(rect.center().y() + int(metrics.lineSpacing()))

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
        app = QtWidgets.QApplication.instance()
        rect = app.desktop().availableGeometry(self.parent())
        self.setGeometry(rect)

    def showEvent(self, event):
        self.setFocus()
        self.parent().thumbnail_viewer_widget = self
        self.parent().setUpdatesEnabled(False)
        self._fit_screen_geometry()

    def hideEvent(self, event):
        self.parent().setUpdatesEnabled(True)
        self.parent().thumbnail_viewer_widget = None

    def mousePressEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.close()

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.close()


class DescriptionEditorWidget(QtWidgets.QLineEdit):
    """The editor used to edit the desciption of items."""

    def __init__(self, parent=None):
        super(DescriptionEditorWidget, self).__init__(parent=parent)
        self._connectSignals()

        self.installEventFilter(self)
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        self.setPlaceholderText(u'Edit description...')
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setTextMargins(2, 2, 2, 2)
        self.setStyleSheet(
            """
QLineEdit {{
	font-family: "{FONT}";
	font-size: {SIZE}pt;
    margin: 0px;
    padding: 0px;
}}
        """.format(
                FONT=common.SecondaryFont.family(),
                SIZE=common.SMALL_FONT_SIZE + 1.0
            )
        )

    def _connectSignals(self):
        """Connects signals."""
        self.editingFinished.connect(self.action)
        self.parent().verticalScrollBar().valueChanged.connect(self.hide)
        self.parent().parent().resized.connect(self.update_editor)

    def action(self):
        """Main actions to run when the return key is pressed."""
        index = self.parent().selectionModel().currentIndex()
        text = u'{}'.format(index.data(common.DescriptionRole))
        if text.lower() == self.text().lower():
            self.hide()
            return

        if not index.data(common.ParentPathRole):
            self.hide()
            return

        settings = AssetSettings(index)
        settings.setValue(u'config/description', self.text())

        source_index = index.model().mapToSource(index)
        data = source_index.model().model_data()[source_index.row()]
        data[common.DescriptionRole] = self.text()
        self.parent().update_index(source_index)
        self.hide()

    def update_editor(self):
        """Sets the editor widget's size, position and text contents."""
        index = self.parent().selectionModel().currentIndex()
        if not index.isValid():
            self.hide()
            return

        rect = self.parent().visualRect(index)
        rectangles = self.parent().itemDelegate().get_rectangles(rect)
        description_rect = self.parent().itemDelegate().get_description_rect(rectangles, index)

        # Won't be showing the editor if there's no appropiate description area
        # provided by the delegate (eg. the bookmark items don't have this)
        if not description_rect:
            self.hide()

        # Let's set the size based on the size provided by the delegate but
        # center it instead of a direct overlay
        rect = description_rect.marginsAdded(QtCore.QMargins(0, 4, 0, 4))
        rect.moveCenter(rectangles[delegate.DataRect].center())
        rect.setLeft(
            rectangles[delegate.DataRect].left() + common.INDICATOR_WIDTH)
        rect.setRight(
            rectangles[delegate.DataRect].right() - common.INDICATOR_WIDTH)
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


class Editor(QtWidgets.QLineEdit):
    """Customized QLineEditor to input out filter text."""
    finished = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(Editor, self).__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        self.setStyleSheet("""
QLineEdit {{
    margin: 6px;
    padding: 6px;
    background-color: rgba(38,38,38, 255);
    color: rgba({});
    font-family: "{}";
    font-size: {}pt;
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
        """.format(
            common.rgb(common.TEXT_SELECTED),
            common.PrimaryFont.family(),
            common.psize(common.LARGE_FONT_SIZE)
        ))
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)


class FilterEditor(QtWidgets.QWidget):
    """Editor widget used to set a text filter on the associated model."""
    finished = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(FilterEditor, self).__init__(parent=parent)
        self.editor_widget = None
        self.context_menu_open = False

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum
        )
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self._createUI()
        self._connectSignals()

        self.setFocusProxy(self.editor_widget)

    def _createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN * 2
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        row = add_row(u'', parent=self, padding=0, height=common.ROW_HEIGHT)
        icon = ClickableIconButton(
            u'filter',
            (common.REMOVE, common.REMOVE),
            common.ROW_HEIGHT
        )
        row.layout().addWidget(icon)
        label = u'Edit the filter to help find items in the current list'
        row.layout().addWidget(PaintedLabel(label, parent=self))

        row = add_row(u'', parent=self, padding=0, height=common.ROW_HEIGHT)
        label = u'text'
        label = QtWidgets.QLabel(label)
        label.setStyleSheet(u'color: rgba({});'.format(
            common.rgb(common.SECONDARY_TEXT)))
        label.setWordWrap(True)
        row.layout().addWidget(label, 1)

        row = add_row(u'', parent=self, padding=0, height=common.ROW_HEIGHT)
        row.setFixedHeight(64)
        self.editor_widget = Editor(parent=self)
        row.layout().addWidget(self.editor_widget, 1)
        self.layout().addStretch(1)

    def _connectSignals(self):
        self.editor_widget.finished.connect(self.finished)
        self.finished.connect(self.hide)

    @QtCore.Slot()
    def adjust_size(self):
        if not self.parent():
            return

        self.resize(
            self.parent().geometry().width(),
            self.parent().geometry().height(),
        )

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        painter.setPen(QtCore.Qt.NoPen)

        rect = self.rect()
        center = rect.center()
        rect.setWidth(rect.width() - (common.MARGIN * 2))
        rect.setHeight(rect.height() - (common.MARGIN * 2))
        rect.moveCenter(center)
        painter.setBrush(common.SEPARATOR)
        painter.drawRoundedRect(rect, 6, 6)
        painter.end()

    def keyPressEvent(self, event):
        return_ = event.key() == QtCore.Qt.Key_Return
        enter = event.key() == QtCore.Qt.Key_Enter
        escape = event.key() == QtCore.Qt.Key_Escape

        if escape:
            self.close()
        if return_ or enter:
            self.finished.emit(self.editor_widget.text())

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
        self.adjust_size()
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
                common.PrimaryFont,
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


class ThumbnailsWidget(QtWidgets.QScrollArea):
    """The widget used to let the end-user pick a new thumbnail."""
    thumbnailSelected = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(ThumbnailsWidget, self).__init__(parent=parent)
        self.thumbnail_size = 128

        self.columns = 5
        rows = 4

        self._createUI()

        self.setFixedHeight(
            (self.thumbnail_size + common.INDICATOR_WIDTH) * rows + (common.INDICATOR_WIDTH * 2))
        self.setFixedWidth(
            (self.thumbnail_size + common.INDICATOR_WIDTH) * self.columns + (common.INDICATOR_WIDTH * 2))
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

    def _createUI(self):
        """Using scandir we will get all the installed thumbnail files from the rsc directory."""
        common.set_custom_stylesheet(self)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle(u'Select thumbnail')
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)

        widget = QtWidgets.QWidget()
        QtWidgets.QGridLayout(widget)
        widget.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        widget.layout().setContentsMargins(
            common.INDICATOR_WIDTH,
            common.INDICATOR_WIDTH,
            common.INDICATOR_WIDTH,
            common.INDICATOR_WIDTH)
        widget.layout().setSpacing(common.INDICATOR_WIDTH)

        self.setWidgetResizable(True)
        self.setWidget(widget)

        row = 0
        path = u'{}/../rsc'.format(__file__)
        path = os.path.normpath(os.path.abspath(path))

        idx = 0
        for entry in gwscandir.scandir(path):
            if not entry.name.startswith('thumb_'):
                continue

            pixmap = ImageCache.get_rsc_pixmap(
                entry.name.replace(u'.png', u''), None, self.thumbnail_size)
            if pixmap.isNull():
                continue
            label = ThumbnailLabel(
                entry.path, self.thumbnail_size, parent=self)
            label.setPixmap(pixmap)

            column = idx % self.columns
            if column == 0:
                row += 1
            widget.layout().addWidget(label, row, column)
            label.clicked.connect(self.thumbnailSelected)
            label.clicked.connect(self.close)

            idx += 1

    def _connectSignals(self):
        pass

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.hide()

    def keyPressEvent(self, event):
        """Closes the widget on any key-press."""
        self.close()

    def showEvent(self, event):
        if self.parent():
            center = self.parent().mapToGlobal(self.parent().geometry().center())
            self.move(QtCore.QPoint(
                center.x() - (self.rect().width() / 2),
                center.y() - (self.rect().height() / 2),
            ))
            common.move_widget_to_available_geo(self)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = FilterEditor('')
    widget.show()
    app.exec_()
