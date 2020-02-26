# -*- coding: utf-8 -*-
"""The ``imagecache.py`` module defines most image-operation related classes and
methods including the global image cache.

Thumbnails
    We're relying on ``OpenImageIO`` to generate image and movie thumbnails.
    Thumbnail operations are multi-threaded and are mostly associated with
    the *FilesModel* (we only generate thumbnails from file OpenImageIO
    understands.

    To generate a thumbnail use ``ImageCache.openimageio_thumbnail()``.

All generated thumbnails and ui resources are cached in ``ImageCache``.

"""

import os
import traceback
from xml.etree import ElementTree
from PySide2 import QtWidgets, QtGui, QtCore
import OpenImageIO
from gwbrowser.capture import ScreenGrabber
import gwbrowser.common as common
from functools import wraps


def verify_index(func):
    """Decorator to create a menu set."""
    @wraps(func)
    def func_wrapper(cls, index, **kwargs):
        """Wrapper for function."""
        if not index.isValid():
            return
        if not index.data(common.FileInfoLoaded):
            return
        if hasattr(index, 'sourceModel'):
            index = index.model().mapToSource(index)

        return func(cls, index, **kwargs)
    return func_wrapper


class ImageCache(QtCore.QObject):
    """Utility class for setting, capturing and editing thumbnail and resource
    images.

    All cached images are stored in ``ImageCache.INTERNAL_IMAGE_DATA`` `(dict)` object.
    To add an image to the cache you can use the ``ImageCache.get()`` method.
    Loading and caching ui resource items is done by ``ImageCache.get_rsc_pixmap()``.

    """
    # Data and instance container
    INTERNAL_IMAGE_DATA = {}

    @classmethod
    def get(cls, path, height, overwrite=False):
        """Returns a previously cached `QPixmap` if the image has already been
        cached, otherwise it will read, resize and cache the image found at `path`.

        Args:
            path (unicode):    Path to an image file.
            height (int):  The height of the image
            overwrite (bool): Replaces the cached image with new data

        Returns: QPixmap: The cached and resized QPixmap.

        """
        if not path:
            return None
        try:
            height = int(height)
        except ValueError:
            pass

        path = path.lower()
        k = path + u':' + unicode(height)
        k = k.lower()

        # Return cached item if exsits
        if k in cls.INTERNAL_IMAGE_DATA and not overwrite:
            return cls.INTERNAL_IMAGE_DATA[k]

        if k in cls.INTERNAL_IMAGE_DATA and overwrite:
            del cls.INTERNAL_IMAGE_DATA[k]

        # Checking if the file can be opened
        i = OpenImageIO.ImageInput.open(path)
        if not i:
            return None
        i.close()

        image = QtGui.QPixmap(path)
        if image.isNull():
            return None

        image = cls.resize_image(image, height)
        bg_k = path + u':backgroundcolor'
        cls.INTERNAL_IMAGE_DATA[bg_k] = cls.get_color_average(path)
        if k != bg_k:
            cls.INTERNAL_IMAGE_DATA[k] = image

        return cls.INTERNAL_IMAGE_DATA[k]

    @staticmethod
    def resize_image(image, size):
        """Returns a scaled copy of the `QPixmap` fitting inside the square of
        ``size``.

        Args:
            image (QPixmap): The image to rescale.
            size (int): The width/height of the square.

        Returns:
            QPixmap: The resized copy of the original image.

        """
        if not isinstance(size, (int, float)):
            return image

        if isinstance(image, QtGui.QPixmap):
            image = image.toImage()

        w = image.width()
        h = image.height()
        factor = float(size) / max(float(w), float(h))
        w *= factor
        h *= factor

        image = image.smoothScaled(w, h)
        p = QtGui.QPixmap(w, h)
        p.convertFromImage(image)
        return p

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
    @verify_index
    def capture(cls, index):
        """Uses ``ScreenGrabber`` to save a custom screen-grab."""
        thumbnail_path = index.data(common.ThumbnailPathRole)

        pixmap = ScreenGrabber.capture()
        if not pixmap:
            return
        if pixmap.isNull():
            return
        image = pixmap.toImage()
        image = cls.resize_image(image, common.THUMBNAIL_IMAGE_SIZE)
        if image.isNull():
            return

        f = QtCore.QFile(thumbnail_path)
        if f.exists():
            f.remove()
        if not image.save(thumbnail_path):
            return

        image = cls.get(
            thumbnail_path,
            index.data(QtCore.Qt.SizeHintRole).height() - common.ROW_SEPARATOR,
            overwrite=True)
        color = cls.get(
            thumbnail_path,
            u'backgroundcolor',
            overwrite=False)

        data = index.model().model_data()
        data[index.row()][common.ThumbnailRole] = image
        data[index.row()][common.ThumbnailBackgroundRole] = color
        index.model().updateIndex.emit(index)

    @classmethod
    @verify_index
    def remove(cls, index):
        """Deletes the thumbnail file and the cached entries associated
        with it.

        """
        data = index.model().model_data()[index.row()]
        file_ = QtCore.QFile(data[common.ThumbnailPathRole])

        if file_.exists():
            if not file_.remove():
                print '# Failed to remove thumbnail: {}'.format(
                    data[common.ThumbnailPathRole])

        keys = [k for k in cls.INTERNAL_IMAGE_DATA if data[common.ThumbnailPathRole].lower()
                in k.lower()]
        for key in keys:
            del cls.INTERNAL_IMAGE_DATA[key]

        data[common.ThumbnailRole] = data[common.DefaultThumbnailRole]
        data[common.ThumbnailBackgroundRole] = data[common.DefaultThumbnailBackgroundRole]
        data[common.FileThumbnailLoaded] = False
        index.model().updateIndex.emit(index)

    @classmethod
    @verify_index
    def pick(cls, index, source=None):
        """Opens a file-dialog to select an OpenImageIO compliant file.

        """
        if not source:
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
            source = dialog.selectedFiles()[0]

        thumbnail_path = index.data(common.ThumbnailPathRole)

        cls.remove(index)
        cls.openimageio_thumbnail(
            source,
            thumbnail_path,
            common.THUMBNAIL_IMAGE_SIZE,
            nthreads=4
        )
        image = cls.get(
            thumbnail_path,
            index.data(QtCore.Qt.SizeHintRole).height() - common.ROW_SEPARATOR,
            overwrite=True)
        color = cls.get(
            thumbnail_path,
            u'backgroundcolor',
            overwrite=False)

        data = index.model().model_data()
        data[index.row()][common.ThumbnailRole] = image
        data[index.row()][common.ThumbnailBackgroundRole] = color
        index.model().updateIndex.emit(index)

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

        if get_path:
            # path = os.path.normpath(path)
            file_info = QtCore.QFileInfo(path)
            return file_info.absoluteFilePath()

        k = u'rsc:{name}:{size}:{color}'.format(
            name=name.lower(),
            size=int(size),
            color=u'null' if not color else color.name().lower()
        )

        if k in cls.INTERNAL_IMAGE_DATA:
            return cls.INTERNAL_IMAGE_DATA[k]

        path = os.path.normpath(path)
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            return QtGui.QPixmap(size, size)

        image = QtGui.QPixmap()
        image.load(file_info.filePath())

        if image.isNull():
            return QtGui.QPixmap(size, size)

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
            _image = QtGui.QPixmap(image.size())
            _image.fill(QtCore.Qt.transparent)

            painter = QtGui.QPainter()
            painter.begin(_image)
            painter.setOpacity(opacity)
            painter.drawPixmap(0, 0, image)
            painter.end()

            image = _image

        cls.INTERNAL_IMAGE_DATA[k] = image
        return cls.INTERNAL_IMAGE_DATA[k]

    @classmethod
    @QtCore.Slot()
    def reset_cache(cls):
        """Clears the image-cache."""
        for k in cls.INTERNAL_IMAGE_DATA.keys():
            if u'rsc:' not in k:
                del cls.INTERNAL_IMAGE_DATA[k]

    @classmethod
    def openimageio_thumbnail(cls, source, dest, dest_size, nthreads=4):
        """Generates a thumbnail using OpenImageIO."""
        # First let's check if the file is readable by OpenImageIO
        i = OpenImageIO.ImageInput.open(source)
        if not i:  # the file is not understood by OpenImageIO
            return False
        i.close()

        try:
            img = OpenImageIO.ImageBuf(source)
        except:
            print traceback.format_exc()
            return False
        s = img.spec()
        if source.split('.').pop().lower() in ('tif', 'tiff') and s.format == 'uint16':
            return False

        # Let's check if the loaded item is a movie and let's pick the middle
        # of the timeline as the thumbnail image
        if s.get_int_attribute(u'oiio:Movie') == 1:
            # [BUG] Not all codec formats are supported by ffmpeg. There does
            # not seem to be (?) error handling and an unsupported codec will
            # crash ffmpeg and the rest of the app.
            accepted_codecs = (u'h.264', u'mpeg-4')
            for codec in accepted_codecs:
                codec_name = s.get_string_attribute(u'ffmpeg:codec_name')
                if codec.lower() not in codec_name.lower():
                    return False

            # http://lists.openimageio.org/pipermail/oiio-dev-openimageio.org/2017-December/001104.html
            frame = int(img.nsubimages / 2)
            img.reset(source, subimage=frame)

        if img.has_error:
            return False

        # Deep
        if s.deep:
            img = OpenImageIO.ImageBufAlgo.flatten(img, nthreads=nthreads)


        w = s.width
        h = s.height
        factor = float(dest_size) / max(float(w), float(h))
        w *= factor
        h *= factor

        spec = OpenImageIO.ImageSpec(int(w), int(h), 4, OpenImageIO.FLOAT)
        spec.channelnames = (u'R', u'G', u'B', u'A')
        spec.alpha_channel = 3
        spec.attribute(u'oiio:ColorSpace', u'Linear')
        spec.attribute(u'oiio:Gamma', u'0.454545')

        # Resizing the image
        b = OpenImageIO.ImageBufAlgo.resample(
            img, roi=spec.roi, interpolate=True, nthreads=nthreads * 2)
        b.set_write_format(OpenImageIO.UINT8)

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
            _b.set_write_format(OpenImageIO.UINT8)
            _b.set_pixels(OpenImageIO.get_roi(spec), pixels)
        else:
            _b = b

        # Saving the processed thumbnail
        i = OpenImageIO.ImageInput.open(source)
        if not i:  # the file is not understood by OpenImageIO
            return False
        i.close()

        success = _b.write(dest, dtype=OpenImageIO.UINT8)
        if not success:
            QtCore.QFile(dest).remove()
            return False
        return True
