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

import sys
import re
import time
import traceback
from functools import wraps

from PySide2 import QtWidgets, QtCore, QtGui

from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.baselistwidget import BaseInlineIconWidget
from gwbrowser.baselistwidget import ThreadedBaseWidget
from gwbrowser.baselistwidget import BaseModel
from gwbrowser.baselistwidget import FilterProxyModel
from gwbrowser.baselistwidget import initdata
from gwbrowser.baselistwidget import validate_index

import gwbrowser.gwscandir as gwscandir
import gwbrowser.common as common
from gwbrowser.settings import AssetSettings
from gwbrowser.settings import local_settings
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
    def process_index(index, update=True, exists=False):
        """The main processing function called by the worker.
        Upon loading all the information ``FileInfoLoaded`` is set to ``True``.

        """
        if index.data(common.FileInfoLoaded):
            return
        if not index.data(common.ParentRole):
            return

        try:
            data = index.model().model_data()[index.row()]
        except:
            return

        settings = AssetSettings(index)

        # Item description
        description = settings.value(u'config/description')
        if description:
            data[common.DescriptionRole] = description

        # Todos
        todos = settings.value(u'config/todos')
        todocount = 0
        if todos:
            todocount = [k for k in todos if todos[k][u'text'] and not todos[k][u'checked']]
            todocount = len(todocount)
        else:
            todocount = 0
        data[common.TodoCountRole] = todocount

        # For sequence items we will work out the name of the sequence
        # based on the frames contained in the sequence
        # This is a moderately costly operation hence, we're doing this here
        # on the thread...
        if data[common.TypeRole] == common.SequenceItem:
            intframes = [int(f) for f in data[common.FramesRole]]
            padding = len(data[common.FramesRole][0])
            rangestring = common.get_ranges(intframes, padding)

            p = data[common.SequenceRole].expand(
                ur'\1{}\3.\4')
            startpath = p.format(unicode(min(intframes)).zfill(padding))
            endpath = p.format(unicode(max(intframes)).zfill(padding))
            seqpath = p.format(u'[{}]'.format(rangestring))
            seqname = seqpath.split(u'/')[-1]

            # Setting the path names
            data[common.StartpathRole] = startpath
            data[common.EndpathRole] = endpath
            data[QtCore.Qt.StatusTipRole] = seqpath
            data[QtCore.Qt.ToolTipRole] = seqpath
            data[QtCore.Qt.DisplayRole] = seqname
            data[QtCore.Qt.EditRole] = seqname

            # File description string
            if data[common.EntryRole]:
                mtime = 0
                for entry in data[common.EntryRole]:
                    stat = entry.stat()
                    mtime = stat.st_mtime if stat.st_mtime > mtime else mtime
                    data[common.SortBySize] += stat.st_size
                data[common.SortByLastModified] = mtime
                mtime = common.qlast_modified(mtime)

                info_string = u'{count} files;{day}/{month}/{year} {hour}:{minute};{size}'.format(
                    count=len(intframes),
                    day=mtime.toString(u'dd'),
                    month=mtime.toString(u'MM'),
                    year=mtime.toString(u'yyyy'),
                    hour=mtime.toString(u'hh'),
                    minute=mtime.toString(u'mm'),
                    size=common.byte_to_string(data[common.SortBySize])
                )
                data[common.FileDetailsRole] = info_string
        else:
            if data[common.EntryRole]:
                stat = data[common.EntryRole][0].stat()
                mtime = stat.st_mtime
                data[common.SortByLastModified] = mtime
                mtime = common.qlast_modified(mtime)
                data[common.SortBySize] = stat.st_size
                info_string = u'{day}/{month}/{year} {hour}:{minute};{size}'.format(
                    day=mtime.toString(u'dd'),
                    month=mtime.toString(u'MM'),
                    year=mtime.toString(u'yyyy'),
                    hour=mtime.toString(u'hh'),
                    minute=mtime.toString(u'mm'),
                    size=common.byte_to_string(data[common.SortBySize])
                )
                data[common.FileDetailsRole] = info_string

        # Item flags
        flags = index.flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled

        if settings.value(u'config/archived'):
            flags = flags | common.MarkedAsArchived
        data[common.FlagsRole] = flags

        # We can ask the worker specifically to check if the file exists
        # We're using this for the favourites to remove stale items from our list
        if exists:
            _path = common.get_sequence_endpath(data[QtCore.Qt.StatusTipRole])
            file_info = QtCore.QFileInfo(_path)
            if not file_info.exists():
                flags = QtCore.Qt.ItemIsEditable | common.MarkedAsArchived
                data[common.FlagsRole] = flags

        # Finally, we set the FileInfoLoaded flag to indicate this item
        # has loaded the file data successfully
        data[common.FileInfoLoaded] = True

        # Forces a ui repaint to show the data-change
        if update:
            index.model().indexUpdated.emit(index)


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
                time.sleep(1)  # Will wait 1 sec between each tries

                if not self.model:
                    continue
                if self.model.file_info_loaded:
                    continue

                all_loaded = True
                data = self.model.model_data()
                for n in xrange(self.model.rowCount()):
                    index = self.model.index(n, 0)

                    if not data[n][common.FileInfoLoaded]:
                        self.model.InfoThread.Worker.process_index(index, update=True)
                        all_loaded = False

                    if not data[n][common.FileThumbnailLoaded]:
                        self.model.ThumbnailThread.Worker.process_index(
                            index, update=True, make=False)

                if all_loaded:
                    self.model.file_info_loaded = True
        except:
            sys.stderr.write('{}\n'.format(traceback.format_exc()))
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
    def process_index(index, update=True, make=True):
        """The static method responsible for querrying the file item's thumbnail.

        We will get the thumbnail's path, check if a cached thumbnail exists already,
        then load it. If there's no thumbnail, we will try to generate a thumbnail
        using OpenImageIO.

        Args:
            update (bool): Repaints the associated view if the index is visible
            make (bool): Will generate a thumbnail image if there isn't one already

        """
        if not index.data(common.FileInfoLoaded):
            return
        if index.flags() & common.MarkedAsArchived:
            return
        try:
            data = index.model().model_data()[index.row()]
        except KeyError:
            return
        settings = AssetSettings(index)

        data[common.ThumbnailPathRole] = settings.thumbnail_path()
        height = data[QtCore.Qt.SizeHintRole].height() - common.ROW_SEPARATOR
        ext = data[QtCore.Qt.StatusTipRole].split(u'.')[-1].lower()
        image = None

        # Checking if we can load an existing image
        if QtCore.QFileInfo(data[common.ThumbnailPathRole]).exists():
            image = ImageCache.get(
                data[common.ThumbnailPathRole], height, overwrite=True)
            if image:
                color = ImageCache.get(
                    data[common.ThumbnailPathRole], u'BackgroundColor')
                data[common.ThumbnailRole] = image
                data[common.ThumbnailBackgroundRole] = color
                data[common.FileThumbnailLoaded] = True
                if update:
                    index.model().indexUpdated.emit(index)
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

            if update:
                model.indexUpdated.emit(index)

            # Emits an indexUpdated signal if successfully generated the thumbnail
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
            self.add_thumbnail_menu()

        self.add_separator()

        if index.isValid():
            self.add_reveal_item_menu()
            self.add_rv_menu()
            self.add_copy_menu()

        self.add_separator()

        self.add_sort_menu()
        self.add_collapse_sequence_menu()
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

    @initdata
    def __initdata__(self):
        """The method is responsible for getting the bare-bones file and
        sequence definitions by running a file-iterator stemming from
        ``self._parent_item``.

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
        def add_keywords(l):
            """Adds searchable keywords given a list of string."""
            arr = []
            for s in l:
                self._keywords[s] = s
                ns = u'--{}'.format(s)
                self._keywords[ns] = ns

                arr.append(s)
                k = u' '.join(arr).strip()
                self._keywords[k] = k
                nk = u' --'.join(arr).strip()
                self._keywords[nk] = nk

        def dflags():
            """The default flags to apply to the item."""
            return (
                QtCore.Qt.ItemNeverHasChildren |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable)

        self.reset_thread_worker_queues()

        # Invalid asset, we'll do nothing.
        if not self._parent_item:
            return
        if not all(self._parent_item):
            return

        dkey = self.data_key()
        rowsize = QtCore.QSize(0, common.ROW_HEIGHT)

        default_thumbnail_image = ImageCache.get(
            common.rsc_path(__file__, u'placeholder'),
            rowsize.height() - common.ROW_SEPARATOR)
        default_background_color = common.THUMBNAIL_BACKGROUND

        thumbnails = {}
        defined_thumbnails = set(
            common.creative_cloud_formats +
            common.exports_formats +
            common.scene_formats +
            common.misc_formats
        )
        for ext in defined_thumbnails:
            thumbnails[ext] = ImageCache.get(
                common.rsc_path(__file__, ext), rowsize.height())

        self._data[dkey] = {
            common.FileItem: {},
            common.SequenceItem: {}
        }

        seqs = {}

        favourites = local_settings.value(u'favourites')
        favourites = [f.lower() for f in favourites] if favourites else []
        sfavourites = set(favourites)
        activefile = local_settings.value('activepath/file')

        server, job, root, asset = self._parent_item
        location = self.data_key()
        location_is_filtered = location in common.NameFilters
        location_path = (u'{}/{}/{}/{}/{}'.format(
            server, job, root, asset, location
        ))

        regex = re.compile(ur'[\._\-\s]+')

        nth = 987
        c = 0
        for _, _, fileentries in common.walk(location_path):
            for entry in fileentries:
                filename = entry.name

                if filename[0] == u'.':
                    continue
                if u'thumbs.db' in filename.lower():
                    continue

                filepath = entry.path.replace(u'\\', u'/')
                ext = filename.split(u'.')[-1].lower()

                # This line will make sure only extensions we choose to display
                # are actually returned. This is important for the Context widgets
                if location_is_filtered:
                    if ext not in common.NameFilters[location]:
                        continue

                # Progress bar
                c += 1
                if not c % nth:
                    self.messageChanged.emit(
                        u'Found {} files...'.format(c))
                    QtWidgets.QApplication.instance().processEvents(
                        QtCore.QEventLoop.ExcludeUserInputEvents)

                fileroot = filepath.replace(location_path, u'')
                fileroot = u'/'.join(fileroot.split(u'/')[:-1]).strip(u'/')

                seq = common.get_sequence(filepath)

                if ext in defined_thumbnails:
                    placeholder_image = thumbnails[ext]
                else:
                    placeholder_image = default_thumbnail_image

                flags = dflags()

                if filepath.lower() in sfavourites:
                    flags = flags | common.MarkedAsFavourite

                if activefile:
                    if activefile in filepath:
                        flags = flags | common.MarkedAsActive

                # stat = entry.stat()
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
                    common.ParentRole: (server, job, root, asset, location, fileroot),
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
                    common.SortByName: filepath,
                    common.SortByLastModified: 0,
                    common.SortBySize: 0,
                }

                # Keywords for filtering
                # We will prefix folernames with '%%'.
                # This has no significance, just an arbitary prefix that
                # will be used by the FilterEditor to display the folder
                # keywords
                _rr = u'%%{}'.format(fileroot)
                self._keywords[_rr] = _rr
                self._keywords[filename] = filename

                split_root = fileroot.split(u'/')
                _rr = u'%%{}'.format(split_root[0])
                self._keywords[_rr] = _rr
                if len(split_root) <= 4:
                    add_keywords(split_root)
                    add_keywords(regex.split(filename))

                    for _root in split_root:
                        add_keywords(regex.split(_root))
                        self._keywords[_root] = _root

                # If the file in question is a sequence, we will also save a reference
                # to it in `self._model_data[location][True]` dictionary.
                if seq:
                    try:
                        seqpath = u'{}[0]{}.{}'.format(
                            unicode(seq.group(1), 'utf-8'),
                            unicode(seq.group(3), 'utf-8'),
                            unicode(seq.group(4), 'utf-8'))
                    except TypeError:
                        seqpath = u'{}[0]{}.{}'.format(
                            seq.group(1),
                            seq.group(3),
                            seq.group(4))

                    # If the sequence has not yet been added to our dictionary
                    # of seqeunces we add it here
                    if seqpath.lower() not in seqs:  # ... and create it if it doesn't exist
                        seqname = seqpath.split(u'/')[-1]
                        flags = dflags()
                        try:
                            key = u'{}{}.{}'.format(
                                unicode(seq.group(1), 'utf-8'),
                                unicode(seq.group(3), 'utf-8'),
                                unicode(seq.group(4), 'utf-8'))
                        except TypeError:
                            key = u'{}{}.{}'.format(
                                seq.group(1),
                                seq.group(3),
                                seq.group(4))

                        if key.lower() in sfavourites:
                            flags = flags | common.MarkedAsFavourite

                        seqs[seqpath.lower()] = {
                            QtCore.Qt.DisplayRole: seqname,
                            QtCore.Qt.EditRole: seqname,
                            QtCore.Qt.StatusTipRole: seqpath,
                            QtCore.Qt.ToolTipRole: seqpath,
                            QtCore.Qt.SizeHintRole: rowsize,
                            common.EntryRole: [],
                            common.FlagsRole: flags,
                            common.ParentRole: (server, job, root, asset, location, fileroot),
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
                            common.SortByName: seqpath,
                            common.SortByLastModified: 0,
                            common.SortBySize: 0,  # Initializing with null-size
                        }

                    seqs[seqpath.lower()][common.FramesRole].append(seq.group(2))
                    seqs[seqpath.lower()][common.EntryRole].append(entry)
                else:
                    seqs[filepath] = self._data[dkey][common.FileItem][idx]

        # Casting the sequence data onto the model
        for v in seqs.itervalues():
            idx = len(self._data[dkey][common.SequenceItem])

            # A sequence with only one element is not a sequence!
            if len(v[common.FramesRole]) == 1:
                filepath = v[common.SequenceRole].expand(ur'\1{}\3.\4')
                filepath = filepath.format(v[common.FramesRole][0])
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
                    _firsframe = v[common.SequenceRole].expand(ur'\1{}\3.\4')
                    _firsframe = _firsframe.format(min(v[common.FramesRole]))
                    if activefile in _firsframe:
                        v[common.FlagsRole] = v[common.FlagsRole] | common.MarkedAsActive
            self._data[dkey][common.SequenceItem][idx] = v

    def data_key(self):
        """Current key to the data dictionary."""
        if not self._datakey:
            val = None
            key = u'activepath/location'
            savedval = local_settings.value(key)
            return savedval if savedval else val
        return self._datakey

    @QtCore.Slot(unicode)
    def set_data_key(self, val):
        """Slot used to save data key to the model instance and the local
        settings.

        Each subfolder inside the root folder, defined by``_parent_item``,
        corresponds to a `key`. We use these keys to save model data associated
        with these folders.

        It's important to make sure the key we're about to be set corresponds to
        an existing folder. We will use a reasonable default if the folder does
        not exist.

        """
        k = u'activepath/location'
        stored_value = local_settings.value(k)
        # Nothing to do for us when the parent is not set
        if not self._parent_item:
            return

        if self._datakey is None and stored_value:
            self._datakey = stored_value

        # We are in sync with a valid value set already
        if self._datakey == val == stored_value and stored_value is not None:
            return

        # Update the local_settings
        if self._datakey == val and val != stored_value:
            local_settings.setValue(k, val)
            return

        # About to set a new value. We can accept or reject this...
        if val == self._datakey and val is not None:
            return

        entries = self.can_accept_datakey(val)
        if not entries:
            self._datakey = None
            return

        if val in entries:
            self._datakey = val
            local_settings.setValue(k, val)
            return
        elif val not in entries and self._datakey in entries:
            val = self._datakey
            local_settings.setValue(k, self._datakey)
            stored_value = self._datakey
            return
        elif val not in entries and u'scenes' in entries:
            val = u'scenes'

        val = entries[0]
        self._datakey = val
        local_settings.setValue(k, val)

    def can_accept_datakey(self, val):
        """Checks if the key about to be set corresponds to a real
        folder. If not, we will try to pick a default value, u'scenes', or
        the first folder if the default does not exist.

        """
        if not self._parent_item:
            return False
        path = u'/'.join(self._parent_item)
        entries = [f.name.lower() for f in gwscandir.scandir(path)]
        if not entries:
            return False
        if val not in entries:
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
        metrics = QtGui.QFontMetrics(font)
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
        self.setAutoScroll(True)

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
        parent_role = index.data(common.ParentRole)
        if not parent_role:
            return
        if len(parent_role) < 5:
            return

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        filepath = u'{}/{}'.format(  # location/subdir/filename.ext
            parent_role[5],
            common.get_sequence_startpath(file_info.fileName()))
        local_settings.setValue(u'activepath/file', filepath)

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

        description_rect = QtCore.QRect(name_rect)

        name_rect.moveTop(name_rect.top() + (name_rect.height() / 2.0))
        name_rect.setHeight(metrics.height())
        name_rect.moveTop(name_rect.top() - (name_rect.height() / 2.0))

        # Moving the rectangle down one line
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

    def startDrag(self, supported_actions):
        """Creating a custom drag object here for displaying setting hotspots."""
        index = self.selectionModel().currentIndex()
        model = self.model().sourceModel()

        if not index.isValid():
            return
        if not index.data(QtCore.Qt.StatusTipRole):
            return
        if not index.data(common.ParentRole):
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

        bookmark = u'/'.join(index.data(common.ParentRole)[:3])
        path = path.replace(bookmark, u'')
        path = path.strip(u'/')
        if no_modifier:
            pixmap = index.data(common.ThumbnailRole)
            pixmap = QtGui.QPixmap.fromImage(pixmap)
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
            path = u'{}, ++'.format(common.get_sequence_startpath(path))
            pixmap = ImageCache.get_rsc_pixmap(
                u'multiples_files', common.SECONDARY_TEXT, height)
        else:
            return

        self.update(index)
        pixmap = DragPixmap.pixmap(pixmap, path)
        drag.setPixmap(pixmap)
        # drag.setHotSpot(pixmap)

        drag.exec_(supported_actions)

        # Cleanup
        self.drag_source_index = QtCore.QModelIndex()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = FilesWidget()
    widget.show()
    app.exec_()
