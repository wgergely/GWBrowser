# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, W0613, R0201, E1120

"""Widgets used to edit data in the list widgets."""

import os
import functools
from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser.gwscandir as gwscandir
import gwbrowser.common as common
from gwbrowser.settings import AssetSettings
from gwbrowser.imagecache import ImageCache
from gwbrowser.alembicpreview import get_alembic_thumbnail
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.basecontextmenu import contextmenu


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
        self._secondarywidget = None

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

        if self._secondarywidget:
            self._secondarywidget.deleteLater()
            self._secondarywidget = None

        if path.split('.').pop() == u'abc':
            self.clear()

            file_info = QtCore.QFileInfo(path)
            if not file_info.exists():
                self.clear()
                self.setText(u'Alembic not found.')
                return

            path = str(file_info.filePath())

            alembicwidget = get_alembic_thumbnail(path)
            alembicwidget.setParent(self)
            alembicwidget.show()
            # alembicwidget.setFocusProxy(self)
            alembicwidget.setFocusPolicy(QtCore.Qt.NoFocus)

            alembicwidget.move(
                self.rect().center().x() - (alembicwidget.width() / 2),
                self.rect().center().y() - (alembicwidget.height() / 2)
            )

            self._secondarywidget = alembicwidget
            alembicwidget.show()

            return

        settings = AssetSettings(index)
        file_info = QtCore.QFileInfo(settings.thumbnail_path())

        if not index.isValid():
            self.clear()
            self.setText(u'Invalid selection.')
            return

        if not file_info.exists():
            self.clear()
            self.setText(u'No thumbnail found.')
            return

        pixmap = QtGui.QPixmap(settings.thumbnail_path())
        if pixmap.isNull():
            self.clear()
            self.setText(u'Unable to load pixmap.')
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
        self.layout().setContentsMargins(
            common.INDICATOR_WIDTH, common.INDICATOR_WIDTH / 2,
            common.INDICATOR_WIDTH / 2, common.INDICATOR_WIDTH)
        self.layout().setSpacing(3)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )

        self.editor = QtWidgets.QLineEdit()
        self.editor.setAlignment(QtCore.Qt.AlignCenter)
        self.editor.setTextMargins(0, 0, 0, 0)

        self.editor.setStyleSheet("""
background-color: rgb(50,50,50);
font-family: "{}"; font-size: {}pt;
color: rgba({});
            """.format(
            common.SecondaryFont.family(),
            common.psize(common.SMALL_FONT_SIZE),
            '{},{},{},{}'.format(*common.TEXT_SELECTED.getRgb()),
        ))

        label = QtWidgets.QLabel(u'Edit description')
        label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        label.setStyleSheet(
            'font-family: "{}";\
            font-size: {}pt;\
            color: rgba({},{},{},{});'.format(
                common.PrimaryFont.family(),
                common.psize(common.SMALL_FONT_SIZE),
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


class FilterIcon(QtWidgets.QLabel):
    """Widget responsible for displaying the keywords list"""

    def __init__(self, parent=None):
        super(FilterIcon, self).__init__(parent=parent)
        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT * 1.3)
        self.setFixedWidth(common.ROW_BUTTONS_HEIGHT)
        pixmap = ImageCache.get_rsc_pixmap(
            u'filter', common.FAVOURITE, common.INLINE_ICON_SIZE)
        self.setPixmap(pixmap)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)


