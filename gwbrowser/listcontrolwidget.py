# -*- coding: utf-8 -*-
"""Widget reponsible controlling the displayed list and the filter-modes."""

from PySide2 import QtWidgets, QtGui, QtCore

from gwbrowser.datakeywidget import DataKeyView
import gwbrowser.common as common
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.common_ui import ClickableIconButton, PaintedLabel
from gwbrowser.editors import FilterEditor

from gwbrowser.imagecache import ImageCache
from gwbrowser.fileswidget import FileThumbnailWorker

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

    def stacked_widget(self):
        if not self.parent():
            return None
        if not self.parent():
            return None
        try:
            return self.parent().parent().stackedwidget
        except:
            return None

    def current_widget(self):
        if not self.stacked_widget():
            return None
        if self.stacked_widget().currentIndex() > 3:
            return None
        return self.stacked_widget().currentWidget()

    def current_index(self):
        if not self.stacked_widget():
            return None
        return self.stacked_widget().currentIndex()


class FilterButton(BaseControlButton):
    """Button for showing the filter editor."""

    def __init__(self, parent=None):
        super(FilterButton, self).__init__(
            u'filter',
            u'Edit search filter',
            parent=parent
        )

    def state(self):
        if not self.current_widget():
            return False
        filter_text = self.current_widget().model().filterText()
        if not filter_text:
            return False
        if filter_text == u'/':
            return False
        return True

    def action(self):
        """The action to perform when finished editing the filter text."""
        if not self.current_widget():
            return
        filter_text = self.current_widget().model().filterText()
        filter_text = common.clean_filter_text(filter_text)
        #
        parent = self.stacked_widget().parent().stackedwidget
        editor = FilterEditor(filter_text, parent=parent)

        model = self.current_widget().model()
        editor.finished.connect(lambda x: model.filterTextChanged.emit(
            common.regexify_filter_text(x)))
        editor.finished.connect(self.update)
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
        if not self.current_widget():
            return
        datatype = self.current_widget().model().sourceModel().data_type()
        if datatype == common.FileItem:
            return False
        return True

    @QtCore.Slot()
    def action(self):
        """Only lists containing sequences can be collapsed."""
        if self.current_index() not in (2, 3):
            return
        if not self.current_widget():
            return
        datatype = self.current_widget().model().sourceModel().data_type()
        if datatype == common.FileItem:
            self.current_widget().model().sourceModel().dataTypeChanged.emit(common.SequenceItem)
        else:
            self.current_widget().model().sourceModel().dataTypeChanged.emit(common.FileItem)

    def update(self):
        super(CollapseSequenceButton, self).update()
        if self.current_index() in (2, 3):
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
        if not self.current_widget():
            return
        val = self.current_widget().model().filterFlag(common.MarkedAsArchived)
        return val

    @QtCore.Slot()
    def action(self):
        if not self.current_widget():
            return
        val = self.current_widget().model().filterFlag(common.MarkedAsArchived)
        self.current_widget().model().filterFlagChanged.emit(
            common.MarkedAsArchived, not val)

    def update(self):
        super(ToggleArchivedButton, self).update()
        if self.current_index() < 3:
            self.show()
        else:
            self.hide()


