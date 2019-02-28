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
from browser.baselistwidget import StackedWidget
from browser.bookmarkswidget import BookmarksWidget
from browser.assetwidget import AssetWidget
from browser.fileswidget import FilesWidget
from browser.listcontrolwidget import ListControlWidget
from browser.listcontrolwidget import ListControlDropdown
from browser.listcontrolwidget import FilterButton

from browser.editors import ClickableLabel
from browser.imagecache import ImageCache

from browser.settings import local_settings, Active, active_monitor


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

        idx = local_settings.value(u'widget/mode')
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
        # Filter proxy model
        def _set_mode():
            self.listcontrolwidget.setCurrentMode(self.stackedwidget.currentIndex())
        self.fileswidget.model().filterModeChanged.connect(_set_mode)
        self.assetswidget.model().filterModeChanged.connect(_set_mode)
        self.bookmarkswidget.model().filterModeChanged.connect(_set_mode)

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

        self.bookmarkswidget.model().sourceModel(
        ).activeBookmarkChanged.connect(
            lambda: self.listcontrolwidget.modeChanged.emit(1))

        active_monitor.activeBookmarkChanged.connect(
            self.bookmarkswidget.refresh)

        # Asset
        # A new asset has been activated and all the data has to be re-initialized
        self.assetswidget.model().sourceModel().activeAssetChanged.connect(
            self.fileswidget.model().sourceModel().set_asset)
        dropdown = self.listcontrolwidget.findChild(ListControlDropdown)
        self.assetswidget.model().sourceModel().activeAssetChanged.connect(
            dropdown.model().activeAssetChanged)
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
