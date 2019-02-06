# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903, C0330

"""Custom saver widget.

Note:
    The widget itself will only return a filepath and is not performing any save
    operations.

    When the selection is made by the user the ``SaverWidget.fileSaveRequested``
    signal is emitted with the output path.

"""


import re
import functools
from PySide2 import QtCore, QtWidgets, QtGui

import browser.common as common

from browser.delegate import BaseDelegate
from browser.delegate import paintmethod
from browser.editors import ClickableLabel
from browser.settings import Active

from browser.bookmarkswidget import BookmarksModel
from browser.assetwidget import AssetModel
from browser.browserwidget import HeaderWidget, CloseButton, MinimizeButton

from browser.settings import MarkedAsActive, MarkedAsArchived


class ThumbnailButton(ClickableLabel):
    """Button used to select the thumbnail for this item."""

    def __init__(self, parent=None):
        super(ThumbnailButton, self).__init__(parent=parent)
        self.setFixedSize(QtCore.QSize(common.ROW_HEIGHT + (common.INDICATOR_WIDTH * 2),
                                       common.ROW_HEIGHT + (common.INDICATOR_WIDTH * 2)))
        self.setAlignment(QtCore.Qt.AlignCenter)
        pixmap = common.get_rsc_pixmap(
            u'pick_thumbnail', common.FAVOURITE, common.ROW_HEIGHT)
        self.setPixmap(pixmap)


class VersionIndicator(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(VersionIndicator, self).__init__(parent=parent)
        self.setFixedHeight(common.ROW_HEIGHT)
        self.setFixedWidth(common.ROW_HEIGHT)

    def get_current_version(self):
        """Retrun the current file's version."""
        # Starts a new sequence when there's no current file given.
        if not self.window().currentfile:
            return u'001'

        # Check if it's a sequence
        match = common.get_sequence(self.window().currentfile)
        return u'001' if not match else match.group(2)

    def paintEvent(self, event):
        rect = QtCore.QRect(self.rect())
        painter = QtGui.QPainter()
        painter.begin(self)
        font = QtGui.QFont(u'Roboto Black')
        font.setPointSize(12)
        painter.setFont(font)
        painter.setPen(common.TEXT)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawText(rect, QtCore.Qt.AlignCenter,
                         self.get_current_version())
        painter.end()


class BaseCombobox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(BaseCombobox, self).__init__(parent=parent)
        self.setFixedHeight(common.ROW_HEIGHT / 2.0)
        self.setFixedWidth(100)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
        )

    def showPopup(self):
        """Moves the popup to a custom position and sets the height."""
        self.view().parent().setFrameShape(QtWidgets.QFrame.NoFrame)
        parent = self.window()
        right = parent.rect().topRight()
        right = parent.mapToGlobal(right)
        left = parent.rect().topLeft()
        left = parent.mapToGlobal(left)
        bottom = parent.rect().bottomLeft()
        bottom = parent.mapToGlobal(bottom)

        self.view().setFixedWidth(right.x() - left.x() - common.MARGIN)
        self.view().window().move(left.x() + (common.MARGIN / 2.0),
                                  bottom.y() - (common.MARGIN / 2.0) - 4)

        height = 0
        rows = self.model().rowCount(parent=self.rootModelIndex())
        sizehint = self.itemDelegate().sizeHint(None, QtCore.QModelIndex()).height()

        if not rows:
            mbox = QtWidgets.QMessageBox(parent=self)
            mbox.setText(
                u'No bookmarks or assets to work with...yet!')
            mbox.setInformativeText(u'You have to add at least one valid Bookmark before using this saver. See the Browser\'s bookmark tab for more info.')
            mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            mbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
            mbox.setWindowTitle('Oops')
            return mbox.exec_()

        for n in xrange(rows):
            height += sizehint
            if isinstance(self.view(), QtWidgets.QTreeView):
                height = sizehint * 8
                break
            if n > 8:
                break

        self.view().setFixedHeight(height)
        self.view().window().setFixedHeight(height)

        self.view().window().show()


class FoldersIconProvider(QtWidgets.QFileIconProvider):
    def __init__(self, parent=None):
        super(FoldersIconProvider, self).__init__(parent=parent)
        self.FolderIcon = common.get_rsc_pixmap(
            'folder', common.TEXT, common.ROW_BUTTONS_HEIGHT)

    def icon(self, type):
        return QtGui.QIcon(self.FolderIcon)


