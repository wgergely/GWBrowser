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
import sys
from PySide2 import QtWidgets, QtGui, QtCore

import browser.common as common
from browser.baselistwidget import StackedWidget
from browser.bookmarkswidget import BookmarksWidget
from browser.assetwidget import AssetWidget
from browser.fileswidget import FilesWidget
from browser.listcontrolwidget import ListControlWidget
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
        self.listcontrolwidget = None
        self.assetswidget = None
        self.fileswidget = None

        active_monitor.timer.start()

        self._createUI()
        self._connectSignals()

        # app = QtWidgets.QApplication.instance()
        # app.processEvents()
        # self.bookmarkswidget.model().sourceModel().modelDataResetRequested.emit()

        # self._add_shortcuts()



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
        f.model().sourceModel().dataKeyChanged.connect(lambda x: l.model().modelDataResetRequested.emit())

        # Listcontrol signals
        l.clicked.connect(lambda x: lb.set_text(x.data(QtCore.Qt.DisplayRole)))

        # Statusbar
        b.entered.connect(self.entered)
        a.entered.connect(self.entered)
        f.entered.connect(self.entered)
        l.entered.connect(self.entered)

    # def _add_shortcuts(self):
    #     # Show bookmarks shortcut
    #     shortcut = QtWidgets.QShortcut(
    #         QtGui.QKeySequence(u'Alt+1'), self)
    #     shortcut.setAutoRepeat(False)
    #     shortcut.setContext(QtCore.Qt.WindowShortcut)
    #     shortcut.activated.connect(
    #         lambda: self.listcontrolwidget.listChanged.emit(0))
    #     # Show asset shortcut
    #     shortcut = QtWidgets.QShortcut(
    #         QtGui.QKeySequence(u'Alt+2'), self)
    #     shortcut.setAutoRepeat(False)
    #     shortcut.setContext(QtCore.Qt.WindowShortcut)
    #     shortcut.activated.connect(
    #         lambda: self.listcontrolwidget.listChanged.emit(1))
    #     # Show files shortcut
    #     shortcut = QtWidgets.QShortcut(
    #         QtGui.QKeySequence(u'Alt+3'), self)
    #     shortcut.setAutoRepeat(False)
    #     shortcut.setContext(QtCore.Qt.WindowShortcut)
    #     shortcut.activated.connect(
    #         lambda: self.listcontrolwidget.listChanged.emit(2))
    #     # Search
    #     shortcut = QtWidgets.QShortcut(
    #         QtGui.QKeySequence(u'Alt+F'), self)
    #     shortcut.setAutoRepeat(False)
    #     shortcut.setContext(QtCore.Qt.WindowShortcut)
    #
    #     filterbutton = self.listcontrolwidget.findChild(FilterButton)
    #     shortcut.activated.connect(filterbutton.clicked)


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
