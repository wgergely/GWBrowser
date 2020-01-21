# -*- coding: utf-8 -*-
"""``bookmarkswidget.py`` defines the main objects needed for interacting with
bookmarks. This includes the utility classes for getting bookmark status and to
allow dropping files and urls on the view.

"""
import re

from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser._scandir as gwscandir
from gwbrowser.imagecache import ImageCache
import gwbrowser.common as common
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.baselistwidget import BaseInlineIconWidget
from gwbrowser.baselistwidget import BaseModel
from gwbrowser.baselistwidget import initdata
from gwbrowser.settings import local_settings, Active
from gwbrowser.settings import AssetSettings
import gwbrowser.delegate as delegate
from gwbrowser.delegate import BookmarksWidgetDelegate


class BookmarkInfo(QtCore.QFileInfo):
    """QFileInfo for bookmarks."""

    def __init__(self, bookmark, parent=None):
        self.server = bookmark[u'server']
        self.job = bookmark[u'job']
        self.root = bookmark[u'root']
        self.exists = None

        path = u'{}/{}/{}'.format(self.server, self.job, self.root)
        super(BookmarkInfo, self).__init__(path, parent=parent)

        if not QtCore.QFileInfo(path).exists():
            self.size = lambda: 0
            self.count = lambda: 0
            self.exists = lambda: False
            return

        self.exists = lambda: True
        self.size = lambda: self.count_assets(path)
        self.count = lambda: self.count_assets(path)

    @staticmethod
    def count_assets(path):
        """Returns the number of assets inside the given folder."""
        count = 0
        for entry in gwscandir.scandir(path):
            if not entry.is_dir():
                continue
            identifier_path = u'{}/{}'.format(
                entry.path,
                common.ASSET_IDENTIFIER)
            if QtCore.QFileInfo(identifier_path).exists():
                count += 1
        return count


class BookmarksWidgetContextMenu(BaseContextMenu):
    """Context menu associated with the BookmarksWidget.

    Methods:
        refresh: Refreshes the collector and repopulates the widget.

    """

    def __init__(self, index, parent=None):
        super(BookmarksWidgetContextMenu, self).__init__(index, parent=parent)
        # Adding persistent actions
        self.add_add_bookmark_menu()
        if index.isValid():
            self.add_mode_toggles_menu()
            self.add_separator()
            self.add_thumbnail_menu()

        self.add_separator()

        if index.isValid():
            self.add_reveal_item_menu()
            self.add_copy_menu()

        self.add_separator()

        self.add_sort_menu()

        self.add_separator()

        self.add_display_toggles_menu()

        self.add_separator()

        self.add_refresh_menu()


