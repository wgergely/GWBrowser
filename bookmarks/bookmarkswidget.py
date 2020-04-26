# -*- coding: utf-8 -*-
"""The widget, model and context menu needed for interacting with bookmarks.

Copyright (C) 2020 Gergely Wootsch

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <https://www.gnu.org/licenses/>.

"""
import json
import base64
import weakref
import time
import functools
from PySide2 import QtWidgets, QtGui, QtCore

import bookmarks.log as log
import bookmarks.common as common
import bookmarks.bookmark_db as bookmark_db
import bookmarks.images as images
import bookmarks.threads as threads
import bookmarks._scandir as _scandir
import bookmarks.baselistwidget as baselistwidget
import bookmarks.basecontextmenu as basecontextmenu
import bookmarks.settings as settings
import bookmarks.delegate as delegate


def count_assets(bookmark_path, ASSET_IDENTIFIER):
    n = 0
    for entry in _scandir.scandir(bookmark_path):
        if entry.name.startswith(u'.'):
            continue
        if not entry.is_dir():
            continue

        filepath = entry.path.replace(u'\\', u'/')

        if ASSET_IDENTIFIER:
            identifier = u'{}/{}'.format(
                filepath, ASSET_IDENTIFIER)
            if not QtCore.QFileInfo(identifier).exists():
                continue
        n += 1
    return n


class BookmarksWidgetContextMenu(basecontextmenu.BaseContextMenu):
    """Context menu associated with the BookmarksWidget.

    Methods:
        refresh: Refreshes the collector and repopulates the widget.

    """

    def __init__(self, index, parent=None):
        super(BookmarksWidgetContextMenu, self).__init__(index, parent=parent)
        self.add_manage_bookmarks_menu()
        self.add_separator()
        if index.isValid():
            self.add_mode_toggles_menu()
            self.add_separator()
        self.add_separator()
        self.add_row_size_menu()
        self.add_separator()
        self.add_set_generate_thumbnails_menu()
        if index.isValid():
            self.add_copy_menu()
            self.add_reveal_item_menu()
        self.add_separator()
        self.add_sort_menu()
        self.add_separator()
        self.add_display_toggles_menu()
        self.add_separator()
        self.add_refresh_menu()


