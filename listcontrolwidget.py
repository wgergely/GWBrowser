# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903, C0330

"""Widget reponsible controlling the displayed list and the filter-modes."""

import functools
from PySide2 import QtWidgets, QtGui, QtCore

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



class LocationsMenu(BaseContextMenu):
    def __init__(self, parent=None):
        super(LocationsMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_location_toggles_menu()

    @contextmenu
    def add_location_toggles_menu(self, menu_set):
        """Adds the menu needed to change context"""
        locations_icon_pixmap = ImageCache.get_rsc_pixmap(
            u'location', common.TEXT_SELECTED, common.INLINE_ICON_SIZE)
        item_on_pixmap = ImageCache.get_rsc_pixmap(
            u'item_on', common.TEXT_SELECTED, common.INLINE_ICON_SIZE)

        for k in sorted(list(common.NameFilters)):
            checked = self.parent().model().sourceModel().get_location() == k
            menu_set[k] = {
                u'text': k.title(),
                u'checkable': True,
                u'checked': checked,
                u'icon': item_on_pixmap if checked else QtGui.QPixmap(),
                u'action': functools.partial(self.parent().model().sourceModel().set_location, k)
            }
        return menu_set


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


class LocationsButton(QtWidgets.QWidget):
    """Button responsible for switching and displaying the current location of the list widget."""

    def __init__(self, parent=None):
        super(LocationsButton, self).__init__(parent=parent)
        self.icon = None
        self.text = None
        self.setToolTip('Select the asset location to browse')
        self._createUI()

        pixmap = ImageCache.get_rsc_pixmap(
            u'location', common.FAVOURITE, common.INLINE_ICON_SIZE)
        self.icon.setPixmap(pixmap)

        self.text.setText(self.location.title())

    def update_(self, *args, **kwargs):
        self.text.setText(self.location.title())

    @property
    def location(self):
        return self.parent().window().findChild(FilesWidget).model().sourceModel().get_location()

    def mousePressEvent(self, event):
        self.clicked()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(common.INDICATOR_WIDTH * 3)

        self.icon = ClickableLabel(parent=self)
        self.icon.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.icon.setFixedSize(
            common.INLINE_ICON_SIZE,
            common.INLINE_ICON_SIZE,
        )
        self.layout().addWidget(self.icon)
        self.text = QtWidgets.QLabel()
        self.text.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.layout().addWidget(self.text)

    def setPixmap(self, pixmap):
        self.label.setPixmap(pixmap)

    def clicked(self):
        parent = self.parent().parent().findChild(FilesWidget)
        menu = LocationsMenu(parent=parent)
        # left =
        bottom = self.parent().mapToGlobal(self.parent().rect().bottomLeft())
        left = self.icon.mapToGlobal(self.icon.rect().bottomLeft())
        menu.move(left.x(), bottom.y())

        right = self.parent().mapToGlobal(self.parent().rect().bottomRight())
        menu.setFixedWidth((right - left).x())

        menu.exec_()
        self.text.setText(self.location.title())


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

        idx = local_settings.value(u'widget/current_index')
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
        self.layout().addWidget(LocationsButton(parent=self))
        self.layout().addStretch(1)
        self.layout().addWidget(AddBookmarkButton(parent=self))
        self.layout().addWidget(FilterButton(parent=self))
        self.layout().addWidget(CollapseSequenceButton(parent=self))
        self.layout().addWidget(ToggleArchivedButton(parent=self))
        self.layout().addWidget(ToggleFavouriteButton(parent=self))
        self.layout().addSpacing(common.MARGIN)

    def _connectSignals(self):
        addbookmarkbutton = self.findChild(AddBookmarkButton)
        combobox = self.findChild(ListControlDropdown)
        bookmarkswidget = self.parent().findChild(BookmarksWidget)

        combobox.currentIndexChanged.connect(self.modeChanged.emit)
        self.modeChanged.connect(self.setCurrentMode)
        self.modeChanged.connect(combobox.setCurrentIndex)
        self.modeChanged.connect(combobox.apply_flags)

        addbookmarkbutton.clicked.connect(
            bookmarkswidget.show_add_bookmark_widget)

    def setCurrentMode(self, idx):
        """Sets the current mode of ``ListControlWidget``."""
        addbookmark = self.findChild(AddBookmarkButton)
        locations = self.findChild(LocationsButton)
        filterbutton = self.findChild(FilterButton)
        collapsesequence = self.findChild(CollapseSequenceButton)
        togglearchived = self.findChild(ToggleArchivedButton)
        togglefavourite = self.findChild(ToggleFavouriteButton)

        if idx == 0:  # Bookmarks
            addbookmark.setHidden(False)
            locations.setHidden(True)
            filterbutton.setHidden(False)
            collapsesequence.setHidden(True)
            togglearchived.setHidden(False)
            togglefavourite.setHidden(False)
        elif idx == 1:  # Assets
            addbookmark.setHidden(True)
            togglearchived.setHidden(True)
            locations.setHidden(True)
            filterbutton.setHidden(False)
            collapsesequence.setHidden(True)
            togglearchived.setHidden(False)
            togglefavourite.setHidden(False)
        elif idx == 2:  # Files
            addbookmark.setHidden(True)
            locations.setHidden(False)
            filterbutton.setHidden(False)
            collapsesequence.setHidden(False)
            togglearchived.setHidden(False)
            togglefavourite.setHidden(False)

        togglearchived.update_(idx)
        filterbutton.update_(idx)
        collapsesequence.update_(idx)
        togglefavourite.update_(idx)
        locations.update_(idx)


class ListControlDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super(ListControlDelegate, self).__init__(parent=parent)

    def sizeHint(self, option, index):
        return QtCore.QSize(self.parent().parent().width(), common.ROW_BUTTONS_HEIGHT)

    def paint(self, painter, option, index):
        """The main paint method."""
        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing
            | QtGui.QPainter.Antialiasing
            | QtGui.QPainter.SmoothPixmapTransform,
            on=True
        )
        selected = option.state & QtWidgets.QStyle.State_Selected
        args = (painter, option, index, selected)

        self.paint_background(*args)
        self.paint_name(*args)

    @paintmethod
    def paint_name(self, *args):
        painter, option, index, _ = args
        active = self.parent().currentIndex() == index.row()
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSize(10)

        rect = QtCore.QRect(option.rect)
        rect.setLeft(rect.left() + common.MARGIN)

        color = common.TEXT
        if hover:
            color = common.TEXT_SELECTED
        if index.flags() == QtCore.Qt.NoItemFlags:
            color = common.TEXT_DISABLED
        if active:
            color = common.TEXT

        text = index.data(QtCore.Qt.DisplayRole)
        common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)

    @paintmethod
    def paint_background(self, *args):
        """Paints the background."""
        painter, option, index, selected = args
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        color = common.BACKGROUND
        if selected:
            color = common.BACKGROUND_SELECTED
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(option.rect)

    @paintmethod
    def paint_thumbnail(self, *args):
        """Paints the thumbnail of the item."""
        painter, option, index, selected = args
        active = self.parent().currentIndex() == index.row()
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        rect = QtCore.QRect(option.rect)
        rect.setWidth(rect.height())

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        color = common.TEXT
        if active:
            color = common.FAVOURITE
        if index.flags() == QtCore.Qt.NoItemFlags:
            color = common.TEXT_DISABLED

        if index.row() == 0:
            pixmap = ImageCache.get_rsc_pixmap(
                u'bookmark', color, rect.height())
        if index.row() == 1:
            pixmap = ImageCache.get_rsc_pixmap(
                u'package', color, rect.height())
        if index.row() == 2:
            pixmap = ImageCache.get_rsc_pixmap(u'file', color, rect.height())

        painter.drawPixmap(
            rect,
            pixmap,
            pixmap.rect()
        )

    def sizeHint(self, option, index):
        return QtCore.QSize(common.WIDTH, common.BOOKMARK_ROW_HEIGHT)