class BookmarksModel(BaseModel):
    """The model used store the data necessary to display bookmarks.

    The model is drop-enabled, and accepts file are urls. The dropped items will
    be copied to the root of the bookmark folder.

    """

    def __init__(self, thread_count=0, parent=None):
        super(BookmarksModel, self).__init__(thread_count=thread_count, parent=parent)

    @initdata
    def __initdata__(self):
        """Collects the data needed to populate the bookmarks model.

        Bookmarks are made up of a tuple of ``(server, job, root)`` values and
        are stored in the local user system settings, eg. the Registry
        in under windows. Each bookmarks can be associated with a thumbnail,
        custom description and a list of comments, todo items.

        Note:
            This model does not have threads associated with it as fetching
            necessary data is relatively inexpensive.

        """
        self._data[self.data_key()] = {
            common.FileItem: {}, common.SequenceItem: {}}

        rowsize = QtCore.QSize(0, common.BOOKMARK_ROW_HEIGHT)
        active_paths = Active.paths()

        items = local_settings.value(
            u'bookmarks') if local_settings.value(u'bookmarks') else []
        items = [BookmarkInfo(items[k]) for k in items]
        items = sorted(items, key=lambda x: x.filePath())

        thumbcolor = QtGui.QColor(common.SEPARATOR)
        thumbcolor.setAlpha(100)
        default_thumbnail_image = ImageCache.get_rsc_pixmap(
            u'bookmark_sm',
            thumbcolor,
            common.BOOKMARK_ROW_HEIGHT - common.ROW_SEPARATOR)
        default_thumbnail_image = default_thumbnail_image.toImage()
        default_background_color = common.THUMBNAIL_BACKGROUND

        favourites = local_settings.value(u'favourites')
        favourites = [f.lower() for f in favourites] if favourites else []
        favourites = set(favourites)

        for file_info in items:
            # Let's make sure the Browser's configuration folder exists
            # This folder lives in the root of the bookmarks folder and is
            # created here if not created previously.
            if file_info.exists():
                _confpath = u'{}/.browser/'.format(file_info.filePath())
                _confpath = QtCore.QFileInfo(_confpath)
                QtCore.QDir().mkpath(_confpath.filePath())

            flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

            if not file_info.exists():
                flags = flags | common.MarkedAsArchived

            # Active
            if (
                file_info.server == active_paths[u'server'] and
                file_info.job == active_paths[u'job'] and
                file_info.root == active_paths[u'root']
            ):
                flags = flags | common.MarkedAsActive

            if file_info.filePath().lower() in favourites:
                flags = flags | common.MarkedAsFavourite

            data = self.model_data()
            idx = len(data)

            text = u'{}   |   {}'.format(file_info.job, file_info.root)
            text = text.replace(u'_', u' ')
            text = text.replace(u'/', u' / ')

            data[idx] = {
                QtCore.Qt.DisplayRole: text,
                QtCore.Qt.EditRole: file_info.job,
                QtCore.Qt.StatusTipRole: file_info.filePath(),
                QtCore.Qt.ToolTipRole: file_info.filePath(),
                QtCore.Qt.SizeHintRole: rowsize,
                #
                common.EntryRole: [],
                common.FlagsRole: flags,
                common.ParentPathRole: (file_info.server, file_info.job, file_info.root),
                common.DescriptionRole: None,
                common.TodoCountRole: 0,
                common.FileDetailsRole: file_info.size(),
                common.SequenceRole: None,
                common.EntryRole: [],
                common.FileInfoLoaded: True,
                common.StartpathRole: None,
                common.EndpathRole: None,
                common.AssetCountRole: file_info.size(),
                #
                common.DefaultThumbnailRole: QtGui.QImage(),
                common.DefaultThumbnailBackgroundRole: QtGui.QColor(0, 0, 0, 0),
                common.ThumbnailPathRole: None,
                common.ThumbnailRole: QtGui.QImage(),
                common.ThumbnailBackgroundRole: QtGui.QColor(0, 0, 0, 0),
                #
                common.TypeRole: common.FileItem,
                common.FileInfoLoaded: True,
                #
                common.SortByName: file_info.filePath(),
                common.SortByLastModified: file_info.filePath(),
                common.SortBySize: u'{}'.format(file_info.size()),
            }

            if not file_info.exists():
                continue

            # Thumbnail
            index = self.index(idx, 0)
            settings = AssetSettings(index)
            data[idx][common.ThumbnailPathRole] = settings.thumbnail_path()

            image = ImageCache.get(
                data[idx][common.ThumbnailPathRole],
                rowsize.height() - common.ROW_SEPARATOR,
                overwrite=True)

            if image:
                if not image.isNull():
                    color = ImageCache.get(
                        data[idx][common.ThumbnailPathRole],
                        u'BackgroundColor')

                    data[idx][common.ThumbnailRole] = image
                    data[idx][common.ThumbnailBackgroundRole] = color

            description = settings.value(u'config/description')
            if not description:
                data[idx][common.DescriptionRole] = file_info.filePath()
                settings.setValue(u'config/description', file_info.filePath())
            else:
                data[idx][common.DescriptionRole] = description

            # Todos
            todos = settings.value(u'config/todos')
            todocount = 0
            if todos:
                todocount = len([k for k in todos if not todos[k]
                                 [u'checked'] and todos[k][u'text']])
            else:
                todocount = 0
            data[idx][common.TodoCountRole] = todocount

    def data_key(self):
        """Data keys are only implemented on the FilesModel but need to return a
        value for compatibility other functions.

        """
        return u'.'


