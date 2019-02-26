# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903, C0330

"""Widget reponsible controlling the displayed list and the filter-modes."""

import functools
from PySide2 import QtWidgets, QtGui, QtCore

from browser.settings import Active
import browser.common as common
from browser.delegate import paintmethod
from browser.baselistwidget import BaseContextMenu
from browser.baselistwidget import contextmenu
from browser.baselistwidget import StackedWidget
from browser.baselistwidget import BaseModel
from browser.bookmarkswidget import BookmarksWidget
from browser.fileswidget import FilesWidget
from browser.editors import FilterEditor
from browser.editors import ClickableLabel
from browser.imagecache import ImageCache
from browser.settings import local_settings
from browser.settings import AssetSettings



class BrowserButtonContextMenu(BaseContextMenu):
    """The context-menu associated with the BrowserButton."""

    def __init__(self, parent=None):
        super(BrowserButtonContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_show_menu()
        self.add_toolbar_menu()

    @contextmenu
    def add_show_menu(self, menu_set):
        if not hasattr(self.parent(), 'clicked'):
            return menu_set
        menu_set[u'show'] = {
            u'icon': ImageCache.get_rsc_pixmap(u'custom', None, common.INLINE_ICON_SIZE),
            u'text': u'Open...',
            u'action': self.parent().clicked.emit
        }
        return menu_set

    @contextmenu
    def add_toolbar_menu(self, menu_set):
        active_paths = Active.get_active_paths()
        bookmark = (active_paths[u'server'],
                    active_paths[u'job'], active_paths[u'root'])
        asset = bookmark + (active_paths[u'asset'],)
        location = asset + (active_paths[u'location'],)

        if all(bookmark):
            menu_set[u'bookmark'] = {
                u'icon': ImageCache.get_rsc_pixmap('bookmark', common.TEXT, common.INLINE_ICON_SIZE),
                u'disabled': not all(bookmark),
                u'text': u'Show active bookmark in the file manager...',
                u'action': functools.partial(common.reveal, u'/'.join(bookmark))
            }
            if all(asset):
                menu_set[u'asset'] = {
                    u'icon': ImageCache.get_rsc_pixmap(u'assets', common.TEXT, common.INLINE_ICON_SIZE),
                    u'disabled': not all(asset),
                    u'text': u'Show active asset in the file manager...',
                    u'action': functools.partial(common.reveal, '/'.join(asset))
                }
                if all(location):
                    menu_set[u'location'] = {
                        u'icon': ImageCache.get_rsc_pixmap(u'location', common.TEXT, common.INLINE_ICON_SIZE),
                        u'disabled': not all(location),
                        u'text': u'Show active location in the file manager...',
                        u'action': functools.partial(common.reveal, '/'.join(location))
                    }

        return menu_set


class BrowserButton(ClickableLabel):
    """Small widget to embed into the context to toggle the BrowserWidget's visibility."""

    def __init__(self, height=common.ROW_HEIGHT, parent=None):
        super(BrowserButton, self).__init__(parent=parent)
        self.context_menu_cls = BrowserButtonContextMenu
        self.setFixedWidth(height)
        self.setFixedHeight(height)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setWindowFlags(
            QtCore.Qt.Widget |
            QtCore.Qt.FramelessWindowHint
        )
        pixmap = ImageCache.get_rsc_pixmap(
            u'custom', None, height)
        self.setPixmap(pixmap)

    def set_size(self, size):
        self.setFixedWidth(int(size))
        self.setFixedHeight(int(size))
        pixmap = ImageCache.get_rsc_pixmap(
            u'custom', None, int(size))
        self.setPixmap(pixmap)

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.initFrom(self)

        painter = QtGui.QPainter()
        painter.begin(self)
        brush = self.pixmap().toImage()

        painter.setBrush(brush)
        painter.setPen(QtCore.Qt.NoPen)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        painter.setOpacity(0.8)
        if option.state & QtWidgets.QStyle.State_MouseOver:
            painter.setOpacity(1)

        painter.drawRoundedRect(self.rect(), 2, 2)
        painter.end()

    def contextMenuEvent(self, event):
        """Context menu event."""
        # Custom context menu
        shift_modifier = event.modifiers() & QtCore.Qt.ShiftModifier
        alt_modifier = event.modifiers() & QtCore.Qt.AltModifier
        control_modifier = event.modifiers() & QtCore.Qt.ControlModifier
        if shift_modifier or alt_modifier or control_modifier:
            self.customContextMenuRequested.emit()
            return

        widget = self.context_menu_cls(parent=self)
        widget.move(self.mapToGlobal(self.rect().bottomLeft()))
        widget.setFixedWidth(300)
        common.move_widget_to_available_geo(widget)
        widget.exec_()


class CustomButton(BrowserButton):
    def __init__(self, parent=None):
        self.context_menu_cls = BrowserButtonContextMenu
        super(CustomButton, self).__init__(height=common.INLINE_ICON_SIZE, parent=parent)
        self.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(r'https://gwbcn.slack.com/'))