class FoldersModelDelegate(BaseDelegate):
    def __init__(self, parent=None):
        super(FoldersModelDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        """Defines how the BookmarksWidgetItems should be painted."""
        args = self._get_paint_args(painter, option, index)
        self.paint_background(*args)
        self.paint_thumbnail(*args)
        self.paint_name(*args)

    @paintmethod
    def paint_name(self, *args):
        """Paints the item names inside the ``AssetWidget``."""
        painter, option, index, _, _, active, _, _ = args

        rect = QtCore.QRect(option.rect)
        rect.setLeft(rect.left() + rect.height() + (common.MARGIN / 2.0))
        rect.setRight(rect.right() - common.MARGIN)

        font = QtGui.QFont('Roboto Black')
        font.setPointSize(9)
        painter.setFont(font)
        metrics = QtGui.QFontMetrics(font)

        # Resizing the height and centering
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - (rect.height() / 2.0))

        # Asset name
        text = index.data(QtCore.Qt.DisplayRole)
        text = re.sub(r'[^0-9a-zA-Z]+', ' ', text)
        text = re.sub(r'[_]{1,}', '_', text).strip('_')
        text = metrics.elidedText(
            text.upper(),
            QtCore.Qt.ElideRight,
            rect.width()
        )

        color = self.get_state_color(option, index, common.TEXT)

        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(QtGui.QPen(color))
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            text
        )

    @paintmethod
    def paint_thumbnail(self, *args):
        """Paints the thumbnail of the ``BookmarkWidget`` item."""
        painter, option, index, _, _, active, _, _ = args

        rect = QtCore.QRect(option.rect)
        rect.setLeft(option.rect.left())
        rect.setTop(rect.top() + 1)
        rect.setBottom(rect.bottom() - 1)
        rect.setRight(option.rect.left() + rect.height())

        pixmap = index.data(QtCore.Qt.DecorationRole).pixmap(
            option.rect.height(),
            option.rect.height(),
            QtGui.QIcon.Normal
        )

        center = rect.center()
        rect.setWidth(rect.width() / 2.0)
        rect.setHeight(rect.height() / 2.0)
        rect.moveCenter(center)

        painter.drawPixmap(
            rect,
            pixmap,
            pixmap.rect()
        )

    @paintmethod
    def paint_background(self, *args):
        """Paints the background."""
        painter, option, index, _, _, _, _, _ = args
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        active = self.parent().model().filePath(index) == self.parent().model().active_path

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        color = QtGui.QColor(common.BACKGROUND)
        if hover:
            color = QtGui.QColor(common.BACKGROUND_SELECTED)
        if active:
            color = QtGui.QColor(49, 107, 218)

        rect = QtCore.QRect(option.rect)
        rect.setTop(rect.top() + 1)
        rect.setBottom(rect.bottom() - 1)
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(rect)

        rect = QtCore.QRect(option.rect)
        rect.setTop(rect.top() + 1)
        rect.setBottom(rect.bottom() - 1)
        rect.setWidth(option.rect.height() - 1)

        color.setHsl(
            color.hue(),
            color.saturation(),
            color.lightness() - 10
        )
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(rect)

    def sizeHint(self, index, parent=QtCore.QModelIndex()):
        return QtCore.QSize(common.WIDTH, common.ROW_BUTTONS_HEIGHT)


class FoldersModel(QtWidgets.QFileSystemModel):
    activeFolderChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super(FoldersModel, self).__init__(parent=parent)
        self.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
        self.setIconProvider(FoldersIconProvider(parent=self))
        self.active_path = None

    def columnCount(self, index, parent=QtCore.QModelIndex()):
        return 1


class FoldersView(QtWidgets.QTreeView):
    def __init__(self, parent=None):
        super(FoldersView, self).__init__(parent=parent)
        self.setHeaderHidden(True)
        self.setItemDelegate(FoldersModelDelegate(parent=self))
        self.setAnimated(True)

