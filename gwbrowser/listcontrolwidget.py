# -*- coding: utf-8 -*-
"""Widget reponsible controlling the displayed list and the filter-modes."""

import os
from PySide2 import QtWidgets, QtGui, QtCore

from gwbrowser.datakeywidget import DataKeyView
import gwbrowser.common as common
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.common_ui import ClickableIconButton
from gwbrowser.editors import FilterEditor
import gwbrowser.settings as Settings

from gwbrowser.imagecache import ImageCache
from gwbrowser.imagecache import ImageCacheWorker
from gwbrowser.fileswidget import FilesWidget

from gwbrowser.assetswidget import AssetModel
from gwbrowser.bookmarkswidget import BookmarksModel

from gwbrowser.settings import local_settings


class BaseControlButton(ClickableIconButton):
    """Base class with a few default values."""

    def __init__(self, pixmap, description, parent=None):
        super(BaseControlButton, self).__init__(
            pixmap,
            (common.TEXT_SELECTED, common.SECONDARY_BACKGROUND),
            common.INLINE_ICON_SIZE,
            description=description,
            parent=parent
        )
        self._parent = parent

    def set_parent(self, widget):
        self._parent = widget

    def current(self):
        if not self._parent:
            return None
        return self._parent.currentWidget()


class TodoButton(BaseControlButton):
    """The button for showing the todo editor."""

    def __init__(self, parent=None):
        super(TodoButton, self).__init__(
            u'todo',
            u'Show the Todo & Note editor',
            parent=parent
        )

    def state(self):
        index = self._parent.widget(1).model().sourceModel().active_index()
        if not index.isValid():
            return False
        if index.data(common.TodoCountRole):
            return True
        return False

    def action(self):
        idx = self._parent.currentIndex()
        # if idx not in (0, 1, 2):
        #     return
        index = self._parent.currentWidget().selectionModel().currentIndex()
        if not index.isValid():
            return
        self._parent.currentWidget().show_todos(index)

    def repaint(self):
        super(TodoButton, self).repaint()
        if self._parent.currentIndex() in (2,):
            self.show()
        else:
            self.hide()


class FilterButton(BaseControlButton):
    """Button for showing the filter editor."""

    def __init__(self, parent=None):
        super(FilterButton, self).__init__(
            u'filter',
            u'Edit search filter',
            parent=parent
        )

    def state(self):
        filter_text = self.current().model().filterText()
        if not filter_text:
            return False
        if filter_text == u'/':
            return False
        return True

    def action(self):
        """The action to perform when finished editing the filter text."""
        filter_text = self.current().model().filterText()
        filter_text = common.clean_filter_text(filter_text)
        #
        parent = self._parent.parent().stackedwidget
        editor = FilterEditor(filter_text, parent=parent)

        model = self.current().model()
        editor.finished.connect(lambda x: model.filterTextChanged.emit(
            common.regexify_filter_text(x)))
        editor.finished.connect(self.repaint)
        editor.finished.connect(editor.deleteLater)
        #
        editor.show()


class CollapseSequenceButton(BaseControlButton):
    """The buttons responsible for collapsing/expanding the sequences of the
    current list.

    """
    def __init__(self, parent=None):
        super(CollapseSequenceButton, self).__init__(
            u'collapse',
            u'Group sequences together',
            parent=parent
        )

    def pixmap(self):
        if self.state():
            return ImageCache.get_rsc_pixmap(u'collapse', self._on_color, common.INLINE_ICON_SIZE)
        return ImageCache.get_rsc_pixmap(u'expand', self._off_color, common.INLINE_ICON_SIZE)

    def state(self):
        datatype = self.current().model().sourceModel().data_type()
        if datatype == common.FileItem:
            return False
        return True

    @QtCore.Slot()
    def action(self):
        """Only lists containing sequences can be collapsed."""
        if self._parent.currentIndex() not in (2, 3):
            return

        datatype = self.current().model().sourceModel().data_type()
        if datatype == common.FileItem:
            self.current().model().sourceModel().dataTypeChanged.emit(common.SequenceItem)
        else:
            self.current().model().sourceModel().dataTypeChanged.emit(common.FileItem)

    def repaint(self):
        super(CollapseSequenceButton, self).repaint()
        if self._parent.currentIndex() in (2, 3):
            self.show()
        else:
            self.hide()


