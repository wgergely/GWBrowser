import sys
from PySide2 import QtWidgets, QtGui, QtCore

import browser.modules
import oiio.OpenImageIO as oiio
from oiio.OpenImageIO import ImageBuf, ImageSpec, ImageBufAlgo

from browser.settings import AssetSettings
import browser.common as common



class ThumbnailGenerator(QtCore.QObject):
    """I'm guessing this object has to live permanently in the scope for the
    thread to work."""

    thumbnailUpdated = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, parent=None):
        super(ThumbnailGenerator, self).__init__(parent=parent)

    def get_all(self, parent):
        for n in xrange(parent.model().rowCount()):
            index = parent.model().index(n, 0, parent=QtCore.QModelIndex())
            self.get(index)

    def get(self, index):
        if not index.isValid():
            return

        worker = ModelIndexWorker(self.action, index)
        worker.signals.finished.connect(self.thumbnailUpdated.emit)
        QtCore.QThreadPool.globalInstance().start(worker)




class Signals(QtCore.QObject):
    """QRunnables can't define signals themselves."""
    finished = QtCore.Signal(QtCore.QModelIndex)


class Worker(QtCore.QRunnable):
    """Generic QRunnable, taking an index as it's first argument, used by ThumbnailGenerator
    to provide multithreading."""

    def __init__(self, func, index, *args, **kwargs):
        super(Worker, self).__init__()
        self.func = func
        self.index = index
        # QRunnable doesnt have the capability to define signals
        self.signals = Signals()

        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.func(self.index, *self.args, **self.kwargs)
            self.signals.finished.emit(self.index)
        except Exception as err:
            sys.stderr.write(u'# Worker error:\n{}\n'.format(err))




if __name__ == '__main__':
    path = r'//gordo/jobs/audible_8100/films/vignettes/shots/AU_dragon_lady/renders/render/helmet_formado/helmet_formado_05/vignettes_AU_dragon_lady_fx_helmet_formado_V05_deep_0295.exr'
    generate_thumbnail(path, 'C:/temp/tbhofjmr_8K_Specular.jpg.png')