class BookmarksModel(baselistwidget.BaseModel):
    """The model used store the data necessary to display bookmarks.

    """
    DEFAULT_ROW_SIZE = QtCore.QSize(1, common.BOOKMARK_ROW_HEIGHT())
    val = settings.local_settings.value(u'widget/bookmarksmodel/rowheight')
    val = val if val else DEFAULT_ROW_SIZE.height()
    val = DEFAULT_ROW_SIZE.height() if val < DEFAULT_ROW_SIZE.height() else val
    ROW_SIZE = QtCore.QSize(1, val)

    queue_type = threads.BookmarkInfoQueue
    thumbnail_queue_type = threads.BookmarkThumbnailQueue

    def __init__(self, has_threads=True, parent=None):
        super(BookmarksModel, self).__init__(
            has_threads=has_threads, parent=parent)
        self.parent_path = (u'.',)

    @baselistwidget.initdata
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

        task_folder = self.task_folder()

        active_paths = settings.local_settings.verify_paths()
        favourites = settings.local_settings.favourites()
        bookmarks = settings.local_settings.value(u'bookmarks')
        bookmarks = bookmarks if bookmarks else {}

        _height = self.ROW_SIZE.height() - common.ROW_SEPARATOR()

        for k, v in bookmarks.iteritems():
            if not all(v.values()):
                continue

            file_info = QtCore.QFileInfo(k)
            exists = file_info.exists()

            if exists:
                flags = dflags()
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'bookmark_sm', common.ADD, _height)
            else:
                flags = dflags() | common.MarkedAsArchived
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'failed', common.REMOVE, _height)
            placeholder_image = pixmap
            default_thumbnail_image = pixmap

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
                v[u'job'],
                v[u'root'],
                # v[u'root'].split(u'/').pop(),
            )

            data = self.INTERNAL_MODEL_DATA[task_folder][common.FileItem]
            idx = len(data)

            data[idx] = common.DataDict({
                QtCore.Qt.DisplayRole: text,
                QtCore.Qt.EditRole: text,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.ToolTipRole: filepath,
                QtCore.Qt.SizeHintRole: self.ROW_SIZE,
                #
                common.TextSegmentRole: self.get_text_segments(text),
                #
                common.EntryRole: [],
                common.FlagsRole: flags,
                common.ParentPathRole: (v[u'server'], v[u'job'], v[u'root']),
                common.DescriptionRole: u'',
                common.TodoCountRole: 0,
                common.FileDetailsRole: None,
                common.SequenceRole: None,
                common.EntryRole: [],
                common.FileInfoLoaded: False,
                common.StartpathRole: None,
                common.EndpathRole: None,
                #
                common.ThumbnailLoaded: False,
                #
                common.TypeRole: common.FileItem,
                #
                common.SortByNameRole: text,
                common.SortByLastModifiedRole: file_info.lastModified().toMSecsSinceEpoch(),
                common.SortBySizeRole: file_info.size(),
                #
                common.AssetCountRole: 0,
                #
                common.IdRole: idx
            })

            db = None
            n = 0
            db = bookmark_db.get_db(
                v[u'server'],
                v[u'job'],
                v[u'root'],
            )
            with db.transactions():
                # Item flags
                flags = data[idx][common.FlagsRole]
                v = db.value(data[idx][QtCore.Qt.StatusTipRole], u'flags')
                flags = flags | v if v is not None else flags
                data[idx][common.FlagsRole] = flags

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
                            log.error(u'Error decoding JSON notes')

                data[idx][common.TodoCountRole] = n
                self.update_description(db, data[idx])

        self.activeChanged.emit(self.active_index())

    def __resetdata__(self):
        self.INTERNAL_MODEL_DATA[self.task_folder()] = common.DataDict({
            common.FileItem: common.DataDict({}),
            common.SequenceItem: common.DataDict({}),
        })
        self.__initdata__()
        self.endResetModel()

    def update_description(self, db, data):
        t = u'properties'
        v = {}

        ASSET_IDENTIFIER = db.value(1, u'identifier', table=t)
        data[common.AssetCountRole] = count_assets(
            data[QtCore.Qt.StatusTipRole], ASSET_IDENTIFIER)

        for _k in bookmark_db.KEYS[t]:
            v[_k] = db.value(1, _k, table=t)

        info = u'{w}{h}{fps}{pre}{start}{duration}'.format(
            w=u'{}'.format(int(v['width'])) if (
                v['width'] and v['height']) else u'',
            h=u'x{}px'.format(int(v['height'])) if (
                v['width'] and v['height']) else u'',
            fps=u'  |  {}fps'.format(
                v['framerate']) if v['framerate'] else u'',
            pre=u'  |  {}'.format(v['prefix']) if v['prefix'] else u'',
            start=u'  |  {}'.format(
                int(v['startframe'])) if v['startframe'] else u'',
            duration=u'-{} ({} frames)'.format(
                int(v['startframe']) + int(v['duration']),
                int(v['duration']) if v['duration'] else u'') if v['duration'] else u''
        )

        c = data[common.AssetCountRole]
        desc = u'{count}{info}'.format(
            count=u'{} assets'.format(c) if c else u'',
            info=u'\n' + info if c else info,
        )
        data[common.DescriptionRole] = desc
        data[QtCore.Qt.ToolTipRole] = desc

    def get_text_segments(self, text):
        """Returns a tuple of text and colour information to be used to mimick
        rich-text like colouring of individual text elements.

        Used by the delegate to represent the job name and root folder.

        """
        if not text:
            return {}

        text = text.strip().strip(u'/').strip(u'\\')
        if not text:
            return {}

        d = {}
        v = text.split(u'|')
        for i, s in enumerate(v):

            if i == 0:
                c = common.FAVOURITE.darker(250)
            else:
                c = common.TEXT

            _v = s.split(u'/')
            for _i, _s in enumerate(_v):
                _s = _s.upper().strip()
                d[len(d)] = (_s, c)
                if _i < (len(_v) - 1):
                    d[len(d)] = (u' / ', common.FAVOURITE.darker(250))
            if i < (len(v) - 1):
                d[len(d)] = (u'   |    ', common.FAVOURITE.darker(250))
        return d