class FoldersWidget(BaseCombobox):
    def __init__(self, parent=None):
        super(FoldersWidget, self).__init__(parent=parent)
        view = FoldersView(parent=self)
        self.setView(view)
        self.setModel(FoldersModel(parent=self))
        self.activated.connect(self.activate_current_index)

    def select_index(self, index):
        """Selects and activates the given index."""
        parent = self.rootModelIndex()
        self.setRootModelIndex(index.parent())
        self.setCurrentIndex(index.row())
        self.view().expand(index)
        self.view().selectionModel().setCurrentIndex(index, QtCore.QItemSelectionModel.ClearAndSelect)
        self.activate_current_index()
        self.setRootModelIndex(parent)

    def active_index(self):
        if not self.model().active_path:
            return QtCore.QModelIndex()
        return self.model().index(self.model().active_path)

    def activate_current_index(self, *args):
        """Sets the current index as ``active``."""
        index = self.view().selectionModel().currentIndex()
        if not index.isValid():
            return
        self.model().active_path = self.model().filePath(index)
        self.model().activeFolderChanged.emit()

    def set_asset(self, asset):
        path = list(asset) + [self.window().location,]
        path = u'/'.join(path)

        # Sets the root to the location folder.
        self.model().setRootPath(path)
        index = self.model().index(path)
        self.setRootModelIndex(self.model().index(path))

        # When currentfile is set, we want to match a folder inside to root,
        # based on the
        self.select_index(index)
        if self.diff(asset):
            index = self.model().index('{}/{}'.format(path, self.diff(asset)))
            self.select_index(index)

    def diff(self, asset):
        path = u'/'.join(list(asset) + [self.window().location, ])
        currentfile = QtCore.QFileInfo(self.window().currentfile).path()
        if path in currentfile:
            return currentfile.replace(path, u'').strip(u'/')
        return None


class BookmarksWidget(BaseCombobox):
    """Combobox to view and select the destination bookmark."""

    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)

        self.setModel(BookmarksModel(parent=self))
        self.setItemDelegate(BookmarksListDelegate(parent=self))

        self.activated.connect(self.activate_current_index)

        # Selecting the active bookmark
        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0, parent=QtCore.QModelIndex())
            if index.flags() & MarkedAsActive:
                self.setCurrentIndex(n)
                self.view().scrollTo(index)
                break

    def active_index(self):
        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0, parent=QtCore.QModelIndex())
            if index.flags() & MarkedAsActive:
                return index
        return QtCore.QModelIndex()

    def activate_current_index(self, *args):
        """Sets the current index as ``active``."""
        index = self.view().selectionModel().currentIndex()
        if not index.isValid():
            return
        if index.flags() == QtCore.Qt.NoItemFlags:
            return
        if index.flags() & MarkedAsArchived:
            return
        # Removing flag from previous active
        if self.active_index().isValid():
            self.model().setData(
                self.active_index(),
                self.active_index().flags() & ~MarkedAsActive,
                role=common.FlagsRole)
        # Adding flag to current
        self.model().setData(
            index,
            index.flags() | MarkedAsActive,
            role=common.FlagsRole)

        self.model().activeBookmarkChanged.emit(index.data(common.ParentRole))


