# -*- coding: utf-8 -*-
"""Module defines a ListWidget used to represent the assets found in the root
of the `server/job/assets` folder.

The asset collector expects a asset to contain an identifier file,
in the case of the default implementation, a ``*.mel`` file in the root of the asset folder.
If the identifier file is not found the folder will be ignored!

Assets are based on maya's project structure and ``Browser`` expects a
a ``renders``, ``textures``, ``exports`` and a ``scenes`` folder to be present.

The actual name of these folders can be customized in the ``common.py`` module.

"""
# pylint: disable=E1101, C0103, R0913, I1101

import re
import os
import functools

from PySide2 import QtWidgets, QtGui, QtCore, QtNetwork

from gwbrowser.imagecache import ImageCache
import gwbrowser.common as common
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.baselistwidget import BaseInlineIconWidget
from gwbrowser.baselistwidget import BaseModel
from gwbrowser.settings import local_settings, Active, active_monitor
from gwbrowser.settings import AssetSettings
from gwbrowser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite
from gwbrowser.delegate import BookmarksWidgetDelegate
from gwbrowser.delegate import BaseDelegate
from gwbrowser.delegate import paintmethod
import gwbrowser.editors as editors
from gwbrowser.addbookmarkswidget import AddBookmarksWidget


class ImageDownloader(QtCore.QObject):
    """Utility class to download an image from a url. Used by the drag and drop operations."""
    # Signals
    downloaded = QtCore.Signal(QtCore.QByteArray, unicode)

    def __init__(self, url, destination, parent=None):
        super(ImageDownloader, self).__init__(parent=parent)
        self.url = url
        self.manager = QtNetwork.QNetworkAccessManager(parent=self)
        self.request = QtNetwork.QNetworkRequest(self.url)
        self.manager.finished.connect(
            lambda reply: self.downloaded.emit(reply.readAll(), destination))
        self.downloaded.connect(self.save_image)

    def get(self):
        self.manager.get(self.request)

    def save_image(self, data, path):
        """Saves the downloaded data as an image."""
        image = QtGui.QImage()
        loaded = image.loadFromData(data)
        if not loaded:
            return

        image = image.convertToFormat(QtGui.QImage.Format_RGB32)
        image.save(path)


class BookmarkInfo(QtCore.QFileInfo):
    """QFileInfo for bookmarks."""

    def __init__(self, bookmark, parent=None):
        self.server = bookmark[u'server']
        self.job = bookmark[u'job']
        self.root = bookmark[u'root']

        path = u'{}/{}/{}'.format(self.server, self.job, self.root)
        super(BookmarkInfo, self).__init__(path, parent=parent)

        self.size = functools.partial(lambda n: n, self.count_assets(path))
        self.count = functools.partial(lambda n: n, self.count_assets(path))

    @staticmethod
    def count_assets(path):
        """Returns the number of assets inside the given folder."""
        dir_ = QtCore.QDir(path)
        dir_.setFilter(
            QtCore.QDir.NoDotAndDotDot
            | QtCore.QDir.Dirs
            | QtCore.QDir.Readable
        )

        # Counting the number assets found
        count = 0
        for file_info in dir_.entryInfoList():
            d = QtCore.QDir(file_info.filePath())
            d.setFilter(QtCore.QDir.Files)
            d.setNameFilters((common.ASSET_IDENTIFIER,))
            if d.entryInfoList():
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
            self.add_thumbnail_menu()

        self.add_separator()

        if index.isValid():
            self.add_reveal_item_menu()
            self.add_copy_menu()

        self.add_separator()

        self.add_sort_menu()
        self.add_display_toggles_menu()

        self.add_separator()

        self.add_refresh_menu()


