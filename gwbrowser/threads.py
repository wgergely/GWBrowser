# -*- coding: utf-8 -*-
"""The threads and the associated workers are defined here.

GWBrowser does OpenImageIO and file-load operations on separate threads
controlled by QThread objects.

Each thread is assigned a single Worker - usually responsible for taking
*QModelIndexes* from the thread's python Queue.

"""
from PySide2 import QtCore, QtGui, QtWidgets
import time
import Queue
import functools
import re
import weakref
import sys
import traceback
import collections
import Queue
from PySide2 import QtCore

from gwbrowser.imagecache import ImageCache
import gwbrowser.bookmark_db as bookmark_db
import gwbrowser.delegate as delegate
import gwbrowser.common as common
import OpenImageIO


THREADS = {}


class UniqueQueue(Queue.Queue):
    """A queue for queuing only unique items.
    https://stackoverflow.com/questions/16506429/check-if-element-is-already-in-a-queue"""

    def _init(self, maxsize):
        self.queue = collections.deque()

    def _put(self, item):
        self.queue.appendleft(item)

    def _get(self):
        return self.queue.pop()


def process(func):
    """Decorator wraps the worker's process_data call:
    Will take and pass the next available data in
    the queue for processing and emits the dataReady

    """
    @functools.wraps(func)
    def func_wrapper(self):
        result = None
        try:
            result = func(self, self.data_queue.get(False))
            if not result:
                common.Log.info(u'process_data() was interrupted')
                return
            common.Log.success('dataReady.emit()')
            self.dataReady.emit(result)
            self.data_queue.task_done()
        except Queue.Empty:
            common.Log.info(u'Thread is waiting for data...')
            return
        except:
            common.Log.error(u'process_data() failed')
        finally:
            self.interrupt = False

    return func_wrapper


class BaseWorker(QtCore.QObject):
    dataRequested = QtCore.Signal()
    dataReady = QtCore.Signal(dict)
    resetQueue = QtCore.Signal()

    def __init__(self, parent=None):
        super(BaseWorker, self).__init__(parent=parent)
        self.interrupt = False
        self.data_queue = UniqueQueue()
        self.dataRequested.connect(self.process_data, QtCore.Qt.DirectConnection)
        self.resetQueue.connect(self.reset_queue, QtCore.Qt.QueuedConnection)

    @QtCore.Slot()
    def reset_queue(self):
        self.interrupt = True
        try:
            while True:
                self.data_queue.get(False)
        except Queue.Empty:
            return
        except Exception:
            common.Log.error('Error resetting the queue')
        finally:
            common.Log.success('Queue reset')

    @process
    @QtCore.Slot()
    def process_data(self, ref):
        common.Log.info(u'Begin processing {}'.format(repr(ref)))
        if self.interrupt:
            return None
        return ref


class BaseThread(QtCore.QThread):
    """Base thread controller used across GWBrowser.
    Threads are responsible for updating the items with the missing
    information and generating thumbnails.

    """
    mutex = QtCore.QMutex()
    startTimer = QtCore.Signal()
    stopTimer = QtCore.Signal()

    def __init__(self, cls, interval=1000, parent=None):
        super(BaseThread, self).__init__(parent=parent)
        if repr(self) not in THREADS:
            THREADS[repr(self)] = self

        self._interval = interval
        self.worker = cls
        self.timer = None
        self.setTerminationEnabled(True)

        self.started.connect(self.move_worker_to_thread)
        self.started.connect(
            lambda: common.Log.info('BaseThread started'))

        QtCore.QCoreApplication.instance().aboutToQuit.connect(self.quit)
        QtGui.QGuiApplication.instance().lastWindowClosed.connect(self.quit)

    def run(self):
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(False)
        self.timer.setInterval(self._interval)
        self.timer.setTimerType(QtCore.Qt.CoarseTimer)
        self.startTimer.connect(self.timer.start)
        self.stopTimer.connect(self.timer.stop)

        self.exec_()

    @QtCore.Slot()
    def move_worker_to_thread(self):
        self.worker.moveToThread(self)
        self.timer.timeout.connect(
            self.worker.dataRequested, QtCore.Qt.DirectConnection)

    def put(self, ref):
        """Main method to add an item to the thread's worker queue.

        Because the underlying data structure wil be destroyed by sorting and
        data reloads, we'll take weakrefs to the data. The worker will have
        to check whilst processing to verify the data is still valid.

        """
        if not isinstance(ref, weakref.ref):
            raise TypeError(u'Invalid data type. Must be <type \'weakref\'>')
        try:
            self.worker.interrupt = False
            if ref in self.worker.data_queue.queue:
                return
            self.worker.data_queue.put(ref)
            common.Log.info(u'Data queued: {}'.format(ref()[QtCore.Qt.DisplayRole]))
        except Queue.Full:
            common.Log.error(u'Queue is full')