class EditorContextMenu(BaseContextMenu):
    """The context menu associated with the filter text editor."""

    def __init__(self, parent=None):
        super(EditorContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_keywords_menu()

    @contextmenu
    def add_keywords_menu(self, menu_set):
        """Custom context menu to add a keyword to the search list."""
        pixmap = ImageCache.get_rsc_pixmap(
            u'filter', common.TEXT, common.INLINE_ICON_SIZE)
        kws = self.parent().parent().keywords()

        def insert_keyword(s):
            """The action to execute when a keyword is inserted."""
            s = s.split(u'/')
            s = u' '.join(s)

            self.parent().insert(s)
            self.parent().parent().finished.emit(self.parent().text())
            parent = self.parent().parent().parent().parent()
            parent.listcontrolwidget._filterbutton.action()

        for k in sorted(list(kws.iterkeys())):
            text = kws[k].split(u'/')
            text = u'  |  '.join(text) if len(text) > 1 else text[0]
            menu_set[k] = {
                u'text': text.upper(),
                u'icon': pixmap,
                u'action': functools.partial(insert_keyword, kws[k])
            }
        return menu_set


class Editor(QtWidgets.QLineEdit):
    """Customized QLineEditor to input out filter text."""

    def __init__(self, parent=None):
        super(Editor, self).__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setPlaceholderText(u'Filter...')
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
            '{},{},{},{}'.format(*common.TEXT_SELECTED.getRgb()),
            common.PrimaryFont.family(),
            common.psize(common.LARGE_FONT_SIZE)
        ))

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

    def contextMenuEvent(self, event):
        """Custom context menu for the editor widget."""
        if not self.parent().keywords():
            return

        widget = EditorContextMenu(parent=self)
        pos = self.rect().bottomLeft()
        pos = self.mapToGlobal(pos)
        widget.move(pos)
        self.parent().context_menu_open = True
        widget.exec_()
        self.parent().context_menu_open = False


class FilterEditor(QtWidgets.QWidget):
    """Editor widget used to set the filter for the current model."""
    finished = QtCore.Signal(unicode)

    def __init__(self, text, parent=None):
        super(FilterEditor, self).__init__(parent=parent)
        self.editor_widget = None
        self.context_menu_open = False

        self.row1_height = common.ROW_BUTTONS_HEIGHT * 1.5
        self.row2_height = self.parent().geometry().height() - self.row1_height

        self._createUI()
        self._connectSignals()
        self.setFocusProxy(self.editor_widget)

        self.editor_widget.setText(u'' if text == u'/' else text)
        self.editor_widget.selectAll()
        self.editor_widget.focusOutEvent = self.focusOutEvent

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(QtCore.Qt.Window |
                            QtCore.Qt.FramelessWindowHint)

    def keywords(self):
        """Shortcut to the keyword values we stored."""
        if not self.parent():
            return {}
        return self.parent().parent().stackedwidget.currentWidget().model().sourceModel().keywords()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        label = FilterIcon(parent=self)
        self.editor_widget = Editor(parent=self)

        # Settings the completer associated with the Editor widget
        completer = QtWidgets.QCompleter(
            sorted(self.keywords().keys()), self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        completer.setCompletionMode(
            QtWidgets.QCompleter.InlineCompletion)
        self.editor_widget.setCompleter(completer)

        self.layout().addWidget(label, 0)
        self.layout().addWidget(self.editor_widget, 1)

    def _connectSignals(self):
        self.finished.connect(self.close)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        rect = self.rect()
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
            self.finished.emit(self.editor_widget.text())

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            if self.context_menu_open:
                return
            self.close()


class ThumbnailLabel(ClickableLabel):
    """Custom QLabel to select a thumbnail."""
    clicked = QtCore.Signal(unicode)

    def __init__(self, path, size, parent=None):
        super(ThumbnailLabel, self).__init__(parent=parent)
        self._path = path

        self.setFixedWidth(size)
        self.setFixedHeight(size)
        self.setMouseTracking(True)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum)

    def enterEvent(self, event):
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def mouseReleaseEvent(self, event):
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
        self.columns = 3

        self._createUI()

        self.setFixedHeight(
            (self.thumbnail_size + common.INDICATOR_WIDTH) * 6 + (common.INDICATOR_WIDTH * 2))
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
                entry.path.replace(u'\\', u'/'), self.thumbnail_size, parent=self)
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


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = ThumbnailsWidget()
    widget.show()
    app.exec_()