class BookmarksWidget(baselistwidget.ThreadedBaseWidget):
    """The view used to display the contents of a ``BookmarksModel`` instance."""
    SourceModel = BookmarksModel
    Delegate = delegate.BookmarksWidgetDelegate
    ContextMenu = BookmarksWidgetContextMenu

    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)
        self.setWindowTitle(u'Bookmarks')

        import bookmarks.managebookmarks as managebookmarks

        self._background_icon = u'bookmark'
        self.manage_bookmarks = managebookmarks.ManageBookmarks(parent=self)

        @QtCore.Slot(unicode)
        def _update(bookmark):
            self.model().sourceModel().__resetdata__()

        self.manage_bookmarks.bookmarkAdded.connect(_update)
        self.manage_bookmarks.bookmarkRemoved.connect(_update)

    def mousePressEvent(self, event):
        super(BookmarksWidget, self).mousePressEvent(event)
        self.reset_multitoggle()

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return

        cursor_position = self.mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)

        if not index.isValid():
            return
        if index.flags() & common.MarkedAsArchived:
            return

        rect = self.visualRect(index)
        rectangles = delegate.get_rectangles(rect, self.inline_icons_count())

        if rectangles[delegate.AddAssetRect].contains(cursor_position):
            self.show_add_asset_widget()
        elif rectangles[delegate.BookmarkPropertiesRect].contains(cursor_position):
            self.show_bookmark_properties_widget()
        else:
            super(BookmarksWidget, self).mouseReleaseEvent(event)

    def inline_icons_count(self):
        """The number of row-icons an item has."""
        if self.buttons_hidden():
            return 0
        return 6

    def show_bookmark_properties_widget(self):
        def update_description(index, res):
            db = bookmark_db.get_db(
                index.data(common.ParentPathRole)[0],
                index.data(common.ParentPathRole)[1],
                index.data(common.ParentPathRole)[2],
            )
            source_index = self.model().mapToSource(index)
            data = source_index.model().model_data()[source_index.row()]
            self.model().sourceModel().update_description(db, data)

        import bookmarks.bookmark_properties as bookmark_properties
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        widget = bookmark_properties.BookmarkPropertiesWidget(
            index.data(common.ParentPathRole)[0],
            index.data(common.ParentPathRole)[1],
            index.data(common.ParentPathRole)[2],
            parent=self
        )

        self.resized.connect(widget.setGeometry)
        widget.setGeometry(self.viewport().geometry())
        widget.open()

        widget.finished.connect(functools.partial(update_description, index))

    def show_add_asset_widget(self):
        @QtCore.Slot(unicode)
        def show_and_select_added_asset(name):
            """If adding items to the active bookmark, we will go ahead and show
            the added item.

            """
            view = self.parent().widget(1)
            if self.selectionModel().currentIndex() != view.model().sourceModel().active_index():
                return

            view.model().sourceModel().modelDataResetRequested.emit()
            self.parent().parent().listcontrolwidget.listChanged.emit(1)

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

        import bookmarks.addassetwidget as addassetwidget

        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        widget = addassetwidget.AddAssetWidget(
            index.data(common.ParentPathRole)[0],
            index.data(common.ParentPathRole)[1],
            index.data(common.ParentPathRole)[2]
        )
        widget.templates_widget.templateCreated.connect(
            show_and_select_added_asset)
        widget.show()

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

    def toggle_item_flag(self, index, flag, state=None):
        if flag == common.MarkedAsArchived:
            if hasattr(index.model(), 'sourceModel'):
                index = self.model().mapToSource(index)

            model = self.model()
            data = model.sourceModel().model_data()[index.row()]

            data[common.FlagsRole] = data[common.FlagsRole] | common.MarkedAsArchived
            self.update_row(weakref.ref(data))

            self.manage_bookmarks.scrollarea.widget().remove_saved_bookmark(
                *index.data(common.ParentPathRole))

            bookmark_db.remove_db(index)

            if self.model().sourceModel().active_index() == index:
                self.unset_activated()
            else:
                settings.local_settings.verify_paths()
        else:
            super(BookmarksWidget, self).toggle_item_flag(
                index, flag, state=state)
