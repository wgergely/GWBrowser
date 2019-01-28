# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets
import time

"""https://stackoverflow.com/questions/6783194/background-thread-with-qthread-in-pyqt"""


class ModelWorker(QtCore.QObject):
    dataReady = QtCore.Signal(str)
    finished = QtCore.Signal() # Telling the tread to quit

    @QtCore.Slot(str)
    def get_data(self, path):
        def _iterator(path):
            """Iterates over all subfolders and delegates the THreadworker to querry
            the folders."""
            dir_ = QtCore.QDir(path)
            dir_.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
            dir_.setSorting(QtCore.QDir.Unsorted)
            for entry in dir_.entryList():
                self.dataReady.emit('{}/{}'.format(path, entry))
                _iterator('{}/{}'.format(path, entry))
        _iterator(path)
        self.finished.emit()


class Threadworker(QtCore.QObject):
    dataRequested = QtCore.Signal(str)
    finished = QtCore.Signal()

    def __init__(self, parent=None):
        super(Threadworker, self).__init__(parent=parent)
        self.thread = QtCore.QThread()

        self.worker = ModelWorker()
        self.worker.moveToThread(self.thread)
        self.dataRequested.connect(self.worker.get_data)
        self.worker.finished.connect(self.thread.exit)


def _print(data):
    print data, data

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    obj = Threadworker()
    obj.thread.finished.connect(app.quit)
    obj.thread.start()
    obj.dataRequested.connect(_print)
    # obj.thread.worker.finished.emit()
    for n in xrange(10):
        obj.dataRequested.emit(r'Z:\tkwwbk_8077\films\prologue\shots\sh_030\renders')
    # for n in xrange(20):
    #     obj.dataRequested.emit(n)


    app.exec_()
