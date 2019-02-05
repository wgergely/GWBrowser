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
import collections
from PySide2 import QtCore, QtWidgets, QtGui

import browser.common as common

from browser.delegate import BaseDelegate
from browser.baselistwidget import BaseContextMenu
from browser.delegate import paintmethod
from browser.editors import ClickableLabel
from browser.settings import Active

from browser.bookmarkswidget import BookmarksModel
from browser.assetwidget import AssetModel
from browser.browserwidget import HeaderWidget, CloseButton, MinimizeButton

from browser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite


class VersionIndicator(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(VersionIndicator, self).__init__(parent=parent)
        self.setFixedHeight(common.ROW_HEIGHT)
        self.setFixedWidth(common.ROW_HEIGHT)

    def get_current_version(self):
        """Retrun the current file's version."""
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


class ThumbnailButton(ClickableLabel):
    """Button used to select the thumbnail for this item."""

    def __init__(self, parent=None):
        super(ThumbnailButton, self).__init__(parent=parent)
        self.setFixedSize(QtCore.QSize(common.ROW_HEIGHT + (common.INDICATOR_WIDTH * 2),
                                       common.ROW_HEIGHT + (common.INDICATOR_WIDTH * 2)))
        self.setAlignment(QtCore.Qt.AlignCenter)
        pixmap = common.get_rsc_pixmap(
            u'placeholder', common.TEXT, common.ROW_HEIGHT)
        self.setPixmap(pixmap)


class ParentButton(ClickableLabel):
    """Button responsible for selecting the subfolder the new file should be saved to."""

    # Signal
    parentFolderChanged = QtCore.Signal(basestring)

    def __init__(self, parent=None):
        super(ParentButton, self).__init__(parent=parent)
        self.selected_path = None

        self._createUI()
        self.clicked.connect(self.showPopup)

    def _createUI(self):
        self.setStyleSheet("""
            QLabel {{
                background-color: rgba({});}}
        """.format(u'{}/{}/{}/{}'.format(*common.BACKGROUND_SELECTED.getRgb())))

        self.setFixedSize(QtCore.QSize(
            common.ROW_HEIGHT / 2.0, common.ROW_HEIGHT / 2.0))
        pixmap = common.get_rsc_pixmap(
            u'folder', common.TEXT, common.INLINE_ICON_SIZE)
        self.setPixmap(pixmap)

    def _get_subfolders(self, path):
        """The distinct subfolder loaded into a dictionary."""
        # Getting all the subfolders from the current location
        dir_ = QtCore.QDir(path)
        dir_.setFilter(QtCore.QDir.NoDotAndDotDot |
                       QtCore.QDir.Dirs |
                       QtCore.QDir.Readable)
        it = QtCore.QDirIterator(
            dir_, flags=QtCore.QDirIterator.Subdirectories)

        def _get(ks, d):
            for k in ks:
                if k not in d:
                    d[k] = {}
                ks.pop(0)
                d = d[k]
                _get(ks, d)

        d = {}
        while it.hasNext():
            filepath = it.next()
            rootpath = filepath.replace(path, u'')
            folders = rootpath.strip(u'/').split(u'/')
            _get(folders, d)

        return d

    def itemSelected(self, path):
        """Slot connected to the popup menu, saves the path selection."""
        print path
        self.selected_path = path

    def showPopup(self):
        """Collects the available parent folders."""
        parent = self.parent().parent().parent().parent()

        # Making sure bookmark and asset is set.
        bookmarkswidget = parent.findChild(BookmarksWidget)
        if not bookmarkswidget.active_index().isValid():
            return
        server, job, root = bookmarkswidget.active_index().data(common.ParentRole)

        assetswidget = parent.findChild(AssetsWidget)
        if not assetswidget.active_index().isValid():
            return

        # The location selection so far
        server, job, root, asset = assetswidget.active_index().data(common.ParentRole)
        location = parent.location
        path = u'/'.join((server, job, root, asset, location))

        menus = self._get_subfolders(path)
        menu = SubfoldersMenu(menus, parent=self)
        menu.itemSelected.connect(self.itemSelected)
        menu.exec_()


class SubfoldersMenu(BaseContextMenu):
    itemSelected = QtCore.Signal(basestring)

    def __init__(self, menus, parent=None):
        super(SubfoldersMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.setFixedWidth(350)

        parent = self.parent().window()
        assetswidget = parent.findChild(AssetsWidget)
        server, job, root, asset = assetswidget.active_index().data(common.ParentRole)

        # Getting the active
        currentfolder = QtCore.QFileInfo(parent.currentfile).dir()
        if not currentfolder.exists():
            currentfolder = ''
        else:
            currentfolder = currentfolder.path()

        matchpath = self.parent().selected_path if self.parent().selected_path else currentfolder

        # Let's find the common basepath of the selection and the
        rootpath = '/'.join((server, job, root, asset, parent.location))
        currentsubpath = None
        if rootpath in matchpath:
            currentsubpath = matchpath.replace(rootpath, '')
            currentsubpath = currentsubpath.split('/')
            currentsubpath.pop()
            currentsubpath = '/'.join(currentsubpath)
            currentsubpath = currentsubpath.strip('/')

        menus = self.build_folders_data(menus)
        self.add_subfolders_menu(menus, currentsubpath)

    def add_subfolders_menu(self, menus, matchpath):
        pixmap = common.get_rsc_pixmap(
            u'folder', common.TEXT_DISABLED, common.INLINE_ICON_SIZE)
        active_pixmap = common.get_rsc_pixmap(
            u'item_on', common.SELECTION, common.INLINE_ICON_SIZE)

        menu_set = collections.OrderedDict()
        for k in sorted(list(menus)):
            if '/' in k:
                kk = k.split('/')
                modedir = kk.pop(0)
                menu_set[modedir] = collections.OrderedDict()
                menu_set['{}:text'.format(modedir)] = modedir.upper()

                if matchpath:
                    active = modedir in matchpath
                else:
                    active = False
                menu_set['{}:icon'.format(
                    modedir)] = active_pixmap if active else pixmap
                def func(arg):
                    print '!!!!!!'
                menu_set['{}:action'.format(
                    modedir)] = func

                _arr = []
                for subdir in kk:
                    _arr.append(subdir)

                    if matchpath:
                        active = subdir == matchpath
                    else:
                        active = False

                    k = '{}/{}'.format(modedir, '/'.join(_arr))
                    pk = '{}  /  {}'.format(modedir, '  /  '.join(_arr))
                    menu_set[k] = {
                        'icon': active_pixmap if active else pixmap,
                        'text': pk.upper()
                    }
            else:
                if matchpath:
                    active = k == matchpath
                else:
                    active = False
                menu_set[k] = {
                    'icon':  active_pixmap if active else pixmap,
                    'text': k.upper(),
                }
        self.create_menu(menu_set)

    def build_folders_data(self, dictionary):
        """Returns the data needed to build the menus."""
        keys = []
        def _build_folders_menus(dictionary, path):
            path = path.strip(u'/')
            if not dictionary:
                keys.append(path)
                path = ''
                return
            for k in sorted(list(dictionary)):
                pp = u'{}/{}'.format(path, k)
                _build_folders_menus(dictionary[k], pp)

        _build_folders_menus(dictionary, u'')
        return keys


    def showEvent(self, event):
        pos = self.parent().rect().bottomLeft()
        pos = self.parent().mapToGlobal(pos)
        self.move(pos)

        super(SubfoldersMenu, self).show()


class BookmarksWidget(QtWidgets.QComboBox):
    """Combobox to view and select the destination bookmark."""

    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)
        self.setModel(BookmarksModel(parent=self))

        self.setFixedHeight(common.ROW_HEIGHT / 2.0)
        self.view().setFixedWidth(common.WIDTH)
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

    def showPopup(self):
        parent = self.parent().parent().parent().parent()
        left = parent.rect().topRight()
        left = parent.mapToGlobal(left).x()
        right = self.rect().topLeft()
        right = self.mapToGlobal(right).x()
        self.view().setFixedWidth(left - right + common.MARGIN)
        super(BookmarksWidget, self).showPopup()


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


class AssetsWidget(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(AssetsWidget, self).__init__(parent=parent)
        active_paths = Active.get_active_paths()
        bookmark = (
            active_paths[u'server'],
            active_paths[u'job'],
            active_paths[u'root']
        )
        self.setModel(AssetModel(bookmark, parent=self))

        self.setFixedHeight(common.ROW_HEIGHT / 2.0)
        self.setItemDelegate(AssetWidgetDelegate(parent=self))

        self.activated.connect(self.activate_current_index)

        # Selecting the active bookmark
        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0, parent=QtCore.QModelIndex())
            if index.flags() & MarkedAsActive:
                self.setCurrentIndex(n)
                self.view().scrollTo(index)
                break

    def showPopup(self):
        parent = self.parent().parent().parent().parent()
        left = parent.rect().topRight()
        left = parent.mapToGlobal(left).x()
        right = self.rect().topLeft()
        right = self.mapToGlobal(right).x()
        self.view().setFixedWidth(left - right + common.MARGIN)
        super(AssetsWidget, self).showPopup()

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
        self._connectSignals()

    def _createUI(self):
        o = common.INDICATOR_WIDTH

        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(
            common.MARGIN, common.MARGIN, common.MARGIN, common.MARGIN)
        self.layout().setSpacing(0)

        self.setFixedHeight(common.ROW_HEIGHT * 2)
        self.setFixedWidth(common.WIDTH)

        common.set_custom_stylesheet(self)

        label = ThumbnailButton(parent=self)
        label.setStyleSheet(
            u'background-color: rgba({});'.format(u'{}/{}/{}/{}'.format(*common.BACKGROUND.getRgb())))
        self.layout().addWidget(label)

        stack = QtWidgets.QWidget()
        stack.setFocusPolicy(QtCore.Qt.NoFocus)
        QtWidgets.QVBoxLayout(stack)
        stack.layout().setContentsMargins(0, 0, 0, 0)
        stack.layout().setSpacing(0)

        row = QtWidgets.QWidget(parent=self)
        QtWidgets.QHBoxLayout(row)
        row.layout().setContentsMargins(0, 0, 0, 0)
        row.layout().setSpacing(1)

        row.layout().addWidget(BookmarksWidget(parent=self))
        row.layout().addWidget(AssetsWidget(parent=self))
        row.layout().addWidget(ParentButton(parent=self))
        stack.layout().addWidget(row)

        row = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row)
        row.layout().setContentsMargins(0, 0, 0, 0)
        row.layout().setSpacing(0)

        editor = QtWidgets.QLineEdit()
        editor.setPlaceholderText(u'Add description here...')
        editor.setStyleSheet("""
            QLineEdit {{background-color: rgba({});}}
        """.format(u'{}/{}/{}/{}'.format(*common.SECONDARY_BACKGROUND.getRgb())))
        row.layout().addWidget(editor)
        stack.layout().addWidget(row)

        self.layout().addWidget(stack)
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
        rect.setWidth(rect.width() - (common.MARGIN * 1.5))
        rect.setHeight(rect.height() - (common.MARGIN * 1.5))
        rect.moveCenter(center)

        painter.setBrush(common.BACKGROUND)
        painter.drawRoundedRect(rect, 4, 4)
        painter.end()

    def select_thumbnail(self):
        """Prompts to select an image file."""
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

        print dialog.selectedFiles()
        # TODO: Implement this fucker

    def _connectSignals(self):
        self.findChild(ThumbnailButton).clicked.connect(self.select_thumbnail)
        bookmarksmodel = self.findChild(BookmarksModel)
        assetsmodel = self.findChild(AssetModel)
        bookmarksmodel.activeBookmarkChanged.connect(assetsmodel.set_bookmark)
        parentbutton = self.findChild(ParentButton)


