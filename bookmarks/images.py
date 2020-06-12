# -*- coding: utf-8 -*-
"""Module for most image related classes and methods including the
app's.

Thumbnails:
    We're relying on ``OpenImageIO`` to generate image and movie thumbnails.
    Thumbnail operations are multi-threaded.

    See ``ImageCache.oiio_make_thumbnail()`` for the OpenImageIO wrapper for
    generating thubmanails.

All generated thumbnails and ui resources are cached in ``ImageCache``.

"""
import uuid
import os
import functools
import OpenImageIO

from PySide2 import QtWidgets, QtGui, QtCore

import bookmarks.log as log
import bookmarks.common as common
import _scandir as _scandir
import bookmarks.defaultpaths as defaultpaths


oiio_cache = OpenImageIO.ImageCache(shared=True)
oiio_cache.attribute(u'max_memory_MB', 4096.0)
oiio_cache.attribute(u'max_open_files', 0)
oiio_cache.attribute(u'trust_file_extensions', 1)


BufferType = QtCore.Qt.UserRole
PixmapType = BufferType + 1
ImageType = PixmapType + 1
ResourcePixmapType = ImageType + 1
ColorType = ResourcePixmapType + 1

_capture_widget = None
_library_widget = None
_filedialog_widget = None
_viewer_widget = None


@QtCore.Slot(QtCore.QModelIndex)
@QtCore.Slot(unicode)
def set_from_source(index, source):
    """Method used to load a resource from source and cache to `ImageCache`.

    """
    if not index.isValid():
        return

    destination = get_thumbnail_path(
        index.data(common.ParentPathRole)[0],
        index.data(common.ParentPathRole)[1],
        index.data(common.ParentPathRole)[2],
        index.data(QtCore.Qt.StatusTipRole)
    )
    if QtCore.QFileInfo(destination).exists():
        if not QtCore.QFile(destination).remove():
            import bookmarks.common_ui as common_ui
            s = u'Error removing the previous thumbnail file'
            log.error(s)
            common_ui.ErrorBox(s, u'').open()
            raise RuntimeError(s)

    res = ImageCache.oiio_make_thumbnail(
        source,
        destination,
        common.THUMBNAIL_IMAGE_SIZE
    )
    if not res:
        import bookmarks.common_ui as common_ui
        s = u'Failed to make thumbnail.'
        log.error(s)
        common_ui.ErrorBox(s, u'').open()
        raise RuntimeError(s)

    # Flush and re-cache
    size = int(index.data(QtCore.Qt.SizeHintRole).height())

    ImageCache.flush(destination)
    ImageCache.get_image(destination, size)
    ImageCache.make_color(destination)

    if hasattr(index.model(), 'updateIndex'):
        index.model().updateIndex.emit(index)
    else:
        index.model().sourceModel().updateIndex.emit(index)


@QtCore.Slot(QtCore.QModelIndex)
def capture(index):
    """Used to capture and save and cache a thumbnail.

    Args:
        index (QtCore.QModelIndex):     An index associated with a file.

    """
    if not isinstance(index, QtCore.QModelIndex):
        s = u'Expected <type \'QModelIndex\'>, got {}'.format(type(index))
        log.error(s)
        raise TypeError(s)

    if not index.isValid():
        return

    widget = ScreenCapture()
    widget.captureFinished.connect(functools.partial(set_from_source, index))
    widget.open()


@QtCore.Slot(QtCore.QModelIndex)
def pick(index):
    """Prompts the user to select and image on the computer.

    Args:
        index (QtCore.QModelIndex):     A valid model index.

    """
    if not index.isValid():
        return

    global _filedialog_widget
    _filedialog_widget = QtWidgets.QFileDialog()
    _filedialog_widget.setFileMode(QtWidgets.QFileDialog.ExistingFile)
    _filedialog_widget.setViewMode(QtWidgets.QFileDialog.List)
    _filedialog_widget.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
    _filedialog_widget.setNameFilter(common.get_oiio_namefilters())
    _filedialog_widget.setFilter(
        QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
    _filedialog_widget.setLabelText(
        QtWidgets.QFileDialog.Accept, u'Pick thumbnail')
    # _filedialog_widget.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    _filedialog_widget.fileSelected.connect(
        functools.partial(set_from_source, index))
    _filedialog_widget.open()


@QtCore.Slot(QtCore.QModelIndex)
def remove(index):
    """Deletes the thumbnail file and the cached entries associated
    with it.

    """
    if not index.isValid():
        return
    source = get_thumbnail_path(
        index.data(common.ParentPathRole)[0],
        index.data(common.ParentPathRole)[1],
        index.data(common.ParentPathRole)[2],
        index.data(QtCore.Qt.StatusTipRole),
    )
    ImageCache.flush(source)

    if QtCore.QFile(source).exists():
        if not QtCore.QFile(source).remove():
            import bookmarks.common_ui as common_ui
            s = u'Could not remove the thumbnail'
            log.error(s)
            common_ui.ErrorBox(u'Error.', s).open()
            raise RuntimeError(s)

    data = index.model().model_data()[index.row()]
    data[common.ThumbnailLoaded] = False
    index.model().updateIndex.emit(index)


@QtCore.Slot(QtCore.QModelIndex)
def pick_from_library(index):
    global _filedialog_widget
    widget = ThumbnailLibraryWidget()
    widget.thumbnailSelected.connect(functools.partial(set_from_source, index))
    widget.open()


def get_thumbnail_path(server, job, root, file_path, proxy=False):
    """Returns the path of a thumbnail.

    If the `file_path` is a sequence, we will use the sequence's first
    item as our thumbnail.

    Args:
        server (unicode):       The `server` segment of the file path.
        job (unicode):          The `job` segment of the file path.
        root (unicode):         The `root` segment of the file path.
        file_path (unicode):    The full file path.

    Returns:
        unicode:                The resolved thumbnail path.

    """
    if common.is_collapsed(file_path) or proxy:
        file_path = common.proxy_path(file_path)
    name = common.get_hash(file_path) + u'.' + common.THUMBNAIL_FORMAT
    return (server + u'/' + job + u'/' + root + u'/.bookmark/' + name).lower()