class BookmarksModel(BaseModel):
    """Drop-enabled model for displaying Bookmarks."""

    def __init__(self, parent=None):
        super(BookmarksModel, self).__init__(parent=parent)

    def __initdata__(self):
        """Collects the data needed to populate the bookmarks model.

        Bookmarks are made up of a tuple of ``(server, job, root)`` values and
        are stored are saved in the local system settings, eg. the Registry
        in under windows.

        """
        self._data[self.data_key()] = {
            common.FileItem: {}, common.SequenceItem: {}}

        rowsize = QtCore.QSize(common.WIDTH, common.BOOKMARK_ROW_HEIGHT)
        active_paths = Active.paths()

        items = local_settings.value(
            u'bookmarks') if local_settings.value(u'bookmarks') else []
        items = [BookmarkInfo(items[k]) for k in items]
        items = sorted(items, key=lambda x: x.filePath())


        thumbcolor = QtGui.QColor(common.SEPARATOR)
        thumbcolor.setAlpha(100)
        default_thumbnail_image = ImageCache.instance().get_rsc_pixmap(
            u'bookmark_sm',
            thumbcolor,
            common.BOOKMARK_ROW_HEIGHT - 2)
        default_thumbnail_image = default_thumbnail_image.toImage()


        # default_thumbnail_path = '{}/../rsc/placeholder.png'.format(__file__)
        # default_thumbnail_path = os.path.normpath(os.path.abspath(default_thumbnail_path))
        # default_thumbnail_image = ImageCache.instance().get(
        #     default_thumbnail_path, rowsize.height() - 2)
        default_background_color = QtGui.QColor(0, 0, 0, 55)

        for idx, file_info in enumerate(items):
            # Let's make sure the Browser's configuration folder exists
            # This folder lives in the root of the bookmarks folder and is
            # created here if not created previously.
            _confpath = u'{}/.browser/'.format(file_info.filePath())
            _confpath = QtCore.QFileInfo(_confpath)
            if not _confpath.exists():
                QtCore.QDir().mkpath(_confpath.filePath())

            flags = (
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsDropEnabled |
                QtCore.Qt.ItemIsEditable
            )

            # Active
            if (
                file_info.server == active_paths[u'server'] and
                file_info.job == active_paths[u'job'] and
                file_info.root == active_paths[u'root']
            ):
                flags = flags | MarkedAsActive

            favourites = local_settings.value(u'favourites')
            favourites = favourites if favourites else []
            if file_info.filePath() in favourites:
                flags = flags | MarkedAsFavourite

            if not file_info.exists():
                flags = QtCore.Qt.ItemIsSelectable | MarkedAsArchived

            data = self.model_data()
            data[idx] = {
                QtCore.Qt.DisplayRole: file_info.job,
                QtCore.Qt.EditRole: file_info.job,
                QtCore.Qt.StatusTipRole: file_info.filePath(),
                QtCore.Qt.ToolTipRole: file_info.filePath(),
                QtCore.Qt.SizeHintRole: rowsize,
                #
                common.FlagsRole: flags,
                common.ParentRole: (file_info.server, file_info.job, file_info.root),
                common.DescriptionRole: None,
                common.TodoCountRole: 0,
                common.FileDetailsRole: file_info.size(),
                common.AssetCountRole: file_info.size(),
                #
                common.DefaultThumbnailRole: default_thumbnail_image,
                common.DefaultThumbnailBackgroundRole: default_background_color,
                common.ThumbnailPathRole: None,
                common.ThumbnailRole: default_thumbnail_image,
                common.ThumbnailBackgroundRole: default_background_color,
                #
                common.TypeRole: common.BookmarkItem,
                common.StatusRole: True,
                #
                common.SortByName: file_info.filePath(),
                common.SortByLastModified: file_info.filePath(),
                common.SortBySize: u'{}'.format(file_info.size()),
            }

            # Thumbnail
            index = self.index(idx, 0)
            settings = AssetSettings(index)
            data[idx][common.ThumbnailPathRole] = settings.thumbnail_path()
            image = ImageCache.instance().get(
                data[idx][common.ThumbnailPathRole],
                rowsize.height() - 2)

            if image:
                if not image.isNull():
                    color = ImageCache.instance().get(
                        data[idx][common.ThumbnailPathRole],
                        'BackgroundColor')

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


        self.endResetModel()

    def canDropMimeData(self, data, action, row, column, parent):
        if data.hasUrls():
            return True

    def dropMimeData(self, data, action, row, column, parent):
        index = parent
        if not parent.isValid():
            return
        if not data.hasUrls():
            return

        for url in data.urls():
            if not url.isLocalFile():  # url is coming from the web!
                destination = u'{}/{}'.format(index.data(
                    QtCore.Qt.StatusTipRole), url.fileName())
                downloader = ImageDownloader(url, destination, parent=self)
                downloader.get()
                continue

            source = QtCore.QFileInfo(url.toLocalFile())
            destination = u'{}/{}'.format(index.data(
                QtCore.Qt.StatusTipRole), source.fileName())
            destination = QtCore.QFileInfo(destination)

            if source.filePath() == destination.filePath():
                continue

            if destination.exists():
                res = QtWidgets.QMessageBox(
                    QtWidgets.QMessageBox.Warning,
                    u'File already exist',
                    u'{} already exists in the folder. Are you sure you want to override it with the new file?.'.format(
                        destination.fileName()),
                    QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
                    parent=self
                ).exec_()
                if res == QtWidgets.QMessageBox.Cancel:
                    break  # Cancels the operation
                if res == QtWidgets.QMessageBox.Ok:
                    QtCore.QFile.remove(destination.filePath())

            if action == QtCore.Qt.CopyAction:
                QtCore.QFile.copy(source.filePath(), destination.filePath())
                continue
            if action == QtCore.Qt.MoveAction:
                QtCore.QFile.rename(source.filePath(), destination.filePath())
                continue
            # return True
        return True

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction | QtCore.Qt.CopyAction

    def data_key(self):
        """There is no location associated with the asset widget,
        Needed context menu functionality only."""
        return None