class SaverHeaderWidget(HeaderWidget):
    def __init__(self, parent=None):
        super(SaverHeaderWidget, self).__init__(parent=parent)
        self._connectSignals()

    def _connectSignals(self):
        bookmarkswidget = self.parent().findChild(BookmarksWidget)
        assetswidget = self.parent().findChild(AssetsWidget)
        bookmarkswidget.activated.connect(self.itemActivated)
        assetswidget.activated.connect(self.itemActivated)

    def itemActivated(self, *args, **kwargs):
        """Slot to update the header."""
        bookmarkswidget = self.parent().findChild(BookmarksWidget)

        if not bookmarkswidget.active_index().isValid():
            text = u'No bookmark set'
        else:
            _, job, root = bookmarkswidget.active_index().data(common.ParentRole)
            text = u'{} | {}'.format(job, root)

        assetswidget = self.parent().findChild(AssetsWidget)
        if not assetswidget.active_index().isValid():
            text = u'{} | No asset set'.format(text)
        else:
            _, _, _, asset = assetswidget.active_index().data(common.ParentRole)
            text = u'{} | {}'.format(text, asset)

        self.label.setText(text)


class SaverWidget(QtWidgets.QDialog):
    fileSaveRequested = QtCore.Signal(basestring)

    def __init__(self, currentfile='', location=common.ScenesFolder, parent=None):
        super(SaverWidget, self).__init__(parent=parent)
        self.currentfile = currentfile
        self.location = location

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint
        )

        self._createUI()
        self._connectSignals()

    def _createUI(self):
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.layout().addWidget(Saver(parent=self))
        self.layout().insertWidget(0, SaverHeaderWidget(parent=self))

        minimizebutton = self.findChild(MinimizeButton)
        minimizebutton.setHidden(True)

    def _connectSignals(self):
        closebutton = self.findChild(CloseButton)
        closebutton.clicked.connect(self.close)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    currentfile = ''
    # currentfile = '//gordo/jobs/tkwwbk_8077/films/prologue/shots/sh_210/scenes/fx/branches/sh_210_v004.ma'
    location = common.ScenesFolder
    widget = SaverWidget(currentfile=currentfile, location=location)
    widget.show()
    app.exec_()
