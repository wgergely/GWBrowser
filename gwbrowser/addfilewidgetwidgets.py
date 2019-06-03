# -*- coding: utf-8 -*-
"""This modules contains all the elements needed to select a folder from inside
the active location.

"""

import re
import functools

from PySide2 import QtCore, QtWidgets, QtGui

import gwbrowser.common as common
from gwbrowser.editors import ClickableLabel
from gwbrowser.delegate import BaseDelegate
from gwbrowser.delegate import paintmethod
from gwbrowser.basecontextmenu import BaseContextMenu, contextmenu
from gwbrowser.delegate import AssetsWidgetDelegate
from gwbrowser.delegate import BookmarksWidgetDelegate
from gwbrowser.baselistwidget import BaseInlineIconWidget


class SelectFolderContextMenu(BaseContextMenu):
    """Context menu associated with the thumbnail."""

    def __init__(self, parent=None):
        super(SelectFolderContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_reveal_item_menu()

    @contextmenu
    def add_reveal_item_menu(self, menu_set):
        """Menu for thumbnail operations."""
        asset = self.parent().view().model().asset()
        if asset.isValid():
            asset_path = asset.data(common.ParentRole)
            asset_path = '/'.join(asset_path)
            menu_set[u'Reveal asset'] = {
                u'action': functools.partial(common.reveal, asset_path)
            }
            destination = self.parent().view().model().destination()
            if destination:
                menu_set[u'Reveal destination'] = {
                    u'action': functools.partial(common.reveal, destination)
                }
        return menu_set


class SelectFolderDelegate(BaseDelegate):
    """Delegate responsible for painting the FolderWidget items."""

    def __init__(self, parent=None):
        super(SelectFolderDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        """Defines how the BookmarksWidgetItems should be painted."""
        args = self._get_paint_args(painter, option, index)
        self.paint_background(*args)
        self.paint_name(*args)

    @paintmethod
    def paint_name(self, *args):
        """Paints the item names inside the ``FoldersWidget``."""
        painter, option, index, _, _, _, _, _, _ = args

        rect = QtCore.QRect(option.rect)
        root = self.parent().model().parent(index) == self.parent().rootIndex()
        active = self.parent().model().destination(
        ) == self.parent().model().filePath(index)

        if root:
            color = self.get_state_color(option, index, common.TEXT)
        else:
            color = self.get_state_color(option, index, common.SECONDARY_TEXT)
        rect.setLeft(rect.left() + common.MARGIN)
        rect.setRight(rect.right() - common.MARGIN)

        # Resizing the height and centering
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(common.INLINE_ICON_SIZE)
        rect.moveTop(rect.top() - (rect.height() / 2.0))

        font = QtGui.QFont(common.PrimaryFont)
        metrics = QtGui.QFontMetrics(font)

        text = index.data(QtCore.Qt.DisplayRole)
        if index.flags() == QtCore.Qt.NoItemFlags:
            painter.setBrush(common.TEXT)
            painter.setPen(QtCore.Qt.NoPen)
            common.draw_aliased_text(
                painter, common.PrimaryFont, rect, text, QtCore.Qt.AlignCenter, common.TEXT)
            return

        # Asset name
        text = re.sub(r'[^0-9a-zA-Z]+', ' ', text)
        text = re.sub(r'[_]{1,}', '_', text).strip('_')
        if active:
            text = ' >  {}  < '.format(text).upper()
        else:
            text = ' {} '.format(text).upper()
            # text = '{}'.format(text)
        rect.setWidth(metrics.width(text))

        if root:
            painter.setBrush(common.FAVOURITE)
            pen = QtGui.QPen(common.FAVOURITE)
        else:
            painter.setBrush(common.SECONDARY_BACKGROUND)
            pen = QtGui.QPen(common.SECONDARY_BACKGROUND)

            pen.setWidth(common.INDICATOR_WIDTH)
        if self.parent().model().destination() == self.parent().model().filePath(index):
            color = QtGui.QColor(30, 200, 120)
            painter.setBrush(color)
            pen.setColor(color)
            color = common.TEXT_SELECTED
        painter.setPen(pen)

        painter.drawRoundedRect(rect, 2, 2)
        common.draw_aliased_text(
            painter, common.PrimaryFont, rect, text, QtCore.Qt.AlignCenter, color)

    @paintmethod
    def paint_background(self, *args):
        """Paints the background."""
        painter, option, index, _, _, _, _, _, _ = args
        if index.flags() == QtCore.Qt.NoItemFlags:
            return
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        color = QtGui.QColor(common.BACKGROUND)
        if hover:
            color = QtGui.QColor(common.BACKGROUND_SELECTED)

        rect = QtCore.QRect(option.rect)
        root = self.parent().model().parent(index) == self.parent().rootIndex()
        if root:
            rect.setTop(rect.top() + 2)
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(rect)

    def sizeHint(self, index, parent=QtCore.QModelIndex()):
        return QtCore.QSize(common.WIDTH, common.ROW_BUTTONS_HEIGHT)


class SelectFolderView(QtWidgets.QTreeView):
    """Simple tree view for browsing the available folders."""
    widgetShown = QtCore.Signal()

    def __init__(self, parent=None):
        super(SelectFolderView, self).__init__(parent=parent)
        self.setHeaderHidden(True)
        self.setItemDelegate(SelectFolderDelegate(parent=self))
        self.setIndentation(common.MARGIN / 2)
        self.setRootIsDecorated(False)
        common.set_custom_stylesheet(self)

        self.clicked.connect(lambda i: self.collapse(
            i) if self.isExpanded(i) else self.expand(i), type=QtCore.Qt.QueuedConnection)
        self.clicked.connect(self.index_expanded,
                             type=QtCore.Qt.QueuedConnection)
        self.activated.connect(self.hide)

    def set_model(self, model):
        self.setModel(model)
        self.model().directoryLoaded.connect(self.index_expanded)
        root_index = self.model().index(self.model().rootPath())
        self.setRootIndex(root_index)
        self.activated.connect(self.model().destinationChanged)

    def index_expanded(self, index):
        self.adjust_height()

    def showEvent(self, event):
        self.widgetShown.emit()
        self.adjust_height()

        if self.model().destination():
            self.collapseAll()
            index = self.model().index(self.model().destination())
            self.selectionModel().setCurrentIndex(
                index, QtCore.QItemSelectionModel.ClearAndSelect)
            self.expand(index)
            self.scrollTo(index)

        super(SelectFolderView, self).showEvent(event)

    @QtCore.Slot()
    def adjust_height(self, *args, **kwargs):
        """Adjusts the size of the view to fix the items exactly."""
        index = self.rootIndex()
        height = 0
        while True:
            index = self.indexBelow(index)
            if not index.isValid():
                break
            height += self.itemDelegate().sizeHint(QtCore.QModelIndex()).height()
            if height > 300:
                break
        self.setFixedHeight(height)

    @QtCore.Slot(QtCore.QModelIndex)
    def set_asset(self, index):
        if not index.isValid():
            self.model().setRootPath(u'.')
        else:
            path = u'/'.join(index.data(common.ParentRole))
            self.model().setRootPath(path)

        self.model()._asset = index
        self.model().destinationChanged.emit(QtCore.QModelIndex())
        self.setRootIndex(self.model().index(self.model().rootPath()))


class SelectFolderModel(QtWidgets.QFileSystemModel):
    """Contains all the available folders for saving a file."""
    destinationChanged = QtCore.Signal(QtCore.QModelIndex)
    fileTypeChanged = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(SelectFolderModel, self).__init__(parent=parent)
        self.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
        self._asset = QtCore.QModelIndex()
        self._destination = None

    @QtCore.Slot(unicode)
    def set_filetype(self, suffix):
        """Setting a filetype will automatically define a default location
        for the file."""
        if not self.asset().isValid():
            return  # can't set the destination without the asset

        # Check if the suffix is `understood` by the Browser
        parent = list(self.asset().data(common.ParentRole))
        index = QtCore.QModelIndex()

        if suffix in common.exports_formats:
            location = common.ExportsFolder
            destination = u'/'.join(parent + [common.ExportsFolder, suffix])
            destination_dir = QtCore.QDir(destination)
            if not destination_dir.exists():
                if not self.create_folder(location, suffix, destination_dir):
                    return
            index = self.index(destination)
        elif suffix in (list(common.scene_formats) + list(common.creative_cloud_formats)):
            location = common.ScenesFolder
            destination = u'/'.join(parent + [common.ScenesFolder])
            destination_dir = QtCore.QDir(destination)
            if not destination_dir.exists():
                if not self.create_folder(location, suffix, destination_dir):
                    return
            index = self.index(destination)
        else:
            destination = u'/'.join(parent)
            index = self.index(destination)
        if index.isValid():
            self.destinationChanged.emit(index)

    def create_folder(self, location, suffix, destination_dir):
        """Creates a folder inside the asset to store the given suffix
        files."""
        result = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Warning,
            u'Destination folder missing',
            u'The default destination folder for "{}" files is missing.\nDo you want to create it now?\n\n({})'.format(
                suffix, destination_dir.absolutePath()),
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
        ).exec_()
        if result == QtWidgets.QMessageBox.Ok:
            return QtCore.QDir().mkpath(destination_dir.absolutePath())
        return False

    def is_model_valid(self):
        """The model is `invalid` if the root path or the asset has not yet#
        been set."""
        if self.rootPath() == '.':
            return False
        if not self._asset.isValid():
            return False
        return True

    def asset(self):
        """The active asset."""
        return self._asset

    def columnCount(self, index, parent=QtCore.QModelIndex()):
        return 1

    def destination(self):
        """The folder to save the file into."""
        return self._destination

    @QtCore.Slot(QtCore.QModelIndex)
    def set_destination(self, index):
        """The folder to save the file into."""
        if not index.isValid():
            self._destination = None
        self._destination = self.filePath(index)

    def flags(self, index):
        """Without a valid asset index, the model will not allow item selection."""
        if self.is_model_valid():
            flags = super(SelectFolderModel, self).flags(index)
            if self.filePath(index) == self._destination:
                flags = flags | common.MarkedAsActive
            return flags
        return QtCore.Qt.NoItemFlags

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """Without a valid asset index, the model will not allow item selection."""
        if self.rootPath() == u'.':
            return u'Asset has not yet been selected'
        if not self.asset().isValid():
            return u'Asset has not yet been selected'
        return super(SelectFolderModel, self).data(index, role=role)


class SelectFolderButton(ClickableLabel):
    """A ClickableLabel for showing the FolderView."""

    def __init__(self, parent=None):
        super(SelectFolderButton, self).__init__(parent=parent)
        self._view = None
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        self.setMouseTracking(True)
        self.setText(u'Select destination folder...')
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setObjectName(u'SelectFolderButton')
        self.setFixedHeight(36)

        self.clicked.connect(self.show_view, type=QtCore.Qt.QueuedConnection)

    def contextMenuEvent(self, event):
        widget = SelectFolderContextMenu(parent=self)
        pos = self.rect().bottomLeft()
        pos = self.mapToGlobal(pos)
        widget.move(pos)
        common.move_widget_to_available_geo(widget)
        widget.exec_()

    def set_view(self, widget):
        """Sets the view associated with this custom button."""
        self._view = widget
        widget.setParent(self)
        self._view.setWindowFlags(
            QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self._view.model().destinationChanged.connect(self.destinationChanged)

    def view(self):
        """The view associated with this custom button."""
        return self._view

    def show_view(self):
        """Shows the view associated with this custom button."""
        if not self.view():
            return
        if self.view().isVisible():
            self.view().hide()
            return

        pos = self.rect().bottomLeft()
        y = self.mapToGlobal(pos).y()
        pos = self.parent().window().rect().bottomLeft()
        x = self.parent().window().mapToGlobal(pos).x()
        y = self.parent().window().mapToGlobal(pos).y()
        width = self.parent().window().rect().width()
        self.view().move(x, y)
        self.view().setFixedWidth(width)
        self.view().show()
        self.view().setFocus()
        self.view().raise_()

        index = QtCore.QModelIndex()
        if hasattr(self.view().model(), 'sourceModel'):
            source_index = self.view().model().sourceModel().active_index()
            if not source_index.isValid():
                return
            index = self.view().model().mapFromSource(source_index)
        else:
            dest = self.view().model().destination()
            if dest:
                index = self.view().model().index(dest)

        self.view().selectionModel().setCurrentIndex(
            index, QtCore.QItemSelectionModel.ClearAndSelect)
        self.view().scrollTo(
            index, QtWidgets.QAbstractItemView.PositionAtCenter)

    def showEvent(self, event):
        return super(SelectFolderButton, self).showEvent(event)

    @QtCore.Slot(QtCore.QModelIndex)
    def destinationChanged(self, index):
        if not index.isValid():
            self.setText(u'Select destination folder...')
            return

        data = self.view().model().fileName(index)
        self.setText(data.upper())

    @QtCore.Slot(unicode)
    def setText(self, text):
        super(SelectFolderButton, self).setText(text)
        metrics = QtGui.QFontMetrics(common.PrimaryFont)
        width = metrics.width(self.text())
        self.setFixedWidth(width + (common.MARGIN * 2))
        self.update()

    def enterEvent(self, event):
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        color = common.FAVOURITE if hover else common.TEXT

        if self.view().model().destination():
            color = QtGui.QColor(30, 200, 120)

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        common.draw_aliased_text(
            painter, common.PrimaryFont, self.rect(),
            self.text(), QtCore.Qt.AlignCenter, color)

        rect = QtCore.QRect(self.rect())
        rect.setTop(rect.bottom() - 1)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 1, 1)
        painter.end()


class SelectAssetDelegate(AssetsWidgetDelegate):
    """Delegate used by the ``AssetsWidget`` to display the collecteds assets."""

    def paint(self, painter, option, index):
        """Defines how the ``AssetsWidget``'s' items should be painted."""
        args = self._get_paint_args(painter, option, index)

        self.paint_background(*args)
        #
        self.paint_thumbnail(*args)
        self.paint_archived(*args)
        self.paint_thumbnail_shadow(*args)
        #
        self.paint_name(*args)
        self.paint_description(*args)
        #
        self.paint_selection_indicator(*args)

    def sizeHint(self, option, index):
        return QtCore.QSize(common.WIDTH, common.ASSET_ROW_HEIGHT)


class SaverListView(BaseInlineIconWidget):
    widgetShown = QtCore.Signal()

    def __init__(self, parent=None):
        super(SaverListView, self).__init__(parent=parent)
        common.set_custom_stylesheet(self)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, False)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground, False)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground, False)

    def showEvent(self, event):
        self.widgetShown.emit()
        self.adjust_height()

    @QtCore.Slot()
    def adjust_height(self, *args, **kwargs):
        """Adjusts the size of the view to fit the contents exactly."""
        height = 0

        option = QtWidgets.QStyleOptionViewItem()
        option.initFrom(self)

        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0)
            if not index.isValid():
                break
            height += self.itemDelegate().sizeHint(option, index).height()
            if height > 300:
                break
        if height == 0:
            height += self.itemDelegate().sizeHint(option, index).height()
        self.setFixedHeight(height)

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.hide()

    def mouseDoubleClickEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.activate(self.selectionModel().currentIndex())

    def inline_icons_count(self):
        return 0