def get_placeholder_path(file_path, fallback=None):
    """Returns an image path to use a generat thumbnail for the item.

    When an item has no generated or user-set thumbnail, we'll try and find
    a general one based on the file's type.

    Args:
        file_path (unicode): Path to a file or folder.

    Returns:
        unicode: Path to the placehoder image.

    """
    if not isinstance(file_path, unicode):
        raise TypeError(
            u'Invalid type. Expected <type \'unicode\', got {}'.format(type(file_path)))

    file_info = QtCore.QFileInfo(file_path)
    suffix = file_info.suffix().lower()
    if suffix:
        for ext in defaultpaths.get_extensions(
            defaultpaths.SceneFilter |
            defaultpaths.ExportFilter |
            defaultpaths.MiscFilter |
            defaultpaths.AdobeFilter
        ):
            if ext.lower() == suffix:
                return common.rsc_path(__file__, ext)
    if not fallback:
        fallback = u'placeholder'
    return common.rsc_path(__file__, fallback)



def invalidate(func):
    """Decorator.
    """
    @functools.wraps(func)
    def func_wrapper(source, **kwargs):
        result = func(source, **kwargs)
        oiio_cache.invalidate(source, force=True)
        return result

    return func_wrapper


@invalidate
def oiio_get_buf(source, hash=None, force=False):
    """Check and load a source image with OpenImageIO's format reader.

    Args:
        source (unicode):   Path to an OpenImageIO compatible image file.
        hash (str):         Defaults to `None`.
        force (bool):       When true, forces the buffer to be re-cached.

    Returns:
        ImageBuf: An `ImageBuf` instance or `None` if the file is invalid.

    """
    if not isinstance(source, unicode):
        raise TypeError(
            u'Expected <type \'unicode\'>, got {}'.format(type(source)))
    if hash is None:
        hash = common.get_hash(source)

    if not force and ImageCache.contains(hash, BufferType):
        return ImageCache.value(hash, BufferType)

    # We use the extension to initiate an ImageInput with a format
    # which in turn is used to check the source's validity
    if u'.' not in source:
        return None
    ext = source.split(u'.').pop().lower()
    i = OpenImageIO.ImageInput.create(ext)
    if not i:
        return None
    if not i.valid_file(source):
        i.close()
        return None

    # If all went well, we can initiate an ImageBuf
    i.close()
    buf = OpenImageIO.ImageBuf()
    buf.reset(source, 0, 0)
    if buf.has_error:
        return None

    ImageCache.setValue(hash, buf, BufferType)
    return buf


def oiio_get_qimage(path, buf=None, force=True):
    """Load the pixel data using OpenImageIO and return it as a
    `RGBA8888` / `RGB888` QImage.

    Args:
        path (unicode):                 Path to an OpenImageIO readable image.
        buf (OpenImageIO.ImageBuf):     When buf is valid ImageBuf instance it will be used
                                        as the source instead of `path`. Defaults to `None`.

    Returns:
        QImage: An QImage instance or `None` if the image/path is invalid.

    """
    if buf is None:
        buf = oiio_get_buf(path, force=force)
        oiio_cache.invalidate(path, force=True)
        if buf is None:
            return None

    # Cache this would require some serious legwork
    # Return the cached version if exists
    # hash = common.get_hash(buf.name)
    # if not force and hash in ImageCache.PIXEL_DATA:
    #     return ImageCache.PIXEL_DATA[hash]

    spec = buf.spec()
    if not int(spec.nchannels):
        return None
    if int(spec.nchannels) < 3:
        b = OpenImageIO.ImageBufAlgo.channels(
            buf,
            (spec.channelnames[0], spec.channelnames[0], spec.channelnames[0]),
            (u'R', u'G', u'B')
        )
    elif int(spec.nchannels) > 4:
        if spec.channelindex(u'A') > -1:
            b = OpenImageIO.ImageBufAlgo.channels(
                b, (u'R', u'G', u'B', u'A'), (u'R', u'G', u'B', u'A'))
        else:
            b = OpenImageIO.ImageBufAlgo.channels(
                b, (u'R', u'G', u'B'), (u'R', u'G', u'B'))

    np_arr = buf.get_pixels(OpenImageIO.UINT8)
    # np_arr = (np_arr / (1.0 / 255.0)).astype(np.uint8)

    if np_arr.shape[2] == 1:
        _format = QtGui.QImage.Format_Grayscale8
    if np_arr.shape[2] == 2:
        _format = QtGui.QImage.Format_Invalid
    elif np_arr.shape[2] == 3:
        _format = QtGui.QImage.Format_RGB888
    elif np_arr.shape[2] == 4:
        _format = QtGui.QImage.Format_RGBA8888
    elif np_arr.shape[2] > 4:
        _format = QtGui.QImage.Format_Invalid

    image = QtGui.QImage(
        np_arr,
        spec.width,
        spec.height,
        spec.width * spec.nchannels,  # scanlines
        _format
    )

    # The loaded pixel values are cached by OpenImageIO automatically.
    # By invalidating the buf, we can ditch the cached data.
    oiio_cache.invalidate(path, force=True)
    oiio_cache.invalidate(buf.name, force=True)

    # As soon as the numpy array is garbage collected, the data for QImage becomes
    # unusable and Qt5 crashes. This could possibly be a bug, I would expect,
    # the data to be copied automatically, but by making a copy
    # the numpy array can safely be GC'd
    return image.copy()


