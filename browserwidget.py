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
from browser.listcontrolwidget import FilterButton
from browser.imagecache import ImageCache
from browser.settings import local_settings, Active, active_monitor
import browser.settings as Settings


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
        self._initialized = False
        self.stackedwidget = None
        self.bookmarkswidget = None
        self.listcontrolwidget = None
        self.assetswidget = None
        self.fileswidget = None

        Active.paths()
        active_monitor.timer.start()

        self._createUI()
        self._connectSignals()

        self._add_shortcuts()

    def initialize(self):
        """Applying the saved values and initiating the model datas."""
        # Switching stacked widget to saved index...
        idx = local_settings.value(u'widget/mode')
        idx = 0 if idx is None else idx
        self.listcontrolwidget.control_view().listChanged.emit(idx)
        if idx == 0:
            index = self.listcontrolwidget.control_view().model().index(0, 0)
            text = index.data(QtCore.Qt.DisplayRole)
        if idx == 1:
            index = self.listcontrolwidget.control_view().model().index(1, 0)
            text = index.data(QtCore.Qt.DisplayRole)
        if idx == 2:
            text = self.fileswidget.model().sourceModel().data_key()
        self.listcontrolwidget.control_view().textChanged.emit(text)

        # Proxy model
        b = self.bookmarkswidget
        a = self.assetswidget
        f = self.fileswidget

        b.model().filterTextChanged.emit(b.model().get_filtertext())
        a.model().filterTextChanged.emit(a.model().get_filtertext())
        f.model().filterTextChanged.emit(f.model().get_filtertext())

        b.model().filterFlagChanged.emit(Settings.MarkedAsActive, b.model().get_filter_flag_value(Settings.MarkedAsActive))
        b.model().filterFlagChanged.emit(Settings.MarkedAsArchived, b.model().get_filter_flag_value(Settings.MarkedAsArchived))
        b.model().filterFlagChanged.emit(Settings.MarkedAsFavourite, b.model().get_filter_flag_value(Settings.MarkedAsFavourite))
        #
        a.model().filterFlagChanged.emit(Settings.MarkedAsActive, a.model().get_filter_flag_value(Settings.MarkedAsActive))
        a.model().filterFlagChanged.emit(Settings.MarkedAsArchived, a.model().get_filter_flag_value(Settings.MarkedAsArchived))
        a.model().filterFlagChanged.emit(Settings.MarkedAsFavourite, a.model().get_filter_flag_value(Settings.MarkedAsFavourite))
        #
        f.model().filterFlagChanged.emit(Settings.MarkedAsActive, f.model().get_filter_flag_value(Settings.MarkedAsActive))
        f.model().filterFlagChanged.emit(Settings.MarkedAsArchived, f.model().get_filter_flag_value(Settings.MarkedAsArchived))
        f.model().filterFlagChanged.emit(Settings.MarkedAsFavourite, f.model().get_filter_flag_value(Settings.MarkedAsFavourite))

        b.model().sortingChanged.emit(
            b.model().sortRole(),
            b.model().get_sortorder())
        a.model().sortingChanged.emit(
            b.model().sortRole(),
            b.model().get_sortorder())
        f.model().sortingChanged.emit(
            b.model().sortRole(),
            b.model().get_sortorder())

        # self.stackedwidget.currentChanged.emit(self.stackedwidget.currentIndex())

        # Source model data
        timer = QtCore.QTimer(parent=self)
        timer.setSingleShot(True)
        timer.setInterval(1000)
        timer.timeout.connect(b.model().sourceModel().modelDataResetRequested.emit)
        timer.timeout.connect(timer.deleteLater)
        timer.start()
        # b.model().sourceModel().modelDataResetRequested.emit()

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

        self.bookmarkswidget = BookmarksWidget(parent=self)
        self.assetswidget = AssetWidget(parent=self)
        self.fileswidget = FilesWidget(parent=self)

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
        self.statusbar.addPermanentWidget(grip)

        grip = self.statusbar.findChild(QtWidgets.QSizeGrip)
        grip.hide()

        self.layout().addWidget(self.listcontrolwidget)
        self.layout().addWidget(self.stackedwidget)
        self.layout().addWidget(self.statusbar)

    def _connectSignals(self):
        """This is where the bulk of the model, view and control widget
        signals and slots are connected. I tried coding the widgets in a
        manner that they can all operate independently and the signal/slot
        connections are not hard-coded.

        """
        b = self.bookmarkswidget
        a = self.assetswidget
        f = self.fileswidget
        lc = self.listcontrolwidget
        l = lc.control_view()
        lb = lc.control_button()
        s = self.stackedwidget

        # Signal/slot connections for the primary bookmark/asset and filemodels
        b.model().sourceModel().modelReset.connect(
            lambda: a.model().sourceModel().set_active(b.model().sourceModel().active_index()))
        b.model().sourceModel().modelReset.connect(
            a.model().sourceModel().modelDataResetRequested.emit)

        b.model().sourceModel().activeChanged.connect(
            a.model().sourceModel().set_active)
        b.model().sourceModel().activeChanged.connect(
            lambda x: a.model().sourceModel().modelDataResetRequested.emit())

        a.model().sourceModel().modelReset.connect(
            lambda: f.model().sourceModel().set_active(a.model().sourceModel().active_index()))
        a.model().sourceModel().modelReset.connect(
            f.model().sourceModel().modelDataResetRequested.emit)
        a.model().sourceModel().modelReset.connect(f.model().invalidate)

        a.model().sourceModel().activeChanged.connect(
            f.model().sourceModel().set_active)
        a.model().sourceModel().activeChanged.connect(
            lambda x: f.model().sourceModel().modelDataResetRequested.emit())

        # Bookmark/Asset/FileModel/View  ->  ListControlModel/View
        # These connections are responsible for keeping the ListControlModel updated
        # when navigating the list widgets.
        b.model().sourceModel().modelReset.connect(
            l.model().modelDataResetRequested.emit)

        a.model().sourceModel().modelReset.connect(
            lambda: l.model().set_active(a.model().sourceModel().active_index()))
        a.model().sourceModel().modelReset.connect(
            l.model().modelDataResetRequested.emit)

        a.model().sourceModel().activeChanged.connect(
            l.model().set_active)
        a.model().sourceModel().activeChanged.connect(
            lambda x: l.model().modelDataResetRequested.emit())

        b.model().sourceModel().modelReset.connect(
            lambda: l.model().set_bookmark(b.model().sourceModel().active_index()))

        b.model().sourceModel().activeChanged.connect(l.model().set_bookmark)
        f.model().sourceModel().dataKeyChanged.connect(l.model().set_data_key)
        f.model().sourceModel().modelReset.connect(
            lambda: l.model().set_data_key(f.model().sourceModel().data_key()))
        f.model().sourceModel().dataTypeChanged.connect(l.model().set_data_type)
        f.model().sourceModel().dataKeyChanged.connect(
            lambda x: l.model().modelDataResetRequested.emit())

        # Bookmark/Asset/FileModel/View  <-  ListControlModel/View
        # These are the signals responsible for changing the active items & data keys.
        l.listChanged.connect(s.setCurrentIndex)
        l.dataKeyChanged.connect(f.model().sourceModel().dataKeyChanged)
        l.textChanged.connect(lb.set_text)
        f.model().sourceModel().dataKeyChanged.connect(l.textChanged.emit)
        l.listChanged.connect(lambda i: l.textChanged.emit(
            u'Bookmarks' if i == 0 else (
                u'Assets' if i == 1 else f.model().sourceModel().data_key())))

        # Stacked widget navigation
        b.activated.connect(lambda: l.listChanged.emit(1))
        b.activated.connect(lambda: l.textChanged.emit(u'Assets'))
        a.activated.connect(lambda: l.listChanged.emit(2))
        a.activated.connect(lambda: l.textChanged.emit(f.model().sourceModel().data_key()))

        # Statusbar
        b.entered.connect(self.entered)
        a.entered.connect(self.entered)
        f.entered.connect(self.entered)
        l.entered.connect(self.entered)

        self.listcontrolwidget._archivedbutton.set_parent(self.stackedwidget)

        self.listcontrolwidget._todobutton.set_parent(self.stackedwidget)
        self.listcontrolwidget._filterbutton.set_parent(self.stackedwidget)
        self.listcontrolwidget._activebutton.set_parent(self.stackedwidget)
        self.listcontrolwidget._collapsebutton.set_parent(self.stackedwidget)
        self.listcontrolwidget._archivedbutton.set_parent(self.stackedwidget)
        self.listcontrolwidget._favouritebutton.set_parent(self.stackedwidget)

        # Updates the list-control buttons when changing lists
        l.listChanged.connect(lambda x: self.listcontrolwidget._todobutton.repaint())
        l.listChanged.connect(lambda x: self.listcontrolwidget._filterbutton.repaint())
        l.listChanged.connect(lambda x: self.listcontrolwidget._activebutton.repaint())
        l.listChanged.connect(lambda x: self.listcontrolwidget._collapsebutton.repaint())
        l.listChanged.connect(lambda x: self.listcontrolwidget._archivedbutton.repaint())
        l.listChanged.connect(lambda x: self.listcontrolwidget._favouritebutton.repaint())

    def _add_shortcuts(self):
        for n in xrange(3):
            shortcut = QtWidgets.QShortcut(
                QtGui.QKeySequence(u'Alt+{}'.format(n + 1)), self)
            shortcut.setAutoRepeat(False)
            shortcut.setContext(QtCore.Qt.WindowShortcut)
            shortcut.activated.connect(
                functools.partial(self.listcontrolwidget.control_view().listChanged.emit, n))

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Alt+F'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.WindowShortcut)

        filterbutton = self.listcontrolwidget.findChild(FilterButton)
        shortcut.activated.connect(filterbutton.clicked)

    def entered(self, index):
        """Custom itemEntered signal."""
        message = index.data(QtCore.Qt.StatusTipRole)
        self.statusbar.showMessage(message, timeout=1500)

    def activate_widget(self, idx):
        """Method to change between views."""
        self.stackedwidget.setCurrentIndex(idx)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH, common.HEIGHT)

    def showEvent(self, event):
        if self._initialized is False:
            self.initialize()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = BrowserWidget()
    widget.show()
    app.exec_()
