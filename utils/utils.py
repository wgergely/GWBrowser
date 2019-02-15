import sys
import array
from contextlib import contextmanager

from PySide2 import QtWidgets, QtGui, QtCore

from browser.settings import AssetSettings


import browser.common as common


def encode_to_sRGB(v):
    if (v <= 0.0031308):
        return (v * 12.92) * 255.0
    else:
        return (1.055 * (v**(1.0 / 2.4)) - 0.055) * 255.0



def resize_Image(image, size):
    try:
        sys.path.insert(0, '{}\\..\\'.format(__file__))
        import browser.utils.OpenEXR as OpenEXR
        import browser.utils.pillow.Image as Image
        import browser.utils.Imath as Imath
    except ImportError as err:
        sys.stderr.write('# Browser: OpenEXR, Pillow import error\n{}\n'.format(err))
        return

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
    try:
        sys.path.insert(0, '{}\\..\\'.format(__file__))
        import browser.utils.OpenEXR as OpenEXR
        import browser.utils.pillow.Image as Image
        import browser.utils.Imath as Imath
    except ImportError as err:
        sys.stderr.write('# Browser: OpenEXR, Pillow import error\n{}\n'.format(err))
        return

    exr = OpenEXR.InputFile(path)
    if not exr.isComplete():
        return

    ptype = Imath.PixelType(Imath.PixelType.FLOAT)
    rawmode = 'F;32NF'
    dw = exr.header()['dataWindow']
    size = (dw.max.x - dw.min.x + 1, dw.max.y - dw.min.y + 1)
    exr_channels = exr.header()['channels']

    def check_mode(cns):
        for c in cns:
            if c not in exr_channels:
                cns = cns.replace(c, '')
        return cns

    mode = check_mode('RGBA')
    if not mode:
        mode, rawmode = check_mode('Z')
        if not mode:
            mode, rawmode = check_mode('N')
            if not mode:
                mode, rawmode = check_mode('U')

    if not mode:
        return

    channels = []
    for channel in mode:
        channel = exr.channel(channel, ptype)
        pixels = array.array('f', channel)
        #
        for idx in xrange(len(pixels)):
            pixels[idx] = encode_to_sRGB(pixels[idx])

        image = Image.frombytes(
            'F', size, pixels.tostring(), "raw", 'F;16', 10, 1)
        channels.append(image.convert('L'))  # converts to luminosity

    if 'RGB' in mode:
        image = Image.merge(mode, channels)
    else:
        image = Image.merge('RGB', [channels[0],] * 3)

    image = image.crop(image.getbbox())
    image = resize_Image(image, common.THUMBNAIL_IMAGE_SIZE)
    for outpath in outpaths:
        conf_dir = QtCore.QFileInfo(outpath)
        if not conf_dir.exists():
            QtCore.QDir().mkpath(conf_dir.path())
        image.save(outpath, format='PNG')


class ThumbnailGenerator(QtCore.QObject):
    """I'm guessing this object has to live permanently in the scope for the
    thread to work."""

    thumbnailUpdated = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, parent=None):
        super(ThumbnailGenerator, self).__init__(parent=parent)
        self.threadpool = QtCore.QThreadPool()
        self.threadpool.setMaxThreadCount(2)

    def get_all(self, parent):
        for n in xrange(parent.model().rowCount()):
            index = parent.model().index(n, 0, parent=QtCore.QModelIndex())
            self.get(index)

    def get(self, index):
        if not index.isValid():
            return

        worker = Worker(self.action, index)
        worker.signals.finished.connect(self.thumbnailUpdated.emit)
        self.threadpool.start(worker)

    def action(self, index):
        """The action executed by the QRunnable."""
        try:
            sys.path.insert(0, '{}\\..\\'.format(__file__))
            import browser.utils.OpenEXR as OpenEXR
            import browser.utils.pillow.Image as Image
            import browser.utils.Imath as Imath
        except ImportError as err:
            sys.stderr.write('# Browser: OpenEXR, Pillow import error\n{}\n'.format(err))
            return

        path = self.get_biggest_file(index)
        file_info = QtCore.QFileInfo(path)
        if u'exr' in file_info.suffix():
            exr_to_thumbnail(path, (AssetSettings(index).thumbnail_path(),))
        self.cache_thumbnail(index)

    def cache_thumbnail(self, index):
        """Caches the saved thumbnail image to the image cache."""
        if not index.isValid():
            return

        self.parent().setUpdatesEnabled(False)
        settings = AssetSettings(index)

        common.delete_image(settings.thumbnail_path(), delete_file=False)
        height = self.parent().visualRect(index).height() - 2
        common.cache_image(settings.thumbnail_path(), height)

        k = u'{path}:{height}'.format(
            path=settings.thumbnail_path(),
            height=height
        )

        self.parent().setUpdatesEnabled(True)

    def get_biggest_file(self, index):
        """Finds the sequence's largest file from sequence filepath.
        The largest files of the sequence will probably hold enough visual information
        to be used a s thumbnail image. :)

        """
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
    """QRunnables can't define signals themselves."""
    finished = QtCore.Signal(QtCore.QModelIndex)
    error = QtCore.Signal(basestring)


class Worker(QtCore.QRunnable):

    def __init__(self, func, index, *args, **kwargs):
        super(Worker, self).__init__(*args, **kwargs)
        self.func = func
        self.index = index

        # QRunnable doesnt have the capability to define signals
        self.signals = WorkerSignals()

        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.func(self.index, *self.args, **self.kwargs)
            self.signals.finished.emit(self.index)
        except Exception as err:
            errstr = u'# Browser: Failed to generate thumbnail.\n{}\n'.format(
                err)
            sys.stderr.write(errstr)
            self.signals.error.emit(errstr)


if __name__ == '__main__':
    pass

    # path = r'\\gordo\jobs\audible_8100\films\vignettes\shots\AU_dragon_lady\renders\render\helmet_formado\helmet_formado_01\vignettes_AU_dragon_lady_fx_helmet_formado_01_0351.exr'
    path = 'C:/temp/32L.exr'
    exr_to_thumbnail(path, ('C:/temp/32L.png', ))
    path = 'C:/temp/16L.exr'
    exr_to_thumbnail(path, ('C:/temp/16L.png', ))
    path = 'C:/temp/8L.exr'
    exr_to_thumbnail(path, ('C:/temp/8L.png', ))
