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


class Progressbar(QtWidgets.QLabel):
    """Custom loading indicator."""

    def __init__(self, parent=None):
        super(Progressbar, self).__init__(parent=parent)
        self.processmonitor = QtCore.QTimer()
        self.processmonitor.setSingleShot(False)
        self.processmonitor.setInterval(80)
        self.processmonitor.timeout.connect(self.set_visibility)
        self.processmonitor.start()

        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        self.setStyleSheet("""
            QLabel {{
                font-family: "{}";
                font-size: 8pt;
                color: rgba({});
                background-color: rgba(0,0,0,0);
            	border: 0px solid;
                padding: 0px;
                margin: 0px;
            }}
        """.format(
            common.SecondaryFont.family(),
            u'{},{},{},{}'.format(*common.FAVOURITE.getRgb()))
        )

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        self.setText(u'Working...')
        common.ProgressMessage.instance().messageChanged.connect(self.setText)

    def set_visibility(self):
        """Checks if the thread pool is has running threads."""
        pool = QtCore.QThreadPool.globalInstance()
        app = QtWidgets.QApplication.instance()
        if pool.activeThreadCount():
            app.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.show()
        else:
            app.restoreOverrideCursor()
            self.hide()
            common.ProgressMessage.instance().clear_message()


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
        super(CustomButton, self).__init__(
            height=common.INLINE_ICON_SIZE, parent=parent)
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
        filewidget.model().sourceModel().set_collapsed(not grouped)

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

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(common.INDICATOR_WIDTH * 3)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT)

        # Listwidget
        self.layout().addSpacing(common.MARGIN)
        self.layout().addWidget(ListControlDropdown(parent=self))
        self.layout().addStretch()
        self.layout().addWidget(Progressbar(parent=self), 1)
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

        combobox.view.activated.connect(lambda index: self.update_controls(index.row()))
        self.modeChanged.connect(self.update_controls)

        addbookmarkbutton.clicked.connect(
            bookmarkswidget.show_add_bookmark_widget)

    @QtCore.Slot(int)
    def update_controls(self, mode):
        """Sets the current mode of ``ListControlWidget`` and updates
        all widgets accordingly."""
        if mode > 2:
            listcontrolmode = int(mode)
            local_settings.setValue(u'widget/listcontrolmode', listcontrolmode)

            self.update_controls(2)

            listcontrol = self.findChild(ListControlDropdown)
            index = listcontrol.view.model().index(listcontrolmode, 0)
            model = self.parent().fileswidget.model().sourceModel()
            model.set_location(index.data(QtCore.Qt.DisplayRole))

        mode = mode if mode >= 0 else 0
        mode = mode if mode < 2 else 2

        addbookmark = self.findChild(AddBookmarkButton)
        filterbutton = self.findChild(FilterButton)
        collapsesequence = self.findChild(CollapseSequenceButton)
        togglearchived = self.findChild(ToggleArchivedButton)
        togglefavourite = self.findChild(ToggleFavouriteButton)

        if mode == 0:  # Bookmarks
            addbookmark.setHidden(False)
            filterbutton.setHidden(False)
            collapsesequence.setHidden(True)
            togglearchived.setHidden(False)
            togglefavourite.setHidden(False)
        elif mode == 1:  # Assets
            addbookmark.setHidden(True)
            togglearchived.setHidden(True)
            filterbutton.setHidden(False)
            collapsesequence.setHidden(True)
            togglearchived.setHidden(False)
            togglefavourite.setHidden(False)
        elif mode == 2:  # Files
            addbookmark.setHidden(True)
            filterbutton.setHidden(False)
            collapsesequence.setHidden(False)
            togglearchived.setHidden(False)
            togglefavourite.setHidden(False)

        togglearchived.update_(mode)
        filterbutton.update_(mode)
        collapsesequence.update_(mode)
        togglefavourite.update_(mode)


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

        parent = self.parent().parent()  # browserwidget
        currentmode = parent.fileswidget.model().sourceModel().get_location()

        active = currentmode.lower() == index.data(QtCore.Qt.DisplayRole).lower()
        active = active if parent.findChild(
            StackedWidget).currentIndex() == 2 else False

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

        parent = self.parent().parent()  # browserwidget
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
            text = '{}'.format(active_index.data(
                QtCore.Qt.DisplayRole).upper())
        common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)

    @paintmethod
    def paint_bookmark(self, *args):
        painter, option, index, _ = args
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        Mode = 0

        if index.row() != Mode:
            return

        parent = self.parent().parent()  # browserwidget
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
        rect.setLeft(common.INDICATOR_WIDTH +
                     rect.height() + common.INDICATOR_WIDTH)
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
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.close()

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
        self.parentwidget = parent
        super(ListControlModel, self).__init__(parent=parent)
        self.__initdata__()

    def __initdata__(self):
        """Bookmarks and assets are static. But files will be any number of """
        self.model_data = {}  # resetting data
        flags = (QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        # Static folder - we're expecting these to be always present
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

        # Dynamic folders - this list might change depending on the asset
        active_asset = self.parentwidget.parent().assetswidget.active_index()
        if active_asset.isValid():
            path = active_asset.data(QtCore.Qt.StatusTipRole)
            dir_ = QtCore.QDir(path)
            dir_.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)

            idx = len(self.static_string_list)
            for item in sorted(dir_.entryList()):
                if item in (f[QtCore.Qt.DisplayRole] for f in self.model_data.itervalues()):
                    continue  # skipping existing items
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
        self.modelDataAboutToChange.emit()
        self.beginResetModel()
        self.model_data = {}
        self.endResetModel()


class ListControlDropdown(ClickableLabel):
    """Drop-down widget to switch between the list"""
    activeAssetChanged = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, parent=None):
        super(ListControlDropdown, self).__init__(parent=parent)
        self.view = ListControlView(parent=parent)
        self.view.setModel(ListControlModel(parent=parent))
        self.view.setItemDelegate(ListControlDelegate(parent=parent))

        self.activeAssetChanged.connect(self.assetChanged)
        self.clicked.connect(self.showPopup)

        self.setFixedWidth(150)

    def paintEvent(self, event):
        idx = self.parent().parent().stackedwidget.currentIndex()
        text = self.view.model().index(idx, 0).data(QtCore.Qt.DisplayRole)

        painter = QtGui.QPainter()
        painter.begin(self)
        common.draw_aliased_text(
            painter, common.PrimaryFont, self.rect(), text, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, common.TEXT)
        painter.end()

    @QtCore.Slot(QtCore.QModelIndex)
    def assetChanged(self, index):
        self.model().__resetdata__()
        self.model().__initdata__()

    def showPopup(self):
        """Showing view."""
        pos = self.parent().mapToGlobal(self.parent().rect().bottomLeft())
        self.view.move(pos)
        self.view.setFixedWidth(self.parent().rect().width())

        # Setting the height based on the conents
        height = 0
        for n in xrange(self.view.model().rowCount()):
            index = self.view.model().index(n,0, parent=QtCore.QModelIndex())
            height += self.view.visualRect(index).height()
        self.view.setFixedHeight(height)

        # Selecting the current item
        idx = self.parent().parent().stackedwidget.currentIndex()
        index = self.view.model().index(idx, 0, parent=QtCore.QModelIndex())
        self.view.selectionModel().setCurrentIndex(
            index,
            QtCore.QItemSelectionModel.ClearAndSelect
        )
        self.view.show()
