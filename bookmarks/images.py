# -*- coding: utf-8 -*-
"""Module for most image related classes and methods including the
app's.

Thumbnails:
    We're relying on ``OpenImageIO`` to generate image and movie thumbnails.
    Thumbnail operations are multi-threaded.

    See ``ImageCache.oiio_make_thumbnail()`` for the OpenImageIO wrapper for
    generating thubmanails.

All generated thumbnails and ui resources are cached in ``ImageCache``.

Copyright (C) 2020 Gergely Wootsch

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <https://www.gnu.org/licenses/>.

"""
import os
import functools
import numpy as np
import OpenImageIO

from PySide2 import QtWidgets, QtGui, QtCore

import bookmarks.common as common
import bookmarks.defaultpaths as defaultpaths


oiio_cache = OpenImageIO.ImageCache(shared=True)
oiio_cache.attribute('max_memory_MB', 4096.0)
oiio_cache.attribute('max_open_files', 0)
oiio_cache.attribute('trust_file_extensions', 1)


def verify_index(func):
    """Decorator to create a menu set."""
    @functools.wraps(func)
    def func_wrapper(cls, index, **kwargs):
        """Wrapper for function."""
        if not index.isValid():
            return None
        if not index.data(common.FileInfoLoaded):
            return None
        if hasattr(index.model(), 'sourceModel'):
            index = index.model().mapToSource(index)

        return func(cls, index, **kwargs)
    return func_wrapper


def oiio_get_buf(source):
    """Check the given file for compatibility.

    Args:
        source (unicode): Path to an OpenImageIO compatible image file.

    Returns:
        ImageBuf: An `ImageBuf` instance or `None` if the file is invalid.

    """
    ext = source.split(u'.').pop().lower()
    i = OpenImageIO.ImageInput.create(ext)
    if not i:
        common.Log.error(OpenImageIO.geterror())
        return None

    if not i.valid_file(source):
        i.close()
        common.Log.error(u'{} is invalid'.format(source))
        return None

    i.close()

    buf = OpenImageIO.ImageBuf()
    buf.reset(source, 0, 0)

    if buf.has_error:
        common.Log.error(buf.geterror())
        return None

    return buf


def oiio_get_qimage(path):
    """Get the pixel data using OpenImageIO and wrap it in a QImage instance.

    """
    buf = oiio_get_buf(path)
    if buf is None:
        return None

    spec = buf.spec()
    if not int(spec.nchannels):
        return None
    if int(spec.nchannels) < 3:
        b = OpenImageIO.ImageBufAlgo.channels(
            buf,
            (spec.channelnames[0], spec.channelnames[0], spec.channelnames[0]),
            ('R', 'G', 'B')
        )
    elif int(spec.nchannels) > 4:
        if spec.channelindex('A') > -1:
            b = OpenImageIO.ImageBufAlgo.channels(
                b, ('R', 'G', 'B', 'A'), ('R', 'G', 'B', 'A'))
        else:
            b = OpenImageIO.ImageBufAlgo.channels(
                b, ('R', 'G', 'B'), ('R', 'G', 'B'))

    np_arr = buf.get_pixels()
    np_arr = (np_arr / (1.0 / 255.0)).astype(np.uint8)
    if np_arr.shape[2] == 3:
        format = QtGui.QImage.Format_RGB888
    elif np_arr.shape[2] == 4:
        format = QtGui.QImage.Format_RGBA8888
    else:
        format = QtGui.QImage.Format_RGB888

    image = QtGui.QImage(
        np_arr,
        spec.width,
        spec.height,
        spec.width * spec.nchannels,  # scanlines
        format
    )

    # As soon as the numpy array is garbage collected, the QImage becomes
    # unuseable. By making a copy, the numpy array can safely be GC'd
    # OpenImageIO.ImageCache().invalidate(path)
    return image.copy()


