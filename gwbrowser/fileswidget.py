# -*- coding: utf-8 -*-
"""Defines the models, threads and context menus needed to browser the files of
a asset.

``FilesModel`` is responsible for storing file-data. There is a key design
choice determining the model's overall functionality: we're interested in
getting an overview of all files contained in an asset. The reason for this is
that files are sometimes are tucked away into subfolders and are hard to get to.
GWBrowser will expand all sub-folders, get all files inside them and present the
items as a flat list that can be filtered later.

Note:
    We'using Python 3's ``scandir.walk()`` to querry the filesystem. This is
    because of performance considerations, on my test ``scandir`` outperformed
    Qt's ``QDirIterator``. GWBrowser uses a custom build of ``scandir``
    comptible with Python 2.7.

``FilesModel`` differs from the other models as in it doesn't load all necessary
data in the main-thread. It instead relies on workers to querry and set
addittional data. The model will also try to generate thumbnails for any
``OpenImageIO`` readable file-format via its workers.

"""
import json
import base64
import sys
import time
import traceback

from PySide2 import QtWidgets, QtCore, QtGui

import gwbrowser.bookmark_db as bookmark_db

from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.baselistwidget import ThreadedBaseWidget
from gwbrowser.baselistwidget import BaseModel
from gwbrowser.baselistwidget import initdata
from gwbrowser.baselistwidget import validate_index

import gwbrowser.gwscandir as gwscandir
import gwbrowser.common as common
from gwbrowser.settings import AssetSettings
import gwbrowser.settings as settings_
import gwbrowser.delegate as delegate
from gwbrowser.delegate import FilesWidgetDelegate

from gwbrowser.imagecache import ImageCache
from gwbrowser.imagecache import oiio_make_thumbnail

from gwbrowser.threads import BaseThread
from gwbrowser.threads import BaseWorker
from gwbrowser.threads import Unique


class FileInfoWorker(BaseWorker):
    """The worker associated with the ``FileInfoThread``.

    The worker is responsible for loading the file-size, last modified
    timestamps, saved flags and descriptions. These loads involve the
    file-system and can be expensive to perform.

    The worker performs  the same function as ``SecondaryFileInfoWorker`` but it
    has it own queue and is concerned with iterating over **only** the visible
    file-items.

    """
    queue = Unique(999999)
    indexes_in_progress = []

    @staticmethod
    @validate_index
    @QtCore.Slot(QtCore.QModelIndex)
    def process_index(index, exists=False):
        """The main processing function called by the worker.
        Upon loading all the information ``FileInfoLoaded`` is set to ``True``.

        """
        if index.data(common.FileInfoLoaded):
            return
        if not index.data(common.ParentPathRole):
            return

        try:
            data = index.model().model_data()[index.row()]
        except:
            return

        if not index.data(common.ParentPathRole):
            return

        db = bookmark_db.get_db(index)
        if not db:
            return

        # DATABASE --BEGIN--
        with db.transactions():
            # Item description
            if data[common.SequenceRole]:
                k = data[common.SequenceRole]
                k = k.group(1) + u'[0]' + k.group(3) + u'.' + k.group(4)
            else:
                k = data[QtCore.Qt.StatusTipRole]

            # Description
            v = db.value(k, u'description')
            if v:
                data[common.DescriptionRole] = v

            # Todos - We'll have to load the data to count the items.
            # Hope fully this won't end up as a super costly operation
            v = db.value(k, u'notes')
            count = 0
            if v:
                try:
                    v = base64.b64decode(v)
                    v = json.loads(v)
                except:
                    pass
                else:
                    count = [k for k in v if v[k][u'text'] and not v[k][u'checked']]
                    count = len(count)
            data[common.TodoCountRole] = count

            # Item flags
            flags = data[common.FlagsRole] | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled
            v = db.value(k, u'flags')
            if v:
                flags = flags | v
            data[common.FlagsRole] = flags

        # For sequence items we will work out the name of the sequence based on
        # the frames.
        if data[common.TypeRole] == common.SequenceItem:
            intframes = [int(f) for f in data[common.FramesRole]]
            padding = len(data[common.FramesRole][0])
            rangestring = common.get_ranges(intframes, padding)

            seq = data[common.SequenceRole]
            startpath = seq.group(1) + unicode(min(intframes)).zfill(padding) + seq.group(3) + u'.' + seq.group(4)
            endpath = seq.group(1) + unicode(max(intframes)).zfill(padding) + seq.group(3) + u'.' + seq.group(4)
            seqpath = seq.group(1) + u'[' + rangestring + u']' + seq.group(3) + u'.' + seq.group(4)
            seqname = seqpath.split(u'/')[-1]

            # Setting the path names
            data[common.StartpathRole] = startpath
            data[common.EndpathRole] = endpath
            data[QtCore.Qt.StatusTipRole] = seqpath
            data[QtCore.Qt.ToolTipRole] = seqpath
            data[QtCore.Qt.DisplayRole] = seqname
            data[QtCore.Qt.EditRole] = seqname

            # We saved the DirEntry instances previously in `__initdata__` but
            # only for the thread to extract the information from it.
            if data[common.EntryRole]:
                mtime = 0
                for entry in data[common.EntryRole]:
                    stat = entry.stat()
                    mtime = stat.st_mtime if stat.st_mtime > mtime else mtime
                    data[common.SortBySize] += stat.st_size
                data[common.SortByLastModified] = mtime
                mtime = common.qlast_modified(mtime)

                info_string = unicode(len(intframes)) + u'files;' + mtime.toString(u'dd') + u'/' + mtime.toString(u'MM') + u'/' + mtime.toString(u'yyyy') + u' ' + mtime.toString(u'hh') + u':' + mtime.toString(u'mm') + u';' + common.byte_to_string(data[common.SortBySize])
                data[common.FileDetailsRole] = info_string

        if data[common.TypeRole] == common.FileItem:
            if data[common.EntryRole]:
                stat = data[common.EntryRole][0].stat()
                mtime = stat.st_mtime
                data[common.SortByLastModified] = mtime
                mtime = common.qlast_modified(mtime)
                data[common.SortBySize] = stat.st_size
                info_string = mtime.toString(u'dd') + u'/' + mtime.toString(u'MM') + u'/' + mtime.toString(u'yyyy') + u' ' + mtime.toString(u'hh') + u':' + mtime.toString(u'mm') + u';' + common.byte_to_string(data[common.SortBySize])
                data[common.FileDetailsRole] = info_string

        # Finally, we set the FileInfoLoaded flag to indicate this item
        # has loaded the file data successfully
        data[common.FileInfoLoaded] = True
        index.model().updateIndex.emit(index)


