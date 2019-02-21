# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, W0613, R0201

"""Widgets used to edit data in the list widgets."""

import sys
import functools

from PySide2 import QtWidgets, QtGui, QtCore

from browser.capture import ScreenGrabber
import browser.common as common
from browser.settings import AssetSettings

import browser.modules  # loads the numpy, oiio libraries
import oiio.OpenImageIO as oiio
from oiio.OpenImageIO import ImageBuf, ImageSpec, ImageBufAlgo
from browser.spinner import longprocess


class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super(ClickableLabel, self).__init__(parent=parent)
        self.setFixedSize(QtCore.QSize(
            common.ROW_BUTTONS_HEIGHT, common.ROW_BUTTONS_HEIGHT))
        self.setAlignment(QtCore.Qt.AlignCenter)

    def mouseReleaseEvent(self, event):
        """Only triggered when the left buttons is pressed."""
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()


class ThumbnailViewer(QtWidgets.QLabel):
    """Widget used to view a thumbnail."""

    def __init__(self, index, parent=None):
        super(ThumbnailViewer, self).__init__(parent=parent)
        self.setWindowFlags(
            QtCore.Qt.Dialog
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.setAlignment(QtCore.Qt.AlignCenter)

        # self.setFocusProxy(self.parent())
        self.reset_pixmap()
        self.show()

    def reset_pixmap(self):
        self.setStyleSheet(
            u'QLabel {background-color: rgba(50,50,50,50); color:rgba(200,200,200,255);}')
        index = self.parent().selectionModel().currentIndex()
        settings = AssetSettings(index)
        file_info = QtCore.QFileInfo(settings.thumbnail_path())

        if not index.isValid():
            self.clear()
            self.setText('Invalid selection.')
            return

        if not file_info.exists():
            self.clear()
            self.setText('No thumbnail found.')
            return

        pixmap = QtGui.QPixmap(settings.thumbnail_path())
        if pixmap.isNull():
            self.clear()
            self.setText('Unable to load pixmap.')
            return

        self.clear()
        self.setPixmap(pixmap)

    def paintEvent(self, event):
        """Custom paint event"""
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        painter.setBrush(QtGui.QColor(0, 0, 0, 170))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(self.rect())

        # Let's paint extra information:
        index = self.parent().selectionModel().currentIndex()
        if index.isValid():
            font = QtGui.QFont(common.PrimaryFont)
            metrics = QtGui.QFontMetrics(font)
            if self.pixmap():
                rect = self.rect()
                center = rect.center()
                rect.setHeight(metrics.height())
                rect.setWidth(rect.width() - (common.MARGIN * 4))
                rect.moveCenter(center)

                # Aligned to the bottom of the pixmap
                rect.moveTop(
                    rect.top() + self.pixmap().rect().height() / 2.0 + common.MARGIN)
                # Filename
                common.draw_aliased_text(painter, font, rect, index.data(
                    QtCore.Qt.StatusTipRole), QtCore.Qt.AlignCenter, common.TEXT)
                rect.moveTop(rect.center().y() + metrics.height())

                common.draw_aliased_text(painter, font, rect, index.data(
                    common.DescriptionRole), QtCore.Qt.AlignCenter, common.FAVOURITE)

        painter.end()
        super(ThumbnailViewer, self).paintEvent(event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Down:
            self.parent().key_down()
            self.reset_pixmap()
        elif event.key() == QtCore.Qt.Key_Up:
            self.parent().key_up()
            self.reset_pixmap()
        else:
            self.close()

    def _fit_screen_geometry(self):
        # Compute the union of all screen geometries, and resize to fit.
        app = QtCore.QCoreApplication.instance()
        rect = app.desktop().availableGeometry(self.parent())
        self.setGeometry(rect)

    def showEvent(self, event):
        self.setFocus()
        self.parent()._thumbnailvieweropen = self
        self._fit_screen_geometry()

    def hideEvent(self, event):
        self.parent()._thumbnailvieweropen = None

    def mousePressEvent(self, event):
        self.close()

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.close()


class ImageCache(QtCore.QObject):
    """Utility class for setting, capturing and editing thumbnail and resource
    images.

    All cached images are stored in ``ImageCache.__data`` `(dict)` object.
    To add an image to the cache you can use the ``ImageCache.cache_image()`` method.
    Loading and caching ui resource items is done by ``ImageCache.get_rsc_pixmap()``.
    """
    # Main data-container
    __data = {}
    # Signals
    thumbnailChanged = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, parent=None):
        super(ImageCache, self).__init__(parent=parent)

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

    def _find_largest_file(self, index):
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
        """Generates all the thumbnails for the given list of indexes."""
        app = QtCore.QCoreApplication.instance()

        import browser.spinner as spinner
        parent = [f for f in app.allWidgets() if f.objectName()
                  == 'browserListStackWidget'][0]
        spinner = spinner.Spinner(parent=parent)
        spinner.setFixedWidth(parent.width())

        spinner.count = len(indexes)
        spinner.current = 0
        spinner.start()

        # Multi-threaded approach
        threads = []
        for _ in xrange(QtCore.QThread.idealThreadCount()):
            thread = QtCore.QThread()
            thread.start()
            threads.append(thread)

        for idx, index in enumerate(indexes):
            dest = AssetSettings(index).thumbnail_path()
            if not overwrite and QtCore.QFileInfo(dest).exists():
                continue

            func = functools.partial(self.generate, index)

            worker = Worker(spinner, func)
            worker.signals.progressUpdate.connect(spinner.setText)
            worker.signals.finished.connect(spinner.stop)

            worker.moveToThread(
                threads[idx % QtCore.QThread.idealThreadCount()])
            worker.run()

    def generate(self, index, source=None):
        """OpenImageIO based method to generate sRGB thumbnails bound by ``THUMBNAIL_IMAGE_SIZE``."""
        if not index.isValid():
            return

        # If it's a sequence, we will find the largest file in the sequence and
        # generate the thumbnail for that item
        path = index.data(QtCore.Qt.StatusTipRole)
        if not source:
            if common.is_collapsed(path):
                source = self._find_largest_file(index)

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
            self.thumbnailChanged.emit(index)

    def capture(self, index):
        """Captures a thumbnail for the current index item using ScreenGrabber."""
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
        """Deletes the given thumbnail."""
        if not index.isValid():
            return
        settings = AssetSettings(index)
        self._reset_cached_item(settings.thumbnail_path(), removefile=True)
        self.thumbnailChanged.emit(index)

    def pick(self, index):
        dialog = QtWidgets.QFileDialog()
        common.set_custom_stylesheet(dialog)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilters(common.get_oiio_namefilters())
        dialog.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dialog.setLabelText(QtWidgets.QFileDialog.Accept, 'Pick thumbnail')
        dialog.setDirectory(QtCore.QFileInfo(
            index.data(QtCore.Qt.StatusTipRole)).path())
        # dialog.setOption(
        #     QtWidgets.QFileDialog.DontUseCustomDirectoryIcons, True)

        if not dialog.exec_():
            return
        if not dialog.selectedFiles():
            return

        # Saving the thumbnail
        self.generate(index, source=dialog.selectedFiles()[0])

    def get_rsc_pixmap(self, name, color, size, opacity=1.0):
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

        if k in self.__data:
            return self.__data[k]

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

        image = self.resize_image(image, size)
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

        self.__data[k] = pixmap
        return self.__data[k]


class Signals(QtCore.QObject):
    """QRunnables can't define signals themselves so we're passing this
    dude to the worker. It defines a single finished signal.

    """
    progressUpdate = QtCore.Signal(basestring)
    start = QtCore.Signal()
    finished = QtCore.Signal()


class Worker(QtCore.QObject):
    """Generic QRunnable, taking an index as it's first argument."""

    def __init__(self, parent, func):
        super(Worker, self).__init__()
        # self.setAutoDelete(True)
        self.func = func
        self.parent = parent
        self.signals = Signals()

    def run(self):
        if self.parent.current == 0:
            self.signals.start.emit()
        text = '# Processing thumbnail {} of {}'.format(
            self.parent.current + 1, self.parent.count)
        self.signals.progressUpdate.emit(text)

        try:
            self.func()
        except Exception as err:
            sys.stderr.write(u'# Worker error:\n{}\n'.format(err))

        self.parent.current += 1
        sys.stdout.write(u'# Thumbnail generated.\n')
        self.signals.progressUpdate.emit(text)
        QtWidgets.QApplication.instance().processEvents(
            QtCore.QEventLoop.ExcludeUserInputEvents)

        if self.parent.current >= self.parent.count:
            self.signals.finished.emit()


class DescriptionEditorWidget(QtWidgets.QWidget):
    """Note editor baseclass."""

    def __init__(self, index, parent=None):
        super(DescriptionEditorWidget, self).__init__(parent=parent)
        self._index = index

        self.editor = None
        self.settings = AssetSettings(index)
        self._createUI()

        self.editor.focusOutEvent = self.focusOutEvent
        self.editor.installEventFilter(self)
        self.installEventFilter(self)

        self._connectSignals()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self.set_size(self.parent().viewport().size())
        self.setFocusProxy(self.editor)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.editor.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.show()
        self.editor.setFocus()

        self.editor.setText(self.settings.value(u'config/description'))
        self.editor.selectAll()

    def sizeHint(self):
        return QtCore.QSize(
            self.parent().visualRect(self._index).width(),
            self.parent().visualRect(self._index).height()
        )

    def set_size(self, size):
        """Sets the widget size."""
        rect = QtCore.QRect(self.parent().visualRect(self._index))
        rect.setLeft(rect.left() + common.INDICATOR_WIDTH
                     + (rect.height() - 2))
        self.move(rect.left(), rect.top())
        self.resize(size.width() - rect.left(), rect.height())

    def eventFilter(self, widget, event):
        """We're filtering the enter key event here, otherwise, the
        list widget would close open finishing editing.

        """
        if not event.type() == QtCore.QEvent.KeyPress:
            return False

        shift = event.modifiers() == QtCore.Qt.ShiftModifier

        escape = event.key() == QtCore.Qt.Key_Escape

        tab = event.key() == QtCore.Qt.Key_Tab
        backtab = event.key() == QtCore.Qt.Key_Backtab

        return_ = event.key() == QtCore.Qt.Key_Return
        enter = event.key() == QtCore.Qt.Key_Enter

        if escape:
            self.close()
            return True

        if enter or return_:
            self.action()
            self.close()
            return True

        if not shift and tab:
            self.action()
            self.parent().key_down()
            self.parent().key_tab()
            widget = DescriptionEditorWidget(
                self.parent().currentIndex(), parent=self.parent())
            widget.show()
            return True

        if (shift and tab) or backtab:
            self.action()
            self.parent().key_up()
            self.parent().key_tab()
            widget = DescriptionEditorWidget(
                self.parent().currentIndex(), parent=self.parent())
            widget.show()
            return True

        return False

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.close()

    def _connectSignals(self):
        """Connects signals."""
        self.editor.editingFinished.connect(self.action)
        self.parent().sizeChanged.connect(self.set_size)

    def _createUI(self):
        """Creates the layout."""
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(common.MARGIN * 1.5, 0, common.MARGIN * 0.5, 0)
        self.layout().setSpacing(6)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )

        self.editor = QtWidgets.QLineEdit()
        self.editor.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.editor.setTextMargins(0, 0, 0, 0)

        self.editor.setStyleSheet(
            'background-color: rgb(50,50,50);\
            font-family: "{}"; font-size: 8pt;\
            color: rgba({},{},{},{});'.format(
                common.SecondaryFont.family(),
                *common.TEXT_NOTE.getRgb()
            ))

        label = QtWidgets.QLabel(u'Edit description')
        label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        label.setStyleSheet(
            'font-family: "{}";\
            font-size: 8pt;\
            color: rgba({},{},{},{});'.format(
                common.PrimaryFont.family(),
                *common.TEXT.getRgb()
            ))

        self.layout().addStretch(1)
        self.layout().addWidget(label, 1)
        self.layout().addWidget(self.editor, 1)
        self.layout().addStretch(1)

    def paintEvent(self, event):
        """Custom paint used to paint the background."""
        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            rect = QtCore.QRect()
            rect.setWidth(self.width())
            rect.setHeight(self.height())

            pen = QtGui.QPen(common.SELECTION)
            pen.setWidth(2)
            painter.setPen(pen)
            color = QtGui.QColor(common.BACKGROUND_SELECTED)
            painter.setBrush(QtGui.QBrush(color))
            painter.drawRect(rect)
            painter.end()

            return
        super(DescriptionEditorWidget, self).paintEvent(event)

    def action(self):
        """Main actions to run when the return key is pressed."""
        if self.settings.value(u'config/description') == self.editor.text():
            self.close()
            return

        source_index = self.parent().model().mapToSource(self._index)
        self.parent().model().sourceModel().setData(
            source_index,
            self.editor.text(),
            role=common.DescriptionRole
        )
        self.settings.setValue(u'config/description', self.editor.text())
        self.close()