class CaptureScreen(QtWidgets.QDialog):
    """A modal screen capture widget.

    Inspired by Shotgun's screen capture tool.

    Example:

    .. code-block:: python
        :linenos:

        w = CaptureScreen()
        pixmap = w.exec_()

    """
    pixmapCaptured = QtCore.Signal(QtGui.QPixmap)

    def __init__(self, parent=None):
        super(CaptureScreen, self).__init__(parent=parent)
        self._pixmap = None

        effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

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
        self.setCursor(QtCore.Qt.CrossCursor)

        self.setMouseTracking(True)
        self.installEventFilter(self)

        self.accepted.connect(self.capture)

    def pixmap(self):
        """The captured rectangle."""
        return self._pixmap

    def _fit_screen_geometry(self):
        # Compute the union of all screen geometries, and resize to fit.
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

    @classmethod
    def _get_desktop_pixmap(cls, rect):
        app = QtWidgets.QApplication.instance()
        screen = app.screenAt(rect.center())
        if not screen:
            common.Log.error(u'Unable to find screen.')
            return None
        return screen.grabWindow(
            app.screens().index(screen),
            rect.x(),
            rect.y(),
            rect.width(),
            rect.height()
        )

    @QtCore.Slot()
    def capture(self):
        """Slot called by the dialog's accepted signal.
        Performs the capture operation and saves the resulting pixmap
        to self._pixmap

        """
        self._pixmap = self._get_desktop_pixmap(self._capture_rect)
        self.pixmapCaptured.emit(self._pixmap)

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
            self.ignore()

    def mousePressEvent(self, event):
        """Start the capture"""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.button() == QtCore.Qt.LeftButton:
            self._click_pos = event.globalPos()
        if event.button() == QtCore.Qt.RightButton:
            self.ignore()

    def mouseReleaseEvent(self, event):
        """Finalise the caputre"""
        if not isinstance(event, QtGui.QMouseEvent):
            return

        if event.button() == QtCore.Qt.LeftButton and self._click_pos is not None:
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

    def exec_(self):
        super(CaptureScreen, self).exec_()
        return self._pixmap


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
    def get(cls, path, height=None, overwrite=False):
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

        if height is not None:
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

        # A little leap of faith here as I'm using OpenImageIO to check if Qt5
        # can load the image. My reasoning is that the performance of oiio is
        # excellent and both qt5 and oiio use the same PNG library, hence if
        # oiio can open it qt5 should be able to as well. I also get access to
        # image properties this way
        buf = oiio_get_buf(path)
        if buf is None:
            return None

        if not height:
            spec = buf.spec()
            height = max((spec.height, spec.width))

        image = QtGui.QPixmap(path)
        if image.isNull():
            return None

        image = cls.resize_image(image, height)
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

    @classmethod
    @verify_index
    def capture(cls, index):
        """Save a custom screen-grab."""
        thumbnail_path = index.data(common.ThumbnailPathRole)

        w = CaptureScreen()
        image = w.exec_()

        if not image:
            return
        image = cls.resize_image(image, common.THUMBNAIL_IMAGE_SIZE)
        if image.isNull():
            return

        f = QtCore.QFile(thumbnail_path)
        if f.exists():
            f.remove()

        # Check if the folder is indeed writable
        dirpath = QtCore.QFileInfo(thumbnail_path).path()
        if not QtCore.QFileInfo(dirpath).isWritable():
            common.Log.error('The output path is not writable.')
            return

        if not image.save(thumbnail_path):
            return

        image = cls.get(
            thumbnail_path,
            index.data(QtCore.Qt.SizeHintRole).height() -
            common.ROW_SEPARATOR(),
            overwrite=True
        )

        data = index.model().model_data()
        data[index.row()][common.ThumbnailRole] = image
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
                s = u'Could not remove {}'.format(
                    data[common.ThumbnailPathRole])
                common.Log.error(s)

        keys = [k for k in cls.INTERNAL_IMAGE_DATA if data[common.ThumbnailPathRole].lower()
                in k.lower()]
        for key in keys:
            del cls.INTERNAL_IMAGE_DATA[key]

        data[common.ThumbnailRole] = data[common.DefaultThumbnailRole]
        data[common.FileThumbnailLoaded] = False
        index.model().updateIndex.emit(index)

    @classmethod
    @verify_index
    def pick(cls, index, source=None, parent=None):
        """Opens a file-dialog to select an OpenImageIO compliant file.

        """
        if not source:
            dialog = QtWidgets.QFileDialog(parent=parent)
            dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
            dialog.setViewMode(QtWidgets.QFileDialog.List)
            dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
            dialog.setNameFilter(common.get_oiio_namefilters())
            dialog.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
            dialog.setLabelText(
                QtWidgets.QFileDialog.Accept, u'Pick thumbnail')
            dialog.setDirectory(QtCore.QFileInfo(
                index.data(QtCore.Qt.StatusTipRole)).filePath())

            if not dialog.exec_():
                return
            if not dialog.selectedFiles():
                return
            source = dialog.selectedFiles()[0]

        thumbnail_path = index.data(common.ThumbnailPathRole)
        cls.remove(index)

        if not QtCore.QFileInfo(QtCore.QFileInfo(thumbnail_path).path()).isWritable():
            common.Log.error(u'Destination path is not writable.')
            return

        cls.oiio_make_thumbnail(
            source,
            thumbnail_path,
            common.THUMBNAIL_IMAGE_SIZE,
            nthreads=4)
        image = cls.get(
            thumbnail_path,
            index.data(QtCore.Qt.SizeHintRole).height(),
            overwrite=True)

        data = index.model().model_data()
        data[index.row()][common.ThumbnailRole] = image

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
            return QtGui.QPixmap()

        image = QtGui.QPixmap()
        image.load(file_info.filePath())

        if image.isNull():
            return QtGui.QPixmap()

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
            if u'rsc:' in k:
                continue
            del cls.INTERNAL_IMAGE_DATA[k]

    @classmethod
    def oiio_make_thumbnail(cls, source, dest, dest_size, nthreads=4):
        """OpenImageIO wrapper converts `source` to an sRGB image fitting int the bounds of `dest_size`.

        Args:
            source (unicode): Source image's file path.
            dest (unicode): Destination of the converted image.
            dest_size (int): The bounds to fit the converted image (in pixels).
            nthreads (int): Number of threads to use. Defaults to 4.

        Returns:
            bool: True if successfully converted the image.

        """
        common.Log.debug(u'Converting {}...'.format(source), cls)

        def get_scaled_spec(source_spec):
            w = source_spec.width
            h = source_spec.height
            factor = float(dest_size) / max(float(w), float(h))
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
                buf, roi=dest_spec.roi, interpolate=True, nthreads=nthreads)
            return buf

        def flatten(buf, source_spec):
            if source_spec.deep:
                buf = OpenImageIO.ImageBufAlgo.flatten(buf, nthreads=nthreads)
            return buf

        def convert_color(buf, source_spec):
            colorspace = source_spec.get_string_attribute(u'oiio:ColorSpace')
            try:
                if colorspace != 'sRGB':
                    buf = OpenImageIO.ImageBufAlgo.colorconvert(
                        buf, colorspace, 'sRGB')
            except:
                common.Log.error('Could not conver tthe color profile')
            return buf

        buf = oiio_get_buf(source)
        if not buf:
            return False

        source_spec = buf.spec()
        accepted_codecs = (u'h.264', u'h264', u'mpeg-4', u'mpeg4')
        codec_name = source_spec.get_string_attribute(u'ffmpeg:codec_name')

        if ext in (u'tif', u'tiff', u'gif') and source_spec.format == 'uint16':
            pass
            # return False

        if source_spec.get_int_attribute(u'oiio:Movie') == 1:
            # [BUG] Not all codec formats are supported by ffmpeg. There does
            # not seem to be (?) error handling and an unsupported codec will
            # crash ffmpeg and the rest of the app.
            for codec in accepted_codecs:
                if codec.lower() not in codec_name.lower():
                    common.Log.error(
                        u'Unsupported movie format: {}'.format(codec_name))
                    return False

        dest_spec = get_scaled_spec(source_spec)
        buf = shuffle_channels(buf, source_spec)
        buf = flatten(buf, source_spec)
        # buf = convert_color(buf, source_spec)
        buf = resize(buf, source_spec)

        if buf.nchannels > 3:
            background_buf = OpenImageIO.ImageBuf(dest_spec)
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
        # applications and the PNG library. The sRGB profile seems to be out of date
        # and pnglib crashes when encounters an invalid profile.
        # Removing the ICC profile seems to fix the issue. Annoying!
        _spec = OpenImageIO.ImageSpec()
        _spec.from_xml(spec.to_xml())  # this doesn't copy the extra attributes
        for i in spec.extra_attribs:
            if i.name.lower() == u'iccprofile':
                continue
            try:
                _spec[i.name] = i.value
            except:
                common.Log.error(u'Error saving iccprofile. Continuing.')
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

        if not QtCore.QFileInfo(QtCore.QFileInfo(dest).path()).isWritable():
            common.Log.error(u'Destination path is not writable')
            return

        success = _buf.write(dest, dtype=OpenImageIO.UINT8)
        if not success:
            common.Log.error(buf.geterror())
            common.Log.error(OpenImageIO.geterror())
            QtCore.QFile(dest).remove()
            return False
        return True


