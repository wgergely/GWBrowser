# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903, C0330

"""Browser's custom saver widget.

Note:
    The widget itself will only return a filepath and is not performing any save
    operations.

    When the selection is made by the user the ``SaverWidget.fileSaveRequested``
    signal is emitted with the output path.

"""


import re
import functools
import collections
from PySide2 import QtCore, QtWidgets, QtGui

import browser.common as common

from browser.delegate import BaseDelegate
from browser.delegate import BookmarksWidgetDelegate
from browser.delegate import AssetWidgetDelegate
from browser.delegate import paintmethod
from browser.editors import ClickableLabel
from browser.settings import Active

from browser.bookmarkswidget import BookmarksModel
from browser.baselistwidget import BaseContextMenu
from browser.capture import ScreenGrabber
from browser.assetwidget import AssetModel
from browser.browserwidget import HeaderWidget, CloseButton, MinimizeButton

from browser.settings import MarkedAsActive, MarkedAsArchived


class ThumbnailMenu(BaseContextMenu):
    def __init__(self, parent=None):
        super(ThumbnailMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_thumbnail_menu()

    def add_thumbnail_menu(self):
        """Menu for thumbnail operations."""
        capture_thumbnail_pixmap = common.get_rsc_pixmap(
            u'capture_thumbnail', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        pick_thumbnail_pixmap = common.get_rsc_pixmap(
            u'pick_thumbnail', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        revomove_thumbnail_pixmap = common.get_rsc_pixmap(
            u'todo_remove', common.FAVOURITE, common.INLINE_ICON_SIZE)
        show_thumbnail = common.get_rsc_pixmap(
            u'active', common.FAVOURITE, common.INLINE_ICON_SIZE)

        menu_set = collections.OrderedDict()
        menu_set[u'separator'] = {}

        menu_set[u'Capture thumbnail'] = {
            u'icon': capture_thumbnail_pixmap,
            u'action': self.capture
        }
        menu_set[u'Pick thumbnail'] = {
            u'icon': pick_thumbnail_pixmap,
            u'action': self.parent().window().pick_thumbnail
        }
        self.create_menu(menu_set)

    def capture(self):
        path = ScreenGrabber.capture()
        image = common.cache_image(path, common.ASSET_ROW_HEIGHT)
        self.image = common.cache_image(path, common.THUMBNAIL_IMAGE_SIZE)
        pixmap = QtGui.QPixmap()
        pixmap.convertFromImage(image)
        self.parent().window().findChild(ThumbnailButton).setPixmap(pixmap)


class ThumbnailButton(ClickableLabel):
    """Button used to select the thumbnail for this item."""

    def __init__(self, parent=None):
        super(ThumbnailButton, self).__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignCenter)
        pixmap = common.get_rsc_pixmap(
            u'pick_thumbnail', common.FAVOURITE, common.ROW_HEIGHT)
        self.setPixmap(pixmap)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self.setStyleSheet(
            u'background-color: rgba({});'.format(u'{}/{}/{}/{}'.format(*common.BACKGROUND.getRgb())))

    def contextMenuEvent(self, event):
        menu = ThumbnailMenu(parent=self)
        pos = self.rect().center()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()


class BaseCombobox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(BaseCombobox, self).__init__(parent=parent)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def showPopup(self):
        """Moves the popup to a custom position and sets the height."""
        self.view().parent().setFrameShape(QtWidgets.QFrame.NoFrame)
        parent = self.window()
        right = self.window().rect().topRight()
        right = self.window().mapToGlobal(right)
        left = self.window().rect().topLeft()
        left = self.window().mapToGlobal(left)
        bottom = self.window().rect().bottomLeft()
        bottom = self.window().mapToGlobal(bottom)

        self.view().setFixedWidth(right.x() - left.x())
        self.view().window().move(left.x(), bottom.y())

        self.set_view_height()
        self.view().window().show()

    def set_view_height(self, *args, **kwargs):
        """Resizes the view to fit the visible rows."""
        def count_visible_rows(index, count=-1):
            count += 1
            below = self.view().indexBelow(index)
            if not below.isValid():
                return count
            return count_visible_rows(below, count=count)

        height = 0
        rows = self.model().rowCount(parent=self.rootModelIndex())
        rows = count_visible_rows(self.rootModelIndex()) if isinstance(
            self.view(), QtWidgets.QTreeView) else rows
        sizehint = self.itemDelegate().sizeHint(None, QtCore.QModelIndex()).height()

        if not rows:
            return  # no items

        for n in xrange(rows):
            height += sizehint
            if height > 600.0:
                height = int(600.0 / sizehint) * sizehint
                break

        self.view().setFixedHeight(height)
        self.view().window().setFixedHeight(height)


class FoldersIconProvider(QtWidgets.QFileIconProvider):
    def __init__(self, parent=None):
        super(FoldersIconProvider, self).__init__(parent=parent)
        self.FolderIcon = common.get_rsc_pixmap(
            'folder', common.TEXT, common.ROW_BUTTONS_HEIGHT)

    def icon(self, type):
        return QtGui.QIcon(self.FolderIcon)


class FoldersWidgetDelegate(BaseDelegate):
    def __init__(self, parent=None):
        super(FoldersWidgetDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        """Defines how the BookmarksWidgetItems should be painted."""
        args = self._get_paint_args(painter, option, index)
        self.paint_background(*args)
        self.paint_name(*args)

    @paintmethod
    def paint_name(self, *args):
        """Paints the item names inside the ``FoldersWidget``."""
        painter, option, index, _, _, active, _, _ = args
        rect = QtCore.QRect(option.rect)
        root = self.parent().model().parent(index) == self.parent().rootIndex()

        if root:
            color = self.get_state_color(option, index, common.TEXT)
        else:
            color = self.get_state_color(option, index, common.SECONDARY_TEXT)
        rect.setLeft(rect.left() + common.MARGIN)
        rect.setRight(rect.right() - common.MARGIN)

        font = QtGui.QFont(common.PrimaryFont)
        painter.setFont(font)
        metrics = QtGui.QFontMetrics(font)

        # Resizing the height and centering
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(common.INLINE_ICON_SIZE)
        rect.moveTop(rect.top() - (rect.height() / 2.0))

        # Asset name
        text = index.data(QtCore.Qt.DisplayRole)
        text = re.sub(r'[^0-9a-zA-Z]+', ' ', text)
        text = re.sub(r'[_]{1,}', '_', text).strip('_')
        text = ' {} '.format(text)
        text = metrics.elidedText(
            text.upper(),
            QtCore.Qt.ElideRight,
            rect.width()
        )
        width = metrics.width(text)
        rect.setWidth(width)

        if root:
            painter.setBrush(common.FAVOURITE)
            pen = QtGui.QPen(common.FAVOURITE)
        else:
            painter.setBrush(common.SECONDARY_BACKGROUND)
            pen = QtGui.QPen(common.SECONDARY_BACKGROUND)

        pen.setWidth(common.INDICATOR_WIDTH)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 2, 2)

        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(QtGui.QPen(color))
        painter.drawText(
            rect,
            QtCore.Qt.AlignCenter,
            text
        )

    @paintmethod
    def paint_thumbnail(self, *args):
        """Paints the thumbnail of the ``FoldersWidget`` item."""
        painter, option, index, _, _, active, _, _ = args

        if self.parent().model().parent(index) != self.parent().rootIndex():
            return

        rect = QtCore.QRect(option.rect)
        rect.setLeft(option.rect.left())
        rect.setTop(rect.top())
        rect.setBottom(rect.bottom())
        rect.setRight(option.rect.left() + option.rect.height())

        center = rect.center()
        rect.setWidth(rect.width() / 2)
        rect.setHeight(rect.height() / 2)
        rect.moveCenter(center)

        pixmap = index.data(QtCore.Qt.DecorationRole).pixmap(
            option.rect.height(),
            option.rect.height(),
            QtGui.QIcon.Normal
        )
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

        active = self.parent().model().filePath(
            index) == self.parent().model().active_path

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        color = QtGui.QColor(common.BACKGROUND)
        if hover:
            color = QtGui.QColor(common.BACKGROUND_SELECTED)
        if active:
            color = QtGui.QColor(49, 107, 218)

        rect = QtCore.QRect(option.rect)
        root = self.parent().model().parent(index) == self.parent().rootIndex()
        if root:
            rect.setTop(rect.top() + 2)
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
        self.setItemDelegate(FoldersWidgetDelegate(parent=self))
        # self.setAnimated(True)
        self.setIndentation(common.MARGIN)
        self.setRootIsDecorated(False)


class FoldersWidget(BaseCombobox):
    def __init__(self, parent=None):
        super(FoldersWidget, self).__init__(parent=parent)
        view = FoldersView(parent=self)
        self.setView(view)
        self.setModel(FoldersModel(parent=self))
        self.override = False
        # Active selections
        self.activated.connect(self.activate_current_index)
        # Signals the user made a folder selection
        self.activated.connect(lambda int: self.set_override(True))

        self.model().directoryLoaded.connect(self.expand_to_depth)
        self.view().expanded.connect(self.set_view_height)
        self.view().collapsed.connect(self.set_view_height)

        self.setFixedWidth(120)

    def expand_to_depth(self):
        self.view().expandToDepth(0)

    def set_override(self, val):
        self.override = val

    def select_index(self, index):
        """Selects and activates the given index. A bit hackish..."""
        parent = self.rootModelIndex()
        self.setRootModelIndex(index.parent())
        self.setCurrentIndex(index.row())
        self.view().expand(index)
        self.view().selectionModel().setCurrentIndex(
            index, QtCore.QItemSelectionModel.ClearAndSelect)
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
        if len(asset) == 3:
            self.model().setRootPath(u'.')
            index = self.model().index(u'.')
            self.setRootModelIndex(index)

            self.select_index(QtCore.QModelIndex())
            self.setCurrentIndex(-1)
            return

        path = u'/'.join(list(asset) + [self.window().location, ])
        # Sets the root to the location folder.
        self.model().setRootPath(path)
        self.setRootModelIndex(self.model().index(path))

        # location = '{}/abc'.format(self.window().location) if isexport else self.window().location
        # path = u'/'.join(list(asset) + [location, ])
        self.override = False

        if self.window().location == common.ExportsFolder:
            path = u'/'.join(list(asset) + [self.window().location, 'abc'])
        # When currentfile is set, we want to match a folder inside to root,
        if self.diff(asset):
            index = self.model().index('{}/{}'.format(path, self.diff(asset)))
        else:
            index = self.model().index(path)
        self.select_index(index)

    def diff(self, asset):
        path = u'/'.join(list(asset) + [self.window().location, ])
        currentfile = QtCore.QFileInfo(self.window().currentfile).path()
        if self.override:
            currentfile = self.model().active_path
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


class BookmarksListDelegate(BookmarksWidgetDelegate):
    """The delegate used to paint the bookmark items."""

    def paint(self, painter, option, index):
        """Defines how the BookmarksWidgetItems should be painted."""
        args = self._get_paint_args(painter, option, index)
        self.paint_background(*args)
        #
        self.paint_thumbnail(*args)
        self.paint_archived(*args)
        #
        self.paint_name(*args)
        #
        self.paint_count(*args)
        #
        self.paint_selection_indicator(*args)
        self.paint_active_indicator(*args)

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
        self.setItemDelegate(AssetListDelegate(parent=self))

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


class AssetListDelegate(AssetWidgetDelegate):
    """Delegate used by the ``AssetWidget`` to display the collecteds assets."""

    def paint(self, painter, option, index):
        """Defines how the ``AssetWidget``'s' items should be painted."""
        args = self._get_paint_args(painter, option, index)

        self.paint_background(*args)
        #
        self.paint_thumbnail(*args)
        self.paint_archived(*args)
        self.paint_thumbnail_shadow(*args)
        #
        self.paint_name(*args)
        self.paint_description(*args)
        #
        self.paint_selection_indicator(*args)
        self.paint_active_indicator(*args)

    def sizeHint(self, option, index):
        return QtCore.QSize(common.WIDTH, common.ASSET_ROW_HEIGHT)


class SaverHeaderWidget(HeaderWidget):
    def __init__(self, parent=None):
        super(SaverHeaderWidget, self).__init__(parent=parent)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        rect = event.rect()
        rect.setTop(rect.bottom())
        painter.setBrush(QtGui.QBrush(common.BACKGROUND))
        painter.drawRect(event.rect())
        painter.end()


class SaverFileInfo(QtCore.QObject):
    """Utility class responsible for getting the currently set path components."""

    def __init__(self, parent):
        super(SaverFileInfo, self).__init__(parent=parent)

    def fileInfo(self):
        """Returns the path as a QFileInfo instance"""
        return QtCore.QFileInfo('{}/{}'.format(self.path(), self.fileName()))

    def path(self):
        """Returns the path() element of the set path."""
        paths = self._paths()
        arr = []
        for k in paths:
            if not paths[k]:
                break
            arr.append(paths[k])
        return u'/'.join(arr).rstrip(u'/')

    def _paths(self):
        """Private method querries the ui choices and constructs a valid path"""
        bookmarkswidget = self.parent().window().findChild(BookmarksWidget)
        assetswidget = self.parent().window().findChild(AssetsWidget)
        folderswidget = self.parent().window().findChild(FoldersWidget)

        paths = collections.OrderedDict()
        paths['server'] = None
        paths['job'] = None
        paths['root'] = None
        paths['asset'] = None
        paths['location'] = None
        paths['folder'] = None

        if not bookmarkswidget.active_index().isValid() or bookmarkswidget.currentIndex() == -1:
            return paths

        server, job, root = bookmarkswidget.active_index().data(common.ParentRole)
        paths['server'] = server
        paths['job'] = job
        paths['root'] = root

        if not assetswidget.active_index().isValid() or assetswidget.currentIndex() == -1:
            return paths

        _, _, _, asset = assetswidget.active_index().data(common.ParentRole)
        paths['asset'] = asset
        paths['location'] = self.parent().window().location

        if not folderswidget.active_index().isValid() or folderswidget.currentIndex() == -1:
            return paths

        # If the location is the same as the folder, we're not setting the folder
        if folderswidget.model().filePath(folderswidget.rootModelIndex()) == folderswidget.model().active_path:
            return paths

        diff = folderswidget.diff((
            paths['server'],
            paths['job'],
            paths['root'],
            paths['asset'],
        ))

        if diff:
            paths['folder'] = diff
            return paths

        if folderswidget.model().active_path:
            loc = (
                paths['server'],
                paths['job'],
                paths['root'],
                paths['asset'],
                paths['location'],
            )
            folder = folderswidget.model().active_path.replace(
                u'/'.join(loc), u'').rstrip(u'/')
            # There's no folder selected and
            if folder.rstrip(u'/') == u'/'.join(loc).rstrip(u'/'):
                folder = u'/'
            paths[u'folder'] = folder

        return paths

    def fileName(self, style=common.LowerCase):
        """The main method to get the new file's filename."""
        currentfile = self.parent().window().currentfile

        if currentfile:
            match = common.get_valid_filename(currentfile)
            if match:
                custom = self.parent().window().findChild(Custom).text()

                # Not including the username if the destination is the exports folder
                filename = match.expand(r'\1_\2_\3_{}_{}_\6.\7'.format(
                    custom if custom else u'untitled',
                    u'{}'.format(int(match.group(5)) +
                                 1).zfill(len(match.group(5)))
                ))
            else:
                filename = self._increment_sequence(currentfile)
        else:
            filename = self._new()

        if style == common.LowerCase:
            filename = filename.lower()
        elif style == common.UpperCase:
            filename = filename.upper()

        return filename

    def _new(self):
        """Creates a new filename based on the currently set properties."""
        paths = self._paths()

        custom = self.parent().window().findChild(Custom).text()
        regex = re.compile(r'[^0-9a-z]+', flags=re.IGNORECASE)
        job = regex.sub(u'', paths[u'job'])[
            :3] if paths[u'job'] else u'gw'

        asset = regex.sub(u'', paths[u'asset'])[
            :12] if paths[u'asset'] else u'sandbox'

        folder = paths['folder'].split(
            u'/')[0] if paths['folder'] else self.parent().window().location
        folder = regex.sub(u'', folder)[
            :12] if folder else self.parent().window().location

        custom = custom if custom else u'untitled'
        custom = regex.sub(u'-', custom)[:25]

        version = u'001'

        user = next(f for f in QtCore.QStandardPaths.standardLocations(
            QtCore.QStandardPaths.HomeLocation))
        user = QtCore.QFileInfo(user).fileName()
        user = regex.sub(u'', user)

        isexport = self.parent().window().location == common.ExportsFolder
        folder = self.parent().window().extension if isexport else folder
        return '{job}_{asset}_{folder}_{custom}_{version}_{user}.{ext}'.format(
            job=job,
            asset=asset,
            folder=folder,
            custom=custom,
            version=version,
            user=user,
            ext=self.parent().window().extension,
        )

    def _increment_sequence(self, currentfile):
        file_info = QtCore.QFileInfo(currentfile)
        match = common.get_sequence(file_info.fileName())

        if not match:
            return currentfile

        version = '{}'.format(int(match.group(2)) +
                              1).zfill(len(match.group(2)))
        print match.groups()
        return match.expand(r'\1{}\3.\4').format(version)


class BaseNameLabel(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super(BaseNameLabel, self).__init__(parent=parent)
        self.setTextFormat(QtCore.Qt.RichText)
        self.setOpenExternalLinks(False)
        self.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)

        self.setStyleSheet(
            """QLabel{{
                background-color: rgba(0,0,0,0);
                font-family: "{}";
                font-size: 11pt;
            }}""".format(common.PrimaryFont.family())
        )


class Prefix(BaseNameLabel):
    def __init__(self, parent=None):
        super(Prefix, self).__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)


class Custom(QtWidgets.QLineEdit):
    """Editor widget for editing the custom filename component."""

    def __init__(self, parent=None):
        super(Custom, self).__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignCenter)

        self.setMaxLength(25)
        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSize(11)
        metrics = QtGui.QFontMetrics(font)

        self.setPlaceholderText('untitled')
        self.setStyleSheet("""QLineEdit{{
            background-color: rgba(0,0,0,0);
            border-bottom: 2px solid rgba(255,255,255,255);
            padding: 0px;
            margin: 0px;
            color: rgba({});
            font-family: "{}";
            font-size: 11pt;
        }}""".format(
            '{},{},{},{}'.format(*common.TEXT_SELECTED.getRgb()),
            common.PrimaryFont.family()))

        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSize(12)
        metrics = QtGui.QFontMetrics(font)
        self.setFixedWidth(metrics.width('untitled'))

        self.textChanged.connect(self.resizeLineEditToContents)
        self.textChanged.connect(self.verify)

    def verify(self, text):
        cpos = self.cursorPosition()
        text = re.sub(r'[^a-z0-9\-]+', '-', text, flags=re.IGNORECASE)
        text = re.sub(r'-{2,}', '-', text, flags=re.IGNORECASE)
        self.setText(text)
        self.setCursorPosition(cpos)

    def resizeLineEditToContents(self, text):
        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSize(12)
        metrics = QtGui.QFontMetrics(font)
        width = metrics.width(text)
        minwidth = metrics.width('untitled')
        width = minwidth if width < minwidth else width
        self.setFixedSize(width, self.height())


