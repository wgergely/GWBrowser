# -*- coding: utf-8 -*-
"""``browserwidget.py`` is the main widget of GWBrowser.
"""
import sys
import time
import functools
from PySide2 import QtWidgets, QtGui, QtCore

from gwbrowser.addbookmarkswidget import AddBookmarksWidget
from gwbrowser.assetswidget import AssetsWidget
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.basecontextmenu import contextmenu
from gwbrowser.baselistwidget import StackedWidget
from gwbrowser.bookmarkswidget import BookmarksWidget
from gwbrowser.common_ui import ClickableIconButton, PaintedLabel, add_row
from gwbrowser.favouriteswidget import FavouritesWidget
from gwbrowser.fileswidget import FilesWidget
from gwbrowser.imagecache import ImageCache
from gwbrowser.listcontrolwidget import ListControlWidget
from gwbrowser.preferenceswidget import PreferencesWidget
from gwbrowser.settings import Active
from gwbrowser.settings import local_settings, Active
from gwbrowser.threads import BaseThread
import gwbrowser.common as common
import gwbrowser.mode as mode
import gwbrowser.settings as Settings


DEBUG = False




@QtCore.Slot(unicode)
def debug_signals(label, *args, **kwargs):
    print u'{time}:{label}     -->     {args}  |  {kwargs}'.format(time='{}'.format(time.time())[:-3], label=label, args=args,kwargs=kwargs)



class TrayMenu(BaseContextMenu):
    """The context-menu associated with the BrowserButton."""

    def __init__(self, parent=None):
        super(TrayMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)

        self.stays_on_top = False
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)

        self.add_show_menu()
        self.add_toolbar_menu()
        self.add_visibility_menu()

    def show_window(self):
        """Raises and shows the widget."""
        screen = self.parent().window().windowHandle().screen()
        self.parent().move(screen.geometry().center() - self.parent().rect().center())
        self.parent().showNormal()
        self.parent().activateWindow()

    @contextmenu
    def add_visibility_menu(self, menu_set):
        """Actions associated with the visibility of the widget."""

        def toggle_window_flag():
            """Sets the WindowStaysOnTopHint for the window."""
            flags = self.parent().windowFlags()
            self.hide()
            if flags & QtCore.Qt.WindowStaysOnTopHint:
                flags = flags & ~QtCore.Qt.WindowStaysOnTopHint
            else:
                flags = flags | QtCore.Qt.WindowStaysOnTopHint
            self.parent().setWindowFlags(flags)
            self.parent().showNormal()
            self.parent().activateWindow()

        menu_set['Keep on top of other windows'] = {
            'checkable': True,
            'checked': self.parent().windowFlags() & QtCore.Qt.WindowStaysOnTopHint,
            'action': toggle_window_flag
        }
        menu_set['Restore window...'] = {
            'action': self.show_window
        }
        menu_set['separator1'] = {}
        menu_set['Quit'] = {
            'action': self.parent().shutdown.emit
        }
        return menu_set

    @contextmenu
    def add_show_menu(self, menu_set):
        if not hasattr(self.parent(), 'clicked'):
            return menu_set
        menu_set[u'show'] = {
            u'icon': ImageCache.get_rsc_pixmap(u'custom_bw', None, common.INLINE_ICON_SIZE),
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
                u'action': lambda: common.reveal(u'/'.join(bookmark))
            }
            if all(asset):
                menu_set[u'asset'] = {
                    u'icon': ImageCache.get_rsc_pixmap(u'assets', common.TEXT, common.INLINE_ICON_SIZE),
                    u'disabled': not all(asset),
                    u'text': u'Show active asset in the file manager...',
                    u'action': lambda: common.reveal(u'/'.join(asset))
                }
                if all(location):
                    menu_set[u'location'] = {
                        u'icon': ImageCache.get_rsc_pixmap(u'location', common.TEXT, common.INLINE_ICON_SIZE),
                        u'disabled': not all(location),
                        u'text': u'Show current task folder in the file manager...',
                        u'action': lambda: common.reveal(u'/'.join(location))
                    }

        return menu_set


