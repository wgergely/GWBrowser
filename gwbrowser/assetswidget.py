# -*- coding: utf-8 -*-
"""``assetswidget.py`` defines the main objects needed for interacting with assets."""

import time
import re
import traceback
import sys
from PySide2 import QtCore, QtGui, QtWidgets

import gwbrowser.gwscandir as gwscandir
from gwbrowser.imagecache import ImageCache
import gwbrowser.common as common
from gwbrowser.imagecache import oiio_make_thumbnail
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.baselistwidget import BaseInlineIconWidget
from gwbrowser.baselistwidget import ThreadedBaseWidget
from gwbrowser.baselistwidget import BaseModel
from gwbrowser.baselistwidget import initdata
from gwbrowser.baselistwidget import validate_index
import gwbrowser.delegate as delegate
from gwbrowser.delegate import AssetsWidgetDelegate

from gwbrowser.settings import AssetSettings
import gwbrowser.settings as settings_

from gwbrowser.fileswidget import FileInfoWorker
from gwbrowser.fileswidget import SecondaryFileInfoWorker
from gwbrowser.fileswidget import FileThumbnailWorker
from gwbrowser.threads import BaseThread
from gwbrowser.threads import BaseWorker
from gwbrowser.threads import Unique


class AssetInfoWorker(FileInfoWorker):
    queue = Unique(999999)
    indexes_in_progress = []


class SecondaryAssetInfoWorker(AssetInfoWorker):
    """The worker associated with the ``SecondaryAssetInfoWorker``.

    The worker performs  the same function as ``FileInfoWorker`` but
    it has it own queue and is concerned with iterating over all file-items.

    """
    queue = Unique(999999)
    indexes_in_progress = []


class AssetThumbnailWorker(FileThumbnailWorker):
    """The worker associated with the ``AssetThumbnailThread``.

    The worker is responsible for loading the existing thumbnail images from
    the cache folder, and if needed and possible, generating new thumbnails from
    the source file.

    """
    queue = Unique(999)
    indexes_in_progress = []


class AssetInfoThread(BaseThread):
    """Thread controller associated with the ``FilesModel``."""
    Worker = AssetInfoWorker


class SecondaryAssetInfoThread(BaseThread):
    """Thread controller associated with the ``FilesModel``."""
    Worker = SecondaryAssetInfoWorker


class AssetThumbnailThread(BaseThread):
    """Thread controller associated with the ``FilesModel``."""
    Worker = AssetThumbnailWorker


class AssetsWidgetContextMenu(BaseContextMenu):
    """The context menu associated with the AssetsWidget."""

    def __init__(self, index, parent=None):
        super(AssetsWidgetContextMenu, self).__init__(index, parent=parent)
        if index.isValid():
            self.add_mode_toggles_menu()

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


