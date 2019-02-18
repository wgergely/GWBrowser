import sys
from PySide2 import QtWidgets, QtGui, QtCore

import browser.modules
import numpy
import oiio.OpenImageIO as oiio
from oiio.OpenImageIO import ImageBuf, ImageSpec, ImageBufAlgo

from browser.settings import AssetSettings
import browser.common as common



def generate_thumbnail(source, dest):
    """OpenImageIO based method to generate sRGB thumbnails bound by ``THUMBNAIL_IMAGE_SIZE``."""
    img = ImageBuf(source)

    if img.has_error:
        sys.stderr.write('# OpenImageIO: Skipped reading {}\n{}\n'.format(source, img.geterror()))
        return

    size = int(common.THUMBNAIL_IMAGE_SIZE)
    spec = ImageSpec(size, size, 4, "uint8")
    spec.channelnames = ('R', 'G', 'B', 'A')
    spec.alpha_channel = 3
    spec.attribute('oiio:ColorSpace', 'Linear')
    b = ImageBuf(spec)
    b.set_write_format('uint8')

    oiio.set_roi_full(img.spec(), oiio.get_roi(img.spec()))
    ImageBufAlgo.fit(b, img)

    file_info = QtCore.QFileInfo(dest)
    if not file_info.dir().exists():
        QtCore.QDir().mkpath(file_info.path())

    b = ImageBufAlgo.flatten(b)

    spec = b.spec()
    if spec.get_string_attribute('oiio:ColorSpace') == 'Linear':
        roi = oiio.get_roi(b.spec())
        roi.chbegin = 0
        roi.chend = 3
        ImageBufAlgo.pow(b, b, 1.0/2.2, roi)

    if int(spec.nchannels) < 3:
        b = ImageBufAlgo.channels(
            b, (spec.channelnames[0], spec.channelnames[0], spec.channelnames[0]), ('R', 'G', 'B'))
    elif int(spec.nchannels) > 4:
        if spec.channelindex('A') > -1:
            b = ImageBufAlgo.channels(
                b, ('R', 'G', 'B', 'A'), ('R', 'G', 'B', 'A'))
        else:
            b = ImageBufAlgo.channels(b, ('R', 'G', 'B'), ('R', 'G', 'B'))

    if b.has_error:
        sys.stderr.write(
            '# OpenImageIO: Channel error {}.\n{}\n'.format(b.geterror()))

    # There seems to be a problem with the ICC profile exported from Adobe
    # applications and the PNG library. The sRGB profile seems to be out of date
    # and pnglib crashes when encounters an invalid profile.
    # Removing the ICC profile seems to fix the issue. Annoying!

    # First, rebuilding the attributes as a modified xml tree
    modified = False

    from xml.etree import ElementTree
    root = ElementTree.fromstring(b.spec().to_xml())
    for attrib in root.findall('attrib'):
        if attrib.attrib['name'] == 'ICCProfile':
            root.remove(attrib)
            modified = True
            break

    if modified:
        xml = ElementTree.tostring(root)
        # Initiating a new spec with the modified xml
        spec = oiio.ImageSpec()
        spec.from_xml(xml)

        # Lastly, copying the pixels over from the old to the new buffer.
        _b = ImageBuf(spec)
        pixels = b.get_pixels()
        print _b.spec().width
        _b.set_write_format('uint8')
        _b.set_pixels(oiio.get_roi(spec), pixels)
        if _b.has_error:
            sys.stderr.write('# OpenImageIO: Error setting pixels of {}.\n{}\n{}\n'.format(
                file_info.fileName(), _b.geterror(), oiio.geterror()))
    else:
        _b = b
        
    # Ready to write
    if not _b.write(dest, dtype='uint8'):
        sys.stderr.write('# OpenImageIO: Error saving {}.\n{}\n{}\n'.format(
            file_info.fileName(), _b.geterror(), oiio.geterror()))
        QtCore.QFile(dest).remove() # removing failed thumbnail save


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
        if self.parent().model().sourceModel().is_grouped():
            path = self.get_biggest_file(index)
        else:
            path = index.data(QtCore.Qt.StatusTipRole)

        file_info = QtCore.QFileInfo(path)
        generate_thumbnail(path, AssetSettings(index).thumbnail_path())
        self.cache_thumbnail(index)

    def cache_thumbnail(self, index):
        """Caches the saved thumbnail image to the image cache."""
        if not index.isValid():
            return

        settings = AssetSettings(index)

        common.delete_image(settings.thumbnail_path(), delete_file=False)
        height = self.parent().visualRect(index).height() - 2
        common.cache_image(settings.thumbnail_path(), height)

        k = u'{path}:{height}'.format(
            path=settings.thumbnail_path(),
            height=height
        )


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
    path = r'//gordo/jobs/audible_8100/films/vignettes/shots/AU_dragon_lady/textures/Rock_Lava_tbhofjmr_8K_surface_ms/tbhofjmr_8K_Specular.jpg'
    generate_thumbnail(path, 'C:/temp/tbhofjmr_8K_Specular.jpg.png')
