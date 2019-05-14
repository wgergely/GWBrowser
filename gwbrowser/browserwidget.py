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
import sys

from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser.common as common
from gwbrowser.baselistwidget import StackedWidget
from gwbrowser.bookmarkswidget import BookmarksWidget
from gwbrowser.assetswidget import AssetsWidget
from gwbrowser.fileswidget import FilesWidget
from gwbrowser.editors import ClickableLabel
from gwbrowser.favouriteswidget import FavouritesWidget
from gwbrowser.listcontrolwidget import ListControlWidget
from gwbrowser.listcontrolwidget import FilterButton
from gwbrowser.imagecache import ImageCache
from gwbrowser.settings import local_settings, Active, active_monitor
import gwbrowser.settings as Settings


qn = 0
"""Number of tries before quitting"""


class VersionLabel(QtWidgets.QLabel):
    """Small version label responsible for displaying information
    about GWBrowser."""

    def __init__(self, parent=None):
        super(VersionLabel, self).__init__(parent=parent)
        import gwbrowser
        self.setText(
            u'<font color=gray size={}pt>{}</font>'.format(
                common.psize(common.SMALL_FONT_SIZE),
                gwbrowser.__version__))

    def mousePressEvent(self, event):
        import gwbrowser
        version = u'{}'.format(gwbrowser.__version__)
        self.parent().showMessage(version)

    def mousePressEvent(self, event):
        QtGui.QDesktopServices.openUrl(ur'https://gergely-wootsch.com/gwbrowser-about')



