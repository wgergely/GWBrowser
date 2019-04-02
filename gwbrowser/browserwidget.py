# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903, C0330

"""``BrowserWidget`` is the plug-in's main widget.
When launched from within Maya it inherints from MayaQWidgetDockableMixin baseclass,
otherwise MayaQWidgetDockableMixin is replaced with a ``common.LocalContext``, a dummy class.

Example:

.. code-block:: python
    :linenos:

    from gwbrowser.toolbar import BrowserWidget
    widget = BrowserWidget()
    widget.show()

The asset and the file lists are collected by the ``collector.AssetCollector``
and ```collector.FilesCollector`` classes. The gathered files then are displayed
in the ``listwidgets.AssetsListWidget`` and ``listwidgets.FilesListWidget`` items.

"""
import functools
from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser.common as common
from gwbrowser.baselistwidget import StackedWidget
from gwbrowser.bookmarkswidget import BookmarksWidget
from gwbrowser.assetwidget import AssetWidget
from gwbrowser.fileswidget import FilesWidget
from gwbrowser.listcontrolwidget import ListControlWidget
from gwbrowser.listcontrolwidget import FilterButton
from gwbrowser.listcontrolwidget import Progresslabel
from gwbrowser.imagecache import ImageCache
from gwbrowser.settings import local_settings, Active, active_monitor
import gwbrowser.settings as Settings


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
    initialized = QtCore.Signal()

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

        self.settingstimer = QtCore.QTimer(parent=self)
        self.settingstimer.setInterval(1000)
        self.settingstimer.setSingleShot(False)
        self.settingstimer.setTimerType(QtCore.Qt.CoarseTimer)
        self.settingstimer.timeout.connect(active_monitor.check_state)

        self.initializer = QtCore.QTimer()
        self.initializer.setSingleShot(True)
        self.initializer.setInterval(200)
        self.initializer.timeout.connect(self.initialize)
        self.initializer.timeout.connect(self.settingstimer.start)
        self.initializer.timeout.connect(self.initializer.deleteLater)

        self.init_progress = u'Loading...'
        self.repaint()

    @QtCore.Slot()
    def initialize(self):
        """Applying the saved values and initiating the model datas."""
        if self._initialized:
            return

        self._createUI()
        self._connectSignals()
        self._add_shortcuts()

        Active.paths()

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

        b.model().filterTextChanged.emit(b.model().filterText())
        a.model().filterTextChanged.emit(a.model().filterText())
        f.model().filterTextChanged.emit(f.model().filterText())

        b.model().filterFlagChanged.emit(Settings.MarkedAsActive, b.model().filterFlag(Settings.MarkedAsActive))
        b.model().filterFlagChanged.emit(Settings.MarkedAsArchived, b.model().filterFlag(Settings.MarkedAsArchived))
        b.model().filterFlagChanged.emit(Settings.MarkedAsFavourite, b.model().filterFlag(Settings.MarkedAsFavourite))
        #
        a.model().filterFlagChanged.emit(Settings.MarkedAsActive, a.model().filterFlag(Settings.MarkedAsActive))
        a.model().filterFlagChanged.emit(Settings.MarkedAsArchived, a.model().filterFlag(Settings.MarkedAsArchived))
        a.model().filterFlagChanged.emit(Settings.MarkedAsFavourite, a.model().filterFlag(Settings.MarkedAsFavourite))
        #
        f.model().filterFlagChanged.emit(Settings.MarkedAsActive, f.model().filterFlag(Settings.MarkedAsActive))
        f.model().filterFlagChanged.emit(Settings.MarkedAsArchived, f.model().filterFlag(Settings.MarkedAsArchived))
        f.model().filterFlagChanged.emit(Settings.MarkedAsFavourite, f.model().filterFlag(Settings.MarkedAsFavourite))

        # Source model data
        timer = QtCore.QTimer(parent=self)
        timer.setSingleShot(True)
        timer.setInterval(1000)
        timer.timeout.connect(b.model().sourceModel().modelDataResetRequested)
        timer.timeout.connect(timer.deleteLater)
        timer.start()

        self._initialized = True
        self.initialized.emit()

    def _createUI(self):
        app = QtWidgets.QApplication.instance()
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

        self.init_progress = u'Creating bookmarks tab...'
        self.repaint()
        app.processEvents(flags=QtCore.QEventLoop.ExcludeUserInputEvents)

        self.bookmarkswidget = BookmarksWidget(parent=self)

        self.init_progress = u'Creating assets tab...'
        self.repaint()
        app.processEvents(flags=QtCore.QEventLoop.ExcludeUserInputEvents)

        self.assetswidget = AssetWidget(parent=self)

        self.init_progress = u'Creating files tab...'
        self.repaint()
        app.processEvents(flags=QtCore.QEventLoop.ExcludeUserInputEvents)

        self.fileswidget = FilesWidget(parent=self)
        self.stackedwidget.addWidget(self.bookmarkswidget)
        self.stackedwidget.addWidget(self.assetswidget)
        self.stackedwidget.addWidget(self.fileswidget)

        self.init_progress = u'Adding top bar...'
        self.repaint()
        app.processEvents(flags=QtCore.QEventLoop.ExcludeUserInputEvents)

        self.listcontrolwidget = ListControlWidget(parent=self)

        self.init_progress = u'Finishing...'
        self.repaint()
        app.processEvents(flags=QtCore.QEventLoop.ExcludeUserInputEvents)

        self.statusbar = QtWidgets.QStatusBar()
        self.statusbar.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.statusbar.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.statusbar.setFixedHeight(common.ROW_BUTTONS_HEIGHT / 2.0)
        self.statusbar.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )
        self.statusbar.setSizeGripEnabled(False)

        # Swapping the default grip with my custom one
        grip = self.statusbar.findChild(QtWidgets.QSizeGrip)
        if grip:
            grip.deleteLater()
        grip = SizeGrip(self)
        self.statusbar.addPermanentWidget(grip)

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
        m = self.listcontrolwidget.findChild(Progresslabel)

        # Signals responsible for saveing the activation changes
        b.model().sourceModel().activeChanged.connect(b.save_activated)
        a.model().sourceModel().activeChanged.connect(a.save_activated)
        f.model().sourceModel().activeChanged.connect(f.save_activated)

        # Signal/slot connections for the primary bookmark/asset and filemodels
        b.model().sourceModel().modelReset.connect(
            lambda: a.model().sourceModel().set_active(b.model().sourceModel().active_index()))
        b.model().sourceModel().modelReset.connect(
            a.model().sourceModel().modelDataResetRequested)
        b.model().sourceModel().activeChanged.connect(
            a.model().sourceModel().set_active)
        b.model().sourceModel().activeChanged.connect(
            lambda x: a.model().sourceModel().modelDataResetRequested.emit())

        a.model().sourceModel().modelReset.connect(
            lambda: f.model().sourceModel().set_active(a.model().sourceModel().active_index()))
        a.model().sourceModel().modelReset.connect(
            f.model().sourceModel().modelDataResetRequested)

        a.model().sourceModel().activeChanged.connect(
            f.model().sourceModel().set_active)
        a.model().sourceModel().activeChanged.connect(
            lambda x: f.model().sourceModel().modelDataResetRequested.emit())

        a.model().sourceModel().modelReset.connect(f.model().invalidateFilter)


        # Bookmark/Asset/FileModel/View  ->  ListControlModel/View
        # These connections are responsible for keeping the ListControlModel updated
        # when navigating the list widgets.
        b.model().sourceModel().modelReset.connect(
            l.model().modelDataResetRequested)

        a.model().sourceModel().modelReset.connect(
            lambda: l.model().set_active(a.model().sourceModel().active_index()))
        b.model().sourceModel().modelReset.connect(
            lambda: l.model().set_bookmark(b.model().sourceModel().active_index()))

        a.model().sourceModel().activeChanged.connect(
            l.model().set_active)
        b.model().sourceModel().activeChanged.connect(l.model().set_bookmark)

        a.model().sourceModel().activeChanged.connect(
            lambda x: l.model().modelDataResetRequested.emit())

        f.model().sourceModel().dataKeyChanged.connect(l.model().set_data_key)
        f.model().sourceModel().dataTypeChanged.connect(l.model().set_data_type)

        b.model().modelReset.connect(lb.repaint)
        b.model().layoutChanged.connect(lb.repaint)
        a.model().modelReset.connect(lb.repaint)
        a.model().layoutChanged.connect(lb.repaint)
        f.model().modelReset.connect(lb.repaint)
        f.model().layoutChanged.connect(lb.repaint)

        # Bookmark/Asset/FileModel/View  <-  ListControlModel/View
        # These are the signals responsible for changing the active items & data keys.
        l.textChanged.connect(lb.set_text)
        l.listChanged.connect(s.setCurrentIndex)
        l.dataKeyChanged.connect(f.model().sourceModel().dataKeyChanged)
        l.dataKeyChanged.connect(l.textChanged)
        f.model().sourceModel().dataKeyChanged.connect(l.textChanged)

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

        lc._addbutton.set_parent(self.stackedwidget)
        lc._archivedbutton.set_parent(self.stackedwidget)

        lc._todobutton.set_parent(self.stackedwidget)
        lc._filterbutton.set_parent(self.stackedwidget)
        lc._collapsebutton.set_parent(self.stackedwidget)
        lc._archivedbutton.set_parent(self.stackedwidget)
        lc._favouritebutton.set_parent(self.stackedwidget)

        # Updates the list-control buttons when changing lists
        l.listChanged.connect(lambda x: lb.repaint())
        l.listChanged.connect(lambda x: lc._addbutton.repaint())
        l.listChanged.connect(lambda x: lc._todobutton.repaint())
        l.listChanged.connect(lambda x: lc._filterbutton.repaint())
        l.listChanged.connect(lambda x: lc._collapsebutton.repaint())
        l.listChanged.connect(lambda x: lc._archivedbutton.repaint())
        l.listChanged.connect(lambda x: lc._favouritebutton.repaint())

        f.model().sourceModel().dataTypeChanged.connect(lambda x: lc._collapsebutton.repaint())
        b.model().filterFlagChanged.connect(lambda x, y: lc._archivedbutton.repaint())
        a.model().filterFlagChanged.connect(lambda x, y: lc._archivedbutton.repaint())
        f.model().filterFlagChanged.connect(lambda x, y: lc._archivedbutton.repaint())
        b.model().filterFlagChanged.connect(lambda x, y: lc._favouritebutton.repaint())
        a.model().filterFlagChanged.connect(lambda x, y: lc._favouritebutton.repaint())
        f.model().filterFlagChanged.connect(lambda x, y: lc._favouritebutton.repaint())
        b.model().filterFlagChanged.connect(lambda x, y: lc._filterbutton.repaint())
        a.model().filterFlagChanged.connect(lambda x, y: lc._filterbutton.repaint())
        f.model().filterFlagChanged.connect(lambda x, y: lc._filterbutton.repaint())

        b.model().filterTextChanged.connect(lambda x: lc._filterbutton.repaint())
        a.model().filterTextChanged.connect(lambda x: lc._filterbutton.repaint())
        f.model().filterTextChanged.connect(lambda x: lc._filterbutton.repaint())

        b.model().modelReset.connect(lc._archivedbutton.repaint)
        a.model().modelReset.connect(lc._archivedbutton.repaint)
        f.model().modelReset.connect(lc._archivedbutton.repaint)
        b.model().modelReset.connect(lc._favouritebutton.repaint)
        a.model().modelReset.connect(lc._favouritebutton.repaint)
        f.model().modelReset.connect(lc._favouritebutton.repaint)
        b.model().modelReset.connect(lc._filterbutton.repaint)
        a.model().modelReset.connect(lc._filterbutton.repaint)
        f.model().modelReset.connect(lc._filterbutton.repaint)

        b.model().layoutChanged.connect(lc._archivedbutton.repaint)
        a.model().layoutChanged.connect(lc._archivedbutton.repaint)
        f.model().layoutChanged.connect(lc._archivedbutton.repaint)
        b.model().layoutChanged.connect(lc._favouritebutton.repaint)
        a.model().layoutChanged.connect(lc._favouritebutton.repaint)
        f.model().layoutChanged.connect(lc._favouritebutton.repaint)
        b.model().layoutChanged.connect(lc._filterbutton.repaint)
        a.model().layoutChanged.connect(lc._filterbutton.repaint)
        f.model().layoutChanged.connect(lc._filterbutton.repaint)

        b.model().layoutChanged.connect(b.repaint)
        a.model().layoutChanged.connect(a.repaint)
        f.model().layoutChanged.connect(f.repaint)

        # Active monitor
        b.activated.connect(
            lambda x: active_monitor.save_state(u'server', x.data(common.ParentRole)[0]))
        b.activated.connect(
            lambda x: active_monitor.save_state(u'job', x.data(common.ParentRole)[1]))
        b.activated.connect(
            lambda x: active_monitor.save_state(u'root', x.data(common.ParentRole)[2]))
        active_monitor.activeBookmarkChanged.connect(b.model().sourceModel().modelDataResetRequested)
        active_monitor.activeBookmarkChanged.connect(lambda: l.listChanged.emit(1))

        a.activated.connect(
            lambda x: active_monitor.save_state(u'asset', x.data(common.ParentRole)[-1]))
        active_monitor.activeAssetChanged.connect(a.model().sourceModel().modelDataResetRequested)
        active_monitor.activeAssetChanged.connect(lambda: l.listChanged.emit(1))

        f.model().sourceModel().dataKeyChanged.connect(f.save_data_key)
        l.dataKeyChanged.connect(f.save_data_key)

        f.model().sourceModel().dataKeyChanged.connect(
            lambda x: active_monitor.save_state(u'location', x))
        l.dataKeyChanged.connect(
            lambda x: active_monitor.save_state(u'location', x))

        active_monitor.activeLocationChanged.connect(l.dataKeyChanged)
        active_monitor.activeLocationChanged.connect(lambda: l.listChanged.emit(2) if x else l.listChanged.emit(1))
        # I don't think we have to respond to any active file changes

        # Progresslabel
        b.model().modelAboutToBeReset.connect(lambda: m.messageChanged.emit(u'Getting bookmarks...'))
        b.model().layoutAboutToBeChanged.connect(lambda x: m.messageChanged.emit(u'Getting bookmarks...'))
        b.model().modelReset.connect(lambda: m.messageChanged.emit(u''))
        b.model().layoutChanged.connect(lambda x: m.messageChanged.emit(u''))

        a.model().modelAboutToBeReset.connect(lambda: m.messageChanged.emit(u'Getting assets...'))
        a.model().layoutAboutToBeChanged.connect(lambda x: m.messageChanged.emit(u'Getting assets...'))
        a.model().modelReset.connect(lambda: m.messageChanged.emit(u''))
        a.model().layoutChanged.connect(lambda x: m.messageChanged.emit(u''))

        # f.model().sourceModel().modelDataResetRequested.connect(lambda: m.messageChanged.emit(u'3Getting files...'))
        f.model().sourceModel().layoutAboutToBeChanged.connect(lambda x: m.messageChanged.emit(u'4Getting files...'))
        f.model().sourceModel().modelReset.connect(lambda: m.messageChanged.emit(u''))
        f.model().sourceModel().layoutChanged.connect(lambda: m.messageChanged.emit(u''))

        f.model().modelAboutToBeReset.connect(lambda: m.messageChanged.emit(u'Getting files...'))
        f.model().layoutAboutToBeChanged.connect(lambda x: m.messageChanged.emit(u'Getting files...'))
        f.model().modelReset.connect(lambda: m.messageChanged.emit(u''))
        f.model().layoutChanged.connect(lambda x: m.messageChanged.emit(u''))


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

    def paintEvent(self, event):
        """Drawing a rounded background help to identify that the widget
        is in standalone mode."""
        painter = QtGui.QPainter()
        painter.begin(self)

        rect = QtCore.QRect(self.rect())
        # center = rect.center()
        # rect.setWidth(rect.width() - (common.MARGIN / 2))
        # rect.setHeight(rect.height() - (common.MARGIN / 2))
        # rect.moveCenter(center)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.SEPARATOR)
        painter.drawRoundedRect(rect, 3, 3)

        if not self._initialized:
            font = QtGui.QFont(common.PrimaryFont)
            font.setPointSize(10)

            rect = QtCore.QRect(self.rect())
            align = QtCore.Qt.AlignCenter
            color = QtGui.QColor(255,255,255,80)

            pixmaprect = QtCore.QRect(rect)
            center = pixmaprect.center()
            pixmaprect.setWidth(64)
            pixmaprect.setHeight(64)
            pixmaprect.moveCenter(center)

            pixmap = ImageCache.get_rsc_pixmap(
                'custom_bw', QtGui.QColor(0, 0, 0, 50), 64)
            painter.drawPixmap(pixmaprect, pixmap, pixmap.rect())
            rect.setTop(pixmaprect.bottom() + common.INDICATOR_WIDTH)
            common.draw_aliased_text(painter, font, rect, self.init_progress, align, color)

        painter.end()

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
        if not self._initialized:
            self.initializer.start()

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = BrowserWidget()
    widget.show()
    app.exec_()
