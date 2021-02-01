# -*- coding: utf-8 -*-
"""The bar above the bookmark/asset/file widgets.

"""
import functools
from PySide2 import QtWidgets, QtGui, QtCore

from . import log
from . import common
from . import common_ui
from . import contextmenu
from . import images
from . import settings
from . import bookmark_db
from . import actions
from . import shortcuts

from .lists import tasks
from .lists import base
from .lists import delegate


class QuickSwitchMenu(contextmenu.BaseContextMenu):
    def stacked_widget(self):
        return self.parent().parent().parent().stackedwidget

    @property
    def index(self):
        return self.stacked_widget().currentWidget().model().sourceModel().active_index()

    @index.setter
    def index(self, v):
        pass

    def add_switch_menu(self, widget, label):
        """Adds the items needed to quickly change bookmarks or assets."""
        off_pixmap = images.ImageCache.get_rsc_pixmap(
            u'folder', common.SECONDARY_TEXT, common.MARGIN())
        on_pixmap = images.ImageCache.get_rsc_pixmap(
            u'check', common.ADD, common.MARGIN())

        self.menu[label] = {
            u'disabled': True
        }

        active_index = widget.model().sourceModel().active_index()
        for n in xrange(widget.model().rowCount()):
            index = widget.model().index(n, 0)

            name = index.data(QtCore.Qt.DisplayRole)
            active = False
            if active_index.isValid():
                n = active_index.data(QtCore.Qt.DisplayRole)
                active = n.lower() == name.lower()

            thumbnail_path = images.get_cached_thumbnail_path(
                index.data(common.ParentPathRole)[0],
                index.data(common.ParentPathRole)[1],
                index.data(common.ParentPathRole)[2],
                index.data(QtCore.Qt.StatusTipRole),
            )
            pixmap = images.ImageCache.get_pixmap(
                thumbnail_path, common.MARGIN() * 2)
            pixmap = pixmap if pixmap else off_pixmap
            pixmap = on_pixmap if active else pixmap
            icon = QtGui.QIcon(pixmap)
            self.menu[name.upper()] = {
                u'icon': icon,
                u'action': functools.partial(widget.activate, index)
            }
        return


