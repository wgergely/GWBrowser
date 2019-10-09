# -*- coding: utf-8 -*-
"""Widgets used to edit data in the list widgets."""

import os
import functools
from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser.gwscandir as gwscandir
import gwbrowser.common as common
from gwbrowser.common_ui import add_row, PaintedLabel, ClickableIconButton
from gwbrowser.settings import AssetSettings
from gwbrowser.imagecache import ImageCache
from gwbrowser.alembicpreview import get_alembic_thumbnail
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.basecontextmenu import contextmenu


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

    def __init__(self, parent=None):
        super(DescriptionEditorWidget, self).__init__(parent=parent)
        self.editor = None

        self._createUI()
        self._connectSignals()

        self.editor.focusOutEvent = self.focusOutEvent
        self.editor.installEventFilter(self)

        self.setFocusPolicy(QtCore.Qt.NoFocus)

        self.editor.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.editor.setFocus(QtCore.Qt.PopupFocusReason)

    def index(self):
        return self.parent().selectionModel().currentIndex()

    def showEvent(self, event):
        if not self.index().isValid():
            self.hide()
        if not self.index().data(common.FileInfoLoaded):
            self.hide()

        self.update_editor(self.parent().viewport().size())
        self.editor.setFocus(QtCore.Qt.PopupFocusReason)

    def update_editor(self, size):
        """Sets the widget size, position and contents."""
        if not self.index().isValid():
            self.hide()

        rect = QtCore.QRect(self.parent().visualRect(self.index()))
        rect.setLeft(rect.left() + common.INDICATOR_WIDTH +
                     (rect.height() - 2))
        self.move(rect.left(), rect.top())
        self.resize(size.width() - rect.left(), rect.height())

        self.editor.setText(self.index().data(common.DescriptionRole))
        self.editor.selectAll()

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

    def _connectSignals(self):
        """Connects signals."""
        self.editor.editingFinished.connect(self.action)
        self.parent().sizeChanged.connect(self.update_editor)

    def _createUI(self):
        """Creates the layout."""
        QtWidgets.QHBoxLayout(self)
        self.setWindowFlags(QtCore.Qt.Widget)
        o = common.INDICATOR_WIDTH
        self.layout().setContentsMargins(o,o,o,o)
        self.layout().setSpacing(o)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        self.editor = QtWidgets.QLineEdit(parent=self)
        self.editor.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.editor.setTextMargins(0, 0, 0, 0)
        self.editor.setStyleSheet("""
background-color: rgb(50,50,50);
font-family: "{}"; font-size: {}pt;
color: rgba({});
            """.format(
            common.SecondaryFont.family(),
            common.psize(common.SMALL_FONT_SIZE),
            common.rgb(common.TEXT_SELECTED),
        ))

        label = QtWidgets.QLabel(u'Edit description')
        label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        label.setStyleSheet(
            'font-family: "{}";\
            font-size: {}pt;\
            color: rgba({});'.format(
                common.PrimaryFont.family(),
                common.psize(common.SMALL_FONT_SIZE),
                common.rgb(common.TEXT)
            ))

        self.layout().addWidget(label)
        self.layout().addWidget(self.editor, 1)

    def paintEvent(self, event):
        """Custom paint used to paint the background."""
        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            rect = QtCore.QRect()
            rect.setWidth(self.width())
            rect.setHeight(self.height())

            pen = QtGui.QPen(common.FAVOURITE)
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
        if self.index().data(common.DescriptionRole) == self.editor.text():
            self.hide()
            return

        if not self.index().data(common.ParentRole):
            self.hide()
            return

        settings = AssetSettings(self.index())
        settings.setValue(u'config/description', self.editor.text())

        source_index = self.index().model().mapToSource(self.index())
        data = source_index.model().model_data()[source_index.row()]
        data[common.DescriptionRole] = self.editor.text()
        source_index.model().dataChanged.emit(self.index(), self.index())
        self.hide()