class ImageCache(QtCore.QObject):
    """Utility class for storing, and accessing image data.

    Data is associated with type, and hash values.
    The hash values are generated by `common.get_hash` using inpout file-paths.

    All cached images are stored in ``ImageCache.INTERNAL_DATA``. Loading image
    resources using `get_image()`, `get_pixmap()` will automatically cache
    values. To get and set values manually use the `value()` and `setValue()`
    methods. Application resources are loaded by
    ``ImageCache.get_rsc_pixmap()``.

    """
    COLOR_DATA = common.DataDict()
    RESOURCE_DATA = common.DataDict()
    PIXEL_DATA = common.DataDict()
    INTERNAL_DATA = common.DataDict({
        BufferType: common.DataDict(),
        PixmapType: common.DataDict(),
        ImageType: common.DataDict(),
        ResourcePixmapType: common.DataDict(),
        ColorType: common.DataDict(),
    })

    @classmethod
    def contains(cls, hash, cache_type):
        """Checks if the given hash exists in the database."""
        return hash in cls.INTERNAL_DATA[cache_type]

    @classmethod
    def value(cls, hash, cache_type, size=None):
        """Get a value from the ImageCache.

        Args:
            hash (str): A hash value generated by `common.get_hash`

        """
        if not cls.contains(hash, cache_type):
            return None
        if size is not None:
            if size not in cls.INTERNAL_DATA[cache_type][hash]:
                return None
            return cls.INTERNAL_DATA[cache_type][hash][size]
        return cls.INTERNAL_DATA[cache_type][hash]

    @classmethod
    def setValue(cls, hash, value, cache_type, size=None):
        """Sets a value in the ImageCache using `hash` and the `cache_type`.

        If force is `True`, we will flush the sizes stored in the cache before
        setting the new value. This only applies to Image- and PixmapTypes.

        """
        if not cls.contains(hash, cache_type):
            cls.INTERNAL_DATA[cache_type][hash] = common.DataDict()

        if cache_type == BufferType:
            if not isinstance(value, OpenImageIO.ImageBuf):
                raise TypeError(
                    u'Invalid type. Expected <type \'ImageBuf\'>, got {}'.format(type(value)))

            cls.INTERNAL_DATA[BufferType][hash] = value
            return cls.INTERNAL_DATA[BufferType][hash]

        elif cache_type == ImageType:
            if not isinstance(value, QtGui.QImage):
                raise TypeError(
                    u'Invalid type. Expected <type \'QImage\'>, got {}'.format(type(value)))
            if size is None:
                raise TypeError(u'size not set.')

            if not isinstance(size, int):
                size = int(size)

            cls.INTERNAL_DATA[cache_type][hash][size] = value
            return cls.INTERNAL_DATA[cache_type][hash][size]

        elif cache_type == PixmapType or cache_type == ResourcePixmapType:
            if not isinstance(value, QtGui.QPixmap):
                raise TypeError(
                    u'Invalid type. Expected <type \'QPixmap\'>, got {}'.format(type(value)))

            if not isinstance(size, int):
                size = int(size)

            cls.INTERNAL_DATA[cache_type][hash][size] = value
            return cls.INTERNAL_DATA[cache_type][hash][size]

        elif cache_type == ColorType:
            if not isinstance(value, QtGui.QColor):
                raise TypeError(
                    u'Invalid type. Expected <type \'QColor\'>, got {}'.format(type(value)))

            cls.INTERNAL_DATA[ColorType][hash] = value
            return cls.INTERNAL_DATA[ColorType][hash]
        else:
            raise TypeError('Invalid cache type.')

    @classmethod
    def flush(cls, source):
        hash = common.get_hash(source)
        for k in cls.INTERNAL_DATA:
            if hash in cls.INTERNAL_DATA[k]:
                del cls.INTERNAL_DATA[k][hash]

    @classmethod
    def get_pixmap(cls, source, size, hash=None, force=False):
        """Loads, resizes `source` as a QPixmap and stores it for later use.

        The resource will be stored as a QPixmap instance in
        `INTERNAL_DATA[PixmapType][hash]`. The hash value is generated using
        `source`'s value but this can be overwritten by explicitly setting
        `hash`.

        Note:
            It is not possible to call this method outside the main gui thread.
            Use `get_image` instead. This method is backed by `get_image()`
            anyway!

        Args:
            source (unicode):   Path to an OpenImageIO compliant image file.
            size (int):         The size of the requested image.
            hash (str):         Use this hash key instead source to store the data.

        Returns:
            QPixmap: The loaded and resized QPixmap, or null pixmap if loading fails.

        """
        if not isinstance(source, unicode):
            raise TypeError(u'Invalid type. Expected <type \'unicode\'>')

        if QtWidgets.QApplication.instance().thread() != QtCore.QThread.currentThread():
            s = u'Pixmaps can only be initiated in the main gui thread.'
            log.error(s)
            raise RuntimeError(s)

        if size is not None:
            if not isinstance(size, int):
                raise TypeError(u'Invalid type. Expected <type \'int\'>')

        # Check the cache and return the previously stored value if exists
        hash = common.get_hash(source)
        contains = cls.contains(hash, PixmapType)
        if not force and contains:
            data = cls.value(hash, PixmapType, size=size)
            if data:
                return data

        # We'll load a cache a QImage to use as the basis for the qpixmap. This
        # is because of how the thread affinity of QPixmaps don't permit use
        # outside the main gui thread
        image = cls.get_image(source, size, hash=hash, force=force)
        if not image:
            return None

        pixmap = QtGui.QPixmap()
        pixmap.convertFromImage(image, flags=QtCore.Qt.ColorOnly)
        if pixmap.isNull():
            return None
        cls.setValue(hash, pixmap, PixmapType, size=size)
        return pixmap

    @classmethod
    def get_color(cls, source, force=False):
        """Get a color
        """
        if not isinstance(source, unicode):
            raise TypeError(u'Invalid type. Expected <type \'unicode\'>')

        # Check the cache and return the previously stored value if exists
        hash = common.get_hash(source)

        if not force and cls.contains(hash, ColorType):
            data = cls.value(hash, ColorType)
            if data:
                return data
        if force:
            color = cls.make_color(source)
            if color:
                return color
        return None

    @classmethod
    def make_color(cls, source):
        buf = oiio_get_buf(source)
        if not buf:
            return None

        hash = common.get_hash(source)

        stats = OpenImageIO.ImageBufAlgo.computePixelStats(buf)
        if not stats:
            return None
        if stats.avg and len(stats.avg) > 3:
            color = QtGui.QColor(
                int(stats.avg[0] * 255),
                int(stats.avg[1] * 255),
                int(stats.avg[2] * 255),
                a=240
                # a=int(stats.avg[3] * 255)
            )
        elif stats.avg and len(stats.avg) == 3:
            color = QtGui.QColor(
                int(stats.avg[0] * 255),
                int(stats.avg[1] * 255),
                int(stats.avg[2] * 255),
            )
        elif stats.avg and len(stats.avg) < 3:
            color = QtGui.QColor(
                int(stats.avg[0] * 255),
                int(stats.avg[0] * 255),
                int(stats.avg[0] * 255),
            )
        else:
            return None

        cls.setValue(hash, color, ColorType)
        return color

    @classmethod
    def get_image(cls, source, size, hash=None, force=False):
        """Loads, resizes `source` as a QImage and stores it for later use.

        The resource will be stored as QImage instance at
        `INTERNAL_DATA[ImageType][hash]`. The hash value is generated by default
        using `source`'s value but this can be overwritten by explicitly
        setting `hash`.

        Args:
            source (unicode):   Path to an OpenImageIO compliant image file.
            size (int):         The size of the requested image.
            hash (str):         Use this hash key instead source to store the data.

        Returns:
            QImage: The loaded and resized QImage, or `None` if loading fails.

        """
        if not isinstance(source, unicode):
            raise TypeError(u'Invalid type. Expected <type \'unicode\'>')
        if size is not None:
            if isinstance(size, float):
                size = int(size)
            if not isinstance(size, int):
                raise TypeError(
                    u'Invalid type. Expected <type \'int\'>, got {}'.format(type(size)))

        if hash is None:
            hash = common.get_hash(source)

        # Check the cache and return the previously stored value
        if not force and cls.contains(hash, ImageType):
            data = cls.value(hash, ImageType, size=size)
            if data:
                return data

        # If not yet stored, load and save the data
        buf = oiio_get_buf(source, hash=hash, force=force)
        if not buf:
            return None

        image = QtGui.QImage(source)
        if image.isNull():
            return None

        # Let's resize...
        image = cls.resize_image(image, size)
        if image.isNull():
            return None

        # ...and store
        cls.setValue(hash, image, ImageType, size=size)
        return image

    @staticmethod
    def resize_image(image, size):
        """Returns a scaled copy of the image that fits in size.

        Args:
            image (QImage): The image to rescale.
            size (int): The size of the square to fit.

        Returns:
            QImage: The resized copy of the original image.

        """
        if not isinstance(size, (int, float)):
            raise TypeError(u'Invalid size.')
        if not isinstance(image, QtGui.QImage):
            raise TypeError(
                u'Expected a <type \'QtGui.QImage\'>, got {}.'.format(type(image)))

        w = image.width()
        h = image.height()
        factor = float(size) / max(float(w), float(h))
        w *= factor
        h *= factor

        return image.smoothScaled(int(w), int(h))

    @classmethod
    def get_rsc_pixmap(cls, name, color, size, opacity=1.0, get_path=False):
        """Loads an image resource and returns it as a sized (and recolored) QPixmap.

        Args:
            name (str): Name of the resource without the extension.
            color (QColor): The colour of the icon.
            size (int): The size of pixmap.

        Returns:
            QPixmap: The loaded image

        """
        source = u'{}/../rsc/{}.png'.format(__file__, name)
        file_info = QtCore.QFileInfo(source)

        if get_path:
            return file_info.absoluteFilePath()

        k = u'rsc:{name}:{size}:{color}'.format(
            name=name.lower(),
            size=int(size),
            color=u'null' if not color else color.name().lower()
        )

        if k in cls.RESOURCE_DATA:
            return cls.RESOURCE_DATA[k]

        if not file_info.exists():
            return QtGui.QPixmap()

        image = QtGui.QImage()
        image.load(file_info.filePath())
        if image.isNull():
            return QtGui.QPixmap()

        # Do a re-color pass on the source image
        if color is not None:
            painter = QtGui.QPainter()
            painter.begin(image)
            painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
            painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
            painter.setBrush(QtGui.QBrush(color))
            painter.drawRect(image.rect())
            painter.end()

        image = cls.resize_image(image, size)

        # Setting transparency
        if opacity < 1.0:
            _image = QtGui.QImage(image)
            _image.fill(QtCore.Qt.transparent)

            painter = QtGui.QPainter()
            painter.begin(_image)
            painter.setOpacity(opacity)
            painter.drawImage(0, 0, image)
            painter.end()
            image = _image

        # Finally, we'll convert the image to a pixmap
        pixmap = QtGui.QPixmap()
        pixmap.convertFromImage(image, flags=QtCore.Qt.ColorOnly)
        cls.RESOURCE_DATA[k] = pixmap
        return cls.RESOURCE_DATA[k]

    @classmethod
    def oiio_make_thumbnail(cls, source, destination, size, nthreads=4):
        """Converts `source` to an sRGB image fitting the bounds of `size`.

        Args:
            source (unicode): Source image's file path.
            destination (unicode): Destination of the converted image.
            size (int): The bounds to fit the converted image (in pixels).
            nthreads (int): Number of threads to use. Defaults to 4.

        Returns:
            bool: True if successfully converted the image.

        """
        log.debug(u'Converting {}...'.format(source), cls)

        def get_scaled_spec(source_spec):
            w = source_spec.width
            h = source_spec.height
            factor = float(size) / max(float(w), float(h))
            w *= factor
            h *= factor

            s = OpenImageIO.ImageSpec(int(w), int(h), 4, OpenImageIO.UINT8)
            s.channelnames = (u'R', u'G', u'B', u'A')
            s.alpha_channel = 3
            s.attribute(u'oiio:ColorSpace', u'sRGB')
            s.attribute(u'oiio:Gamma', u'0.454545')
            return s

        def shuffle_channels(buf, source_spec):
            if int(source_spec.nchannels) < 3:
                buf = OpenImageIO.ImageBufAlgo.channels(
                    buf,
                    (source_spec.channelnames[0], source_spec.channelnames[0],
                     source_spec.channelnames[0]),
                    (u'R', u'G', u'B')
                )
            elif int(source_spec.nchannels) > 4:
                if source_spec.channelindex(u'A') > -1:
                    buf = OpenImageIO.ImageBufAlgo.channels(
                        buf, (u'R', u'G', u'B', u'A'), (u'R', u'G', u'B', u'A'))
                else:
                    buf = OpenImageIO.ImageBufAlgo.channels(
                        buf, (u'R', u'G', u'B'), (u'R', u'G', u'B'))
            return buf

        def resize(buf, source_spec):
            buf = OpenImageIO.ImageBufAlgo.resample(
                buf, roi=destination_spec.roi, interpolate=True, nthreads=nthreads)
            return buf

        def flatten(buf, source_spec):
            if source_spec.deep:
                buf = OpenImageIO.ImageBufAlgo.flatten(buf, nthreads=nthreads)
            return buf

        def convert_color(buf, source_spec):
            colorspace = source_spec.get_string_attribute(u'oiio:ColorSpace')
            try:
                if colorspace != u'sRGB':
                    buf = OpenImageIO.ImageBufAlgo.colorconvert(
                        buf, colorspace, u'sRGB')
            except:
                log.error(u'Could not convert the color profile')
            return buf

        buf = oiio_get_buf(source)
        if not buf:
            return False
        source_spec = buf.spec()
        if source_spec.get_int_attribute(u'oiio:Movie') == 1:
            accepted_codecs = (u'h.264', u'h264', u'mpeg-4', u'mpeg4')
            codec_name = source_spec.get_string_attribute(u'ffmpeg:codec_name')
            # [BUG] Not all codec formats are supported by ffmpeg. There does
            # not seem to be (?) error handling and an unsupported codec will
            # crash ffmpeg and the rest of the app.
            if codec_name:
                if not [f for f in accepted_codecs if f.lower() in codec_name.lower()]:
                    log.debug(
                        u'Unsupported movie format: {}'.format(codec_name))
                    oiio_cache.invalidate(source, force=True)
                    return False

        destination_spec = get_scaled_spec(source_spec)
        buf = shuffle_channels(buf, source_spec)
        buf = flatten(buf, source_spec)
        # buf = convert_color(buf, source_spec)
        buf = resize(buf, source_spec)

        if buf.nchannels > 3:
            background_buf = OpenImageIO.ImageBuf(destination_spec)
            OpenImageIO.ImageBufAlgo.checker(
                background_buf,
                12, 12, 1,
                (0.3, 0.3, 0.3),
                (0.2, 0.2, 0.2)
            )
            buf = OpenImageIO.ImageBufAlgo.over(buf, background_buf)

        spec = buf.spec()
        buf.set_write_format(OpenImageIO.UINT8)

        # There seems to be a problem with the ICC profile exported from Adobe
        # applications and the PNG library. The sRGB profile seems to be out of
        # date and pnglib crashes when encounters an invalid profile. Removing
        # the ICC profile seems to fix the issue.
        _spec = OpenImageIO.ImageSpec()
        _spec.from_xml(spec.to_xml())  # this doesn't copy the extra attributes
        for i in spec.extra_attribs:
            if i.name.lower() == u'iccprofile':
                continue
            try:
                _spec[i.name] = i.value
            except:
                continue
        spec = _spec

        # On some dpx images I'm getting "GammaCorrectedinf"
        if spec.get_string_attribute(u'oiio:ColorSpace') == u'GammaCorrectedinf':
            spec[u'oiio:ColorSpace'] = u'sRGB'
            spec[u'oiio:Gamma'] = u'0.454545'

        # Initiating a new spec with the modified spec
        _buf = OpenImageIO.ImageBuf(spec)
        _buf.copy_pixels(buf)
        _buf.set_write_format(OpenImageIO.UINT8)

        if not QtCore.QFileInfo(QtCore.QFileInfo(destination).path()).isWritable():
            oiio_cache.invalidate(source, force=True)
            oiio_cache.invalidate(destination, force=True)
            log.error(u'Destination path is not writable')
            return False

        success = _buf.write(destination, dtype=OpenImageIO.UINT8)

        if not success:
            s = u'{}\n{}'.format(
                buf.geterror(),
                OpenImageIO.geterror())
            log.error(s)

            if not QtCore.QFile(destination).remove():
                log.error(u'Cleanup failed.')

            oiio_cache.invalidate(source, force=True)
            oiio_cache.invalidate(destination, force=True)
            return False

        oiio_cache.invalidate(source, force=True)
        oiio_cache.invalidate(destination, force=True)
        return True