class SelectAssetView(SaverListView):
    """Simple tree view for browsing the available assets."""

    def __init__(self, parent=None):
        super(SelectAssetView, self).__init__(parent=parent)
        self.setItemDelegate(SelectAssetDelegate(parent=self))
        self.clicked.connect(self.activate, type=QtCore.Qt.QueuedConnection)
        self.clicked.connect(self.hide, type=QtCore.Qt.QueuedConnection)


class SelectAssetButton(SelectFolderButton):
    """The button responsible for showing the assets view."""

    def __init__(self, parent=None):
        super(SelectAssetButton, self).__init__(parent=parent)
        self.setText('Select asset...')
        self.setObjectName(u'SelectAssetButton')

    def set_view(self, widget):
        self._view = widget
        widget.setParent(self)
        self._view.setWindowFlags(
            QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

        widget.model().sourceModel().activeChanged.connect(self.activeAssetChanged)
        widget.model().sourceModel().modelAboutToBeReset.connect(
            functools.partial(self.setText, 'Select asset...'))
        widget.model().sourceModel().modelReset.connect(
            lambda: widget.model().sourceModel().activeChanged.emit(widget.model().sourceModel().active_index()))

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        color = common.FAVOURITE if hover else common.TEXT

        if self.view().model().sourceModel().active_index().isValid():
            color = QtGui.QColor(30, 200, 120)

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        common.draw_aliased_text(
            painter, common.PrimaryFont, self.rect(),
            self.text(), QtCore.Qt.AlignCenter, color)

        rect = QtCore.QRect(self.rect())
        rect.setTop(rect.bottom() - 1)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 1, 1)

        painter.end()

    @QtCore.Slot(QtCore.QModelIndex)
    def activeAssetChanged(self, index):
        if not index.isValid():
            return
        parent = index.data(common.ParentRole)
        # text = u'{}'.format(parent[1], parent[-1])
        self.setText(parent[-1].upper())


