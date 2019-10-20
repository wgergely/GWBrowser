# -*- coding: utf-8 -*-
"""``browserwidget.py`` is the main widget of GWBrowser.
It contains the ``StackedWidget`` and the ``HeaderWidget`` in standalone mode.

"""
import sys
from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser.common as common
from gwbrowser.common_ui import ClickableIconButton, add_row
from gwbrowser.threads import BaseThread
from gwbrowser.baselistwidget import StackedWidget
from gwbrowser.addbookmarkswidget import AddBookmarksWidget
from gwbrowser.bookmarkswidget import BookmarksWidget
from gwbrowser.assetswidget import AssetsWidget
from gwbrowser.fileswidget import FilesWidget
from gwbrowser.favouriteswidget import FavouritesWidget
from gwbrowser.listcontrolwidget import ListControlWidget
from gwbrowser.imagecache import ImageCache
import gwbrowser.settings as Settings
from gwbrowser.settings import local_settings, Active
from gwbrowser.preferenceswidget import PreferencesWidget


DEBUG = False


@QtCore.Slot(unicode)
def debug_signals(label, *args, **kwargs):
    import time
    print u'{time}:{label}     -->     {args}  |  {kwargs}'.format(time='{}'.format(time.time())[:-3], label=label, args=args,kwargs=kwargs)


class SettingsButton(ClickableIconButton):
    """Small version label responsible for displaying information
    about GWBrowser."""

    def __init__(self, pixmap, colors, size, description=u'', parent=None):
        super(SettingsButton, self).__init__(pixmap, colors,
                                             size, description=description, parent=parent)
        self.clicked.connect(self.parent().show_preferences)


class SoloButton(ClickableIconButton):
    """Small version label responsible for displaying information
    about GWBrowser."""

    def __init__(self, parent=None):
        super(SoloButton, self).__init__(
            'settings',
            (common.TEXT, common.TEXT),
            common.INLINE_ICON_SIZE + (common.INDICATOR_WIDTH * 2),
            description='Click to toggle the solo mode.\nWhen on, your bookmark and asset selections won\'t be\nsaved and will revert the next time you start GWBrowser.',
            parent=parent
        )

        self.clicked.connect(self.toggle_solo)
        self.clicked.connect(self.update)

    def state(self):
        return Settings.SOLO

    def toggle_solo(self):
        Settings.SOLO = not Settings.SOLO

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)

        rect = self.rect()
        center = rect.center()
        rect.setWidth(12)
        rect.setHeight(12)
        rect.moveCenter(center)

        color = common.TEXT if self.state() else common.SECONDARY_BACKGROUND
        painter.setBrush(color)
        if self.state():
            painter.drawRect(rect)
        else:
            painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        painter.end()


