# -*- coding: utf-8 -*-
"""The threads and associated worker classes.

Thumbnail and file-load work on carried out on secondary threads.
Each thread is assigned a single Worker - usually responsible for taking
a *weakref.ref* from the thread's queue.

"""
import base64
import json
import functools
import weakref
import collections
import uuid

from PySide2 import QtCore, QtGui, QtWidgets

from . import log
from . import common
from . import images
from . import bookmark_db


THREADS = {}
"""Global thread controller cache."""

FileThumbnailQueue = 1
FavouriteThumbnailQueue = FileThumbnailQueue + 1
AssetThumbnailQueue = FavouriteThumbnailQueue + 1
BookmarkThumbnailQueue = AssetThumbnailQueue + 1
FileInfoQueue = BookmarkThumbnailQueue + 1
FavouriteInfoQueue = FileInfoQueue + 1
AssetInfoQueue = FavouriteInfoQueue + 1
BookmarkInfoQueue = AssetInfoQueue + 1
TaskFolderInfoQueue = BookmarkInfoQueue + 1


QUEUES = {
    FileThumbnailQueue: collections.deque([], 99),
    FavouriteThumbnailQueue: collections.deque([], 99),
    AssetThumbnailQueue: collections.deque([], 99),
    BookmarkThumbnailQueue: collections.deque([], 99),
    FileInfoQueue: collections.deque([], common.MAXITEMS),
    FavouriteInfoQueue: collections.deque([], common.MAXITEMS),
    AssetInfoQueue: collections.deque([], common.MAXITEMS),
    BookmarkInfoQueue: collections.deque([], common.MAXITEMS),
    TaskFolderInfoQueue: collections.deque([], common.MAXITEMS),
}
"""Global thread queues."""


class ModelLoadedDummy(object):
    """Dummy class used to help signal a model has been fully processed."""

    def __init__(self, data_type):
        self.data_type = data_type


def verify_thread_affinity():
    """Prohibits running methods from the main gui thread.

    Raises:
        RuntimeError: If the calling thread is the main gui thread.

    """
    if QtCore.QThread.currentThread() == QtWidgets.QApplication.instance().thread():
        s = u'Method cannot be called from the main gui thread'
        log.error(s)
        raise RuntimeError(s)


def process(func):
    """Decorator for worker `process_data` slots.

    Takes and passes the next available data in the queue for processing
    and emits the `updateRow` signal if the data has been correctly loaded.

    """
    @functools.wraps(func)
    def func_wrapper(self):
        verify_thread_affinity()
        try:
            if self.interrupt:
                return

            ref = QUEUES[self.queue_type].pop()

            # Let the source model know that we loaded a data segment fully
            if isinstance(ref, ModelLoadedDummy):
                if self.interrupt:
                    return
                self.modelLoaded.emit(ref.data_type)
                return

            if not ref() or self.interrupt:
                return

            # Call process_data
            result = func(self, ref)
            if not isinstance(result, bool):
                raise TypeError(
                    u'Invalid return value from process_data(). Expected <type \'bool\'>, got {}'.format(type(result)))

            # Let the models/views know the data has been processed ok and
            # and request a row repaint
            if not ref() or self.interrupt or not result:
                return
            self.updateRow.emit(ref()[common.IdRole])

        except IndexError:
            pass  # ignore index errors
        except (ValueError, RuntimeError, TypeError):
            log.error(u'Error processing data - {}'.format(self))
        finally:
            self.interrupt = False

    return func_wrapper


class ThreadMonitor(QtWidgets.QWidget):
    """A progress label used to display the number of items currently in the
    processing queues across all threads.

    """

    def __init__(self, parent=None):
        super(ThreadMonitor, self).__init__(parent=parent)
        self.timer = QtCore.QTimer(parent=self)
        self.timer.setInterval(500)
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.update)
        self.metrics = common.font_db.primary_font(common.SMALL_FONT_SIZE())[1]

    def showEvent(self, event):
        self.timer.start()

    def hideEvent(self, event):
        self.timer.stop()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(common.SMALL_FONT_SIZE())[0],
            self.rect(),
            self.text(),
            QtCore.Qt.AlignCenter,
            common.ADD
        )
        painter.end()

    def update(self):
        self.setFixedWidth(self.metrics.width(self.text()) + common.MARGIN())
        super(ThreadMonitor, self).update()

    @staticmethod
    def text():
        c = 0
        for q in QUEUES.itervalues():
            c += len(q)
        if not c:
            return u''
        return u'Loading... ({} left)'.format(c)