class EditorContextMenu(BaseContextMenu):
    """The context menu associated with the filter text editor."""
    finished = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(EditorContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_keywords_menu()

    @contextmenu
    def add_keywords_menu(self, menu_set):
        """Custom context menu to add a keyword to the search list."""
        pixmap = ImageCache.get_rsc_pixmap(
            u'filter', common.TEXT, common.INLINE_ICON_SIZE)
        kws = self.parent().parent().parent().keywords()
        if not kws:
            return menu_set

        def insert_keyword(s):
            """The action to execute when a keyword is inserted."""
            s = s.split(u'/')
            s = u' '.join(s)

            self.parent().insert(s)
            self.finished.emit(self.parent().text())

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
    finished = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(Editor, self).__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setPlaceholderText(u'Filter text...')
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

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

    def contextMenuEvent(self, event):
        """Custom context menu for the editor widget."""
        if not self.parent().parent().keywords():
            return

        widget = EditorContextMenu(parent=self)
        widget.finished.connect(self.finished)
        pos = self.rect().bottomLeft()
        pos = self.mapToGlobal(pos)
        widget.move(pos)
        self.parent().context_menu_open = True
        widget.exec_()
        self.parent().context_menu_open = False


class FilterEditor(QtWidgets.QWidget):
    """Editor widget used to set a text filter on the associated model."""
    finished = QtCore.Signal(unicode)

    def __init__(self, text, parent=None):
        super(FilterEditor, self).__init__(parent=parent)
        self.editor_widget = None
        self.subfolders_widget = None
        self.context_menu_open = False
        self.kw_row = None

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum
        )
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(QtCore.Qt.Window |
                            QtCore.Qt.FramelessWindowHint)
        self._createUI()
        self._connectSignals()

        self.setFocusProxy(self.editor_widget)
        self.editor_widget.setText(u'' if text == u'/' else text)
        self.editor_widget.selectAll()
        self.editor_widget.setFocus()

        # Settings the completer associated with the Editor widget
        if not self.keywords():
            return

        keys = self.keywords().keys()
        if not keys:
            self.kw_row.hide()
            return

        completer = QtWidgets.QCompleter(sorted(keys), self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        completer.setCompletionMode(
            QtWidgets.QCompleter.InlineCompletion)
        self.editor_widget.setCompleter(completer)

        self.add_keywords(keys)

    def _createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN * 2
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(12)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        self.layout().addStretch(1)

        row = add_row(u'', parent=self, padding=0, height=common.ROW_HEIGHT)
        icon = ClickableIconButton(
            u'filter',
            (common.REMOVE, common.REMOVE),
            common.ROW_HEIGHT
        )
        row.layout().addWidget(icon)
        label = u'Edit the filter to help find items in the current list:'
        row.layout().addWidget(PaintedLabel(label, parent=self))



        self.f_row = add_row(u'', parent=self, padding=0, height=common.ROW_HEIGHT)
        self.editor_widget = Editor(parent=self)
        self.editor_widget.setAlignment(QtCore.Qt.AlignLeft)
        self.f_row.layout().addWidget(self.editor_widget, 1)

        self.kw_row = add_row(u'Keywords', padding=0, parent=self, height=common.ASSET_ROW_HEIGHT)
        self.subfolders_widget = QtWidgets.QListWidget(parent=self)
        self.kw_row.layout().addStretch(1)
        self.kw_row.layout().addSpacing(o)
        self.kw_row.layout().addWidget(self.subfolders_widget)
        self.layout().addStretch(1)

    def _connectSignals(self):
        if self.parent():
            self.parent().parent().resized.connect(self.adjust_size)
        self.subfolders_widget.itemActivated.connect(lambda i: self.finished.emit(i.text()))
        self.subfolders_widget.itemClicked.connect(lambda i: self.finished.emit(i.text()))
        self.editor_widget.finished.connect(self.finished)
        self.finished.connect(self.close)

    def add_keywords(self, keys):
        scrollToItem = None
        for key in sorted([f.replace(u'%%', u'') for f in keys if u'%%' in f]):
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, key.upper())
            item.setData(common.DescriptionRole, key.upper())
            item.setData(QtCore.Qt.StatusTipRole, key.upper())
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                200, common.INLINE_ICON_SIZE))

            if self.editor_widget.text().lower() != key.lower():
                scrollToItem = item
                item.setForeground(QtGui.QBrush(common.SECONDARY_TEXT))
            else:
                item.setForeground(QtGui.QBrush(common.TEXT))

            self.subfolders_widget.addItem(item)

        if scrollToItem:
            self.subfolders_widget.scrollToItem(item, hint=QtWidgets.QAbstractItemView.PositionAtCenter)

    def keywords(self):
        """Shortcut to access the models filter keyword values."""
        if not self.parent():
            return {}

        val = self.parent().currentWidget().model().sourceModel().keywords()
        return val

    @QtCore.Slot()
    def adjust_size(self):
        if not self.parent():
            return

        rect = self.parent().rect()
        pos = rect.topLeft()
        pos = self.parent().mapToGlobal(pos)
        self.move(pos)
        self.setFocus()
        self.resize(rect.width(), self.height())

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        painter.setPen(QtCore.Qt.NoPen)

        rect = self.rect()
        center = rect.center()
        rect.setWidth(rect.width() - common.MARGIN)
        rect.setHeight(rect.height() - common.MARGIN)
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
        if self.parent():
            self.parent().currentWidget().disabled_overlay_widget.show()
        if not self.keywords():
            self.kw_row.hide()

    def hideEvent(self, event):
        if self.parent():
            self.parent().currentWidget().disabled_overlay_widget.hide()

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