class ScreenCapture(QtWidgets.QDialog):
    """A modal capture widget used to save a thumbnail.

    Signals:
        captureFinished (unicode): Emited with a filepath to the captured image.

    """
    captureFinished = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        global _capture_widget
        _capture_widget = self
        super(ScreenCapture, self).__init__(parent=parent)

        effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.capture_path = None

        self.fade_in = QtCore.QPropertyAnimation(effect, 'opacity')
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(0.5)
        self.fade_in.setDuration(500)
        self.fade_in.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        self._mouse_pos = None
        self._click_pos = None
        self._offset_pos = None

        self._capture_rect = QtCore.QRect()

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setCursor(QtCore.Qt.CrossCursor)

        self.setMouseTracking(True)
        self.installEventFilter(self)

        self.accepted.connect(self.capture)

    def _fit_screen_geometry(self):
        """Compute the union of all screen geometries, and resize to fit.

        """
        app = QtWidgets.QApplication.instance()
        try:
            workspace_rect = QtCore.QRect()
            for screen in app.screens():
                workspace_rect = workspace_rect.united(
                    screen.availableGeometry())
            self.setGeometry(workspace_rect)
        except:
            rect = app.primaryScreen().availableGeometry()
            self.setGeometry(rect)

    @QtCore.Slot()
    def capture(self):
        """Capture the screen using the current `capture_rectangle`.

        Saves the resulting pixmap as `png` and emits the `captureFinished`
        signal with the file's path. The slot is called by the dialog's
        accepted signal.

        """
        app = QtWidgets.QApplication.instance()
        if not app:
            return

        screen = app.screenAt(self._capture_rect.center())
        if not screen:
            log.error(u'Unable to find screen.')
            return

        pixmap = screen.grabWindow(
            app.screens().index(screen),
            self._capture_rect.x(),
            self._capture_rect.y(),
            self._capture_rect.width(),
            self._capture_rect.height()
        )
        if pixmap.isNull():
            import bookmarks.common_ui as common_ui
            s = u'Unknown error occured capturing the pixmap.'
            log.error(s)
            common_ui.ErrorBox(u'Capture failed', s).open()
            raise RuntimeError(s)

        destination = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation)
        destination = u'{}/{}/temp/{}.{}'.format(
            destination,
            common.PRODUCT,
            uuid.uuid1(),
            common.THUMBNAIL_FORMAT
        )
        f = QtCore.QFileInfo(destination)
        if not f.dir().exists():
            if not f.dir().mkpath(u'.'):
                import bookmarks.common_ui as common_ui
                s = u'Could not create temp folder.'
                log.error(s)
                common_ui.ErrorBox(u'Capture failed', s).open()
                raise RuntimeError(s)

        res = pixmap.save(
            destination,
            format='png',
            quality=100
        )

        if not res:
            import bookmarks.common_ui as common_ui
            s = u'Could not save the capture.'
            log.error(s)
            common_ui.ErrorBox(
                s, u'Was trying to save to {}'.format(destination)).open()
            raise RuntimeError(s)

        self.capture_path = destination
        self.captureFinished.emit(destination)

    def paintEvent(self, event):
        """Paint the capture window."""
        # Convert click and current mouse positions to local space.
        if not self._mouse_pos:
            mouse_pos = self.mapFromGlobal(QtGui.QCursor.pos())
        else:
            mouse_pos = self.mapFromGlobal(self._mouse_pos)

        click_pos = None
        if self._click_pos is not None:
            click_pos = self.mapFromGlobal(self._click_pos)

        painter = QtGui.QPainter()
        painter.begin(self)

        # Draw background. Aside from aesthetics, this makes the full
        # tool region accept mouse events.
        painter.setBrush(QtGui.QColor(0, 0, 0, 255))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(event.rect())

        # Clear the capture area
        if click_pos is not None:
            capture_rect = QtCore.QRect(click_pos, mouse_pos)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
            painter.drawRect(capture_rect)
            painter.setCompositionMode(
                QtGui.QPainter.CompositionMode_SourceOver)

        pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 64),
                         common.ROW_SEPARATOR(), QtCore.Qt.DotLine)
        painter.setPen(pen)

        # Draw cropping markers at click position
        if click_pos is not None:
            painter.drawLine(event.rect().left(), click_pos.y(),
                             event.rect().right(), click_pos.y())
            painter.drawLine(click_pos.x(), event.rect().top(),
                             click_pos.x(), event.rect().bottom())

        # Draw cropping markers at current mouse position
        painter.drawLine(event.rect().left(), mouse_pos.y(),
                         event.rect().right(), mouse_pos.y())
        painter.drawLine(mouse_pos.x(), event.rect().top(),
                         mouse_pos.x(), event.rect().bottom())

        painter.end()

    def keyPressEvent(self, event):
        """Cancel the capture on keypress."""
        if event.key() == QtCore.Qt.Key_Escape:
            self.reject()

    def mousePressEvent(self, event):
        """Start the capture"""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self._click_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        """Finalise the caputre"""
        if not isinstance(event, QtGui.QMouseEvent):
            return

        if event.button() != QtCore.Qt.NoButton and self._click_pos is not None and self._mouse_pos is not None:
            # End click drag operation and commit the current capture rect
            self._capture_rect = QtCore.QRect(
                self._click_pos,
                self._mouse_pos
            ).normalized()
            self._click_pos = None
            self._offset_pos = None
            self._mouse_pos = None
            self.accept()

    def mouseMoveEvent(self, event):
        """Constrain and resize the capture window."""
        self.update()

        if not isinstance(event, QtGui.QMouseEvent):
            return

        if not self._click_pos:
            return

        self._mouse_pos = event.globalPos()

        app = QtWidgets.QApplication.instance()
        modifiers = app.queryKeyboardModifiers()

        no_modifier = modifiers == QtCore.Qt.NoModifier

        control_modifier = modifiers & QtCore.Qt.ControlModifier
        alt_modifier = modifiers & QtCore.Qt.AltModifier

        const_mod = modifiers & QtCore.Qt.ShiftModifier
        move_mod = (not not control_modifier) or (not not alt_modifier)

        if no_modifier:
            self.__click_pos = None
            self._offset_pos = None
            self.update()
            return

        # Allowing the shifting of the rectagle with the modifier keys
        if move_mod:
            if not self._offset_pos:
                self.__click_pos = QtCore.QPoint(self._click_pos)
                self._offset_pos = QtCore.QPoint(event.globalPos())

            self._click_pos = QtCore.QPoint(
                self.__click_pos.x() - (self._offset_pos.x() - event.globalPos().x()),
                self.__click_pos.y() - (self._offset_pos.y() - event.globalPos().y())
            )

        # Shift constrains the rectangle to a square
        if const_mod:
            rect = QtCore.QRect()
            rect.setTopLeft(self._click_pos)
            rect.setBottomRight(event.globalPos())
            rect.setHeight(rect.width())
            self._mouse_pos = rect.bottomRight()

        self.update()

    def showEvent(self, event):
        self._fit_screen_geometry()
        self.fade_in.start()