class BaseThread(QtCore.QThread):
    """Thread controller.

    The threads are associated with workers and are used to consume items
    from their associated queues.

    Signals:
        * resetQueue: Empty the worker's queue.
        * startCheckQueue: Start the worker's queue timer.
        * stopCheckQueue: Stop the worker's queue timer.
        * updateRow: Called when the worker finished processing an item and a row repaint is needed.
        * queueModel: Request the worker to load the entire model data to the queue.
        * modelLoaded: Called by the worker when all items previously added by queueModel have finished processing.

    """
    resetQueue = QtCore.Signal()
    startCheckQueue = QtCore.Signal()
    stopCheckQueue = QtCore.Signal()
    updateRow = QtCore.Signal(int)
    queueModel = QtCore.Signal(str)
    modelLoaded = QtCore.Signal(int)

    def __init__(self, worker, parent=None):
        super(BaseThread, self).__init__(parent=parent)
        if not isinstance(worker, BaseWorker):
            raise TypeError(u'Invalid worker type')

        if repr(self) not in THREADS:
            THREADS[repr(self)] = self

        self.setObjectName(u'Thread{}'.format(uuid.uuid1()))
        self.setTerminationEnabled(True)

        self.worker = worker
        self._connect_signals()

    def _connect_signals(self):
        QtCore.QCoreApplication.instance().aboutToQuit.connect(self.quit)
        QtGui.QGuiApplication.instance().lastWindowClosed.connect(self.quit)

        self.started.connect(
            lambda: log.debug(u'started --> move_worker_to_thread', self))
        self.started.connect(self.move_worker_to_thread)

    @QtCore.Slot()
    def move_worker_to_thread(self):
        """Slot called when the thread is started.

        We'll move the worker to the thread and connnect all signals needed to
        communicate with the worker.

        """
        log.debug(u'move_worker_to_thread()', self)

        self.worker.moveToThread(self)
        cnx = QtCore.Qt.QueuedConnection

        if self.worker.thread() == QtWidgets.QApplication.instance().thread():
            s = u'The worker cannot be used in the main gui thread.'
            log.error(s)
            raise RuntimeError(s)

        self.resetQueue.connect(
            lambda: log.debug(u'resetQueue --> worker.resetQueue', self))
        self.resetQueue.connect(self.worker.resetQueue, cnx)
        self.queueModel.connect(
            lambda: log.debug(u'queueModel --> worker.queueModel', self))
        self.queueModel.connect(self.worker.queueModel, cnx)

        self.startCheckQueue.connect(
            lambda: log.debug(u'startCheckQueue --> worker.startCheckQueue', self))
        self.startCheckQueue.connect(self.worker.startCheckQueue, cnx)
        self.stopCheckQueue.connect(
            lambda: log.debug(u'stopCheckQueue --> worker.stopCheckQueue', self))
        self.stopCheckQueue.connect(self.worker.stopCheckQueue, cnx)
        self.worker.updateRow.connect(self.updateRow, cnx)
        self.worker.modelLoaded.connect(self.modelLoaded, cnx)

    def add_to_queue(self, ref):
        """Add an item to the worker's queue.

        Args:
            ref (weakref.ref): A weak reference to a data segment.
            end (bool): Add to the end of the queue instead if `True`.

        """
        if not isinstance(ref, weakref.ref):
            raise TypeError(u'Invalid type. Expected <type \'weakref.ref\'>')
        q = QUEUES[self.worker.queue_type]
        if ref not in q and ref():
            q.append(ref)


