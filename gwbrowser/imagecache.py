# -*- coding: utf-8 -*-
"""The ``imagecache.py`` module defines most image-operation related classes and
methods including the global image cache.

Thumbnails
    We're relying on ``OpenImageIO`` to read and generate image and movie thumbnails.
    Thumbnail operations are multi-threaded and are mostly associated with
    the *FilesModel* (we only generate thumbnails from file OpenImageIO
    understands - bookmarks and assets are folders).

    The actual thumbnail processing is done ``oiio_make_thumbnail()``.

All generated thumbnails and ui resources are cached in ``ImageCache``.

"""

import os
import sys
import traceback
from xml.etree import ElementTree
from PySide2 import QtWidgets, QtGui, QtCore
import OpenImageIO.OpenImageIO as OpenImageIO
from gwbrowser.capture import ScreenGrabber
import gwbrowser.common as common

def get_width_height(bound, width, height):
    aspect = float(max((width, height))) / float(min((width, height)))
    is_horizontal = width > height

    if is_horizontal:
        _width = bound
        _height = bound / aspect
    else:
        _width = bound / aspect
        _height = bound
    return int(_width), int(_height)


def oiio(func):
    """Decorator to wrap the oiio process"""
    def func_wrapper(index, source=None, dest=None, dest_size=common.THUMBNAIL_IMAGE_SIZE):
        """This wrapper will make sure the passed parameters are ok to pass onto
        OpenImageIO. We will also update the index value here."""

        # When no source and destination are declared we expect the
        if not source and not dest and not index.isValid():
            return
        if index.isValid():
            # We won't process any items have a FileThumbnailLoaded propery set to `true`
            if index.data(common.FileThumbnailLoaded):
                return
            # These are saveguards for ignoring uninitiated index values
            if not index.data(QtCore.Qt.StatusTipRole):
                return
            if not index.data(common.FileInfoLoaded):
                return
            if not index.data(QtCore.Qt.SizeHintRole):
                return
            if not index.data(common.ThumbnailPathRole):
                return

            model = index.model()
            data = model.model_data()[index.row()]
            error_pixmap = ImageCache.get(
                common.rsc_path(__file__, u'failed'),
                data[QtCore.Qt.SizeHintRole].height() - common.ROW_SEPARATOR)
        try:
            func(index, source=source,
                 dest=dest, dest_size=dest_size)
        except Exception as err:
            sys.stderr.write(traceback.format_exc())
            if index.isValid():
                data[common.ThumbnailRole] = error_pixmap
                data[common.ThumbnailBackgroundRole] = common.THUMBNAIL_BACKGROUND
                data[common.FileThumbnailLoaded] = True
                model.indexUpdated.emit(index)
    return func_wrapper