class Viewer(QtWidgets.QGraphicsView):
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

        font = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())
        metrics = QtGui.QFontMetrics(font)
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
            metrics = QtGui.QFontMetrics(
                common.font_db.secondary_font(common.SMALL_FONT_SIZE()))

            path = index.data(QtCore.Qt.StatusTipRole)
            path = common.get_sequence_endpath(path)
            img = OpenImageIO.ImageBuf(path)
            image_info = img.spec().serialize().split('\n')
            image_info = [f.strip() for f in image_info if f]
            for n, text in enumerate(image_info):
                if n > 2:
                    break
                common.draw_aliased_text(painter, common.font_db.secondary_font(common.SMALL_FONT_SIZE()), QtCore.QRect(
                    rect), text, QtCore.Qt.AlignLeft, common.SECONDARY_TEXT)
                rect.moveTop(rect.center().y() + int(metrics.lineSpacing()))
        painter.end()

    def set_image(self, path):
        image = oiio_get_qimage(path)
        if not image:
            return None

        if image.isNull():
            return None

        pixmap = QtGui.QPixmap.fromImage(image)
        if pixmap.isNull():
            common.Log.error('Could not convert QImage to QPixmap')
            return None

        self.item.setPixmap(pixmap)
        self.item.setShapeMode(QtWidgets.QGraphicsPixmapItem.MaskShape)
        self.item.setTransformationMode(QtCore.Qt.SmoothTransformation)

        size = self.item.pixmap().size()
        if size.height() > self.height() or size.width() > self.width():
            self.fitInView(self.item, QtCore.Qt.KeepAspectRatio)
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


class ImageViewer(QtWidgets.QWidget):
    def __init__(self, path, parent=None):
        super(ImageViewer, self).__init__(parent=parent)

        if not isinstance(path, unicode):
            raise ValueError(
                u'Expected <type \'unicode\'>, got {}'.format(type(path)))

        import bookmarks.common_ui as common_ui

        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            s = '{} does not exists.'.format(path)
            common_ui.ErrorBox(
                u'Error previewing image.', s).exec_()
            common.Log.error(s)
            self.deleteLater()
            raise RuntimeError(s)

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
        pen.setWidthF(common.ROW_SEPARATOR())
        painter.setPen(pen)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(20, 20, 20, 240))
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


# if __name__ == '__main__':
    # import bookmarks.standalone as standlone
    # app = standlone.StandaloneApp([])
    # w = ImageViewer(
    #     ur'c:\temp\example_job_a\shots\sh0010\renders\subfolder\logo_full_bleed.png')
    # w.exec_()
