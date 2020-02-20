# -*- coding: utf-8 -*-
"""``bookmarkswidget.py`` defines the main objects needed for interacting with
bookmarks. This includes the utility classes for getting bookmark status and to
allow dropping files and urls on the view.

"""
import json
import base64
from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser.bookmark_db as bookmark_db
import gwbrowser.gwscandir as gwscandir
from gwbrowser.imagecache import ImageCache
import gwbrowser.common as common
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.baselistwidget import BaseInlineIconWidget
from gwbrowser.baselistwidget import BaseModel
from gwbrowser.baselistwidget import initdata
import gwbrowser.settings as settings_
from gwbrowser.settings import AssetSettings
import gwbrowser.delegate as delegate
from gwbrowser.delegate import BookmarksWidgetDelegate


def count_assets(path):
    """Counts number of assets found inside `path`.

    Args:
        path (unicode): A path to a directory.

    Returns:
        int: The number of assets found.

    """
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
        def dflags():
            """The default flags to apply to the item."""
            return (
                QtCore.Qt.ItemNeverHasChildren |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable)

        self._data[self.data_key()] = {
            common.FileItem: {}, common.SequenceItem: {}}

        rowsize = QtCore.QSize(0, common.BOOKMARK_ROW_HEIGHT)
        _height = common.BOOKMARK_ROW_HEIGHT - common.ROW_SEPARATOR
        active_paths = settings_.local_settings.verify_paths()

        favourites = settings_.local_settings.favourites()
        sfavourites = set(favourites)

        bookmarks = settings_.local_settings.value(u'bookmarks')
        bookmarks = bookmarks if bookmarks else {}


        for k, v in bookmarks.iteritems():
            file_info = QtCore.QFileInfo(k)
            exists = file_info.exists()

            if exists:
                flags = dflags()
                count = count_assets(k)
                placeholder_image = ImageCache.get_rsc_pixmap(
                    u'bookmark_sm', common.ADD, _height)
                default_thumbnail_image = ImageCache.get_rsc_pixmap(
                    u'bookmark_sm', common.ADD, _height)
                default_background_color = common.SEPARATOR
            else:
                count = 0
                flags = dflags() | common.MarkedAsArchived

                placeholder_image = ImageCache.get_rsc_pixmap(
                    u'remove', common.REMOVE, _height)
                default_thumbnail_image = ImageCache.get_rsc_pixmap(
                    u'remove', common.REMOVE, _height)
                default_background_color = common.SEPARATOR

            filepath = file_info.filePath().lower()

            # Active Flag
            if all((
                v[u'server'] == active_paths[u'server'],
                v[u'job'] == active_paths[u'job'],
                v[u'bookmark_folder'] == active_paths[u'root']
            )):
                flags = flags | common.MarkedAsActive
            # Favourite Flag
            if filepath in favourites:
                flags = flags | common.MarkedAsFavourite

            data = self.model_data()
            idx = len(data)

            text = u'{} | {}'.format(v[u'job'], v[u'bookmark_folder'])

            data[idx] = {
                QtCore.Qt.DisplayRole: text,
                QtCore.Qt.EditRole: text,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.ToolTipRole: filepath,
                QtCore.Qt.SizeHintRole: rowsize,
                #
                common.EntryRole: [],
                common.FlagsRole: flags,
                common.ParentPathRole: (v[u'server'], v[u'job'], v[u'bookmark_folder']),
                common.DescriptionRole: None,
                common.TodoCountRole: 0,
                common.FileDetailsRole: count,
                common.SequenceRole: None,
                common.EntryRole: [],
                common.FileInfoLoaded: True,
                common.StartpathRole: None,
                common.EndpathRole: None,
                common.AssetCountRole: file_info.size(),
                #
                common.DefaultThumbnailRole: placeholder_image,
                common.DefaultThumbnailBackgroundRole: default_background_color,
                common.ThumbnailPathRole: None,
                common.ThumbnailRole: default_thumbnail_image,
                common.ThumbnailBackgroundRole: default_background_color,
                #
                common.TypeRole: common.FileItem,
                common.FileInfoLoaded: True,
                #
                common.SortByName: common.namekey(filepath),
                common.SortByLastModified: common.namekey(filepath),
                common.SortBySize: count,
            }

            index = self.index(idx, 0)
            db = bookmark_db.get_db(index)
            with db.transactions():
                # Item flags
                flags = data[idx][common.FlagsRole]
                v = db.value(data[idx][QtCore.Qt.StatusTipRole], u'flags')
                flags = flags | v if v is not None else flags
                data[idx][common.FlagsRole] = flags

                # Thumbnail
                data[idx][common.ThumbnailPathRole] = db.thumbnail_path(data[idx][QtCore.Qt.StatusTipRole])
                image = ImageCache.get(
                    data[idx][common.ThumbnailPathRole], _height, overwrite=False)
                if image:
                    if not image.isNull():
                        color = ImageCache.get(
                            data[idx][common.ThumbnailPathRole],
                            u'BackgroundColor')
                        data[idx][common.ThumbnailRole] = image
                        data[idx][common.ThumbnailBackgroundRole] = color

                # Todos are a little more convoluted - the todo count refers to
                # all the current outstanding todos af all assets, including
                # the bookmark itself
                n = 0
                for v in db.values(u'notes').itervalues():
                    if not v:
                        continue
                    if not v['notes']:
                        continue
                    try:
                        v = base64.b64decode(v['notes'])
                        d = json.loads(v)
                        n += len([k for k in d if not d[k][u'checked'] and d[k][u'text']])
                    except (ValueError, TypeError):
                        continue

                data[idx][common.TodoCountRole] = n

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

        import gwbrowser.managebookmarks as managebookmarks

        # Adding the bookmark manager widget
        widget = QtWidgets.QScrollArea(parent=self)
        widget.setWidgetResizable(True)
        manage_widget = managebookmarks.ManageBookmarksWidget(parent=self)
        widget.setWidget(manage_widget)
        self.manage_bookmarks = widget
        self.manage_bookmarks.hide()
        self.parent().resized.connect(
            lambda x: self.manage_bookmarks.setGeometry(self.viewport().geometry()))
        widget.widget().hide_button.clicked.connect(self.manage_bookmarks.hide)

        @QtCore.Slot(unicode)
        def _update(bookmark):
            self.model().sourceModel().blockSignals(True)
            self.model().sourceModel().__initdata__()
            self.model().invalidate()
            self.model().sourceModel().blockSignals(False)
        manage_widget.bookmark_list.bookmarkAdded.connect(_update)
        manage_widget.bookmark_list.bookmarkRemoved.connect(_update)


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

    def showEvent(self, event):
        self.manage_bookmarks.resize(self.viewport().geometry().size())
        super(BookmarksWidget, self).showEvent(event)

    def inline_icons_count(self):
        """The number of row-icons an item has."""
        if self.buttons_hidden():
            return 0
        return 5

    def add_asset(self):
        import gwbrowser.addassetwidget as addassetwidget

        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        bookmark = index.data(common.ParentPathRole)
        bookmark = u'/'.join(bookmark)

        @QtCore.Slot(unicode)
        def select(name):
            self.parent().parent().listcontrolwidget.listChanged.emit(1)
            view = self.parent().widget(1)
            view.model().sourceModel().modelDataResetRequested.emit()
            for n in xrange(view.model().rowCount()):
                index = view.model().index(n, 0)
                file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
                if file_info.fileName().lower() == name.lower():
                    view.selectionModel().setCurrentIndex(
                        index, QtCore.QItemSelectionModel.ClearAndSelect)
                    view.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
                    break

        widget = addassetwidget.AddAssetWidget(bookmark, parent=self)
        widget.templates_widget.templateCreated.connect(select)
        widget.setGeometry(self.viewport().geometry())
        pos = self.geometry().topLeft()
        pos = self.mapToGlobal(pos)
        widget.move(pos)
        widget.exec_()


        # except:
        #     raise
        # finally:
        #     self.disabled_overlay_widget.hide()

    @QtCore.Slot(QtCore.QModelIndex)
    def save_activated(self, index):
        """Saves the activated index to ``LocalSettings``."""
        server, job, root = index.data(common.ParentPathRole)
        settings_.local_settings.setValue(u'activepath/server', server)
        settings_.local_settings.setValue(u'activepath/job', job)
        settings_.local_settings.setValue(u'activepath/root', root)
        settings_.local_settings.verify_paths()  # Resetting invalid paths

    def unset_activated(self):
        """Saves the activated index to ``LocalSettings``."""
        server, job, root = None, None, None
        settings_.local_settings.setValue(u'activepath/server', server)
        settings_.local_settings.setValue(u'activepath/job', job)
        settings_.local_settings.setValue(u'activepath/root', root)
        settings_.local_settings.verify_paths()  # Resetting invalid paths

    # def toggle_item_flag(self, index, flag, state=None):
    #     """Bookmarks cannot be archived but they're automatically removed from
    #     from the ``local_settings``."""
    #
    #     self.reset_multitoggle()
    #     res = QtWidgets.QMessageBox(
    #         QtWidgets.QMessageBox.NoIcon,
    #         u'Remove bookmark?',
    #         u'Do you want to remove this bookmark?\nDon\'t worry, files won\'t be affected.',
    #         QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
    #         parent=self
    #     ).exec_()
    #
    #     if res == QtWidgets.QMessageBox.Cancel:
    #         return
    #
    #     if not index:
    #         index = self.selectionModel().currentIndex()
    #         index = self.model().mapToSource(index)
    #     if not index.isValid():
    #         return
    #
    #     # Removing the bookmark
    #     k = index.data(QtCore.Qt.StatusTipRole)
    #     d = settings_.local_settings.value(u'bookmarks')
    #     if k.lower() in d:
    #         del d[k.lower()]
    #
    #     settings_.local_settings.setValue(u'bookmarks', d)
    #     settings_.local_settings.sync()
    #
    #     if index == self.model().sourceModel().active_index():
    #         self.unset_activated()
    #         self.model().sourceModel().modelDataResetRequested.emit()
    #         return
    #
    #     self.model().sourceModel().blockSignals(True)
    #     self.model().sourceModel().__initdata__()
    #     self.model().invalidate()
    #     self.model().sourceModel().blockSignals(False)

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
