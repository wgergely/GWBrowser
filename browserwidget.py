# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903, C0330

"""``BrowserWidget`` is the plug-in's main widget.
When launched from within Maya it inherints from MayaQWidgetDockableMixin baseclass,
otherwise MayaQWidgetDockableMixin is replaced with a ``common.LocalContext``, a dummy class.

Example:

.. code-block:: python
    :linenos:

    from browser.toolbar import BrowserWidget
    widget = BrowserWidget()
    widget.show()

The asset and the file lists are collected by the ``collector.AssetCollector``
and ```collector.FilesCollector`` classes. The gathered files then are displayed
in the ``listwidgets.AssetsListWidget`` and ``listwidgets.FilesListWidget`` items.

"""

import functools
from PySide2 import QtWidgets, QtGui, QtCore

import browser.common as common
from browser.baselistwidget import BaseContextMenu
from browser.baselistwidget import contextmenu
from browser.baselistwidget import StackedWidget
from browser.bookmarkswidget import BookmarksWidget
from browser.assetwidget import AssetWidget
from browser.fileswidget import FilesWidget
from browser.listcontrolwidget import ListControlWidget
from browser.listcontrolwidget import FilterButton
from browser.listcontrolwidget import LocationsButton

from browser.editors import ClickableLabel
from browser.imagecache import ImageCache

from browser.settings import local_settings, Active, active_monitor


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
        active_paths = Active.get_active_paths()
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


class SizeGrip(QtWidgets.QSizeGrip):
    def __init__(self, parent):
        super(SizeGrip, self).__init__(parent)
        self.setFixedWidth(common.INLINE_ICON_SIZE / 2)
        self.setFixedHeight(common.INLINE_ICON_SIZE / 2)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        pixmap = ImageCache.get_rsc_pixmap(
            'resize', common.TEXT, common.INLINE_ICON_SIZE / 2)
        painter.setOpacity(0.1)
        painter.drawPixmap(self.rect(), pixmap)
        painter.end()


class RefreshButton(ClickableLabel):
    """Small widget to embed into the context to toggle the BrowserWidget's visibility."""

    def __init__(self, parent=None):
        super(RefreshButton, self).__init__(parent=parent)
        self.context_menu_cls = BrowserButtonContextMenu
        self.setFixedWidth(common.INLINE_ICON_SIZE / 2)
        self.setFixedHeight(common.INLINE_ICON_SIZE / 2)

        self.setToolTip(
            'Files have changed and an update is necessary. Click to refresh.')

        self.needs_update = False
        self.clicked.connect(self.do_refresh)

    def do_refresh(self):
        if not self.needs_update:
            return
        self.parent().parent().stackedwidget.currentWidget().refresh()
        self.needs_update = False
        self.repaint()

    def check_refresh_requests(self, location):
        """Will check if the model needs a refresh."""
        if self.parent().parent().stackedwidget.currentIndex() != 2:
            return

        widget = self.parent().parent().stackedwidget.currentWidget()
        model = widget.model().sourceModel()

        if not model.rowCount():
            return

        # Check the currently visible model has this path inside
        # (might be a different location, in this case we'll ignore the request)
        # We'll check against all changes and their timestamp
        for n in xrange(model.rowCount()):
            index = model.index(n, 0, parent=QtCore.QModelIndex())
            file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
            if file_info.path() in model._last_changed:
                if model._last_refreshed[location] < model._last_changed[file_info.path()]:
                    self.needs_update = True
                    self.repaint()
                    return

        self.needs_update = False
        self.repaint()

    def paintEvent(self, event):
        if not self.needs_update:
            return
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(250, 100, 0))
        painter.drawRoundedRect(
            self.rect(), self.width() / 2, self.width() / 2)


class BrowserButton(ClickableLabel):
    """Small widget to embed into the context to toggle the BrowserWidget's visibility."""

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
            QtCore.Qt.Widget |
            QtCore.Qt.FramelessWindowHint
        )
        pixmap = ImageCache.get_rsc_pixmap(
            u'custom', None, height)
        self.setPixmap(pixmap)

    def set_size(self, size):
        self.setFixedWidth(int(size))
        self.setFixedHeight(int(size))
        pixmap = ImageCache.get_rsc_pixmap(
            u'custom', None, int(size))
        self.setPixmap(pixmap)

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()

    def paintEvent(self, event):
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




