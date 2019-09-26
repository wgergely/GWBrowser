# -*- coding: utf-8 -*-
"""This modules contains all the elements needed to select a folder from inside
the current task folder.

"""

import re
import functools
from PySide2 import QtCore, QtWidgets, QtGui

import gwbrowser.common as common
from gwbrowser.common_ui import ClickableLabel
from gwbrowser.bookmarkswidget import BookmarksModel
from gwbrowser.delegate import BaseDelegate
from gwbrowser.delegate import paintmethod
from gwbrowser.basecontextmenu import BaseContextMenu, contextmenu
from gwbrowser.delegate import AssetsWidgetDelegate
from gwbrowser.delegate import BookmarksWidgetDelegate
from gwbrowser.baselistwidget import BaseInlineIconWidget


class SelectButton(QtWidgets.QLabel):
    """A clickable text label with a view widget attached.
    Used to pick the bookmark, asset and subfolders when using the saver.

    Signals:
        activeChanged (QModelIndex): Notifies other components of a selection-change.

    """
    activeChanged = QtCore.Signal(QtCore.QModelIndex)
    clicked = QtCore.Signal()
    widgetMoved = QtCore.Signal(QtCore.QRect)

    Context_menu_cls = None

    def __init__(self, label, view, parent=None):
        super(SelectButton, self).__init__(parent=parent)
        self._view = view

        common.set_custom_stylesheet(self)
        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setText(label)
        self.setFocusProxy(self.view())

        self._connectSignals()

    def select_active(self):
        active_index = self.view().model().sourceModel().active_index()
        if not active_index.isValid():
            return

        proxy_index = self.view().model().mapFromSource(active_index)
        self.activated(proxy_index)
        self.view().scrollTo(proxy_index, QtWidgets.QAbstractItemView.PositionAtCenter)
        self.view().selectionModel().setCurrentIndex(proxy_index, QtCore.QItemSelectionModel.ClearAndSelect)
        self.repaint()

    def _connectSignals(self):
        self.clicked.connect(self.show_view)
        self.widgetMoved.connect(self.adjust_view)
        self.view().activated.connect(self.activated)
        self.view().activated.connect(lambda x: self.activeChanged.emit(self.view().model().mapToSource(x)))
        self.view().model().sourceModel().modelReset.connect(self.select_active)

    def has_selection(self):
        return self.view().selectionModel().hasSelection()

    def view(self):
        """The view associated with this custom button."""
        return self._view

    def set_view(self, widget):
        """Sets the view associated with this custom button."""
        self._view = widget
        widget.setParent(self)

    def show_view(self):
        """Shows the view associated with this custom button."""
        if not self.view():
            return
        if self.view().isVisible():
            self.view().hide()
            return

        self.view().setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Window)

        pos = self.rect().bottomLeft()
        y = self.mapToGlobal(pos).y()
        pos = self.rect().bottomLeft()
        x = self.mapToGlobal(pos).x()
        y = self.mapToGlobal(pos).y()
        width = self.rect().width()
        self.view().move(x, y)
        self.view().setFixedWidth(width)

        self.view().show()
        self.view().raise_()
        self.view().setFocus()

    @QtCore.Slot(QtCore.QModelIndex)
    def activated(self, index):
        source_index = self.view().model().mapToSource(index)
        self.setText(source_index.data(QtCore.Qt.DisplayRole))
        self.repaint()

    @QtCore.Slot(QtCore.QRect)
    def adjust_view(self, rect):
        top_left = rect.topLeft()
        top_left = self.mapToGlobal(top_left)
        self.view().move(top_left)

    @QtCore.Slot(QtCore.QModelIndex)
    def destinationChanged(self, index):
        if not index.isValid():
            self.setText(u'Select destination folder...')
            return

        data = self.view().model().fileName(index)
        self.setText(data.upper())

    @QtCore.Slot(unicode)
    def setText(self, text):
        super(SelectButton, self).setText(text)
        metrics = QtGui.QFontMetrics(common.PrimaryFont)
        width = metrics.width(self.text())
        self.setFixedWidth(width + (common.MARGIN * 2))
        self.repaint()

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        color = common.FAVOURITE if hover else common.TEXT

        if self.has_selection():
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

    def contextMenuEvent(self, event):
        if not self.Context_menu_cls:
            return

        w = self.Context_menu_cls(parent=self)
        pos = self.rect().bottomLeft()
        pos = self.mapToGlobal(pos)
        w.move(pos)

        common.move_widget_to_available_geo(w)

        widget.exec_()

    def enterEvent(self, event):
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.button() == QtCore.Qt.LeftButton:
            pos = QtGui.QCursor().pos()
            if self.geometry().contains(pos):
                self.clicked.emit()

    def hideEvent(self, event):
        self.view().hide()

    def showEvent(self, event):
        self.view().hide()

    def resizeEvent(self, event):
        self.widgetMoved.emit(self.rect())

    def moveEvent(self, event):
        self.widgetMoved.emit(self.rect())


