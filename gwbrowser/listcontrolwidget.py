# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903, C0330, E1120

"""Widget reponsible controlling the displayed list and the filter-modes."""

import sys
import functools
from PySide2 import QtWidgets, QtGui, QtCore

from gwbrowser.datakeywidget import DataKeyView
from gwbrowser.settings import Active
import gwbrowser.common as common
from gwbrowser.basecontextmenu import BaseContextMenu, contextmenu

from gwbrowser.editors import FilterEditor
from gwbrowser.editors import ClickableLabel
import gwbrowser.settings as Settings

from gwbrowser.imagecache import ImageCache
from gwbrowser.imagecache import ImageCacheWorker
from gwbrowser.fileswidget import FilesWidget

from gwbrowser.assetswidget import AssetModel
from gwbrowser.bookmarkswidget import BookmarksModel

from gwbrowser.settings import local_settings


class BrowserButtonContextMenu(BaseContextMenu):
    """The context-menu associated with the BrowserButton."""

    def __init__(self, parent=None):
        super(BrowserButtonContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_show_menu()
        self.add_toolbar_menu()

    @contextmenu
    def add_show_menu(self, menu_set):
        if not hasattr(self.parent(), 'clicked'):
            return menu_set
        menu_set[u'show'] = {
            u'icon': ImageCache.get_rsc_pixmap(u'custom', None, common.INLINE_ICON_SIZE),
            u'text': u'Open...',
            u'action': self.parent().clicked.emit
        }
        return menu_set

    @contextmenu
    def add_toolbar_menu(self, menu_set):
        active_paths = Active.paths()
        bookmark = (active_paths[u'server'],
                    active_paths[u'job'], active_paths[u'root'])
        asset = bookmark + (active_paths[u'asset'],)
        location = asset + (active_paths[u'location'],)

        if all(bookmark):
            menu_set[u'bookmark'] = {
                u'icon': ImageCache.get_rsc_pixmap('bookmark', common.TEXT, common.INLINE_ICON_SIZE),
                u'disabled': not all(bookmark),
                u'text': u'Show active bookmark in the file manager...',
                u'action': functools.partial(common.reveal, u'/'.join(bookmark))
            }
            if all(asset):
                menu_set[u'asset'] = {
                    u'icon': ImageCache.get_rsc_pixmap(u'assets', common.TEXT, common.INLINE_ICON_SIZE),
                    u'disabled': not all(asset),
                    u'text': u'Show active asset in the file manager...',
                    u'action': functools.partial(common.reveal, '/'.join(asset))
                }
                if all(location):
                    menu_set[u'location'] = {
                        u'icon': ImageCache.get_rsc_pixmap(u'location', common.TEXT, common.INLINE_ICON_SIZE),
                        u'disabled': not all(location),
                        u'text': u'Show active location in the file manager...',
                        u'action': functools.partial(common.reveal, '/'.join(location))
                    }

        return menu_set


class BrowserButton(ClickableLabel):
    """Small widget to embed into the context to toggle the BrowserWidget's visibility.

    """
    message = QtCore.Signal(unicode)

    def __init__(self, height=common.ROW_HEIGHT, parent=None):
        super(BrowserButton, self).__init__(parent=parent)
        self.context_menu_cls = BrowserButtonContextMenu
        self.setFixedWidth(height)
        self.setFixedHeight(height)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setWindowFlags(
            QtCore.Qt.Widget
            | QtCore.Qt.FramelessWindowHint
        )
        pixmap = ImageCache.get_rsc_pixmap(
            u'custom_bw', common.SECONDARY_TEXT, height)
        self.setPixmap(pixmap)
        self.setStatusTip(u'Opens GWBrowser')

    def set_size(self, size):
        self.setFixedWidth(int(size))
        self.setFixedHeight(int(size))
        pixmap = ImageCache.get_rsc_pixmap(
            u'custom_bw', common.SECONDARY_TEXT, int(size))
        self.setPixmap(pixmap)

    def enterEvent(self, event):
        self.message.emit(self.statusTip())
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def paintEvent(self, event):
        """Browser button's custom paint event."""
        option = QtWidgets.QStyleOption()
        option.initFrom(self)

        painter = QtGui.QPainter()
        painter.begin(self)
        brush = self.pixmap().toImage()

        painter.setBrush(brush)
        painter.setPen(QtCore.Qt.NoPen)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        painter.setOpacity(0.8)
        if option.state & QtWidgets.QStyle.State_MouseOver:
            painter.setOpacity(1)

        painter.drawRoundedRect(self.rect(), 2, 2)
        painter.end()

    def contextMenuEvent(self, event):
        """Context menu event."""
        # Custom context menu
        shift_modifier = event.modifiers() & QtCore.Qt.ShiftModifier
        alt_modifier = event.modifiers() & QtCore.Qt.AltModifier
        control_modifier = event.modifiers() & QtCore.Qt.ControlModifier
        if shift_modifier or alt_modifier or control_modifier:
            self.customContextMenuRequested.emit()
            return

        widget = self.context_menu_cls(parent=self)
        widget.move(self.mapToGlobal(self.rect().bottomLeft()))
        widget.setFixedWidth(300)
        common.move_widget_to_available_geo(widget)
        widget.exec_()


class SlackButton(BrowserButton):
    """The button used to open slack."""

    def __init__(self, parent=None):
        self.context_menu_cls = BrowserButtonContextMenu
        super(SlackButton, self).__init__(
            height=common.INLINE_ICON_SIZE, parent=parent)
        self.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(ur'https://gwbcn.slack.com/'), type=QtCore.Qt.QueuedConnection)
        self.setStatusTip(u'Ctrl+Shift+S: Open slack in the web-browser')

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+Shift+S'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(self.clicked)
        shortcut.activated.connect(self.repaint)

        pixmap = ImageCache.get_rsc_pixmap(
            u'slack', common.SECONDARY_TEXT, self.height())
        self.setPixmap(pixmap)
        self.setStatusTip(u'Opens GWBrowser')