class FilterButton(ClickableLabel):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(FilterButton, self).__init__(parent=parent)
        self.setFixedSize(
            common.INLINE_ICON_SIZE,
            common.INLINE_ICON_SIZE,
        )
        self.clicked.connect(self.action)

    def action(self):
        widget = self.parent().parent().findChild(StackedWidget)
        filterstring = widget.currentWidget().model().get_filterstring()
        editor = FilterEditor(filterstring, parent=widget)
        editor.finished.connect(
            widget.currentWidget().model().set_filterstring)
        editor.finished.connect(lambda: self.update_(widget.currentIndex()))
        editor.editor.textEdited.connect(
            widget.currentWidget().model().invalidate)
        editor.editor.textEdited.connect(
            widget.currentWidget().model().set_filterstring)
        editor.editor.textEdited.connect(
            lambda s: self.update_(widget.currentIndex()))

        pos = self.rect().center()
        pos = self.mapToGlobal(pos)
        editor.move(
            pos.x() - editor.width() + (self.width() / 2.0),
            pos.y() - (editor.height() / 2.0)
        )
        editor.show()

    def update_(self, idx):
        stackwidget = self.parent().parent().findChild(StackedWidget)
        if stackwidget.widget(idx).model().get_filterstring() != u'/':
            pixmap = ImageCache.get_rsc_pixmap(
                u'filter', common.FAVOURITE, common.INLINE_ICON_SIZE)
        else:
            pixmap = ImageCache.get_rsc_pixmap(
                u'filter', common.TEXT, common.INLINE_ICON_SIZE)
        self.setPixmap(pixmap)



class CollapseSequenceButton(ClickableLabel):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(CollapseSequenceButton, self).__init__(parent=parent)
        self.setFixedSize(
            common.INLINE_ICON_SIZE,
            common.INLINE_ICON_SIZE,
        )
        self.clicked.connect(self.toggle)
        stackwidget = self.parent().parent().findChild(StackedWidget)
        self.clicked.connect(lambda: self.update_(stackwidget.currentIndex()))

    def toggle(self):
        filewidget = self.parent().parent().findChild(FilesWidget)
        grouped = filewidget.model().sourceModel().is_grouped()
        filewidget.model().sourceModel().set_grouped(not grouped)

    def update_(self, idx):
        stackwidget = self.parent().parent().findChild(StackedWidget)
        if stackwidget.widget(idx).model().sourceModel().is_grouped():
            pixmap = ImageCache.get_rsc_pixmap(
                u'collapse', common.FAVOURITE, common.INLINE_ICON_SIZE)
        else:
            pixmap = ImageCache.get_rsc_pixmap(
                u'expand', common.TEXT, common.INLINE_ICON_SIZE)
        self.setPixmap(pixmap)