class InfoWorker(BaseWorker):
    @process
    @QtCore.Slot()
    def process_data(self, ref):
        """"""
        if not ref() or self.interrupt:
            return None
        ref = self.process_file_information(ref)
        return ref

    @classmethod
    def process_file_information(cls, ref):
        if ref()[common.FileInfoLoaded]:
            return ref
        db = bookmark_db.get_db(
            QtCore.QModelIndex(),
            server=ref()[common.ParentPathRole][0],
            job=ref()[common.ParentPathRole][1],
            root=ref()[common.ParentPathRole][2]
        )
        if not db:
            return None
        # DATABASE --BEGIN--
        with db.transactions():
            # Item description
            k = ref()[common.SequenceRole]
            if k:
                k = k.group(1) + u'[0]' + k.group(3) + u'.' + k.group(4)
            else:
                k = ref()[QtCore.Qt.StatusTipRole]

            # Description
            v = db.value(k, u'description')
            if v:
                ref()[common.DescriptionRole] = v

            # Todos - We'll have to load the data to count the items.
            # Hope fully this won't end up as a super costly operation
            v = db.value(k, u'notes')
            count = 0
            if v:
                try:
                    v = base64.b64decode(v)
                    v = json.loads(v)
                    count = [k for k in v if v[k][u'text'] and not v[k][u'checked']]
                    count = len(count)
                except:
                    common.Log.error('Could not read notes')

            ref()[common.TodoCountRole] = count

            # Item flags
            flags = ref()[common.FlagsRole] | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled
            v = db.value(k, u'flags')
            if v:
                flags = flags | v

            ref()[common.FlagsRole] = flags

        if not ref():
            return None

        # For sequence items we will work out the name of the sequence based on
        # the frames.
        if ref()[common.TypeRole] == common.SequenceItem:
            intframes = [int(f) for f in ref()[common.FramesRole]]
            padding = len(ref()[common.FramesRole][0])
            rangestring = common.get_ranges(intframes, padding)

            seq = ref()[common.SequenceRole]
            startpath = \
                seq.group(1) + \
                unicode(min(intframes)).zfill(padding) + \
                seq.group(3) + \
                u'.' + \
                seq.group(4)
            endpath = \
                seq.group(1) + \
                unicode(max(intframes)).zfill(padding) + \
                seq.group(3) + \
                u'.' + \
                seq.group(4)
            seqpath = \
                seq.group(1) + \
                u'[' + rangestring + u']' + \
                seq.group(3) + \
                u'.' + \
                seq.group(4)
            seqname = seqpath.split(u'/')[-1]

            # Setting the path names
            ref()[common.StartpathRole] = startpath
            ref()[common.EndpathRole] = endpath
            ref()[QtCore.Qt.StatusTipRole] = seqpath
            ref()[QtCore.Qt.ToolTipRole] = seqpath
            ref()[QtCore.Qt.DisplayRole] = seqname
            ref()[QtCore.Qt.EditRole] = seqname

            # We saved the DirEntry instances previously in `__initdata__` but
            # only for the thread to extract the information from it.
            if ref()[common.EntryRole]:
                mtime = 0
                for entry in ref()[common.EntryRole]:
                    stat = entry.stat()
                    mtime = stat.st_mtime if stat.st_mtime > mtime else mtime
                    ref()[common.SortBySize] += stat.st_size
                ref()[common.SortByLastModified] = mtime
                mtime = common.qlast_modified(mtime)

                info_string = \
                    unicode(len(intframes)) + u' files;' + \
                    mtime.toString(u'dd') + u'/' + \
                    mtime.toString(u'MM') + u'/' + \
                    mtime.toString(u'yyyy') + u' ' + \
                    mtime.toString(u'hh') + u':' + \
                    mtime.toString(u'mm') + u';' + \
                    common.byte_to_string(ref()[common.SortBySize])
                ref()[common.FileDetailsRole] = info_string

        if not ref():
            return None

        if ref()[common.TypeRole] == common.FileItem:
            if ref()[common.EntryRole]:
                stat = ref()[common.EntryRole][0].stat()
                mtime = stat.st_mtime
                ref()[common.SortByLastModified] = mtime
                mtime = common.qlast_modified(mtime)
                ref()[common.SortBySize] = stat.st_size
                info_string = \
                    mtime.toString(u'dd') + u'/' + \
                    mtime.toString(u'MM') + u'/' + \
                    mtime.toString(u'yyyy') + u' ' + \
                    mtime.toString(u'hh') + u':' + \
                    mtime.toString(u'mm') + u';' + \
                    common.byte_to_string(ref()[common.SortBySize])

                ref()[common.FileDetailsRole] = info_string

        if not ref():
            return None

        # Finally, set flag to mark this loaded
        ref()[common.FileInfoLoaded] = True
        return ref