class BookmarksListDelegate(BaseDelegate):
    """The delegate used to paint the bookmark items."""

    def _get_root_text(self, index, rect, metrics):
        """Gets the text for drawing the root."""
        root = index.data(common.ParentRole)[2]
        count = index.data(common.FileDetailsRole)
        active = index.flags() & MarkedAsActive

        text = re.sub(r'[_]+', ' ', root.upper())
        text = u'{} ({})'.format(text, count) if count else text

        return metrics.elidedText(
            text,
            QtCore.Qt.ElideLeft,
            rect.width()
        )

    def paint(self, painter, option, index):
        """Defines how the BookmarksWidgetItems should be painted."""
        args = self._get_paint_args(painter, option, index)

        self.paint_background(*args)
        self.paint_archived(*args)
        self.paint_name(*args)
        self.paint_active_indicator(*args)

    @paintmethod
    def paint_background(self, *args):
        """Paints the background."""
        painter, option, _, selected, _, active, _, _ = args

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        if selected and not active:
            color = QtGui.QColor(common.BACKGROUND_SELECTED)
        elif not selected and not active:
            color = QtGui.QColor(common.BACKGROUND)
        elif selected and active:
            color = QtGui.QColor(49, 107, 218)
        elif not selected and active:
            color = QtGui.QColor(29, 87, 198)

        rect = QtCore.QRect(option.rect)
        rect.setTop(rect.top() + 1)
        rect.setBottom(rect.bottom() - 1)

        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(rect)

    @paintmethod
    def paint_name(self, *args):
        """Paints name of the ``bookmarkswidget``'s items."""
        painter, option, index, selected, _, _, _, _ = args

        active = index.flags() & MarkedAsActive
        count = index.data(common.FileDetailsRole)

        rect, font, metrics = self.get_text_area(
            option.rect, common.PRIMARY_FONT)
        rect.setLeft(option.rect.left() + common.MARGIN)
        painter.setFont(font)

        # Centering rect
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - (rect.height() / 2.0))

        # Job
        text = index.data(QtCore.Qt.DisplayRole)
        text = re.sub(r'[\W\d\_]+', '', text)
        text = u' {} '.format(text)
        width = metrics.width(text)
        rect.setWidth(width)

        offset = common.INDICATOR_WIDTH

        # Name background
        pen = QtGui.QPen(common.FAVOURITE)
        pen.setWidth(offset)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(common.FAVOURITE))
        painter.drawRoundedRect(rect, 2, 2)
        # Name
        painter.setPen(common.TEXT)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawText(
            rect,
            QtCore.Qt.AlignCenter,
            text
        )

        if count:
            color = QtGui.QColor(common.TEXT)
        else:
            color = QtGui.QColor(common.TEXT_DISABLED)
            if selected:
                color = QtGui.QColor(common.TEXT)
        if active:
            color = common.SELECTION

        rect.setLeft(rect.right() + common.MARGIN)
        rect.setRight(option.rect.right() - common.MARGIN)
        # Name
        text = self._get_root_text(index, rect, metrics)

        painter.setFont(font)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(color)
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            text
        )

    def sizeHint(self, option, index):
        return QtCore.QSize(common.WIDTH, common.ROW_BUTTONS_HEIGHT)


class AssetsWidget(BaseCombobox):
    def __init__(self, parent=None):
        super(AssetsWidget, self).__init__(parent=parent)
        active_paths = Active.get_active_paths()
        bookmark = (
            active_paths[u'server'],
            active_paths[u'job'],
            active_paths[u'root']
        )

        self.setModel(AssetModel(bookmark, parent=self))
        self.setItemDelegate(AssetWidgetDelegate(parent=self))

        self.activated.connect(self.activate_current_index)

        # Selecting the active bookmark
        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0, parent=QtCore.QModelIndex())
            if index.flags() & MarkedAsActive:
                self.setCurrentIndex(n)
                self.view().scrollTo(index)
                break

    def inline_icons_count(self):
        return 0

    def active_index(self):
        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0, parent=QtCore.QModelIndex())
            if index.flags() & MarkedAsActive:
                return index
        return QtCore.QModelIndex()

    def activate_current_index(self, *args):
        """Sets the current index as ``active``."""
        index = self.view().selectionModel().currentIndex()
        if not index.isValid():
            return
        if index.flags() == QtCore.Qt.NoItemFlags:
            return
        if index.flags() & MarkedAsArchived:
            return
        # Removing flag from previous active
        if self.active_index().isValid():
            self.model().setData(
                self.active_index(),
                self.active_index().flags() & ~MarkedAsActive,
                role=common.FlagsRole)
        # Adding flag to current
        self.model().setData(
            index,
            index.flags() | MarkedAsActive,
            role=common.FlagsRole)

        self.model().activeAssetChanged.emit(index.data(common.ParentRole))


class AssetWidgetDelegate(BaseDelegate):
    """Delegate used by the ``AssetWidget`` to display the collecteds assets."""

    def paint(self, painter, option, index):
        """Defines how the ``AssetWidget``'s' items should be painted."""
        args = self._get_paint_args(painter, option, index)

        self.paint_background(*args)
        #
        self.paint_thumbnail(*args)
        self.paint_archived(*args)
        #
        self.paint_name(*args)
        self.paint_description(*args)
        #
        # self.paint_selection_indicator(*args)
        self.paint_active_indicator(*args)

    @paintmethod
    def paint_name(self, *args):
        """Paints the item names inside the ``AssetWidget``."""
        painter, option, index, _, _, active, _, _ = args

        rect, font, metrics = self.get_text_area(
            option.rect, common.PRIMARY_FONT)

        # Resizing the height and centering
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - (rect.height() / 2.0))

        # Asset name
        text = index.data(QtCore.Qt.DisplayRole)
        text = re.sub(r'[^0-9a-zA-Z]+', ' ', text)
        text = re.sub(r'[_]{1,}', '_', text)
        text = metrics.elidedText(
            text.upper(),
            QtCore.Qt.ElideRight,
            rect.width()
        )

        color = self.get_state_color(option, index, common.TEXT)

        painter.setFont(font)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(QtGui.QPen(color))
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            text
        )

    def sizeHint(self, option, index):
        return QtCore.QSize(common.WIDTH, common.ASSET_ROW_HEIGHT)