class SelectListView(BaseInlineIconWidget):
    widgetShown = QtCore.Signal()

    def __init__(self, model, delegate, parent=None):
        super(SelectListView, self).__init__(parent=parent)
        self.set_model(model)
        delegate.setParent(self)
        self.setItemDelegate(delegate)

        # common.set_custom_stylesheet(self)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, False)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground, False)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.removeEventFilter(self)

        self._connectSignals()

    def _connectSignals(self):
        self.clicked.connect(self.hide)
        self.clicked.connect(self.activated)

    def showEvent(self, event):
        self.widgetShown.emit()
        self.adjust_height()

        if self.selectionModel().hasSelection():
            self.scrollTo(self.selectionModel().currentIndex())

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
            self.hide()
            return
        #     height += self.itemDelegate().sizeHint(option, QtCore.QModelIndex()).height()
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


# class SelectFolderContextMenu(BaseContextMenu):
#     """Context menu associated with the thumbnail."""
#
#     def __init__(self, parent=None):
#         super(SelectFolderContextMenu, self).__init__(
#             QtCore.QModelIndex(), parent=parent)
#         self.add_reveal_item_menu()
#
#     @contextmenu
#     def add_reveal_item_menu(self, menu_set):
#         """Menu for thumbnail operations."""
#         asset = self.parent().view().model().asset()
#         if asset.isValid():
#             asset_path = asset.data(common.ParentRole)
#             asset_path = u'/'.join(asset_path)
#             menu_set[u'Reveal asset'] = {
#                 u'action': functools.partial(common.reveal, asset_path)
#             }
#             destination = self.parent().view().model().destination()
#             if destination:
#                 menu_set[u'Reveal destination'] = {
#                     u'action': functools.partial(common.reveal, destination)
#                 }
#         return menu_set
#
#
# class SelectFolderDelegate(BaseDelegate):
#     """Delegate responsible for painting the FolderWidget items."""
#
#     def __init__(self, parent=None):
#         super(SelectFolderDelegate, self).__init__(parent=parent)
#
#     def paint(self, painter, option, index):
#         """Defines how the BookmarksWidgetItems should be painted."""
#         args = self._get_paint_args(painter, option, index)
#         self.paint_background(*args)
#         self.paint_name(*args)
#
#     @paintmethod
#     def paint_name(self, *args):
#         """Paints the item names inside the ``FoldersWidget``."""
#         painter, option, index, _, _, _, _, _, hover = args
#
#         rect = QtCore.QRect(option.rect)
#         root = self.parent().model().parent(index) == self.parent().rootIndex()
#         active = self.parent().model().destination(
#         ) == self.parent().model().filePath(index)
#
#         center = rect.center()
#         rect.setHeight(common.INLINE_ICON_SIZE)
#         rect.setWidth(rect.width() - (common.MARGIN * 2))
#         rect.moveCenter(center)
#
#         font = QtGui.QFont(common.PrimaryFont)
#         metrics = QtGui.QFontMetrics(font)
#
#         text = index.data(QtCore.Qt.DisplayRole)
#         color = common.TEXT if root else common.SECONDARY_TEXT
#         color = common.TEXT_SELECTED if hover else color
#
#         if index.flags() == QtCore.Qt.NoItemFlags:
#             common.draw_aliased_text(
#                 painter, font, rect, text, QtCore.Qt.AlignCenter, common.TEXT)
#             return
#
#         # Asset name
#         text = re.sub(ur'[^0-9a-zA-Z]+', u' ', text)
#         text = re.sub(ur'[_]{1,}', u'_', text).strip(u'_')
#         if active:
#             text = u'>  {}  <'.format(text).upper()
#         else:
#             text = u'{}'.format(text).upper()
#             # text = '{}'.format(text)
#         rect.setWidth(metrics.width(text) + common.INDICATOR_WIDTH)
#
#         if root:
#             painter.setBrush(common.FAVOURITE)
#             pen = QtGui.QPen(common.FAVOURITE)
#         else:
#             painter.setBrush(common.SECONDARY_BACKGROUND)
#             pen = QtGui.QPen(common.SECONDARY_BACKGROUND)
#
#             pen.setWidth(common.INDICATOR_WIDTH)
#         if self.parent().model().destination() == self.parent().model().filePath(index):
#             color = QtGui.QColor(30, 200, 120)
#             painter.setBrush(color)
#             pen.setColor(color)
#             color = common.TEXT_SELECTED
#         painter.setPen(pen)
#
#         painter.drawRoundedRect(rect, 2, 2)
#         common.draw_aliased_text(
#             painter, common.PrimaryFont, rect, text, QtCore.Qt.AlignCenter, color)
#
#     @paintmethod
#     def paint_background(self, *args):
#         """Paints the background."""
#         painter, option, index, _, _, _, _, _, _ = args
#         if index.flags() == QtCore.Qt.NoItemFlags:
#             return
#         hover = option.state & QtWidgets.QStyle.State_MouseOver
#
#         painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
#         color = QtGui.QColor(common.BACKGROUND)
#         if hover:
#             color = QtGui.QColor(common.BACKGROUND_SELECTED)
#
#         rect = QtCore.QRect(option.rect)
#         root = self.parent().model().parent(index) == self.parent().rootIndex()
#         if root:
#             rect.setTop(rect.top() + 2)
#         painter.setBrush(QtGui.QBrush(color))
#         painter.drawRect(rect)
#
#     def sizeHint(self, index, parent=QtCore.QModelIndex()):
#         return QtCore.QSize(common.WIDTH, common.ROW_BUTTONS_HEIGHT)

