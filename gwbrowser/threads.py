# -*- coding: utf-8 -*-
"""The threads/worker classes supportin the data models are defined here.
"""
# pylint: disable=E1101, C0103, R0913, I1101

import sys
import traceback
import Queue

from PySide2 import QtWidgets, QtCore

import gwbrowser.common as common


class Unique(Queue.Queue):
    """https://stackoverflow.com/questions/16506429/check-if-element-is-already-in-a-queue"""
    def _init(self, maxsize):
        self.queue = set()
    def _put(self, item):
        self.queue.add(item)
    def _get(self):
        return self.queue.pop()

class BaseWorker(QtCore.QObject):
    """Thread-worker class responsible for updating the given indexes."""
    queue = Unique(999999)
    queueFinished = QtCore.Signal()
    indexUpdated = QtCore.Signal(QtCore.QModelIndex)
    queueError = QtCore.Signal(basestring)

    def __init__(self, parent=None):
        super(BaseWorker, self).__init__(parent=parent)

    @classmethod
    @QtCore.Slot(tuple)
    def add_to_queue(cls, items):
        for item in items:
            cls.queue.put(item)

    @classmethod
    def reset_queue(cls):
        while not cls.queue.empty():
            cls.queue.get(False)

    @QtCore.Slot(tuple)
    def begin_processing(self):
        """Starts the processing queue of this worker.

        Each worker class is assigned a Queue, the process will automatically
        take the item as it becomes available.

        Note:
            get(True) will block the thread until a new item is available in
            the queue.

        """
        try:
            while True:
                self.process_index(self.queue.get(True))
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
            self.begin_processing()

    @QtCore.Slot(QtCore.QModelIndex)
    def process_index(self, index):
        """The actual processing happens here."""
        raise NotImplementedError('process_index must to be subclassed.')




class BaseThread(QtCore.QThread):
    """The thread responsible for updating the file-list with the missing
    information. I can't get threads to work using the documented way -
    depending on conditions I don't understand, the thread sometimes executes
    the worker, sometimes the `started` signal doesn't fire when the Worker is
    created outside the thread.

    This is a custom implementation - the worker is created in start() amking sure,
    it is affiliated with the thread (moveToThread didn't work for me).

    The thread.start() is called when the ``FileModel`` is initialized.

    """
    __worker = None
    Worker = BaseWorker

    def __init__(self, parent=None):
        super(BaseThread, self).__init__(parent=parent)
        self.thread_id = None
        self.worker = None

        app = QtWidgets.QApplication.instance()
        if app:
            app.aboutToQuit.connect(self.terminate)
            # app.aboutToQuit.connect(self.wait)
            app.aboutToQuit.connect(self.deleteLater)

    def run(self):
        self.worker = self.Worker()
        self.worker.begin_processing()
        self.started.emit()
        self.exec_()
