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
        widget = AddBookmarkWidget(parent=self)
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


class AddBookmarkWidget(QtWidgets.QWidget):
    """Defines a widget used add a new ``Bookmark``.
    The final Bookmark path is made up of ``AddBookmarkWidget.server``,
    ``AddBookmarkWidget.job`` and ``AddBookmarkWidget.root``

    Attributes:
        server (str):   The path to the server. `None` if invalid.
        job (str):      The name of the job folder. `None` if invalid.
        root (str):     A relative path to the folder where the assets are located. `None` if invalid.

    """

    def __init__(self, parent=None):
        super(AddBookmarkWidget, self).__init__(parent=parent)
        self._root = None  # The `root` folder
        self._path = None

        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_widget_pos = None

        self._createUI()
        common.set_custom_stylesheet(self)
        self.setWindowTitle(u'GWBrowser: Add bookmark')
        self.setMouseTracking(True)
        self.installEventFilter(self)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Window)

        self._connectSignals()
        self._set_initial_values()

    def get_bookmark(self):
        """Querries the selection and picks made in the widget and return a `dict` object.

        Returns:
            dict: A dictionary object containing the selected bookmark.

        """
        server = self.pick_server_widget.currentData(common.DescriptionRole)
        job = self.pick_job_widget.currentData(common.DescriptionRole)
        root = self._root
        key = u'{}/{}/{}'.format(server, job, root)
        return {key: {u'server': server, u'job': job, u'root': root}}

    def _createUI(self):
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(
            common.MARGIN,
            common.MARGIN,
            common.MARGIN,
            common.MARGIN
        )

        # top label
        label = QtWidgets.QLabel()

        text = u'<p style="font-size: {s}pt; color: rgba({},{},{},{}); font-family: "{f}"">Add bookmark</p>'
        text = text.format(
            *common.TEXT.getRgb(),
            s=common.psize(common.LARGE_FONT_SIZE),
            f=common.PrimaryFont.family()
        )
        label.setText(text)

        label.setAlignment(QtCore.Qt.AlignJustify)
        label.setWordWrap(True)
        self.layout().addWidget(label, 0)

        self.pathsettings = QtWidgets.QWidget()
        self.pathsettings.setMinimumWidth(300)
        QtWidgets.QVBoxLayout(self.pathsettings)
        self.pathsettings.layout().setContentsMargins(0, 0, 0, 0)
        self.pathsettings.layout().setSpacing(common.INDICATOR_WIDTH)

        # Server
        self.pick_server_widget = QtWidgets.QComboBox()
        view = QtWidgets.QListWidget()  # Setting a custom view here
        self.pick_server_widget.setModel(view.model())
        self.pick_server_widget.setView(view)
        self.pick_server_widget.setDuplicatesEnabled(False)
        self.pick_server_widget.setItemDelegate(
            ComboBoxItemDelegate(self.pick_server_widget))

        self.pick_job_widget = QtWidgets.QComboBox()
        view = QtWidgets.QListWidget()  # Setting a custom view here
        self.pick_job_widget.setModel(view.model())
        self.pick_job_widget.setView(view)
        self.pick_job_widget.setDuplicatesEnabled(False)
        self.pick_job_widget.setItemDelegate(
            ComboBoxItemDelegate(self.pick_job_widget))

        self.pick_root_widget = QtWidgets.QPushButton(u'Pick bookmark folder')

        row = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row)

        self.ok_button = QtWidgets.QPushButton(u'Add bookmark')
        self.ok_button.setDisabled(True)
        self.cancel_button = QtWidgets.QPushButton(u'Cancel')

        row.layout().addWidget(self.ok_button, 1)
        row.layout().addWidget(self.cancel_button, 1)

        # Adding it all together
        main_widget = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(main_widget)

        self.label = QtWidgets.QLabel()
        label.setAlignment(QtCore.Qt.AlignJustify)
        label.setWordWrap(True)

        pixmap = ImageCache.get_rsc_pixmap(
            u'bookmark', common.SECONDARY_TEXT, 128)
        self.label.setPixmap(pixmap)
        main_widget.layout().addWidget(self.label)
        main_widget.layout().addSpacing(common.MARGIN)
        main_widget.layout().addWidget(self.pathsettings, 1)
        self.layout().addWidget(main_widget)

        # Server Header
        self.layout().addWidget(row)
        text = u'<p style="font-size: {s}pt; color: rgba({},{},{},{}); font-family: "{f}"">Server</p>'
        text = text.format(
            *common.TEXT.getRgb(),
            s=common.psize(common.MEDIUM_FONT_SIZE),
            f=common.PrimaryFont.family()
        )
        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignJustify)
        label.setWordWrap(True)
        self.pathsettings.layout().addWidget(label)

        # Server description
        text = u'<p style="font-size: {s}pt; color: rgba({},{},{},{}); font-family: "{f}"">Select the server the bookmark is located at:</p>'
        text = text.format(
            *common.BACKGROUND.getRgb(),
            s=common.psize(common.SMALL_FONT_SIZE),
            f=common.SecondaryFont.family()
        )
        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignJustify)
        label.setWordWrap(True)
        self.pathsettings.layout().addWidget(label)

        self.pathsettings.layout().addWidget(self.pick_server_widget)
        self.pathsettings.layout().addSpacing(common.INDICATOR_WIDTH * 2)

        # Job header
        text = u'<p style="font-size: {s}pt; color: rgba({},{},{},{}); font-family: "{f}"">Job</p>'
        text = text.format(
            *common.TEXT.getRgb(),
            s=common.psize(common.MEDIUM_FONT_SIZE),
            f=common.PrimaryFont.family()
        )
        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignJustify)
        self.pathsettings.layout().addWidget(label)

        # Job description
        text = u'<p style="font-size: {s}pt; color: rgba({},{},{},{}); font-family: "{f}"">Select the name of the job:</p>'
        text = text.format(
            *common.BACKGROUND.getRgb(),
            s=common.psize(common.SMALL_FONT_SIZE),
            f=common.SecondaryFont.family()
        )
        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignJustify)

        self.pathsettings.layout().addWidget(label)
        self.pathsettings.layout().addWidget(self.pick_job_widget)
        self.pathsettings.layout().addSpacing(common.INDICATOR_WIDTH * 2)

        # Bookmarks header
        text = u'<p style="font-size: {s}pt; color: rgba({},{},{},{}); font-family: "{f}"">Bookmark folder</span>'
        text = text.format(
            *common.TEXT.getRgb(),
            s=common.psize(common.MEDIUM_FONT_SIZE),
            f=common.PrimaryFont.family()
        )
        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignJustify)
        self.pathsettings.layout().addWidget(label)

        # Bookmarks description

        text = u'<p style="font-size: {s}pt; color: rgba({},{},{},{}); font-family: "{f}"">Select the folder inside the job to be bookmarked.<br/><br/>'
        text += 'Any folder inside the job can be bookmarked but only folders containing <span style="color: silver;">assets</span> are considered valid:</p>'
        text = text.format(
            *common.BACKGROUND.getRgb(),
            s=common.psize(common.SMALL_FONT_SIZE),
            f=common.SecondaryFont.family()
        )
        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignJustify)
        self.pathsettings.layout().addWidget(label)

        self.pathsettings.layout().addWidget(self.pick_root_widget)

    def _connectSignals(self):
        self.pick_server_widget.currentIndexChanged.connect(
            self.server_changed)
        self.pick_job_widget.currentIndexChanged.connect(self.job_changed)
        self.pick_root_widget.pressed.connect(self.pick_root)

        self.cancel_button.pressed.connect(self.close)
        self.ok_button.pressed.connect(self.action)

    @QtCore.Slot()
    def action(self):
        """The action to execute when the `Ok` button has been pressed."""
        bookmark = self.get_bookmark()
        if not all(bookmark[k] for k in bookmark):
            return
        key = next((k for k in bookmark), None)

        # Let's double-check the integrity of the choice.
        path = u''
        sequence = (bookmark[key][u'server'], bookmark[key]
                    [u'job'], bookmark[key][u'root'])
        for value in sequence:
            path += u'{}/'.format(value)
            dir_ = QtCore.QDir(path)
            if dir_.exists():
                continue
            return QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Warning,
                u'Could not add bookmark',
                u'The selected folder could not be found:\n{}/{}/{}'.format(
                    bookmark[key][u'server'],
                    bookmark[key][u'job'],
                    bookmark[key][u'root'],
                ),
                QtWidgets.QMessageBox.Ok,
                parent=self
            ).exec_()
        path = path.rstrip(u'/')
        bookmarks = local_settings.value(u'bookmarks')
        if not bookmarks:
            local_settings.setValue(u'bookmarks', bookmark)
        else:
            bookmarks[key] = bookmark[key]
            local_settings.setValue(u'bookmarks', bookmarks)

        self._path = path
        self.parent().model().sourceModel().modelReset.connect(self.select_item)
        self.parent().model().sourceModel().modelReset.connect(self.close)
        self.parent().model().sourceModel().modelReset.connect(self.deleteLater)

        self.parent().model().sourceModel().beginResetModel()
        self.parent().model().sourceModel().__initdata__()

    def select_item(self):
        """Selects the item based on the given path."""
        if not self.parent():
            return
        for n in xrange(self.parent().model().rowCount()):
            index = self.parent().model().index(n, 0)
            if index.data(QtCore.Qt.StatusTipRole) == self._path:
                self.parent().selectionModel().setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect
                )
                self.parent().scrollTo(index)
                return

    def _add_servers(self):
        self.pick_server_widget.clear()

        for server in common.SERVERS:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, server[u'nickname'])
            item.setData(QtCore.Qt.EditRole, server[u'nickname'])
            item.setData(QtCore.Qt.StatusTipRole,
                         QtCore.QFileInfo(server[u'path']).filePath())
            item.setData(QtCore.Qt.ToolTipRole,
                         u'{}\n{}'.format(server[u'nickname'], server[u'path']))
            item.setData(common.DescriptionRole, server[u'path'])
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                200, common.ROW_BUTTONS_HEIGHT))

            self.pick_server_widget.view().addItem(item)

            file_info = QtCore.QFileInfo(item.data(QtCore.Qt.StatusTipRole))
            if not file_info.exists():
                item.setFlags(QtCore.Qt.NoItemFlags)

            item.setData(common.FlagsRole, item.flags())

    def add_jobs(self, qdir):
        """Querries the given folder and return all readable folder within.

        Args:
            qdir (type): Description of parameter `qdir`.

        Returns:
            type: Description of returned object.

        """

        qdir.setFilter(
            QtCore.QDir.NoDotAndDotDot |
            QtCore.QDir.Dirs |
            QtCore.QDir.NoSymLinks
        )

        self.pick_job_widget.clear()

        for file_info in qdir.entryInfoList():
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, file_info.fileName())
            item.setData(QtCore.Qt.EditRole, file_info.fileName())
            item.setData(QtCore.Qt.StatusTipRole, file_info.filePath())
            item.setData(QtCore.Qt.ToolTipRole, file_info.filePath())
            item.setData(common.DescriptionRole, file_info.fileName())
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                common.WIDTH, common.ROW_BUTTONS_HEIGHT))

            if not file_info.isReadable():
                item.setFlags(QtCore.Qt.NoItemFlags)
            item.setData(common.FlagsRole, item.flags())
            self.pick_job_widget.view().addItem(item)

    @QtCore.Slot()
    def pick_root(self):
        """Method to select a the root folder of the assets. Called by the Assets push button."""
        self._root = None

        dialog = QtWidgets.QFileDialog()
        dialog.setViewMode(QtWidgets.QFileDialog.Detail)

        path = self.pick_job_widget.currentData(QtCore.Qt.StatusTipRole)
        file_info = QtCore.QFileInfo(path)

        path = dialog.getExistingDirectory(
            self,
            u'Pick the location of the assets folder',
            file_info.filePath(),
            QtWidgets.QFileDialog.ShowDirsOnly |
            QtWidgets.QFileDialog.DontResolveSymlinks |
            QtWidgets.QFileDialog.DontUseCustomDirectoryIcons |
            QtWidgets.QFileDialog.HideNameFilterDetails |
            QtWidgets.QFileDialog.ReadOnly
        )
        if not path:
            self.ok_button.setDisabled(True)
            self.pick_root_widget.setText(u'Select folder')
            self._root = None
            return

        self.ok_button.setDisabled(False)
        count = BookmarkInfo.count_assets(path)

        # Removing the server and job name from the selection
        path = path.replace(self.pick_job_widget.currentData(
            QtCore.Qt.StatusTipRole), u'')
        path = path.lstrip(u'/').rstrip(u'/')

        # Setting the internal root variable
        self._root = path

        if count:
            stylesheet = u'color: rgba({},{},{},{});'.format(*common.TEXT.getRgb())
            stylesheet += u'background-color: "green";'
            self.pick_root_widget.setStyleSheet(stylesheet)
        else:
            stylesheet = u'color: rgba({},{},{},{});'.format(
                *common.TEXT.getRgb())
            self.pick_root_widget.setStyleSheet(stylesheet)

        path = u'{}:  {} assets'.format(path, count)
        self.pick_root_widget.setText(path)

    @QtCore.Slot(int)
    def job_changed(self, idx):
        """Triggered when the pick_job_widget selection changes."""
        self._root = None
        stylesheet = u'color: rgba({},{},{},{});'.format(*common.TEXT.getRgb())
        stylesheet += u'background-color: rgba({},{},{},{});'.format(
            *common.SECONDARY_TEXT.getRgb())

        self.pick_root_widget.setStyleSheet(stylesheet)
        self.pick_root_widget.setText(u'Pick bookmark folder')

    @QtCore.Slot(int)
    def server_changed(self, idx):
        """Triggered when the pick_server_widget selection changes."""
        if idx < 0:
            self.pick_job_widget.clear()
            return

        item = self.pick_server_widget.view().item(idx)
        qdir = QtCore.QDir(item.data(QtCore.Qt.StatusTipRole))
        self.add_jobs(qdir)

    def _set_initial_values(self):
        """Sets the initial values in the widget."""
        self._add_servers()
        local_paths = Active.paths()

        # Select the currently active server
        if local_paths[u'server']:
            idx = self.pick_server_widget.findData(
                local_paths[u'server'],
                role=common.DescriptionRole,
                flags=QtCore.Qt.MatchFixedString
            )
            self.pick_server_widget.setCurrentIndex(idx)

        # Select the currently active server
        if local_paths[u'job']:
            idx = self.pick_job_widget.findData(
                local_paths[u'job'],
                role=common.DescriptionRole,
                flags=QtCore.Qt.MatchFixedString
            )
            self.pick_job_widget.setCurrentIndex(idx)

    def mousePressEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.move_in_progress = True
        self.move_start_event_pos = event.pos()
        self.move_start_widget_pos = self.mapToGlobal(self.rect().topLeft())

    def mouseMoveEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.buttons() == QtCore.Qt.NoButton:
            return
        if self.move_start_widget_pos:
            offset = (event.pos() - self.move_start_event_pos)
            self.move(self.mapToGlobal(self.rect().topLeft()) + offset)

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_widget_pos = None