class Saver(QtWidgets.QWidget):
    """Our custom file-saver to be used in the context."""

    def __init__(self, parent=None):
        super(Saver, self).__init__(parent=parent)
        self._createUI()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(
            common.MARGIN, common.MARGIN, common.MARGIN, common.MARGIN)
        self.layout().setSpacing(2)

        self.setFixedHeight(common.ROW_HEIGHT * 2)
        self.setFixedWidth(common.WIDTH)

        common.set_custom_stylesheet(self)

        label = ThumbnailButton(parent=self)
        label.setStyleSheet(
            u'background-color: rgba({});'.format(u'{}/{}/{}/{}'.format(*common.BACKGROUND.getRgb())))
        self.layout().addWidget(label)

        self.layout().addWidget(BookmarksWidget(parent=self))
        self.layout().addWidget(AssetsWidget(parent=self))
        self.layout().addWidget(FoldersWidget(parent=self))

        editor = QtWidgets.QLineEdit()
        editor.setPlaceholderText(u'Description...')
        editor.setStyleSheet("""
            QLineEdit {{background-color: rgba({});}}
        """.format(u'{}/{}/{}/{}'.format(*common.SECONDARY_BACKGROUND.getRgb())))

        self.layout().addWidget(editor)
        self.layout().addStretch(1)
        self.layout().addWidget(VersionIndicator(parent=self))

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        rect = self.rect()
        painter.setPen(QtCore.Qt.NoPen)

        painter.setBrush(common.SEPARATOR)
        painter.drawRect(rect)

        center = rect.center()
        rect.setWidth(rect.width() - (common.MARGIN))
        rect.setHeight(rect.height() - (common.MARGIN))
        rect.moveCenter(center)

        painter.setBrush(common.BACKGROUND)
        painter.drawRoundedRect(rect, 4, 4)
        painter.end()


class SaverHeaderWidget(HeaderWidget):
    def __init__(self, parent=None):
        super(SaverHeaderWidget, self).__init__(parent=parent)
        self.label.setTextFormat(QtCore.Qt.RichText)
        self.label.setOpenExternalLinks(False)
        self.label.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        # self.setFocusPolicy(QtCore.Qt.NoFocus)
        # self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
    def update_header_text(self, *args, **kwargs):
        """Slot to update the header."""
        paths = self.window().active_path()
        text = '{jobroot} | {asset} | {location} | {folder}'.format(
            jobroot='{} | {}'.format(paths['job'], paths['root']).upper() if paths['root'] else '<span style="color:rgba({});">bookmark not set</span>'.format('{},{},{},{}').format(*common.FAVOURITE.getRgb()),
            asset=paths['asset'].upper() if paths['asset'] else '<span style="color:rgba({});">asset not set</span>'.format('{},{},{},{}').format(*common.FAVOURITE.getRgb()),
            location=paths['location'].upper(),
            folder=paths['folder'].upper() if paths['folder'] else '<span style="color:rgba({});">folder not set</span>'.format('{},{},{},{}').format(*common.FAVOURITE.getRgb())
        )
        self.label.setText(text)