class BackgroundInfoWorker(InfoWorker):
    @process
    @QtCore.Slot()
    def process_data(self, ref):
        if not ref() or self.interrupt:
            return
        for item in ref().itervalues():
            if not ref() or self.interrupt:
                return None
            self.process_file_information(weakref.ref(item))
        if not ref() or self.interrupt:
            return None
        return None

    def reset_queue(self):
        self.interrupt = True


class ThumbnailWorker(BaseWorker):
    @process
    @QtCore.Slot()
    def process_data(self, ref):
        """The static method responsible for querrying the file item's thumbnail.

        We will get the thumbnail's path, check if a cached thumbnail exists already,
        then load it. If there's no thumbnail, we will try to generate a thumbnail
        using OpenImageIO.

        Args:
            make (bool): Will generate a thumbnail image if there isn't one already

        """
        if not ref() or self.interrupt:
            return None

        if ref()[common.FlagsRole] & common.MarkedAsArchived:
            return None

        db = bookmark_db.get_db(
            QtCore.QModelIndex(),
            server=ref()[common.ParentPathRole][0],
            job=ref()[common.ParentPathRole][1],
            root=ref()[common.ParentPathRole][2]
        )
        if not db:
            return None

        if not ref():
            return None

        thumbnail_path = db.thumbnail_path(ref()[QtCore.Qt.StatusTipRole])
        ref()[common.ThumbnailPathRole] = thumbnail_path

        height = ref()[QtCore.Qt.SizeHintRole].height() - common.ROW_SEPARATOR
        ext = ref()[QtCore.Qt.StatusTipRole].split(u'.')[-1].lower()
        image = None

        # Checking if we can load an existing image
        if QtCore.QFileInfo(thumbnail_path).exists():
            image = ImageCache.get(
                thumbnail_path, height, overwrite=True)
            if image:
                color = ImageCache.get(
                    thumbnail_path, u'backgroundcolor')

                ref()[common.ThumbnailRole] = image
                ref()[common.ThumbnailBackgroundRole] = color
                ref()[common.FileThumbnailLoaded] = True
                return ref

        # If the item doesn't have a saved thumbnail we will check if
        # OpenImageIO is able to make a thumbnail for it:
        if ext.lower() not in common.oiio_formats:
            return None

        ref()[common.FileThumbnailLoaded] = False

        if not ref() or self.interrupt:
            return None

        if not self.process_thumbnail(ref):
            return None
        return ref

    QtCore.Slot(weakref.ref)
    @staticmethod
    def process_thumbnail(ref):
        """Wraps the `openimageio_thumbnail()` call when the source data is
        a weak dict reference.

        Args:
            ref (weakref.ref):  A weak reference to a data segment

        Returns:
            bool: `True` when the operation was successful, `False` otherwise

        """
        try:
            # OpenImageIO ImageCache instance to control file handles
            cache = OpenImageIO.ImageCache()

            source = ref()[QtCore.Qt.StatusTipRole]
            if common.is_collapsed(source):
                source = common.get_sequence_startpath(source)
            dest = ref()[common.ThumbnailPathRole] 

            # Make sure we're not trying to generate a thumbnail for
            # an enournmous file...
            if QtCore.QFileInfo(source).size() >= 836870912:
                return False

            if not ImageCache.openimageio_thumbnail(source, dest, common.THUMBNAIL_IMAGE_SIZE):
                return False

            if not ref():
                return False

            # Load the image and the background color
            image = ImageCache.get(
                ref()[common.ThumbnailPathRole],
                ref()[QtCore.Qt.SizeHintRole].height() - common.ROW_SEPARATOR,
                overwrite=True)
            color = ImageCache.get(
                ref()[common.ThumbnailPathRole],
                u'backgroundcolor',
                overwrite=False)
            ref()[common.ThumbnailRole] = image
            ref()[common.ThumbnailBackgroundRole] = color
            return True
        except:
            print traceback.format_exc()
            if not ref():
                return
            ref()[common.ThumbnailRole] = ref()[common.DefaultThumbnailRole]
            ref()[common.ThumbnailBackgroundRole] = ref()[common.DefaultThumbnailBackgroundRole]
            common.Log.error('Failed to generate thumbnail')
        finally:
            ref()[common.FileThumbnailLoaded] = True
            cache.invalidate(source, force=True)
            cache.invalidate(dest, force=True)