class Viewer(QtWidgets.QGraphicsView):
    """The graphics view used to display an QPixmap read using OpenImageIO.

    """

    def __init__(self, parent=None):
        super(Viewer, self).__init__(parent=parent)
        self.item = QtWidgets.QGraphicsPixmapItem()
        self.item.setTransformationMode(QtCore.Qt.SmoothTransformation)
        self.setScene(QtWidgets.QGraphicsScene(parent=self))
        self.scene().addItem(self.item)

        self._track = True
        self._pos = None

        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setBackgroundBrush(QtGui.QColor(0, 0, 0, 0))
        self.setInteractive(True)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

        self.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

    def index(self):
        return self.parent().index()

    def paintEvent(self, event):
        """Custom paint event"""
        super(Viewer, self).paintEvent(event)

        index = self.index()
        if not index.isValid():
            return

        painter = QtGui.QPainter()
        painter.begin(self.viewport())

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        o = common.MARGIN()
        rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))

        font, metrics = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())
        rect.setHeight(metrics.height())

        # Filename
        text = index.data(QtCore.Qt.StatusTipRole)
        if text:
            common.draw_aliased_text(painter, font, QtCore.QRect(
                rect), text, QtCore.Qt.AlignLeft, common.TEXT)
            rect.moveTop(rect.center().y() + metrics.lineSpacing())

        text = index.data(common.DescriptionRole)
        if text:
            text = text if text else u''
            common.draw_aliased_text(painter, font, QtCore.QRect(
                rect), text, QtCore.Qt.AlignLeft, common.FAVOURITE)
            rect.moveTop(rect.center().y() + metrics.lineSpacing())
        text = index.data(common.FileDetailsRole)
        if text:
            text = u'{}'.format(text)
            text = u'   |   '.join(text.split(u';')) if text else u'-'
            common.draw_aliased_text(painter, font, QtCore.QRect(
                rect), text, QtCore.Qt.AlignLeft, common.TEXT)
            rect.moveTop(rect.center().y() + metrics.lineSpacing())

        # Image info
        ext = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole)).suffix()
        if ext.lower() in defaultpaths.get_extensions(defaultpaths.OpenImageIOFilter):
            font, metrics = common.font_db.secondary_font(
                common.SMALL_FONT_SIZE())

            path = index.data(QtCore.Qt.StatusTipRole)
            path = common.get_sequence_endpath(path)
            img = OpenImageIO.ImageBuf(path)
            image_info = img.spec().serialize().split('\n')
            image_info = [f.strip() for f in image_info if f]
            for n, text in enumerate(image_info):
                if n > 2:
                    break
                common.draw_aliased_text(
                    painter,
                    font,
                    QtCore.QRect(rect),
                    text,
                    QtCore.Qt.AlignLeft,
                    common.SECONDARY_TEXT
                )
                rect.moveTop(rect.center().y() + int(metrics.lineSpacing()))
        painter.end()

    def set_image(self, path):
        """Loads an image using OpenImageIO and displays the contents as a
        QPoxmap item.

        """
        image = oiio_get_qimage(path)

        if not image:
            return None
        if image.isNull():
            return None

        # Let's make sure we're not locking the resource
        oiio_cache.invalidate(path, force=True)

        pixmap = QtGui.QPixmap.fromImage(image)
        if pixmap.isNull():
            log.error('Could not convert QImage to QPixmap')
            return None

        self.item.setPixmap(pixmap)
        self.item.setShapeMode(QtWidgets.QGraphicsPixmapItem.MaskShape)
        self.item.setTransformationMode(QtCore.Qt.SmoothTransformation)

        size = self.item.pixmap().size()
        if size.height() > self.height() or size.width() > self.width():
            self.fitInView(self.item, QtCore.Qt.KeepAspectRatio)
        return self.item

    def wheelEvent(self, event):
        # Zoom Factor
        zoom_in_factor = 1.25
        zoom_out_factor = 1.0 / zoom_in_factor

        # Set Anchors
        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setResizeAnchor(QtWidgets.QGraphicsView.NoAnchor)

        # Save the scene pos
        original_pos = self.mapToScene(event.pos())

        # Zoom
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        self.scale(zoom_factor, zoom_factor)

        # Get the new position
        new_position = self.mapToScene(event.pos())

        # Move scene to old position
        delta = new_position - original_pos
        self.translate(delta.x(), delta.y())

    def keyPressEvent(self, event):
        event.ignore()