class AssetModel(BaseModel):
    """The model used store the data necessary to display assets.

    Assets themselves are just simple folder stuctures with a special indentier
    file at their room (see ``common.ASSET_IDENTIFIER``).

    The model will querry the currently set bookmark folder and will pull all
    necessary information via the **__initdata__** method. In practice the path
    used for the querry is extrapolated from ``self.parent_path``.

    Example:
        .. code-block:: python

           model = AssetModel()
           model.set_active(index) # Must set the parent item of the model using the index of the active bookmark item
           model.modelDataResetRequested.emit() # this signal will call __initdata__ and populate the model

    """
    InfoThread = AssetInfoThread
    SecondaryInfoThread = SecondaryAssetInfoThread
    ThumbnailThread = AssetThumbnailThread

    def __init__(self, thread_count=common.FTHREAD_COUNT, parent=None):
        super(AssetModel, self).__init__(
            thread_count=thread_count, parent=parent)

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

        self.reset_thread_worker_queues()

        if not self.parent_path:
            return
        if not all(self.parent_path):
            return

        dkey = self.data_key()
        dtype = self.data_type()
        rowsize = QtCore.QSize(0, common.ASSET_ROW_HEIGHT)

        default_thumbnail_image = ImageCache.get(
            common.rsc_path(__file__, u'placeholder'),
            rowsize.height() - common.ROW_SEPARATOR)
        default_background_color = common.THUMBNAIL_BACKGROUND

        self._data[self.data_key()] = {
            common.FileItem: {}, common.SequenceItem: {}}

        favourites = settings_.local_settings.favourites()
        sfavourites = set(favourites)

        activeasset = settings_.local_settings.value(u'activepath/asset')
        server, job, root = self.parent_path
        bookmark_path = u'{}/{}/{}'.format(server, job, root)

        nth = 3
        c = 0
        for entry in gwscandir.scandir(bookmark_path):
            if entry.name.startswith(u'.'):
                continue
            if not entry.is_dir():
                continue

            filepath = entry.path

            identifier_file = u'{}/{}'.format(filepath,
                                              common.ASSET_IDENTIFIER)
            if not QtCore.QFileInfo(identifier_file).exists():
                continue

            # Progress bar
            c += 1
            if not c % nth:
                self.messageChanged.emit(u'Found {} assets...'.format(c))
                QtWidgets.QApplication.instance().processEvents(
                    QtCore.QEventLoop.ExcludeUserInputEvents)

            filename = entry.name

            flags = dflags()

            if filepath.lower() in sfavourites:
                flags = flags | common.MarkedAsFavourite

            if activeasset:
                if activeasset.lower() == filename.lower():
                    flags = flags | common.MarkedAsActive

            idx = len(self._data[dkey][dtype])
            name = re.sub(ur'[_]{1,}', u' ', filename).strip(u'_')
            self._data[dkey][dtype][idx] = {
                QtCore.Qt.DisplayRole: name,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.ToolTipRole: filepath,
                QtCore.Qt.SizeHintRole: rowsize,
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
            }

    def data_key(self):
        """Data keys are only implemented on the FilesModel but need to return a
        value for compatibility other functions.

        """
        return u'.'


class AssetsWidget(ThreadedBaseWidget):
    """The view used to display the contents of a ``AssetModel`` instance."""
    SourceModel = AssetModel
    Delegate = AssetsWidgetDelegate
    ContextMenu = AssetsWidgetContextMenu

    def __init__(self, parent=None):
        super(AssetsWidget, self).__init__(parent=parent)
        self.setWindowTitle(u'Assets')

        # I'm not sure why but the proxy is not updated properly after refresh
        self.model().sourceModel().dataSorted.connect(self.model().invalidate)

    def buttons_hidden(self):
        """Returns the visibility of the inline icon buttons. There's no need to
        hide the asset buttons, therefore this function will always return
        False.

        """
        return False

    def eventFilter(self, widget, event):
        """Custom event filter used to paint the background icon."""
        super(AssetsWidget, self).eventFilter(widget, event)

        if widget is not self:
            return False

        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            pixmap = ImageCache.get_rsc_pixmap(
                u'assets', QtGui.QColor(0, 0, 0, 20), 180)
            rect = pixmap.rect()
            rect.moveCenter(self.rect().center())
            painter.drawPixmap(rect, pixmap, pixmap.rect())
            painter.end()
            return True

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
        settings_.local_settings.setValue(
            u'activepath/asset', index.data(common.ParentPathRole)[-1])
        # Resetting invalid paths
        settings_.local_settings.verify_paths()

    def showEvent(self, event):
        source_index = self.model().sourceModel().active_index()
        if not source_index.isValid():
            return super(AssetsWidget, self).showEvent(event)

        index = self.model().mapFromSource(source_index)
        self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
        self.selectionModel().setCurrentIndex(
            index, QtCore.QItemSelectionModel.ClearAndSelect)
        return super(AssetsWidget, self).showEvent(event)
