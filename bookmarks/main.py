# -*- coding: utf-8 -*-
"""Bookmarks's main widget.

This is where the UI is assembled and signals & slots are connected.

"""
import gc
import functools
from PySide2 import QtWidgets, QtGui, QtCore

from . import log
from . import common
from . import common_ui
from . import images
from . import settings
from . import threads
from . import contextmenu
from . import topbar
from . import shortcuts
from . import actions
from . import rv

from .lists import base
from .lists import assets
from .lists import bookmarks
from .lists import favourites
from .lists import files


_instance = None


def instance():
    return _instance


class StatusBar(QtWidgets.QStatusBar):
    """Bookmarks's statusbar on the bottom of the window.

    """

    def __init__(self, height, parent=None):
        super(StatusBar, self).__init__(parent=parent)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.setSizeGripEnabled(False)
        self.setFixedHeight(height)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        font, _ = common.font_db.secondary_font(common.SMALL_FONT_SIZE())
        common.draw_aliased_text(
            painter,
            font,
            self.rect().marginsRemoved(QtCore.QMargins(
                common.INDICATOR_WIDTH(), 0, common.INDICATOR_WIDTH(), 0)),
            u'  {}  '.format(self.currentMessage()),
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            common.TEXT
        )
        painter.end()


class ToggleModeButton(QtWidgets.QWidget):
    """The button used to switch between syncronised and solo modes."""
    clicked = QtCore.Signal()
    message = QtCore.Signal(unicode)

    def __init__(self, size, parent=None):
        super(ToggleModeButton, self).__init__(parent=parent)
        self.setFixedSize(size, size)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.animation_value = 1.0
        self.animation = QtCore.QVariantAnimation(parent=self)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.5)
        self.animation.setEasingCurve(QtCore.QEasingCurve.InCubic)
        self.animation.setLoopCount(1)  # Loops for forever
        self.animation.setDirection(QtCore.QAbstractAnimation.Forward)
        self.animation.setDuration(1500)
        self.animation.valueChanged.connect(self.update)
        self.animation.finished.connect(self.reverse_direction)
        self.clicked.connect(self.toggle_mode)

    def statusTip(self):
        if settings.local_settings.current_mode() == common.SynchronisedMode:
            return u'Instance is syncronised. Click to toggle.'
        elif settings.local_settings.current_mode() == common.SoloMode:
            return u'Instance not synronised. Click to toggle.'
        return u'Invalid mode.'

    @QtCore.Slot()
    def reverse_direction(self):
        """ A bounce."""
        if self.animation.direction() == QtCore.QPropertyAnimation.Forward:
            self.animation.setDirection(QtCore.QPropertyAnimation.Backward)
        else:
            self.animation.setDirection(QtCore.QPropertyAnimation.Forward)
        self.animation.start()
        self.update()

    @QtCore.Slot()
    def toggle_mode(self):
        """Simply toggles the solo mode."""
        settings.local_settings.sync()

        if settings.local_settings.current_mode() == common.SynchronisedMode:
            settings.local_settings.set_mode(common.SoloMode)
            self.animation.setCurrentTime(0)
            self.animation.start()
        elif settings.local_settings.current_mode() == common.SoloMode:
            settings.local_settings.set_mode(common.SynchronisedMode)
            self.animation.setCurrentTime(0)
            self.animation.stop()

        self.update()
        settings.local_settings.sync()
        settings.local_settings.save_mode_lockfile()
        settings.local_settings.load_and_verify_stored_paths()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtCore.Qt.NoBrush)

        color = common.REMOVE if settings.local_settings.current_mode() else common.ADD
        pen = QtGui.QPen(color)

        o = common.INDICATOR_WIDTH() * 1.5
        pen.setWidth(common.INDICATOR_WIDTH() * 0.66)
        painter.setPen(pen)
        painter.setOpacity(self.animation.currentValue())
        rect = QtCore.QRect(self.rect())
        rect = rect.marginsRemoved(QtCore.QMargins(o, o, o, o))
        center = self.rect().center()

        size = QtCore.QSize(rect.width() - (o), rect.height() - (o))
        rect.setSize(size * self.animation.currentValue())
        rect.moveCenter(center)
        c = rect.height() / 2.0
        painter.drawRoundedRect(rect, c, c)

        painter.end()

    def enterEvent(self, event):
        self.message.emit(self.statusTip())

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        cursor_position = self.mapFromGlobal(common.cursor.pos())
        if self.rect().contains(cursor_position):
            self.clicked.emit()

    def showEvent(self, event):
        if settings.local_settings.current_mode() == common.SoloMode:
            self.animation.setCurrentTime(0)
            self.animation.start()
            self.update()
        elif settings.local_settings.current_mode() == common.SynchronisedMode:
            self.animation.setCurrentTime(0)
            self.animation.stop()
            self.update()