class ImageViewer(QtWidgets.QDialog):
    """Used to view an image.

    The image data is loaded using OpenImageIO and is then wrapped in a QGraphicsScene,
    using a QPixmap. See ``Viewer``.

    """

    def __init__(self, path, parent=None):
        global _viewer_widget
        _viewer_widget = self
        super(ImageViewer, self).__init__(parent=parent)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )

        self.delete_timer = QtCore.QTimer(parent=self)
        self.delete_timer.setSingleShot(True)
        self.delete_timer.setInterval(50)
        self.delete_timer.timeout.connect(self.close)
        self.delete_timer.timeout.connect(self.delete_timer.deleteLater)
        self.delete_timer.timeout.connect(self.deleteLater)

        self.load_timer = QtCore.QTimer(parent=self)
        self.load_timer.setSingleShot(True)
        self.load_timer.setInterval(10)
        self.load_timer.timeout.connect(self.load_timer.deleteLater)

        if not isinstance(path, unicode):
            self.done(QtWidgets.QDialog.Rejected)
            raise ValueError(
                u'Expected <type \'unicode\'>, got {}'.format(type(path)))

        import bookmarks.common_ui as common_ui

        self.path = path

        if not self.parent():
            common.set_custom_stylesheet(self)

        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            s = u'{} does not exists.'.format(path)
            common_ui.ErrorBox(
                u'Error previewing image.', s).open()
            log.error(s)
            self.done(QtWidgets.QDialog.Rejected)
            raise RuntimeError(s)

        if not oiio_get_buf(path, force=True):
            s = u'{} seems invalid.'.format(path)
            common_ui.ErrorBox(
                u'Error previewing image.', s).open()
            log.error(s)
            self.done(QtWidgets.QDialog.Rejected)
            raise RuntimeError(s)

        QtWidgets.QVBoxLayout(self)
        height = common.ROW_HEIGHT() * 0.6
        o = 0
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        self.hide_button = common_ui.ClickableIconButton(
            u'close',
            (common.REMOVE, common.REMOVE),
            height,
            parent=self
        )
        self.hide_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))

        def get_row(parent=None):
            row = QtWidgets.QWidget(parent=parent)
            row.setFixedHeight(height)
            QtWidgets.QHBoxLayout(row)
            row.layout().setContentsMargins(0, 0, 0, 0)
            row.layout().setSpacing(0)
            parent.layout().addWidget(row)
            row.setStyleSheet('background-color: rgba(0, 0, 0, 255);')
            return row

        row = get_row(parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.hide_button, 0)

        self.viewer = Viewer(parent=self)
        self.load_timer.timeout.connect(self.load_timer.deleteLater)
        self.load_timer.timeout.connect(lambda: self.viewer.set_image(path))

        self.layout().addWidget(self.viewer, 1)

        row = get_row(parent=self)

    def index(self):
        if self.parent():
            return self.parent().selectionModel().currentIndex()
        return QtCore.QModelIndex()

    def _fit_screen_geometry(self):
        app = QtWidgets.QApplication.instance()
        rect = app.primaryScreen().geometry()
        self.setGeometry(rect)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        pen = QtGui.QPen(common.SEPARATOR)
        pen.setWidth(common.ROW_SEPARATOR())
        painter.setPen(pen)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        color = ImageCache.get_color(self.path)
        if not color:
            color = ImageCache.make_color(self.path)
        if not color:
            color = QtGui.QColor(20, 20, 20, 240)
        painter.setBrush(color)
        painter.drawRect(self.rect())

        painter.end()

    def mousePressEvent(self, event):
        event.accept()
        self.close()
        self.deleteLater()

    def keyPressEvent(self, event):
        """We're mapping the key press events to the parent list."""
        if self.parent():
            if event.key() == QtCore.Qt.Key_Down:
                self.parent().key_down()
                self.parent().key_space()
            elif event.key() == QtCore.Qt.Key_Up:
                self.parent().key_up()
                self.parent().key_space()
            elif event.key() == QtCore.Qt.Key_Tab:
                self.parent().key_up()
                self.parent().key_space()
            elif event.key() == QtCore.Qt.Key_Backtab:
                self.parent().key_down()
                self.parent().key_space()

        self.delete_timer.start()

    def showEvent(self, event):
        self._fit_screen_geometry()
        self.load_timer.start()