class BrowserWidget(QtWidgets.QWidget):
    """Main widget to browse pipline data."""

    def __init__(self, parent=None):
        super(BrowserWidget, self).__init__(parent=parent)
        self.setObjectName(u'BrowserWidget')
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint
        )

        pixmap = ImageCache.get_rsc_pixmap(u'custom', None, 64)
        self.setWindowIcon(QtGui.QIcon(pixmap))
        self._contextMenu = None

        self.stackedwidget = None
        self.bookmarkswidget = None
        self.assetswidget = None
        self.fileswidget = None

        # Applying the initial config settings.
        active_paths = Active.get_active_paths()
        self.bookmarkswidget = BookmarksWidget()
        self.assetswidget = AssetWidget((
            active_paths[u'server'],
            active_paths[u'job'],
            active_paths[u'root']
        ))
        self.fileswidget = FilesWidget((
            active_paths[u'server'],
            active_paths[u'job'],
            active_paths[u'root'],
            active_paths[u'asset'])
        )

        # Create layout
        self._createUI()
        self._connectSignals()

        idx = local_settings.value(u'widget/current_index')
        idx = idx if idx else 0
        self.activate_widget(idx)

        # Let's start the monitor
        active_monitor.timer.start()

    def _createUI(self):
        common.set_custom_stylesheet(self)

        # Main layout
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred
        )

        self.stackedwidget = StackedWidget(parent=self)
        self.stackedwidget.setObjectName('browserStackedWidget')
        self.stackedwidget.addWidget(self.bookmarkswidget)
        self.stackedwidget.addWidget(self.assetswidget)
        self.stackedwidget.addWidget(self.fileswidget)

        self.listcontrolwidget = ListControlWidget(parent=self)

        self.statusbar = QtWidgets.QStatusBar()
        self.statusbar.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.statusbar.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.statusbar.setFixedHeight(common.ROW_BUTTONS_HEIGHT / 2.0)
        self.statusbar.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )
        self.statusbar.setSizeGripEnabled(False)

        grip = SizeGrip(self)
        self.statusbar.addPermanentWidget(RefreshButton(parent=self))
        self.statusbar.addPermanentWidget(grip)

        grip = self.statusbar.findChild(QtWidgets.QSizeGrip)
        grip.hide()

        self.layout().addWidget(self.listcontrolwidget)
        self.layout().addWidget(self.stackedwidget)
        self.layout().addWidget(self.statusbar)

    def _connectSignals(self):
        self.listcontrolwidget.modeChanged.connect(self.activate_widget)

        # Bookmark
        self.bookmarkswidget.model().sourceModel().activeBookmarkChanged.connect(
            self.assetswidget.model().sourceModel().set_bookmark)
        active_monitor.activeBookmarkChanged.connect(
            self.assetswidget.model().sourceModel().set_bookmark)

        filterbutton = self.listcontrolwidget.findChild(FilterButton)
        locationsbutton = self.listcontrolwidget.findChild(LocationsButton)

        def func(text): return locationsbutton.text.setText(text.title())
        self.fileswidget.model().sourceModel().activeLocationChanged.connect(func)
        # Filter proxy model
        def func(): return self.listcontrolwidget.setCurrentMode(
            self.stackedwidget.currentIndex())
        self.fileswidget.model().filterModeChanged.connect(func)
        self.assetswidget.model().filterModeChanged.connect(func)
        self.bookmarkswidget.model().filterModeChanged.connect(func)

        # Show bookmarks shortcut
        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Alt+1'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(
            lambda: self.listcontrolwidget.modeChanged.emit(0))
        # Show asset shortcut
        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Alt+2'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(
            lambda: self.listcontrolwidget.modeChanged.emit(1))
        # Show files shortcut
        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Alt+3'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(
            lambda: self.listcontrolwidget.modeChanged.emit(2))
        # Search
        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Alt+F'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(filterbutton.clicked)
        # Search
        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Alt+L'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)
        shortcut.activated.connect(locationsbutton.clicked)

        self.bookmarkswidget.model().sourceModel(
        ).activeBookmarkChanged.connect(
            lambda: self.listcontrolwidget.modeChanged.emit(1))

        active_monitor.activeBookmarkChanged.connect(
            self.bookmarkswidget.refresh)

        # Asset
        # A new asset has been activated and all the data has to be re-initialized
        self.assetswidget.model().sourceModel().activeAssetChanged.connect(
            self.fileswidget.model().sourceModel().set_asset)
        # First, clear the data
        self.assetswidget.model().sourceModel().modelDataResetRequested.connect(
            self.fileswidget.model().sourceModel().modelDataResetRequested.emit)
        # Re-populates the data for the current location
        self.assetswidget.model().sourceModel(
        ).modelDataResetRequested.connect(self.fileswidget.refresh)

        # Shows the FilesWidget
        self.assetswidget.model().sourceModel().activeAssetChanged.connect(
            lambda: self.listcontrolwidget.modeChanged.emit(2))
        # Updates the controls above the list

        active_monitor.activeAssetChanged.connect(self.assetswidget.refresh)
        active_monitor.activeAssetChanged.connect(
            self.fileswidget.model().sourceModel().set_asset)
        active_monitor.activeAssetChanged.connect(
            self.fileswidget.model().sourceModel().__resetdata__)
        active_monitor.activeAssetChanged.connect(self.fileswidget.refresh)

        # Statusbar
        self.bookmarkswidget.entered.connect(self.entered)
        self.assetswidget.entered.connect(self.entered)
        self.fileswidget.entered.connect(self.entered)

        self.fileswidget.model().sourceModel().activeLocationChanged.connect(
            lambda: self.listcontrolwidget.modeChanged.emit(2))
        self.fileswidget.model().sourceModel().grouppingChanged.connect(
            lambda: self.listcontrolwidget.modeChanged.emit(2))

        # file-monitor
        refreshbutton = self.findChild(RefreshButton)
        self.fileswidget.model().sourceModel().refreshRequested.connect(
            refreshbutton.check_refresh_requests)

        def func(idx):
            if idx != 2:
                return

            location = self.fileswidget.model().sourceModel().get_location()
            refreshbutton.check_refresh_requests(location)

        self.listcontrolwidget.modeChanged.connect(func)

    def entered(self, index):
        """Custom itemEntered signal."""
        message = index.data(QtCore.Qt.StatusTipRole)
        self.statusbar.showMessage(message, timeout=1500)

    def activate_widget(self, idx):
        """Method to change between views."""
        self.stackedwidget.setCurrentIndex(idx)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH, common.HEIGHT)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = BrowserWidget()
    widget.show()
    app.exec_()
