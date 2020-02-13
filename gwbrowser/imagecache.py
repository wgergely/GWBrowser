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
import OpenImageIO
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
    def func_wrapper(index, source=None, dest=None, dest_size=common.THUMBNAIL_IMAGE_SIZE, update=True):
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
            if hasattr(index, 'sourceModel'):
                index = index.model().mapToSource(index)
            model = index.model()
            data = model.model_data()[index.row()]
        try:
            return func(index, source=source,
                 dest=dest, dest_size=dest_size, update=update)
        except Exception as err:
            sys.stderr.write(traceback.format_exc())
            if index.isValid():
                data[common.ThumbnailRole] = data[common.DefaultThumbnailRole]
                data[common.ThumbnailBackgroundRole] = data[common.DefaultThumbnailBackgroundRole]
                data[common.FileThumbnailLoaded] = True
                model.indexUpdated.emit(index)
            return False
    return func_wrapper


@QtCore.Slot(QtCore.QModelIndex)
@oiio
def oiio_make_thumbnail(index, source=None, dest=None, dest_size=common.THUMBNAIL_IMAGE_SIZE, update=True, nthreads=3):
    """Main function for generating thumbnails using the python bindings of
    OpenImageIO.

    Example:

        .. code-block:: python

        # Pass an invalid QModelIndex when making a thumbnail from a specific file
        oiio_make_thumbnail(
            QtCore.QModelIndex(),
            source=ur'//sloth/jobs/TSTPP_0005/FILMS/TEASER/SHOTS/TS_0090/renders/animation/personajes/TENORIO SC9 ROUGH FINAL.mov',
            dest=ur'C:/tmp/debug_thumb.png',
            dest_size=1024
        )

        # Otherwise, both the destination and the source paths will be retrieved
        # from `QModelIndex.data()`
        oiio_make_thumbnail(
            index,
            dest_size=1024
        )

    Args:
        index (QModelIndex): A QModelIndex item.
        source (unicode): The path of the source file.
        dest (unicode): The save destination for the generated thumbnail.
        dest_size (int): The size of the generated thumbnail.
        update (bool): Emits an ``indexChanged`` signal when `true`.
        nthreads (int): The number of threads to use.

    Returns:
        Bool: `True` is the operation was successful, `False` upon failure.

    """
    def set_error_thumbnail():
        """This method will set the default thumbnail when generating a preview
        fails."""
        if not index.isValid():
            return
        model = index.model()
        data = model.model_data()[index.row()]
        data[common.ThumbnailRole] = data[common.DefaultThumbnailRole]
        data[common.ThumbnailBackgroundRole] = data[common.DefaultThumbnailBackgroundRole]
        data[common.FileThumbnailLoaded] = True

    # OpenImageIO ImageCache instance to control file handles
    cache = OpenImageIO.ImageCache()

    # If it's a sequence, we will find the largest file in the sequence and
    # generate the thumbnail for that item
    source = source if source else index.data(QtCore.Qt.StatusTipRole)
    if common.is_collapsed(source):
        source = common.find_largest_file(index)
    dest = dest if dest else index.data(common.ThumbnailPathRole)

    # It is best to make sure we're not trying to generate a thumbnail for
    # an enournmous file
    if QtCore.QFileInfo(source).size() >= 836870912:
        set_error_thumbnail()
        cache.invalidate(source, force=True)
        cache.invalidate(dest, force=True)
        return False

    # First let's check if the file is readable by OpenImageIO
    i = OpenImageIO.ImageInput.open(source)
    if not i:  # the file is not understood by OpenImageIO
        set_error_thumbnail()
        cache.invalidate(source, force=True)
        cache.invalidate(dest, force=True)
        return False
    i.close()

    img = OpenImageIO.ImageBuf(source)
    cache.invalidate(source, force=True)
    cache.invalidate(dest, force=True)

    # Let's check if the loaded item is a movie and let's pick the middle
    # of the timeline as the thumbnail image
    if img.spec().get_int_attribute(u'oiio:Movie') == 1:
        # [BUG] Not all codec formats are supported by ffmpeg. Sadly, there does
        # not seem to be proper error handling and an unsupported codec will
        # crash the whole app. I'll
        accepted_codecs = (u'h.264', u'mpeg-4')
        for codec in accepted_codecs:
            codec_name = img.spec().get_string_attribute(u'ffmpeg:codec_name')
            if codec.lower() not in codec_name.lower():
                set_error_thumbnail()
                cache.invalidate(source, force=True)
                cache.invalidate(dest, force=True)
                return False

        # http://lists.openimageio.org/pipermail/oiio-dev-openimageio.org/2017-December/001104.html
        frame = int(img.nsubimages / 2)
        img.reset(source, subimage=frame)

    if img.has_error:
        set_error_thumbnail()
        cache.invalidate(source, force=True)
        cache.invalidate(dest, force=True)
        return False

    _width, _height = get_width_height(
        int(dest_size), img.spec().width, img.spec().height)

    # Deep
    if img.spec().deep:
        img = OpenImageIO.ImageBufAlgo.flatten(img, nthreads=nthreads)

    spec = OpenImageIO.ImageSpec(_width, _height, 4, u'uint8')
    spec.channelnames = (u'R', u'G', u'B', u'A')
    spec.alpha_channel = 3
    spec.attribute(u'oiio:ColorSpace', u'Linear')
    spec.attribute(u'oiio:Gamma', u'0.454545')

    # Resizing the image
    b = OpenImageIO.ImageBufAlgo.resample(
        img, roi=spec.roi, interpolate=True, nthreads=nthreads)
    b.set_write_format(u'uint8')

    spec = b.spec()
    if spec.get_string_attribute(u'oiio:ColorSpace') == u'Linear':
        roi = OpenImageIO.get_roi(b.spec())
        roi.chbegin = 0
        roi.chend = 3
        OpenImageIO.ImageBufAlgo.pow(
            b, b, 1.0 / 2.2, roi, nthreads=nthreads)

    # On some dpx images I'm getting "GammaCorrectedinf" - trying to pretend here it is linear
    if spec.get_string_attribute(u'oiio:ColorSpace') == u'GammaCorrectedinf':
        spec.attribute(u'oiio:ColorSpace', u'Linear')
        spec.attribute(u'oiio:Gamma', u'0.454545')

    if int(spec.nchannels) < 3:
        b = OpenImageIO.ImageBufAlgo.channels(
            b, (spec.channelnames[0], spec.channelnames[0], spec.channelnames[0]), (u'R', u'G', u'B'))
    elif int(spec.nchannels) > 4:
        if spec.channelindex(u'A') > -1:
            b = OpenImageIO.ImageBufAlgo.channels(
                b, (u'R', u'G', u'B', u'A'), (u'R', u'G', u'B', u'A'))
        else:
            b = OpenImageIO.ImageBufAlgo.channels(
                b, (u'R', u'G', u'B'), (u'R', u'G', u'B'))

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
        xml, ElementTree.XMLParser(encoding=u'utf-8'))
    for attrib in root.findall(u'attrib'):
        if attrib.attrib[u'name'] == u'ICCProfile':
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
        _b.set_write_format(u'uint8')
        _b.set_pixels(OpenImageIO.get_roi(spec), pixels)
    else:
        _b = b

    # Saving the processed thumbnail
    i = OpenImageIO.ImageInput.open(source)
    if not i:  # the file is not understood by OpenImageIO
        set_error_thumbnail()
        cache.invalidate(source, force=True)
        cache.invalidate(dest, force=True)
        return False
    i.close()

    success = _b.write(dest, dtype=u'uint8')
    if not success:
        QtCore.QFile(dest).remove()
        set_error_thumbnail()
        cache.invalidate(source, force=True)
        cache.invalidate(dest, force=True)
        return False

    # We will update the index with saved and ask the model/view to update
    if not index.isValid():
        cache.invalidate(source, force=True)
        cache.invalidate(dest, force=True)
        return False

    model = index.model()
    try:
        data = model.model_data()[index.row()]
    except KeyError:
        cache.invalidate(source, force=True)
        cache.invalidate(dest, force=True)
        return True

    # We will load the image and the background color
    image = ImageCache.get(
        data[common.ThumbnailPathRole],
        data[QtCore.Qt.SizeHintRole].height() - common.ROW_SEPARATOR,
        overwrite=True)
    color = ImageCache.get(
        data[common.ThumbnailPathRole],
        u'BackgroundColor',
        overwrite=False)

    data[common.ThumbnailRole] = image
    data[common.ThumbnailBackgroundRole] = color
    data[common.FileThumbnailLoaded] = True

    if update:
        model.indexUpdated.emit(index)

    cache.invalidate(source, force=True)
    cache.invalidate(dest, force=True)
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

    @classmethod
    def get(cls, path, height, overwrite=False):
        """Returns a previously cached `QImage` if the image has already been
        cached, otherwise it will read, resize and cache the image found at `path`.

        Args:
            path (unicode):    Path to an image file.
            height (int):  The height of the image
            overwrite (bool): Replaces the cached image with new data

        Returns: QImage: The cached and resized QImage.

        """
        if not path:
            return None
        try:
            height = int(height)
        except ValueError:
            pass

        k = u'{path}:{height}'.format(
            path=path,
            height=height
        ).lower()

        # Return cached item if exsits
        if k in cls._data and not overwrite:
            return cls._data[k]
        if k in cls._data and overwrite:
            del cls._data[k]

        # Checking if the file can be opened
        i = OpenImageIO.ImageInput.open(path)
        if not i:
            return None
        i.close()

        image = QtGui.QImage(path)
        if image.isNull():
            return None

        image = cls.resize_image(image, height)
        image = image.convertToFormat(QtGui.QImage.Format_ARGB32)

        cls._data[u'{}:BackgroundColor'.format(path)] = cls.get_color_average(path)
        cls._data[k] = image

        return cls._data[k]

    @staticmethod
    def resize_image(image, size):
        """Returns a scaled copy of the `QImage` fitting inside the square of
        ``size``.

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
    def get_color_average(path):
        """Returns the average color of an image."""
        img = OpenImageIO.ImageBuf(path)
        stats = OpenImageIO.ImageBufAlgo.computePixelStats(img)
        a = stats.avg
        if len(a) in (3, 4):
            return QtGui.QColor.fromRgbF(*a)
        return QtGui.QColor()

    @classmethod
    def capture(cls, index):
        """Uses ``ScreenGrabber`` to save a custom screen-grab."""
        if not index.isValid():
            return

        if hasattr(index, 'sourceModel'):
            index = index.model().mapToSource(index)

        pixmap = ScreenGrabber.capture()
        if not pixmap:
            return
        if pixmap.isNull():
            return
        image = pixmap.toImage()
        image = cls.resize_image(image, common.THUMBNAIL_IMAGE_SIZE)
        if image.isNull():
            return

        f = QtCore.QFile(index.data(common.ThumbnailPathRole))
        if f.exists():
            f.remove()
        if not image.save(index.data(common.ThumbnailPathRole)):
            return

        image = cls.get(
            index.data(common.ThumbnailPathRole),
            index.data(QtCore.Qt.SizeHintRole).height() - 2,
            overwrite=True)
        color = cls.get(
            index.data(common.ThumbnailPathRole),
            'BackgroundColor',
            overwrite=False)

        data = index.model().model_data()
        data[index.row()][common.ThumbnailRole] = image
        data[index.row()][common.ThumbnailBackgroundRole] = color
        index.model().indexUpdated.emit(index)

    @classmethod
    def remove(cls, index):
        """Deletes the thumbnail file and the cached entries associated
        with it.

        """
        if not index.isValid():
            return

        source_index = index
        if hasattr(index, 'sourceModel'):
            source_index = index.model().mapToSource(index)

        data = source_index.model().model_data()
        data = data[source_index.row()]
        file_ = QtCore.QFile(data[common.ThumbnailPathRole])

        if file_.exists():
            if not file_.remove():
                print '# Failed to remove thumbnail: {}'.format(
                    data[common.ThumbnailPathRole])

        keys = [k for k in cls._data if data[common.ThumbnailPathRole].lower()
                in k.lower()]
        for key in keys:
            del cls._data[key]

        data[common.ThumbnailRole] = data[common.DefaultThumbnailRole]
        data[common.ThumbnailBackgroundRole] = data[common.DefaultThumbnailBackgroundRole]
        data[common.FileThumbnailLoaded] = False

        model = source_index.model()
        if not model.generate_thumbnails:
            source_index.model().indexUpdated.emit(source_index)
            return

        if not hasattr(source_index.model(), u'ThumbnailThread'):
            return
        if not source_index.model().ThumbnailThread:
            return

        source_index.model().ThumbnailThread.Worker.add_to_queue([index, ])
        source_index.model().indexUpdated.emit(source_index)

    @classmethod
    def pick(cls, index):
        """Opens a file-dialog to select an OpenImageIO compliant file# to use as a thumbnail."""
        if hasattr(index.model(), 'sourceModel'):
            index = index.model().mapToSource(index)

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
        cls.remove(index)
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
            return file_info.absoluteFilePath()

        k = u'rsc:{name}:{size}:{color}'.format(
            name=name, size=size, color=u'null' if not color else color.name())

        if k in cls._data:
            return cls._data[k]

        if not file_info.exists():
            return QtGui.QPixmap(size, size)

        image = QtGui.QImage()
        image.load(file_info.absoluteFilePath())

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

        # Setting transparency
        if opacity < 1.0:
            image = QtGui.QImage(
                image.size(), QtGui.QImage.Format_ARGB32)
            image.fill(QtCore.Qt.transparent)

            painter = QtGui.QPainter()
            painter.begin(image)
            painter.setOpacity(opacity)
            painter.drawImage(0, 0, image)
            painter.end()

            pixmap = QtGui.QPixmap()
            pixmap.convertFromImage(image)

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