class FilterListButton(ClickableLabel):
    pass


class FilterEditor(QtWidgets.QWidget):
    """Editor widget used to set the filter for the current view."""
    finished = QtCore.Signal(basestring)

    def __init__(self, text, parent=None):
        super(FilterEditor, self).__init__(parent=parent)
        self.editor = None

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(QtCore.Qt.Window
                            | QtCore.Qt.FramelessWindowHint)

        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT)

        self._createUI()
        self._connectSignals()

        self.setFocusProxy(self.editor)

        if text == u'/':
            text = u''
        self.editor.setText(text)
        self.editor.selectAll()
        self.editor.focusOutEvent = self.focusOutEvent

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 4, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        self.setFixedWidth(300)
        self.label = FilterListButton()
        self.label.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
        self.label.setFixedWidth(common.ROW_BUTTONS_HEIGHT)
        pixmap = image_cache.get_rsc_pixmap(
            u'filter', common.FAVOURITE, common.ROW_BUTTONS_HEIGHT / 2.0)
        self.label.setPixmap(pixmap)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setFocusPolicy(QtCore.Qt.NoFocus)

        self.editor = QtWidgets.QLineEdit()
        self.editor.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.editor.setPlaceholderText('Find...')
        self.setStyleSheet("""
            QLineEdit {{
                margin: 0px;
                padding: 5px;
                background-color: rgba(30,30,30, 255);
                color: rgba(200,200,200,255);
                font-family: "{}";
                font-size: 11pt;
            	border-width: 0px;
            	border: none;
            	outline: 0;
                border-radius: 4px;
            }}
            QLineEdit:active {{
            	border: none;
            	outline: 0;
            }}
            QLineEdit:focus {{
            	border: none;
            	outline: 0;
            }}
        """.format(common.PrimaryFont.family()))
        self.layout().addWidget(self.label, 0)
        self.layout().addWidget(self.editor, 1)

    def _connectSignals(self):
        self.finished.connect(self.close)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.SEPARATOR)
        painter.drawRoundRect(self.rect(), 4, 4)
        painter.end()

    def keyPressEvent(self, event):
        return_ = event.key() == QtCore.Qt.Key_Return
        enter = event.key() == QtCore.Qt.Key_Enter
        escape = event.key() == QtCore.Qt.Key_Escape

        if escape:
            self.close()
        if return_ or enter:
            self.finished.emit(self.editor.text())

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.close()


# Initializing the ImageCache:
image_cache = ImageCache()

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = FilterEditor('/')
    widget.show()
    app.exec_()