#
# class SelectFolderView(QtWidgets.QTreeView):
#     """Simple tree view for browsing the available folders."""
#     widgetShown = QtCore.Signal()
#
#     def __init__(self, parent=None):
#         super(SelectFolderView, self).__init__(parent=parent)
#         self.setHeaderHidden(True)
#         self.setItemDelegate(SelectFolderDelegate(parent=self))
#         self.setIndentation(common.MARGIN / 2)
#         self.setRootIsDecorated(False)
#         common.set_custom_stylesheet(self)
#
#         self.clicked.connect(lambda i: self.collapse(
#             i) if self.isExpanded(i) else self.expand(i), type=QtCore.Qt.QueuedConnection)
#         self.clicked.connect(self.index_expanded,
#                              type=QtCore.Qt.QueuedConnection)
#         self.activated.connect(self.hide)
#
#     def set_model(self, model):
#         self.setModel(model)
#
#         model.setRootPath(u'.')
#         index = model.index(model.rootPath())
#         self.setRootIndex(index)
#
#         self.model().directoryLoaded.connect(self.index_expanded)
#         self.model().directoryLoaded.connect(self.adjust_height)
#         self.activated.connect(self.model().destinationChanged)
#
#     def index_expanded(self, index):
#         self.adjust_height()
#
#     def showEvent(self, event):
#         self.widgetShown.emit()
#         self.adjust_height()
#
#         if self.model().destination():
#             self.collapseAll()
#             index = self.model().index(self.model().destination())
#             self.selectionModel().setCurrentIndex(
#                 index, QtCore.QItemSelectionModel.ClearAndSelect)
#             self.expand(index)
#             self.scrollTo(index)
#
#         super(SelectFolderView, self).showEvent(event)
#
#     @QtCore.Slot()
#     def adjust_height(self, *args, **kwargs):
#         """Adjusts the size of the view to fix the items exactly."""
#         index = self.rootIndex()
#
#         height = 0
#         row_height = self.itemDelegate().sizeHint(QtCore.QModelIndex()).height()
#         while True:
#             index = self.indexBelow(index)
#             if not index.isValid():
#                 break
#             height += row_height
#             if height > 300:
#                 break
#         if height == 0:
#             height = 3
#         self.setFixedHeight(height)
#
#     @QtCore.Slot(QtCore.QModelIndex)
#     def set_root_index(self, index):
#         if not index.isValid():
#             path = u'.'
#         else:
#             path = u'/'.join(index.data(common.ParentRole))
#
#         self._asset = index
#
#         self.model().setRootPath(path)
#         index = self.model().index(self.model().rootPath())
#         self.setRootIndex(index)
#
#         self.model().destinationChanged.emit(index)