class MainWidget(QtWidgets.QWidget):
    """Our super-duper main widget.

    Contains the list control bar with the tab buttons, the stacked widget
    containing the Bookmark-, Asset-, File- and FavouriteWidgets and the
    statusbar.

    """
    initialized = QtCore.Signal()
    terminated = QtCore.Signal()
    shutdown = QtCore.Signal()

    def __init__(self, parent=None):
        global _instance
        if _instance is not None:
            raise RuntimeError(
                '{} cannot be initialised more than once.'.format(self.__class__.__name__))
        _instance = self

        super(MainWidget, self).__init__(parent=parent)

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'icon', None, common.ASSET_ROW_HEIGHT())
        self.setWindowIcon(QtGui.QIcon(pixmap))

        self._contextMenu = None
        self._initialized = False
        self.shortcuts = []

        self.stackedwidget = None
        self.bookmarkswidget = None
        self.topbar = None
        self.assetswidget = None
        self.fileswidget = None
        self.favouriteswidget = None
        self.statusbar = None
        self.solo_button = None

        self.thread_monitor = None

        self.initializer = QtCore.QTimer(parent=self)
        self.initializer.setSingleShot(True)
        self.initializer.setInterval(1000)
        self.initializer.timeout.connect(self.initialize)

        self.init_progress = u'Loading...'

    @common.debug
    @common.error
    def _create_ui(self):
        o = 0
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
        )

        self.stackedwidget = base.StackedWidget(parent=self)
        self.bookmarkswidget = bookmarks.BookmarksWidget(parent=self)
        self.assetswidget = assets.AssetsWidget(parent=self)
        self.fileswidget = files.FilesWidget(parent=self)
        self.favouriteswidget = favourites.FavouritesWidget(parent=self)

        self.stackedwidget.addWidget(self.bookmarkswidget)
        self.stackedwidget.addWidget(self.assetswidget)
        self.stackedwidget.addWidget(self.fileswidget)
        self.stackedwidget.addWidget(self.favouriteswidget)

        # Setting the tab now before we do any more initialisation
        idx = settings.local_settings.value(
            settings.UIStateSection,
            settings.CurrentList
        )
        idx = 0 if idx is None or False else idx
        idx = 0 if idx < 0 else idx
        idx = 3 if idx > 3 else idx
        self.stackedwidget._setCurrentIndex(idx)

        self.topbar = topbar.ListControlWidget(parent=self)

        self.layout().addWidget(self.topbar)
        self.layout().addWidget(self.stackedwidget)

        height = common.MARGIN() + (common.INDICATOR_WIDTH() * 2)
        row = common_ui.add_row(None, padding=0, height=height, parent=self)
        row.layout().setSpacing(0)
        row.layout().setContentsMargins(0, 0, 0, 0)

        self.statusbar = StatusBar(height, parent=self)
        self.solo_button = ToggleModeButton(height, parent=self)
        self.solo_button.message.connect(
            lambda s: self.statusbar.showMessage(s, 4000))

        self.thread_monitor = threads.ThreadMonitor(parent=self)

        row.layout().addWidget(self.thread_monitor, 0)
        row.layout().addWidget(self.statusbar, 1)
        row.layout().addWidget(self.solo_button, 0)

    @common.debug
    @common.error
    def _connect_signals(self):
        """This is where the bulk of the model, view and control widget
        signals and slots are connected.

        """
        b = self.bookmarkswidget
        a = self.assetswidget
        f = self.fileswidget
        ff = self.favouriteswidget
        lc = self.topbar
        l = lc.control_view()
        lb = lc.control_button()
        s = self.stackedwidget

        lc.bookmarks_button.clicked.connect(
            lambda: lc.listChanged.emit(base.BookmarkTab))
        lc.assets_button.clicked.connect(
            lambda: lc.listChanged.emit(base.AssetTab))
        lc.files_button.clicked.connect(
            lambda: lc.listChanged.emit(base.FileTab))
        lc.favourites_button.clicked.connect(
            lambda: lc.listChanged.emit(base.FavouriteTab))
        #####################################################
        # Bookmark -> Asset
        b.model().sourceModel().activeChanged.connect(
            a.model().sourceModel().modelDataResetRequested)
        a.model().sourceModel().activeChanged.connect(
            f.model().sourceModel().modelDataResetRequested)

        # * -> Listcontrol
        b.model().sourceModel().activeChanged.connect(
            l.model().modelDataResetRequested)
        a.model().sourceModel().activeChanged.connect(
            l.model().modelDataResetRequested)
        f.model().sourceModel().modelDataResetRequested.connect(
            l.model().modelDataResetRequested)

        #####################################################
        # Stacked widget navigation
        lc.listChanged.connect(s.setCurrentIndex)
        b.activated.connect(lambda: lc.listChanged.emit(1))
        a.activated.connect(lambda: lc.listChanged.emit(2))

        a.model().sourceModel().activeChanged.connect(l.model().check_task)
        a.activated.connect(l.model().check_task)
        lc.listChanged.connect(l.model().check_task)

        # Control bar connections
        lc.taskFolderChanged.connect(f.model().sourceModel().taskFolderChanged)
        lc.taskFolderChanged.connect(lc.textChanged)
        f.model().sourceModel().taskFolderChanged.connect(lc.textChanged)

        #####################################################

        b.activated.connect(
            lambda: lc.textChanged.emit(f.model().sourceModel().task()) if f.model().sourceModel().task() else 'Files')
        b.model().sourceModel().activeChanged.connect(
            lambda x: lc.textChanged.emit(f.model().sourceModel().task()) if f.model().sourceModel().task() else 'Files')
        a.activated.connect(
            lambda: lc.textChanged.emit(f.model().sourceModel().task()) if f.model().sourceModel().task() else 'Files')
        a.model().sourceModel().activeChanged.connect(
            lambda x: lc.textChanged.emit(f.model().sourceModel().task()) if f.model().sourceModel().task() else 'Files')

        #####################################################

        lc.listChanged.connect(lb.update)
        lc.listChanged.connect(lc.update_buttons)

        s.currentChanged.connect(lc.update_buttons)
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
            lambda: self.statusbar.showMessage(u'Loading bookmarks...', 99999))
        b.model().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))
        b.model().sourceModel().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))

        a.model().modelAboutToBeReset.connect(
            lambda: self.statusbar.showMessage(u'Loading assets...', 99999))
        a.model().modelReset.connect(lambda: self.statusbar.showMessage(u'', 99999))
        a.model().sourceModel().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))
        f.model().modelAboutToBeReset.connect(
            lambda: self.statusbar.showMessage(u'Loading files...', 99999))
        f.model().modelReset.connect(lambda: self.statusbar.showMessage(u'', 99999))

        f.model().sourceModel().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))
        b.model().sourceModel().progressMessage.connect(
            lambda m: self.statusbar.showMessage(m, 99999))
        a.model().sourceModel().progressMessage.connect(
            lambda m: self.statusbar.showMessage(m, 99999))
        f.model().sourceModel().progressMessage.connect(
            lambda m: self.statusbar.showMessage(m, 99999))
        ff.model().sourceModel().progressMessage.connect(
            lambda m: self.statusbar.showMessage(m, 99999))
        #############################################################
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
        #####################################################
        b.model().sourceModel().activeChanged.connect(lc.slack_button.check_token)
        #####################################################
        f.model().sourceModel().taskFolderChanged.connect(f.model().sourceModel().init_row_size)
        f.model().sourceModel().taskFolderChanged.connect(f.reset_row_layout)
        #####################################################
        lc.taskswidget.connect_signals()

    @common.error
    @common.debug
    def destroy_ui(self):
        """Destroys child widgets, all associated timers and helper classes.

        """
        settings.local_settings.server_mount_timer.stop()

        self.topbar.bookmarks_button.timer.stop()
        self.topbar.assets_button.timer.stop()
        self.topbar.files_button.timer.stop()
        self.topbar.favourites_button.timer.stop()

        self.bookmarkswidget.timer.stop()
        self.assetswidget.timer.stop()
        self.fileswidget.timer.stop()
        self.favouriteswidget.timer.stop()

        self.hide()
        self.setUpdatesEnabled(False)
        self.deleteLater()

        for widget in (
            self.bookmarkswidget,
            self.assetswidget,
            self.fileswidget,
            self.favouriteswidget,
            self.topbar.taskswidget
        ):
            try:
                widget.removeEventFilter(self)
                widget.hide()
                widget.setUpdatesEnabled(False)
                widget.blockSignals(True)

                if hasattr(widget, 'timer'):
                    widget.timer.stop()
                if hasattr(widget, 'request_visible_fileinfo_timer'):
                    widget.request_visible_fileinfo_timer.stop()
                if hasattr(widget, 'request_visible_thumbnail_timer'):
                    widget.request_visible_thumbnail_timer.stop()
                if hasattr(widget, 'queue_model_timer'):
                    widget.queue_model_timer.stop()
                if hasattr(widget.model(), 'sourceModel'):
                    widget.model().sourceModel().deleteLater()
                widget.model().deleteLater()
                widget.deleteLater()

                for child in widget.children():
                    child.deleteLater()
            except Exception as err:
                log.error(u'Error occured deleteing the ui.')

        for widget in (self.topbar, self.stackedwidget, self.statusbar):
            widget.setUpdatesEnabled(False)
            widget.blockSignals(True)
            widget.hide()
            widget.deleteLater()
            for child in widget.children():
                child.deleteLater()

        images.ImageCache.INTERNAL_MODEL_DATA = None

        settings.local_settings.deleteLater()
        settings.local_settings = None
        gc.collect()


    @QtCore.Slot()
    def initialize(self):
        """Slot connected to the ``initializer``.

        To make sure the widget is shown as soon as it is created, we're
        initiating the ui and the models with a little delay. Settings saved in the
        local_settings are applied after the ui is initialized and the models
        finished loading their data.

        """
        if self._initialized:
            return

        def emit_saved_states():
            for flag in (common.MarkedAsActive, common.MarkedAsActive, common.MarkedAsFavourite):
                b.filterFlagChanged.emit(flag, b.filter_flag(flag))
                a.filterFlagChanged.emit(flag, a.filter_flag(flag))
                f.filterFlagChanged.emit(flag, f.filter_flag(flag))
                ff.filterFlagChanged.emit(flag, ff.filter_flag(flag))

        settings.local_settings.touch_mode_lockfile()
        settings.local_settings.save_mode_lockfile()

        self._init_shortcuts()
        self._create_ui()
        self._connect_signals()

        settings.local_settings.load_and_verify_stored_paths()

        # Proxy model
        b = self.bookmarkswidget.model()
        a = self.assetswidget.model()
        f = self.fileswidget.model()
        ff = self.favouriteswidget.model()

        b.filterTextChanged.emit(b.filter_text())
        a.filterTextChanged.emit(a.filter_text())
        f.filterTextChanged.emit(f.filter_text())
        ff.filterTextChanged.emit(ff.filter_text())

        emit_saved_states()

        b.sourceModel().modelDataResetRequested.emit()

        @QtCore.Slot(QtCore.QModelIndex)
        def update_window_title(index):
            if not index.isValid():
                return
            if not index.data(common.ParentPathRole):
                return
            p = list(index.data(common.ParentPathRole))
            s = u'/'.join(p)
            self.setWindowTitle(s.upper())

        for n in xrange(3):
            model = self.stackedwidget.widget(n).model().sourceModel()
            model.activeChanged.connect(update_window_title)
            model.modelReset.connect(
                functools.partial(update_window_title, model.active_index()))

        self.init_queued_transaction_thread()

        self._initialized = True
        self.initialized.emit()

    @common.debug
    @common.error
    def init_queued_transaction_thread(self):
        """This additional thread is responsible for setting item flags.

        """
        t_worker = threads.TransactionsWorker(threads.QueuedDatabaseTransaction)
        t_thread = threads.BaseThread(t_worker)
        t_thread.started.connect(t_thread.startCheckQueue)
        t_thread.start()

    @common.debug
    @common.error
    def _init_shortcuts(self):
        connect = functools.partial(shortcuts.connect, shortcuts.MainWidgetShortcuts)

        # Adding shortcuts to the MainWidget
        shortcuts.add_shortcuts(self, shortcuts.MainWidgetShortcuts)

        connect(shortcuts.RowIncrease, actions.increase_row_size)
        connect(shortcuts.RowDecrease, actions.decrease_row_size)
        connect(shortcuts.RowReset, actions.reset_row_size)

        connect(shortcuts.ToggleSortOrder, actions.toggle_sort_order)

        connect(shortcuts.ShowBookmarksTab, functools.partial(actions.change_tab, base.BookmarkTab))
        connect(shortcuts.ShowAssetsTab, functools.partial(actions.change_tab, base.AssetTab))
        connect(shortcuts.ShowFilesTab, functools.partial(actions.change_tab, base.FileTab))
        connect(shortcuts.ShowFavouritesTab, functools.partial(actions.change_tab, base.FavouriteTab))

        connect(shortcuts.NextTab, actions.next_tab)
        connect(shortcuts.PreviousTab, actions.previous_tab)

        connect(shortcuts.AddItem, actions.add_item)
        connect(shortcuts.EditItem, actions.edit_item)

        connect(shortcuts.Refresh, actions.refresh)

        connect(shortcuts.CopyItemPath, actions.copy_selected_path)
        connect(shortcuts.CopyAltItemPath, actions.copy_selected_alt_path)
        connect(shortcuts.RevealItem, actions.reveal_selected)
        connect(shortcuts.RevealAltItem, actions.reveal_url)

        connect(shortcuts.CopyProperties, actions.copy_properties)
        connect(shortcuts.PasteProperties, actions.paste_properties)

        if common.STANDALONE:
            connect(shortcuts.Quit, actions.quit)
            connect(shortcuts.Minimize, actions.toggle_minimized)
            connect(shortcuts.Maximize, actions.toggle_maximized)
            connect(shortcuts.FullScreen, actions.toggle_fullscreen)
            connect(shortcuts.OpenNewInstance, actions.exec_instance)

        connect(shortcuts.ToggleGenerateThumbnails, actions.signals.toggleMakeThumbnailsButton)
        connect(shortcuts.ToggleSearch, actions.signals.toggleFilterButton)
        connect(shortcuts.ToggleSequence, actions.signals.toggleSequenceButton)
        connect(shortcuts.ToggleArchived, actions.signals.toggleArchivedButton)
        connect(shortcuts.ToggleFavourite, actions.signals.toggleFavouritesButton)
        connect(shortcuts.ToggleActive, actions.toggle_active_item)

        connect(shortcuts.HideInlineButtons, actions.signals.toggleSimpleButton)

        connect(shortcuts.OpenSlack, actions.show_slack)
        connect(shortcuts.OpenPreferences, actions.show_preferences)
        connect(shortcuts.OpenTodo, actions.show_todos)

        connect(shortcuts.ToggleItemArchived, actions.toggle_archived)
        connect(shortcuts.ToggleItemFavourite, actions.toggle_favourite)



    def widget(self):
        return self.stackedwidget.currentWidget()

    def index(self):
        if not self.widget().selectionModel().hasSelection():
            return QtCore.QModelIndex()
        index = self.widget().selectionModel().currentIndex()
        if not index.isValid():
            return QtCore.QModelIndex()
        return index

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        self._paint_background(painter)
        if not self._initialized:
            self._paint_loading(painter)
        painter.end()

    def _paint_background(self, painter):
        rect = QtCore.QRect(self.rect())
        pen = QtGui.QPen(QtGui.QColor(35, 35, 35, 255))
        pen.setWidth(common.ROW_SEPARATOR())
        painter.setPen(pen)
        painter.setBrush(common.SEPARATOR.darker(110))
        painter.drawRect(rect)

    def _paint_loading(self, painter):
        font, metrics = common.font_db.primary_font(
            common.MEDIUM_FONT_SIZE())
        rect = QtCore.QRect(self.rect())
        align = QtCore.Qt.AlignCenter
        color = QtGui.QColor(255, 255, 255, 80)

        pixmaprect = QtCore.QRect(rect)
        center = pixmaprect.center()
        s = common.ASSET_ROW_HEIGHT() * 1.5
        o = common.MARGIN()

        pixmaprect.setWidth(s)
        pixmaprect.setHeight(s)
        pixmaprect.moveCenter(center)

        painter.setBrush(QtGui.QColor(0, 0, 0, 20))
        pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 20))
        painter.setPen(pen)

        painter.drawRoundedRect(
            pixmaprect.marginsAdded(
                QtCore.QMargins(o * 3, o * 3, o * 3, o * 3)),
            o, o)

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'icon_bw', None, s)
        painter.setOpacity(0.5)
        painter.drawPixmap(pixmaprect, pixmap, pixmap.rect())
        painter.setOpacity(1.0)

        rect.setTop(pixmaprect.bottom() + (o * 0.5))
        rect.setHeight(metrics.height())
        common.draw_aliased_text(
            painter, font, rect, self.init_progress, align, color)


    @QtCore.Slot(QtCore.QModelIndex)
    def entered(self, index, role=QtCore.Qt.StatusTipRole):
        """Displays an index's StatusTipRole in the status bar.

        """
        if not index.isValid():
            return
        message = index.data(role)
        self.statusbar.showMessage(message, timeout=1500)

    @QtCore.Slot(unicode)
    def entered2(self, message):
        """Displays a custom message in the statusbar.

        """
        if not message:
            return
        self.statusbar.showMessage(message, timeout=1500)

    def sizeHint(self):
        """The widget's default size."""
        return QtCore.QSize(common.WIDTH(), common.HEIGHT())

    def showEvent(self, event):
        """Show event. When we first show the widget we will initialize it to
        load the models.

        """
        if not self._initialized:
            self.initializer.start()

    @common.error
    @common.debug
    def rv_push(self):
        """Pushes the selected footage to RV."""
        if not self.widget().hasSelection():
            return
        index = self.widget().currentIndex()
        if not index.isValid():
            return
        path = common.get_sequence_startpath(
            index.data(QtCore.Qt.StatusTipRole))
        rv.push(path)
