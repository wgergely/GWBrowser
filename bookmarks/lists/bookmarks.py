# -*- coding: utf-8 -*-
"""The widget, model and context menu needed for listing bookmarks stored
in `local_settings`.

"""
from PySide2 import QtWidgets, QtGui, QtCore

import _scandir

from .. import log
from .. import common
from .. import bookmark_db
from .. import threads
from .. import contextmenu
from .. import settings
from .. import actions

from . import base
from . import delegate


BOOKMARK_DESCRIPTION = u'{description}{width}{height}{framerate}{prefix}'


def get_description(server, job, root, db=None):
    """Utility method for contructing a short description for a bookmark item.

    The description includes currently set properties and the description of
    the bookmark.

    Args:
        server (unicode):   Server name.
        job (unicode):   Job name.
        root (unicode):   Root folder name.

    Returns:
        unicode:    The description of the bookmark.

    """
    def _get_data(db):
        data = {}
        for k in bookmark_db.TABLES[bookmark_db.BookmarkTable]:
            v = db.value(db.source(), k, table=bookmark_db.BookmarkTable)
            v = v if v else None
            data[k] = v
        return data

    if db:
        v = _get_data(db)
    else:
        with bookmark_db.transactions(server, job, root) as _db:
            v = _get_data(_db)

    try:
        separator = u'  |  '

        description = v['description'] + separator if v['description'] else u''
        width = v['width'] if (v['width'] and v['height']) else u''
        height = u'x{}px'.format(v['height']) if (v['width'] and v['height']) else u''
        framerate = u'{}{}fps'.format(separator, v['framerate']) if v['framerate'] else u''
        prefix = u'{}{}'.format(separator, v['prefix']) if v['prefix'] else u''

        s = BOOKMARK_DESCRIPTION.format(
            description=description,
            width=width,
            height=height,
            framerate=framerate,
            prefix=prefix
        )
        s = s.replace(separator + separator, separator)
        s = s.strip(separator).strip() # pylint: disable=E1310
        return s
    except:
        log.error(u'Error constructing description.')
        return u''


class BookmarksWidgetContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with the BookmarksWidget.

    Methods:
        refresh: Refreshes the collector and repopulates the widget.

    """

    @common.debug
    @common.error
    def setup(self):
        self.window_menu()

        self.separator()

        self.bookmark_editor_menu()

        self.separator()
        self.title()

        self.bookmark_url_menu()
        self.asset_url_menu()
        self.sg_url_menu()
        self.reveal_item_menu()

        self.separator()

        self.add_asset_to_bookmark_menu()
        self.edit_selected_bookmark_menu()
        self.bookmark_clipboard_menu()
        self.notes_menu()
        self.mode_toggles_menu()

        self.separator()

        self.set_generate_thumbnails_menu()
        self.row_size_menu()
        self.sort_menu()
        self.display_toggles_menu()
        self.refresh_menu()

        self.separator()

        self.preferences_menu()

        self.separator()

        self.quit_menu()


class BookmarksModel(base.BaseModel):
    """The model used store the data necessary to display bookmarks.

    """
    queue_type = threads.BookmarkInfoQueue
    thumbnail_queue_type = threads.BookmarkThumbnailQueue

    def __init__(self, has_threads=True, parent=None):
        super(BookmarksModel, self).__init__(
            has_threads=has_threads, parent=parent)

    @base.initdata
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

        task = self.task()

        settings.local_settings.sync()
        favourites = settings.local_settings.get_favourites()
        bookmarks = settings.local_settings.get_bookmarks()

        bookmarks = bookmarks if bookmarks else {}

        for k, v in bookmarks.iteritems():
            if not all(v.values()):
                continue
            if not len(v.values()) >= 3:
                raise ValueError(u'Invalid bookmark value.')

            server = v[settings.ServerKey]
            job =v[settings.JobKey]
            root = v[settings.RootKey]

            file_info = QtCore.QFileInfo(k)
            exists = file_info.exists()

            # We'll mark the item archived if the saved bookmark does not refer
            # to an existing file
            if exists:
                flags = dflags()
            else:
                flags = dflags() | common.MarkedAsArchived

            filepath = file_info.filePath()

            # Item flags. Active and favourite flags will be only set if the
            # bookmark exist
            if all((
                server == settings.active(settings.ServerKey),
                job == settings.active(settings.JobKey),
                root == settings.active(settings.RootKey)
            )) and exists:
                flags = flags | common.MarkedAsActive

            if filepath in favourites and exists:
                flags = flags | common.MarkedAsFavourite

            text = u'{}  |  {}'.format(
                job,
                root
            )

            data = self.INTERNAL_MODEL_DATA[task][common.FileItem]
            idx = len(data)
            data[idx] = common.DataDict({
                QtCore.Qt.DisplayRole: text,
                QtCore.Qt.EditRole: text,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.ToolTipRole: filepath,
                QtCore.Qt.SizeHintRole: self.row_size(),
                #
                common.TextSegmentRole: {},
                #
                common.EntryRole: [],
                common.FlagsRole: flags,
                common.ParentPathRole: (server, job, root),
                common.DescriptionRole: u'',
                common.TodoCountRole: 0,
                common.AssetCountRole: 0,
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
                common.IdRole: idx,
                #
                common.SGConfiguredRole: False,
            })

            if not exists:
                continue

            with bookmark_db.transactions(server, job, root) as db:
                # Custom item flags
                flags = data[idx][common.FlagsRole]
                v = db.value(
                    data[idx][QtCore.Qt.StatusTipRole],
                    u'flags'
                )
                data[idx][common.FlagsRole] = flags | v if v is not None else flags

                description = get_description(server, job, root, db=db)
                data[idx][common.DescriptionRole] = description
                data[idx][QtCore.Qt.ToolTipRole] = description
                data[idx][common.TextSegmentRole] = self.get_text_segments(text, description)

        self.activeChanged.emit(self.active_index())

    def __resetdata__(self):
        self.INTERNAL_MODEL_DATA[self.task()] = common.DataDict({
            common.FileItem: common.DataDict({}),
            common.SequenceItem: common.DataDict({}),
        })
        self.__initdata__()
        self.endResetModel()

    @staticmethod
    def get_text_segments(text, description):
        """Returns a tuple of text and colour information to be used to mimick
        rich-text like colouring of individual text elements.

        Used by the list delegate to paint the job name and root folder.

        """
        if not text:
            return {}

        text = text.strip().strip(u'/').strip(u'\\')
        if not text:
            return {}

        d = {}
        v = text.split(u'|')

        s_color = common.FAVOURITE.darker(250)

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
                    d[len(d)] = (u' / ', s_color)
            if i < (len(v) - 1):
                d[len(d)] = (u'   |    ', s_color)

        if description:
            d[len(d)] = (u'   |   ', s_color)
            d[len(d)] = (description, s_color)
        return d

    def default_row_size(self):
        return QtCore.QSize(1, common.BOOKMARK_ROW_HEIGHT())

    def local_settings_key(self):
        return settings.BookmarksKey


class BookmarksWidget(base.ThreadedBaseWidget):
    """The view used to display the contents of a ``BookmarksModel`` instance."""
    SourceModel = BookmarksModel
    Delegate = delegate.BookmarksWidgetDelegate
    ContextMenu = BookmarksWidgetContextMenu

    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)
        self.setWindowTitle(u'Bookmarks')
        self._background_icon = u'bookmark'

        self.remove_bookmark_timer = QtCore.QTimer(parent=self)
        self.remove_bookmark_timer.setSingleShot(True)
        self.remove_bookmark_timer.setInterval(10)
        self.remove_bookmark_timer.timeout.connect(
            self.remove_queued_bookmarks)

        self.bookmarks_to_remove = []

        actions.signals.bookmarksChanged.connect(
            self.model().sourceModel().__resetdata__)
        actions.signals.bookmarkValueUpdated.connect(self.update_model_value)

    @QtCore.Slot()
    def remove_queued_bookmarks(self):
        if self.multi_toggle_pos:
            self.remove_bookmark_timer.start(self.remove_bookmark_timer.interval())
            return
        for bookmark in [f for f in self.bookmarks_to_remove]:
            settings.local_settings.remove_bookmark(*bookmark)
            del self.bookmarks_to_remove[self.bookmarks_to_remove.index(
                bookmark)]

        self.model().sourceModel().__resetdata__()

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return

        cursor_position = self.mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)
        if not index.isValid():
            return

        if index.flags() & common.MarkedAsArchived:
            super(BookmarksWidget, self).toggle_item_flag(
                index,
                common.MarkedAsArchived,
                state=False,
            )
            self.update(index)
            self.reset_multitoggle()
            return

        rect = self.visualRect(index)
        rectangles = delegate.get_rectangles(
            rect, self.inline_icons_count())

        super(BookmarksWidget, self).mouseReleaseEvent(event)

        server, job, root = index.data(common.ParentPathRole)[0:3]
        if rectangles[delegate.AddAssetRect].contains(cursor_position):
            actions.add_asset(server=server, job=job, root=root)
            return

        if rectangles[delegate.PropertiesRect].contains(cursor_position):
            actions.edit_bookmark(server=server, job=job, root=root)
            return

    def inline_icons_count(self):
        """The number of row-icons an item has."""
        if self.buttons_hidden():
            return 0
        return 6

    @QtCore.Slot(QtCore.QModelIndex)
    def save_activated(self, index, reset=False):
        """Saves the activated index to ``Settings``."""
        if not reset:
            if not index.isValid() and not reset:
                return
            if not index.data(common.ParentPathRole):
                return
            server, job, root = index.data(common.ParentPathRole)
        else:
            server, job, root = None, None, None

        settings.set_active(settings.ServerKey, server)
        settings.set_active(settings.JobKey, job)
        settings.set_active(settings.RootKey, root)

    def toggle_item_flag(self, index, flag, state=None, commit_now=True):
        if flag == common.MarkedAsArchived:
            if hasattr(index.model(), 'sourceModel'):
                index = self.model().mapToSource(index)

            idx = index.row()
            data = index.model().model_data()
            data[idx][common.FlagsRole] = data[idx][common.FlagsRole] | common.MarkedAsArchived
            self.update(index)

            self.bookmarks_to_remove.append(index.data(common.ParentPathRole))
            self.remove_bookmark_timer.start()
            return

        super(BookmarksWidget, self).toggle_item_flag(
            index, flag, state=state, commit_now=commit_now)

    def get_hint_string(self):
        return u'Right-click -> Bookmark Editor to add a new bookmark'

    @QtCore.Slot(unicode)
    @QtCore.Slot(int)
    @QtCore.Slot(object)
    def update_model_value(self, source, role, v):
        model = self.model().sourceModel()
        data = model.model_data()
        for idx in xrange(model.rowCount()):
            if source != data[idx][QtCore.Qt.StatusTipRole]:
                continue

            data[idx][role] = v

            # Update the description after a value-change
            server, job, root = data[idx][common.ParentPathRole]
            t = u'{}  |  {}'.format(job, root)
            v = get_description(server, job, root)
            data[idx][common.DescriptionRole] = v
            data[idx][QtCore.Qt.ToolTipRole] = v
            data[idx][common.TextSegmentRole] = model.get_text_segments(t, v)

            self.update_row(idx)
            break
