# -*- coding: utf-8 -*-
"""The widget, model and context menu needed for interacting with assets.

"""
import re
from PySide2 import QtCore, QtWidgets, QtGui

import bookmarks.common as common
import _scandir as _scandir
import bookmarks.threads as threads
import bookmarks.delegate as delegate
import bookmarks.baselist as baselist
import bookmarks.basecontextmenu as basecontextmenu
import bookmarks.bookmark_db as bookmark_db


import bookmarks.settings as settings


class AssetsWidgetContextMenu(basecontextmenu.BaseContextMenu):
    """The context menu associated with the AssetsWidget."""

    def __init__(self, index, parent=None):
        super(AssetsWidgetContextMenu, self).__init__(index, parent=parent)
        self.add_show_addasset_menu()
        if index.isValid():
            self.add_mode_toggles_menu()
        self.add_separator()
        self.add_row_size_menu()
        self.add_separator()
        self.add_set_generate_thumbnails_menu()
        self.add_separator()
        if index.isValid():
            self.add_copy_menu()
            self.add_reveal_item_menu()
        self.add_separator()
        self.add_sort_menu()
        self.add_separator()
        self.add_display_toggles_menu()
        self.add_separator()
        self.add_refresh_menu()


class AssetModel(baselist.BaseModel):
    """Asset data model."""
    DEFAULT_ROW_SIZE = QtCore.QSize(1, common.ASSET_ROW_HEIGHT())
    val = settings.local_settings.value(u'widget/assetmodel/rowheight')
    val = val if val else DEFAULT_ROW_SIZE.height()
    val = DEFAULT_ROW_SIZE.height() if (val < DEFAULT_ROW_SIZE.height()) else val
    ROW_SIZE = QtCore.QSize(1, val)

    queue_type = threads.AssetInfoQueue
    thumbnail_queue_type = threads.AssetThumbnailQueue

    def __init__(self, has_threads=True, parent=None):
        super(AssetModel, self).__init__(
            has_threads=has_threads, parent=parent)

    @baselist.initdata
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
                QtCore.Qt.ItemIsSelectable)

        settings.local_settings.load_and_verify_stored_paths()
        if not settings.ACTIVE['root']:
            return

        task_folder = self.task_folder()
        dtype = self.data_type()

        self.INTERNAL_MODEL_DATA[task_folder] = common.DataDict({
            common.FileItem: common.DataDict(),
            common.SequenceItem: common.DataDict()
        })

        favourites = settings.local_settings.favourites()
        sfavourites = set(favourites)

        if not settings.ACTIVE['root']:
            return
        bookmark_path = u'{}/{}/{}'.format(
            settings.ACTIVE['server'],
            settings.ACTIVE['job'],
            settings.ACTIVE['root']
        )

        # Let's get the identifier from the bookmark database
        db = bookmark_db.get_db(
            settings.ACTIVE['server'],
            settings.ACTIVE['job'],
            settings.ACTIVE['root']
        )
        ASSET_IDENTIFIER = db.value(1, u'identifier', table='properties')

        nth = 1
        c = 0
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

            # Progress bar
            c += 1
            if not c % nth:
                self.progressMessage.emit(u'Found {} assets...'.format(c))
                QtWidgets.QApplication.instance().processEvents(
                    QtCore.QEventLoop.ExcludeUserInputEvents)

            filename = entry.name
            flags = dflags()

            if filepath.lower() in sfavourites:
                flags = flags | common.MarkedAsFavourite

            if settings.ACTIVE['asset']:
                if settings.ACTIVE['asset'].lower() == filename.lower():
                    flags = flags | common.MarkedAsActive

            idx = len(self.INTERNAL_MODEL_DATA[task_folder][dtype])
            name = re.sub(ur'[_]{1,}', u' ', filename).strip(u'_')
            self.INTERNAL_MODEL_DATA[task_folder][dtype][idx] = common.DataDict({
                QtCore.Qt.DisplayRole: name,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.SizeHintRole: self.ROW_SIZE,
                #
                common.EntryRole: [entry, ],
                common.FlagsRole: flags,
                common.ParentPathRole: (
                    settings.ACTIVE['server'],
                    settings.ACTIVE['job'],
                    settings.ACTIVE['root'],
                    filename
                ),
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

        # Explicitly emit signal to notify the other dependent model
        self.activeChanged.emit(self.active_index())

    def data_type(self):
        return common.FileItem

    def settings_key(self):
        """The key used to store and save item widget and item states in `local_settings`."""
        ks = []
        for k in (u'job', u'root'):
            v = settings.ACTIVE[k]
            if not v:
                return None
            ks.append(v)
        return u'/'.join(ks)


class AssetsWidget(baselist.ThreadedBaseWidget):
    """The view used to display the contents of a ``AssetModel`` instance."""
    SourceModel = AssetModel
    Delegate = delegate.AssetsWidgetDelegate
    ContextMenu = AssetsWidgetContextMenu

    def __init__(self, parent=None):
        super(AssetsWidget, self).__init__(parent=parent)
        self.setWindowTitle(u'Assets')
        self._background_icon = u'assets'

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
        settings.set_active(u'asset', index.data(common.ParentPathRole)[-1])

    def showEvent(self, event):
        source_index = self.model().sourceModel().active_index()
        if source_index.isValid():
            index = self.model().mapFromSource(source_index)
            self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
            self.selectionModel().setCurrentIndex(
                index, QtCore.QItemSelectionModel.ClearAndSelect)
        return super(AssetsWidget, self).showEvent(event)

    @QtCore.Slot()
    def show_properties_widget(self):
        import bookmarks.addassetwidget as addassetwidget

        if not self.selectionModel().hasSelection():
            return
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        if not all((
            settings.ACTIVE[u'server'],
            settings.ACTIVE[u'job'],
            settings.ACTIVE[u'root'],
        )):
            return

        db = bookmark_db.get_db(
            settings.ACTIVE[u'server'],
            settings.ACTIVE[u'job'],
            settings.ACTIVE[u'root'],
        )

        @QtCore.Slot(unicode)
        def update_description(s):
            source_index = self.model().mapToSource(index)
            idx = source_index.row()
            data = self.model().sourceModel().model_data()
            data[idx][common.DescriptionRole] = s
            self.update(index)

        widget = addassetwidget.AddAssetWidget(
            *index.data(common.ParentPathRole),
            update=True
        )
        widget.descriptionUpdated.connect(update_description)
        widget.open()


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
            self.show_add_widget()
        elif rectangles[delegate.BookmarkPropertiesRect].contains(cursor_position):
            self.show_properties_widget()
        else:
            super(AssetsWidget, self).mouseReleaseEvent(event)

    @QtCore.Slot()
    def show_add_widget(self):
        pass