class ToggleArchivedButton(ClickableLabel):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(ToggleArchivedButton, self).__init__(parent=parent)
        self.setFixedSize(
            common.INLINE_ICON_SIZE,
            common.INLINE_ICON_SIZE,
        )
        self.clicked.connect(self.toggle)
        stackwidget = self.parent().parent().findChild(StackedWidget)
        self.clicked.connect(lambda: self.update_(stackwidget.currentIndex()))

    def toggle(self):
        widget = self.parent().parent().findChild(StackedWidget)
        archived = widget.currentWidget().model().get_filtermode(u'archived')
        widget.currentWidget().model().set_filtermode(u'archived', not archived)

    def update_(self, idx):
        stackwidget = self.parent().parent().findChild(StackedWidget)
        if stackwidget.widget(idx).model().get_filtermode(u'archived'):
            pixmap = ImageCache.get_rsc_pixmap(
                u'active', common.TEXT, common.INLINE_ICON_SIZE)
        else:
            pixmap = ImageCache.get_rsc_pixmap(
                u'archived', common.FAVOURITE, common.INLINE_ICON_SIZE)
        self.setPixmap(pixmap)


class ToggleFavouriteButton(ClickableLabel):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(ToggleFavouriteButton, self).__init__(parent=parent)
        self.setFixedSize(
            common.INLINE_ICON_SIZE,
            common.INLINE_ICON_SIZE,
        )
        self.clicked.connect(self.toggle)
        stackwidget = self.parent().parent().findChild(StackedWidget)
        self.clicked.connect(lambda: self.update_(stackwidget.currentIndex()))

    def toggle(self):
        widget = self.parent().parent().findChild(StackedWidget)
        favourite = widget.currentWidget().model().get_filtermode(u'favourite')
        widget.currentWidget().model().set_filtermode(u'favourite', not favourite)

    def update_(self, idx):
        stackwidget = self.parent().parent().findChild(StackedWidget)
        if stackwidget.widget(idx).model().get_filtermode(u'favourite'):
            pixmap = ImageCache.get_rsc_pixmap(
                u'favourite', common.FAVOURITE, common.INLINE_ICON_SIZE)
        else:
            pixmap = ImageCache.get_rsc_pixmap(
                u'favourite', common.TEXT, common.INLINE_ICON_SIZE)
        self.setPixmap(pixmap)