class ControlButton(ClickableLabel):
    """Baseclass used for controls buttons to control list display."""
    message = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(ControlButton, self).__init__(parent=parent)
        self._parent = None
        self.setFixedSize(
            common.INLINE_ICON_SIZE,
            common.INLINE_ICON_SIZE,
        )
        self.clicked.connect(self.action, type=QtCore.Qt.QueuedConnection)
        self.setStatusTip(u'')

    def enterEvent(self, event):
        self.message.emit(self.statusTip())
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def pixmap(self, c):
        return QtGui.QPixmap(common.INLINE_ICON_SIZE, common.INLINE_ICON_SIZE)

    def current(self):
        if not self._parent:
            return None
        return self._parent.currentWidget()

    def set_parent(self, widget):
        self._parent = widget

    def state(self):
        return False

    @QtCore.Slot()
    def action(self):
        pass

    def paintEvent(self, event):
        """ControlButton's custom paint event."""
        painter = QtGui.QPainter()
        painter.begin(self)

        option = QtWidgets.QStyleOptionButton()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        color = common.FAVOURITE if self.state() else QtGui.QColor(255, 255, 255, 50)
        color = common.TEXT_SELECTED if hover else color
        pixmap = self.pixmap(color)
        painter.drawPixmap(self.rect(), pixmap, pixmap.rect())
        painter.end()