class ToggleArchivedButton(BaseControlButton):
    """Custom QLabel with a `clicked` signal."""
    def __init__(self, parent=None):
        super(ToggleArchivedButton, self).__init__(
            u'collapse',
            u'Show archived items',
            parent=parent
        )

    def pixmap(self):
        if self.state():
            return ImageCache.get_rsc_pixmap(u'active', self._on_color, common.INLINE_ICON_SIZE)
        return ImageCache.get_rsc_pixmap(u'archived', self._off_color, common.INLINE_ICON_SIZE)

    def state(self):
        val = self.current().model().filterFlag(common.MarkedAsArchived)
        return val

    @QtCore.Slot()
    def action(self):
        val = self.current().model().filterFlag(common.MarkedAsArchived)
        self.current().model().filterFlagChanged.emit(
            common.MarkedAsArchived, not val)

    def repaint(self):
        super(ToggleArchivedButton, self).repaint()
        if self._parent.currentIndex() < 3:
            self.show()
        else:
            self.hide()


class ToggleButtons(BaseControlButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(ToggleButtons, self).__init__(
            u'showbuttons',
            u'Show or hide list buttons',
            parent=parent
        )

    def state(self):
        val = self.current().buttons_hidden()
        return val

    @QtCore.Slot()
    def action(self):
        val = self.current().buttons_hidden()
        self.current().set_buttons_hidden(not val)
        self.current().repaint()

    def repaint(self):
        super(ToggleButtons, self).repaint()
        if self._parent.currentIndex() == 2:
            self.show()
        else:
            self.hide()


class ToggleFavouriteButton(BaseControlButton):
    """Toggle the visibility of items marked as favourites."""

    def __init__(self, parent=None):
        super(ToggleFavouriteButton, self).__init__(
            u'favourite',
            u'Show starred only',
            parent=parent
        )

    def state(self):
        val = self.current().model().filterFlag(common.MarkedAsFavourite)
        return val

    @QtCore.Slot()
    def action(self):
        val = self.current().model().filterFlag(common.MarkedAsFavourite)
        self.current().model().filterFlagChanged.emit(
            common.MarkedAsFavourite, not val)

    def repaint(self):
        super(ToggleFavouriteButton, self).repaint()
        if self._parent.currentIndex() < 3:
            self.show()
        else:
            self.hide()


class SlackButton(BaseControlButton):
    """The button used to open slack."""

    def __init__(self, parent=None):
        super(SlackButton, self).__init__(
            u'slack',
            u'Open Slack',
            parent=parent
        )

    @QtCore.Slot()
    def action(self):
        """Opens the set slack workspace."""
        QtGui.QDesktopServices.openUrl(common.SLACK_URL)

    def state(self):
        return True


class AddButton(BaseControlButton):
    """The buttons responsible for adding new items.

    The functionality differs based on the currently selected tab:
    For bookmarks the user will be prompted with the ``AddBookmarksWidget``,
    for assets, a new asset will be created, and for files a new template file
    can be added.

    """

    def __init__(self, parent=None):
        super(AddButton, self).__init__(
            u'add',
            u'Click to add a new bookmark, asset, or file...',
            parent=parent
        )

    def state(self):
        if self._parent.currentIndex() == 0:
            return True
        if self._parent.currentIndex() == 1:
            if self._parent.widget(0).model().sourceModel().active_index().isValid():
                return True
            return False
        if self._parent.currentIndex() == 2:
            if self._parent.widget(1).model().sourceModel().active_index().isValid():
                return True
            return False
        return False

    def add_asset(self):
        from gwbrowser.addassetwidget import AddAssetWidget

        view = self._parent.widget(0)
        model = view.model().sourceModel()
        bookmark = model.active_index()
        if not bookmark.isValid():
            return

        bookmark = bookmark.data(common.ParentRole)
        bookmark = u'/'.join(bookmark)
        widget = AddAssetWidget(
            bookmark, parent=self._parent)
        pos = self.window().rect().center()
        pos = self.window().mapToGlobal(pos)
        widget.move(
            pos.x() - (widget.width() / 2),
            pos.y() - (widget.height() / 2),
        )

        cwidget = self.parent().parent().stackedwidget.currentWidget()
        cwidget.disabled_overlay_widget.show()
        widget.exec_()

        if not widget.last_asset_added:
            cwidget.disabled_overlay_widget.hide()
            return

        model.modelDataResetRequested.emit()
        view = self._parent.widget(1)
        for n in xrange(view.model().rowCount()):
            index = view.model().index(n, 0)
            if index.data(QtCore.Qt.DisplayRole).lower() == widget.last_asset_added.lower():
                view.selectionModel().setCurrentIndex(
                    index, QtCore.QItemSelectionModel.ClearAndSelect)
                view.scrollTo(index)
                break

        cwidget.disabled_overlay_widget.hide()
        return

    def create_file(self):
        """Adds an empty reference file."""
        from gwbrowser.addfilewidget import AddFileWidget
        widget = AddFileWidget(u'temp')

        if widget.exec_() == QtWidgets.QDialog.Accepted:
            file_path = widget.filePath()
            with open(file_path, 'w') as f:
                f.write(u'A temporary reference file created by GWBrowser...')
                common.reveal(file_path)



    @QtCore.Slot()
    def action(self):
        """``AddButton`` action."""
        # Bookmark
        if self._parent.currentIndex() == 0:
            self.current().show_add_bookmark_widget()
            return
        # Asset
        if self._parent.currentIndex() == 1:
            self.add_asset()
            return
        # This will open the Saver to save a new file
        if self._parent.currentIndex() == 2:
            self.create_file()

    def repaint(self):
        """The button is only visible when showing bookmarks or files."""
        super(AddButton, self).repaint()
        if self._parent.currentIndex() in (0, 1, 2):
            self.show()
        else:
            self.hide()


class GenerateThumbnailsButton(BaseControlButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(GenerateThumbnailsButton, self).__init__(
            u'spinner_btn',
            u'Toggle thumbnail generation. If experiencing performance issues, turn this off!',
            parent=parent
        )

    def state(self):
        """The state of the auto-thumbnails"""
        if self._parent.currentIndex() < 2:
            return False
        model = self._parent.currentWidget().model().sourceModel()
        return model.generate_thumbnails

    @QtCore.Slot()
    def action(self):
        """Toggles thumbnail generation."""
        model = self._parent.currentWidget().model().sourceModel()
        val = model.generate_thumbnails

        cls = model.__class__.__name__
        local_settings.setValue(
            u'widget/{}/generate_thumbnails'.format(cls), not val)
        if not val == False:
            ImageCacheWorker.reset_queue()
        model.generate_thumbnails = not val
        self.repaint()

    def repaint(self):
        """Will only show for favourite and file items."""
        super(GenerateThumbnailsButton, self).repaint()
        if self._parent.currentIndex() >= 2:
            self.show()
        else:
            self.hide()


class CollapseSequenceMenu(BaseContextMenu):
    def __init__(self, parent=None):
        super(CollapseSequenceMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_collapse_sequence_menu()


class PaintedTextButton(QtWidgets.QLabel):
    """Baseclass for text-based control buttons."""
    clicked = QtCore.Signal()
    doubleClicked = QtCore.Signal()
    message = QtCore.Signal(unicode)

    def __init__(self, height=common.CONTROL_HEIGHT, parent=None):
        super(PaintedTextButton, self).__init__(parent=parent)
        self._parent = None
        self.index = 0

        self.font = QtGui.QFont(common.PrimaryFont)

        self.setStatusTip(u'')
        self.setFixedHeight(height)

    def set_parent(self, widget):
        self._parent = widget

    def set_text(self, text):
        """Sets the text and the width for  the ``FilesTabButton``."""
        text = text if text else u'Files'
        self.setText(text.title())

        metrics = QtGui.QFontMetrics(self.font)
        width = metrics.width(self.text()) + (common.INDICATOR_WIDTH * 2)
        self.setFixedWidth(width)

    def enterEvent(self, event):
        """Emitting the statustip for the task bar."""
        self.message.emit(self.statusTip())
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def paintEvent(self, event):
        """The control button's paint method - shows the the set text and
        an underline if the tab is active."""
        if not self._parent:
            return

        rect = QtCore.QRect(self.rect())
        rect.setLeft(rect.left() + common.INDICATOR_WIDTH)

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        option = QtWidgets.QStyleOptionButton()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        if self._parent.currentIndex() == self.index:
            color = common.TEXT_SELECTED if hover else common.TEXT
        else:
            color = common.TEXT_SELECTED if hover else common.SECONDARY_TEXT

        common.draw_aliased_text(
            painter,
            self.font,
            rect,
            self.text(),
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            color
        )

        if self._parent.currentIndex() == self.index:
            metrics = QtGui.QFontMetrics(self.font)
            center = rect.center()
            rect.setHeight(2)
            rect.moveCenter(center)
            rect.moveTop(rect.top() + (metrics.height() / 2) + 3)
            rect.setWidth(metrics.width(self.text()))
            painter.setBrush(color)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRect(rect)
        painter.end()

    def mouseReleaseEvent(self, event):
        """Only triggered when the left buttons is pressed."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()

    def mouseDoubleClickEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.doubleClicked.emit()


class BookmarksTabButton(PaintedTextButton):
    """The button responsible for revealing the ``BookmarksWidget``"""

    def __init__(self, parent=None):
        super(BookmarksTabButton, self).__init__(parent=parent)
        self.index = 0
        self.set_text(u'Bookmarks')
        self.setStatusTip(u'Click to see the list of added bookmarks')


class AssetsTabButton(PaintedTextButton):
    """The button responsible for revealing the ``AssetsWidget``"""

    def __init__(self, parent=None):
        super(AssetsTabButton, self).__init__(parent=parent)
        self.index = 1
        self.set_text(u'Assets')
        self.setStatusTip(
            u'Click to see the list of available assets')


class FilesTabButton(PaintedTextButton):
    """The buttons responsible for swtiching the the FilesWidget and showing
    the switch to change the data-key."""

    def __init__(self, parent=None):
        self._view = None
        super(FilesTabButton, self).__init__(parent=parent)
        self.index = 2
        self.set_text(u'Files')
        self.setStatusTip(
            u'Click to see or change the current task folder')

        self.clicked.connect(self.show_view)

    def paintEvent(self, event):
        """Indicating the visibility of the DataKeyView."""
        if not self._view.isHidden():
            painter = QtGui.QPainter()
            painter.begin(self)

            rect = self.rect()
            center = rect.center()
            rect.setHeight(common.INLINE_ICON_SIZE + common.INDICATOR_WIDTH)
            rect.moveCenter(center)

            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(0, 0, 0, 30))

            painter.drawRoundedRect(rect, 4, 4)
            painter.drawRect(rect)

            common.draw_aliased_text(
                painter,
                common.PrimaryFont,
                rect,
                u'...',
                QtCore.Qt.AlignCenter,
                common.SECONDARY_BACKGROUND
            )
            painter.end()
        else:
            super(FilesTabButton, self).paintEvent(event)

    def view(self):
        return self._view

    def set_view(self, widget):
        self._view = widget

    @QtCore.Slot()
    def show_view(self):
        """Shows the ``DataKeyView`` widget for browsing."""
        if not self.view():
            return

        if self.view().model().rowCount() == 0:
            return

        if not self.view().isHidden():
            self.view().hide()
            return

        stackedwidget = self.view().altparent.parent().stackedwidget
        if stackedwidget.currentIndex() != 2:
            return  # We're not showing the widget when files are not tyhe visible list

        geo = self.view().parent().geometry()
        self.view().setGeometry(geo)
        self.view().move(0, 0)
        self.view().show()
        self.view().setFocus(QtCore.Qt.PopupFocusReason)
        self.view().viewport().setFocus(QtCore.Qt.PopupFocusReason)

        key = stackedwidget.currentWidget().model().sourceModel().data_key()
        if not key:
            return

        for n in xrange(self.view().model().rowCount()):
            index = self.view().model().index(n, 0)
            if key.lower() == index.data(QtCore.Qt.DisplayRole).lower():
                self.view().selectionModel().setCurrentIndex(
                    index, QtCore.QItemSelectionModel.ClearAndSelect)
                self.view().scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
                break


class FavouritesTabButton(PaintedTextButton):
    """Drop-down widget to switch between the list"""

    def __init__(self, parent=None):
        super(FavouritesTabButton, self).__init__(parent=parent)
        self.index = 3
        self.set_text(u'Starred')
        self.setStatusTip(u'Click to see your saved favourites')


class ListControlWidget(QtWidgets.QWidget):
    """The bar above the list to control the mode, filters and sorting."""

    textChanged = QtCore.Signal(unicode)
    listChanged = QtCore.Signal(int)
    dataKeyChanged = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(ListControlWidget, self).__init__(parent=parent)
        self._createUI()
        self._connectSignals()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(common.INDICATOR_WIDTH * 2)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedHeight(common.CONTROL_HEIGHT)

        # Control view/model/button
        self._bookmarksbutton = BookmarksTabButton(parent=self)
        self._assetsbutton = AssetsTabButton(parent=self)
        self._filesbutton = FilesTabButton(parent=self)

        self._controlview = DataKeyView(
            parent=self.parent().fileswidget, altparent=self)
        self._controlview.setHidden(True)

        self._filesbutton.set_view(self._controlview)
        self._favouritesbutton = FavouritesTabButton(parent=self)

        self._addbutton = AddButton(parent=self)
        self._generatethumbnailsbutton = GenerateThumbnailsButton(parent=self)
        self._todobutton = TodoButton(parent=self)
        self._filterbutton = FilterButton(parent=self)
        self._collapsebutton = CollapseSequenceButton(parent=self)
        self._archivedbutton = ToggleArchivedButton(parent=self)
        self._favouritebutton = ToggleFavouriteButton(parent=self)
        self._slackbutton = SlackButton(parent=self)
        self._togglebuttonsbutton = ToggleButtons(parent=self)

        self.layout().addSpacing(common.INDICATOR_WIDTH)
        self.layout().addWidget(self._bookmarksbutton)
        self.layout().addWidget(self._assetsbutton)
        self.layout().addWidget(self._filesbutton)
        self.layout().addWidget(self._favouritesbutton)
        self.layout().addStretch()
        self.layout().addWidget(self._togglebuttonsbutton)
        self.layout().addWidget(self._addbutton)
        self.layout().addWidget(self._generatethumbnailsbutton)
        self.layout().addWidget(self._todobutton)
        self.layout().addWidget(self._filterbutton)
        self.layout().addWidget(self._collapsebutton)
        self.layout().addWidget(self._archivedbutton)
        self.layout().addWidget(self._favouritebutton)
        self.layout().addWidget(self._slackbutton)
        self.layout().addSpacing(common.INDICATOR_WIDTH * 2)

    @QtCore.Slot(QtCore.QModelIndex)
    def signal_dispatcher(self, index):
        self.listChanged.emit(2)
        self.dataKeyChanged.emit(index.data(QtCore.Qt.DisplayRole))
        self.textChanged.emit(index.data(QtCore.Qt.DisplayRole))

    def _connectSignals(self):
        pass

    def control_view(self):
        return self._controlview

    def control_button(self):
        return self.findChild(FilesTabButton)