class BaseWorker(QtCore.QObject):
    """Workers are used to load file and thumbnail information.

    Each worker is associated with global queues using `queue_type` and their signals
    are connected to the respective thread signals. This is so that we can
    rely on Qt's event queue for communicating between threads.

    """
    resetQueue = QtCore.Signal()
    startCheckQueue = QtCore.Signal()
    stopCheckQueue = QtCore.Signal()
    updateRow = QtCore.Signal(int)
    queueModel = QtCore.Signal(str)
    modelLoaded = QtCore.Signal(int)

    def __init__(self, queue_type, parent=None):
        if not isinstance(queue_type, int):
            raise TypeError(
                u'Invalid value, expected <type \'int\'>, got {}'.format(type(queue_type)))
        if queue_type not in QUEUES:
            raise ValueError(u'Invalid queue type.')

        super(BaseWorker, self).__init__(parent=parent)
        self.setObjectName(u'Worker{}'.format(uuid.uuid1()))

        self.interrupt = False
        self.queue_type = queue_type
        self.check_queue_timer = QtCore.QTimer(parent=self)
        self.check_queue_timer.setInterval(333)

        self.resetQueue.connect(self.reset_queue, QtCore.Qt.DirectConnection)
        self.queueModel.connect(self.add_model_to_queue,
                                QtCore.Qt.DirectConnection)

        self.startCheckQueue.connect(
            self.check_queue_timer.start, QtCore.Qt.DirectConnection)
        self.stopCheckQueue.connect(
            self.check_queue_timer.stop, QtCore.Qt.DirectConnection)
        self.check_queue_timer.timeout.connect(
            self.check_queue, QtCore.Qt.DirectConnection)

    @QtCore.Slot()
    def check_queue(self):
        """Slot called to see if a queue contains any items waiting to be
        consumed.

        If the queue is not empty we will call :func:`.BaseWorker.process_data`
        untiol the queue is empty.

        """
        verify_thread_affinity()

        q = QUEUES[self.queue_type]
        if not len(q):
            return
        n = 0

        while len(q):
            if n >= common.MAXITEMS:
                break
            if self.interrupt:
                break
            self.process_data()
            n += 1

    @QtCore.Slot(str)
    def add_model_to_queue(self, repr_name):
        """Load the entirety of the model's data in the queue for processing.

        `repr_name` is the name of the source class. This is needed because the connections are
        queued and passing model data directly would incur a significant overhead. Instead, `repr_name` is
        used as a pointer to located data from in the model directly.

        Args:
            repr_name (str): The string representation of the calling class.

        """
        verify_thread_affinity()

        from . import main
        if not main.instance():
            return

        # Let's determine the type
        if 'BookmarksModel' in repr_name:
            n = 0
        elif 'AssetModel' in repr_name:
            n = 1
        elif 'FilesModel' in repr_name:
            n = 2
        elif 'FavouritesModel' in repr_name:
            n = 3

        # and load the data
        view = main.instance().stackedwidget.widget(n)
        model = view.model().sourceModel()

        q = QUEUES[self.queue_type]

        k = model.task_folder()
        if k not in model.INTERNAL_MODEL_DATA:
            return

        # We will load the current item type first
        if model.data_type() == common.FileItem:
            data_types = (common.FileItem, common.SequenceItem)
        else:
            data_types = (common.SequenceItem, common.FileItem)

        for data_type in data_types:
            if data_type not in model.INTERNAL_MODEL_DATA[k]:
                continue

            for data in model.INTERNAL_MODEL_DATA[k][data_type].itervalues():
                if self.interrupt:
                    return
                if data[common.FileInfoLoaded]:
                    continue
                _ref = weakref.ref(data)
                q.appendleft(_ref)

            # The very last item we add is a dummy object that will be used to
            # signal the model that all data has been loaded
            q.appendleft(ModelLoadedDummy(data_type))
            return True

    @QtCore.Slot()
    def reset_queue(self):
        """Slot called by the `resetQueue` signal and is responsible for
        clearing the worker's queue.

        """
        verify_thread_affinity()
        log.debug(u'reset_queue()', self)
        self.interrupt = True
        QUEUES[self.queue_type].clear()
        self.interrupt = False

    @process
    @QtCore.Slot()
    def process_data(self, ref):
        """This is an abstract method and must be overwritten in the subclass."""
        if not ref() or self.interrupt:
            return False
        return True