class ThumbnailLibraryItem(QtWidgets.QLabel):
    """Custom QLabel ssed by the ThumbnailLibraryWidget to display an image.

    """
    clicked = QtCore.Signal(unicode)

    def __init__(self, path, parent=None):
        super(ThumbnailLibraryItem, self).__init__(parent=parent)
        self._path = path
        self._pixmap = None

        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setScaledContents(True)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        self.setMinimumSize(QtCore.QSize(
            common.ROW_HEIGHT() * 2, common.ROW_HEIGHT() * 2))

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.clicked.emit(self._path)

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        o = 1.0 if hover else 0.7
        painter.setOpacity(o)

        if not self._pixmap:
            self._pixmap = ImageCache.get_pixmap(
                self._path,
                self.height(),
                force=True
            )
            if not self._pixmap:
                return

        s = float(min((self.rect().height(), self.rect().width())))
        longest_edge = float(
            max((self._pixmap.width(), self._pixmap.height())))
        ratio = s / longest_edge
        w = self._pixmap.width() * ratio
        h = self._pixmap.height() * ratio
        _rect = QtCore.QRect(0, 0, w, h)
        _rect.moveCenter(self.rect().center())
        painter.drawPixmap(
            _rect,
            self._pixmap,
        )
        if not hover:
            painter.end()
            return

        painter.setPen(common.TEXT)
        rect = self.rect()
        rect.moveTopLeft(rect.topLeft() + QtCore.QPoint(1, 1))

        text = self._path.split(u'/').pop()
        text = text.replace(u'thumb_', u'')
        font, metrics = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())

        common.draw_aliased_text(
            painter,
            font,
            rect,
            text,
            QtCore.Qt.AlignCenter,
            QtGui.QColor(0, 0, 0, 255),
        )

        rect = self.rect()
        common.draw_aliased_text(
            painter,
            font,
            rect,
            text,
            QtCore.Qt.AlignCenter,
            common.TEXT_SELECTED,
        )
        painter.end()


