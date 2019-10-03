# -*- coding: utf-8 -*-
"""``browserwidget.py`` is the main widget of GWBrowser.
It contains the ``StackedWidget`` and the ``HeaderWidget`` in standalone mode.

"""

from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser.common as common
from gwbrowser.common_ui import ClickableIconButton
from gwbrowser.threads import BaseThread
from gwbrowser.baselistwidget import StackedWidget
from gwbrowser.bookmarkswidget import BookmarksWidget
from gwbrowser.assetswidget import AssetsWidget
from gwbrowser.fileswidget import FilesWidget
from gwbrowser.favouriteswidget import FavouritesWidget
from gwbrowser.listcontrolwidget import ListControlWidget
from gwbrowser.imagecache import ImageCache
from gwbrowser.settings import local_settings, Active
from gwbrowser.preferenceswidget import PreferencesWidget


class SettingsButton(ClickableIconButton):
    """Small version label responsible for displaying information
    about GWBrowser."""

    def __init__(self, pixmap, colors, size, description=u'', parent=None):
        super(SettingsButton, self).__init__(pixmap, colors,
                                             size, description=description, parent=parent)

        # import gwbrowser
        # import OpenImageIO.OpenImageIO as oiio
        # message = u'Click to read the documentation | v{} | PySide2 {} | OpenImageIO {}'.format(
        #     gwbrowser.__version__,
        #     QtCore.__version__,
        #     oiio.__version__
        # )
        self.clicked.connect(self.parent().preferences_widget.show)