class SecondaryFileInfoWorker(FileInfoWorker):
    """The worker associated with the ``SecondaryFileInfoThread``.

    The worker performs  the same function as ``FileInfoWorker`` but
    it has it own queue and is concerned with iterating over all file-items.

    """
    queue = Unique(999999)
    indexes_in_progress = []

    @QtCore.Slot()
    def begin_processing(self):
        """Instead of relying on a queue, we will use this to set all file information
        data on the source-model. There's only one thread for this worker.

        """
        try:
            while not self.shutdown_requested:
                time.sleep(1.5)  # Will wait n secs between each tries

                model = self.model
                if not model:
                    continue
                if model.file_info_loaded:
                    continue

                all_loaded = True
                data = model.model_data()
                for n in xrange(model.rowCount()):
                    index = model.index(n, 0)

                    if not data[n][common.FileInfoLoaded]:
                        model.InfoThread.Worker.process_index(index)
                        all_loaded = False

                if all_loaded:
                    model.file_info_loaded = True
                    sorted_by_name = model.sort_role() in (common.SortBySize, common.SortByLastModified)
                    if not sorted_by_name or not model.sort_order():
                        model.sortingChanged.emit(model.sort_role(), model.sort_order())

        except Queue.Empty:
            pass
        except:
            sys.stderr.write(u'{}\n'.format(traceback.format_exc()))
        finally:
            if self.shutdown_requested:
                self.finished.emit()
            else:
                self.begin_processing()


class FileThumbnailWorker(BaseWorker):
    """The worker associated with the ``FileThumbnailThread``.

    The worker is responsible for loading the existing thumbnail images from
    the cache folder, and if needed and possible, generating new thumbnails from
    the source file.

    """
    queue = Unique(999)
    indexes_in_progress = []

    @staticmethod
    @validate_index
    @QtCore.Slot(QtCore.QModelIndex)
    def process_index(index, make=True):
        """The static method responsible for querrying the file item's thumbnail.

        We will get the thumbnail's path, check if a cached thumbnail exists already,
        then load it. If there's no thumbnail, we will try to generate a thumbnail
        using OpenImageIO.

        Args:
            make (bool): Will generate a thumbnail image if there isn't one already

        """
        if index.flags() & common.MarkedAsArchived:
            return

        # The model might be loading...
        if not index.model():
            return
        data = index.model().model_data()
        if not data:
            return

        try:
            data = index.model().model_data()[index.row()]
        except KeyError:
            return

        db = bookmark_db.get_db(index)
        if not db:
            return

        data[common.ThumbnailPathRole] = db.thumbnail_path(
            data[QtCore.Qt.StatusTipRole])

        # This is a less than elegant solution for making the thumbnail size
        # of the AssetsWidget are not sceled
        import gwbrowser.assetswidget as assetswidget
        if isinstance(index.model(), assetswidget.AssetModel):
            height = data[QtCore.Qt.SizeHintRole].height() - common.ROW_SEPARATOR
        else:
            height = delegate.ROW_HEIGHT - common.ROW_SEPARATOR

        ext = data[QtCore.Qt.StatusTipRole].split(u'.')[-1].lower()
        image = None

        # Checking if we can load an existing image
        if QtCore.QFileInfo(data[common.ThumbnailPathRole]).exists():
            image = ImageCache.get(
                data[common.ThumbnailPathRole], height, overwrite=True)
            if image:
                color = ImageCache.get(
                    data[common.ThumbnailPathRole], u'backgroundcolor')
                data[common.ThumbnailRole] = image
                data[common.ThumbnailBackgroundRole] = color
                data[common.FileThumbnailLoaded] = True
                index.model().updateIndex.emit(index)
                return

        # If the item doesn't have a saved thumbnail we will check if
        # OpenImageIO is able to make a thumbnail for it:
        if index.model().generate_thumbnails and make and ext in common.oiio_formats:
            model = index.model()
            data = model.model_data()[index.row()]
            spinner_pixmap = ImageCache.get(
                common.rsc_path(__file__, u'spinner'),
                data[QtCore.Qt.SizeHintRole].height() - common.ROW_SEPARATOR)
            data[common.ThumbnailRole] = spinner_pixmap
            data[common.ThumbnailBackgroundRole] = common.THUMBNAIL_BACKGROUND

            data[common.FileThumbnailLoaded] = False
            index.model().updateIndex.emit(index)

            oiio_make_thumbnail(index)


