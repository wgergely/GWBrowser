# -*- coding: utf-8 -*-
"""Widget reponsible controlling the displayed list and the filter-modes."""

from PySide2 import QtWidgets, QtGui, QtCore

from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.common_ui import ClickableIconButton
from gwbrowser.common_ui import PaintedLabel
from gwbrowser.datakeywidget import DataKeyView
from gwbrowser.editors import FilterEditor
from gwbrowser.fileswidget import FileThumbnailWorker
from gwbrowser.imagecache import ImageCache
from gwbrowser.settings import local_settings
import gwbrowser.common as common


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
        filter_text = self.current_widget().model().filter_text()
        if not filter_text:
            return False
        if filter_text == u'/':
            return False
        return True

    def action(self):
        """The action to perform when finished editing the filter text."""
        if not self.current_widget():
            return
        if self.current_widget().filter_editor.isHidden():
            self.current_widget().filter_editor.show()
            return
        self.current_widget().filter_editor.hide()

    def mouseReleaseEvent(self, event):
        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        no_modifier = modifiers == QtCore.Qt.NoModifier
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier
        control_modifier = modifiers & QtCore.Qt.ControlModifier

        if alt_modifier or shift_modifier or control_modifier:
            self.current_widget().model().filterTextChanged.emit(u'')
            return

        super(FilterButton, self).mouseReleaseEvent(event)


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
            self.current_widget().model().sourceModel(
            ).dataTypeChanged.emit(common.SequenceItem)
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
            u'Show Favourites only',
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
        self.parent().listChanged.emit(6)

    def state(self):
        return True


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
        k = u'widget/{}/generate_thumbnails'.format(cls)

        local_settings.setValue(k, not val)
        model.generate_thumbnails = not val
        self.update()

        if not val == False:
            model.ThumbnailThread.Worker.reset_queue()
            FileThumbnailWorker.reset_queue()
        if val == True:
            self.current_widget().initialize_visible_indexes()

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

    def __init__(self, label, idx, description, parent=None):
        super(PaintedTextButton, self).__init__(parent=parent)
        self.default_label = label
        self.index = idx
        self.font = QtGui.QFont(common.PrimaryFont)
        self.font.setPointSizeF(common.MEDIUM_FONT_SIZE)

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
        self.message.emit(u' ')
        self.update()

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
        o = common.INDICATOR_WIDTH * 3
        width = QtGui.QFontMetrics(self.font).width(self.text()) + (o * 2)
        height = common.INLINE_ICON_SIZE + (common.INDICATOR_WIDTH * 2)
        return QtCore.QSize(width, height)

    @QtCore.Slot()
    def adjust_size(self):
        """Slot responsible for setting the size of the widget to match the text."""
        self.setFixedSize(self.get_size())
        self.update()

    def showEvent(self, event):
        self.adjust_size()

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
        painter.setPen(QtCore.Qt.NoPen)

        if self.current_index() == self.index:
            color = common.TEXT_SELECTED if hover else common.TEXT
            painter.setBrush(color)
        else:
            color = common.TEXT if hover else common.BACKGROUND
            painter.setBrush(color)

        metrics = QtGui.QFontMetrics(self.font)
        width = metrics.width(self.text())

        x = (self.width() / 2.0) - (width / 2.0)
        y = self.rect().center().y() + (metrics.ascent() * 0.5)
        path = QtGui.QPainterPath()
        path.addText(x, y, self.font, self.text())
        painter.drawPath(path)


        if self.current_index() != self.index:
            return
        color = common.TEXT if hover else common.REMOVE
        rect.setHeight(2.0)
        rect.setWidth(self.rect().width())
        painter.setBrush(color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setOpacity(0.9)
        painter.drawRect(rect)
        painter.end()


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

            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(0, 0, 0, 30))
            painter.drawRect(self.rect())

            rect = self.rect()
            center = rect.center()
            rect.setHeight(2.0)
            painter.setBrush(common.ADD)
            painter.drawRect(rect)

            common.draw_aliased_text(
                painter,
                common.PrimaryFont,
                self.rect(),
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
            u'Favourites',
            3,
            u'Click to see your saved favourites',
            parent=parent
        )