@QtCore.Slot(QtCore.QModelIndex)
@QtCore.Slot(unicode)
@oiio
def oiio_make_thumbnail(index, source=None, dest=None, dest_size=common.THUMBNAIL_IMAGE_SIZE, nthreads=3):
    """This is a the main method generating thumbnail for items in GWBrowser.
    We're using the python binds of OpenImageIO to process the images.

    """
    def set_error_thumbnail():
        if not index.isValid():
            return
        model = index.model()
        data = model.model_data()[index.row()]
        error_pixmap = ImageCache.get(
            common.rsc_path(__file__, u'failed'),
            data[QtCore.Qt.SizeHintRole].height() - common.ROW_SEPARATOR)
        data[common.ThumbnailRole] = error_pixmap
        data[common.ThumbnailBackgroundRole] = common.THUMBNAIL_BACKGROUND
        data[common.FileThumbnailLoaded] = True

    # If it's a sequence, we will find the largest file in the sequence and
    # generate the thumbnail for that item
    source = source if source else index.data(QtCore.Qt.StatusTipRole)
    if common.is_collapsed(source):
        source = common.find_largest_file(index)
    dest = dest if dest else index.data(common.ThumbnailPathRole)

    # It is best to make sure we're not trying to generate a thumbnail for
    # an enournmous file - eg 512MB should be the biggest file we take
    if QtCore.QFileInfo(source).size() >= 836870912:
        set_error_thumbnail()
        return False
    # First let's check if the file is readable by OpenImageIO
    i = OpenImageIO.ImageInput.open(source)
    if not i:  # the file is not understood by OpenImageIO
        set_error_thumbnail()
        return False
    i.close()
    img = OpenImageIO.ImageBuf(source)

    # Let's check if the loaded item is a movie and let's pick the middle
    # of the timeline as the thumbnail image
    if img.spec().get_int_attribute('oiio:Movie') == 1:
        # http://lists.openimageio.org/pipermail/oiio-dev-openimageio.org/2017-December/001104.html
        frame = int(img.nsubimages / 2)
        img.reset(source, subimage=frame)

    if img.has_error:
        set_error_thumbnail()
        return False

    _width, _height = get_width_height(common.THUMBNAIL_IMAGE_SIZE, img.spec().width, img.spec().height)

    # Deep
    if img.spec().deep:
        img = OpenImageIO.ImageBufAlgo.flatten(img, nthreads=nthreads)

    size = int(dest_size)
    spec = OpenImageIO.ImageSpec(_width, _height, 4, 'uint8')
    spec.channelnames = ('R', 'G', 'B', 'A')
    spec.alpha_channel = 3
    spec.attribute('oiio:ColorSpace', 'Linear')
    spec.attribute('oiio:Gamma', '0.454545')

    b = OpenImageIO.ImageBufAlgo.resample(img, roi=spec.roi, interpolate=False, nthreads=nthreads)
    b.set_write_format('uint8')

    spec = b.spec()
    if spec.get_string_attribute('oiio:ColorSpace') == 'Linear':
        roi = OpenImageIO.get_roi(b.spec())
        roi.chbegin = 0
        roi.chend = 3
        OpenImageIO.ImageBufAlgo.pow(
            b, b, 1.0 / 2.2, roi, nthreads=nthreads)

    # On some dpx images I'm getting "GammaCorrectedinf" - trying to pretend here it is linear
    if spec.get_string_attribute('oiio:ColorSpace') == 'GammaCorrectedinf':
        spec.attribute('oiio:ColorSpace', 'Linear')
        spec.attribute('oiio:Gamma', '0.454545')

    if int(spec.nchannels) < 3:
        b = OpenImageIO.ImageBufAlgo.channels(
            b, (spec.channelnames[0], spec.channelnames[0], spec.channelnames[0]), ('R', 'G', 'B'))
    elif int(spec.nchannels) > 4:
        if spec.channelindex('A') > -1:
            b = OpenImageIO.ImageBufAlgo.channels(
                b, ('R', 'G', 'B', 'A'), ('R', 'G', 'B', 'A'))
        else:
            b = OpenImageIO.ImageBufAlgo.channels(
                b, ('R', 'G', 'B'), ('R', 'G', 'B'))

    # There seems to be a problem with the ICC profile exported from Adobe
    # applications and the PNG library. The sRGB profile seems to be out of date
    # and pnglib crashes when encounters an invalid profile.
    # Removing the ICC profile seems to fix the issue. Annoying!

    # First, rebuilding the attributes as a modified xml tree
    modified = False

    # On a few dpx images, I encoutered odd character-data that the xml
    # parser wouldn't take
    xml = b.spec().to_xml()
    xml = ''.join([i if ord(i) < 128 else ' ' for i in xml])
    root = ElementTree.fromstring(
        xml, ElementTree.XMLParser(encoding='utf-8'))
    for attrib in root.findall('attrib'):
        if attrib.attrib['name'] == 'ICCProfile':
            root.remove(attrib)
            modified = True
            break

    if modified:
        xml = ElementTree.tostring(root)
        # Initiating a new spec with the modified xml
        spec = OpenImageIO.ImageSpec()
        spec.from_xml(xml)

        # Lastly, copying the pixels over from the old to the new buffer.
        _b = OpenImageIO.ImageBuf(spec)
        pixels = b.get_pixels()
        _b.set_write_format('uint8')
        _b.set_pixels(OpenImageIO.get_roi(spec), pixels)
    else:
        _b = b

    # Saving the processed thumbnail
    success = _b.write(dest, dtype='uint8')
    if not success:
        QtCore.QFile(dest).remove()
        set_error_thumbnail()
        return False

    # We will update the index with saved and ask the model/view to update
    if not index.isValid():
        return False

    model = index.model()
    try:
        data = model.model_data()[index.row()]
    except KeyError:
        return

    # We will load the image and the background color
    image = ImageCache.get(
        data[common.ThumbnailPathRole],
        data[QtCore.Qt.SizeHintRole].height() - common.ROW_SEPARATOR,
        overwrite=True)
    color = ImageCache.get(
        data[common.ThumbnailPathRole],
        'BackgroundColor',
        overwrite=False)

    data[common.ThumbnailRole] = image
    data[common.ThumbnailBackgroundRole] = color
    data[common.FileThumbnailLoaded] = True
    model.indexUpdated.emit(index)
    return True


