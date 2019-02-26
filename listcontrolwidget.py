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
from browser.settings import AssetSettings
from browser.settings import Active



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

        # Text
        rect = QtCore.QRect(option.rect)
        rect.setLeft(common.INDICATOR_WIDTH + (rect.height() * 2))
        color = common.TEXT_SELECTED if hover else common.TEXT
        color = common.FAVOURITE if active else color

        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSize(10)
        text = index.data(QtCore.Qt.DisplayRole).upper()
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

        # Thumbnail
        rect = QtCore.QRect(option.rect)
        rect.setWidth(rect.height())
        rect.moveLeft(common.INDICATOR_WIDTH + rect.height())
        center = rect.center()
        rect.setWidth(rect.width() / 1.5)
        rect.setHeight(rect.height() / 1.5)
        rect.moveCenter(center)
        if active:
            color = common.FAVOURITE
        else:
            color = common.SEPARATOR
        pixmap = ImageCache.get_rsc_pixmap(
            u'files', color, rect.height())
        painter.drawPixmap(rect, pixmap, pixmap.rect())

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
                rect.setWidth(rect.width() / 1.5)
                rect.setHeight(rect.height() / 1.5)
                rect.moveCenter(center)
                pixmap = ImageCache.get_rsc_pixmap(
                    u'assets', color, rect.height())
                background = QtGui.QColor(0, 0, 0, 0)
        else:
            center = rect.center()
            rect.setWidth(rect.width() / 1.5)
            rect.setHeight(rect.height() / 1.5)
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
        font.setPointSize(10)
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
        rect.setWidth(rect.width() / 1.5)
        rect.setHeight(rect.height() / 1.5)
        rect.moveCenter(center)
        if currentmode == Mode:  # currently browsing bookmarks
            color = common.FAVOURITE
        else:
            color = common.SEPARATOR
        pixmap = ImageCache.get_rsc_pixmap(
            u'bookmark', color, rect.height())
        painter.drawPixmap(rect, pixmap, pixmap.rect())

        # Text
        rect.setLeft(rect.right()+ common.MARGIN)
        rect.setRight(option.rect.right())
        color = common.TEXT_SELECTED if hover else common.TEXT

        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSize(10)
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
        color = common.SECONDARY_BACKGROUND
        if selected:
            color = common.BACKGROUND_SELECTED
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(option.rect)

    def sizeHint(self, option, index):
        return QtCore.QSize(common.WIDTH, common.BOOKMARK_ROW_HEIGHT / 1.5)


class ListControlView(QtWidgets.QListView):
    def __init__(self, parent=None):
        super(ListControlView, self).__init__(parent=parent)


class ListControlModel(BaseModel):
    """The model responsible for storing the available modes to browse."""

    static_string_list = (
        'Bookmarks',
        'Assets',
        common.ScenesFolder,
        common.ExportsFolder,
        common.RendersFolder,
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
        for idx, item in enumerate(sorted(dir_.entryList())):
            if item in self.model_data:
                continue # skipping existing items
            self.model_data[idx + len(self.static_string_list)] = {
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


    def rowCount(self, parent=QtCore.QModelIndex()):
        """Sets the item flags based on the currently available active paths."""
        active_bookmark = self.parentwidget.parent().bookmarkswidget.active_index()
        if not active_bookmark.isValid():
            return 1

        active_asset = self.parentwidget.parent().assetswidget.active_index()
        if not active_asset.isValid():
            return 2

        active_asset.data(QtCore.Qt.StatusTipRole)

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
            None, None).height() * self.model().rowCount())

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