class SimpleModeButton(BaseControlButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(SimpleModeButton, self).__init__(
            u'showbuttons',
            u'Show or hide list buttons',
            parent=parent
        )

    def state(self):
        if not self.current_widget():
            return False
        val = self.current_widget().buttons_hidden()
        return val

    def showEvent(self, event):
        if not self.current_widget():
            return
        cls = self.current_widget().__class__.__name__
        k = 'widget/{}/sort_with_basename'.format(cls)
        val = local_settings.value(k)
        if val is None:
            local_settings.setValue(k, self.state())
        common.SORT_WITH_BASENAME = val

    def hideEvent(self, event):
        common.SORT_WITH_BASENAME = False


    @QtCore.Slot()
    def action(self):
        if not self.current_widget():
            return
        val = self.state()
        common.SORT_WITH_BASENAME = not val
        self.current_widget().set_buttons_hidden(not val)
        self.current_widget().model().sourceModel().sort_data()
        self.current_widget().reset()

        cls = self.current_widget().__class__.__name__
        k = 'widget/{}/sort_with_basename'.format(cls)
        local_settings.setValue(k, not val)

        # self.current_widget().update()

    def update(self):
        super(SimpleModeButton, self).update()
        if self.current_index() == 2:
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
        if not self.current_widget():
            return
        val = self.current_widget().model().filterFlag(common.MarkedAsFavourite)
        return val

    @QtCore.Slot()
    def action(self):
        if not self.current_widget():
            return
        val = self.current_widget().model().filterFlag(common.MarkedAsFavourite)
        self.current_widget().model().filterFlagChanged.emit(
            common.MarkedAsFavourite, not val)

    def update(self):
        super(ToggleFavouriteButton, self).update()
        if self.current_index() < 3:
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
        if self.current_index() == 0:
            return True
        if self.current_index() == 1:
            if self.stacked_widget().widget(0).model().sourceModel().active_index().isValid():
                return True
            return False
        if self.current_index() == 2:
            if self.stacked_widget().widget(1).model().sourceModel().active_index().isValid():
                return True
            return False
        return False

    def add_asset(self):
        from gwbrowser.addassetwidget import AddAssetWidget

        view = self.stacked_widget().widget(0)
        model = view.model().sourceModel()
        bookmark = model.active_index()
        if not bookmark.isValid():
            return

        bookmark = bookmark.data(common.ParentRole)
        bookmark = u'/'.join(bookmark)
        widget = AddAssetWidget(
            bookmark, parent=self.stacked_widget())
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
        view = self.stacked_widget().widget(1)
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
        if not self.current_widget():
            return
        # Bookmark
        if self.current_index() == 0:
            self.current_widget().show_add_bookmark_widget()
            return
        # Asset
        if self.current_index() == 1:
            self.add_asset()
            return
        # This will open the Saver to save a new file
        if self.current_index() == 2:
            self.create_file()

    def update(self):
        """The button is only visible when showing bookmarks or files."""
        super(AddButton, self).update()
        if self.current_index() in (0, 1, 2):
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
        if not self.current_widget():
            return
        if self.current_index() < 2:
            return False
        model = self.current_widget().model().sourceModel()
        return model.generate_thumbnails

    @QtCore.Slot()
    def action(self):
        """Toggles thumbnail generation."""
        if not self.current_widget():
            return
        model = self.current_widget().model().sourceModel()
        val = model.generate_thumbnails

        cls = model.__class__.__name__
        local_settings.setValue(
            u'widget/{}/generate_thumbnails'.format(cls), not val)
        if not val == False:
            FileThumbnailWorker.reset_queue()
        model.generate_thumbnails = not val
        self.update()

    def update(self):
        """Will only show for favourite and file items."""
        super(GenerateThumbnailsButton, self).update()
        if self.current_index() >= 2:
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

    def __init__(self, label, idx, description, height=common.CONTROL_HEIGHT, parent=None):
        super(PaintedTextButton, self).__init__(parent=parent)
        self.default_label = label
        self._height = height
        self.index = idx
        self.font = QtGui.QFont(common.PrimaryFont)

        self.setStatusTip(description)
        self.setToolTip(description)

        self.timer = QtCore.QTimer(parent=self)
        self.timer.setSingleShot(False)
        self.timer.setInterval(400)
        self.timer.timeout.connect(self.adjust_size)
        self.timer.start()

    def stacked_widget(self):
        if not self.parent():
            return
        if not self.parent().parent():
            return
        try:
            return self.parent().parent().stackedwidget
        except:
            return None

    def current_widget(self):
        if not self.stacked_widget():
            return None
        if self.stacked_widget().currentIndex() > 3:
            return None
        return self.stacked_widget().currentWidget()

    def current_index(self):
        if not self.stacked_widget():
            return None
        return self.stacked_widget().currentIndex()

    def active_index(self, idx):
        if not self.stacked_widget():
            return
        return self.stacked_widget().widget(idx).model().sourceModel().active_index()

    def enterEvent(self, event):
        """Emitting the statustip for the task bar."""
        self.message.emit(self.statusTip())
        self.update()

    def leaveEvent(self, event):
        self.update()

    def paintEvent(self, event):
        """The control button's paint method - shows the the set text and
        an underline if the tab is active."""
        if not self.stacked_widget():
            return

        rect = QtCore.QRect(self.rect())

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        option = QtWidgets.QStyleOptionButton()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        if self.current_index() == self.index:
            color = common.TEXT_SELECTED if hover else common.TEXT
        else:
            color = common.SECONDARY_TEXT if hover else common.BACKGROUND

        common.draw_aliased_text(
            painter,
            self.font,
            rect,
            self.text(),
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            color
        )

        if not hover and self.current_index() != self.index:
            return
        metrics = QtGui.QFontMetrics(self.font)
        center = rect.center()
        rect.setHeight(2)
        rect.moveCenter(center)
        rect.moveTop(rect.top() + (metrics.height() / 2) + 3)
        rect.setWidth(metrics.width(self.text()))
        painter.setBrush(color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setOpacity(0.5)
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

    def text(self):
        if not self.stacked_widget():
            return self.default_label
        index = self.active_index(self.index)
        if index.isValid():
            text = index.data(QtCore.Qt.DisplayRole).split(u'/').pop().upper()
            if self.parent().parent().width() < 640:
                if len(text) > 20:
                    text = u'{}...{}'.format(text[0:8], text[-9:])
        else:
            text = self.default_label
        return text

    def get_size(self):
        metrics = QtGui.QFontMetrics(self.font)
        width = metrics.width(self.text()) + (common.INDICATOR_WIDTH * 2)
        return QtCore.QSize(width, self._height)

    @QtCore.Slot()
    def adjust_size(self):
        """Slot responsible for setting the size of the widget to match the text."""
        self.setFixedSize(self.get_size())
        self.repaint()
        self.update()

    def showEvent(self, event):
        self.adjust_size()


class BookmarksTabButton(PaintedTextButton):
    """The button responsible for revealing the ``BookmarksWidget``"""

    def __init__(self, parent=None):
        super(BookmarksTabButton, self).__init__(
            u'Select bookmark...',
            0,
            u'Click to see the list of added bookmarks',
            parent=parent
        )
    def text(self):
        if not self.stacked_widget():
            return self.default_label
        index = self.active_index(self.index)
        if index.isValid():
            text = u'Bookmarks'
        else:
            text = self.default_label
        return text


class AssetsTabButton(PaintedTextButton):
    """The button responsible for revealing the ``AssetsWidget``"""

    def __init__(self, parent=None):
        super(AssetsTabButton, self).__init__(
            u'Select asset...',
            1,
            u'Click to see the list of available assets',
            parent=parent
        )

    @QtCore.Slot()
    def adjust_size(self):
        if not self.stacked_widget():
            return
        index = self.stacked_widget().widget(0).model().sourceModel().active_index()
        self.setHidden(not index.isValid())
        super(AssetsTabButton, self).adjust_size()



class FilesTabButton(PaintedTextButton):
    """The buttons responsible for swtiching the the FilesWidget and showing
    the switch to change the data-key."""

    def __init__(self, parent=None):
        super(FilesTabButton, self).__init__(
            u'Select folder...',
            2,
            u'Click to see or change the current task folder',
            parent=parent)
        self.clicked.connect(self.show_view)

    def view(self):
        return self.parent().data_key_view

    @QtCore.Slot()
    def adjust_size(self):
        if not self.stacked_widget():
            return
        index = self.stacked_widget().widget(1).model().sourceModel().active_index()
        self.setHidden(not index.isValid())
        super(FilesTabButton, self).adjust_size()

    def text(self):
        if not self.stacked_widget():
            return self.default_label
        data_key = self.stacked_widget().widget(2).model().sourceModel().data_key()
        if data_key:
            data_key = data_key.upper()
            if len(data_key) > 25:
                data_key = u'{}...{}'.format(data_key[0:10], data_key[-12:])
        else:
            data_key = self.default_label
        return data_key

    def paintEvent(self, event):
        """Indicating the visibility of the DataKeyView."""
        if not self.view().isHidden():
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
                common.BACKGROUND
            )
            painter.end()
        else:
            super(FilesTabButton, self).paintEvent(event)

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
        super(FavouritesTabButton, self).__init__(
            u'Starred',
            3,
            u'Click to see your saved favourites',
            parent=parent
        )


class ListControlWidget(QtWidgets.QWidget):
    """The bar above the stacked widget containing the main app control buttons.
    """

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
        self.layout().setSpacing(common.INDICATOR_WIDTH)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedHeight(common.CONTROL_HEIGHT)

        # Control view/model/button
        self.bookmarks_button = BookmarksTabButton(parent=self)
        self.assets_button = AssetsTabButton(parent=self)
        self.files_button = FilesTabButton(parent=self)
        self.favourites_button = FavouritesTabButton(parent=self)

        self.data_key_view = DataKeyView(
            parent=self.parent().fileswidget, altparent=self)
        self.data_key_view.setHidden(True)


        self.add_button = AddButton(parent=self)
        self.generate_thumbnails_button = GenerateThumbnailsButton(parent=self)
        self.filter_button = FilterButton(parent=self)
        self.collapse_button = CollapseSequenceButton(parent=self)
        self.archived_button = ToggleArchivedButton(parent=self)
        self.favourite_button = ToggleFavouriteButton(parent=self)
        self.slack_button = SlackButton(parent=self)
        self.simple_mode_button = SimpleModeButton(parent=self)

        self.layout().addSpacing(common.INDICATOR_WIDTH)
        #
        self.layout().addWidget(self.bookmarks_button)
        # sep = PaintedLabel(u': ', color=common.SECONDARY_BACKGROUND, size=common.MEDIUM_FONT_SIZE, parent=self)
        # sep.setFixedHeight(common.CONTROL_HEIGHT)
        # self.layout().addWidget(sep, 0)
        self.layout().addWidget(self.assets_button)
        self.layout().addWidget(self.files_button)
        sep = PaintedLabel(u'| ', color=common.SECONDARY_BACKGROUND, size=common.MEDIUM_FONT_SIZE, parent=self)
        sep.setFixedHeight(common.CONTROL_HEIGHT)
        self.layout().addWidget(sep, 0)
        self.layout().addWidget(self.favourites_button)
        #
        self.layout().addStretch()
        #
        self.layout().addWidget(self.simple_mode_button)
        self.layout().addWidget(self.add_button)
        self.layout().addWidget(self.generate_thumbnails_button)
        self.layout().addWidget(self.filter_button)
        self.layout().addWidget(self.collapse_button)
        self.layout().addWidget(self.archived_button)
        self.layout().addWidget(self.favourite_button)
        self.layout().addWidget(self.slack_button)
        #
        self.layout().addSpacing(common.INDICATOR_WIDTH * 2)

    @QtCore.Slot(QtCore.QModelIndex)
    def signal_dispatcher(self, index):
        self.dataKeyChanged.emit(index.data(QtCore.Qt.DisplayRole))
        self.textChanged.emit(index.data(QtCore.Qt.DisplayRole))
        self.listChanged.emit(2)

    def _connectSignals(self):
        pass

    def control_view(self):
        return self.data_key_view

    def control_button(self):
        return self.findChild(FilesTabButton)