class BrowserWidget(QtWidgets.QWidget):
    """GWBrowser's main widget."""

    initialized = QtCore.Signal()
    shutdown = QtCore.Signal()
    resized = QtCore.Signal(QtCore.QRect)

    def __init__(self, parent=None):
        super(BrowserWidget, self).__init__(parent=parent)
        self.setObjectName(u'BrowserWidget')
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        pixmap = ImageCache.get_rsc_pixmap(u'custom', None, 64)
        self.setWindowIcon(QtGui.QIcon(pixmap))

        self.__qn = 0
        self._contextMenu = None
        self._initialized = False
        self.stackedwidget = None
        self.bookmarkswidget = None
        self.listcontrolwidget = None
        self.assetswidget = None
        self.fileswidget = None
        self.favouriteswidget = None
        self.statusbar = None

        self.active_monitor = Active(parent=self)

        self.check_active_state_timer = QtCore.QTimer(parent=self)
        self.check_active_state_timer.setInterval(1000)
        self.check_active_state_timer.setSingleShot(False)
        # self.check_active_state_timer.setTimerType(QtCore.Qt.CoarseTimer)
        self.check_active_state_timer.timeout.connect(
            self.active_monitor.check_state)

        self.preferences_widget = None

        self.initializer = QtCore.QTimer(parent=self)
        self.initializer.setSingleShot(True)
        self.initializer.setInterval(200)
        self.initializer.timeout.connect(self.initialize)
        self.initializer.timeout.connect(self.initializer.deleteLater)

        # Shutdown monitor - we will exit the application when all the threads
        # have finished running
        self.shutdown_timer = QtCore.QTimer(parent=self)
        self.shutdown_timer.setInterval(250)
        self.shutdown_timer.setSingleShot(False)

        self.init_progress = u'Loading...'
        self.repaint()

    @QtCore.Slot()
    def initialize(self):
        """To make sure the widget is shown as soon as it is created, we're
        initiating the ui and the models with a little delay. Settings saved in the
        local_settings are applied after the ui is initialized.

        """
        self.shortcuts = []
        if self._initialized:
            return

        self._createUI()
        self._connectSignals()
        self._add_shortcuts()

        if common.get_platform() == u'mac':
            self.active_monitor.macos_mount_timer.start()

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

        b.model().filterFlagChanged.emit(common.MarkedAsActive,
                                         b.model().filterFlag(common.MarkedAsActive))
        b.model().filterFlagChanged.emit(common.MarkedAsArchived,
                                         b.model().filterFlag(common.MarkedAsArchived))
        b.model().filterFlagChanged.emit(common.MarkedAsFavourite,
                                         b.model().filterFlag(common.MarkedAsFavourite))

        a.model().filterFlagChanged.emit(common.MarkedAsActive,
                                         a.model().filterFlag(common.MarkedAsActive))
        a.model().filterFlagChanged.emit(common.MarkedAsArchived,
                                         a.model().filterFlag(common.MarkedAsArchived))
        a.model().filterFlagChanged.emit(common.MarkedAsFavourite,
                                         a.model().filterFlag(common.MarkedAsFavourite))

        f.model().filterFlagChanged.emit(common.MarkedAsActive,
                                         f.model().filterFlag(common.MarkedAsActive))
        f.model().filterFlagChanged.emit(common.MarkedAsArchived,
                                         f.model().filterFlag(common.MarkedAsArchived))
        f.model().filterFlagChanged.emit(common.MarkedAsFavourite,
                                         f.model().filterFlag(common.MarkedAsFavourite))

        ff.model().filterFlagChanged.emit(common.MarkedAsActive,
                                          ff.model().filterFlag(common.MarkedAsActive))
        ff.model().filterFlagChanged.emit(common.MarkedAsArchived,
                                          ff.model().filterFlag(common.MarkedAsArchived))
        ff.model().filterFlagChanged.emit(common.MarkedAsFavourite,
                                          ff.model().filterFlag(common.MarkedAsFavourite))

        # Source model data
        timer = QtCore.QTimer(parent=self)
        timer.setSingleShot(True)
        timer.setInterval(1000)
        timer.timeout.connect(b.model().sourceModel().modelDataResetRequested)
        timer.timeout.connect(self.check_active_state_timer.start)
        timer.timeout.connect(timer.deleteLater)
        timer.start()

        self.stackedwidget.currentWidget().setFocus()

        self._initialized = True
        self.initialized.emit()

        # Anything here will be run the first time gwbrowser is launched
        if local_settings.value(u'firstrun') is None:
            local_settings.setValue(u'firstrun', False)

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

        self.preferences_widget = PreferencesWidget(parent=self)
        self.preferences_widget.hide()

        self.stackedwidget = StackedWidget(parent=self)

        self.init_progress = u'Creating bookmarks tab...'
        self.repaint()

        self.bookmarkswidget = BookmarksWidget(parent=self)

        self.init_progress = u'Creating assets tab...'
        self.repaint()

        self.assetswidget = AssetsWidget(parent=self)

        self.init_progress = u'Creating files tab...'
        self.repaint()

        self.fileswidget = FilesWidget(parent=self)
        self.favouriteswidget = FavouritesWidget(parent=self)
        self.stackedwidget.addWidget(self.bookmarkswidget)
        self.stackedwidget.addWidget(self.assetswidget)
        self.stackedwidget.addWidget(self.fileswidget)
        self.stackedwidget.addWidget(self.favouriteswidget)

        self.init_progress = u'Adding top bar...'
        self.repaint()

        self.listcontrolwidget = ListControlWidget(parent=self)

        self.init_progress = u'Finishing...'
        self.repaint()

        statusbar = QtWidgets.QStatusBar(parent=self)
        statusbar.setSizeGripEnabled(False)

        settings_button = SettingsButton(
            u'info',
            (common.TEXT_SELECTED, common.SECONDARY_TEXT),
            common.INLINE_ICON_SIZE,
            description=u'Click to open the settings',
            parent=self
        )
        settings_button.message.connect(
            lambda s: statusbar.showMessage(s, 4000))
        statusbar.addPermanentWidget(settings_button)
        # statusbar.addPermanentWidget(grip)
        statusbar.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        statusbar.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        statusbar.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )
        statusbar.setFixedHeight(
            common.INLINE_ICON_SIZE + (common.INDICATOR_WIDTH * 2))
        statusbar.layout().setAlignment(QtCore.Qt.AlignRight)

        # statusbar.layout().setContentsMargins(20, 20, 20, 20)
        self.statusbar = statusbar

        self.layout().addWidget(self.listcontrolwidget)
        self.layout().addWidget(self.stackedwidget)
        self.layout().addWidget(self.statusbar)

    def show_preferences(self):
        self.preferences_widget.show()

    def next_tab(self):
        n = self.stackedwidget.currentIndex()
        n += 1
        if n > (self.stackedwidget.count() - 1):
            self.listcontrolwidget.listChanged.emit(0)
            return
        self.listcontrolwidget.listChanged.emit(n)

    def previous_tab(self):
        n = self.stackedwidget.currentIndex()
        n -= 1
        if n < 0:
            n = self.stackedwidget.count() - 1
            self.listcontrolwidget.listChanged.emit(n)
            return
        self.listcontrolwidget.listChanged.emit(n)

    def add_shortcut(self, keys, targets, repeat=False, context=QtCore.Qt.WidgetWithChildrenShortcut):
        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(keys), self)
        shortcut.setAutoRepeat(repeat)
        shortcut.setContext(context)
        for func in targets:
            shortcut.activated.connect(func)
        self.shortcuts.append(shortcut)

    def _add_shortcuts(self):
        lc = self.listcontrolwidget
        self.add_shortcut(
            u'Ctrl+1', (lc._bookmarksbutton.clicked, lc._bookmarksbutton.repaint))
        self.add_shortcut(
            u'Ctrl+2', (lc._assetsbutton.clicked, lc._assetsbutton.repaint))
        self.add_shortcut(
            u'Ctrl+3', (lc._filesbutton.clicked, lc._filesbutton.repaint))
        self.add_shortcut(
            u'Ctrl+4', (lc._favouritesbutton.clicked, lc._favouritesbutton.repaint))
        #
        self.add_shortcut(
            u'Ctrl+N', (lc._addbutton.action, lc._addbutton.repaint))
        self.add_shortcut(
            u'Ctrl+M', (lc._generatethumbnailsbutton.action, lc._generatethumbnailsbutton.repaint))
        self.add_shortcut(
            u'Ctrl+T', (lc._todobutton.action, lc._todobutton.repaint))
        self.add_shortcut(
            u'Ctrl+F', (lc._filterbutton.action, lc._filterbutton.repaint))
        self.add_shortcut(
            u'Ctrl+G', (lc._collapsebutton.action, lc._collapsebutton.repaint))
        self.add_shortcut(
            u'Ctrl+Shift+A', (lc._archivedbutton.action, lc._archivedbutton.repaint))
        self.add_shortcut(
            u'Ctrl+Shift+F', (lc._favouritebutton.action, lc._favouritebutton.repaint))
        self.add_shortcut(
            u'Alt+S', (lc._slackbutton.action, lc._slackbutton.repaint))
        self.add_shortcut(
            u'Ctrl+H', (lc._togglebuttonsbutton.action, lc._togglebuttonsbutton.repaint))
        #
        self.add_shortcut(
            u'Alt+Right', (self.next_tab, ), repeat=True)
        self.add_shortcut(
            u'Alt+Left', (self.previous_tab, ), repeat=True)

    def get_all_threads(self):
        """Returns all running threads associated with GWBrowser.
        The ``BaseThread`` will keep track of all instances so we can use it to querry."""
        return BaseThread._instances.values()

    @QtCore.Slot()
    def terminate(self, quit_app=False):
        """Terminates the browserwidget gracefully by stopping the associated threads.

        """
        self.__qn += 1
        self.statusbar.showMessage(u'Quitting...')

        threadpool = self.get_all_threads()
        for thread in threadpool:
            if thread.isRunning():
                thread.worker.shutdown()
                thread.exit(0)

        if all([not f.isRunning() for f in threadpool]):
            if quit_app:
                self.deleteLater()
                QtWidgets.QApplication.instance().exit(0)
            else:
                self.deleteLater()

        # Forcing the application to close after n tries
        # circa 5 seconds to wrap things up, will exit by force after
        if self.__qn < 20:
            return

        # After that time we will force-terminate the threads
        for thread in threadpool:
            thread.terminate()

        self.deleteLater()
        if quit_app:
            QtWidgets.QApplication.instance().closeAllWindows()
            QtWidgets.QApplication.instance().exit(0)

    def _connectSignals(self):
        """This is where the bulk of the model, view and control widget
        signals and slots are connected.

        """
        b = self.bookmarkswidget
        a = self.assetswidget
        f = self.fileswidget
        ff = self.favouriteswidget
        lc = self.listcontrolwidget

        l = lc.control_view()
        lb = lc.control_button()

        # Progress
        f.model().sourceModel().modelAboutToBeReset.connect(b._progress_widget.show)
        f.model().sourceModel().modelReset.connect(b._progress_widget.hide)
        f.model().sourceModel().modelAboutToBeReset.connect(a._progress_widget.show)
        f.model().sourceModel().modelReset.connect(a._progress_widget.hide)
        f.model().sourceModel().modelAboutToBeReset.connect(ff._progress_widget.show)
        f.model().sourceModel().modelReset.connect(ff._progress_widget.hide)

        s = self.stackedwidget

        self.shutdown.connect(self.shutdown_timer.start)

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
        f.model().modelReset.connect(l.model().modelDataResetRequested)
        f.model().sourceModel().modelReset.connect(l.model().modelDataResetRequested)

        b.activated.connect(
            lambda x: l.model().modelDataResetRequested.emit())
        a.activated.connect(
            lambda x: l.model().modelDataResetRequested.emit())

        b.model().modelReset.connect(lb.repaint)
        b.model().layoutChanged.connect(lb.repaint)
        a.model().modelReset.connect(lb.repaint)
        a.model().layoutChanged.connect(lb.repaint)
        f.model().modelReset.connect(lb.repaint)
        f.model().layoutChanged.connect(lb.repaint)
        ff.model().modelReset.connect(lb.repaint)
        ff.model().layoutChanged.connect(lb.repaint)

        # Active monitor
        # We have to save the states before we respond to the dataKeyChanged
        # signal in the models
        self.active_monitor.activeLocationChanged.connect(
            lambda x: lc.listChanged.emit(2))
        lc.dataKeyChanged.connect(
            lambda x: self.active_monitor.save_state(u'location', x))
        f.model().sourceModel().dataKeyChanged.connect(
            lambda x: self.active_monitor.save_state(u'location', x))
        self.active_monitor.activeLocationChanged.connect(
            f.model().sourceModel().dataKeyChanged)

        # I don't think we have to respond to any active file changes

        # Bookmark/Asset/FileModel/View  <-  DataKeyModel/View
        # These are the signals responsible for changing the active items & data keys.
        lc.dataKeyChanged.connect(f.model().sourceModel().dataKeyChanged)
        f.model().sourceModel().dataKeyChanged.connect(f.model().sourceModel().set_data_key)
        #
        f.model().sourceModel().dataKeyChanged.connect(lambda x: f.model()._filtertext)
        f.model().sourceModel().dataKeyChanged.connect(f.model().sourceModel().check_data)
        f.model().sourceModel().dataKeyChanged.connect(lambda x: f.model().beginResetModel())
        f.model().sourceModel().dataKeyChanged.connect(lambda x: f.model().endResetModel())
        f.model().sourceModel().dataKeyChanged.connect(lambda x: f.model().sourceModel().sort_data())

        # Visible widget
        lc.listChanged.connect(s.setCurrentIndex)
        # Labels
        lc.dataKeyChanged.connect(lc.textChanged)
        lc.textChanged.connect(lb.set_text)
        f.model().sourceModel().dataKeyChanged.connect(lc.textChanged)

        # Stacked widget navigation
        b.activated.connect(lambda: lc.listChanged.emit(1))
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
        lc.listChanged.connect(lb.repaint)
        lc.listChanged.connect(lc._bookmarksbutton.repaint)
        lc.listChanged.connect(lc._assetsbutton.repaint)
        lc.listChanged.connect(lc._filesbutton.repaint)
        lc.listChanged.connect(lc._favouritesbutton.repaint)
        lc.listChanged.connect(lc._addbutton.repaint)
        lc.listChanged.connect(
            lc._generatethumbnailsbutton.repaint)
        lc.listChanged.connect(lc._todobutton.repaint)
        lc.listChanged.connect(lc._filterbutton.repaint)
        lc.listChanged.connect(lc._collapsebutton.repaint)
        lc.listChanged.connect(lc._archivedbutton.repaint)
        lc.listChanged.connect(lc._favouritebutton.repaint)
        lc.listChanged.connect(lc._togglebuttonsbutton.repaint)

        s.currentChanged.connect(lc._bookmarksbutton.repaint)
        s.currentChanged.connect(lc._assetsbutton.repaint)
        s.currentChanged.connect(lc._filesbutton.repaint)
        s.currentChanged.connect(lc._favouritesbutton.repaint)
        s.currentChanged.connect(lc._togglebuttonsbutton.repaint)

        f.model().sourceModel().dataTypeChanged.connect(lc._collapsebutton.repaint)
        ff.model().sourceModel().dataTypeChanged.connect(lc._collapsebutton.repaint)

        b.model().filterFlagChanged.connect(lc._archivedbutton.repaint)
        a.model().filterFlagChanged.connect(lc._archivedbutton.repaint)
        f.model().filterFlagChanged.connect(lc._archivedbutton.repaint)
        ff.model().filterFlagChanged.connect(lc._archivedbutton.repaint)
        b.model().filterFlagChanged.connect(lc._favouritebutton.repaint)
        a.model().filterFlagChanged.connect(lc._favouritebutton.repaint)
        f.model().filterFlagChanged.connect(lc._favouritebutton.repaint)
        ff.model().filterFlagChanged.connect(lc._favouritebutton.repaint)
        b.model().filterFlagChanged.connect(lc._filterbutton.repaint)
        a.model().filterFlagChanged.connect(lc._filterbutton.repaint)
        f.model().filterFlagChanged.connect(lc._filterbutton.repaint)
        ff.model().filterFlagChanged.connect(lc._filterbutton.repaint)

        b.model().filterTextChanged.connect(lc._filterbutton.repaint)
        a.model().filterTextChanged.connect(lc._filterbutton.repaint)
        f.model().filterTextChanged.connect(lc._filterbutton.repaint)
        ff.model().filterTextChanged.connect(lc._filterbutton.repaint)

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
            lambda x: self.active_monitor.save_state(u'server', x.data(common.ParentRole)[0]))
        b.activated.connect(
            lambda x: self.active_monitor.save_state(u'job', x.data(common.ParentRole)[1]))
        b.activated.connect(
            lambda x: self.active_monitor.save_state(u'root', x.data(common.ParentRole)[2]))
        self.active_monitor.activeBookmarkChanged.connect(
            b.model().sourceModel().modelDataResetRequested)
        self.active_monitor.activeBookmarkChanged.connect(
            lambda: lc.listChanged.emit(1))

        a.activated.connect(
            lambda x: self.active_monitor.save_state(u'asset', x.data(common.ParentRole)[-1]))
        self.active_monitor.activeAssetChanged.connect(
            a.model().sourceModel().modelDataResetRequested)
        self.active_monitor.activeAssetChanged.connect(
            lambda: lc.listChanged.emit(1))

        # Progresslabel
        b.model().modelAboutToBeReset.connect(
            lambda: self.statusbar.showMessage(u'Getting bookmarks...', 99999))
        b.model().layoutAboutToBeChanged.connect(
            lambda: self.statusbar.showMessage(u'Getting bookmarks...', 99999))
        b.model().modelReset.connect(lambda: self.statusbar.showMessage(u'', 99999))
        b.model().layoutChanged.connect(lambda: self.statusbar.showMessage(u'', 99999))
        b.model().sourceModel().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))
        b.model().sourceModel().layoutChanged.connect(
            lambda: self.statusbar.showMessage(u'', 99999))

        a.model().modelAboutToBeReset.connect(
            lambda: self.statusbar.showMessage(u'Getting assets...', 99999))
        a.model().layoutAboutToBeChanged.connect(
            lambda: self.statusbar.showMessage(u'Getting assets...', 99999))
        a.model().modelReset.connect(lambda: self.statusbar.showMessage(u'', 99999))
        a.model().layoutChanged.connect(lambda: self.statusbar.showMessage(u'', 99999))
        a.model().sourceModel().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))
        a.model().sourceModel().layoutChanged.connect(
            lambda: self.statusbar.showMessage(u''))

        f.model().modelAboutToBeReset.connect(
            lambda: self.statusbar.showMessage(u'Getting files...', 99999))
        f.model().layoutAboutToBeChanged.connect(
            lambda: self.statusbar.showMessage(u'Getting files...', 99999))
        f.model().modelReset.connect(lambda: self.statusbar.showMessage(u'', 99999))
        f.model().layoutChanged.connect(lambda: self.statusbar.showMessage(u'', 99999))
        f.model().sourceModel().layoutAboutToBeChanged.connect(
            lambda: self.statusbar.showMessage(u'Getting files...'))
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
        painter.drawRoundedRect(rect, 4, 4)

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
        """The widget's default size."""
        return QtCore.QSize(common.WIDTH, common.HEIGHT)

    def showEvent(self, event):
        """Show event. When we first show the widget we will initialize it to
        load the models.

        """
        if not self._initialized:
            self.initializer.start()
        else:
            self.stackedwidget.currentWidget().setFocus()

    def resizeEvent(self, event):
        """Custom resize event."""
        self.resized.emit(self.geometry())


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = BrowserWidget()
    widget.show()
    app.exec_()