class SaverWidget(QtWidgets.QDialog):
    """Contains the header and the saver widgets."""

    fileSaveRequested = QtCore.Signal(basestring)

    def __init__(self, location, currentfile=None, parent=None):
        super(SaverWidget, self).__init__(parent=parent)
        self.currentfile = currentfile
        self.location = location

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint
        )

        self._createUI()
        self._init_states()
        self._connectSignals()

    def select_thumbnail(self):
        """Prompts to select an image file.

        """
        active_paths = Active.get_active_paths()
        bookmark = (
            active_paths[u'server'],
            active_paths[u'job'],
            active_paths[u'root']
        )
        dialog = QtWidgets.QFileDialog(parent=self)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilter(u'Image files (*.png *.jpg  *.jpeg)')
        dialog.setDirectory(u'/'.join(bookmark))
        dialog.setOption(
            QtWidgets.QFileDialog.DontUseCustomDirectoryIcons, True)

        if not dialog.exec_():
            return
        if not dialog.selectedFiles():
            return

    def active_path(self):
        """The new file's path."""
        bookmarkswidget = self.findChild(BookmarksWidget)
        assetswidget = self.findChild(AssetsWidget)
        folderswidget = self.findChild(FoldersWidget)

        path = {
            'server': None,
            'job': None,
            'root': None,
            'asset': None,
            'location': self.location, # We have initialized the saver with this
            'folder': None,
            'filename': None
        }

        if not bookmarkswidget.active_index().isValid():
            return path

        server, job, root = bookmarkswidget.active_index().data(common.ParentRole)
        path['server'] = server
        path['job'] = job
        path['root'] = root

        if not assetswidget.active_index().isValid():
            return path

        _, _, _, asset = assetswidget.active_index().data(common.ParentRole)
        path['asset'] = asset

        if not folderswidget.active_index().isValid():
            return path

        index = folderswidget.rootModelIndex()
        # If the location is the same as the folder, we're not setting the folder
        if folderswidget.model().filePath(index) != folderswidget.model().active_path:
            path['folder'] = folderswidget.diff((
                path['server'],
                path['job'],
                path['root'],
                path['asset'],
            ))

        return path


    def _createUI(self):
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.layout().addWidget(Saver(parent=self))
        self.layout().insertWidget(0, SaverHeaderWidget(parent=self))

        minimizebutton = self.findChild(MinimizeButton)
        minimizebutton.setHidden(True)

    def _init_states(self):
        bookmarkswidget = self.findChild(BookmarksWidget)
        assetswidget = self.findChild(AssetsWidget)
        folderswidget = self.findChild(FoldersWidget)

        # Valid asset selection
        if assetswidget.active_index().isValid():
            asset = assetswidget.active_index().data(common.ParentRole)
            folderswidget.set_asset(asset)

            if self.window().currentfile: # Selecting the currentfile folder
                path = u'/'.join(list(asset) + [self.window().location, ])
                currentfile = QtCore.QFileInfo(self.window().currentfile).path()
                if path in currentfile:
                    index = folderswidget.model().index(currentfile)
                    folderswidget.select_index(index)
        else:
            index = folderswidget.model().index('.')
            folderswidget.select_index(index)
            folderswidget.setCurrentIndex(-1)

        headerwidget = self.findChild(SaverHeaderWidget)
        headerwidget.update_header_text()


    def _connectSignals(self):
        headerwidget = self.findChild(SaverHeaderWidget)
        closebutton = self.findChild(CloseButton)
        bookmarkswidget = self.findChild(BookmarksWidget)
        assetswidget = self.findChild(AssetsWidget)
        assetmodel = self.findChild(AssetModel)
        folderswidget = self.findChild(FoldersWidget)
        thumbnailbutton = self.findChild(ThumbnailButton)
        bookmarksmodel = self.findChild(BookmarksModel)
        assetsmodel = self.findChild(AssetModel)

        # Closes the dialog
        closebutton.clicked.connect(self.close)
        # Picks a thumbnail
        thumbnailbutton.clicked.connect(self.select_thumbnail)

        # Updates the assets model when the bookmark changes
        bookmarksmodel.activeBookmarkChanged.connect(assetsmodel.set_bookmark)
        assetmodel.activeAssetChanged.connect(folderswidget.set_asset)

        # Update signals for the header display
        bookmarkswidget.activated.connect(headerwidget.update_header_text)
        assetswidget.activated.connect(headerwidget.update_header_text)
        folderswidget.activated.connect(headerwidget.update_header_text)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])

    currentfile = u'//gordo/jobs/tkwwbk_8077/build2/asset_one/scenes/carlos/test/scene_001.ma'
    widget = SaverWidget(common.ScenesFolder, currentfile=None)

    widget.show()
    app.exec_()
