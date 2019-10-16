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
from gwbrowser.delegate import AssetsWidgetDelegate

from gwbrowser.settings import AssetSettings
from gwbrowser.settings import local_settings, Active

from gwbrowser.fileswidget import FileInfoWorker
from gwbrowser.fileswidget import SecondaryFileInfoWorker
from gwbrowser.fileswidget import FileThumbnailWorker
from gwbrowser.threads import BaseThread
from gwbrowser.threads import BaseWorker
from gwbrowser.threads import Unique


class AssetInfoWorker(FileInfoWorker):
    queue = Unique(999999)
    indexes_in_progress = []

    @staticmethod
    @validate_index
    @QtCore.Slot(QtCore.QModelIndex)
    def process_index(index, update=True, exists=False):
        """The main processing function called by the worker.
        Upon loading all the information ``FileInfoLoaded`` is set to ``True``.

        """
        return FileInfoWorker.process_index(index, update=update, exists=exists)


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


class AssetModel(BaseModel):
    """The model used store the data necessary to display assets.

    Assets themselves are just simple folder stuctures with a special indentier
    file at their room (see ``common.ASSET_IDENTIFIER``).

    The model will querry the currently set bookmark folder and will pull all
    necessary information via the **__initdata__** method. In practice the path
    used for the querry is extrapolated from ``self._parent_item``.

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
        super(AssetModel, self).__init__(thread_count=thread_count, parent=parent)

    @initdata
    def __initdata__(self):
        """Collects the data needed to populate the bookmarks model by querrying
        the path stored in ``self._parent_item``.

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

        if not self._parent_item:
            return
        if not all(self._parent_item):
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

        favourites = local_settings.value(u'favourites')
        favourites = [f.lower() for f in favourites] if favourites else []
        sfavourites = set(favourites)
        activeasset = local_settings.value(u'activepath/asset')
        server, job, root = self._parent_item
        bookmark_path = u'{}/{}/{}'.format(server, job, root)

        nth = 3
        c = 0
        for entry in gwscandir.scandir(bookmark_path):
            if entry.name.startswith(u'.'):
                continue
            if not entry.is_dir():
                continue

            filepath = entry.path.replace(u'\\', u'/')

            identifier_file = u'{}/{}'.format(filepath, common.ASSET_IDENTIFIER)
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
                if activeasset in filepath:
                    flags = flags | common.MarkedAsActive

            idx = len(self._data[dkey][dtype])
            name = re.sub(ur'[_]{1,}', ' ', filename).strip(u'_')
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
                common.TypeRole: common.AssetItem,
                #
                common.SortByName: filepath,
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
        local_settings.setValue(
            u'activepath/asset', index.data(common.ParentPathRole)[-1])
        # Resetting invalid paths
        Active.paths()

    def mouseDoubleClickEvent(self, event):
        """Custom double - click event.

        A double click can `activate` an item, or it can trigger an edit event.
        As each item is associated with multiple editors we have to inspect
        the double - click location before deciding what action to take.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
        if index.flags() & common.MarkedAsArchived:
            return

        rect = self.visualRect(index)

        thumbnail_rect = QtCore.QRect(rect)
        thumbnail_rect.setWidth(rect.height())
        thumbnail_rect.moveLeft(common.INDICATOR_WIDTH)

        name_rect = QtCore.QRect(rect)
        name_rect.setLeft(
            common.INDICATOR_WIDTH
            + name_rect.height()
            + common.MARGIN
        )
        name_rect.setRight(name_rect.right() - common.MARGIN)

        font = QtGui.QFont(common.PrimaryFont)
        metrics = QtGui.QFontMetrics(font)

        name_rect.moveTop(name_rect.top() + (name_rect.height() / 2.0))
        name_rect.setHeight(metrics.height())
        name_rect.moveTop(name_rect.top() - (name_rect.height() / 2.0))

        description_rect = QtCore.QRect(rect)
        font = QtGui.QFont(common.SecondaryFont)
        metrics = QtGui.QFontMetrics(font)

        description_rect.moveTop(
            description_rect.top() + (description_rect.height() / 2.0))
        description_rect.setHeight(metrics.height())
        description_rect.moveTop(description_rect.top(
        ) - (description_rect.height() / 2.0) + metrics.lineSpacing())

        source_index = self.model().mapToSource(index)
        if description_rect.contains(event.pos()):
            self.description_editor_widget.show()
            return
        elif thumbnail_rect.contains(event.pos()):
            ImageCache.instance().pick(source_index)
            return
        self.activate(self.selectionModel().currentIndex())

    def showEvent(self, event):
        source_index = self.model().sourceModel().active_index()
        if not source_index.isValid():
            return super(AssetsWidget, self).showEvent(event)

        index = self.model().mapFromSource(source_index)
        self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
        self.selectionModel().setCurrentIndex(index, QtCore.QItemSelectionModel.ClearAndSelect)
        return super(AssetsWidget, self).showEvent(event)