class InfoWorker(BaseWorker):
    """A worker used to retrieve file information.

    We will query the file system for file size, and the bookmark database
    for the description, and file flags.

    """
    @process
    @QtCore.Slot(weakref.ref)
    def process_data(self, ref):
        """Populates the item with the missing file information.

        Args:
            ref (weakref): An internal model data DataDict instance's weakref.

        Returns:
            bool: `True` if all went well, `False` otherwise.

        """
        def is_valid(): return False if not ref() or self.interrupt or ref()[
            common.FileInfoLoaded] else True

        if not is_valid():
            return False

        try:
            pp = ref()[common.ParentPathRole]
            db = bookmark_db.get_db(pp[0], pp[1], pp[2])

            if not is_valid():
                return False

            collapsed = common.is_collapsed(ref()[QtCore.Qt.StatusTipRole])
            seq = ref()[common.SequenceRole]

            if not is_valid():
                return False
            proxy_k = common.proxy_path(ref())
            if collapsed:
                k = proxy_k
            else:
                if not is_valid():
                    return False
                k = ref()[QtCore.Qt.StatusTipRole]

            # Issues SQLite "BEGIN"
            with db.transactions():
                # Description
                v = db.value(k, u'description')
                if v:
                    if not is_valid():
                        return False
                    v = base64.b64decode(v)
                    ref()[common.DescriptionRole] = v

                v = db.value(k, u'notes')
                count = 0
                if v:
                    try:
                        v = base64.b64decode(v)
                        v = json.loads(v)
                        count = [k for k in v if v[k][u'text']
                                 and not v[k][u'checked']]
                        count = len(count)
                    except:
                        log.error(u'Could not read notes')

                if not is_valid():
                    return False
                ref()[common.TodoCountRole] = count

                # Item flags
                if not is_valid():
                    return False
                flags = ref()[
                    common.FlagsRole] | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled

                v = db.value(k, u'flags')
                if v:
                    flags = flags | v
                v = db.value(proxy_k, u'flags')
                if v:
                    flags = flags | v

                if not is_valid():
                    return False
                ref()[common.FlagsRole] = flags

            # For sequences we will work out the name of the sequence based on
            # the frames.
            if not is_valid():
                return False
            if ref()[common.TypeRole] == common.SequenceItem:
                if not is_valid():
                    return False
                frs = ref()[common.FramesRole]
                intframes = [int(f) for f in frs]
                padding = len(frs[0])
                rangestring = common.get_ranges(intframes, padding)

                if not is_valid():
                    return False
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
                if not is_valid():
                    return False
                ref()[common.StartpathRole] = startpath
                if not is_valid():
                    return False
                ref()[common.EndpathRole] = endpath
                if not is_valid():
                    return False
                ref()[QtCore.Qt.StatusTipRole] = seqpath
                if not is_valid():
                    return False
                ref()[QtCore.Qt.ToolTipRole] = seqpath
                if not ref():
                    return False
                ref()[QtCore.Qt.DisplayRole] = seqname
                if not is_valid():
                    return False
                ref()[QtCore.Qt.EditRole] = seqname
                if not is_valid():
                    return False
                # We saved the DirEntry instances previously in `__initdata__` but
                # only for the thread to extract the information from it.
                if not is_valid():
                    return False
                er = ref()[common.EntryRole]
                if er:
                    mtime = 0
                    for entry in er:
                        stat = entry.stat()
                        mtime = stat.st_mtime if stat.st_mtime > mtime else mtime
                        if not is_valid():
                            return False
                        ref()[common.SortBySizeRole] += stat.st_size
                    if not is_valid():
                        return False
                    ref()[common.SortByLastModifiedRole] = mtime
                    mtime = common.qlast_modified(mtime)

                    if not is_valid():
                        return False
                    info_string = \
                        unicode(len(intframes)) + u'f;' + \
                        mtime.toString(u'dd') + u'/' + \
                        mtime.toString(u'MM') + u'/' + \
                        mtime.toString(u'yyyy') + u' ' + \
                        mtime.toString(u'hh') + u':' + \
                        mtime.toString(u'mm') + u';' + \
                        common.byte_to_string(ref()[common.SortBySizeRole])
                    if not is_valid():
                        return False
                    ref()[common.FileDetailsRole] = info_string

            if not is_valid():
                return False
            if ref()[common.TypeRole] == common.FileItem:
                if not is_valid():
                    return False
                er = ref()[common.EntryRole]
                if er:
                    stat = er[0].stat()
                    mtime = stat.st_mtime
                    ref()[common.SortByLastModifiedRole] = mtime
                    mtime = common.qlast_modified(mtime)
                    ref()[common.SortBySizeRole] = stat.st_size
                    info_string = \
                        mtime.toString(u'dd') + u'/' + \
                        mtime.toString(u'MM') + u'/' + \
                        mtime.toString(u'yyyy') + u' ' + \
                        mtime.toString(u'hh') + u':' + \
                        mtime.toString(u'mm') + u';' + \
                        common.byte_to_string(ref()[common.SortBySizeRole])
                    if not is_valid():
                        return False
                    ref()[common.FileDetailsRole] = info_string
                if not is_valid():
                    return False

            # Finally, set flag to mark this loaded
            if not is_valid():
                return False
            return True
        except:
            log.error(u'Error processing file info.')
        finally:
            if ref():
                ref()[common.FileInfoLoaded] = True