class SwitchBookmarkMenu(QuickSwitchMenu):
    def setup(self):
        self.add_menu()
        self.separator()
        self.add_switch_menu(
            self.stacked_widget().widget(base.BookmarkTab),
            u'Change Bookmark'
        )

    def add_menu(self):
        self.menu[u'add'] = {
            u'icon': self.get_icon(u'add', color=common.ADD),
            u'text': u'Add Bookmark...',
            u'action': actions.add_bookmark,
            'shortcut': shortcuts.string(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
        }


class SwitchAssetMenu(QuickSwitchMenu):
    def setup(self):
        self.add_menu()
        self.separator()
        self.add_switch_menu(
            self.stacked_widget().widget(base.AssetTab),
            u'Change Asset'
        )

    def add_menu(self):
        self.menu[u'add'] = {
            u'icon': self.get_icon(u'add', color=common.ADD),
            u'text': u'Add Asset...',
            u'action': actions.add_asset,
            'shortcut': shortcuts.string(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
        }


class BaseControlButton(common_ui.ClickableIconButton):
    """Base-class used for control buttons on the top bar."""

    def __init__(self, pixmap, description, color=(common.TEXT_SELECTED, common.SECONDARY_BACKGROUND), parent=None):
        super(BaseControlButton, self).__init__(
            pixmap,
            color,
            common.MARGIN(),
            description=description,
            parent=parent
        )

    def stacked_widget(self):
        if not self.parent():
            return None
        try:
            return self.parent().parent().stackedwidget
        except:
            log.Error('Error getting stackedwidget')
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
    def __init__(self, parent=None):
        super(FilterButton, self).__init__(
            u'filter',
            u'Search  -  {}'.format(shortcuts.string(shortcuts.MainWidgetShortcuts, shortcuts.ToggleSearch)),
            parent=parent
        )
        self.clicked.connect(actions.signals.toggleFilterButton)
        actions.signals.toggleFilterButton.connect(self.update)

    def state(self):
        if not self.current_widget():
            return False
        filter_text = self.current_widget().model().filter_text()
        if not filter_text:
            return False
        if filter_text == u'/':
            return False
        return True

    def mouseReleaseEvent(self, event):
        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier
        control_modifier = modifiers & QtCore.Qt.ControlModifier

        if alt_modifier or shift_modifier or control_modifier:
            self.current_widget().model().set_filter_text(u'')
            self.current_widget().model().filterTextChanged.emit(u'')
            return

        super(FilterButton, self).mouseReleaseEvent(event)


class ToggleSequenceButton(BaseControlButton):
    def __init__(self, parent=None):
        super(ToggleSequenceButton, self).__init__(
            u'collapse',
            u'Show Files or Sequences  -  {}'.format(shortcuts.string(shortcuts.MainWidgetShortcuts, shortcuts.ToggleSequence)),
            parent=parent
        )

        self.clicked.connect(actions.signals.toggleSequenceButton)
        actions.signals.toggleSequenceButton.connect(self.update)

    def pixmap(self):
        if self.state():
            return images.ImageCache.get_rsc_pixmap(u'collapse', self._on_color, common.MARGIN())
        return images.ImageCache.get_rsc_pixmap(u'expand', self._off_color, common.MARGIN())

    def state(self):
        if not self.current_widget():
            return
        datatype = self.current_widget().model().sourceModel().data_type()
        if datatype == common.FileItem:
            return False
        return True

    def update(self):
        super(ToggleSequenceButton, self).update()
        if self.current_index() in (base.FileTab, base.FavouriteTab):
            self.show()
        else:
            self.hide()


class ToggleArchivedButton(BaseControlButton):
    def __init__(self, parent=None):
        super(ToggleArchivedButton, self).__init__(
            u'collapse',
            u'Show/Hide Archived Items  -  {}'.format(shortcuts.string(shortcuts.MainWidgetShortcuts, shortcuts.ToggleArchived)),
            parent=parent
        )

        self.clicked.connect(actions.signals.toggleArchivedButton)
        actions.signals.toggleArchivedButton.connect(self.update)

    def pixmap(self):
        if self.state():
            return images.ImageCache.get_rsc_pixmap(u'active', self._on_color, common.MARGIN())
        return images.ImageCache.get_rsc_pixmap(u'archived', self._off_color, common.MARGIN())

    def state(self):
        if not self.current_widget():
            return
        return self.current_widget().model().filter_flag(common.MarkedAsArchived)

    def update(self):
        super(ToggleArchivedButton, self).update()
        if self.current_index() < base.FavouriteTab:
            self.show()
        else:
            self.hide()


class SimpleModeButton(BaseControlButton):
    def __init__(self, parent=None):
        super(SimpleModeButton, self).__init__(
            u'showbuttons',
            u'Show/Hide List Buttons  -  {}'.format(shortcuts.string(shortcuts.MainWidgetShortcuts, shortcuts.HideInlineButtons)),
            parent=parent
        )

        self.clicked.connect(actions.signals.toggleSimpleButton)
        actions.signals.toggleSimpleButton.connect(self.update)

    def state(self):
        if not self.current_widget():
            return False
        val = self.current_widget().buttons_hidden()
        return val

    def showEvent(self, event):
        widget = self.current_widget()
        if not widget:
            return

        val = widget.model().sourceModel().get_local_setting(
            settings.SortByBaseNameKey,
            key=widget.__class__.__name__,
            section=settings.UIStateSection
        )
        if val is None:
            widget.model().sourceModel().set_local_setting(
                settings.SortByBaseNameKey,
                self.state(),
                key=widget.__class__.__name__,
                section=settings.UIStateSection
            )
        common.SORT_WITH_BASENAME = val

    def hideEvent(self, event):
        common.SORT_WITH_BASENAME = False


class ToggleFavouriteButton(BaseControlButton):
    def __init__(self, parent=None):
        super(ToggleFavouriteButton, self).__init__(
            u'favourite',
            u'Show/Hide My Files Only  -  {}'.format(shortcuts.string(shortcuts.MainWidgetShortcuts, shortcuts.ToggleFavourite)),
            parent=parent
        )
        self.clicked.connect(actions.signals.toggleFavouritesButton)
        actions.signals.toggleFavouritesButton.connect(self.update)


    def state(self):
        if not self.current_widget():
            return
        val = self.current_widget().model().filter_flag(common.MarkedAsFavourite)
        return val

    def update(self):
        super(ToggleFavouriteButton, self).update()
        if self.current_index() < 3:
            self.show()
        else:
            self.hide()


class SlackButton(BaseControlButton):
    def __init__(self, parent=None):
        super(SlackButton, self).__init__(
            u'slack_color',
            u'Slack Massenger',
            color=(None, None),
            parent=parent
        )
        actions.signals.bookmarkValueUpdated.connect(self.check_token)

    @QtCore.Slot()
    def action(self):
        """Opens the set slack workspace."""
        actions.show_slack()

    def state(self):
        return True

    @QtCore.Slot()
    def check_token(self):
        """Checks if the current bookmark has an active slack token set.

        If the value is set we'll show the button, otherwise it will stay hidden.

        """
        args = [settings.active(f) for f in (settings.ServerKey, settings.JobKey, settings.RootKey)]
        if not all(args):
            self.setHidden(True)
            return False

        with bookmark_db.transactions(*args) as db:
            source = u'/'.join(args)
            slacktoken = db.value(
                source,
                u'slacktoken',
                table=bookmark_db.BookmarkTable
            )

        if not slacktoken:
            self.setHidden(True)
            return False

        self.setHidden(False)
        return True


class GenerateThumbnailsButton(BaseControlButton):
    def __init__(self, parent=None):
        super(GenerateThumbnailsButton, self).__init__(
            u'spinner_btn',
            u'Enable/Disable Generating Thumbnails  -  {}'.format(shortcuts.string(shortcuts.MainWidgetShortcuts, shortcuts.ToggleGenerateThumbnails)),
            parent=parent
        )
        self.clicked.connect(actions.signals.toggleMakeThumbnailsButton)
        actions.signals.toggleMakeThumbnailsButton.connect(self.update)


    def state(self):
        """The state of the auto-thumbnails"""
        if not self.current_widget():
            return
        model = self.current_widget().model().sourceModel()
        return model.generate_thumbnails_enabled()

    @QtCore.Slot()
    def action(self):
        """Toggles thumbnail generation."""



class CollapseSequenceMenu(contextmenu.BaseContextMenu):
    def __init__(self, parent=None):
        super(CollapseSequenceMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_collapse_sequence_menu()


class PaintedTextButton(QtWidgets.QLabel):
    """Baseclass for text-based control buttons."""
    icon = u'assets'

    clicked = QtCore.Signal()
    doubleClicked = QtCore.Signal()
    message = QtCore.Signal(unicode)

    def __init__(self, label, idx, description, parent=None):
        super(PaintedTextButton, self).__init__(parent=parent)
        self.default_label = label
        self.index = idx

        self.setStatusTip(description)
        self.setToolTip(description)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        self.timer = QtCore.QTimer(parent=self)
        self.timer.setSingleShot(False)
        self.timer.setInterval(400)
        self.timer.timeout.connect(self.adjust_size)
        self.timer.start()

    @property
    def active_label(self):
        return self.default_label

    def stacked_widget(self):
        if not self.parent():
            return
        if not self.parent().parent():
            return
        try:
            return self.parent().parent().stackedwidget
        except:
            log.error(u'Error.')
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
        text = self.active_label.upper() if self.active_label else self.default_label
        if len(text) > 20:
            text = u'{}...{}'.format(text[0:8], text[-9:])
        return text

    def get_width(self):
        o = common.INDICATOR_WIDTH() * 6
        _, metrics = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())
        return metrics.width(self.text()) + o

    @QtCore.Slot()
    def adjust_size(self):
        """Slot responsible for setting the size of the widget to match the text."""
        self.setMaximumWidth(self.get_width())
        self.setMinimumWidth(common.MARGIN() * 2)
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

        font, metrics = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())

        # When the width of the button is very small, we'll switch to an icon
        # representation instead of text:
        if (metrics.width(self.text()) + (common.MARGIN() * 0.5)) < self.rect().width():
            # Draw label
            width = metrics.width(self.text())
            x = (self.width() / 2.0) - (width / 2.0)
            y = self.rect().center().y() + (metrics.ascent() * 0.5)
            path = delegate.get_painter_path(x, y, font, self.text())
            painter.drawPath(path)
        else:
            # Draw icon
            pixmap = images.ImageCache.get_rsc_pixmap(
                self.icon,
                color,
                common.MARGIN()
            )
            _rect = QtCore.QRect(0, 0, common.MARGIN(), common.MARGIN())
            _rect.moveCenter(self.rect().center())
            painter.drawPixmap(
                _rect,
                pixmap,
                pixmap.rect()
            )

        # Draw indicator line below icon or text
        rect.setHeight(common.ROW_SEPARATOR() * 2.0)
        painter.setPen(QtCore.Qt.NoPen)
        rect.setWidth(self.rect().width())

        if self.current_index() == self.index:
            painter.setOpacity(0.9)
            color = common.TEXT if hover else common.REMOVE
        else:
            painter.setOpacity(0.3)
            color = common.TEXT if hover else common.FAVOURITE

        painter.setBrush(color)
        painter.drawRect(rect)
        painter.end()


class BookmarksTabButton(PaintedTextButton):
    """The button responsible for revealing the ``BookmarksWidget``"""
    icon = u'bookmark'

    def __init__(self, parent=None):
        super(BookmarksTabButton, self).__init__(
            u'Bookmarks',
            base.BookmarkTab,
            u'Click to see the list of added bookmarks',
            parent=parent
        )

    @property
    def active_label(self):
        if settings.ACTIVE[settings.RootKey]:
            return settings.ACTIVE[settings.RootKey].split(u'/')[-1]
        return self.default_label

    def contextMenuEvent(self, event):
        menu = SwitchBookmarkMenu(QtCore.QModelIndex(), parent=self)
        pos = self.mapToGlobal(event.pos())
        menu.move(pos)
        menu.exec_()


class AssetsTabButton(PaintedTextButton):
    """The button responsible for revealing the ``AssetsWidget``"""
    icon = u'assets'

    def __init__(self, parent=None):
        super(AssetsTabButton, self).__init__(
            u'Assets',
            base.AssetTab,
            u'Click to see the list of available assets',
            parent=parent
        )

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

    @property
    def active_label(self):
        return settings.ACTIVE[settings.AssetKey]

    def contextMenuEvent(self, event):
        menu = SwitchAssetMenu(QtCore.QModelIndex(), parent=self)
        pos = self.mapToGlobal(event.pos())
        menu.move(pos)
        menu.exec_()

    @QtCore.Slot()
    def adjust_size(self):
        if not self.stacked_widget():
            return
        index = self.stacked_widget().widget(base.BookmarkTab).model().sourceModel().active_index()
        self.setHidden(not index.isValid())
        super(AssetsTabButton, self).adjust_size()


class FilesTabButton(PaintedTextButton):
    """The buttons responsible for swtiching the the FilesWidget and showing
    the switch to change the data-key."""
    icon = u'files'

    def __init__(self, parent=None):
        super(FilesTabButton, self).__init__(
            u'Tasks',
            base.FileTab,
            u'Click to see or change the current task folder',
            parent=parent)

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self.clicked.connect(self.toggle_view)

    def contextMenuEvent(self, event):
        self.toggle_view()

    def view(self):
        return self.parent().taskswidget

    @QtCore.Slot()
    def adjust_size(self):
        if not self.stacked_widget():
            return

        asset = settings.ACTIVE[settings.AssetKey]
        _ = self.setHidden(False) if asset else self.setHidden(True)
        super(FilesTabButton, self).adjust_size()

    @property
    def active_label(self):
        v = settings.ACTIVE[settings.TaskKey]
        return v + u'  ▼' if v else v

    def paintEvent(self, event):
        """Indicating the visibility of the TaskFolderWidget."""
        if not self.view().isHidden():
            painter = QtGui.QPainter()
            painter.begin(self)

            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(0, 0, 0, 30))
            painter.drawRect(self.rect())

            rect = self.rect()
            rect.setHeight(common.ROW_SEPARATOR() * 2.0)
            painter.setBrush(common.ADD)
            painter.drawRect(rect)

            common.draw_aliased_text(
                painter,
                common.font_db.primary_font(common.MEDIUM_FONT_SIZE())[0],
                self.rect(),
                u'...',
                QtCore.Qt.AlignCenter,
                common.BACKGROUND
            )
            painter.end()
        else:
            super(FilesTabButton, self).paintEvent(event)

    @QtCore.Slot()
    def toggle_view(self):
        """Shows the ``TaskFolderWidget`` widget for browsing."""
        self.view().setHidden(not self.view().isHidden())