class ListControlView(QtWidgets.QListView):
    def __init__(self, parent=None):
        super(ListControlView, self).__init__(parent=parent)


class ListControlModel(BaseModel):

    static_string_list = ('Bookmarks', 'Assets', 'Files')

    def __init__(self, parent=None):
        super(ListControlModel, self).__init__(parent=parent)

    def __initdata__(self):
        self.model_data = {} # resetting data
        flags = (
            QtCore.Qt.ItemIsSelectable |
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsEditable
        )
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

    def __resetdata__(self):
        """Resets the internal data."""
        # Resetting the file-monitor
        self.modelDataAboutToChange.emit()
        self.beginResetModel()
        self.model_data = {}
        self.endResetModel()

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 1

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 3



class ListControlDropdown(QtWidgets.QComboBox):
    """Drop-down widget to switch between the list"""

    def __init__(self, parent=None):
        super(ListControlDropdown, self).__init__(parent=parent)
        self.currentTextChanged.connect(self._adjustSize)

        self.setView(ListControlView(parent=self.parent()))
        self.setModel(ListControlModel(parent=self.parent())) # parent = ListControlWidget
        self.setItemDelegate(ListControlDelegate(parent=self.view()))

        idx = local_settings.value(u'widget/current_index')
        idx = idx if idx else 0
        self.setCurrentIndex(idx)
        # self.apply_flags()

    def _adjustSize(self, text):
        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSize(11)
        metrics = QtGui.QFontMetrics(font)
        width = metrics.width(text)
        self.setFixedWidth(width)

    def apply_flags(self):
        """Sets the item flags based on the set active paths."""
        return
        # active_paths = Active.get_active_paths()
        # flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        # bookmark = (active_paths[u'server'],
        #             active_paths[u'job'], active_paths[u'root'])
        # for n in xrange(self.model().rowCount()):
        #     item = self.model().item(n)
        #     if n == 1 and not all(bookmark):
        #         item.setFlags(QtCore.Qt.NoItemFlags)
        #         continue
        #     if n == 2 and not active_paths[u'asset']:
        #         item.setFlags(QtCore.Qt.NoItemFlags)
        #         continue
        #     item.setFlags(flags)

    def showPopup(self):
        """Toggling overlay widget when combobox is shown."""
        popup = self.findChild(QtWidgets.QFrame)

        pos = self.parent().mapToGlobal(self.parent().rect().bottomLeft())
        popup.move(pos)
        popup.setFixedWidth(self.parent().rect().width())
        popup.setFixedHeight(self.itemDelegate().sizeHint(
            None, None).height() * self.model().rowCount())
        # Selecting the current item
        index = self.view().model().index(self.currentIndex(), 0)
        self.view().selectionModel().setCurrentIndex(
            index,
            QtCore.QItemSelectionModel.ClearAndSelect
        )
        popup.show()

    def hidePopup(self):
        """Toggling overlay widget when combobox is shown."""
        super(ListControlDropdown, self).hidePopup()