class ThumbnailWorker(BaseWorker):
    """Thread worker responsible for creating and loading thumbnails.

    The resulting image data is saved in the `ImageCache` and used by the item
    listdelegates to paint thumbnails.

    """
    @process
    @QtCore.Slot()
    def process_data(self, ref):
        """Populates the ImageCache with an existing thumbnail or generates a
        new one if `ref` refers to a file understood by OpenImageIO.

        If the return value is not `None`, the model will request a repaint
        event for the row the `ref` corresponds to. See the `@process` decorator
        for details.

        Args:
            ref (weakref.ref): A weakref to a data segment.

        Returns:
            ref or None: `ref` if loaded successfully, else `None`.

        """
        def is_valid(): return False if not ref() or self.interrupt or ref()[
            common.ThumbnailLoaded] or ref()[common.FlagsRole] & common.MarkedAsArchived else True

        if not is_valid():
            return False
        size = ref()[QtCore.Qt.SizeHintRole].height()

        if not is_valid():
            return False
        _p = ref()[common.ParentPathRole]

        if not is_valid():
            return False
        source = ref()[QtCore.Qt.StatusTipRole]

        # Resolve the thumbnail's path...
        destination = images.get_thumbnail_path(
            _p[0],
            _p[1],
            _p[2],
            source,
        )
        # ...and use it to load the resource
        image = images.ImageCache.get_image(
            destination,
            int(size),
            force=True  # force=True will refresh the cache
        )

        try:
            # If the image successfully loads we can wrap things up here
            if image and not image.isNull():
                images.ImageCache.get_image(destination, int(size), force=True)
                images.ImageCache.make_color(destination)
                return True

            # Otherwise, we will try to generate a thumbnail using OpenImageIO

            # If the items is a sequence, we'll use the first image of the
            # sequence to make the thumbnail.
            if not is_valid():
                return False
            if ref()[common.TypeRole] == common.SequenceItem:
                if not is_valid():
                    return False
                source = ref()[common.EntryRole][0].path.replace(u'\\', u'/')

            buf = images.oiio_get_buf(source)
            if not buf:
                return False

            if QtCore.QFileInfo(source).size() >= pow(1024, 3) * 2:
                return False
            res = images.ImageCache.oiio_make_thumbnail(
                source,
                destination,
                common.THUMBNAIL_IMAGE_SIZE,
            )
            if res:
                images.ImageCache.get_image(destination, int(size), force=True)
                images.ImageCache.make_color(destination)
                return True

            # We should never get here ideally, but if we do we'll mark the item
            # with a bespoke 'failed' thumbnail
            res = images.ImageCache.oiio_make_thumbnail(
                common.rsc_path(__file__, u'failed'),
                destination,
                common.THUMBNAIL_IMAGE_SIZE
            )
            if res:
                images.ImageCache.get_image(destination, int(size), force=True)
                images.ImageCache.make_color(destination)
                return True
            return False
        except:
            log.error(u'Failed to generate thumbnail')
        finally:
            if ref():
                ref()[common.ThumbnailLoaded] = True


class TaskFolderWorker(BaseWorker):
    """Used by the TaskFolderModel to count the number of files in a folder."""
    @process
    @QtCore.Slot()
    def process_data(self, ref):
        """Counts the number of items in the task folder up to 999.

        """
        def is_valid():
            return False if not ref() or self.interrupt else True

        if not is_valid():
            return False

        count = 0
        for entry in common.walk(ref()[QtCore.Qt.StatusTipRole]):
            if not is_valid():
                return False
            if entry.name.startswith(u'.'):
                continue
            count += 1
            if count > 999:
                break
        if not is_valid():
            return False
        ref()[common.TodoCountRole] = count
        return True