class Suffix(BaseNameLabel):
    def __init__(self, parent=None):
        super(Suffix, self).__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)


class Check(ClickableLabel):
    def __init__(self, parent=None):
        super(Check, self).__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedSize(common.ASSET_ROW_HEIGHT, common.ASSET_ROW_HEIGHT)
        pixmap = common.get_rsc_pixmap(
            'check', common.FAVOURITE, common.ROW_HEIGHT / 1.5)
        self.setPixmap(pixmap)
        self.setStyleSheet("""
            QLabel {{background-color: rgba({});}}
        """.format(u'{}/{}/{}/{}'.format(*common.BACKGROUND.getRgb())))


class SaverWidget(QtWidgets.QDialog):
    """Contains the header and the saver widgets."""

    fileSaveRequested = QtCore.Signal(basestring)

    def __init__(self, extension, location, currentfile=None, parent=None):
        super(SaverWidget, self).__init__(parent=parent)
        self.extension = extension
        self.currentfile = currentfile
        self.location = location

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint
        )

        self._createUI()
        self._connectSignals()

        self.image = QtGui.QImage()
        self._set_initial_state()

    def pick_thumbnail(self):
        """Prompts to select an image file.

        """
        active_paths = Active.get_active_paths()
        dialog = QtWidgets.QFileDialog(parent=self)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilter(u'Image files (*.png *.jpg  *.jpeg)')

        paths = self.window().active_paths()
        directory = (paths[u'server'], paths[u'job'], paths[u'root'],
                     paths[u'asset'], self.window().location)
        directory = directory if all(directory) else (
            paths[u'server'], paths[u'job'], paths[u'root'])
        directory = directory if all(directory) else (u'/',)

        dialog.setDirectory(u'/'.join(directory))
        dialog.setOption(
            QtWidgets.QFileDialog.DontUseCustomDirectoryIcons, True)

        if not dialog.exec_():
            return
        if not dialog.selectedFiles():
            return

        path = next(f for f in dialog.selectedFiles())
        image = common.cache_image(path, common.ASSET_ROW_HEIGHT)
        self.image = common.cache_image(path, common.THUMBNAIL_IMAGE_SIZE)
        pixmap = QtGui.QPixmap()
        pixmap.convertFromImage(image)
        self.findChild(ThumbnailButton).setPixmap(pixmap)
        self.findChild(ThumbnailButton).setStyleSheet("""QLabel {{background-color: rgba({});}}""".format(
            '{},{},{},{}'.format(*common.IMAGE_CACHE[u'{}:BackgroundColor'.format(path)].getRgb())))

    def _createUI(self):
        common.set_custom_stylesheet(self)
        #
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        #
        self.setFixedWidth(common.WIDTH * 1.5)
        #
        mainrow = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(mainrow)
        mainrow.layout().setContentsMargins(0, 0, 0, 0)
        mainrow.layout().setSpacing(common.INDICATOR_WIDTH)
        mainrow.layout().setAlignment(QtCore.Qt.AlignCenter)
        #
        thumbnailbutton = ThumbnailButton(parent=self)
        thumbnailbutton.setFixedSize(
            common.ASSET_ROW_HEIGHT, common.ASSET_ROW_HEIGHT)
        mainrow.layout().addWidget(thumbnailbutton)
        self.layout().addWidget(mainrow)
        #
        column = QtWidgets.QWidget()
        QtWidgets.QVBoxLayout(column)
        column.layout().setContentsMargins(0, common.MARGIN, 0, common.MARGIN)
        column.layout().setSpacing(common.MARGIN)
        column.layout().setAlignment(QtCore.Qt.AlignCenter)
        mainrow.layout().addWidget(column)

        # Row 1
        row = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row)
        row.layout().setContentsMargins(0, 0, 0, 0)
        row.layout().setSpacing(common.INDICATOR_WIDTH)
        row.layout().setAlignment(QtCore.Qt.AlignCenter)
        column.layout().addWidget(row, 1)
        #
        editor = QtWidgets.QLineEdit(parent=self)
        editor.setPlaceholderText(u'Description...')
        editor.setStyleSheet("""QLineEdit {{
            background-color: rgba(0,0,0,0);
            border-bottom: 2px solid rgba(0,0,0,50);
            padding: 0px;
            margin: 0px;
            color: rgba({});
            font-family: "{}";
            font-size: 11pt;
        }}""".format(
            '{},{},{},{}'.format(*common.TEXT_SELECTED.getRgb()),
            common.PrimaryFont.family()
        ))

        row.layout().addWidget(editor, 1)
        row.layout().addWidget(BookmarksWidget(parent=self))
        row.layout().addWidget(AssetsWidget(parent=self))
        row.layout().addWidget(FoldersWidget(parent=self))
        #
        row = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row)
        row.layout().setContentsMargins(0, 0, 0, 0)
        row.layout().setSpacing(0)
        row.layout().setAlignment(QtCore.Qt.AlignCenter)
        row.layout().addWidget(Prefix(parent=self))
        row.layout().addWidget(Custom(parent=self))
        row.layout().addWidget(Suffix(parent=self), 1)
        column.layout().addWidget(row, 1)

        mainrow.layout().addWidget(Check(parent=self))
        self.layout().insertWidget(0, SaverHeaderWidget(parent=self))

        minimizebutton = self.findChild(MinimizeButton)
        minimizebutton.setHidden(True)

        # Statusbar
        statusbar = QtWidgets.QStatusBar(parent=self)
        statusbar.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
        statusbar.setSizeGripEnabled(False)
        statusbar.layout().setAlignment(QtCore.Qt.AlignRight)
        statusbar.setStyleSheet("""QStatusBar {{
            background-color: rgba(0,0,0,0);
            color: rgba({color});
            font-family: "{family}";
            font-size: 8pt;
        }}""".format(
            color='{},{},{},{}'.format(*common.SECONDARY_TEXT.getRgb()),
            family=common.PrimaryFont.family()
        ))

        statusbar.layout().setContentsMargins(20, 20, 20, 20)

        statusbar.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )

        self.layout().addSpacing(common.MARGIN)
        self.layout().addWidget(statusbar, 1)

    def _set_initial_state(self):
        bookmarkswidget = self.findChild(BookmarksWidget)
        assetswidget = self.findChild(AssetsWidget)
        folderswidget = self.findChild(FoldersWidget)

        if not bookmarkswidget.active_index().isValid():
            assetswidget.setCurrentIndex(-1)

        # Valid asset selection
        if assetswidget.active_index().isValid():
            asset = assetswidget.active_index().data(common.ParentRole)
            folderswidget.set_asset(asset)

            if self.currentfile:  # Selecting the currentfile folder
                path = u'/'.join(list(asset) + [self.location, ])
                currentfile = QtCore.QFileInfo(
                    self.currentfile).path()
                if path in currentfile:
                    index = folderswidget.model().index(currentfile)
                    folderswidget.select_index(index)
        else:
            assetswidget.setCurrentIndex(-1)

            # Folderswidget needs it's root index set before being able to unset
            # the selection
            folderswidget.model().setRootPath(u'.')
            index = folderswidget.model().index(u'.')
            folderswidget.setRootModelIndex(index)

            folderswidget.select_index(QtCore.QModelIndex())
            folderswidget.setCurrentIndex(-1)

        if self.currentfile:
            # Checking if the reference file has a valid pattern
            match = common.get_valid_filename(self.currentfile)
            self.findChild(Custom).setHidden(False)
            if match:
                self.findChild(Custom).setHidden(False)
                self.findChild(Custom).setText(match.group(4))
            else:
                self.findChild(Custom).setHidden(True)
        else:
            self.findChild(Custom).setHidden(False)

        self.update_filename_display()
        self.update_filepath_display()

    def update_filepath_display(self, *args, **kwargs):
        """Slot responsible for updating the file-path display."""
        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSize(8)
        metrics = QtGui.QFontMetrics(font)
        text = metrics.elidedText(
            SaverFileInfo(self).fileInfo().filePath(),
            QtCore.Qt.ElideLeft,
            self.window().rect().width() - common.MARGIN
        )
        self.findChild(QtWidgets.QStatusBar).showMessage(text)

    def update_filename_display(self, *args, **kwargs):
        """Slot responsible for updating the Prefix, Custom, and Suffix widgets."""
        f = SaverFileInfo(parent=self)
        file_info = QtCore.QFileInfo(f.fileName(style=common.LowerCase))

        match = common.get_valid_filename(
            self.currentfile) if self.currentfile else None
        if self.currentfile and not match:
            self.findChild(Prefix).setText(file_info.completeBaseName())
            self.findChild(Suffix).setText(
                '.{}'.format(file_info.completeSuffix()))
        elif self.currentfile and match:
            prefix, suffix = self.prefix_suffix(match, increment=True)
            self.findChild(Prefix).setText(prefix)
            self.findChild(Suffix).setText(suffix)
        else:  # New name
            match = common.get_valid_filename(
                '/{}'.format(f.fileName(style=common.LowerCase)))
            prefix, suffix = self.prefix_suffix(match, increment=False)
            self.findChild(Prefix).setText(prefix)
            self.findChild(Suffix).setText(suffix)

    def prefix_suffix(self, match, increment=True):
        prefix = match.expand(r'\1_\2_\3_')
        suffix = match.expand(r'_<span style="color:rgba({});">{}</span>_\6.\7'.format(
            u'{},{},{},{}'.format(*common.FAVOURITE.getRgb()),
            u'{}'.format(int(match.group(5)) + int(increment)
                         ).zfill(len(match.group(5)))
        ))
        return prefix, suffix

    def _done(self):
        bookmarkswidget = self.findChild(BookmarksWidget)
        assetswidget = self.findChild(AssetsWidget)
        folderswidget = self.findChild(FoldersWidget)

        if not bookmarkswidget.active_index().isValid():
            return QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.NoIcon,
                u'Bookmarks not selected.', u'', parent=self).exec_()
        elif not assetswidget.active_index().isValid():
            return QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.NoIcon,
                u'', u'Asset not selected.', parent=self).exec_()
        elif not folderswidget.active_index().isValid():
            return QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.NoIcon,
                u'', u'Fodler not selected.', parent=self).exec_()

        self.fileSaveRequested.emit(SaverFileInfo(self).fileInfo().filePath())
        self.close()

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
        custom = self.findChild(Custom)
        check = self.findChild(Check)

        check.clicked.connect(self._done)
        # Closes the dialog
        closebutton.clicked.connect(self.close)
        # Picks a thumbnail
        thumbnailbutton.clicked.connect(self.pick_thumbnail)

        # Updates the assets model when the bookmark changes
        bookmarksmodel.activeBookmarkChanged.connect(assetsmodel.set_bookmark)
        bookmarksmodel.activeBookmarkChanged.connect(folderswidget.set_asset)
        assetmodel.activeAssetChanged.connect(folderswidget.set_asset)

        # Filename
        bookmarkswidget.activated.connect(self.update_filename_display)
        assetswidget.activated.connect(self.update_filename_display)
        folderswidget.activated.connect(self.update_filename_display)
        custom.textChanged.connect(self.update_filename_display)
        # Filename
        bookmarkswidget.activated.connect(self.update_filepath_display)
        assetswidget.activated.connect(self.update_filepath_display)
        folderswidget.activated.connect(self.update_filepath_display)
        custom.textChanged.connect(self.update_filepath_display)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    currentfile = u'//gordo/jobs/tkwwbk_8077/build2/asset_one/scenes/carlos/test/job_asset_location_new__filename_002_gergely.ma'

    widget = SaverWidget(u'ma', common.ExportsFolder, currentfile=None)

    def func(path):
        print path
    widget.fileSaveRequested.connect(func)
    widget.show()
    app.exec_()