class CollapseSequenceMenu(BaseContextMenu):
    def __init__(self, parent=None):
        super(CollapseSequenceMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_collapse_sequence_menu()


class AddBookmarkButton(ClickableLabel):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(AddBookmarkButton, self).__init__(parent=parent)
        pixmap = ImageCache.get_rsc_pixmap(
            u'todo_add', common.TEXT, common.INLINE_ICON_SIZE)
        self.setPixmap(pixmap)
        self.setFixedSize(
            common.INLINE_ICON_SIZE,
            common.INLINE_ICON_SIZE,
        )


class ListControlWidget(QtWidgets.QWidget):
    """The bar above the list to control the mode, filters and sorting."""

    modeChanged = QtCore.Signal(int)
    """Mode changed is the main signal emited when the listwidget in view changes."""

    def __init__(self, parent=None):
        super(ListControlWidget, self).__init__(parent=parent)
        self._createUI()
        self._connectSignals()

        idx = local_settings.value(u'widget/mode')
        idx = idx if idx else 0
        self.modeChanged.emit(idx)

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(common.INDICATOR_WIDTH * 3)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT)

        # Listwidget
        self.layout().addSpacing(common.MARGIN)
        self.layout().addWidget(ListControlDropdown(parent=self))
        self.layout().addStretch(1)
        self.layout().addWidget(AddBookmarkButton(parent=self))
        self.layout().addWidget(CustomButton(parent=self))
        self.layout().addWidget(FilterButton(parent=self))
        self.layout().addWidget(CollapseSequenceButton(parent=self))
        self.layout().addWidget(ToggleArchivedButton(parent=self))
        self.layout().addWidget(ToggleFavouriteButton(parent=self))
        self.layout().addSpacing(common.MARGIN)

    def _connectSignals(self):
        addbookmarkbutton = self.findChild(AddBookmarkButton)
        combobox = self.findChild(ListControlDropdown)
        bookmarkswidget = self.parent().findChild(BookmarksWidget)

        combobox.currentIndexChanged.connect(self.currentIndexChanged)
        self.modeChanged.connect(self.setCurrentMode)

        addbookmarkbutton.clicked.connect(
            bookmarkswidget.show_add_bookmark_widget)

    def currentIndexChanged(self, idx):
        local_settings.setValue(u'widget/listcontrolmode', idx)
        if idx < 2:
            self.modeChanged.emit(idx)
            local_settings.setValue(u'widget/mode', idx)
        elif idx >= 2: # Locations
            self.modeChanged.emit(2)
            local_settings.setValue(u'widget/mode', 2)

            combobox = self.findChild(ListControlDropdown)
            index = combobox.model().index(idx, 0, parent=QtCore.QModelIndex())
            self.parent().fileswidget.model().sourceModel().set_location(index.data(QtCore.Qt.DisplayRole))

    def setCurrentMode(self, idx):
        """Sets the current mode of ``ListControlWidget``."""
        idx = idx if idx < 2 else 2

        addbookmark = self.findChild(AddBookmarkButton)
        filterbutton = self.findChild(FilterButton)
        collapsesequence = self.findChild(CollapseSequenceButton)
        togglearchived = self.findChild(ToggleArchivedButton)
        togglefavourite = self.findChild(ToggleFavouriteButton)

        if idx == 0:  # Bookmarks
            addbookmark.setHidden(False)
            filterbutton.setHidden(False)
            collapsesequence.setHidden(True)
            togglearchived.setHidden(False)
            togglefavourite.setHidden(False)
        elif idx == 1:  # Assets
            addbookmark.setHidden(True)
            togglearchived.setHidden(True)
            filterbutton.setHidden(False)
            collapsesequence.setHidden(True)
            togglearchived.setHidden(False)
            togglefavourite.setHidden(False)
        elif idx == 2:  # Files
            addbookmark.setHidden(True)
            filterbutton.setHidden(False)
            collapsesequence.setHidden(False)
            togglearchived.setHidden(False)
            togglefavourite.setHidden(False)

        togglearchived.update_(idx)
        filterbutton.update_(idx)
        collapsesequence.update_(idx)
        togglefavourite.update_(idx)


class ListControlDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super(ListControlDelegate, self).__init__(parent=parent)

    def sizeHint(self, option, index):
        return QtCore.QSize(self.parent().parent().width(), common.ROW_BUTTONS_HEIGHT)

    def paint(self, painter, option, index):
        """The main paint method."""
        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=True
        )
        selected = option.state & QtWidgets.QStyle.State_Selected
        args = (painter, option, index, selected)

        self.paint_background(*args)
        self.paint_bookmark(*args)
        self.paint_asset(*args)
        self.paint_location(*args)

    @paintmethod
    def paint_location(self, *args):
        painter, option, index, _ = args
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        if index.row() < 2:
            return

        parent = self.parent().parent().parent().parent().parent()  # browserwidget
        currentmode = parent.fileswidget.model().sourceModel().get_location()

        active = currentmode.lower() == index.data(QtCore.Qt.DisplayRole).lower()
        active = active if parent.findChild(StackedWidget).currentIndex() == 2 else False

        # Text
        rect = QtCore.QRect(option.rect)
        rect.setLeft(common.INDICATOR_WIDTH + common.MARGIN)
        color = common.TEXT if index.row() <= 5 else common.SECONDARY_TEXT
        color = common.TEXT_SELECTED if hover else color
        color = common.FAVOURITE if active else color

        font = QtGui.QFont(common.PrimaryFont)
        text = index.data(QtCore.Qt.DisplayRole).upper()
        if index.row() > 5:
            font.setItalic(True)
            font.setPointSize(9)
        common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)

        # Indicator
        painter.setPen(QtCore.Qt.NoPen)
        rect = QtCore.QRect(option.rect)
        rect.setWidth(common.INDICATOR_WIDTH)
        if active:
            painter.setBrush(common.FAVOURITE)
        else:
            painter.setBrush(common.SEPARATOR)
        painter.drawRect(rect)

    @paintmethod
    def paint_asset(self, *args):
        painter, option, index, _ = args
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        Mode = 1

        if index.row() != Mode:
            return

        parent = self.parent().parent().parent().parent().parent()  # browserwidget
        currentmode = parent.findChild(StackedWidget).currentIndex()
        active_index = parent.findChild(
            StackedWidget).widget(Mode).active_index()
        active = active_index.isValid()

        # Thumbnail
        rect = QtCore.QRect(option.rect)
        rect.setWidth(rect.height())
        rect.moveLeft(common.INDICATOR_WIDTH)
        if currentmode == Mode:  # currently browsing bookmarks
            color = common.FAVOURITE
        else:
            color = common.SEPARATOR
        painter.setPen(QtCore.Qt.NoPen)
        if active:
            settings = AssetSettings(active_index)
            if QtCore.QFileInfo(settings.thumbnail_path()).exists():
                image = ImageCache.instance().get(settings.thumbnail_path(), rect.height())

                # Resizing the rectangle to accommodate the image's aspect ration
                longer = float(
                    max(image.rect().width(), image.rect().height()))
                factor = float(rect.width() / float(longer))
                center = rect.center()
                if image.rect().width() < image.rect().height():
                    rect.setWidth(int(image.rect().width() * factor) - 2)
                else:
                    rect.setHeight(int(image.rect().height() * factor) - 2)
                rect.moveCenter(center)

                pixmap = QtGui.QPixmap()
                pixmap.convertFromImage(image)
                background = ImageCache.get_color_average(image)

                bgrect = QtCore.QRect(option.rect)
                bgrect.setWidth(bgrect.height())
                bgrect.moveLeft(common.INDICATOR_WIDTH)
                painter.setBrush(background)
                painter.drawRect(bgrect)
            else:
                center = rect.center()
                rect.setWidth(rect.width() / 2)
                rect.setHeight(rect.height() / 2)
                rect.moveCenter(center)
                pixmap = ImageCache.get_rsc_pixmap(
                    u'assets', color, rect.height())
                background = QtGui.QColor(0, 0, 0, 0)
        else:
            center = rect.center()
            rect.setWidth(rect.width() / 2)
            rect.setHeight(rect.height() / 2)
            rect.moveCenter(center)
            pixmap = ImageCache.get_rsc_pixmap(
                u'assets', color, rect.height())
            background = QtGui.QColor(0, 0, 0, 0)
        painter.drawPixmap(rect, pixmap, pixmap.rect())

        # Indicator
        painter.setPen(QtCore.Qt.NoPen)
        rect = QtCore.QRect(option.rect)
        rect.setWidth(common.INDICATOR_WIDTH)
        if currentmode == Mode:  # currently browsing bookmarks
            painter.setBrush(common.FAVOURITE)
        else:
            painter.setBrush(common.SEPARATOR)
        painter.drawRect(rect)

        # Text
        rect = QtCore.QRect(option.rect)
        rect.setLeft(common.INDICATOR_WIDTH + rect.height() + common.MARGIN)
        color = common.TEXT_SELECTED if hover else common.TEXT

        font = QtGui.QFont(common.PrimaryFont)
        text = index.data(QtCore.Qt.DisplayRole)
        if active:
            text = '{}'.format(active_index.data(QtCore.Qt.DisplayRole).upper())
        common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)

    @paintmethod
    def paint_bookmark(self, *args):
        painter, option, index, _ = args
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        Mode = 0

        if index.row() != Mode:
            return

        parent = self.parent().parent().parent().parent().parent()  # browserwidget
        currentmode = parent.findChild(StackedWidget).currentIndex()
        active_index = parent.findChild(
            StackedWidget).widget(Mode).active_index()
        active = active_index.isValid()


        # Indicator
        painter.setPen(QtCore.Qt.NoPen)
        rect = QtCore.QRect(option.rect)
        rect.setWidth(common.INDICATOR_WIDTH)
        if currentmode == Mode:  # currently browsing bookmarks
            painter.setBrush(common.FAVOURITE)
        else:
            painter.setBrush(common.SEPARATOR)
        painter.drawRect(rect)

        # Thumbnail
        rect = QtCore.QRect(option.rect)
        rect.setWidth(rect.height())
        rect.moveLeft(common.INDICATOR_WIDTH)
        center = rect.center()
        rect.setWidth(rect.width() / 2)
        rect.setHeight(rect.height() / 2)
        rect.moveCenter(center)
        if currentmode == Mode:  # currently browsing bookmarks
            color = common.FAVOURITE
        else:
            color = common.SEPARATOR
        pixmap = ImageCache.get_rsc_pixmap(
            u'bookmark', color, rect.height())
        painter.drawPixmap(rect, pixmap, pixmap.rect())

        # Text
        rect = QtCore.QRect(option.rect)
        rect.setLeft(common.INDICATOR_WIDTH + rect.height() + common.INDICATOR_WIDTH)
        color = common.TEXT_SELECTED if hover else common.TEXT

        font = QtGui.QFont(common.PrimaryFont)
        text = index.data(QtCore.Qt.DisplayRole)
        text = '{} - {}'.format(
            active_index.data(QtCore.Qt.DisplayRole).upper(),
            ''.join(active_index.data(common.ParentRole)
                    [-1].split('/')[-1]).upper(),
        ) if active else text

        common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)

    @paintmethod
    def paint_background(self, *args):
        """Paints the background."""
        painter, option, index, selected = args
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        rect = QtCore.QRect(option.rect)
        color = common.SEPARATOR
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(rect)

        if index.row() < 2:
            rect.setHeight(rect.height() - 2)

        if index.row() >= 2:
            color = common.SECONDARY_BACKGROUND
        else:
            color = common.BACKGROUND
        if selected:
            color = common.BACKGROUND_SELECTED
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(rect)

    def sizeHint(self, option, index):
        if not index:
            return QtCore.QSize(common.WIDTH, common.BOOKMARK_ROW_HEIGHT / 2)

        if index.row() < 2:
            return QtCore.QSize(common.WIDTH, common.BOOKMARK_ROW_HEIGHT)
        else:
            return QtCore.QSize(common.WIDTH, common.BOOKMARK_ROW_HEIGHT / 2)