# ++++++++++++++++++++++++++++++
# BOOKMARK
# ++++++++++++++++++++++++++++++

class SelectBookmarkDelegate(BookmarksWidgetDelegate):
    """The delegate used to paint the bookmark items."""

    def paint(self, painter, option, index):
        """Defines how the BookmarksWidgetItems should be painted."""
        args = self._get_paint_args(painter, option, index)
        self.paint_background(*args)
        #
        self.paint_thumbnail(*args)
        self.paint_archived(*args)
        #
        self.paint_name(*args)
        #
        self.paint_count_icon(*args)
        #
        self.paint_selection_indicator(*args)

    def sizeHint(self, option, index):
        return QtCore.QSize(common.WIDTH, common.BOOKMARK_ROW_HEIGHT)


class SelectBookmarkView(SaverListView):
    """Simple tree view for browsing the available assets."""

    def __init__(self, parent=None):
        super(SelectBookmarkView, self).__init__(parent=parent)
        self.setItemDelegate(SelectBookmarkDelegate(parent=self))
        self.clicked.connect(self.activate, type=QtCore.Qt.QueuedConnection)
        self.clicked.connect(self.hide, type=QtCore.Qt.QueuedConnection)
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

    def showEvent(self, event):
        self.widgetShown.emit()
        self.adjust_height()

    @QtCore.Slot()
    def adjust_height(self, *args, **kwargs):
        """Adjusts the size of the view to fit the contents exactly."""
        height = 0
        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0)
            if not index.isValid():
                break
            height += self.itemDelegate().sizeHint(None, None).height()
            if height > 300:
                break
        if height == 0:
            height += self.itemDelegate().sizeHint(None, None).height()
        self.setFixedHeight(height)

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.hide()

    def mouseDoubleClickEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.activate(self.selectionModel().currentIndex())

    def inline_icons_count(self):
        return 0


class SelectBookmarkButton(SelectAssetButton):
    """The button responsible for showing the assets view."""

    def __init__(self, parent=None):
        super(SelectBookmarkButton, self).__init__(parent=parent)
        self.setText('Select bookmark')
        self.setObjectName(u'SelectBookmarkButton')

    def set_view(self, widget):
        super(SelectBookmarkButton, self).set_view(widget)
        widget.model().sourceModel().activeChanged.connect(self.activeAssetChanged)
        widget.model().sourceModel().modelDataResetRequested.emit()

    @QtCore.Slot(QtCore.QModelIndex)
    def activeAssetChanged(self, index):
        if not index.isValid():
            return
        parent = index.data(common.ParentRole)
        text = u'{}: {}'.format(parent[1], parent[-1])
        self.setText(text.upper())