class FileInfoThread(BaseThread):
    """Thread controller associated with the ``FilesModel``."""
    Worker = FileInfoWorker


class SecondaryFileInfoThread(BaseThread):
    """Thread controller associated with the ``FilesModel``."""
    Worker = SecondaryFileInfoWorker


class FileThumbnailThread(BaseThread):
    """Thread controller associated with the ``FilesModel``."""
    Worker = FileThumbnailWorker


class FilesWidgetContextMenu(BaseContextMenu):
    """Context menu associated with the `FilesWidget`."""

    def __init__(self, index, parent=None):
        super(FilesWidgetContextMenu, self).__init__(index, parent=parent)
        # Adding persistent actions
        self.add_location_toggles_menu()

        self.add_separator()

        if index.isValid():
            self.add_mode_toggles_menu()

        self.add_separator()

        if index.isValid():
            self.add_reveal_item_menu()
            self.add_rv_menu()
            self.add_copy_menu()

        self.add_separator()
        #
        self.add_sort_menu()
        self.add_collapse_sequence_menu()
        #
        self.add_separator()
        #
        self.add_display_toggles_menu()

        self.add_separator()

        self.add_refresh_menu()


class FilesModel(BaseModel):
    """The model used store individual and collapsed sequence files found inside
    an asset.

    Every asset contains subfolders, eg. the ``scenes``, ``textures``, ``cache``
    folders. The model will load file-data associated with each of those
    subfolders and save it in ``self._data`` using a **data key**.

    .. code-block:: python

       self._data = {}
       self._data['scenes'] = {} # 'scenes' is a data-key
       self._data['textures'] = {} # 'textures' is a data-key

    To reiterate, the name of the asset subfolders will become our *data keys*.
    Switching between data keys is done by emitting the ``dataKeyChanged``
    signal.

    Note:
        ``datakeywidget.py`` defines the widget and model used to control then
        current data-key.

    """
    InfoThread = FileInfoThread
    SecondaryInfoThread = SecondaryFileInfoThread
    ThumbnailThread = FileThumbnailThread

    def __init__(self, thread_count=common.FTHREAD_COUNT, parent=None):
        super(FilesModel, self).__init__(thread_count=thread_count, parent=parent)
        # Only used to cache the thumbnails
        self._extension_thumbnails = {}
        self._extension_thumbnail_backgrounds = {}
        self._defined_thumbnails = set(
            common.creative_cloud_formats +
            common.exports_formats +
            common.scene_formats +
            common.misc_formats
        )

    def reset_thumbnails(self, force=True):
        """Resets all thumbnail-data to its initial state.
        This in turn allows the `FileThumbnailWorker` to reload all the thumbnails.

        """
        _rowsize = delegate.ROW_HEIGHT - common.ROW_SEPARATOR
        thumbnails = self.get_default_thumbnails(overwrite=True)

        dkey = self.data_key()
        for k in (common.FileItem, common.SequenceItem):
            for item in self._data[dkey][k].itervalues():
                ext = item[QtCore.Qt.StatusTipRole].split(u'.')[-1]
                if not ext:
                    continue

                if ext in thumbnails:
                    placeholder_image = thumbnails[ext]
                    default_thumbnail_image = thumbnails[ext]
                    default_background_color = thumbnails[ext + u':backgroundcolor']
                else:
                    placeholder_image = thumbnails[u'placeholder']
                    default_thumbnail_image = thumbnails[u'placeholder']
                    default_background_color = thumbnails[u'placeholder:backgroundcolor']

                item[common.FileThumbnailLoaded] = False
                item[common.DefaultThumbnailRole] = default_thumbnail_image
                item[common.DefaultThumbnailBackgroundRole] = default_background_color
                item[common.ThumbnailPathRole] = None
                item[common.ThumbnailRole] = placeholder_image
                item[common.ThumbnailBackgroundRole] = default_background_color

    def _entry_iterator(self, path):
        for entry in gwscandir.scandir(path):
            if entry.is_dir():
                for entry in self._entry_iterator(entry.path):
                    yield entry
            else:
                yield entry

    def get_default_thumbnails(self, overwrite=False):
        d = {}
        for ext in set(
            common.creative_cloud_formats +
            common.exports_formats +
            common.scene_formats +
            common.misc_formats
        ):
            ext = ext.lower()
            _ext_path = common.rsc_path(__file__, ext)
            d[ext] = ImageCache.get(
                _ext_path,
                delegate.ROW_HEIGHT - common.ROW_SEPARATOR,
                overwrite=overwrite
            )
            k = _ext_path + u':backgroundcolor'
            k = k.lower()
            d[ext + u':backgroundcolor'] = ImageCache._data[k]

        d[u'placeholder'] = ImageCache.get(
            common.rsc_path(__file__, u'placeholder'),
            delegate.ROW_HEIGHT - common.ROW_SEPARATOR)
        d[u'placeholder:backgroundcolor'] = common.THUMBNAIL_BACKGROUND
        return d

    @initdata
    def __initdata__(self):
        """The method is responsible for getting the bare-bones file and
        sequence definitions by running a file-iterator stemming from
        ``self.parent_path``.

        Getting all additional information, like description, item flags,
        thumbnails are costly and therefore are populated by thread-workers.

        The method will iterate through all files in every subfolder and will
        automatically save individual ``FileItems`` and collapsed
        ``SequenceItems``.

        Switching between the two datasets is done via emitting the
        ``dataTypeChanged`` signal.

        Note:
            Experiencing serious performance issues with the built-in
            QDirIterator on Mac OS X samba shares and the performance isn't
            great on windows either. Querrying the filesystem using the method
            is magnitudes slower than using the same methods on windows.

            A workaround I found was to use Python 3+'s ``scandir`` module. Both
            on Windows and Mac OS X the performance seems to be adequate.

        """
        def dflags():
            """The default flags to apply to the item."""
            return (
                QtCore.Qt.ItemNeverHasChildren |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable)

        self.reset_thread_worker_queues()

        # Invalid asset, we'll do nothing.
        if not self.parent_path:
            return
        if not all(self.parent_path):
            return

        dkey = self.data_key()
        if not dkey:
            return
        dkey = dkey.lower()

        self._data[dkey] = {
            common.FileItem: {},
            common.SequenceItem: {}
        }
        seqs = {}

        rowsize = QtCore.QSize(0, delegate.ROW_HEIGHT)
        _rowsize = delegate.ROW_HEIGHT - common.ROW_SEPARATOR
        thumbnails = self.get_default_thumbnails()

        favourites = settings_.local_settings.favourites()
        sfavourites = set(favourites)
        activefile = settings_.local_settings.value(u'activepath/file')

        server, job, root, asset = self.parent_path
        location_is_filtered = dkey in common.NameFilters
        location_path = u'/'.join(self.parent_path).lower() + u'/' + dkey

        nth = 987
        c = 0
        for entry in self._entry_iterator(location_path):
            # skipping directories
            if entry.is_dir():
                continue
            filename = entry.name.lower()

            if filename[0] == u'.':
                continue
            if u'thumbs.db' in filename:
                continue

            filepath = entry.path.lower().replace(u'\\', u'/')
            ext = filename.split(u'.')[-1]

            if location_is_filtered:
                if ext not in common.NameFilters[dkey]:
                    continue

            # Progress bar
            c += 1
            if not c % nth:
                self.messageChanged.emit(u'Found' + unicode(c) + u'files...')
                QtWidgets.QApplication.instance().processEvents(
                    QtCore.QEventLoop.ExcludeUserInputEvents)


            # Getting the fileroot
            fileroot = filepath.replace(location_path, u'')
            fileroot = u'/'.join(fileroot.split(u'/')[:-1]).strip(u'/')
            seq = common.get_sequence(filepath)

            if ext in thumbnails:
                placeholder_image = thumbnails[ext]
                default_thumbnail_image = thumbnails[ext]
                default_background_color = thumbnails[ext + u':backgroundcolor']
            else:
                placeholder_image = thumbnails[u'placeholder']
                default_thumbnail_image = thumbnails[u'placeholder']
                default_background_color = thumbnails[u'placeholder:backgroundcolor']

            flags = dflags()

            if seq:
                seqpath = seq.group(1) + u'[0]' + seq.group(3) + u'.' + seq.group(4)
                seqpath = seqpath.lower()
                if seqpath in sfavourites:
                    flags = flags | common.MarkedAsFavourite
            else:
                if filepath in sfavourites:
                    flags = flags | common.MarkedAsFavourite

            if activefile:
                if activefile in filepath:
                    flags = flags | common.MarkedAsActive

            idx = len(self._data[dkey][common.FileItem])
            self._data[dkey][common.FileItem][idx] = {
                QtCore.Qt.DisplayRole: filename,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.ToolTipRole: filepath,
                QtCore.Qt.SizeHintRole: rowsize,
                #
                common.EntryRole: [entry, ],
                common.FlagsRole: flags,
                common.ParentPathRole: (server, job, root, asset, dkey, fileroot),
                common.DescriptionRole: u'',
                common.TodoCountRole: 0,
                common.FileDetailsRole: u'',
                common.SequenceRole: seq,
                common.FramesRole: [],
                common.FileInfoLoaded: False,
                common.StartpathRole: None,
                common.EndpathRole: None,
                #
                common.FileThumbnailLoaded: False,
                common.DefaultThumbnailRole: default_thumbnail_image,
                common.DefaultThumbnailBackgroundRole: default_background_color,
                common.ThumbnailPathRole: None,
                common.ThumbnailRole: placeholder_image,
                common.ThumbnailBackgroundRole: default_background_color,
                #
                common.TypeRole: common.FileItem,
                #
                common.SortByName: common.namekey(filepath),
                common.SortByLastModified: 0,
                common.SortBySize: 0,
            }

            # If the file in question is a sequence, we will also save a reference
            # to it in `self._model_data[location][True]` dictionary.
            if seq:
                # If the sequence has not yet been added to our dictionary
                # of seqeunces we add it here
                if seqpath not in seqs:  # ... and create it if it doesn't exist
                    seqname = seqpath.split(u'/')[-1]
                    flags = dflags()

                    if seqpath in sfavourites:
                        flags = flags | common.MarkedAsFavourite

                    seqs[seqpath] = {
                        QtCore.Qt.DisplayRole: seqname,
                        QtCore.Qt.EditRole: seqname,
                        QtCore.Qt.StatusTipRole: seqpath,
                        QtCore.Qt.ToolTipRole: seqpath,
                        QtCore.Qt.SizeHintRole: rowsize,
                        common.EntryRole: [],
                        common.FlagsRole: flags,
                        common.ParentPathRole: (server, job, root, asset, dkey, fileroot),
                        common.DescriptionRole: u'',
                        common.TodoCountRole: 0,
                        common.FileDetailsRole: u'',
                        common.SequenceRole: seq,
                        common.FramesRole: [],
                        common.FileInfoLoaded: False,
                        common.StartpathRole: None,
                        common.EndpathRole: None,
                        #
                        common.FileThumbnailLoaded: False,
                        common.DefaultThumbnailRole: default_thumbnail_image,
                        common.DefaultThumbnailBackgroundRole: default_background_color,
                        common.ThumbnailPathRole: None,
                        common.ThumbnailRole: placeholder_image,
                        common.ThumbnailBackgroundRole: default_background_color,
                        #
                        common.TypeRole: common.SequenceItem,
                        common.SortByName: common.namekey(seqpath),
                        common.SortByLastModified: 0,
                        common.SortBySize: 0,  # Initializing with null-size
                    }

                seqs[seqpath][common.FramesRole].append(seq.group(2))
                seqs[seqpath][common.EntryRole].append(entry)
            else:
                seqs[filepath] = self._data[dkey][common.FileItem][idx]

        # Casting the sequence data onto the model
        for v in seqs.itervalues():
            idx = len(self._data[dkey][common.SequenceItem])

            # A sequence with only one element is not a sequence!
            if len(v[common.FramesRole]) == 1:
                _seq = v[common.SequenceRole]
                filepath = _seq.group(1) + v[common.FramesRole][0] + _seq.group(3) + u'.' + _seq.group(4)
                filename = filepath.split(u'/')[-1]
                v[QtCore.Qt.DisplayRole] = filename
                v[QtCore.Qt.EditRole] = filename
                v[QtCore.Qt.StatusTipRole] = filepath
                v[QtCore.Qt.ToolTipRole] = filepath
                v[common.TypeRole] = common.FileItem
                v[common.SortByName] = filepath
                v[common.SortByLastModified] = 0

                flags = dflags()
                if filepath.lower() in sfavourites:
                    flags = flags | common.MarkedAsFavourite

                if activefile:
                    if activefile in filepath:
                        flags = flags | common.MarkedAsActive

                v[common.FlagsRole] = flags

            elif len(v[common.FramesRole]) == 0:
                v[common.TypeRole] = common.FileItem
            else:
                if activefile:
                    _seq = v[common.SequenceRole]
                    _firsframe = _seq.group(1) + min(v[common.FramesRole]) + _seq.group(3) + u'.' + _seq.group(4)
                    if activefile in _firsframe:
                        v[common.FlagsRole] = v[common.FlagsRole] | common.MarkedAsActive
            self._data[dkey][common.SequenceItem][idx] = v

    def data_key(self):
        """Current key to the data dictionary."""
        if not self._datakey:
            val = None
            key = u'activepath/location'
            savedval = settings_.local_settings.value(key)
            return savedval.lower() if savedval else val
        return self._datakey

    @QtCore.Slot(unicode)
    def set_data_key(self, val):
        """Slot used to save data key to the model instance and the local
        settings.

        Each subfolder inside the root folder, defined by``parent_path``,
        corresponds to a `key`. We use these keys to save model data associated
        with these folders.

        It's important to make sure the key we're about to be set corresponds to
        an existing folder. We will use a reasonable default if the folder does
        not exist.

        """
        k = u'activepath/location'
        stored_value = settings_.local_settings.value(k)
        stored_value = stored_value.lower() if stored_value else stored_value
        self._datakey = self._datakey.lower() if self._datakey else self._datakey
        val = val.lower() if val else val

        # Nothing to do for us when the parent is not set
        if not self.parent_path:
            return

        if self._datakey is None and stored_value:
            self._datakey = stored_value

        # We are in sync with a valid value set already
        if stored_value is not None and self._datakey == val == stored_value:
            return

        # Update the local_settings
        if self._datakey == val and val != stored_value:
            settings_.local_settings.setValue(k, val)
            return

        if val is not None and val == self._datakey:
            return

        # About to set a new value. We can accept or reject this...
        entries = self.can_accept_datakey(val)
        if not entries:
            self._datakey = None
            return

        if val.lower() in entries:
            self._datakey = val
            settings_.local_settings.setValue(k, val)
            return
        elif val not in entries and self._datakey in entries:
            val = self._datakey.lower()
            settings_.local_settings.setValue(k, self._datakey)
            return
        # This is a default fallback...
        elif val not in entries and u'scenes' in entries:
                val = u'scenes'

        val = entries[0]
        self._datakey = val
        settings_.local_settings.setValue(k, val)

    def can_accept_datakey(self, val):
        """Checks if the key about to be set corresponds to a real
        folder. If not, we will try to pick a default value, u'scenes', or
        the first folder if the default does not exist.

        """
        if not self.parent_path:
            return False
        path = u'/'.join(self.parent_path)
        entries = [f.name.lower() for f in gwscandir.scandir(path)]
        if not entries:
            return False
        if val.lower() not in entries:
            return False
        return entries

    def canDropMimeData(self, data, action, row, column):
        return False

    def supportedDropActions(self):
        return QtCore.Qt.IgnoreAction

    def supportedDragActions(self):
        return QtCore.Qt.CopyAction

    def mimeData(self, indexes):
        """The data necessary for supporting drag and drop operations are
        constructed here.

        There is ambiguity in the absence of any good documentation I could find
        regarding what mime types have to be defined exactly for fully
        supporting drag and drop on all platforms.

        Note:
            On windows, ``application/x-qt-windows-mime;value="FileName"`` and
            ``application/x-qt-windows-mime;value="FileNameW"`` types seems to be
            necessary, but on MacOS a simple uri list seem to suffice.

        """
        def add_path_to_mime(mime, path):
            """Adds the given path to the mime data."""
            path = QtCore.QFileInfo(path).absoluteFilePath()
            path = QtCore.QDir.toNativeSeparators(path)

            mime.setUrls(mime.urls() + [QtCore.QUrl.fromLocalFile(path), ])
            data = common.ubytearray(QtCore.QDir.toNativeSeparators(path))
            mime.setData(
                'application/x-qt-windows-mime;value="FileName"', data)
            mime.setData(
                'application/x-qt-windows-mime;value="FileNameW"', data)

            return mime

        mime = QtCore.QMimeData()
        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        no_modifier = modifiers == QtCore.Qt.NoModifier
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier

        for index in indexes:
            if not index.isValid():
                continue
            path = index.data(QtCore.Qt.StatusTipRole)

            if no_modifier:
                path = common.get_sequence_endpath(path)
                add_path_to_mime(mime, path)
            elif alt_modifier and shift_modifier:
                path = QtCore.QFileInfo(path).dir().path()
                add_path_to_mime(mime, path)
            elif alt_modifier:
                path = common.get_sequence_startpath(path)
                add_path_to_mime(mime, path)
            elif shift_modifier:
                paths = common.get_sequence_paths(index)
                for path in paths:
                    add_path_to_mime(mime, path)
        return mime