class TodoButton(ControlButton):
    """The button for showing the todo editor."""

    def __init__(self, parent=None):
        super(TodoButton, self).__init__(parent=parent)
        description = u'Ctrl+T  |  Show the Todo & Note editor'
        self.setToolTip(description)
        self.setStatusTip(description)

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+T'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(self.clicked)
        shortcut.activated.connect(self.repaint)

    def pixmap(self, c):
        return ImageCache.get_rsc_pixmap(u'todo', c, common.INLINE_ICON_SIZE)

    def state(self):
        index = self._parent.widget(1).model().sourceModel().active_index()
        if not index.isValid():
            return
        if index.data(common.TodoCountRole):
            return True
        return False

    def action(self):
        assetswidget = self._parent.widget(1)
        index = assetswidget.model().sourceModel().active_index()
        index = assetswidget.model().mapFromSource(index)
        if not index.isValid():
            return
        assetswidget.show_todos(index)

    def repaint(self):
        super(TodoButton, self).repaint()
        if self._parent.currentIndex() in (2,):
            self.show()
        else:
            self.hide()


class FilterButton(ControlButton):
    """Button for showing the filter editor."""

    def __init__(self, parent=None):
        super(FilterButton, self).__init__(parent=parent)
        description = u'Ctrl+F  |  Edit search filter'
        self.setToolTip(description)
        self.setStatusTip(description)

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+F'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(self.clicked)
        shortcut.activated.connect(self.repaint)

    def pixmap(self, c):
        return ImageCache.get_rsc_pixmap(u'filter', c, common.INLINE_ICON_SIZE)

    def state(self):
        filter_text = self.current().model().filterText()
        if not filter_text:
            return False
        if filter_text == u'/':
            return False
        return True

    def action(self):
        """The action to perform when finished editing the filter text."""
        filter_text = self.current().model().filterText()
        filter_text = common.clean_filter_text(filter_text)
        #
        parent = self._parent.parent().listcontrolwidget
        editor = FilterEditor(filter_text, parent=parent)
        pos = parent.rect().topLeft()
        pos = parent.mapToGlobal(pos)

        editor.move(pos)
        editor.setFixedWidth(parent.rect().width())

        model = self.current().model()
        editor.finished.connect(lambda x: model.filterTextChanged.emit(
            common.regexify_filter_text(x)))
        editor.finished.connect(self.repaint)
        editor.finished.connect(editor.deleteLater)
        #
        editor.show()


class CollapseSequenceButton(ControlButton):
    """The buttons responsible for collapsing/expanding the sequences of the
    current list.

    """

    def __init__(self, parent=None):
        super(CollapseSequenceButton, self).__init__(parent=parent)
        description = u'Ctrl+G  |  Group sequences together'
        self.setToolTip(description)
        self.setStatusTip(description)

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+G'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(self.clicked)
        shortcut.activated.connect(self.repaint)

    def pixmap(self, c):
        return ImageCache.get_rsc_pixmap(u'collapse', c, common.INLINE_ICON_SIZE)

    def state(self):
        datatype = self.current().model().sourceModel().data_type()
        if datatype == common.FileItem:
            return False
        return True

    @QtCore.Slot()
    def action(self):
        """Only lists containing sequences can be collapsed."""
        if self._parent.currentIndex() not in (2, 3):
            return

        datatype = self.current().model().sourceModel().data_type()
        if datatype == common.FileItem:
            self.current().model().sourceModel().dataTypeChanged.emit(common.SequenceItem)
        else:
            self.current().model().sourceModel().dataTypeChanged.emit(common.FileItem)

    def repaint(self):
        super(CollapseSequenceButton, self).repaint()
        if self._parent.currentIndex() in (2, 3):
            self.show()
        else:
            self.hide()