#
# class SelectFolderModel(QtWidgets.QFileSystemModel):
#     """Contains all the available folders for saving a file."""
#     destinationChanged = QtCore.Signal(QtCore.QModelIndex)
#     fileTypeChanged = QtCore.Signal(unicode)
#
#     def __init__(self, parent=None):
#         super(SelectFolderModel, self).__init__(parent=parent)
#         self.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
#         self._asset = QtCore.QModelIndex()
#         self._destination = None
#
#     @QtCore.Slot(unicode)
#     def set_filetype(self, suffix):
#         """Setting a filetype will automatically define a default location
#         for the file."""
#         if not self.asset().isValid():
#             return  # can't set the destination without the asset
#
#         # Check if the suffix is `understood` by the Browser
#         parent = list(self.asset().data(common.ParentRole))
#         index = QtCore.QModelIndex()
#
#         if suffix in common.exports_formats:
#             location = common.ExportsFolder
#             destination = u'/'.join(parent + [common.ExportsFolder, suffix])
#             destination_dir = QtCore.QDir(destination)
#             if not destination_dir.exists():
#                 if not self.create_folder(location, suffix, destination_dir):
#                     return
#             index = self.index(destination)
#         elif suffix in (list(common.scene_formats) + list(common.creative_cloud_formats)):
#             location = common.ScenesFolder
#             destination = u'/'.join(parent + [common.ScenesFolder])
#             destination_dir = QtCore.QDir(destination)
#             if not destination_dir.exists():
#                 if not self.create_folder(location, suffix, destination_dir):
#                     return
#             index = self.index(destination)
#         else:
#             destination = u'/'.join(parent)
#             index = self.index(destination)
#         if index.isValid():
#             self.destinationChanged.emit(index)
#
#     def create_folder(self, location, suffix, destination_dir):
#         """Creates a folder inside the asset to store the given suffix
#         files."""
#         result = QtWidgets.QMessageBox(
#             QtWidgets.QMessageBox.Warning,
#             u'Destination folder missing',
#             u'The default destination folder for "{}" files is missing.\nDo you want to create it now?\n\n({})'.format(
#                 suffix, destination_dir.absolutePath()),
#             QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
#         ).exec_()
#         if result == QtWidgets.QMessageBox.Ok:
#             return QtCore.QDir().mkpath(destination_dir.absolutePath())
#         return False
#
#     def is_model_valid(self):
#         """The model is `invalid` if the root path or the asset has not yet#
#         been set."""
#         if self.rootPath() == u'.':
#             return False
#         if not self._asset.isValid():
#             return False
#         return True
#
#     def asset(self):
#         """The active asset."""
#         return self._asset
#
#     def columnCount(self, index, parent=QtCore.QModelIndex()):
#         return 1
#
#     def destination(self):
#         """The folder to save the file into."""
#         return self._destination
#
#     @QtCore.Slot(QtCore.QModelIndex)
#     def set_destination(self, index):
#         """The folder to save the file into."""
#         if not index.isValid():
#             self._destination = None
#         self._destination = self.filePath(index)
#
#     def flags(self, index):
#         """Without a valid asset index, the model will not allow item selection."""
#         if self.is_model_valid():
#             flags = super(SelectFolderModel, self).flags(index)
#             if self.filePath(index) == self._destination:
#                 flags = flags | common.MarkedAsActive
#             return flags
#         return QtCore.Qt.NoItemFlags


#
# class SelectAssetDelegate(AssetsWidgetDelegate):
#     """Delegate used by the ``AssetsWidget`` to display the collecteds assets."""
#
#     def paint(self, painter, option, index):
#         """Defines how the ``AssetsWidget``'s' items should be painted."""
#         args = self._get_paint_args(painter, option, index)
#
#         self.paint_background(*args)
#         #
#         self.paint_thumbnail(*args)
#         self.paint_archived(*args)
#         self.paint_thumbnail_shadow(*args)
#         #
#         self.paint_name(*args)
#         self.paint_description(*args)
#         #
#         self.paint_selection_indicator(*args)
#
#     def sizeHint(self, option, index):
#         return QtCore.QSize(common.WIDTH, common.ASSET_ROW_HEIGHT)
#
# #


#
# class SelectAssetView(SelectListView):
#     """Simple tree view for browsing the available assets."""
#
#     def __init__(self, parent=None):
#         super(SelectAssetView, self).__init__(parent=parent)
#         self.setItemDelegate(SelectAssetDelegate(parent=self))
#         self.clicked.connect(self.activate)
#         self.clicked.connect(self.hide)


