# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, W0613, R0201, C0326


"""This modules defines most thumbnail-related classes and methods including
the image cache and the OpenImageIO-based thmbnail generator methods.

"""

import sys
import math

from PySide2 import QtWidgets, QtGui, QtCore

from browser.capture import ScreenGrabber
from browser.settings import AssetSettings
import browser.common as common
from browser.spinner import Spinner

import browser.modules  # loads the numpy, oiio libraries
import oiio.OpenImageIO as oiio
from oiio.OpenImageIO import ImageBuf, ImageSpec, ImageBufAlgo


class ImageCache(QtCore.QObject):
    """Utility class for setting, capturing and editing thumbnail and resource
    images.

    All cached images are stored in ``ImageCache.__data`` `(dict)` object.
    To add an image to the cache you can use the ``ImageCache.cache_image()`` method.
    Loading and caching ui resource items is done by ``ImageCache.get_rsc_pixmap()``.

    """
    # Data and instance container
    __data = {}
    __instance = None

    # Signals
    thumbnailChanged = QtCore.Signal(QtCore.QModelIndex)

    @staticmethod
    def instance():
        """ Static access method. """
        if ImageCache.__instance == None:
            ImageCache()
        return ImageCache.__instance

    @classmethod
    def initialize(cls, *args, **kwargs):
        """ Static create method. """
        cls(*args, **kwargs)
        return ImageCache.__instance
        sys.stdout.write('# ImageCache: Initialized.\n')

    def __init__(self, parent=None):
        super(ImageCache, self).__init__(parent=parent)
        if ImageCache.__instance != None:
            raise RuntimeError(u'\n# {} already initialized.\n# Use ImageCache.instance() instead.'.format(
                self.__class__.__name__))
        else:
            ImageCache.__instance = self

    def _reset_cached_item(self, path, removefile=True):
        """Resets any cached items containing `k` with the original placeholder image.

        Args:
            path (str): Normally, the path to the cached item.

        """
        file_ = QtCore.QFile(path)

        if file_.exists() and removefile:
            file_.remove()

        keys = [k for k in self.__data if path.lower() in k.lower()]
        for key in keys:
            if ':' in path:
                path, label = key.split(':')
                if 'BackgroundColor' in label:
                    continue
                self._assign_placeholder(path, int(label))

    def _assign_placeholder(self, path, height):
        """If a thumbnail doesn't exist, we will use a placeholder image to
        represent it.

        The placeholder image will be cached per size and associated with each key
        that doesn't have a valid thumbnail image saved.

        """
        file_info = QtCore.QFileInfo(
            u'{}/../rsc/placeholder.png'.format(__file__))
        height = int(height)

        pk = u'{path}:{height}'.format(
            path=file_info.filePath(),
            height=height
        )
        bgpk = u'{}:BackgroundColor'.format(file_info.filePath())
        k = u'{path}:{height}'.format(
            path=path,
            height=height
        )
        bgk = u'{}:BackgroundColor'.format(path)
        # The placehold has already been cached
        if pk in self.__data:
            self.__data[k] = self.__data[pk]
            self.__data[bgk] = QtGui.QColor(0, 0, 0, 0)
            return self.__data[k]

        if not file_info.exists():
            sys.stderr.write(
                '# Could not find the placeholder image. Using null.\n')
            return QtCore.QImage(height, height)

        # Loading a and resizing a copy of the placeholder
        image = QtGui.QImage()
        image.load(file_info.filePath())

        if image.isNull():
            sys.stderr.write(
                '# Could not load the placeholder image. Using null.\n')
            return QtCore.QImage(height, height)

        image = image.convertToFormat(QtGui.QImage.Format_ARGB32_Premultiplied)
        image = self.resize_image(image, height)

        self.__data[pk] = image
        self.__data[bgpk] = QtGui.QColor(0, 0, 0, 0)
        self.__data[k] = self.__data[pk]
        self.__data[bgk] = self.__data[bgpk]

        return self.__data[k]

    def get(self, path, element):
        """Main method to get a cached image. Automatically caches the element
        if not already in the cache."""
        k = '{}:{}'.format(path, element)
        if k in self.__data:
            return self.__data[k]
        try:
            element = int(element)
        except ValueError:
            return None
        return self.cache_image(path, element)

    def cache_image(self, path, height, overwrite=False):
        """Saves a resized copy of path to the cache.

        Returns the cached image if it already is in the cache, or the placholder
        image if the loading of the image fails. In addittion, each cached entry
        will be associated with an background color based on the image colour
        average.

        Args:
            path (str):    Path to the image file.
            height (int):  Description of parameter `height`.

        Returns:
            QImage: The cached and resized QImage.

        """
        height = int(height)

        k = u'{path}:{height}'.format(
            path=path,
            height=height
        )

        # Return cached item if exsits
        if k in self.__data and not overwrite:
            return self.__data[k]

        # If the file doesn't exist, return a placeholder
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            return self._assign_placeholder(path, height)

        image = QtGui.QImage()
        image.load(file_info.filePath())
        if image.isNull():
            return self._assign_placeholder(path, height)

        image = image.convertToFormat(QtGui.QImage.Format_ARGB32_Premultiplied)
        image = self.resize_image(image, height)

        # Saving the background color
        self.__data[u'{k}:BackgroundColor'.format(
            k=path
        )] = self.get_color_average(image)
        self.__data[k] = image

        return self.__data[k]

    @staticmethod
    def resize_image(image, size):
        """Returns a scaled copy of the image fitting inside the square of ``size``.

        Args:
            image (QImage): The image to rescale.
            size (int): The width/height of the square.

        Returns:
            QImage: The resized copy of the original image.

        """
        longer = float(max(image.width(), image.height()))
        factor = float(float(size) / float(longer))
        if image.width() < image.height():
            image = image.smoothScaled(
                float(image.width()) * factor,
                size
            )
            return image
        image = image.smoothScaled(
            size,
            float(image.height()) * factor
        )
        return image

    @staticmethod
    def get_color_average(image):
        """Returns the average color of an image."""
        if image.isNull():
            return QtGui.QColor(common.SECONDARY_BACKGROUND)

        r = []
        g = []
        b = []

        for x in xrange(image.width()):
            for y in xrange(image.height()):
                if image.pixelColor(x, y).alpha() < 0.01:
                    continue
                r.append(image.pixelColor(x, y).red())
                g.append(image.pixelColor(x, y).green())
                b.append(image.pixelColor(x, y).blue())

        if not all([float(len(r)), float(len(g)), float(len(b))]):
            average_color = QtGui.QColor(common.SECONDARY_BACKGROUND)
        else:
            average_color = QtGui.QColor(
                sum(r) / float(len(r)),
                sum(g) / float(len(g)),
                sum(b) / float(len(b))
            )
        average_color.setAlpha(average_color.alpha() / 2.0)
        return average_color

    @staticmethod
    def _find_largest_file(index):
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

    def generate_all(self, indexes, overwrite=False):
        """Generate"""
        def g(indexes, overwrite=overwrite):
            for index in indexes:
                dest = AssetSettings(index).thumbnail_path()
                if not overwrite and QtCore.QFileInfo(dest).exists():
                    continue
                yield index

        def chunks(l, n):
            """Yield successive n-sized chunks from l."""
            for i in xrange(0, len(l), n):
                yield l[i:i + n]

        idtc = QtCore.QThread.idealThreadCount()
        tc = idtc if idtc < 4 else 4
        # A list of QPersistentModelIndexes
        l = [f for f in g(indexes, overwrite=overwrite)]
        if not l:
            return
        # Chunks for the thread
        chunks = chunks(l, int(math.ceil(float(len(l)) / float(tc))))

        app = QtWidgets.QApplication.instance()
        parent = [f for f in app.allWidgets() if f.objectName()
                  == u'BrowserStackedWidget']
        parent = next((f for f in parent), None)
        if parent:
            spinner = Spinner(parent=parent)
            spinner.setFixedWidth(parent.width())
            spinner.show()
        # Creating threads
        for chunk in chunks:
            worker = CacheWorker(chunk)
            if parent:
                worker.signals.finished.connect(spinner.stop)
                worker.signals.update.connect(spinner.setText)
            QtCore.QThreadPool.globalInstance().start(worker)

    @classmethod
    def generate(cls, index, source=None):
        """OpenImageIO based method to generate sRGB thumbnails bound by ``THUMBNAIL_IMAGE_SIZE``."""
        if not index.isValid():
            return

        # If it's a sequence, we will find the largest file in the sequence and
        # generate the thumbnail for that item
        path = index.data(QtCore.Qt.StatusTipRole)
        if not source:
            if common.is_collapsed(path):
                source = ImageCache._find_largest_file(index)

        source = source if source else index.data(QtCore.Qt.StatusTipRole)
        dest = AssetSettings(index).thumbnail_path()

        # First let's check if the file is competible with OpenImageIO
        i = oiio.ImageInput.open(source)
        if not i:
            sys.stderr.write(oiio.geterror())
            return  # the file is not understood by OenImageIO

        img = ImageBuf(source)

        if img.has_error:
            sys.stderr.write('# OpenImageIO: Skipped reading {}\n{}\n'.format(
                source, img.geterror()))
            return

        # Deep
        if img.spec().deep:
            img = ImageBufAlgo.flatten(img)

        size = int(common.THUMBNAIL_IMAGE_SIZE)
        spec = ImageSpec(size, size, 4, "uint8")
        spec.channelnames = ('R', 'G', 'B', 'A')
        spec.alpha_channel = 3
        spec.attribute('oiio:ColorSpace', 'Linear')
        b = ImageBuf(spec)
        b.set_write_format('uint8')

        oiio.set_roi_full(img.spec(), oiio.get_roi(img.spec()))
        ImageBufAlgo.fit(b, img)

        spec = b.spec()
        if spec.get_string_attribute('oiio:ColorSpace') == 'Linear':
            roi = oiio.get_roi(b.spec())
            roi.chbegin = 0
            roi.chend = 3
            ImageBufAlgo.pow(b, b, 1.0 / 2.2, roi)

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
                '# OpenImageIO: Channel error {}.\n'.format(b.geterror()))

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
            _b.set_write_format('uint8')
            _b.set_pixels(oiio.get_roi(spec), pixels)
            if _b.has_error:
                sys.stderr.write('# OpenImageIO: Error setting pixels of {}.\n{}\n{}\n'.format(
                    dest, _b.geterror(), oiio.geterror()))
        else:
            _b = b

        # Ready to write
        if not _b.write(dest, dtype='uint8'):
            sys.stderr.write('# OpenImageIO: Error saving {}.\n{}\n{}\n'.format(
                dest, _b.geterror(), oiio.geterror()))
            QtCore.QFile(dest).remove()  # removing failed thumbnail save
        else:
            cls.instance().thumbnailChanged.emit(index)

    def capture(self, index):
        """Uses ``ScreenGrabber to save a custom screen-grab."""
        if not index.isValid():
            return
        settings = AssetSettings(index)

        pixmap = ScreenGrabber.capture()
        if pixmap.isNull():
            return

        image = pixmap.toImage()
        image = self.resize_image(image, common.THUMBNAIL_IMAGE_SIZE)
        if image.isNull():
            return

        if not image.save(settings.thumbnail_path()):
            sys.stderr.write('# Capture thumnail error: Error saving {}.\n'.format(
                settings.thumbnail_path()))
        else:
            self.thumbnailChanged.emit(index)

    def remove(self, index):
        """Deletes the thumbnail file from storage and the cached entry associated
        with it.

        Emits ``thumbnailChanged`` signal.

        """
        if not index.isValid():
            return
        settings = AssetSettings(index)
        self._reset_cached_item(settings.thumbnail_path(), removefile=True)

        self.thumbnailChanged.emit(index)

    @classmethod
    def pick(cls, index):
        """Opens a file-dialog to select an OpenImageIO compliant file."""
        dialog = QtWidgets.QFileDialog()
        common.set_custom_stylesheet(dialog)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilters(common.get_oiio_namefilters())
        dialog.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dialog.setLabelText(QtWidgets.QFileDialog.Accept, 'Pick thumbnail')
        dialog.setDirectory(QtCore.QFileInfo(
            index.data(QtCore.Qt.StatusTipRole)).filePath())
        # dialog.setOption(
        #     QtWidgets.QFileDialog.DontUseCustomDirectoryIcons, True)

        if not dialog.exec_():
            return
        if not dialog.selectedFiles():
            return

        # Saving the thumbnail
        cls.generate(index, source=dialog.selectedFiles()[0])

    @classmethod
    def get_rsc_pixmap(cls, name, color, size, opacity=1.0):
        """Loads a rescoure image and returns it as a re-sized and coloured QPixmap.

        Args:
            name (str): Name of the resource without the extension.
            color (QColor): The colour of the icon.
            size (int): The size of pixmap.

        Returns:
            QPixmap: The loaded image

        """

        k = u'{name}:{size}:{color}'.format(
            name=name, size=size, color=u'null' if not color else color.name())

        if k in cls.__data:
            return cls.__data[k]

        file_info = QtCore.QFileInfo(
            u'{}/../rsc/{}.png'.format(__file__, name))
        if not file_info.exists():
            return QtGui.QPixmap(size, size)

        image = QtGui.QImage()
        image.load(file_info.filePath())

        if image.isNull():
            return QtGui.QPixmap(size, size)

        image = image.convertToFormat(QtGui.QImage.Format_ARGB32_Premultiplied)
        if color is not None:
            painter = QtGui.QPainter()
            painter.begin(image)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
            painter.setBrush(QtGui.QBrush(color))
            painter.drawRect(image.rect())
            painter.end()

        image = cls.resize_image(image, size)
        pixmap = QtGui.QPixmap()
        pixmap.convertFromImage(image)

        # Setting transparency
        if opacity < 1.0:
            image = QtGui.QImage(
                pixmap.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
            image.fill(QtCore.Qt.transparent)

            painter = QtGui.QPainter()
            painter.begin(image)
            painter.setOpacity(opacity)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()

            pixmap = QtGui.QPixmap()
            pixmap.convertFromImage(image)

        cls.__data[k] = pixmap
        return cls.__data[k]


class CacheWorkerSignals(QtCore.QObject):
    finished = QtCore.Signal()
    update = QtCore.Signal(basestring)


class CacheWorker(QtCore.QRunnable):
    """Generic QRunnable, taking an index as it's first argument."""

    def __init__(self, chunk):
        super(CacheWorker, self).__init__()
        self.chunk = chunk
        self.signals = CacheWorkerSignals()

    @QtCore.Slot()
    def run(self):
        """The main work method run in a secondary thread."""
        for index in self.chunk:
            filename = QtCore.QFileInfo(index.data(
                QtCore.Qt.StatusTipRole)).fileName()
            self.signals.update.emit('Processing {}...'.format(filename))
            ImageCache.generate(index)
        self.signals.finished.emit()


# Initializing the ImageCache:
ImageCache.initialize()