class ImageCache(QtCore.QObject):
    """Utility class for setting, capturing and editing thumbnail and resource
    images.

    All cached images are stored in ``ImageCache._data`` `(dict)` object.
    To add an image to the cache you can use the ``ImageCache.get()`` method.
    Loading and caching ui resource items is done by ``ImageCache.get_rsc_pixmap()``.

    """
    # Data and instance container
    _data = {}
    __instance = None

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

    def __init__(self, parent=None):
        """Init method.

        The associated ``ImageCacheThread`` control objects will be create and
        started here automatically.

        """
        if ImageCache.__instance != None:
            raise RuntimeError(u'\n# {} already initialized.\n# Use ImageCache.instance() instead.'.format(
                self.__class__.__name__))
        super(ImageCache, self).__init__(parent=parent)
        ImageCache.__instance = self

        # This will cache all the thumbnail images
        def rsc_path(f): return os.path.normpath(
            os.path.abspath(u'{}/../rsc/placeholder.png'.format(f)))
        ImageCache.get(rsc_path(__file__), common.ROW_HEIGHT - 2)


    @staticmethod
    def get(path, height, overwrite=False):
        """Saves a resized copy of path to the cache.

        Returns the cached image if it already is in the cache, or the placholder
        image if loading fails. In addittion, each cached entry
        will be associated with a backgroun- color based on the image's colours.

        Args:
            path (str):    Path to the image file.
            height (int):  Description of parameter `height`.

        Returns:
            QImage: The cached and resized QImage.

        """
        k = u'{path}:{height}'.format(
            path=path,
            height=height
        )

        if not path:
            return None

        # Return cached item if exsits
        if k in ImageCache._data and not overwrite:
            return ImageCache._data[k]

        # Checking if the file can be opened
        i = OpenImageIO.ImageInput.open(path)
        if not i:
            return None
        i.close()

        image = QtGui.QImage()
        image.load(path)
        if image.isNull():
            return None

        image = image.convertToFormat(QtGui.QImage.Format_ARGB32)
        image = ImageCache.resize_image(image, height)

        # Saving the background color
        ImageCache._data[u'{k}:BackgroundColor'.format(
            k=path
        )] = ImageCache.get_color_average(image)
        ImageCache._data[k] = image

        return ImageCache._data[k]

    @staticmethod
    def resize_image(image, size):
        """Returns a scaled copy of the image fitting inside the square of ``size``.

        Args:
            image (QImage): The image to rescale.
            size (int): The width/height of the square.

        Returns:
            QImage: The resized copy of the original image.

        """
        if not isinstance(size, (int, float)):
            return image
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
        # return common.SEPARATOR

        if image.isNull():
            return common.THUMBNAIL_BACKGROUND

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
            return common.THUMBNAIL_BACKGROUND
        else:
            average_color = QtGui.QColor(
                sum(r) / float(len(r)),
                sum(g) / float(len(g)),
                sum(b) / float(len(b))
            )
        return average_color

    def capture(self, index):
        """Uses ``ScreenGrabber`` to save a custom screen-grab."""
        if not index.isValid():
            return

        pixmap = ScreenGrabber.capture()
        if not pixmap:
            return
        if pixmap.isNull():
            return
        image = pixmap.toImage()
        image = self.resize_image(image, common.THUMBNAIL_IMAGE_SIZE)
        if image.isNull():
            return

        f = QtCore.QFile(index.data(common.ThumbnailPathRole))
        if f.exists():
            f.remove()
        if not image.save(index.data(common.ThumbnailPathRole)):
            return

        image = self.get(
            index.data(common.ThumbnailPathRole),
            index.data(QtCore.Qt.SizeHintRole).height() - 2,
            overwrite=True)
        color = self.get(
            index.data(common.ThumbnailPathRole),
            'BackgroundColor',
            overwrite=False)

        data = index.model().model_data()
        data[index.row()][common.ThumbnailRole] = image
        data[index.row()][common.ThumbnailBackgroundRole] = color
        index.model().dataChanged.emit(index, index)

    def remove(self, index):
        """Deletes the thumbnail file from storage and the cached entry associated
        with it.

        """
        if not index.isValid():
            return

        file_ = QtCore.QFile(index.data(common.ThumbnailPathRole))

        if file_.exists():
            file_.remove()

        keys = [k for k in self._data if index.data(
            common.ThumbnailPathRole).lower() in k.lower()]
        for key in keys:
            del self._data[key]

        data = index.model().model_data()
        data[index.row()][common.ThumbnailRole] = data[index.row()
                                                       ][common.DefaultThumbnailRole]
        data[index.row()][common.ThumbnailBackgroundRole] = data[index.row()
                                                                 ][common.DefaultThumbnailBackgroundRole]
        index.model().dataChanged.emit(index, index)

    @classmethod
    def pick(cls, index):
        """Opens a file-dialog to select an OpenImageIO compliant file."""
        dialog = QtWidgets.QFileDialog()
        common.set_custom_stylesheet(dialog)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilter(common.get_oiio_namefilters(as_array=False))
        dialog.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dialog.setLabelText(QtWidgets.QFileDialog.Accept, u'Pick thumbnail')
        dialog.setDirectory(QtCore.QFileInfo(
            index.data(QtCore.Qt.StatusTipRole)).filePath())

        if not dialog.exec_():
            return
        if not dialog.selectedFiles():
            return

        # Saving the thumbnail
        data = index.model().model_data()[index.row()]
        data[common.FileThumbnailLoaded] = False
        oiio_make_thumbnail(index, source=dialog.selectedFiles()[0])

    @classmethod
    def get_rsc_pixmap(cls, name, color, size, opacity=1.0, get_path=False):
        """Loads a rescoure image and returns it as a re-sized and coloured QPixmap.

        Args:
            name (str): Name of the resource without the extension.
            color (QColor): The colour of the icon.
            size (int): The size of pixmap.

        Returns:
            QPixmap: The loaded image

        """
        path = u'{}/../rsc/{}.png'.format(__file__, name)
        path = os.path.normpath(path)
        path = os.path.abspath(path)
        file_info = QtCore.QFileInfo(path)

        if get_path:
            return file_info.filePath()

        k = u'rsc:{name}:{size}:{color}'.format(
            name=name, size=size, color=u'null' if not color else color.name())

        if k in cls._data:
            return cls._data[k]

        if not file_info.exists():
            return QtGui.QPixmap(size, size)

        image = QtGui.QImage()
        image.load(file_info.filePath())

        if image.isNull():
            return QtGui.QPixmap(size, size)

        image = image.convertToFormat(QtGui.QImage.Format_ARGB32)
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
                pixmap.size(), QtGui.QImage.Format_ARGB32)
            image.fill(QtCore.Qt.transparent)

            painter = QtGui.QPainter()
            painter.begin(image)
            painter.setOpacity(opacity)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()

            pixmap = QtGui.QPixmap()
            pixmap.convertFromImage(image)

        cls._data[k] = pixmap
        return cls._data[k]

    @classmethod
    @QtCore.Slot()
    def reset_cache(cls):
        """Clears the image-cache."""
        data = {}
        for k, v in cls._data.iteritems():
            if u'rsc:' in k:
                data[k] = v
        cls._data = data

# Initializing the ImageCache:
ImageCache.initialize()
