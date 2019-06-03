# -*- coding: utf-8 -*-
"""The threads and the associated workers are defined here.

GWBrowser does OpenImageIO and file-load operations on separate threads
controlled by QThread.

Each thread is assigned a single Worker - usually responsible for taking
QModelIndexes from the thread's python Queue.

"""

import traceback
import Queue
import threading
from PySide2 import QtCore


class Unique(Queue.Queue):
    """https://stackoverflow.com/questions/16506429/check-if-element-is-already-in-a-queue"""

    def _init(self, maxsize):
        self.queue = set()

    def _put(self, item):
        self.queue.add(item)

    def _get(self):
        return self.queue.pop()


mutex = QtCore.QMutex()


class BaseWorker(QtCore.QObject):
    """The base for all workers associated with a QThread.
    `begin_processing` is a blocking function and will take any QModelIndexes found
    in the `BaseWorker.Unique`.

    """

    queue = Unique(999999)
    lock = threading.Lock()
    shutdown_requested = False
    indexes_in_progress = []

    queueFinished = QtCore.Signal()
    indexUpdated = QtCore.Signal(QtCore.QModelIndex)
    queueError = QtCore.Signal(basestring)
    finished = QtCore.Signal()

    def __init__(self, parent=None):
        super(BaseWorker, self).__init__(parent=parent)
        self.mutex = QtCore.QMutex()
        self.model = None

    @QtCore.Slot()
    def shutdown(self):
        """Quits the index-processing block.
        We're using the built-in python Queue.get(True) method - it blocks the
        executing thread until there's an available worker to fetch the queued item.

        To break the lock it is necessary to add a dummy-item to the queue.

        """
        # Adding a dummy object should clear the get() block
        self.queue.put(QtCore.QPersistentModelIndex())
        self.shutdown_requested = True

    @QtCore.Slot(tuple)
    @classmethod
    def add_to_queue(cls, indexes, persistent=True):
        """Converts the list of indexes to ``QPersistentModelIndex`` model indexes
        and adds it to the worker's queue.

        """
        # The queue might change size during iteration hence it is better copy it
        current_queue = set(cls.queue.queue)
        for index in indexes:
            if not index.isValid():
                continue
            if persistent:
                index = QtCore.QPersistentModelIndex(index)
            if index.data(QtCore.Qt.StatusTipRole) in [f.data(QtCore.Qt.StatusTipRole) for f in current_queue]:
                continue
            if index.data(QtCore.Qt.StatusTipRole) in [f.data(QtCore.Qt.StatusTipRole) for f in cls.indexes_in_progress]:
                continue
            cls.queue.put(index)

    @classmethod
    def reset_queue(cls):
        """Empties the queue"""
        while not cls.queue.empty():
            cls.queue.get(False)

    @QtCore.Slot()
    def begin_processing(self):
        """Starts the processing queue of this worker.

        Each worker class is assigned a Queue, the process will automatically
        take the item as it becomes available.

        Note:
            get(True) will block the thread until a new item is available in
            the queue. On any Exceptions the function will call itself again.

        """
        try:
            # We will keep taking items from the queue until shutdown had been requested
            while not self.shutdown_requested:
                # We'll take the item from the queue
                # It is possible however, that the item has been added back into
                # the queue after a thread has taken it already
                index = self.queue.get(True)

                # Let's check if this is the case and take the first available
                while index in self.indexes_in_progress:
                    index = self.queue.get(True)

                # This thread is the first to take the item, we will add the index
                # to the list
                if index not in self.indexes_in_progress:
                    self.indexes_in_progress.append(index)

                # Finally, we process the index
                self.process_index(index)

                # We'll remove the index from the currently processing items
                if index in self.indexes_in_progress:
                    self.indexes_in_progress.remove(index)

        except RuntimeError as err:
            errstr = '\nRuntimeError in {}\n{}\n'.format(
                QtCore.QThread.currentThread(), err)
            traceback.print_exc()
            self.error.emit(errstr)
        except ValueError as err:
            errstr = '\nValueError in {}\n{}\n'.format(
                QtCore.QThread.currentThread(), err)
            traceback.print_exc()
            self.error.emit(errstr)
        except Exception as err:
            errstr = '\nError in {}\n{}\n'.format(
                QtCore.QThread.currentThread(), err)
            traceback.print_exc()
            self.error.emit(errstr)
        finally:
            if self.shutdown_requested:
                self.finished.emit()
            else:
                self.begin_processing()

    @QtCore.Slot(QtCore.QModelIndex)
    def process_index(self, index):
        """The actual processing happens here.
        Make sure this overriden in the subclass.

        """
        raise NotImplementedError('process_index must to be subclassed.')


class BaseThread(QtCore.QThread):
    """The thread responsible for updating the file-list with the missing
    information. I can't get threads to work using the documented way -
    depending on conditions I don't understand, the thread sometimes executes
    the worker, sometimes the `started` signal doesn't fire when the Worker is
    created outside the thread.

    This is a custom implementation - the worker is created in start() making sure
    it is affiliated with the thread (qobject.moveToThread didn't work for me).

    The thread.start() is called when the ``FileModel`` is initialized.

    """
    _instances = {}
    __worker = None
    Worker = BaseWorker

    def __init__(self, parent=None):
        super(BaseThread, self).__init__(parent=parent)
        BaseThread._instances[repr(self)] = self
        self.setTerminationEnabled(True)

        self.thread_id = None
        self.worker = None

    def run(self):
        """Start the thread, initializes the worker and shuts the worker when
        the worker finished processing."""
        self.worker = self.Worker()
        self.worker.finished.connect(lambda: self.exit(0))
        self.started.emit()
        self.worker.begin_processing()
        self.exec_()
