# -*- coding: utf-8 -*-
"""The widget, model and context menu needed for interacting with assets.

"""
import re
import _scandir
import functools

from PySide2 import QtCore, QtWidgets, QtGui

from .. import common
from .. import threads
from .. import contextmenu
from .. import bookmark_db
from .. import settings
from .. import actions

from . import delegate
from . import base


class AssetsWidgetContextMenu(contextmenu.BaseContextMenu):
    """The context menu associated with the AssetsWidget."""

    def setup(self):
        self.window_menu()
        self.separator()
        self.show_addasset_menu()
        self.separator()
        self.sg_bulk_link_menu()
        self.separator()
        self.edit_selected_asset_menu()
        self.separator()
        if self.index.isValid():
            self.mode_toggles_menu()
        self.separator()
        self.urls_menu()
        self.separator()
        if self.index.isValid():
            self.notes_menu()
            self.copy_menu()
            self.reveal_item_menu()
        self.separator()
        self.set_generate_thumbnails_menu()
        self.row_size_menu()
        self.sort_menu()
        self.display_toggles_menu()
        self.separator()
        self.refresh_menu()


class AssetModel(base.BaseModel):
    """Asset data model."""
    queue_type = threads.AssetInfoQueue
    thumbnail_queue_type = threads.AssetThumbnailQueue

    def __init__(self, has_threads=True, parent=None):
        super(AssetModel, self).__init__(
            has_threads=has_threads, parent=parent)

    @base.initdata
    def __initdata__(self):
        """Collects the data needed to populate the bookmarks model by querrying
        the active root folder.

        Note:
            Getting asset information is relatively cheap,
            hence the model does not have any threads associated with it.

        """
        def dflags():
            """The default flags to apply to the item."""
            return (
                QtCore.Qt.ItemNeverHasChildren |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable
            )

        settings.local_settings.load_and_verify_stored_paths()

        parent_path = self.parent_path()
        if not parent_path or not all(parent_path):
            return

        # The asset model does not actually use task folders but for compatibility
        # with the files model, we'll access data in the same manner
        task = self.task()
        dtype = self.data_type()

        self.INTERNAL_MODEL_DATA[task] = common.DataDict({
            common.FileItem: common.DataDict(),
            common.SequenceItem: common.DataDict()
        })

        favourites = settings.local_settings.get_favourites()
        sfavourites = set(favourites)
        source = u'/'.join(parent_path)

        # Let's get the identifier from the bookmark database
        with bookmark_db.transactions(*parent_path) as db:
            ASSET_IDENTIFIER = db.value(
                source, u'identifier', table=bookmark_db.BookmarkTable)

        nth = 1
        c = 0

        for entry in self._entry_iterator(source):
            filepath = entry.path.replace(u'\\', u'/')

            if ASSET_IDENTIFIER:
                identifier = u'{}/{}'.format(
                    filepath, ASSET_IDENTIFIER)
                if not QtCore.QFileInfo(identifier).exists():
                    continue

            # Progress bar
            c += 1
            if not c % nth:
                self.progressMessage.emit(u'Found {} assets...'.format(c))
                QtWidgets.QApplication.instance().processEvents(
                    QtCore.QEventLoop.ExcludeUserInputEvents)

            filename = entry.name
            flags = dflags()

            if filepath in sfavourites:
                flags = flags | common.MarkedAsFavourite

            # Is the item currently active?
            active_asset = settings.ACTIVE[settings.AssetKey]
            if active_asset:
                if active_asset == filename:
                    flags = flags | common.MarkedAsActive

            # Beautify the name
            name = re.sub(ur'[_]{1,}', u' ', filename).strip(u'_').strip('')
            idx = len(self.INTERNAL_MODEL_DATA[task][dtype])
            self.INTERNAL_MODEL_DATA[task][dtype][idx] = common.DataDict({
                QtCore.Qt.DisplayRole: name,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.SizeHintRole: self.row_size(),
                #
                common.EntryRole: [entry, ],
                common.FlagsRole: flags,
                common.ParentPathRole: parent_path + (filename,),
                common.DescriptionRole: u'',
                common.TodoCountRole: 0,
                common.FileDetailsRole: u'',
                common.SequenceRole: None,
                common.FramesRole: [],
                common.FileInfoLoaded: False,
                common.StartpathRole: None,
                common.EndpathRole: None,
                #
                common.ThumbnailLoaded: False,
                #
                common.TypeRole: common.FileItem,
                #
                common.SortByNameRole: common.namekey(filepath),
                common.SortByLastModifiedRole: 0,
                common.SortBySizeRole: 0,
                #
                common.IdRole: idx
            })

        # Explicitly emit `activeChanged` to notify other dependent models
        self.activeChanged.emit(self.active_index())

    def parent_path(self):
        """The model's parent folder path.

        Returns:
            tuple: A tuple of path segments.

        """
        return (
            settings.ACTIVE[settings.ServerKey],
            settings.ACTIVE[settings.JobKey],
            settings.ACTIVE[settings.RootKey],
        )

    def _entry_iterator(self, path):
        """Yields DirEntry instances to be processed in __initdata__.

        """
        for entry in _scandir.scandir(path):
            if entry.name.startswith(u'.'):
                continue
            if not entry.is_dir():
                continue
            yield entry

    def data_type(self):
        return common.FileItem

    def local_settings_key(self):
        v = [settings.ACTIVE[k] for k in (settings.JobKey, settings.RootKey)]
        if not all(v):
            return None
        return u'/'.join(v)

    def default_row_size(self):
        return QtCore.QSize(1, common.ASSET_ROW_HEIGHT())



class AssetsWidget(base.ThreadedBaseWidget):
    """The view used to display the contents of a ``AssetModel`` instance."""
    SourceModel = AssetModel
    Delegate = delegate.AssetsWidgetDelegate
    ContextMenu = AssetsWidgetContextMenu

    def __init__(self, parent=None):
        super(AssetsWidget, self).__init__(parent=parent)
        self.setWindowTitle(u'Assets')
        self._background_icon = u'assets'

        actions.signals.assetValueUpdated.connect(self.update_model_value)

    def inline_icons_count(self):
        """The number of icons on the right - hand side."""
        if self.width() < common.WIDTH() * 0.5:
            return 0
        if self.buttons_hidden():
            return 0
        return 6

    @QtCore.Slot(QtCore.QModelIndex)
    def save_activated(self, index):
        """Sets the current item item as ``active`` and
        emits the ``activeChanged`` signal.

        """
        if not index.isValid():
            return
        if not index.data(common.ParentPathRole):
            return
        settings.set_active(settings.AssetKey, index.data(common.ParentPathRole)[-1])

    def showEvent(self, event):
        source_index = self.model().sourceModel().active_index()
        if source_index.isValid():
            index = self.model().mapFromSource(source_index)
            self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
            self.selectionModel().setCurrentIndex(
                index, QtCore.QItemSelectionModel.ClearAndSelect)
        return super(AssetsWidget, self).showEvent(event)

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return

        super(AssetsWidget, self).mouseReleaseEvent(event)

        cursor_position = self.mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)

        if not index.isValid():
            return
        if index.flags() & common.MarkedAsArchived:
            return

        rect = self.visualRect(index)
        rectangles = delegate.get_rectangles(rect, self.inline_icons_count())

        if rectangles[delegate.AddAssetRect].contains(cursor_position):
            self.show_add_widget()
            return

        if rectangles[delegate.PropertiesRect].contains(cursor_position):
            self.show_properties_widget()
            return

    def get_hint_string(self):
        return u'No assets found. Select right-click -> Add Asset to create a new one.'