class ListControlView(QtWidgets.QListView):
    def __init__(self, parent=None):
        super(ListControlView, self).__init__(parent=parent)


class ListControlModel(BaseModel):
    """The model responsible for storing the available modes to browse."""

    static_string_list = (
        'Bookmarks',
        'Assets',
        common.ExportsFolder,
        common.RendersFolder,
        common.ScenesFolder,
        common.TexturesFolder,
    )
    """These are the static folders that will always be present."""

    def __init__(self, parent=None):
        super(ListControlModel, self).__init__(parent=parent)
        self.parentwidget = parent

        active_asset = self.parentwidget.parent().assetswidget.active_index()
        if active_asset.isValid():
            self.activeAssetChanged(active_asset.data(common.ParentRole))

    def __initdata__(self):
        """Bookmarks and assets are static. But files will be any number of """
        self.model_data = {}  # resetting data
        flags = (QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        for idx, item in enumerate(self.static_string_list):
            self.model_data[idx] = {
                QtCore.Qt.DisplayRole: item,
                QtCore.Qt.EditRole: item,
                QtCore.Qt.StatusTipRole: item,
                QtCore.Qt.ToolTipRole: item,
                QtCore.Qt.SizeHintRole: QtCore.QSize(common.WIDTH, common.BOOKMARK_ROW_HEIGHT),
                common.FlagsRole: flags,
                common.ParentRole: None,
                common.DescriptionRole: item,
                common.TodoCountRole: 0,
                common.FileDetailsRole: None,
            }

    def activeAssetChanged(self, asset):
        # Remove dynamic folders:
        for idx, k in enumerate(self.model_data.keys()):
            if idx <= 5:
                continue
            del self.model_data[k]

        path = u'/'.join(asset)
        dir_ = QtCore.QDir(path)
        if not dir_.exists():
            return
        dir_.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)

        flags = (QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        idx = len(self.static_string_list)
        for item in sorted(dir_.entryList()):
            if item in (f[QtCore.Qt.DisplayRole] for f in self.model_data.itervalues()):
                continue # skipping existing items
            self.model_data[idx] = {
                QtCore.Qt.DisplayRole: item,
                QtCore.Qt.EditRole: item,
                QtCore.Qt.StatusTipRole: item,
                QtCore.Qt.ToolTipRole: item,
                QtCore.Qt.SizeHintRole: QtCore.QSize(common.WIDTH, common.BOOKMARK_ROW_HEIGHT),
                common.FlagsRole: flags,
                common.ParentRole: None,
                common.DescriptionRole: item,
                common.TodoCountRole: 0,
                common.FileDetailsRole: None,
            }
            idx += 1

    def rowCount(self, parent=QtCore.QModelIndex()):
        """Sets the item flags based on the currently available active paths."""
        active_bookmark = self.parentwidget.parent().bookmarkswidget.active_index()
        if not active_bookmark.isValid():
            return 1

        active_asset = self.parentwidget.parent().assetswidget.active_index()
        if not active_asset.isValid():
            return 2

        return len(self.model_data)


    def __resetdata__(self):
        """Resets the internal data."""
        # Resetting the file-monitor
        self.modelDataAboutToChange.emit()
        self.beginResetModel()
        self.model_data = {}
        self.endResetModel()



class ListControlDropdown(QtWidgets.QComboBox):
    """Drop-down widget to switch between the list"""

    def __init__(self, parent=None):
        super(ListControlDropdown, self).__init__(parent=parent)
        self.currentTextChanged.connect(self._adjustSize)

        self.setView(ListControlView(parent=self.parent()))
        # parent = ListControlWidget
        self.setModel(ListControlModel(parent=self.parent()))
        self.setItemDelegate(ListControlDelegate(parent=self.view()))

        idx = local_settings.value(u'widget/listcontrolmode')
        idx = idx if idx else 0
        self.setCurrentIndex(idx)

    def _adjustSize(self, text):
        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSize(11)
        metrics = QtGui.QFontMetrics(font)
        width = metrics.width(text)
        self.setFixedWidth(width)

    def showPopup(self):
        """Toggling overlay widget when combobox is shown."""
        popup = self.findChild(QtWidgets.QFrame)

        pos = self.parent().mapToGlobal(self.parent().rect().bottomLeft())
        popup.move(pos)
        popup.setFixedWidth(self.parent().rect().width())
        popup.setFixedHeight(self.itemDelegate().sizeHint(
            None, None).height() * (self.model().rowCount() + 2))

        # Selecting the current item
        index = self.view().model().index(self.currentIndex(), 0, parent=QtCore.QModelIndex())
        self.view().selectionModel().setCurrentIndex(
            index,
            QtCore.QItemSelectionModel.ClearAndSelect
        )
        popup.show()

    def hidePopup(self):
        """Toggling overlay widget when combobox is shown."""
        super(ListControlDropdown, self).hidePopup()