class SizeGrip(QtWidgets.QSizeGrip):
    """Custom size-grip for resizing browser-widget"""
    def __init__(self, browserwidget, parent=None):
        super(SizeGrip, self).__init__(parent)
        self.browserwidget = browserwidget
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

    def update_widgets(self, tracking):
        """Seems to be some issue with resizing the views when using using the grip.
        Also, when mouse-tracking is on resize is slow."""
        stackedwidget = self.browserwidget.stackedwidget
        controlview = self.browserwidget.listcontrolwidget._controlview
        fileswidget = self.browserwidget.fileswidget

        stackedwidget.setMouseTracking(tracking)
        for idx in xrange(stackedwidget.count()):
            widget = stackedwidget.widget(idx)
            # widget.setUpdatesEnabled(tracking)
            widget.setMouseTracking(tracking)
            widget.viewport().setMouseTracking(tracking)
            widget.updateGeometry()

    def mouseMoveEvent(self, event):
        self.update_widgets(False)
        super(SizeGrip, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.update_widgets(True)
        super(SizeGrip, self).mouseReleaseEvent(event)


class BrowserWidget(QtWidgets.QWidget):
    """Main widget to browse pipline data."""
    initialized = QtCore.Signal()
    shutdown = QtCore.Signal()

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
        self.favouriteswidget = None

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

        # Shutdown monitor - we will exit the application when all the threads
        # have finished running
        self.shutdown_timer = QtCore.QTimer()
        self.shutdown_timer.setInterval(250)
        self.shutdown_timer.setSingleShot(False)

        self.init_progress = u'Loading...'
        self.repaint()

        self.effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.effect.setOpacity(0.0)
        self.setGraphicsEffect(self.effect)

        self.animation = QtCore.QPropertyAnimation(
            self.effect, QtCore.QByteArray('opacity'))
        self.animation.setDuration(200)
        self.animation.setKeyValueAt(0, 0)
        self.animation.setKeyValueAt(0.5, 0.8)
        self.animation.setKeyValueAt(1, 1.0)

    @QtCore.Slot()
    def initialize(self):
        """To make sure the widget is shown as soon as it is created, we're
        initiating the ui and the models with a little delay. Settings saved in the
        local_settings are applied after the ui is initialized.

        """
        if self._initialized:
            return

        self._createUI()
        self._connectSignals()

        active_monitor.macos_mount_timer.start()
        Active.paths()

        # Switching stacked widget to saved index...
        idx = local_settings.value(u'widget/mode')
        idx = 0 if idx is None else idx
        self.listcontrolwidget.listChanged.emit(idx)
        if idx == 2:
            text = self.fileswidget.model().sourceModel().data_key()
            text = text.title() if text else None
            self.listcontrolwidget.textChanged.emit(text)

        # Proxy model
        b = self.bookmarkswidget
        a = self.assetswidget
        f = self.fileswidget
        ff = self.favouriteswidget

        b.model().filterTextChanged.emit(b.model().filterText())
        a.model().filterTextChanged.emit(a.model().filterText())
        f.model().filterTextChanged.emit(f.model().filterText())
        ff.model().filterTextChanged.emit(ff.model().filterText())

        b.model().filterFlagChanged.emit(Settings.MarkedAsActive,
                                         b.model().filterFlag(Settings.MarkedAsActive))
        b.model().filterFlagChanged.emit(Settings.MarkedAsArchived,
                                         b.model().filterFlag(Settings.MarkedAsArchived))
        b.model().filterFlagChanged.emit(Settings.MarkedAsFavourite,
                                         b.model().filterFlag(Settings.MarkedAsFavourite))
        #
        a.model().filterFlagChanged.emit(Settings.MarkedAsActive,
                                         a.model().filterFlag(Settings.MarkedAsActive))
        a.model().filterFlagChanged.emit(Settings.MarkedAsArchived,
                                         a.model().filterFlag(Settings.MarkedAsArchived))
        a.model().filterFlagChanged.emit(Settings.MarkedAsFavourite,
                                         a.model().filterFlag(Settings.MarkedAsFavourite))
        #
        f.model().filterFlagChanged.emit(Settings.MarkedAsActive,
                                         f.model().filterFlag(Settings.MarkedAsActive))
        f.model().filterFlagChanged.emit(Settings.MarkedAsArchived,
                                         f.model().filterFlag(Settings.MarkedAsArchived))
        f.model().filterFlagChanged.emit(Settings.MarkedAsFavourite,
                                         f.model().filterFlag(Settings.MarkedAsFavourite))
        #
        ff.model().filterFlagChanged.emit(Settings.MarkedAsActive,
                                          ff.model().filterFlag(Settings.MarkedAsActive))
        ff.model().filterFlagChanged.emit(Settings.MarkedAsArchived,
                                          ff.model().filterFlag(Settings.MarkedAsArchived))
        ff.model().filterFlagChanged.emit(Settings.MarkedAsFavourite,
                                          ff.model().filterFlag(Settings.MarkedAsFavourite))

        # Source model data
        timer = QtCore.QTimer(parent=self)
        timer.setSingleShot(True)
        timer.setInterval(1000)
        timer.timeout.connect(b.model().sourceModel().modelDataResetRequested)
        timer.timeout.connect(timer.deleteLater)
        timer.start()

        self._initialized = True
        self.initialized.emit()

        if local_settings.value(u'firstrun') is None:
            QtGui.QDesktopServices.openUrl(ur'https://gergely-wootsch.com/gwbrowser-about')
            local_settings.setValue(u'firstrun', False)

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

        self.assetswidget = AssetsWidget(parent=self)

        self.init_progress = u'Creating files tab...'
        self.repaint()
        app.processEvents(flags=QtCore.QEventLoop.ExcludeUserInputEvents)

        self.fileswidget = FilesWidget(parent=self)
        self.favouriteswidget = FavouritesWidget(parent=self)
        self.stackedwidget.addWidget(self.bookmarkswidget)
        self.stackedwidget.addWidget(self.assetswidget)
        self.stackedwidget.addWidget(self.fileswidget)
        self.stackedwidget.addWidget(self.favouriteswidget)

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
        self.statusbar.setFixedHeight(common.INLINE_ICON_SIZE)
        self.statusbar.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )
        self.statusbar.setSizeGripEnabled(False)

        # Swapping the default grip with my custom one
        grip = self.statusbar.findChild(QtWidgets.QSizeGrip)
        if grip:
            grip.deleteLater()
        grip = SizeGrip(self, parent=self)

        self.statusbar.addPermanentWidget(VersionLabel(parent=self.statusbar))
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
        ff = self.favouriteswidget
        lc = self.listcontrolwidget

        l = lc.control_view()
        lb = lc.control_button()

        s = self.stackedwidget
        # Shutdown signals
        #
        # I have to make sure not to exit the main application before the threads
        # stopped running. First the workers have to be terminated, then When
        # all the threads stopped running we will quit the application.

        threadpool = (
            list(f.model().sourceModel().threads.itervalues()) +
            list(ff.model().sourceModel().threads.itervalues()) +
            list(ImageCache.instance().threads.itervalues()) +
            list(l.model().threads.itervalues())
        )

        @QtCore.Slot()
        def _quit():
            """When all the threads quit, we'll exit the main application too."""
            global qn
            qn += 1

            for thread in threadpool:
                if thread.isRunning():
                    thread.worker.shutdown()
                    thread.quit()

            if all([not f.isRunning() for f in threadpool]):
                sys.stdout.write('# All threads finished.')
                QtWidgets.QApplication.instance().quit()

            # Forcing the application to close after n tries
            if qn > 20:  # circa 5 seconds to wrap things up, will exit by force after
                QtWidgets.QApplication.instance().quit()
                raise SystemExit(0)

        @QtCore.Slot()
        def finished(thread):
            sys.stdout.write('# {} shut down.\n'.format(
                thread.__class__.__name__))

        self.shutdown_timer.timeout.connect(_quit)
        self.shutdown.connect(
            lambda: self.statusbar.showMessage(u'Quitting...', 1000))
        self.shutdown.connect(self.shutdown_timer.start)
        for thread in threadpool:
            self.shutdown.connect(thread.worker.shutdown)
            thread.finished.connect(functools.partial(finished, thread))

        # Signals responsible for saveing the activation changes
        b.model().sourceModel().activeChanged.connect(b.save_activated)
        a.model().sourceModel().activeChanged.connect(a.save_activated)
        f.model().sourceModel().activeChanged.connect(f.save_activated)
        ff.model().sourceModel().activeChanged.connect(ff.save_activated)

        # Making sure the Favourites widget is updated when the favourite-list changes
        b.favouritesChanged.connect(
            ff.model().sourceModel().modelDataResetRequested)
        a.favouritesChanged.connect(
            ff.model().sourceModel().modelDataResetRequested)
        f.favouritesChanged.connect(
            ff.model().sourceModel().modelDataResetRequested)
        ff.favouritesChanged.connect(
            ff.model().sourceModel().modelDataResetRequested)

        # Signal/slot connections for the primary bookmark/asset and filemodels
        b.model().sourceModel().modelReset.connect(
            lambda: a.model().sourceModel().set_active(b.model().sourceModel().active_index()))
        b.model().sourceModel().modelReset.connect(
            a.model().sourceModel().modelDataResetRequested)
        b.model().sourceModel().activeChanged.connect(
            a.model().sourceModel().set_active)
        b.model().sourceModel().activeChanged.connect(
            lambda x: a.model().sourceModel().modelDataResetRequested.emit())
        #
        b.model().sourceModel().modelReset.connect(
            lambda: ff.model().sourceModel().set_active(b.model().sourceModel().active_index()))
        b.model().sourceModel().modelReset.connect(
            ff.model().sourceModel().modelDataResetRequested)
        b.model().sourceModel().activeChanged.connect(
            ff.model().sourceModel().set_active)
        b.model().sourceModel().activeChanged.connect(
            lambda x: ff.model().sourceModel().modelDataResetRequested.emit())

        a.model().sourceModel().modelReset.connect(
            lambda: f.model().sourceModel().set_active(a.model().sourceModel().active_index()))
        a.model().sourceModel().modelReset.connect(
            f.model().sourceModel().modelDataResetRequested)

        a.model().sourceModel().activeChanged.connect(
            f.model().sourceModel().set_active)
        a.model().sourceModel().activeChanged.connect(
            lambda x: f.model().sourceModel().modelDataResetRequested.emit())

        a.model().sourceModel().modelReset.connect(f.model().invalidateFilter)
        b.model().sourceModel().modelReset.connect(ff.model().invalidateFilter)

        # Bookmark/Asset/FileModel/View  ->  DataKeyModel/View
        # These connections are responsible for keeping the DataKeyModel updated
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
        ff.model().sourceModel().dataTypeChanged.connect(l.model().set_data_type)

        b.model().modelReset.connect(lb.repaint)
        b.model().layoutChanged.connect(lb.repaint)
        a.model().modelReset.connect(lb.repaint)
        a.model().layoutChanged.connect(lb.repaint)
        f.model().modelReset.connect(lb.repaint)
        f.model().layoutChanged.connect(lb.repaint)
        ff.model().modelReset.connect(lb.repaint)
        ff.model().layoutChanged.connect(lb.repaint)

        # Bookmark/Asset/FileModel/View  <-  DataKeyModel/View
        # These are the signals responsible for changing the active items & data keys.
        lc.textChanged.connect(lb.set_text)
        lc.listChanged.connect(s.setCurrentIndex)
        lc.dataKeyChanged.connect(f.model().sourceModel().dataKeyChanged)
        lc.dataKeyChanged.connect(lc.textChanged)
        f.model().sourceModel().dataKeyChanged.connect(lc.textChanged)

        # Stacked widget navigation
        b.activated.connect(lambda: lc.listChanged.emit(1))
        # b.activated.connect(lambda: lc.textChanged.emit(u'Assets'))
        a.activated.connect(lambda: lc.listChanged.emit(2))

        b.activated.connect(
            lambda: lc.textChanged.emit(f.model().sourceModel().data_key()) if f.model().sourceModel().data_key() else 'Files')
        b.model().sourceModel().activeChanged.connect(
            lambda x: lc.textChanged.emit(f.model().sourceModel().data_key()) if f.model().sourceModel().data_key() else 'Files')
        a.activated.connect(
            lambda: lc.textChanged.emit(f.model().sourceModel().data_key()) if f.model().sourceModel().data_key() else 'Files')
        a.model().sourceModel().activeChanged.connect(
            lambda x: lc.textChanged.emit(f.model().sourceModel().data_key()) if f.model().sourceModel().data_key() else 'Files')

        # Statusbar
        b.entered.connect(self.entered)
        a.entered.connect(self.entered)
        f.entered.connect(self.entered)
        ff.entered.connect(self.entered)
        l.entered.connect(self.entered)

        lc._bookmarksbutton.message.connect(self.entered2)
        lc._assetsbutton.message.connect(self.entered2)
        lc._filesbutton.message.connect(self.entered2)
        lc._favouritesbutton.message.connect(self.entered2)

        lc._addbutton.message.connect(self.entered2)
        lc._generatethumbnailsbutton.message.connect(self.entered2)
        lc._todobutton.message.connect(self.entered2)
        lc._filterbutton.message.connect(self.entered2)
        lc._collapsebutton.message.connect(self.entered2)
        lc._archivedbutton.message.connect(self.entered2)
        lc._togglebuttonsbutton.message.connect(self.entered2)
        lc._favouritebutton.message.connect(self.entered2)
        lc._slackbutton.message.connect(self.entered2)

        lc._bookmarksbutton.set_parent(self.stackedwidget)
        lc._assetsbutton.set_parent(self.stackedwidget)
        lc._filesbutton.set_parent(self.stackedwidget)
        lc._favouritesbutton.set_parent(self.stackedwidget)
        lc._addbutton.set_parent(self.stackedwidget)
        lc._generatethumbnailsbutton.set_parent(self.stackedwidget)

        lc._todobutton.set_parent(self.stackedwidget)
        lc._filterbutton.set_parent(self.stackedwidget)
        lc._collapsebutton.set_parent(self.stackedwidget)
        lc._archivedbutton.set_parent(self.stackedwidget)
        lc._favouritebutton.set_parent(self.stackedwidget)
        lc._togglebuttonsbutton.set_parent(self.stackedwidget)

        # Controlbutton text should be invisible when there's no active asset set
        b.model().sourceModel().activeChanged.connect(
            lambda x: lc.textChanged.emit(u'Files'))
        a.model().sourceModel().activeChanged.connect(
            lambda x: self.fileswidget.model().sourceModel().data_key())

        lc._bookmarksbutton.clicked.connect(
            lambda: lc.listChanged.emit(0), type=QtCore.Qt.QueuedConnection)
        lc._assetsbutton.clicked.connect(
            lambda: lc.listChanged.emit(1), type=QtCore.Qt.QueuedConnection)
        lc._filesbutton.clicked.connect(
            lambda: lc.listChanged.emit(2), type=QtCore.Qt.QueuedConnection)
        lc._favouritesbutton.clicked.connect(
            lambda: lc.listChanged.emit(3), type=QtCore.Qt.QueuedConnection)

        # Updates the list-control buttons when changing lists
        lc.listChanged.connect(lambda x: lb.repaint())
        lc.listChanged.connect(lambda x: lc._bookmarksbutton.repaint())
        lc.listChanged.connect(lambda x: lc._assetsbutton.repaint())
        lc.listChanged.connect(lambda x: lc._filesbutton.repaint())
        lc.listChanged.connect(lambda x: lc._favouritesbutton.repaint())
        lc.listChanged.connect(lambda x: lc._addbutton.repaint())
        lc.listChanged.connect(
            lambda x: lc._generatethumbnailsbutton.repaint())
        lc.listChanged.connect(lambda x: lc._todobutton.repaint())
        lc.listChanged.connect(lambda x: lc._filterbutton.repaint())
        lc.listChanged.connect(lambda x: lc._collapsebutton.repaint())
        lc.listChanged.connect(lambda x: lc._archivedbutton.repaint())
        lc.listChanged.connect(lambda x: lc._favouritebutton.repaint())
        lc.listChanged.connect(lambda x: lc._togglebuttonsbutton.repaint())

        s.currentChanged.connect(lambda x: lc._bookmarksbutton.repaint())
        s.currentChanged.connect(lambda x: lc._assetsbutton.repaint())
        s.currentChanged.connect(lambda x: lc._filesbutton.repaint())
        s.currentChanged.connect(lambda x: lc._favouritesbutton.repaint())
        s.currentChanged.connect(lambda x: lc._togglebuttonsbutton.repaint())

        f.model().sourceModel().dataTypeChanged.connect(
            lambda x: lc._collapsebutton.repaint())
        ff.model().sourceModel().dataTypeChanged.connect(
            lambda x: lc._collapsebutton.repaint())
        b.model().filterFlagChanged.connect(lambda x, y: lc._archivedbutton.repaint())
        a.model().filterFlagChanged.connect(lambda x, y: lc._archivedbutton.repaint())
        f.model().filterFlagChanged.connect(lambda x, y: lc._archivedbutton.repaint())
        ff.model().filterFlagChanged.connect(lambda x, y: lc._archivedbutton.repaint())
        b.model().filterFlagChanged.connect(lambda x, y: lc._favouritebutton.repaint())
        a.model().filterFlagChanged.connect(lambda x, y: lc._favouritebutton.repaint())
        f.model().filterFlagChanged.connect(lambda x, y: lc._favouritebutton.repaint())
        ff.model().filterFlagChanged.connect(lambda x, y: lc._favouritebutton.repaint())
        b.model().filterFlagChanged.connect(lambda x, y: lc._filterbutton.repaint())
        a.model().filterFlagChanged.connect(lambda x, y: lc._filterbutton.repaint())
        f.model().filterFlagChanged.connect(lambda x, y: lc._filterbutton.repaint())
        ff.model().filterFlagChanged.connect(lambda x, y: lc._filterbutton.repaint())

        b.model().filterTextChanged.connect(lambda x: lc._filterbutton.repaint())
        a.model().filterTextChanged.connect(lambda x: lc._filterbutton.repaint())
        f.model().filterTextChanged.connect(lambda x: lc._filterbutton.repaint())
        ff.model().filterTextChanged.connect(lambda x: lc._filterbutton.repaint())

        b.model().modelReset.connect(lc._archivedbutton.repaint)
        a.model().modelReset.connect(lc._archivedbutton.repaint)
        f.model().modelReset.connect(lc._archivedbutton.repaint)
        ff.model().modelReset.connect(lc._archivedbutton.repaint)
        b.model().modelReset.connect(lc._favouritebutton.repaint)
        a.model().modelReset.connect(lc._favouritebutton.repaint)
        f.model().modelReset.connect(lc._favouritebutton.repaint)
        ff.model().modelReset.connect(lc._favouritebutton.repaint)
        b.model().modelReset.connect(lc._filterbutton.repaint)
        a.model().modelReset.connect(lc._filterbutton.repaint)
        f.model().modelReset.connect(lc._filterbutton.repaint)
        ff.model().modelReset.connect(lc._filterbutton.repaint)

        b.model().layoutChanged.connect(lc._archivedbutton.repaint)
        a.model().layoutChanged.connect(lc._archivedbutton.repaint)
        f.model().layoutChanged.connect(lc._archivedbutton.repaint)
        ff.model().layoutChanged.connect(lc._archivedbutton.repaint)
        b.model().layoutChanged.connect(lc._favouritebutton.repaint)
        a.model().layoutChanged.connect(lc._favouritebutton.repaint)
        f.model().layoutChanged.connect(lc._favouritebutton.repaint)
        ff.model().layoutChanged.connect(lc._favouritebutton.repaint)
        b.model().layoutChanged.connect(lc._filterbutton.repaint)
        a.model().layoutChanged.connect(lc._filterbutton.repaint)
        f.model().layoutChanged.connect(lc._filterbutton.repaint)
        ff.model().layoutChanged.connect(lc._filterbutton.repaint)

        b.model().layoutChanged.connect(b.repaint)
        a.model().layoutChanged.connect(a.repaint)
        f.model().layoutChanged.connect(f.repaint)
        ff.model().layoutChanged.connect(f.repaint)

        # Active monitor
        b.activated.connect(
            lambda x: active_monitor.save_state(u'server', x.data(common.ParentRole)[0]))
        b.activated.connect(
            lambda x: active_monitor.save_state(u'job', x.data(common.ParentRole)[1]))
        b.activated.connect(
            lambda x: active_monitor.save_state(u'root', x.data(common.ParentRole)[2]))
        active_monitor.activeBookmarkChanged.connect(
            b.model().sourceModel().modelDataResetRequested)
        active_monitor.activeBookmarkChanged.connect(
            lambda: lc.listChanged.emit(1))

        a.activated.connect(
            lambda x: active_monitor.save_state(u'asset', x.data(common.ParentRole)[-1]))
        active_monitor.activeAssetChanged.connect(
            a.model().sourceModel().modelDataResetRequested)
        active_monitor.activeAssetChanged.connect(
            lambda: lc.listChanged.emit(1))

        f.model().sourceModel().dataKeyChanged.connect(f.save_data_key)
        lc.dataKeyChanged.connect(f.save_data_key)

        f.model().sourceModel().dataKeyChanged.connect(
            lambda x: active_monitor.save_state(u'location', x))
        lc.dataKeyChanged.connect(
            lambda x: active_monitor.save_state(u'location', x))

        active_monitor.activeLocationChanged.connect(lc.dataKeyChanged)
        active_monitor.activeLocationChanged.connect(
            lambda x: lc.listChanged.emit(2) if x else lc.listChanged.emit(1))
        # I don't think we have to respond to any active file changes

        # Progresslabel
        b.model().modelAboutToBeReset.connect(
            lambda: self.statusbar.showMessage(u'Getting bookmarks...', 99999))
        b.model().layoutAboutToBeChanged.connect(
            lambda x: self.statusbar.showMessage(u'Getting bookmarks...', 99999))
        b.model().modelReset.connect(lambda: self.statusbar.showMessage(u'', 99999))
        b.model().layoutChanged.connect(lambda x: self.statusbar.showMessage(u'', 99999))
        b.model().sourceModel().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))
        b.model().sourceModel().layoutChanged.connect(
            lambda x: self.statusbar.showMessage(u'', 99999))

        a.model().modelAboutToBeReset.connect(
            lambda: self.statusbar.showMessage(u'Getting assets...', 99999))
        a.model().layoutAboutToBeChanged.connect(
            lambda x: self.statusbar.showMessage(u'Getting assets...', 99999))
        a.model().modelReset.connect(lambda: self.statusbar.showMessage(u'', 99999))
        a.model().layoutChanged.connect(lambda x: self.statusbar.showMessage(u'', 99999))
        a.model().sourceModel().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))
        a.model().sourceModel().layoutChanged.connect(
            lambda: self.statusbar.showMessage(u''))

        f.model().modelAboutToBeReset.connect(
            lambda: self.statusbar.showMessage(u'Getting files...', 99999))
        f.model().layoutAboutToBeChanged.connect(
            lambda x: self.statusbar.showMessage(u'Getting files...', 99999))
        f.model().modelReset.connect(lambda: self.statusbar.showMessage(u'', 99999))
        f.model().layoutChanged.connect(lambda x: self.statusbar.showMessage(u'', 99999))
        f.model().sourceModel().layoutAboutToBeChanged.connect(
            lambda x: self.statusbar.showMessage(u'Getting files...'))
        f.model().sourceModel().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))
        f.model().sourceModel().layoutChanged.connect(
            lambda: self.statusbar.showMessage(u'', 99999))

        f.model().sourceModel().messageChanged.connect(
            lambda m: self.statusbar.showMessage(m, 99999))

    def paintEvent(self, event):
        """Drawing a rounded background help to identify that the widget
        is in standalone mode."""
        painter = QtGui.QPainter()
        painter.begin(self)

        rect = QtCore.QRect(self.rect())

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.SEPARATOR)
        painter.drawRoundedRect(rect, 7, 7)

        if not self._initialized:
            font = QtGui.QFont(common.PrimaryFont)
            font.setPointSize(common.MEDIUM_FONT_SIZE)

            rect = QtCore.QRect(self.rect())
            align = QtCore.Qt.AlignCenter
            color = QtGui.QColor(255, 255, 255, 80)

            pixmaprect = QtCore.QRect(rect)
            center = pixmaprect.center()
            pixmaprect.setWidth(64)
            pixmaprect.setHeight(64)
            pixmaprect.moveCenter(center)

            pixmap = ImageCache.get_rsc_pixmap(
                'custom_bw', QtGui.QColor(0, 0, 0, 50), 64)
            painter.drawPixmap(pixmaprect, pixmap, pixmap.rect())
            rect.setTop(pixmaprect.bottom() + common.INDICATOR_WIDTH)
            common.draw_aliased_text(
                painter, font, rect, self.init_progress, align, color)

        painter.end()

    @QtCore.Slot(QtCore.QModelIndex)
    def entered(self, index):
        """Displays an indexe's status tip in the statusbar."""
        if not index.isValid():
            return
        message = index.data(QtCore.Qt.StatusTipRole)
        self.statusbar.showMessage(message, timeout=1500)

    @QtCore.Slot(unicode)
    def entered2(self, message):
        """Displays a custom message in the statusbar"""
        if not message:
            return
        self.statusbar.showMessage(message, timeout=1500)

    def activate_widget(self, idx):
        """Method to change between views."""
        self.stackedwidget.setCurrentIndex(idx)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH, common.HEIGHT)

    def showEvent(self, event):
        self.animation.stop()
        self.animation.setDirection(QtCore.QAbstractAnimation.Forward)
        self.animation.start(QtCore.QAbstractAnimation.KeepWhenStopped)
        if not self._initialized:
            self.initializer.start()

    def hideEvent(self, event):
        self.animation.stop()
        self.animation.setDirection(QtCore.QAbstractAnimation.Backward)
        self.animation.start(QtCore.QAbstractAnimation.KeepWhenStopped)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = BrowserWidget()
    widget.show()
    app.exec_()
