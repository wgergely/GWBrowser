import sys
import functools
import array
import Queue
from contextlib import contextmanager

from PySide2 import QtWidgets, QtGui, QtCore
import browser.utils.PIL.Image as Image
from browser.settings import AssetSettings

try:
    # To import OpenEXR, the Imath module needs to be added to the system path
    sys.path.append('{}/../'.format(__file__))
    import browser.utils.OpenEXR as OpenEXR
except ImportError as err:
    sys.stderr.write('# Browser: OpenEXR import error\n{}\n'.format(err))

import browser.common as common


@contextmanager
def open_exr(s):
    exr = OpenEXR.InputFile(s)
    yield exr
    exr.close()


def encode_to_sRGB(v):
    if (v <= 0.0031308):
        return (v * 12.92) * 255.0
    else:
        return (1.055 * (v**(1.0 / 2.4)) - 0.055) * 255.0


def resize_Image(image, size):
    longer = float(max(image.size[0], image.size[1]))
    factor = float(float(size) / float(longer))
    if image.size[0] < image.size[1]:
        image = image.resize(
            (int(image.size[0] * factor), int(size)),
            Image.ANTIALIAS)
        return image
    image = image.resize(
        (int(size), int(image.size[1] * factor)),
        Image.ANTIALIAS)
    return image


def get_size(currentsize, size):
    longer = float(max(currentsize[0], currentsize[1]))
    factor = float(float(size) / float(longer))
    if currentsize[0] < currentsize[1]:
        return (int(currentsize[0] * factor), int(size))
    return (int(size), int(currentsize[1] * factor))


def exr_to_thumbnail(path, outpaths):
    """Saves an sRGB png thumbnail of the given exr."""
    with open_exr(path) as exr:
        if not exr.isComplete():
            return

        dw = exr.header()['dataWindow']
        size = (dw.max.x - dw.min.x + 1, dw.max.y - dw.min.y + 1)
        exr_channels = exr.header()['channels']

        mode = 'RGBA'
        rawmode = '32'
        for m in mode:
            if m in exr_channels:
                # https://pillow.readthedocs.io/en/3.1.x/handbook/writing-your-own-file-decoder.html
                k = str(exr_channels[m])
                if 'float' in k.lower():
                    rawmode = 'F;32NF'
                elif 'half' in k.lower():
                    rawmode = 'F;16'
                elif 'uint' in k.lower():
                    rawmode = 'F;8'
            if m not in exr_channels:
                mode = mode.replace(m, '')

        channels = []
        for channel in exr.channels(mode):
            pixels = array.array('f', channel)
            for idx in xrange(len(pixels)):
                pixels[idx] = encode_to_sRGB(pixels[idx])
            image = Image.frombytes(
                'F', size, pixels.tostring(), "raw", rawmode)
            channels.append(image.convert('L'))  # converts to luminosity

        image = Image.merge(mode, channels)
        image = image.crop(image.getbbox())
        image = resize_Image(image, common.THUMBNAIL_IMAGE_SIZE)
        for outpath in outpaths:
            image.save(outpath, format='PNG')


class ThumbnailGenerator(QtCore.QObject):
    """I'm guessing this object has to live permanently in the scope for the
    thread to work."""

    thumbnailUpdated = QtCore.Signal()

    def __init__(self, parent=None):
        super(ThumbnailGenerator, self).__init__(parent=parent)
        self._index = QtCore.QModelIndex()
        self.threadpool = QtCore.QThreadPool()

    def get(self, index):
        if index.isValid():
            self._index = index
        else:
            if not self._index.isValid():
                return

        path = self.get_biggest_file(self._index)
        file_info = QtCore.QFileInfo(path)
        func = None
        if u'exr' in file_info.suffix():
            func = functools.partial(
                exr_to_thumbnail,
                file_info.filePath(),
                (AssetSettings(index).thumbnail_path(),))

        if not func:
            return

        worker = Worker(func)

        def finished():
            print '!!! FINISHED !!!'

        def err(err):
            print '!!! {} !!!'.format(err)

        worker.signals.finished.connect(finished)
        worker.signals.finished.connect(self.cache_thumbnail)

        worker.signals.error.connect(err)
        self.threadpool.start(worker)

    def cache_thumbnail(self):
        if not self._index.isValid():
            return
        settings = AssetSettings(self._index)
        conf_dir = QtCore.QFileInfo(settings.conf_path())
        if not conf_dir.exists():
            QtCore.QDir().mkpath(conf_dir.path())
        height = self.parent().visualRect(self._index).height() - 2
        common.cache_image(settings.thumbnail_path(), height)

        self.thumbnailUpdated.emit()

    def get_biggest_file(self, index):
        """Finds the largest file of a sequence."""
        path = index.data(QtCore.Qt.StatusTipRole)
        path = common.get_sequence_startpath(path)

        file_info = QtCore.QFileInfo(path)
        match = common.get_sequence(file_info.fileName())
        if not match:  # File is not a sequence
            return path

        dir_ = file_info.dir()
        dir_.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        f = u'{}{}{}.{}'.format(
            match.group(1),
            u'?' * (len(match.group(2))),
            match.group(3),
            match.group(4),
        )
        dir_.setNameFilters((f,))
        return max(dir_.entryInfoList(), key=lambda f: f.size()).filePath()


class WorkerSignals(QtCore.QObject):
    finished = QtCore.Signal()
    error = QtCore.Signal(basestring)


class Worker(QtCore.QRunnable):

    def __init__(self, func, *args, **kwargs):
        super(Worker, self).__init__(*args, **kwargs)
        self.func = func

        # QRunnable doesnt have the capability to define signals
        self.signals = WorkerSignals()

        self.args = args
        self.kwargs = kwargs


    def run(self):
        try:
            self.func(*self.args, **self.kwargs)
            self.signals.finished.emit()
        except Exception as err:
            errstr = u'# Browser: Failed to generate thumbnail.\n{}\n'.format(
                err)
            sys.stderr.write(errstr)
            self.signals.error.emit(errstr)


if __name__ == '__main__':
    pass
    # app = QtWidgets.QApplication([])

    path = r'\\gordo\jobs\audible_8100\films\vignettes\shots\AU_dragon_lady\renders\render\helmet_formado\helmet_formado_01\vignettes_AU_dragon_lady_fx_helmet_formado_01_0351.exr'
    with open_exr(path) as exr:
        # print exr.header()
        print exr.header()['channels']['R']
    exr_to_thumbnail(path, ('C:/temp/temp3.png', ))