class BookmarksWidget(BaseInlineIconWidget):
    """The view used to display the contents of a ``BookmarksModel`` instance."""
    SourceModel = BookmarksModel
    Delegate = BookmarksWidgetDelegate
    ContextMenu = BookmarksWidgetContextMenu

    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)
        self.setDragDropOverwriteMode(False)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setWindowTitle(u'Bookmarks')

        # I'm not sure why but the proxy is not updated properly after refresh
        self.model().sourceModel().dataSorted.connect(self.model().invalidate)

    def buttons_hidden(self):
        """Returns the visibility of the inline icon buttons."""
        return False

    def eventFilter(self, widget, event):
        """Custom event filter used to paint the background icon."""
        super(BookmarksWidget, self).eventFilter(widget, event)

        if widget is not self:
            return False

        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            pixmap = ImageCache.get_rsc_pixmap(
                u'bookmark', QtGui.QColor(0, 0, 0, 20), 180)
            rect = pixmap.rect()
            rect.moveCenter(self.rect().center())
            painter.drawPixmap(rect, pixmap, pixmap.rect())
            painter.end()
            return True

        return False

    def inline_icons_count(self):
        """The number of row-icons an item has."""
        if self.buttons_hidden():
            return 0
        return 5

    def add_asset(self):
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        bookmark = index.data(common.ParentPathRole)
        bookmark = u'/'.join(bookmark)

        from gwbrowser.addassetwidget import AddAssetWidget
        widget = AddAssetWidget(bookmark, parent=self)
        pos = self.rect().center()
        pos = self.mapToGlobal(pos)
        widget.move(
            pos.x() - (widget.width() / 2.0),
            self.mapToGlobal(self.rect().topLeft()).y() + common.MARGIN
        )

        self.disabled_overlay_widget.show()
        try:
            widget.exec_()
            if not widget.last_asset_added:
                self.disabled_overlay_widget.hide()
                return

            self.parent().parent().listcontrolwidget.listChanged.emit(1)
            view = self.parent().widget(1)
            view.model().sourceModel().modelDataResetRequested.emit()
            for n in xrange(view.model().rowCount()):
                index = view.model().index(n, 0)
                file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
                if file_info.fileName().lower() == widget.last_asset_added.lower():
                    view.selectionModel().setCurrentIndex(
                        index, QtCore.QItemSelectionModel.ClearAndSelect)
                    view.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
                    break
        finally:
            self.disabled_overlay_widget.hide()

    @QtCore.Slot(QtCore.QModelIndex)
    def save_activated(self, index):
        """Saves the activated index to ``LocalSettings``."""
        server, job, root = index.data(common.ParentPathRole)
        local_settings.setValue(u'activepath/server', server)
        local_settings.setValue(u'activepath/job', job)
        local_settings.setValue(u'activepath/root', root)
        Active.paths()  # Resetting invalid paths

    def unset_activated(self):
        """Saves the activated index to ``LocalSettings``."""
        server, job, root = None, None, None
        local_settings.setValue(u'activepath/server', server)
        local_settings.setValue(u'activepath/job', job)
        local_settings.setValue(u'activepath/root', root)
        Active.paths()  # Resetting invalid paths

    def toggle_archived(self, index=None, state=None):
        """Bookmarks cannot be archived but they're automatically removed from
        from the ``local_settings``."""

        self.reset_multitoggle()
        res = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.NoIcon,
            u'Remove bookmark?',
            u'Are you sure you want to remove this bookmark?\nDon\'t worry, files won\'t be affected.',
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
            parent=self
        ).exec_()

        if res == QtWidgets.QMessageBox.Cancel:
            return

        if not index:
            index = self.selectionModel().currentIndex()
            index = self.model().mapToSource(index)
        if not index.isValid():
            return

        # Removing the bookmark
        k = index.data(QtCore.Qt.StatusTipRole)
        bookmarks = local_settings.value(u'bookmarks')
        bookmarks.pop(k, None)
        local_settings.setValue(u'bookmarks', bookmarks)

        if index == self.model().sourceModel().active_index():
            self.unset_activated()
            self.model().sourceModel().modelDataResetRequested.emit()
            return
        else:
            self.model().sourceModel().__initdata__()

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        cursor_position = self.mapFromGlobal(QtGui.QCursor().pos())
        index = self.indexAt(cursor_position)
        if not index.isValid():
            return
        if index.flags() & common.MarkedAsArchived:
            return

        rect = self.visualRect(index)
        rectangles = self.itemDelegate().get_rectangles(rect)
        cursor_position = self.mapFromGlobal(QtGui.QCursor().pos())

        if rectangles[delegate.BookmarkCountRect].contains(cursor_position):
            self.add_asset()
            return
        super(BookmarksWidget, self).mouseReleaseEvent(event)