class AppIconButton(ClickableIconButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(AppIconButton, self).__init__(
            u'custom',
            (common.SECONDARY_TEXT, common.SECONDARY_TEXT),
            common.INLINE_ICON_SIZE - common.INDICATOR_WIDTH,
            description=u'',
            parent=parent
        )
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.setFocusPolicy(QtCore.Qt.NoFocus)


class MinimizeButton(ClickableIconButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(MinimizeButton, self).__init__(
            u'minimize',
            (common.REMOVE, common.SECONDARY_TEXT),
            common.INLINE_ICON_SIZE - common.INDICATOR_WIDTH,
            description=u'Click to minimize the window...',
            parent=parent
        )


class CloseButton(ClickableIconButton):
    """Button used to close/hide a widget or window."""

    def __init__(self, parent=None):
        super(CloseButton, self).__init__(
            u'close',
            (common.REMOVE, common.SECONDARY_TEXT),
            common.INLINE_ICON_SIZE - common.INDICATOR_WIDTH,
            description=u'Click to close the window...',
            parent=parent
        )


class HeaderWidget(QtWidgets.QWidget):
    """Horizontal widget for controlling the position of the widget active window."""
    widgetMoved = QtCore.Signal(QtCore.QPoint)

    def __init__(self, parent=None):
        super(HeaderWidget, self).__init__(parent=parent)
        self.label = None
        self.closebutton = None
        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_widget_pos = None

        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setFixedHeight(common.INLINE_ICON_SIZE + (common.MARGIN / 2.0))

        self._createUI()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        menu_bar = QtWidgets.QMenuBar(parent=self)
        self.layout().addWidget(menu_bar)
        menu_bar.hide()
        menu = menu_bar.addMenu(u'GWBrowser')
        action = menu.addAction(u'Quit')
        action.triggered.connect(self.parent().shutdown)

        self.layout().addSpacing(common.INDICATOR_WIDTH * 2)
        self.layout().addWidget(AppIconButton(parent=self))
        self.layout().addStretch()
        self.layout().addWidget(MinimizeButton(parent=self))
        self.layout().addSpacing(common.INDICATOR_WIDTH * 2)
        self.layout().addWidget(CloseButton(parent=self))
        self.layout().addSpacing(common.INDICATOR_WIDTH * 2)

    def mousePressEvent(self, event):
        """Custom ``movePressEvent``.
        We're setting the properties needed to moving the main window.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.move_in_progress = True
        self.move_start_event_pos = event.pos()
        self.move_start_widget_pos = self.mapToGlobal(
            self.geometry().topLeft())

    def mouseMoveEvent(self, event):
        """The custom mouse move event responsbiel for moving the parent window.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.buttons() == QtCore.Qt.NoButton:
            return
        if self.move_start_widget_pos:
            margins = self.window().layout().contentsMargins()
            offset = (event.pos() - self.move_start_event_pos)
            pos = self.window().mapToGlobal(self.geometry().topLeft()) + offset
            self.parent().move(
                pos.x() - margins.left(),
                pos.y() - margins.top()
            )
            bl = self.window().rect().bottomLeft()
            bl = self.window().mapToGlobal(bl)
            self.widgetMoved.emit(bl)

    def contextMenuEvent(self, event):
        """Shows the context menu associated with the tray in the header."""
        widget = TrayMenu(parent=self.window())
        pos = self.window().mapToGlobal(event.pos())
        widget.move(pos)
        common.move_widget_to_available_geo(widget)
        widget.show()


class ToggleModeButton(QtWidgets.QWidget):
    """Small version label responsible for displaying information
    about GWBrowser."""
    clicked = QtCore.Signal()
    message = QtCore.Signal(unicode)

    def __init__(self, size, parent=None):
        super(ToggleModeButton, self).__init__(parent=parent)
        size = size - 4
        self.setFixedSize(size, size)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.animation_value = 1.0

        self.animation = QtCore.QVariantAnimation(parent=self)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.5)
        self.animation.setEasingCurve(QtCore.QEasingCurve.InCubic)
        self.animation.setLoopCount(1) # Loops for forever
        self.animation.setDirection(QtCore.QAbstractAnimation.Forward)
        self.animation.setDuration(1500)
        self.animation.valueChanged.connect(self.update)
        self.animation.finished.connect(self.reverse_direction)
        self.clicked.connect(self.toggle_mode)

    def statusTip(self):
        if mode.CURRENT_MODE == common.SynchronisedMode:
            return u'This GWBrowser instance is syncronised with other instances. Click to toggle!'
        elif mode.CURRENT_MODE == common.SoloMode:
            return u'This GWBrowser instance is not synronised with other instances. Click to toggle!'

    @QtCore.Slot()
    def reverse_direction(self):
        """ A bounce."""
        if self.animation.direction() == QtCore.QPropertyAnimation.Forward:
            self.animation.setDirection(QtCore.QPropertyAnimation.Backward)
        else:
            self.animation.setDirection(QtCore.QPropertyAnimation.Forward)
        self.animation.start()
        self.update()

    def toggle_mode(self):
        """Simply toggles the solo mode."""
        if mode.CURRENT_MODE == common.SynchronisedMode:
            mode.CURRENT_MODE = common.SoloMode
            self.animation.setCurrentTime(0)
            self.animation.start()
        elif mode.CURRENT_MODE == common.SoloMode:
            mode.CURRENT_MODE = common.SynchronisedMode
            self.animation.setCurrentTime(0)
            self.animation.stop()
        self.update()
        mode.save()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtCore.Qt.NoBrush)

        color = common.REMOVE if mode.CURRENT_MODE else common.ADD
        pen = QtGui.QPen(color)

        o = 2.5
        pen.setWidthF(o)
        painter.setPen(pen)
        painter.setOpacity(self.animation.currentValue())
        rect = QtCore.QRectF(self.rect())
        center = self.rect().center()

        size = QtCore.QSizeF(rect.width() - (o * 2), rect.height() - (o * 2))
        rect.setSize(size * self.animation.currentValue())
        rect.moveCenter(center)
        c = rect.height() / 2.0
        painter.drawRoundedRect(rect , c, c)

        painter.end()

    def enterEvent(self, event):
        self.message.emit(self.statusTip())

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        cursor_position = self.mapFromGlobal(QtGui.QCursor().pos())
        if self.rect().contains(cursor_position):
            self.clicked.emit()

    def showEvent(self, event):
        if mode.CURRENT_MODE == common.SoloMode:
            self.animation.setCurrentTime(0)
            self.animation.start()
            self.update()
        elif mode.CURRENT_MODE == common.SynchronisedMode:
            self.animation.setCurrentTime(0)
            self.animation.stop()
            self.update()


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

        self._contextMenu = None
        self._initialized = False

        self.headerwidget = None
        self.stackedwidget = None
        self.bookmarkswidget = None
        self.listcontrolwidget = None
        self.assetswidget = None
        self.fileswidget = None
        self.favouriteswidget = None
        self.statusbar = None
        self.preferences_widget = None
        self.add_bookmarks_widget = None
        self.solo_button = None

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

        self.init_progress = u'Loading...'

    def _createUI(self):
        common.set_custom_stylesheet(self)

        # Main layout
        QtWidgets.QVBoxLayout(self)
        o = common.INDICATOR_WIDTH  # offset around the widget
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred
        )

        self.headerwidget = HeaderWidget(parent=self)
        self.stackedwidget = StackedWidget(parent=self)
        self.bookmarkswidget = BookmarksWidget(parent=self)
        self.assetswidget = AssetsWidget(parent=self)
        self.fileswidget = FilesWidget(parent=self)
        self.favouriteswidget = FavouritesWidget(parent=self)
        self.preferences_widget = PreferencesWidget(parent=self)
        self.add_bookmarks_widget = AddBookmarksWidget(parent=self)

        self.stackedwidget.addWidget(self.bookmarkswidget)
        self.stackedwidget.addWidget(self.assetswidget)
        self.stackedwidget.addWidget(self.fileswidget)
        self.stackedwidget.addWidget(self.favouriteswidget)
        self.stackedwidget.addWidget(self.preferences_widget)
        self.stackedwidget.addWidget(self.add_bookmarks_widget)
        self.listcontrolwidget = ListControlWidget(parent=self)

        self.layout().addWidget(self.headerwidget)
        self.layout().addWidget(self.listcontrolwidget)
        self.layout().addWidget(self.stackedwidget)

        height = common.INLINE_ICON_SIZE

        self.statusbar = QtWidgets.QStatusBar(parent=self)
        self.statusbar.layout().setAlignment(QtCore.Qt.AlignRight)
        self.statusbar.setSizeGripEnabled(False)
        self.statusbar.setFixedHeight(height)
        self.statusbar.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.statusbar.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.statusbar.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Fixed
        )

        row = add_row(u'', height=height, parent=self)
        row.layout().setSpacing(0)
        row.layout().addWidget(self.statusbar)

        self.solo_button = ToggleModeButton(height, parent=self)
        self.solo_button.message.connect(
            lambda s: self.statusbar.showMessage(s, 4000))
        row.layout().addWidget(self.solo_button)
        row.layout().addSpacing(common.INDICATOR_WIDTH)

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

        def emit_saved_state(flag):
            b.filterFlagChanged.emit(flag, b.filterFlag(flag))
            a.filterFlagChanged.emit(flag, a.filterFlag(flag))
            f.filterFlagChanged.emit(flag, f.filterFlag(flag))
            ff.filterFlagChanged.emit(flag, ff.filterFlag(flag))

        mode.touch()
        mode.save()

        self.shortcuts = []

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

    @QtCore.Slot()
    def terminate(self):
        """Terminates the browserwidget gracefully by stopping the associated
        threads.

        """
        def ui_teardown():
            self.setUpdatesEnabled(False)
            self.check_active_state_timer.stop()
            self.active_monitor.macos_mount_timer.stop()
            self.listcontrolwidget.bookmarks_button.timer.stop()
            self.listcontrolwidget.assets_button.timer.stop()
            self.listcontrolwidget.files_button.timer.stop()
            self.listcontrolwidget.favourites_button.timer.stop()

            self.bookmarkswidget.timer.stop()
            self.assetswidget.timer.stop()
            self.fileswidget.timer.stop()
            self.favouriteswidget.timer.stop()
            self.check_active_state_timer.stop()

            for widget in (self.assetswidget, self.fileswidget, self.favouriteswidget):
                widget.timer.stop()
                widget.scrollbar_changed_timer.stop()
                widget.hide_archived_items_timer.stop()

                for child in widget.model().sourceModel().children():
                    child.deleteLater()
                widget.model().sourceModel().deleteLater()
                for child in widget.model().children():
                    child.deleteLater()
                widget.model().deleteLater()
                for child in widget.children():
                    child.deleteLater()
                widget.deleteLater()

            for child in self.headerwidget.children():
                child.deleteLater()
            self.headerwidget.deleteLater()
            for child in self.stackedwidget.children():
                child.deleteLater()
            self.stackedwidget.deleteLater()
            for child in self.statusbar.children():
                child.deleteLater()
            self.statusbar.deleteLater()
            for child in self.children():
                child.deleteLater()
            self.deleteLater()

        self.statusbar.showMessage(u'Closing down...')

        threadpool = self.get_all_threads()
        for thread in threadpool:
            if thread.isRunning():
                thread.worker.shutdown()
                thread.exit(0)

        n = 0
        while any([f.isRunning() for f in threadpool]):
            for thread in threadpool:
                if thread.isRunning():
                    thread.worker.shutdown()
                    thread.quit()
            n += 1
            time.sleep(0.4)
            if n > 20:
                for thread in threadpool:
                    thread.terminate()
                break

        # self.hide()
        ui_teardown()

        keys = sys.modules.keys()
        for k in keys:
            if 'gwbrowser' in k:
                del sys.modules[k]

        sys.stdout.write(u'# GWBrowser terminated.\n')
        self.terminated.emit()

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
        self.headerwidget.widgetMoved.connect(self.save_widget_settings)
        self.headerwidget.findChild(MinimizeButton).clicked.connect(self.showMinimized)
        self.headerwidget.findChild(CloseButton).clicked.connect(self.close)
        #####################################################
        self.shutdown.connect(self.terminate)
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
        rect = rect.marginsRemoved(QtCore.QMargins(3,3,3,3))

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

    @QtCore.Slot()
    def save_widget_settings(self):
        """Saves the position and size of thew widget to the local settings."""
        cls = self.__class__.__name__
        geo = self.geometry()
        local_settings.setValue(u'widget/{}/width'.format(cls), geo.width())
        local_settings.setValue(u'widget/{}/height'.format(cls), geo.height())
        local_settings.setValue(u'widget/{}/x'.format(cls), geo.x())
        local_settings.setValue(u'widget/{}/y'.format(cls), geo.y())

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