class BookmarksWidget(BaseInlineIconWidget):
    """Widget to list all saved ``Bookmarks``."""

    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)
        self.setDragDropOverwriteMode(False)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

        self.setWindowTitle(u'Bookmarks')
        self.setItemDelegate(BookmarksWidgetDelegate(parent=self))
        self.context_menu_cls = BookmarksWidgetContextMenu

        self.set_model(BookmarksModel(parent=self))

    def eventFilter(self, widget, event):
        super(BookmarksWidget, self).eventFilter(widget, event)
        if widget is not self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            # Let's paint the icon of the current mode
            painter = QtGui.QPainter()
            painter.begin(self)
            pixmap = ImageCache.get_rsc_pixmap(
                'bookmark', QtGui.QColor(0, 0, 0, 10), 128)
            rect = pixmap.rect()
            rect.moveCenter(self.rect().center())
            painter.drawPixmap(rect, pixmap, pixmap.rect())
            painter.end()
            return True
        return False

    def inline_icons_count(self):
        return 5

    def save_activated(self, index):
        """Saves the activated index to ``LocalSettings``."""
        server, job, root = index.data(common.ParentRole)
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

        self.model().sourceModel().modelDataResetRequested.emit()

    def show_add_bookmark_widget(self):
        """Opens a dialog to add a new project to the list of saved locations."""
        widget = AddBookmarksWidget(parent=self)
        widget.show()
        if self.parent():
            pos = self.parent().rect().center()
            pos = self.parent().mapToGlobal(pos)
            widget.move(
                pos.x() - (widget.width() / 2.0),
                pos.y() - (widget.height() / 2.0),
            )

    def mouseDoubleClickEvent(self, event):
        """When the bookmark item is double-clicked the the item will be actiaved."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
        if index.flags() & MarkedAsArchived:
            return

        rect = self.visualRect(index)

        thumbnail_rect = QtCore.QRect(rect)
        thumbnail_rect.setWidth(rect.height())
        thumbnail_rect.moveLeft(common.INDICATOR_WIDTH)

        font = QtGui.QFont(common.PrimaryFont)
        metrics = QtGui.QFontMetrics(font)

        rect.setLeft(
            common.INDICATOR_WIDTH
            + rect.height()
            + common.MARGIN - 2
        )
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(common.INLINE_ICON_SIZE)
        rect.moveTop(rect.top() - (rect.height() / 2.0))

        text = index.data(QtCore.Qt.DisplayRole)
        text = re.sub(r'[\W\d\_]+', '', text)
        text = u'  {}  |  {}  '.format(
            text, index.data(common.ParentRole)[-1].upper())

        width = metrics.width(text)
        rect.moveLeft(rect.left() + width)

        source_index = self.model().mapToSource(index)
        if rect.contains(event.pos()):
            widget = editors.DescriptionEditorWidget(source_index, parent=self)
            widget.show()
            return
        elif thumbnail_rect.contains(event.pos()):
            ImageCache.instance().pick(source_index)
            return
        if not index.data(common.AssetCountRole):
            return common.reveal(index.data(QtCore.Qt.StatusTipRole))

        self.activate(self.selectionModel().currentIndex())


class ComboBoxItemDelegate(BaseDelegate):
    """Delegate used to render simple list items."""

    def __init__(self, parent=None):
        super(ComboBoxItemDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        """The main paint method."""
        args = self._get_paint_args(painter, option, index)
        self.paint_background(*args)
        self.paint_name(*args)

    @paintmethod
    def paint_background(self, *args):
        painter, option, index, selected, _, _, _, _ = args
        rect = QtCore.QRect(option.rect)
        if selected:
            painter.setBrush(common.BACKGROUND_SELECTED)
        else:
            painter.setBrush(common.BACKGROUND)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(rect)

    @paintmethod
    def paint_name(self, *args):
        """Paints the DisplayRole of the items."""
        painter, option, index, selected, _, _, _, _ = args
        disabled = (index.flags() == QtCore.Qt.NoItemFlags)

        font = QtGui.QFont(common.PrimaryFont)
        painter.setFont(font)

        rect = QtCore.QRect(option.rect)
        rect.setLeft(common.MARGIN)
        rect.setRight(option.rect.right())

        if disabled:
            color = self.get_state_color(option, index, common.TEXT_DISABLED)
        else:
            color = self.get_state_color(option, index, common.TEXT)

        text = index.data(QtCore.Qt.DisplayRole)
        text = re.sub(r'[\W\d\_]+', u' ', text.upper())

        if disabled:
            text = u'{}  |  Unavailable'.format(
                index.data(QtCore.Qt.DisplayRole))
        common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)

    def sizeHint(self, option, index):
        return QtCore.QSize(self.parent().view().width(), common.ROW_HEIGHT * 0.66)
