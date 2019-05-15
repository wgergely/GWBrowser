# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101

"""The threads and the associated workers are defined here.

GWBrowser does OpenImageIO and file-load operations on separate threads
controlled by QThread.

Each thread is assigned a single Worker - usually responsible for taking
QModelIndexes from the thread's python Queue.

"""

import sys
import traceback
import Queue
from PySide2 import QtCore


class Unique(Queue.Queue):
    """https://stackoverflow.com/questions/16506429/check-if-element-is-already-in-a-queue"""

    def _init(self, maxsize):
        self.queue = set()

    def _put(self, item):
        self.queue.add(item)

    def _get(self):
        return self.queue.pop()


class BaseWorker(QtCore.QObject):
    """The base for all workers associated with a QThread.
    `begin_processing` is a blocking function and will take any QModelIndexes found
    in the `BaseWorker.Unique`.

    """

    queue = Unique(999999)
    shutdown_requested = False

    queueFinished = QtCore.Signal()
    indexUpdated = QtCore.Signal(QtCore.QModelIndex)
    queueError = QtCore.Signal(basestring)
    finished = QtCore.Signal()

    def __init__(self, parent=None):
        super(BaseWorker, self).__init__(parent=parent)

    @QtCore.Slot()
    def shutdown(self):
        """Quits the index-processing block.
        We're using the built-in python Queue.get(True) method - it blocks the
        executing thread until there's an available queue item to get.

        To break the lock it is necessary to add a dummy-item to the queue.

        """
        # Adding a dummy object should clear the get() block
        for _ in xrange(10):
            self.queue.put(QtCore.QModelIndex())

        sys.stdout.write('# Stopping {} worker...\n'.format(
            self.__class__.__name__))
        self.shutdown_requested = True

    @classmethod
    @QtCore.Slot(tuple)
    def add_to_queue(cls, items):
        for item in items:
            cls.queue.put(item)

    @classmethod
    def reset_queue(cls):
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
            while not self.shutdown_requested:
                index = self.queue.get(True)
                self.process_index(index)
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
                sys.stdout.write('# {} worker finished processing.\n'.format(
                    self.__class__.__name__))
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

    __worker = None
    Worker = BaseWorker

    def __init__(self, parent=None):
        super(BaseThread, self).__init__(parent=parent)
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