class FavouritesTabButton(PaintedTextButton):
    """Drop-down widget to switch between the list"""
    icon = u'favourite'

    def __init__(self, parent=None):
        super(FavouritesTabButton, self).__init__(
            u'My Files',
            base.FavouriteTab,
            u'Click to see your saved favourites',
            parent=parent
        )


class SlackDropOverlayWidget(QtWidgets.QWidget):
    """Widget used to receive a slack message drop."""

    def __init__(self, parent=None):
        super(SlackDropOverlayWidget, self).__init__(parent=parent)
        self.setAcceptDrops(True)
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
        painter.drawRoundedRect(
            self.rect(), common.INDICATOR_WIDTH(), common.INDICATOR_WIDTH())

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'slack', common.ADD, self.rect().height() - (common.INDICATOR_WIDTH() * 1.5))
        rect = QtCore.QRect(0, 0, common.MARGIN(), common.MARGIN())
        rect.moveCenter(self.rect().center())
        painter.drawPixmap(rect, pixmap, pixmap.rect())

        o = common.INDICATOR_WIDTH()
        rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
        painter.setBrush(QtCore.Qt.NoBrush)
        pen = QtGui.QPen(common.ADD)
        pen.setWidthF(common.ROW_SEPARATOR() * 2.0)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, o, o)
        painter.end()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Slack drop event"""
        try:
            from . import slack
        except ImportError as err:
            common_ui.ErrorBox(
                u'Could not import SlackClient',
                u'The Slack API python module was not loaded:\n{}'.format(err),
            ).open()
            log.error('Slack import error.')
            return

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
        parent = self.parent().parent().stackedwidget
        index = parent.widget(base.BookmarkTab).model().sourceModel().active_index()
        if not index.isValid():
            return

        widget = parent.currentWidget().show_slack()
        widget.message_widget.append_message(message)

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
    taskFolderChanged = QtCore.Signal(unicode)

    slackDragStarted = QtCore.Signal(QtCore.QModelIndex)
    slackDropFinished = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, parent=None):
        super(ListControlWidget, self).__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        height = common.MARGIN() + (common.INDICATOR_WIDTH() * 3)
        self.setFixedHeight(height)

        # Control view/model/button
        self.bookmarks_button = BookmarksTabButton(parent=self)
        self.assets_button = AssetsTabButton(parent=self)
        self.files_button = FilesTabButton(parent=self)
        self.favourites_button = FavouritesTabButton(parent=self)

        self.taskswidget = tasks.TaskFolderWidget(
            parent=self.parent().stackedwidget.widget(base.FileTab))
        self.taskswidget.setHidden(True)

        self.generate_thumbnails_button = GenerateThumbnailsButton(parent=self)
        self.filter_button = FilterButton(parent=self)
        self.collapse_button = ToggleSequenceButton(parent=self)
        self.archived_button = ToggleArchivedButton(parent=self)
        self.favourite_button = ToggleFavouriteButton(parent=self)
        self.slack_button = SlackButton(parent=self)
        self.slack_button.setHidden(True)
        self.simple_mode_button = SimpleModeButton(parent=self)

        self.layout().addWidget(self.bookmarks_button, 1)
        self.layout().addWidget(self.assets_button, 1)
        self.layout().addWidget(self.files_button, 1)

        self.layout().addStretch()

        self.layout().addWidget(self.simple_mode_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH())
        self.layout().addWidget(self.generate_thumbnails_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH())
        self.layout().addWidget(self.filter_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH())
        self.layout().addWidget(self.collapse_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH())
        self.layout().addWidget(self.archived_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH())
        self.layout().addWidget(self.favourite_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH())
        self.layout().addWidget(self.slack_button)

        self.layout().addWidget(self.favourites_button, 1)
        self.layout().addSpacing(common.INDICATOR_WIDTH() * 2)

        self.drop_overlay = SlackDropOverlayWidget(parent=self)
        self.drop_overlay.setHidden(True)

    def _connect_signals(self):
        actions.signals.assetAdded.connect(lambda x: self.listChanged.emit(base.AssetTab))

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

    def control_view(self):
        return self.taskswidget

    def control_button(self):
        return self.findChild(FilesTabButton)

    def paintEvent(self, event):
        """`ListControlWidget`' paint event."""
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'gradient', None, self.height())
        t = QtGui.QTransform()
        t.rotate(90)
        pixmap = pixmap.transformed(t)
        painter.setOpacity(0.8)
        painter.drawPixmap(self.rect(), pixmap, pixmap.rect())
        painter.end()