class DragPixmap(QtWidgets.QWidget):
    """The widget used to drag the dragged items pixmap and name."""

    def __init__(self, pixmap, text, parent=None):
        super(DragPixmap, self).__init__(parent=parent)
        self._pixmap = pixmap
        self._text = text

        font = common.PrimaryFont
        metrics = QtGui.QFontMetricsF(font)
        self._text_width = metrics.width(text)

        width = self._text_width + common.MARGIN
        width = 640 + common.MARGIN if width > 640 else width

        self.setFixedHeight(pixmap.height())
        self.setFixedWidth(
            pixmap.width() + common.INDICATOR_WIDTH + width + common.INDICATOR_WIDTH)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAutoFillBackground(True)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.adjustSize()

    @classmethod
    def pixmap(cls, pixmap, text):
        """Returns the widget as a rendered pixmap."""
        w = cls(pixmap, text)
        pixmap = QtGui.QPixmap(w.size())
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        w.render(painter, QtCore.QPoint(), QtGui.QRegion())
        return pixmap

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.SECONDARY_BACKGROUND)
        painter.setOpacity(0.6)
        painter.drawRoundedRect(self.rect(), 4, 4)
        painter.setOpacity(1.0)

        pixmap_rect = QtCore.QRect(0, 0, self.height(), self.height())
        painter.drawPixmap(pixmap_rect, self._pixmap, self._pixmap.rect())

        width = self._text_width + common.INDICATOR_WIDTH
        width = 640 if width > 640 else width
        rect = QtCore.QRect(
            self._pixmap.rect().width() + common.INDICATOR_WIDTH,
            0,
            width,
            self.height()
        )
        common.draw_aliased_text(
            painter,
            common.PrimaryFont,
            rect,
            self._text,
            QtCore.Qt.AlignCenter,
            common.TEXT_SELECTED
        )
        painter.end()


