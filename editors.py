# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, W0613, R0201

"""Widgets used to edit data in the list widgets."""

import sys

from PySide2 import QtWidgets, QtGui, QtCore

from browser.capture import ScreenGrabber
import browser.common as common
from browser.settings import AssetSettings

import browser.modules # loads the numpy, oiio libraries
import oiio.OpenImageIO as oiio
from oiio.OpenImageIO import ImageBuf, ImageSpec, ImageBufAlgo


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
            QtCore.Qt.Dialog |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
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


class PickThumbnailDialog(QtWidgets.QFileDialog):
    """Editor widget used by the Asset- and FileWidget delegateself.

    The editor is responsible for associating a thumbnail image with
    an Asset- or FileWidget item via a file-browser prompt.

    """

    def __init__(self, index, parent=None):
        super(PickThumbnailDialog, self).__init__(parent=parent)
        settings = AssetSettings(index)
        # Opening dialog to select an image file
        self.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        self.setViewMode(QtWidgets.QFileDialog.List)
        self.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        self.setNameFilter(
            u'Image files (*.png *.jpg  *.jpeg *.tif *.tiff *.dpx *.exr *.psd *.gif *.tga)')
        self.setDirectory(QtCore.QDir(
            index.data(QtCore.Qt.StatusTipRole)))
        self.setOption(
            QtWidgets.QFileDialog.DontUseCustomDirectoryIcons, True)

        if not self.exec_():
            return
        if not self.selectedFiles():
            return

        # Saving the thumbnail
        generate_thumbnail(
            next(f for f in self.selectedFiles()),
            AssetSettings(index).thumbnail_path()
        )
        settings = AssetSettings(index)
        height = self.parent().visualRect(index).height() - 2
        common.cache_image(settings.thumbnail_path(), height, overwrite=True)


class ThumbnailEditor(QtCore.QObject):
    """Utility class for setting, capturing and editing thumbnail."""

    # Signals
    thumbnailChanged = QtCore.Signal(QtCore.QModelIndex)

    def generate(self, index, overwrite=True):
        """OpenImageIO based method to generate sRGB thumbnails bound by ``THUMBNAIL_IMAGE_SIZE``."""
        if not index.isValid():
            return

        source = index.data(QtCore.Qt.StatusTipRole)
        dest = AssetSettings(index).thumbnail_path()
        if not overwrite and QtCore.QFileInfo(dest).exists():
            return # skipping the existing thumbnails

        img = ImageBuf(source)

        if img.has_error:
            sys.stderr.write('# OpenImageIO: Skipped reading {}\n{}\n'.format(source, img.geterror()))
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
            QtCore.QFile(dest).remove() # removing failed thumbnail save
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
        image = common.resize_image(image, common.THUMBNAIL_IMAGE_SIZE)
        if image.isNull():
            return

        if not image.save(settings.thumbnail_path()):
            sys.stderr.write('# Capture thumnail error: Error saving {}.\n'.format(settings.thumbnail_path()))
        else:
            self.thumbnailChanged.emit(index)

    def remove(self, index):
        """Deletes the given thumbnail."""
        if not index.isValid():
            return
        settings = AssetSettings(index)
        self._reset_cached(settings.thumbnail_path(), removefile=True)
        self.thumbnailChanged.emit(index)

    @classmethod
    def _reset_cache(cls, cache_key_element, removefile=True):
        """Resets any cached items containing `k` with the original placeholder image.

        Args:
            cache_key_element (str): Normally, the path to the cached item.

        """
        file_ = QtCore.QFile(cache_key_element)

        if file_.exists() and removefile:
            file_.remove()

        keys = [key for key in common.IMAGE_CACHE if k.lower() in key.lower()]
        for key in keys:
            if ':' in cache_key_element:
                path, label = key.split(':')
                if 'BackgroundColor' in label:
                    common.IMAGE_CACHE[key] = QtGui.QColor(0, 0, 0, 0) # transparent bg
                else:
                    cls._assign_placeholder(path, int(label))

    @staticmethod
    def cache_image(path, height, overwrite=False):
        """Saves the image at the path to the image cache at the given sized.
        The cached images are stored in the IMAGE_CACHE dictionary.

        Returns the cached image if it already is in the cache or the placholder
        image if the loading of the image fails. In addittion, each cached entry
        will be associated with an average background color that can be used
        to paint a unique background.

        Args:
            path (str):    Path to the image file.
            height (int):  Description of parameter `height`.

        Returns:
            QImage: The cached, and resized QImage

        """
        height = int(height)
        file_info = QtCore.QFileInfo(path)

        k = u'{path}:{height}'.format(
            path=file_info.filePath(),
            height=height
        )

        # Return cached item if exsits
        if k in common.IMAGE_CACHE and not overwrite:
            return common.IMAGE_CACHE[k]

        # If the file doesn't exist, return a placeholder
        if not file_info.exists():
            return cache_placeholder(path, k, height)

        image = QtGui.QImage()
        image.load(file_info.filePath())
        if image.isNull():
            return cache_placeholder(path, k, height)

        image = image.convertToFormat(QtGui.QImage.Format_ARGB32_Premultiplied)
        image = resize_image(image, height)

        # Saving the background color
        common.IMAGE_CACHE[u'{k}:BackgroundColor'.format(
            k=path
        )] = get_color_average(image)
        common.IMAGE_CACHE[k] = image

        return common.IMAGE_CACHE[k]

    @staticmethod
    def _assign_placeholder(path, height):
        """If a thumbnail doesn't exist, we will use a placeholder image to
        represent it.

        The placeholder image will be cached per size and associated with each key
        that doesn't have a valid thumbnail image saved.

        """
        file_info = QtCore.QFileInfo(u'{}/../rsc/placeholder.png'.format(__file__))
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
        if pk in common.IMAGE_CACHE:
            common.IMAGE_CACHE[k] = common.IMAGE_CACHE[pk]
            common.IMAGE_CACHE[bgpk] = QtGui.QColor(0,0,0,0)
            return common.IMAGE_CACHE[k]

        if not file_info.exists():
            sys.stderr.write('# Could not find the placeholder image. Using null.\n')
            return QtCore.QImage(height, height)

        # Loading a and resizing a copy of the placeholder
        image = QtGui.QImage()
        image.load(file_info.filePath())

        if image.isNull():
            sys.stderr.write('# Could not load the placeholder image. Using null.\n')
            return QtCore.QImage(height, height)

        image = image.convertToFormat(QtGui.QImage.Format_ARGB32_Premultiplied)
        image = common.resize_image(image, height)

        common.IMAGE_CACHE[k] = image
        common.IMAGE_CACHE[bgk] = QtGui.QColor(0,0,0,0)
        common.IMAGE_CACHE[pk] = image
        common.IMAGE_CACHE[bgpk] = QtGui.QColor(0,0,0,0)

        return common.IMAGE_CACHE[k]


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
        rect.setLeft(rect.left() + common.INDICATOR_WIDTH +
                     (rect.height() - 2))
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
        self.setWindowFlags(QtCore.Qt.Window |
                            QtCore.Qt.FramelessWindowHint)

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
        pixmap = common.get_rsc_pixmap(
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


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = FilterEditor('/')
    widget.show()
    app.exec_()
