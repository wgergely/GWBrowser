# -*- coding: utf-8 -*-
"""Module defines the QListWidget items used to browse the assets and the files
found by the collector classes.

"""
# pylint: disable=E1101, C0103, R0913, I1101

import sys
import traceback
import math
import functools
import Queue

from PySide2 import QtWidgets, QtCore, QtGui

from browser.basecontextmenu import BaseContextMenu
from browser.baselistwidget import BaseInlineIconWidget
from browser.baselistwidget import BaseModel

import browser.common as common
from browser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite
from browser.settings import AssetSettings
from browser.settings import local_settings
from browser.delegate import FilesWidgetDelegate
import browser.editors as editors
from browser.imagecache import ImageCache

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

    indexUpdated = QtCore.Signal(QtCore.QModelIndex)
    finished = QtCore.Signal()
    error = QtCore.Signal(basestring)

    def __init__(self, model, parent=None):
        super(BaseWorker, self).__init__(parent=parent)
        self._model = model

    def model(self):
        return self._model

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
        """Gets and sets the missing information for each index in a background
        thread.

        """
        n = 0
        nth = 9
        try:
            while True:
                n += 1
                if self.queue.qsize():
                    if n % nth == 0:
                        common.ProgressMessage.instance().set_message(
                            'Processing ({} left)...'.format(self.queue.qsize()))
                else:
                    common.ProgressMessage.instance().clear_message()
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

    This is custom implementation - the worker is created in start(),
    this seems to take care of thread affinity (moveToThread didn't work for me).

    The thread.start() is called when the ``FileModel`` is initialized.

    """
    __worker = None
    Worker = BaseWorker

    def __init__(self, model, parent=None):
        super(BaseThread, self).__init__(parent=parent)
        self.thread_id = None
        self.worker = None
        self.model = model

        app = QtWidgets.QApplication.instance()
        if app:
            app.aboutToQuit.connect(self.quit)
            app.aboutToQuit.connect(self.deleteLater)

    def run(self):
        self.worker = self.Worker(self.model)
        self.worker.begin_processing()
        sys.stderr.write(
            '{}.run() -> {}\n'.format(self.__class__.__name__, QtCore.QThread.currentThread()))
        self.started.emit()
        self.exec_()