class ToggleArchivedButton(ControlButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(ToggleArchivedButton, self).__init__(parent=parent)
        description = u'Ctrl+Shift+A  |  Show archived items'
        self.setToolTip(description)
        self.setStatusTip(description)

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+Shift+A'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(self.clicked)
        shortcut.activated.connect(self.repaint)

    def pixmap(self, c):
        return ImageCache.get_rsc_pixmap(u'active', c, common.INLINE_ICON_SIZE)

    def state(self):
        val = self.current().model().filterFlag(common.MarkedAsArchived)
        return val

    @QtCore.Slot()
    def action(self):
        val = self.current().model().filterFlag(common.MarkedAsArchived)
        self.current().model().filterFlagChanged.emit(
            common.MarkedAsArchived, not val)

    def repaint(self):
        super(ToggleArchivedButton, self).repaint()
        if self._parent.currentIndex() < 3:
            self.show()
        else:
            self.hide()


class ToggleButtons(ControlButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(ToggleButtons, self).__init__(parent=parent)
        description = u'Ctrl+H  |  Show or hide list buttons'
        self.setToolTip(description)
        self.setStatusTip(description)

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+H'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(self.clicked)
        shortcut.activated.connect(self.repaint)

    def pixmap(self, c):
        return ImageCache.get_rsc_pixmap(u'showbuttons', c, common.INLINE_ICON_SIZE)

    def state(self):
        val = self.current().buttons_hidden()
        return val

    @QtCore.Slot()
    def action(self):
        val = self.current().buttons_hidden()
        self.current().set_buttons_hidden(not val)
        self.current().repaint()

    def repaint(self):
        super(ToggleButtons, self).repaint()
        if self._parent.currentIndex() == 2:
            self.show()
        else:
            self.hide()


class ToggleFavouriteButton(ControlButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(ToggleFavouriteButton, self).__init__(parent=parent)
        description = u'Ctrl+Shift+F  |  Show my favourites only'
        self.setToolTip(description)
        self.setStatusTip(description)

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+Shift+F'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(self.clicked)
        shortcut.activated.connect(self.repaint)

    def pixmap(self, c):
        return ImageCache.get_rsc_pixmap(u'favourite', c, common.INLINE_ICON_SIZE)

    def state(self):
        val = self.current().model().filterFlag(common.MarkedAsFavourite)
        return val

    @QtCore.Slot()
    def action(self):
        val = self.current().model().filterFlag(common.MarkedAsFavourite)
        self.current().model().filterFlagChanged.emit(
            common.MarkedAsFavourite, not val)

    def repaint(self):
        super(ToggleFavouriteButton, self).repaint()
        if self._parent.currentIndex() < 3:
            self.show()
        else:
            self.hide()


class CollapseSequenceMenu(BaseContextMenu):
    def __init__(self, parent=None):
        super(CollapseSequenceMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_collapse_sequence_menu()


class AddButton(ControlButton):
    """The buttons responsible for adding new items.

    The functionality differs based on the currently selected tab:
    For bookmarks the user will be prompted with the ``AddBookmarksWidget``,
    for assets, a new asset will be created, and for files a new template file
    can be added.

    """

    def __init__(self, parent=None):
        super(AddButton, self).__init__(parent=parent)
        description = u'Ctrl+N  |  Adds a new item'
        self.setToolTip(description)
        self.setStatusTip(description)

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+N'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(self.clicked)
        shortcut.activated.connect(self.repaint)

    def pixmap(self, c):
        return ImageCache.get_rsc_pixmap(u'todo_add', c, common.INLINE_ICON_SIZE)

    def enterEvent(self, event):
        if self._parent.currentIndex() == 0:
            self.setStatusTip(u'Click to add a new Bookmark')
        if self._parent.currentIndex() == 2:
            self.setStatusTip(
                u'Click to add a new placeholder file. This can be used as a file-name template.')
        super(AddButton, self).enterEvent(event)

    def state(self):
        if self._parent.currentIndex() == 0:
            return True
        if self._parent.currentIndex() == 1:
            if self._parent.widget(0).model().sourceModel().active_index().isValid():
                return True
            return False
        if self._parent.currentIndex() == 2:
            return True
        return False

    @QtCore.Slot()
    def action(self):
        """Action to take when the plus icon is clicked.

        Note:
            Adding assets is not yet implemented. I'll work this out for a future
            release.

        """
        # Bookmark
        if self._parent.currentIndex() == 0:
            self.current().show_add_bookmark_widget()
            return

        # Asset
        if self._parent.currentIndex() == 1:
            from gwbrowser.addassetwidget import AddAssetWidget

            view = self._parent.widget(0)
            model = view.model().sourceModel()
            bookmark = model.active_index()
            if not bookmark.isValid():
                return

            bookmark = bookmark.data(common.ParentRole)
            bookmark = u'/'.join(bookmark)
            widget = AddAssetWidget(bookmark, parent=None)
            pos = self.window().rect().center()
            pos = self.window().mapToGlobal(pos)
            widget.move(
                pos.x() - (widget.width() / 2),
                pos.y() - (widget.height() / 2),
            )

            cwidget = self.parent().parent().stackedwidget.currentWidget()
            cwidget.disabled_overlay_widget.show()
            widget.exec_()

            if not widget.last_asset_added:
                cwidget.disabled_overlay_widget.hide()
                return

            model.modelDataResetRequested.emit()
            view = self._parent.widget(1)
            for n in xrange(view.model().rowCount()):
                index = view.model().index(n, 0)
                if index.data(QtCore.Qt.DisplayRole).lower() == widget.last_asset_added.lower():
                    view.selectionModel().setCurrentIndex(
                        index,
                        QtCore.QItemSelectionModel.ClearAndSelect
                    )
                    view.scrollTo(index)
                    break

            cwidget.disabled_overlay_widget.hide()
            return

        # This will open the Saver to save a new file
        if self._parent.currentIndex() == 2:
            import gwbrowser.saver as saver

            index = self._parent.currentWidget().selectionModel().currentIndex()
            if index.isValid():
                if not index.data(common.FileInfoLoaded):
                    return

            bookmark_model = BookmarksModel()
            asset_model = AssetModel()

            extension = u'ext'  # This is a generic extension that can be overriden
            currentfile = None
            data_key = self.current().model().sourceModel().data_key()
            subfolder = data_key if data_key else u'/'

            if index.isValid():
                # When there is a file selected, we will check if it is a sequence
                # increment the version number if it is.
                iscollapsed = common.is_collapsed(
                    index.data(QtCore.Qt.StatusTipRole))
                if iscollapsed:
                    # Replacing the frame-number with placeholder characters
                    currentfile = iscollapsed.expand(ur'\1{}\3')
                    currentfile = currentfile.format(
                        u'#' * len(index.data(common.FramesRole)[-1]))
                else:
                    # Getting the last frame of the sequence
                    currentfile = common.get_sequence_endpath(
                        index.data(QtCore.Qt.StatusTipRole))
                extension = currentfile.split(u'.').pop()

            # If both the currentfile and the data_key are valid we'll set
            # the default location to be the subfolder of the current file.
            if currentfile and data_key:
                # Removing the parentpath
                server, job, root, asset, _, _ = index.data(common.ParentRole)
                parentpath = u'/'.join((server, job, root, asset))
                subfolder = index.data(QtCore.Qt.StatusTipRole)
                subfolder = QtCore.QFileInfo(subfolder)
                subfolder = subfolder.dir().path()
                subfolder = subfolder.replace(parentpath, '')
            else:
                subfolder = u'{}/{}'.format(data_key, subfolder)

            subfolder = subfolder.strip(u'/')
            sys.stdout.write(subfolder)

            widget = saver.SaverWidget(
                bookmark_model,
                asset_model,
                extension,
                currentfile=currentfile
            )

            widget.finished.connect(bookmark_model.deleteLater)
            widget.finished.connect(asset_model.deleteLater)
            widget.finished.connect(widget.deleteLater)

            @QtCore.Slot(unicode)
            def fileSaveRequested(path):
                f = QtCore.QFile(path)
                if not f.exists():
                    f.open(QtCore.QIODevice.ReadWrite)
                    f.close()

                path = QtCore.QDir.toNativeSeparators(path)
                QtGui.QClipboard().setText(path)
                common.reveal(path)

            @QtCore.Slot(tuple)
            def fileDescriptionAdded(args):
                """Slot responsible for saving the description"""
                server, job, root, filepath, description = args
                settings = Settings.AssetSettings(
                    QtCore.QModelIndex(), args=(server, job, root, filepath))
                settings.setValue(u'config/description', description)

            @QtCore.Slot(tuple)
            def fileThumbnailAdded(args):
                server, job, root, filepath, image = args
                settings = Settings.AssetSettings(
                    QtCore.QModelIndex(), args=(server, job, root, filepath))
                if not image.isNull():
                    image.save(settings.thumbnail_path())

                fileswidget = self.parent().parent().findChild(FilesWidget)
                sizehint = fileswidget.itemDelegate().sizeHint(None, None)
                height = sizehint.height() - 2
                ImageCache.get(settings.thumbnail_path(),
                               height, overwrite=True)

                self.parent().parent().findChild(FilesWidget).model(
                ).sourceModel().modelDataResetRequested.emit()

            widget.fileSaveRequested.connect(fileSaveRequested)
            widget.fileDescriptionAdded.connect(fileDescriptionAdded)
            widget.fileThumbnailAdded.connect(fileThumbnailAdded)
            widget.exec_()

    def repaint(self):
        """The button is only visible when showing bookmarks or files."""
        super(AddButton, self).repaint()
        if self._parent.currentIndex() in (0, 1, 2):
            self.show()
        else:
            self.hide()


class GenerateThumbnailsButton(ControlButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(GenerateThumbnailsButton, self).__init__(parent=parent)
        description = u'Ctrl+M  |  Toggle thumbnail generation. If experiencing performance issues, turn this off!'
        self.setToolTip(description)
        self.setStatusTip(description)

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+M'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(self.clicked)
        shortcut.activated.connect(self.repaint)

    def pixmap(self, c):
        return ImageCache.get_rsc_pixmap(u'pick_thumbnail', c, common.INLINE_ICON_SIZE)

    def state(self):
        """The state of the auto-thumbnails"""
        if self._parent.currentIndex() < 2:
            return False
        model = self._parent.currentWidget().model().sourceModel()
        return model.generate_thumbnails

    @QtCore.Slot()
    def action(self):
        """Toggles thumbnail generation."""
        model = self._parent.currentWidget().model().sourceModel()
        val = model.generate_thumbnails

        cls = model.__class__.__name__
        local_settings.setValue(
            u'widget/{}/generate_thumbnails'.format(cls), not val)
        if not val == False:
            ImageCacheWorker.reset_queue()
        model.generate_thumbnails = not val
        self.repaint()

    def repaint(self):
        """Will only show for favourite and file items."""
        super(GenerateThumbnailsButton, self).repaint()
        if self._parent.currentIndex() >= 2:
            self.show()
        else:
            self.hide()


class PaintedTextButton(ClickableLabel):
    """Baseclass for text-based control buttons."""
    message = QtCore.Signal(unicode)

    def __init__(self, height=common.CONTROL_HEIGHT, parent=None):
        super(PaintedTextButton, self).__init__(parent=parent)
        self._parent = None
        self.index = 0

        self.font = QtGui.QFont(common.PrimaryFont)
        self.font.setPointSize(self.font.pointSize() + 1)

        self.setMouseTracking(True)
        self.setStatusTip(u'')
        self.setFixedHeight(height)

    def set_parent(self, widget):
        self._parent = widget

    def set_text(self, text):
        """Sets the text and the width for  the ``FilesTabButton``."""
        text = text if text else u'Files'
        self.setText(text.title())

        metrics = QtGui.QFontMetrics(self.font)
        width = metrics.width(self.text()) + (common.INDICATOR_WIDTH * 2)
        self.setFixedWidth(width)

    def enterEvent(self, event):
        """Emitting the statustip for the task bar."""
        self.message.emit(self.statusTip())
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def paintEvent(self, event):
        """The control button's paint method - shows the the set text and
        an underline if the tab is active."""
        if not self._parent:
            return

        rect = QtCore.QRect(self.rect())
        rect.setLeft(rect.left() + common.INDICATOR_WIDTH)

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        option = QtWidgets.QStyleOptionButton()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        if self._parent.currentIndex() == self.index:
            color = common.TEXT_SELECTED if hover else common.TEXT
        else:
            color = common.TEXT_SELECTED if hover else common.SECONDARY_TEXT

        common.draw_aliased_text(
            painter,
            self.font,
            rect,
            self.text(),
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            color
        )

        if self._parent.currentIndex() == self.index:
            metrics = QtGui.QFontMetrics(self.font)
            center = rect.center()
            rect.setHeight(2)
            rect.moveCenter(center)
            rect.moveTop(rect.top() + (metrics.height() / 2) + 3)
            rect.setWidth(metrics.width(self.text()))
            painter.setBrush(color)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRect(rect)
        painter.end()


class BookmarksTabButton(PaintedTextButton):
    """The button responsible for revealing the ``BookmarksWidget``"""

    def __init__(self, parent=None):
        super(BookmarksTabButton, self).__init__(parent=parent)
        self.index = 0
        self.set_text(u'Bookmarks')
        self.setStatusTip(u'Ctrl+1 | Click to see the list of added bookmarks')

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+1'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(self.clicked)
        shortcut.activated.connect(self.repaint)


class AssetsTabButton(PaintedTextButton):
    """The button responsible for revealing the ``AssetsWidget``"""

    def __init__(self, parent=None):
        super(AssetsTabButton, self).__init__(parent=parent)
        self.index = 1
        self.set_text(u'Assets')
        self.setStatusTip(
            u'Ctrl+2  |  Click to see the list of available assets')

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+2'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(self.clicked)
        shortcut.activated.connect(self.repaint)


class FilesTabButton(PaintedTextButton):
    """The buttons responsible for swtiching the the FilesWidget and showing
    the switch to change the data-key."""

    def __init__(self, parent=None):
        self._view = None
        super(FilesTabButton, self).__init__(parent=parent)
        self.index = 2
        self.set_text(u'Files')
        self.setStatusTip(
            u'Ctrl+3  |  Click to see or change the current task folder')
        self.clicked.connect(self.show_view, type=QtCore.Qt.QueuedConnection)

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+3'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(self.clicked)
        shortcut.activated.connect(self.repaint)

    def paintEvent(self, event):
        """Indicating the visibility of the DataKeyView."""
        if not self._view.isHidden():
            painter = QtGui.QPainter()
            painter.begin(self)
            rect = self.rect()
            rect.setTop(rect.top() + 4)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.SECONDARY_BACKGROUND)

            rect.setTop(rect.top() + 6)
            painter.drawRoundedRect(rect, 6, 6)

            rect.setTop(rect.top() + 6)
            painter.drawRect(rect)

            common.draw_aliased_text(
                painter,
                common.PrimaryFont,
                rect,
                u'...',
                QtCore.Qt.AlignCenter,
                common.TEXT
            )
            painter.end()
        else:
            super(FilesTabButton, self).paintEvent(event)

    def view(self):
        return self._view

    def set_view(self, widget):
        self._view = widget

    @QtCore.Slot()
    def show_view(self):
        """Shows the ``DataKeyView`` widget for browsing."""
        if not self.view():
            return

        if self.view().model().rowCount() == 0:
            return

        if not self.view().isHidden():
            self.view().hide()
            return

        stackedwidget = self.view().altparent.parent().stackedwidget
        if stackedwidget.currentIndex() != 2:
            return  # We're not showing the widget when files are not tyhe visible list

        geo = self.view().parent().geometry()
        self.view().setGeometry(geo)
        self.view().move(0, 0)
        self.view().show()
        self.view().setFocus(QtCore.Qt.PopupFocusReason)
        self.view().viewport().setFocus(QtCore.Qt.PopupFocusReason)

        key = stackedwidget.currentWidget().model().sourceModel().data_key()
        if not key:
            return

        for n in xrange(self.view().model().rowCount()):
            index = self.view().model().index(n, 0)
            if key.lower() == index.data(QtCore.Qt.DisplayRole).lower():
                self.view().selectionModel().setCurrentIndex(
                    index, QtCore.QItemSelectionModel.ClearAndSelect)
                self.view().scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
                break


class FavouritesTabButton(PaintedTextButton):
    """Drop-down widget to switch between the list"""

    def __init__(self, parent=None):
        super(FavouritesTabButton, self).__init__(parent=parent)
        self.index = 3
        self.set_text(u'My favourites')
        self.setStatusTip(u'Ctrl+4  |  Click to see your saved favourites')

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+4'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(self.clicked)
        shortcut.activated.connect(self.repaint)


class ListControlWidget(QtWidgets.QWidget):
    """The bar above the list to control the mode, filters and sorting."""

    textChanged = QtCore.Signal(unicode)
    listChanged = QtCore.Signal(int)
    dataKeyChanged = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(ListControlWidget, self).__init__(parent=parent)
        self._createUI()
        self._connectSignals()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(common.INDICATOR_WIDTH * 2)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedHeight(common.CONTROL_HEIGHT)

        # Control view/model/button
        self._bookmarksbutton = BookmarksTabButton(parent=self)
        self._assetsbutton = AssetsTabButton(parent=self)
        self._filesbutton = FilesTabButton(parent=self)

        self._controlview = DataKeyView(
            parent=self.parent().fileswidget, altparent=self)
        self._controlview.setHidden(True)

        self._filesbutton.set_view(self._controlview)
        self._favouritesbutton = FavouritesTabButton(parent=self)

        self._addbutton = AddButton(parent=self)
        self._generatethumbnailsbutton = GenerateThumbnailsButton(parent=self)
        self._todobutton = TodoButton(parent=self)
        self._filterbutton = FilterButton(parent=self)
        self._collapsebutton = CollapseSequenceButton(parent=self)
        self._archivedbutton = ToggleArchivedButton(parent=self)
        self._favouritebutton = ToggleFavouriteButton(parent=self)
        self._slackbutton = SlackButton(parent=self)
        self._togglebuttonsbutton = ToggleButtons(parent=self)

        self.layout().addSpacing(common.INDICATOR_WIDTH)
        self.layout().addWidget(self._bookmarksbutton)
        self.layout().addWidget(self._assetsbutton)
        self.layout().addWidget(self._filesbutton)
        self.layout().addWidget(self._favouritesbutton)
        self.layout().addStretch()
        self.layout().addWidget(self._togglebuttonsbutton)
        self.layout().addWidget(self._addbutton)
        self.layout().addWidget(self._generatethumbnailsbutton)
        self.layout().addWidget(self._todobutton)
        self.layout().addWidget(self._filterbutton)
        self.layout().addWidget(self._collapsebutton)
        self.layout().addWidget(self._archivedbutton)
        self.layout().addWidget(self._favouritebutton)
        self.layout().addWidget(self._slackbutton)
        self.layout().addSpacing(common.INDICATOR_WIDTH * 2)

    @QtCore.Slot(QtCore.QModelIndex)
    def signal_dispatcher(self, index):
        self.listChanged.emit(2)
        self.dataKeyChanged.emit(index.data(QtCore.Qt.DisplayRole))
        self.textChanged.emit(index.data(QtCore.Qt.DisplayRole))

    def _connectSignals(self):
        pass

    def control_view(self):
        return self._controlview

    def control_button(self):
        return self.findChild(FilesTabButton)
