# -*- coding: utf-8 -*-
"""``assetswidget.py`` defines the main objects needed for interacting with assets."""

import re
from PySide2 import QtCore, QtWidgets

import bookmarks._scandir as _scandir
import bookmarks.images as images
import bookmarks.common as common
from bookmarks.basecontextmenu import BaseContextMenu
from bookmarks.baselistwidget import ThreadedBaseWidget
from bookmarks.baselistwidget import BaseModel
from bookmarks.baselistwidget import initdata
from bookmarks.delegate import AssetsWidgetDelegate
import bookmarks.bookmark_db as bookmark_db

import bookmarks.settings as settings


class AssetsWidgetContextMenu(BaseContextMenu):
    """The context menu associated with the AssetsWidget."""

    def __init__(self, index, parent=None):
        super(AssetsWidgetContextMenu, self).__init__(index, parent=parent)
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


class AssetModel(BaseModel):
    """Asset data model.

    Assets are  folders with a special indentier
    file in their root. Queries the current self.parent_path and
    populates the `INTERNAL_MODEL_DATA` when `self.__initdata__()` is called.

    The model is multithreaded and loads file and thumbnail data using
    thread workers.

    """
    ROW_SIZE = QtCore.QSize(120, common.ASSET_ROW_HEIGHT)

    def __init__(self, parent=None):
        super(AssetModel, self).__init__(parent=parent)


    @initdata
    def __initdata__(self):
        """Collects the data needed to populate the bookmarks model by querrying
        the path stored in ``self.parent_path``.

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

        if not self.parent_path:
            return
        if not all(self.parent_path):
            return

        dkey = self.data_key()
        dtype = self.data_type()

        default_thumbnail_image = images.ImageCache.get(
            common.rsc_path(__file__, u'placeholder'),
            self.ROW_SIZE.height() - common.ROW_SEPARATOR)
        default_background_color = common.THUMBNAIL_BACKGROUND

        self.INTERNAL_MODEL_DATA[dkey] = common.DataDict({
            common.FileItem: common.DataDict(),
            common.SequenceItem: common.DataDict()
        })

        favourites = settings.local_settings.favourites()
        sfavourites = set(favourites)

        activeasset = settings.local_settings.value(u'activepath/asset')
        server, job, root = self.parent_path
        bookmark_path = u'{}/{}/{}'.format(server, job, root)

        try:
            # Let's get the identifier from the bookmark database
            db = bookmark_db.get_db(
                QtCore.QModelIndex(),
                server=server,
                job=job,
                root=root
            )
            ASSET_IDENTIFIER = db.value(0, u'identifier', table='properties')
        except:
            ASSET_IDENTIFIER = None

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

            if activeasset:
                if activeasset.lower() == filename.lower():
                    flags = flags | common.MarkedAsActive

            idx = len(self.INTERNAL_MODEL_DATA[dkey][dtype])
            name = re.sub(ur'[_]{1,}', u' ', filename).strip(u'_')
            self.INTERNAL_MODEL_DATA[dkey][dtype][idx] = common.DataDict({
                QtCore.Qt.DisplayRole: name,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.SizeHintRole: self.ROW_SIZE,
                #
                common.EntryRole: [entry, ],
                common.FlagsRole: flags,
                common.ParentPathRole: (server, job, root, filename),
                common.DescriptionRole: u'',
                common.TodoCountRole: 0,
                common.FileDetailsRole: u'',
                common.SequenceRole: None,
                common.FramesRole: [],
                common.FileInfoLoaded: False,
                common.StartpathRole: None,
                common.EndpathRole: None,
                #
                common.FileThumbnailLoaded: False,
                common.DefaultThumbnailRole: default_thumbnail_image,
                common.DefaultThumbnailBackgroundRole: default_background_color,
                common.ThumbnailPathRole: None,
                common.ThumbnailRole: default_thumbnail_image,
                common.ThumbnailBackgroundRole: default_background_color,
                #
                common.TypeRole: common.FileItem,
                #
                common.SortByName: common.namekey(filepath),
                common.SortByLastModified: 0,
                common.SortBySize: 0,
                #
                common.IdRole: idx
            })

        # Explicitly emit signal to notify the other dependent model
        self.activeChanged.emit(self.active_index())

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


class AssetsWidget(ThreadedBaseWidget):
    """The view used to display the contents of a ``AssetModel`` instance."""
    SourceModel = AssetModel
    Delegate = AssetsWidgetDelegate
    ContextMenu = AssetsWidgetContextMenu

    def __init__(self, parent=None):
        super(AssetsWidget, self).__init__(parent=parent)
        self.setWindowTitle(u'Assets')
        self._background_icon = u'assets'

    def buttons_hidden(self):
        """Returns the visibility of the inline icon buttons. There's no need to
        hide the asset buttons, therefore this function will always return
        False.

        """
        return False

    def inline_icons_count(self):
        """The number of icons on the right - hand side."""
        if self.buttons_hidden():
            return 0
        return 4

    @QtCore.Slot(QtCore.QModelIndex)
    def save_activated(self, index):
        """Sets the current item item as ``active`` and
        emits the ``activeChanged`` signal.

        """
        if not index.isValid():
            return
        if not index.data(common.ParentPathRole):
            return

        settings.local_settings.setValue(
            u'activepath/asset', index.data(common.ParentPathRole)[-1])
        settings.local_settings.verify_paths()

    def showEvent(self, event):
        source_index = self.model().sourceModel().active_index()
        if source_index.isValid():
            index = self.model().mapFromSource(source_index)
            self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
            self.selectionModel().setCurrentIndex(
                index, QtCore.QItemSelectionModel.ClearAndSelect)
        return super(AssetsWidget, self).showEvent(event)

    def increase_row_size(self):
        pass

    def decrease_row_size(self):
        pass
