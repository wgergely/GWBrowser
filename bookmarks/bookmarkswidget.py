# -*- coding: utf-8 -*-
"""``bookmarkswidget.py``

"""
import json
import base64
import weakref
import time
from PySide2 import QtWidgets, QtGui, QtCore

import bookmarks.bookmark_db as bookmark_db
import bookmarks.images as images
import bookmarks.common as common
from bookmarks.basecontextmenu import BaseContextMenu
from bookmarks.baselistwidget import BaseInlineIconWidget
from bookmarks.baselistwidget import BaseModel
from bookmarks.baselistwidget import initdata
import bookmarks.settings as settings
import bookmarks.delegate as delegate
from bookmarks.delegate import BookmarksWidgetDelegate


class BookmarksWidgetContextMenu(BaseContextMenu):
    """Context menu associated with the BookmarksWidget.

    Methods:
        refresh: Refreshes the collector and repopulates the widget.

    """

    def __init__(self, index, parent=None):
        super(BookmarksWidgetContextMenu, self).__init__(index, parent=parent)
        # Adding persistent actions

        self.add_manage_bookmarks_menu()
        self.add_separator()

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
    """

    ROW_SIZE = QtCore.QSize(120, common.BOOKMARK_ROW_HEIGHT)

    def __init__(self, parent=None):
        super(BookmarksModel, self).__init__(parent=parent)
        self.parent_path = (u'.',)

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
                QtCore.Qt.ItemIsDropEnabled |
                QtCore.Qt.ItemNeverHasChildren |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable)

        dkey = self.data_key()

        _height = common.BOOKMARK_ROW_HEIGHT - common.ROW_SEPARATOR

        active_paths = settings.local_settings.verify_paths()
        favourites = settings.local_settings.favourites()
        bookmarks = settings.local_settings.value(u'bookmarks')
        bookmarks = bookmarks if bookmarks else {}

        for k, v in bookmarks.iteritems():
            if not all(v.values()):
                continue

            file_info = QtCore.QFileInfo(k)
            exists = file_info.exists()

            if exists:
                flags = dflags()
                placeholder_image = images.ImageCache.get_rsc_pixmap(
                    u'bookmark_sm', common.ADD, _height)
                default_thumbnail_image = images.ImageCache.get_rsc_pixmap(
                    u'bookmark_sm', common.ADD, _height)
                default_background_color = common.SEPARATOR
            else:
                flags = dflags() | common.MarkedAsArchived

                placeholder_image = images.ImageCache.get_rsc_pixmap(
                    u'remove', common.REMOVE, _height)
                default_thumbnail_image = images.ImageCache.get_rsc_pixmap(
                    u'remove', common.REMOVE, _height)
                default_background_color = common.SEPARATOR

            filepath = file_info.filePath().lower()

            # Active Flag
            if all((
                v[u'server'] == active_paths[u'server'],
                v[u'job'] == active_paths[u'job'],
                v[u'root'] == active_paths[u'root']
            )):
                flags = flags | common.MarkedAsActive
            # Favourite Flag
            if filepath in favourites:
                flags = flags | common.MarkedAsFavourite

            text = u'{}  |  {}'.format(
                v[u'job'], v[u'root'])

            data = self.INTERNAL_MODEL_DATA[dkey][common.FileItem]
            idx = len(data)

            data[idx] = common.DataDict({
                QtCore.Qt.DisplayRole: text,
                QtCore.Qt.EditRole: text,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.ToolTipRole: filepath,
                QtCore.Qt.SizeHintRole: self.ROW_SIZE,
                #
                common.EntryRole: [],
                common.FlagsRole: flags,
                common.ParentPathRole: (v[u'server'], v[u'job'], v[u'root']),
                common.DescriptionRole: None,
                common.TodoCountRole: 0,
                common.FileDetailsRole: None,
                common.SequenceRole: None,
                common.EntryRole: [],
                common.FileInfoLoaded: True,
                common.StartpathRole: None,
                common.EndpathRole: None,
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
                common.SortByLastModified: file_info.lastModified().toMSecsSinceEpoch(),
                common.SortBySize: file_info.size(),
                #
                common.IdRole: idx
            })

            db = None
            n = 0
            while db is None:
                db = bookmark_db.get_db(
                    QtCore.QModelIndex(),
                    server=v[u'server'],
                    job=v[u'job'],
                    root=v[u'root'],
                )
                if db is None:
                    n += 1
                    time.sleep(0.1)
                if n > 10:
                    break

            if db is None:
                common.Log.error(u'Error getting the database')
                continue

            with db.transactions():
                # Item flags
                flags = data[idx][common.FlagsRole]
                v = db.value(data[idx][QtCore.Qt.StatusTipRole], u'flags')
                flags = flags | v if v is not None else flags
                data[idx][common.FlagsRole] = flags

                # Thumbnail
                data[idx][common.ThumbnailPathRole] = db.thumbnail_path(
                    data[idx][QtCore.Qt.StatusTipRole])
                image = images.ImageCache.get(
                    data[idx][common.ThumbnailPathRole], _height, overwrite=False)
                if image:
                    if not image.isNull():
                        color = images.ImageCache.get(
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
                    if v[u'notes']:
                        try:
                            v = base64.b64decode(v[u'notes'])
                            d = json.loads(v)
                            n += len([k for k in d if not d[k]
                                      [u'checked'] and d[k][u'text']])
                        except (ValueError, TypeError):
                            common.Log.error(u'Error decoding JSON notes')

                data[idx][common.TodoCountRole] = n

        self.activeChanged.emit(self.active_index())

    def __resetdata__(self):
        self.INTERNAL_MODEL_DATA[self.data_key()] = common.DataDict({
            common.FileItem: common.DataDict({}),
            common.SequenceItem: common.DataDict({}),
        })
        self.__initdata__()
        self.endResetModel()

    def data_key(self):
        """Data keys are only implemented on the FilesModel but need to return a
        value for compatibility other functions.

        """
        return u'.'

    def data_type(self):
        """Data keys are only implemented on the FilesModel but need to return a
        value for compatibility other functions.

        """
        return common.FileItem

    def reset_thumbnails(self):
        pass

    def initialise_threads(self):
        pass

    def init_generate_thumbnails_enabled(self):
        self._generate_thumbnails_enabled = False

    def generate_thumbnails_enabled(self):
        return False

    def reset_file_info_loaded(self):
        pass

    def reset_thread_worker_queues(self):
        pass


class BookmarksWidget(BaseInlineIconWidget):
    """The view used to display the contents of a ``BookmarksModel`` instance."""
    SourceModel = BookmarksModel
    Delegate = BookmarksWidgetDelegate
    ContextMenu = BookmarksWidgetContextMenu

    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)
        self.setWindowTitle(u'Bookmarks')

        import bookmarks.managebookmarks as managebookmarks

        self._background_icon = u'bookmark'
        self.manage_bookmarks = managebookmarks.Bookmarks(parent=self)
        self.manage_bookmarks.hide()

        @QtCore.Slot(unicode)
        def _update(bookmark):
            self.model().sourceModel().__resetdata__()

        self.manage_bookmarks.widget().bookmark_list.bookmarkAdded.connect(_update)
        self.manage_bookmarks.widget().bookmark_list.bookmarkRemoved.connect(_update)

        self.resized.connect(self.manage_bookmarks.setGeometry)

    def buttons_hidden(self):
        """Returns the visibility of the inline icon buttons."""
        return False

    def showEvent(self, event):
        self.manage_bookmarks.resize(self.viewport().geometry().size())
        super(BookmarksWidget, self).showEvent(event)

    def inline_icons_count(self):
        """The number of row-icons an item has."""
        if self.buttons_hidden():
            return 0
        return 6

    def show_bookmark_properties_widget(self):
        import bookmarks.bookmark_properties as bookmark_properties
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        widget = bookmark_properties.BookmarkPropertiesWidget(
            index, parent=self)
        self.resized.connect(widget.setGeometry)
        widget.setGeometry(self.viewport().geometry())
        widget.open()

    def show_add_asset_widget(self):
        import bookmarks.addassetwidget as addassetwidget

        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        bookmark = index.data(common.ParentPathRole)
        bookmark = u'/'.join(bookmark)

        @QtCore.Slot(unicode)
        def show_and_select_added_asset(name):
            self.parent().parent().listcontrolwidget.listChanged.emit(1)
            view = self.parent().widget(1)
            view.model().sourceModel().modelDataResetRequested.emit()
            for n in xrange(view.model().rowCount()):
                index = view.model().index(n, 0)
                file_info = QtCore.QFileInfo(
                    index.data(QtCore.Qt.StatusTipRole))
                if file_info.fileName().lower() == name.lower():
                    view.selectionModel().setCurrentIndex(
                        index, QtCore.QItemSelectionModel.ClearAndSelect)
                    view.scrollTo(
                        index, QtWidgets.QAbstractItemView.PositionAtCenter)
                    break

        widget = addassetwidget.AddAssetWidget(bookmark, parent=self)
        widget.templates_widget.templateCreated.connect(
            show_and_select_added_asset)
        self.resized.connect(widget.setGeometry)
        widget.setGeometry(self.viewport().geometry())
        widget.open()

    @QtCore.Slot(QtCore.QModelIndex)
    def save_activated(self, index):
        """Saves the activated index to ``LocalSettings``."""
        if not index.isValid():
            return
        if not index.data(common.ParentPathRole):
            return
        server, job, root = index.data(common.ParentPathRole)
        settings.local_settings.setValue(u'activepath/server', server)
        settings.local_settings.setValue(u'activepath/job', job)
        settings.local_settings.setValue(u'activepath/root', root)
        settings.local_settings.verify_paths()  # Resetting invalid paths

    def unset_activated(self):
        """Saves the activated index to ``LocalSettings``."""
        server, job, root = None, None, None
        settings.local_settings.setValue(u'activepath/server', server)
        settings.local_settings.setValue(u'activepath/job', job)
        settings.local_settings.setValue(u'activepath/root', root)
        settings.local_settings.verify_paths()  # Resetting invalid paths

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

        if rectangles[delegate.AddAssetRect].contains(cursor_position):
            self.show_add_asset_widget()
        elif rectangles[delegate.BookmarkPropertiesRect].contains(cursor_position):
            self.show_bookmark_properties_widget()
        else:
            super(BookmarksWidget, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        self.reset_multitoggle()
        super(BookmarksWidget, self).mouseMoveEvent(event)
        self.reset_multitoggle()

    def toggle_item_flag(self, index, flag, state=None):
        if not index.isValid():
            return

        if flag == common.MarkedAsArchived:
            if hasattr(index.model(), 'sourceModel'):
                source_index = self.model().mapToSource(index)

            model = self.model()
            data = model.sourceModel().model_data()[source_index.row()]
            data[common.FlagsRole] = data[common.FlagsRole] | common.MarkedAsArchived

            # There's no reason to do this but for consistency' sake
            self.update_row(weakref.ref(data))
            #
            self.manage_bookmarks.widget().remove_saved_bookmark(
                *index.data(common.ParentPathRole))
            bookmark_db.remove_db(index)

            if self.model().sourceModel().active_index() == source_index:
                self.unset_activated()

            settings.local_settings.verify_paths()

            return

        super(BookmarksWidget, self).toggle_item_flag(index, flag, state=state)