# class SelectAssetButton(SelectFolderButton):
#     """The button responsible for showing the assets view."""
#
#     def __init__(self, parent=None):
#         super(SelectAssetButton, self).__init__(parent=parent)
#
#         self.setText('Select asset...')
#         self.setObjectName(u'SelectAssetButton')
#
#         w = SelectAssetView(parent=self)
#         self._view = w
#         w.model().sourceModel().activeChanged.connect(self.activeAssetChanged)
#         w.model().sourceModel().modelAboutToBeReset.connect(lambda: self.setText(u'Select asset...'))
#         w.model().sourceModel().modelReset.connect(
#             lambda: w.model().sourceModel().activeChanged.emit(w.model().sourceModel().active_index()))
#
#     def paintEvent(self, event):
#         option = QtWidgets.QStyleOption()
#         option.initFrom(self)
#         hover = option.state & QtWidgets.QStyle.State_MouseOver
#         color = common.FAVOURITE if hover else common.TEXT
#
#         if self.view().model().sourceModel().active_index().isValid():
#             color = QtGui.QColor(30, 200, 120)
#
#         painter = QtGui.QPainter()
#         painter.begin(self)
#         painter.setRenderHint(QtGui.QPainter.Antialiasing)
#         painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
#
#         common.draw_aliased_text(
#             painter, common.PrimaryFont, self.rect(),
#             self.text(), QtCore.Qt.AlignCenter, color)
#
#         rect = QtCore.QRect(self.rect())
#         rect.setTop(rect.bottom() - 1)
#         painter.setPen(QtCore.Qt.NoPen)
#         painter.setBrush(color)
#         painter.drawRoundedRect(rect, 1, 1)
#
#         painter.end()
#
#     @QtCore.Slot(QtCore.QModelIndex)
#     def activeAssetChanged(self, index):
#         if not index.isValid():
#             return
#         parent = index.data(common.ParentRole)
#         # text = u'{}'.format(parent[1], parent[-1])
#         self.setText(parent[-1].upper())


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

#
# class SelectBookmarkView(SelectListView):
#     """Simple tree view for browsing the available assets."""
#
#     def __init__(self, parent=None):
#         super(SelectBookmarkView, self).__init__(parent=parent)
#         self.setItemDelegate(SelectBookmarkDelegate(parent=self))
#         self.clicked.connect(self.activate, type=QtCore.Qt.QueuedConnection)
#         self.clicked.connect(self.hide, type=QtCore.Qt.QueuedConnection)
#         self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
#
#     def showEvent(self, event):
#         self.widgetShown.emit()
#         self.adjust_height()
#
#         if self.selectionModel().hasSelection():
#             self.scrollTo(self.selectionModel().currentIndex())
#
#     @QtCore.Slot()
#     def adjust_height(self, *args, **kwargs):
#         """Adjusts the size of the view to fit the contents exactly."""
#         height = 0
#         for n in xrange(self.model().rowCount()):
#             index = self.model().index(n, 0)
#             if not index.isValid():
#                 break
#             height += self.itemDelegate().sizeHint(None, None).height()
#             if height > 300:
#                 break
#         if height == 0:
#             height += self.itemDelegate().sizeHint(None, None).height()
#         self.setFixedHeight(height)
#
#     def focusOutEvent(self, event):
#         """Closes the editor on focus loss."""
#         if event.lostFocus():
#             self.hide()
#
#     def mouseDoubleClickEvent(self, event):
#         if not isinstance(event, QtGui.QMouseEvent):
#             return
#         self.activate(self.selectionModel().currentIndex())
#
#     def inline_icons_count(self):
#         return 0


# class SelectBookmarkButton(SelectAssetButton):
#     """The button responsible for showing the assets view."""
#
#     def __init__(self, parent=None):
#         super(SelectBookmarkButton, self).__init__(parent=parent)
#         self.setText('Select bookmark')
#         self.setObjectName(u'SelectBookmarkButton')
#
#         w = SelectBookmarkView(parent=parent)
#         self._view = w
#
#         w.model().sourceModel().activeChanged.connect(self.activeAssetChanged)
#         w.model().sourceModel().modelAboutToBeReset.connect(lambda: self.setText(u'Select...'))
#         # w.model().sourceModel().modelReset.connect(
#         #     lambda: w.model().sourceModel().activeChanged.emit(w.model().sourceModel().active_index()))
#
#     @QtCore.Slot(QtCore.QModelIndex)
#     def activeAssetChanged(self, index):
#         if not index.isValid():
#             return
#         parent = index.data(common.ParentRole)
#         text = u'{}: {}'.format(parent[1], parent[-1])
#         self.setText(text.upper())

if __name__ == '__main__':
    app = QtWidgets.QApplication([])

    # Bookmarks
    model = BookmarksModel()
    delegate = SelectBookmarkDelegate()
    view = SelectListView(model, delegate)
    widget = SelectButton('Select bookmark...', view)
    widget.show()

    view.model().sourceModel().modelDataResetRequested.emit()
    app.exec_()
