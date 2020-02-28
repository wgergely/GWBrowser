# -*- coding: utf-8 -*-
"""The ``imagecache.py`` module defines most image-operation related classes and
methods including the global image cache.

Thumbnails
    We're relying on ``OpenImageIO`` to generate image and movie thumbnails.
    Thumbnail operations are multi-threaded and are mostly associated with
    the *FilesModel* (we only generate thumbnails from file OpenImageIO
    understands.

    To generate a thumbnail use ``ImageCache.oiio_make_thumbnail()``.

All generated thumbnails and ui resources are cached in ``ImageCache``.

"""

import os
import functools
import tempfile

from PySide2 import QtWidgets, QtGui, QtCore

import OpenImageIO
import gwbrowser.common as common


oiio_cache = OpenImageIO.ImageCache(shared=True)
oiio_cache.attribute('max_memory_MB', 2048.0)
oiio_cache.attribute('max_open_files', 0)
oiio_cache.attribute('trust_file_extensions', 1)



def verify_index(func):
    """Decorator to create a menu set."""
    @functools.wraps(func)
    def func_wrapper(cls, index, **kwargs):
        """Wrapper for function."""
        if not index.isValid():
            return
        if not index.data(common.FileInfoLoaded):
            return
        if hasattr(index.model(), 'sourceModel'):
            index = index.model().mapToSource(index)

        return func(cls, index, **kwargs)
    return func_wrapper



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
        workspace_rect = QtCore.QRect()
        for screen in app.screens():
            workspace_rect = workspace_rect.united(screen.availableGeometry())
        self.setGeometry(workspace_rect)

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
        to self.pixmap()

        """
        if common.get_platform() == u'mac':
            # On macosx we're using the built-in capture-tool because the
            # os doesn't allow capturing pixels from outside the application.
            temppath = tempfile.NamedTemporaryFile(
                suffix=u'.'.format(common.THUMBNAIL_FORMAT),
                prefix=u'screencapture_',
                delete=False
            ).name
            res = os.system(u'screencapture -m -i -s {}'.format(temppath))
            if res == 0:
                self._pixmap = QtGui.QPixmap(temppath)
        else:
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

        pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 64), 1, QtCore.Qt.DotLine)
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
        if event.button() == QtCore.Qt.LeftButton:
            self._click_pos = event.globalPos()
        if event.button() == QtCore.Qt.RightButton:
            self.reject()

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
            index.data(QtCore.Qt.SizeHintRole).height() - common.ROW_SEPARATOR,
            overwrite=True
        )
        color = cls.get(
            thumbnail_path,
            u'backgroundcolor',
            overwrite=False
        )

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

        if not QtCore.QFileInfo(QtCore.QFileInfo(thumbnail_path).path()).isWritable():
            common.Log.error('Destination path is not writable.')
            return

        cls.oiio_make_thumbnail(
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
    def oiio_make_thumbnail(cls, source, dest, dest_size, nthreads=4):
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
                    (source_spec.channelnames[0], source_spec.channelnames[0], source_spec.channelnames[0]),
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
                    buf = OpenImageIO.ImageBufAlgo.colorconvert(buf, colorspace, 'sRGB')
            except:
                common.Log.error('Could not conver tthe color profile')
            return buf


        i = OpenImageIO.ImageInput.open(source)
        if not i:
            common.Log.error(OpenImageIO.geterror())
            return False

        try:
            buf = OpenImageIO.ImageBuf()
            o_spec = i.spec_dimensions(0, miplevel=0)
            buf.reset(source, 0, 0, o_spec)
        except:
            common.Log.error(buf.geterror())
            return False
        finally:
            i.close()

        if buf.has_error:
            common.Log.error(buf.geterror())
            return

        source_spec = buf.spec()
        ext = source.split(u'.').pop().lower()
        accepted_codecs = (u'h.264', u'mpeg-4')
        codec_name = source_spec.get_string_attribute(u'ffmpeg:codec_name')

        if ext in (u'tif', u'tiff', 'gif') and source_spec.format == 'uint16':
            return False

        if source_spec.get_int_attribute(u'oiio:Movie') == 1:
            # [BUG] Not all codec formats are supported by ffmpeg. There does
            # not seem to be (?) error handling and an unsupported codec will
            # crash ffmpeg and the rest of the app.
            for codec in accepted_codecs:
                if codec.lower() not in codec_name.lower():
                    common.Log.error('Unsupported movie format: {}'.format(codec_name))
                    return False


        dest_spec = get_scaled_spec(source_spec)
        buf = shuffle_channels(buf, source_spec)
        buf = flatten(buf, source_spec)
        buf = convert_color(buf, source_spec)
        buf = resize(buf, source_spec)

        if buf.nchannels > 3:
            background_buf = OpenImageIO.ImageBuf(dest_spec)
            OpenImageIO.ImageBufAlgo.checker(
                background_buf,
                12,12,1,
                (0.3,0.3,0.3),
                (0.2,0.2,0.2)
            )
            buf = OpenImageIO.ImageBufAlgo.over(buf, background_buf)

        spec = buf.spec()
        buf.set_write_format(OpenImageIO.UINT8)

        # There seems to be a problem with the ICC profile exported from Adobe
        # applications and the PNG library. The sRGB profile seems to be out of date
        # and pnglib crashes when encounters an invalid profile.
        # Removing the ICC profile seems to fix the issue. Annoying!
        if spec.getattribute('ICCProfile'):
            spec['ICCProfile'] = None
        # On some dpx images I'm getting "GammaCorrectedinf"
        if spec.get_string_attribute(u'oiio:ColorSpace') == u'GammaCorrectedinf':
            spec['oiio:ColorSpace'] = 'sRGB'
            spec['oiio:Gamma'] = u'0.454545'

        # Initiating a new spec with the modified xml
        _buf = OpenImageIO.ImageBuf(spec)
        _buf.copy_pixels(buf)
        _buf.set_write_format(OpenImageIO.UINT8)

        if not QtCore.QFileInfo(QtCore.QFileInfo(dest).path()).isWritable():
            common.Log.error(u'Destination path is not writable')
            return

        success = buf.write(dest, dtype=OpenImageIO.UINT8)
        if not success:
            common.Log.error(buf.geterror())
            common.Log.error(OpenImageIO.geterror())
            QtCore.QFile(dest).remove()
            return False
        return True