class FilesWidget(ThreadedBaseWidget):
    """The view used to display the contents of a ``FilesModel`` instance.
    """
    SourceModel = FilesModel
    Delegate = FilesWidgetDelegate
    ContextMenu = FilesWidgetContextMenu

    def __init__(self, parent=None):
        super(FilesWidget, self).__init__(parent=parent)
        self.drag_source_index = QtCore.QModelIndex()

        self.setWindowTitle(u'Files')
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDropIndicatorShown(False)
        # self.setAutoScroll(True)

        # I'm not sure why but the proxy is not updated properly after refresh
        self.model().sourceModel().dataSorted.connect(self.model().invalidate)

    @QtCore.Slot(unicode)
    @QtCore.Slot(unicode)
    def new_file_added(self, data_key, file_path):
        """Slot to be called when a new file has been added and
        we want to show it the list.

        """
        if not data_key:
            return

        # Setting the data key
        self.model().sourceModel().dataKeyChanged.emit(data_key)
        # And reloading the model...
        self.model().sourceModel().modelDataResetRequested.emit()

        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0)
            path = index.data(QtCore.Qt.StatusTipRole)
            path = common.get_sequence_endpath(path)
            if path.lower() == file_path:
                self.scrollTo(
                    index,
                    QtWidgets.QAbstractItemView.PositionAtCenter)
                self.selectionModel().setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect)
                break

    def eventFilter(self, widget, event):
        """Custom event filter to drawm the background pixmap."""
        super(FilesWidget, self).eventFilter(widget, event)

        if widget is not self:
            return False

        if event.type() == QtCore.QEvent.Paint:
            # Let's paint the icon of the current mode
            painter = QtGui.QPainter()
            painter.begin(self)
            pixmap = ImageCache.get_rsc_pixmap(
                u'files', QtGui.QColor(0, 0, 0, 20), 180)
            rect = pixmap.rect()
            rect.moveCenter(self.rect().center())
            painter.drawPixmap(rect, pixmap, pixmap.rect())
            painter.end()
            return True

        return False

    def inline_icons_count(self):
        if self.buttons_hidden():
            return 0
        return 3

    def action_on_enter_key(self):
        self.activate(self.selectionModel().currentIndex())

    @QtCore.Slot(QtCore.QModelIndex)
    def save_activated(self, index):
        """Sets the current file as the ``active`` file."""
        parent_role = index.data(common.ParentPathRole)
        if not parent_role:
            return
        if len(parent_role) < 5:
            return

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        filepath = parent_role[5] +  u'/' + common.get_sequence_startpath(file_info.fileName())
        settings_.local_settings.setValue(u'activepath/file', filepath)

    def mouseDoubleClickEvent(self, event):
        """We will check if the event is over one of the sub-dir rectangles,
        and if so we will reveal the folder in the file-explorer.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
        if index.flags() & common.MarkedAsArchived:
            return

        rect = self.visualRect(index)
        rectangles = self.itemDelegate().get_rectangles(rect)

        if self.buttons_hidden():
            return super(FilesWidget, self).mouseDoubleClickEvent(event)

        clickable_rectangles = self.itemDelegate().get_clickable_rectangles(index, rectangles)
        cursor_position = self.mapFromGlobal(QtGui.QCursor().pos())

        if not clickable_rectangles:
            return super(FilesWidget, self).mouseDoubleClickEvent(event)

        root_dir = []
        if clickable_rectangles[0][0].contains(cursor_position):
            return self.description_editor_widget.show()

        for item in clickable_rectangles:
            rect, text = item

            if not text:
                continue

            root_dir.append(text)
            if rect.contains(cursor_position):
                path = u'/'.join(index.data(common.ParentPathRole)[0:5]).rstrip('/')
                root_path = u'/'.join(root_dir).strip(u'/')
                path = path + u'/' + root_path
                return common.reveal(path)

        return super(FilesWidget, self).mouseDoubleClickEvent(event)

    def startDrag(self, supported_actions):
        """Creating a custom drag object here for displaying setting hotspots."""
        index = self.selectionModel().currentIndex()
        model = self.model().sourceModel()

        if not index.isValid():
            return
        if not index.data(QtCore.Qt.StatusTipRole):
            return
        if not index.data(common.ParentPathRole):
            return

        self.drag_source_index = index
        drag = QtGui.QDrag(self)
        # Getting the data from the source model
        drag.setMimeData(model.mimeData([index, ]))

        # Setting our custom cursor icons
        option = QtWidgets.QStyleOptionViewItem()
        option.initFrom(self)
        height = self.itemDelegate().sizeHint(option, index).height()

        def px(s):
            return ImageCache.get_rsc_pixmap(s, None, common.INLINE_ICON_SIZE)

        # Set drag icon
        drag.setDragCursor(px('CopyAction'), QtCore.Qt.CopyAction)
        drag.setDragCursor(px('MoveAction'), QtCore.Qt.MoveAction)
        # drag.setDragCursor(px('LinkAction'), QtCore.Qt.LinkAction)
        drag.setDragCursor(px('IgnoreAction'), QtCore.Qt.ActionMask)
        drag.setDragCursor(px('IgnoreAction'), QtCore.Qt.IgnoreAction)
        # drag.setDragCursor(px('TargetMoveAction'), QtCore.Qt.TargetMoveAction)

        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        no_modifier = modifiers == QtCore.Qt.NoModifier
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier

        # Set pixmap
        pixmap = None
        path = index.data(QtCore.Qt.StatusTipRole)

        bookmark = u'/'.join(index.data(common.ParentPathRole)[:3])
        path = path.replace(bookmark, u'')
        path = path.strip(u'/')
        if no_modifier:
            pixmap = index.data(common.ThumbnailRole)
            if not pixmap:
                pixmap = ImageCache.get_rsc_pixmap(
                    u'files', common.SECONDARY_TEXT, height)
            path = common.get_sequence_endpath(path)
        elif alt_modifier and shift_modifier:
            pixmap = ImageCache.get_rsc_pixmap(
                u'folder', common.SECONDARY_TEXT, height)
            path = QtCore.QFileInfo(path).dir().path()
        elif alt_modifier:
            pixmap = ImageCache.get_rsc_pixmap(
                u'files', common.SECONDARY_TEXT, height)
            path = common.get_sequence_startpath(path)
        elif shift_modifier:
            path = common.get_sequence_startpath(path) + u', ++'
            pixmap = ImageCache.get_rsc_pixmap(
                u'multiples_files', common.SECONDARY_TEXT, height)
        else:
            return

        self.update(index)
        pixmap = DragPixmap.pixmap(pixmap, path)
        drag.setPixmap(pixmap)

        lc = self.parent().parent().listcontrolwidget
        lc.drop_overlay.show()
        drag.exec_(supported_actions)
        lc.drop_overlay.hide()
        self.drag_source_index = QtCore.QModelIndex()

    def mouseReleaseEvent(self, event):
        """The files widget has a few addittional clickable inline icons
        that control filtering we set the action for here.

        ``Shift`` modifier will add a "positive" filter and hide all items
        that does not contain the given text.

        The ``alt`` or control modifiers will add a "negative filter"
        and hide the selected subfolder from the view.

        """
        cursor_position = self.mapFromGlobal(QtGui.QCursor().pos())
        index = self.indexAt(cursor_position)

        if not index.isValid():
            return super(FilesWidget, self).mouseReleaseEvent(event)

        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        no_modifier = modifiers == QtCore.Qt.NoModifier
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier
        control_modifier = modifiers & QtCore.Qt.ControlModifier

        rect = self.visualRect(index)
        if self.buttons_hidden():
            return super(FilesWidget, self).mouseReleaseEvent(event)

        rectangles = self.itemDelegate().get_rectangles(rect)
        clickable_rectangles = self.itemDelegate().get_clickable_rectangles(index, rectangles)
        cursor_position = self.mapFromGlobal(QtGui.QCursor().pos())
        if not clickable_rectangles:
            return super(FilesWidget, self).mouseReleaseEvent(event)

        for idx, item in enumerate(clickable_rectangles):
            if idx == 0: # First rectanble is always the description editor
                continue
            rect, text = item
            text = text.lower()

            if rect.contains(cursor_position):
                filter_text = self.model().filter_text().lower()
                filter_text = filter_text if filter_text else u''

                # Shift modifier will add a "positive" filter and hide all items
                # that does not contain the given text.
                if shift_modifier:
                    folder_filter = u'"/' + text + u'/"'

                    if folder_filter in filter_text:
                        filter_text = filter_text.replace(folder_filter, u'')
                    else:
                        filter_text = filter_text + u' ' + folder_filter
                    self.model().filterTextChanged.emit(filter_text)
                    self.repaint(self.rect())
                    return super(FilesWidget, self).mouseReleaseEvent(event)

                # The alt or control modifiers will add a "negative filter"
                # and hide the selected subfolder from the view
                if alt_modifier or control_modifier:
                    folder_filter = u'--"/' + text + u'/"'
                    _folder_filter = u'"/' + text + u'/"'

                    if filter_text:
                        if _folder_filter in filter_text:
                            filter_text = filter_text.replace(_folder_filter, u'')
                        if folder_filter not in filter_text:
                            folder_filter = filter_text + u' ' + folder_filter

                    self.model().filterTextChanged.emit(folder_filter)
                    self.repaint(self.rect())
                    return super(FilesWidget, self).mouseReleaseEvent(event)

        super(FilesWidget, self).mouseReleaseEvent(event)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = FilesWidget()
    widget.show()
    app.exec_()