class ThumbnailLibraryWidget(QtWidgets.QDialog):
    """The widget used to browser and select a thumbnai from a set of
    predefined thumbnails.

    The thumbnail files are stored in the ./rsc folder and are prefixed by
    `thumb_*`.

    """
    thumbnailSelected = QtCore.Signal(unicode)
    label_size = common.ASSET_ROW_HEIGHT()

    def __init__(self, parent=None):

        # Global binding to avoid the widget being garbage collected.
        global _library_widget
        _library_widget = self

        super(ThumbnailLibraryWidget, self).__init__(parent=parent)
        self.scrollarea = None
        self.columns = 5

        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle(u'Select thumbnail')

        self._create_UI()
        self._add_thumbnails()

    def _create_UI(self):
        """Using scandir we will get all the installed thumbnail files from the rsc directory."""
        import bookmarks.common_ui as common_ui

        if not self.parent():
            common.set_custom_stylesheet(self)

        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN()

        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        row = common_ui.add_row(
            None, height=common.ROW_HEIGHT(), padding=None, parent=self)
        label = common_ui.PaintedLabel(
            u'Select a thumbnail',
            color=common.TEXT,
            size=common.LARGE_FONT_SIZE(),
            parent=self
        )
        row.layout().addWidget(label)

        widget = QtWidgets.QWidget(parent=self)
        widget.setStyleSheet(
            u'background-color: rgba({})'.format(common.rgb(common.SEPARATOR)))

        QtWidgets.QGridLayout(widget)
        widget.layout().setAlignment(QtCore.Qt.AlignCenter)
        widget.layout().setContentsMargins(
            common.INDICATOR_WIDTH(),
            common.INDICATOR_WIDTH(),
            common.INDICATOR_WIDTH(),
            common.INDICATOR_WIDTH())
        widget.layout().setSpacing(common.INDICATOR_WIDTH())

        self.scrollarea = QtWidgets.QScrollArea(parent=self)
        self.scrollarea.setWidgetResizable(True)
        self.scrollarea.setWidget(widget)
        self.layout().addWidget(self.scrollarea, 1)

    def _add_thumbnails(self):
        row = 0
        path = u'{}/../rsc'.format(__file__)
        path = os.path.normpath(os.path.abspath(path))

        idx = 0
        for entry in _scandir.scandir(path):
            if not entry.name.startswith(u'thumb_'):
                continue

            label = ThumbnailLibraryItem(
                entry.path.replace(u'\\', u'/'),
                parent=self
            )

            column = idx % self.columns
            if column == 0:
                row += 1
            self.scrollarea.widget().layout().addWidget(label, row, column)
            label.clicked.connect(self.thumbnailSelected)
            label.clicked.connect(self.close)

            idx += 1

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setBrush(common.SEPARATOR)
        pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 50))
        pen.setWidth(common.ROW_SEPARATOR())
        painter.setPen(pen)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        o = common.INDICATOR_WIDTH() * 2.0
        painter.setOpacity
        painter.drawRoundedRect(
            self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o)),
            o, o
        )
        painter.end()

    def showEvent(self, event):
        self._resize_widget()

    def _resize_widget(self):
        app = QtWidgets.QApplication.instance()
        rect = app.primaryScreen().availableGeometry()

        w = rect.width() * 0.66
        h = rect.height() * 0.66

        _rect = QtCore.QRect(0, 0, int(w), int(h))
        _rect.moveCenter(rect.center())
        self.setGeometry(_rect)