class BrowserWidget(QtWidgets.QWidget):
    """GWBrowser's main widget."""

    initialized = QtCore.Signal()
    terminated = QtCore.Signal()
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
        self.setMouseTracking(True)

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
        self.preferences_widget = None
        self.add_bookmarks_widget = None

        self.active_monitor = Active(parent=self)

        self.check_active_state_timer = QtCore.QTimer(parent=self)
        self.check_active_state_timer.setInterval(1000)
        self.check_active_state_timer.setSingleShot(False)
        self.check_active_state_timer.setTimerType(QtCore.Qt.CoarseTimer)
        self.check_active_state_timer.timeout.connect(
            self.active_monitor.check_state)

        self.initializer = QtCore.QTimer(parent=self)
        self.initializer.setSingleShot(True)
        self.initializer.setInterval(1000)
        self.initializer.timeout.connect(self.initialize)
        self.initializer.timeout.connect(self.initializer.deleteLater)

        self.shutdown_timer = QtCore.QTimer(parent=self)
        self.shutdown_timer.setInterval(250)
        self.shutdown_timer.setSingleShot(False)

        self.init_progress = u'Loading...'
        # self.adjustSize()
        # self.update()

    @QtCore.Slot()
    def initialize(self):
        """Slot connected to the ``initializer``.

        To make sure the widget is shown as soon as it is created, we're
        initiating the ui and the models with a little delay. Settings saved in the
        local_settings are applied after the ui is initialized and the models
        finished loading their data.

        """
        def emit_saved_state(flag):
            b.filterFlagChanged.emit(flag, b.filterFlag(flag))
            a.filterFlagChanged.emit(flag, a.filterFlag(flag))
            f.filterFlagChanged.emit(flag, f.filterFlag(flag))
            ff.filterFlagChanged.emit(flag, ff.filterFlag(flag))

        self.shortcuts = []
        if self._initialized:
            return

        self._createUI()
        if DEBUG:
            self._connectDebugSignals()
        self._connectSignals()
        self._add_shortcuts()

        if common.get_platform() == u'mac':
            self.active_monitor.macos_mount_timer.start()

        Active.paths()

        # Proxy model
        b = self.bookmarkswidget.model()
        a = self.assetswidget.model()
        f = self.fileswidget.model()
        ff = self.favouriteswidget.model()

        b.filterTextChanged.emit(b.filter_text())
        a.filterTextChanged.emit(a.filter_text())
        f.filterTextChanged.emit(f.filter_text())
        ff.filterTextChanged.emit(ff.filter_text())

        for flag in (common.MarkedAsActive, common.MarkedAsActive, common.MarkedAsFavourite):
            emit_saved_state(flag)

        b.sourceModel().modelDataResetRequested.emit()
        self.check_active_state_timer.start()
        idx = local_settings.value(u'widget/mode')
        self.listcontrolwidget.listChanged.emit(idx)
        self.stackedwidget.currentWidget().setFocus()

        if local_settings.value(u'firstrun') is None:
            local_settings.setValue(u'firstrun', False)

        self._initialized = True
        self.initialized.emit()

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

        self.init_progress = u'Creating bookmarks tab...'
        self.update()

        self.bookmarkswidget = BookmarksWidget(parent=self)

        self.init_progress = u'Creating assets tab...'
        self.update()

        self.assetswidget = AssetsWidget(parent=self)

        self.init_progress = u'Creating files tab...'
        self.update()

        self.fileswidget = FilesWidget(parent=self)
        self.favouriteswidget = FavouritesWidget(parent=self)
        self.preferences_widget = PreferencesWidget(parent=self)
        self.preferences_widget.hide()
        self.add_bookmarks_widget = AddBookmarksWidget(parent=self)
        self.add_bookmarks_widget.hide()

        self.stackedwidget.addWidget(self.bookmarkswidget)
        self.stackedwidget.addWidget(self.assetswidget)
        self.stackedwidget.addWidget(self.fileswidget)
        self.stackedwidget.addWidget(self.favouriteswidget)
        self.stackedwidget.addWidget(self.preferences_widget)
        self.stackedwidget.addWidget(self.add_bookmarks_widget)

        self.init_progress = u'Adding top bar...'
        self.update()

        self.listcontrolwidget = ListControlWidget(parent=self)

        self.init_progress = u'Finishing...'
        self.update()

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

        statusbar.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        statusbar.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        statusbar.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )
        height = common.INLINE_ICON_SIZE + (common.INDICATOR_WIDTH * 2)
        statusbar.setFixedHeight(height)
        statusbar.layout().setAlignment(QtCore.Qt.AlignRight)

        # statusbar.layout().setContentsMargins(20, 20, 20, 20)
        self.statusbar = statusbar

        self.layout().addWidget(self.listcontrolwidget)
        self.layout().addWidget(self.stackedwidget)

        row = add_row('', height=height, parent=self)
        row.layout().setSpacing(0)
        row.layout().addWidget(self.statusbar)
        row.layout().addWidget(settings_button)

        solo_button = SoloButton(parent=self)
        row.layout().addWidget(solo_button)

    def show_preferences(self):
        self.stackedwidget.setCurrentIndex(4)

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
            u'Ctrl+1', (lc.bookmarks_button.clicked, lc.bookmarks_button.update))
        self.add_shortcut(
            u'Ctrl+2', (lc.assets_button.clicked, lc.assets_button.update))
        self.add_shortcut(
            u'Ctrl+3', (lc.files_button.clicked, lc.files_button.update))
        self.add_shortcut(
            u'Ctrl+4', (lc.favourites_button.clicked, lc.favourites_button.update))
        #
        self.add_shortcut(
            u'Ctrl+M', (lc.generate_thumbnails_button.action, lc.generate_thumbnails_button.update))
        self.add_shortcut(
            u'Ctrl+F', (lc.filter_button.action, lc.filter_button.update))
        self.add_shortcut(
            u'Ctrl+G', (lc.collapse_button.action, lc.collapse_button.update))
        self.add_shortcut(
            u'Ctrl+Shift+A', (lc.archived_button.action, lc.archived_button.update))
        self.add_shortcut(
            u'Ctrl+Shift+F', (lc.favourite_button.action, lc.favourite_button.update))
        self.add_shortcut(
            u'Alt+S', (lc.slack_button.action, lc.slack_button.update))
        self.add_shortcut(
            u'Ctrl+H', (lc.simple_mode_button.action, lc.simple_mode_button.update))
        #
        self.add_shortcut(
            u'Alt+Right', (self.next_tab, ), repeat=True)
        self.add_shortcut(
            u'Alt+Left', (self.previous_tab, ), repeat=True)
        #
        self.add_shortcut(
            u'Ctrl++', (self.increase_row_size, ), repeat=True)
        self.add_shortcut(
            u'Ctrl+-', (self.decrease_row_size, ), repeat=True)

    def decrease_row_size(self):
        import gwbrowser.delegate as d
        if (d.ROW_HEIGHT - 12.0) < common.ROW_HEIGHT:
            return
        d.ROW_HEIGHT -= 12.0
        d.SMALL_FONT_SIZE -= 1.0
        for n in xrange(self.stackedwidget.count()):
            self.stackedwidget.widget(2).reset()

    def increase_row_size(self):
        import gwbrowser.delegate as d
        if (d.ROW_HEIGHT + 12.0) > common.ASSET_ROW_HEIGHT:
            return
        d.ROW_HEIGHT += 12.0
        d.SMALL_FONT_SIZE += 1.0
        for n in xrange(self.stackedwidget.count()):
            if n >= 3:
                continue
            self.stackedwidget.widget(n).reset()

    def get_all_threads(self):
        """Returns all running threads associated with GWBrowser.
        The ``BaseThread`` will keep track of all instances so we can use it to querry."""
        return BaseThread._instances.values()

    @QtCore.Slot()
    def terminate(self, quit_app=False):
        """Terminates the browserwidget gracefully by stopping the associated
        threads.

        """
        self.__qn += 1
        self.statusbar.showMessage(u'Closing down...')

        self.listcontrolwidget.bookmarks_button.timer.stop()
        self.listcontrolwidget.assets_button.timer.stop()
        self.listcontrolwidget.files_button.timer.stop()
        self.listcontrolwidget.favourites_button.timer.stop()

        self.bookmarkswidget.timer.stop()
        self.assetswidget.timer.stop()
        self.fileswidget.timer.stop()
        self.favouriteswidget.timer.stop()
        self.check_active_state_timer.stop()

        threadpool = self.get_all_threads()
        for thread in threadpool:
            if thread.isRunning():
                thread.worker.shutdown()
                thread.exit(0)

        if all([not f.isRunning() for f in threadpool]):
            if quit_app:
                QtWidgets.QApplication.instance().exit(0)

        # Forcing the application to close after n tries
        # circa 5 seconds to wrap things up, will exit by force after
        if self.__qn < 20:
            return

        # After that time we will force-terminate the threads
        for thread in threadpool:
            thread.terminate()

        if quit_app:
            QtWidgets.QApplication.instance().closeAllWindows()
            QtWidgets.QApplication.instance().exit(0)

        sys.stdout.write(u'# GWBrowser terminated.\n')
        self.terminated.emit()

    @QtCore.Slot(unicode)
    def show_progress_message(self, message):
        b = self.bookmarkswidget.progress_widget
        a = self.assetswidget.progress_widget
        f = self.fileswidget.progress_widget
        ff = self.favouriteswidget.progress_widget
        progress_widgets = (b, a, f, ff)
        for widget in progress_widgets:
            widget.show()
            widget.set_message(message)
            # widget.update()
            widget.repaint()

    @QtCore.Slot()
    def hide_progress_message(self):
        b = self.bookmarkswidget.progress_widget
        a = self.assetswidget.progress_widget
        f = self.fileswidget.progress_widget
        ff = self.favouriteswidget.progress_widget
        progress_widgets = (b, a, f, ff)
        for widget in progress_widgets:
            widget.hide()
            widget.set_message(u'Loading...')

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
        s = self.stackedwidget

        #####################################################
        self.shutdown.connect(self.shutdown_timer.start)
        #####################################################
        lc.bookmarks_button.clicked.connect(
            lambda: lc.listChanged.emit(0))
        lc.assets_button.clicked.connect(
            lambda: lc.listChanged.emit(1))
        lc.files_button.clicked.connect(
            lambda: lc.listChanged.emit(2))
        lc.favourites_button.clicked.connect(
            lambda: lc.listChanged.emit(3))
        #####################################################
        # Active monitor
        b.activated.connect(
            lambda x: self.active_monitor.save_state(u'server', x.data(common.ParentPathRole)[0]))
        b.activated.connect(
            lambda x: self.active_monitor.save_state(u'job', x.data(common.ParentPathRole)[1]))
        b.activated.connect(
            lambda x: self.active_monitor.save_state(u'root', x.data(common.ParentPathRole)[2]))
        a.activated.connect(
            lambda x: self.active_monitor.save_state(u'asset', x.data(common.ParentPathRole)[-1]))
        f.model().sourceModel().dataKeyChanged.connect(
            lambda x: self.active_monitor.save_state(u'location', x))
        #####################################################
        # Linkage between the different tabs are established here
        # Fist, the parent paths are set
        b.model().sourceModel().modelReset.connect(
            lambda: a.model().sourceModel().set_active(b.model().sourceModel().active_index()))
        b.model().sourceModel().activeChanged.connect(
            a.model().sourceModel().set_active)
        a.model().sourceModel().modelReset.connect(
            lambda: f.model().sourceModel().set_active(a.model().sourceModel().active_index()))
        a.model().sourceModel().activeChanged.connect(
            f.model().sourceModel().set_active)

        b.model().sourceModel().modelReset.connect(
            a.model().sourceModel().modelDataResetRequested)
        b.model().sourceModel().activeChanged.connect(
            a.model().sourceModel().modelDataResetRequested)
        b.model().sourceModel().activeChanged.connect(
            l.model().modelDataResetRequested)
        a.model().sourceModel().modelReset.connect(
            f.model().sourceModel().modelDataResetRequested)
        a.model().sourceModel().activeChanged.connect(
            f.model().sourceModel().modelDataResetRequested)
        a.model().sourceModel().activeChanged.connect(
            l.model().modelDataResetRequested)
        f.model().sourceModel().modelDataResetRequested.connect(
            l.model().modelDataResetRequested)

        ff.favouritesChanged.connect(ff.model().sourceModel().modelDataResetRequested)
        #####################################################
        # Stacked widget navigation
        lc.listChanged.connect(s.setCurrentIndex)
        b.activated.connect(lambda: lc.listChanged.emit(1))
        a.activated.connect(lambda: lc.listChanged.emit(2))
        b.model().sourceModel().activeChanged.connect(lambda x: lc.listChanged.emit(1))
        a.model().sourceModel().activeChanged.connect(lambda x: lc.listChanged.emit(2))
        #####################################################
        @QtCore.Slot(unicode)
        def set_filter_text(data_key):
            model = f.model().sourceModel()
            cls = model.__class__.__name__
            k = u'widget/{}/{}/filtertext'.format(cls, data_key)
            f.model().set_filter_text(local_settings.value(k))


        f.model().sourceModel().dataKeyChanged.connect(
            f.model().sourceModel().set_data_key)
        f.model().sourceModel().dataKeyChanged.connect(
            f.model().sourceModel().reset_thread_worker_queues)
        f.model().sourceModel().dataKeyChanged.connect(
            lambda *a: f.model().sourceModel().set_data_type(f.model().sourceModel().data_type()))
        f.model().sourceModel().dataKeyChanged.connect(
            f.model().sourceModel().check_data)
        f.model().sourceModel().dataKeyChanged.connect(set_filter_text)
        f.model().sourceModel().dataKeyChanged.connect(f.model().invalidate)
        f.model().sourceModel().dataKeyChanged.connect(f.reselect_previous)

        # Control bar connections
        lc.dataKeyChanged.connect(f.model().sourceModel().dataKeyChanged)
        lc.dataKeyChanged.connect(lc.textChanged)
        f.model().sourceModel().dataKeyChanged.connect(lc.textChanged)
        #####################################################
        # Active monitor
        self.active_monitor.activeBookmarkChanged.connect(
            b.model().sourceModel().modelDataResetRequested)
        self.active_monitor.activeAssetChanged.connect(
            a.model().sourceModel().modelDataResetRequested)
        self.active_monitor.activeLocationChanged.connect(
            f.model().sourceModel().dataKeyChanged)
        self.active_monitor.activeLocationChanged.connect(
            l.model().modelDataResetRequested)
        self.active_monitor.activeLocationChanged.connect(
            l.model().dataKeyChanged)
        #####################################################
        b.activated.connect(
            lambda: lc.textChanged.emit(f.model().sourceModel().data_key()) if f.model().sourceModel().data_key() else 'Files')
        b.model().sourceModel().activeChanged.connect(
            lambda x: lc.textChanged.emit(f.model().sourceModel().data_key()) if f.model().sourceModel().data_key() else 'Files')
        a.activated.connect(
            lambda: lc.textChanged.emit(f.model().sourceModel().data_key()) if f.model().sourceModel().data_key() else 'Files')
        a.model().sourceModel().activeChanged.connect(
            lambda x: lc.textChanged.emit(f.model().sourceModel().data_key()) if f.model().sourceModel().data_key() else 'Files')
        #####################################################
        # b.model().sourceModel().activeChanged.connect(
        #     lambda x: lc.textChanged.emit(u'Files'))
        # Updates the list-control buttons when changing lists
        lc.listChanged.connect(lb.update)
        lc.listChanged.connect(lc.update_buttons)

        self.stackedwidget.animationFinished.connect(lc.update_buttons)
        s.currentChanged.connect(lc.bookmarks_button.update)

        f.model().sourceModel().dataTypeChanged.connect(lc.update_buttons)
        ff.model().sourceModel().dataTypeChanged.connect(lc.update_buttons)
        b.model().filterFlagChanged.connect(lc.update_buttons)
        a.model().filterFlagChanged.connect(lc.update_buttons)
        f.model().filterFlagChanged.connect(lc.update_buttons)
        ff.model().filterFlagChanged.connect(lc.update_buttons)
        b.model().filterTextChanged.connect(lc.update_buttons)
        a.model().filterTextChanged.connect(lc.update_buttons)
        f.model().filterTextChanged.connect(lc.update_buttons)
        ff.model().filterTextChanged.connect(lc.update_buttons)
        b.model().modelReset.connect(lc.update_buttons)
        a.model().modelReset.connect(lc.update_buttons)
        f.model().modelReset.connect(lc.update_buttons)
        ff.model().modelReset.connect(lc.update_buttons)

        b.model().modelReset.connect(lb.update)
        a.model().modelReset.connect(lb.update)
        f.model().modelReset.connect(lb.update)
        ff.model().modelReset.connect(lb.update)
        ########################################################################
        # Messages
        b.model().modelAboutToBeReset.connect(
            lambda: self.statusbar.showMessage(u'Getting bookmarks...', 99999))
        b.model().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))
        b.model().sourceModel().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))

        a.model().modelAboutToBeReset.connect(
            lambda: self.statusbar.showMessage(u'Getting assets...', 99999))
        a.model().modelReset.connect(lambda: self.statusbar.showMessage(u'', 99999))
        a.model().sourceModel().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))
        f.model().modelAboutToBeReset.connect(
            lambda: self.statusbar.showMessage(u'Getting files...', 99999))
        f.model().modelReset.connect(lambda: self.statusbar.showMessage(u'', 99999))
        f.model().sourceModel().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))
        b.model().sourceModel().messageChanged.connect(
            lambda m: self.statusbar.showMessage(m, 99999))
        a.model().sourceModel().messageChanged.connect(
            lambda m: self.statusbar.showMessage(m, 99999))
        f.model().sourceModel().messageChanged.connect(
            lambda m: self.statusbar.showMessage(m, 99999))
        ff.model().sourceModel().messageChanged.connect(
            lambda m: self.statusbar.showMessage(m, 99999))


        # Statusbar
        b.entered.connect(self.entered)
        a.entered.connect(self.entered)
        f.entered.connect(self.entered)
        ff.entered.connect(self.entered)
        l.entered.connect(self.entered)
        lc.bookmarks_button.message.connect(self.entered2)
        lc.assets_button.message.connect(self.entered2)
        lc.files_button.message.connect(self.entered2)
        lc.favourites_button.message.connect(self.entered2)
        lc.generate_thumbnails_button.message.connect(self.entered2)
        lc.filter_button.message.connect(self.entered2)
        lc.collapse_button.message.connect(self.entered2)
        lc.archived_button.message.connect(self.entered2)
        lc.simple_mode_button.message.connect(self.entered2)
        lc.favourite_button.message.connect(self.entered2)
        lc.slack_button.message.connect(self.entered2)

    def _connectDebugSignals(self):
        b = self.bookmarkswidget
        a = self.assetswidget
        f = self.fileswidget
        ff = self.favouriteswidget
        lc = self.listcontrolwidget
        l = lc.control_view()
        lb = lc.control_button()

        ###############################################
        b.model().sourceModel().dataSorted.connect(
            lambda *a, **kw: debug_signals('bookmarks:source   dataSorted', *a, **kw))
        b.model().sourceModel().modelAboutToBeReset.connect(
            lambda *a, **kw: debug_signals('bookmarks:source   modelAboutToBeReset', *a, **kw))
        b.model().modelAboutToBeReset.connect(
            lambda *a, **kw: debug_signals('bookmarks:proxy    modelAboutToBeReset', *a, **kw))
        b.model().sourceModel().modelReset.connect(
            lambda *a, **kw: debug_signals('bookmarks:source   modelReset', *a, **kw))
        b.model().modelReset.connect(
            lambda *a, **kw: debug_signals('bookmarks:proxy    modelReset', *a, **kw))
        ################################################
        a.model().sourceModel().dataSorted.connect(
            lambda *a, **kw: debug_signals('assets:source      dataSorted', *a, **kw))
        a.model().sourceModel().modelAboutToBeReset.connect(
            lambda *a, **kw: debug_signals('assets:source      modelAboutToBeReset', *a, **kw))
        a.model().modelAboutToBeReset.connect(
            lambda *a, **kw: debug_signals('assets:proxy       modelAboutToBeReset', *a, **kw))
        a.model().sourceModel().modelReset.connect(
            lambda *a, **kw: debug_signals('assets:source      modelReset', *a, **kw))
        a.model().modelReset.connect(
            lambda *a, **kw: debug_signals('assets:proxy       modelReset', *a, **kw))
        ###############################################
        f.model().sourceModel().dataSorted.connect(
            lambda *a, **kw: debug_signals('files:source       dataSorted', *a, **kw))
        f.model().sourceModel().modelAboutToBeReset.connect(
            lambda *a, **kw: debug_signals('files:source       modelAboutToBeReset', *a, **kw))
        f.model().modelAboutToBeReset.connect(
            lambda *a, **kw: debug_signals('files:proxy        modelAboutToBeReset', *a, **kw))
        f.model().sourceModel().modelReset.connect(
            lambda *a, **kw: debug_signals('files:source       modelReset', *a, **kw))
        f.model().modelReset.connect(
            lambda *a, **kw: debug_signals('files:proxy        modelReset', *a, **kw))
        ################################################
        f.model().sourceModel().dataKeyChanged.connect(
            lambda *a, **kw: debug_signals('files:source       dataKeyChanged', *a, **kw))
        f.model().sourceModel().dataTypeChanged.connect(
            lambda *a, **kw: debug_signals('files:source       dataTypeChanged', *a, **kw))
        f.model().sourceModel().sortingChanged.connect(
            lambda *a, **kw: debug_signals('files:source       sortingChanged', *a, **kw))
        f.model().filterFlagChanged.connect(
            lambda *a, **kw: debug_signals('files:source       filterFlagChanged', *a, **kw))
        f.model().filterTextChanged.connect(
            lambda *a, **kw: debug_signals('files:source       filterTextChanged', *a, **kw))
        ################################################

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
        painter.drawRoundedRect(rect, 10, 10)

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
            return
        self.stackedwidget.currentWidget().setFocus()


    def resizeEvent(self, event):
        """Custom resize event."""
        self.resized.emit(self.geometry())


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = BrowserWidget()
    widget.show()
    app.exec_()