class ListControlWidgetDropOverlay(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ListControlWidgetDropOverlay, self).__init__(parent=parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.drop_target = True
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint
        )
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

    def paintEvent(self, event):
        if not self.drop_target:
            return

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.SEPARATOR)
        painter.drawRoundedRect(self.rect(), 4, 4)

        pixmap = ImageCache.get_rsc_pixmap(u'slack', common.ADD, self.rect().height() - 6)
        rect = pixmap.rect()
        rect.moveCenter(self.rect().center())
        painter.drawPixmap(rect, pixmap, pixmap.rect())

        rect = self.rect().marginsRemoved(QtCore.QMargins(1,1,1,1))
        painter.setBrush(QtCore.Qt.NoBrush)
        pen = QtGui.QPen(common.ADD)
        pen.setWidthF(2.0)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 4, 4)

        painter.end()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        import gwbrowser.slacker as slacker
        if event.source() == self:
            return  # Won't allow dropping an item from itself
        mime = event.mimeData()

        if not mime.hasUrls():
            return

        event.accept()

        message = []
        for f in mime.urls():
            file_info = QtCore.QFileInfo(f.toLocalFile())
            line = u'```{}```'.format(file_info.filePath())
            message.append(line)

        message = u'\n'.join(message)
        self.parent().parent().slack_widget.append_message(message)
        self.parent().listChanged.emit(6)

    def showEvent(self, event):
        pos = self.parent().rect().topLeft()
        pos = self.parent().mapToGlobal(pos)
        self.move(pos)
        self.setFixedWidth(self.parent().rect().width())
        self.setFixedHeight(self.parent().rect().height())


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
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        height = common.INLINE_ICON_SIZE + (common.INDICATOR_WIDTH * 2)
        self.setFixedHeight(height)

        # Control view/model/button
        self.bookmarks_button = BookmarksTabButton(parent=self)
        self.assets_button = AssetsTabButton(parent=self)
        self.files_button = FilesTabButton(parent=self)
        self.favourites_button = FavouritesTabButton(parent=self)

        self.data_key_view = DataKeyView(
            parent=self.parent().fileswidget, altparent=self)
        self.data_key_view.setHidden(True)

        self.generate_thumbnails_button = GenerateThumbnailsButton(parent=self)
        self.filter_button = FilterButton(parent=self)
        self.collapse_button = CollapseSequenceButton(parent=self)
        self.archived_button = ToggleArchivedButton(parent=self)
        self.favourite_button = ToggleFavouriteButton(parent=self)
        self.slack_button = SlackButton(parent=self)
        self.simple_mode_button = SimpleModeButton(parent=self)

        t = QtGui.QTransform()
        t.rotate(180)
        pixmap = ImageCache.get_rsc_pixmap(
            u'gradient', None, height)
        pixmap = pixmap.transformed(t)
        pixmap = pixmap.scaled(common.INDICATOR_WIDTH, pixmap.height())
        label = QtWidgets.QLabel()
        label.setPixmap(pixmap)
        self.layout().addWidget(label)

        self.layout().addWidget(self.bookmarks_button)
        self.layout().addWidget(self.assets_button)
        self.layout().addWidget(self.files_button)
        self.layout().addWidget(self.favourites_button)
        self.layout().addStretch()
        self.layout().addWidget(self.simple_mode_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH)
        self.layout().addWidget(self.generate_thumbnails_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH)
        self.layout().addWidget(self.filter_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH)
        self.layout().addWidget(self.collapse_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH)
        self.layout().addWidget(self.archived_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH)
        self.layout().addWidget(self.favourite_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH)
        self.layout().addWidget(self.slack_button)
        #
        self.layout().addSpacing(common.INDICATOR_WIDTH * 2)

        self.drop_overlay = ListControlWidgetDropOverlay(parent=self)
        self.drop_overlay.setHidden(True)

    @QtCore.Slot()
    def update_buttons(self):
        self.bookmarks_button.update()
        self.assets_button.update()
        self.files_button.update()
        self.favourites_button.update()
        self.generate_thumbnails_button.update()
        self.filter_button.update()
        self.collapse_button.update()
        self.archived_button.update()
        self.favourite_button.update()
        self.slack_button.update()
        self.simple_mode_button.update()

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

    def paintEvent(self, event):
        painter=QtGui.QPainter()
        painter.begin(self)
        pixmap = ImageCache.get_rsc_pixmap(u'gradient', None, self.height())
        t = QtGui.QTransform()

        t.rotate(90)
        pixmap = pixmap.transformed(t)
        painter.setOpacity(0.5)
        painter.drawPixmap(self.rect(), pixmap, pixmap.rect())
        painter.end()
