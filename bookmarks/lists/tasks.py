# -*- coding: utf-8 -*-
"""Defines the view and model used to display and pick subfolders found
in an asset's root.

Folders found in an asset's root are referred to as `task folders`. Bookmarks
generally expects them to be associated with a task or data-type eg. ``render``,
``comp``, ``textures``, etc.

Core task folders are defined by `asset_config.py`.

"""
import weakref
from functools import partial
import _scandir

from PySide2 import QtWidgets, QtGui, QtCore

from .. import log
from .. import common
from .. import contextmenu
from .. import images
from .. import settings
from .. import threads
from ..properties import asset_config

from . import base
from . import delegate


class TaskFolderContextMenu(contextmenu.BaseContextMenu):
    """The context menu associated with the TaskFolderWidget."""

    def __init__(self, index, parent=None):
        super(TaskFolderContextMenu, self).__init__(index, parent=parent)
        self.add_reveal_item_menu()
        self.add_copy_menu()


class TaskFolderWidgetDelegate(delegate.BaseDelegate):
    """The delegate used to paint the available subfolders inside the asset folder."""

    def paint(self, painter, option, index):
        """The main paint method."""
        args = self.get_paint_arguments(painter, option, index)
        self.paint_background(*args)
        self.paint_name(*args)
        self.paint_selection_indicator(*args)

    def get_text_segments(self):
        return []

    @delegate.paintmethod
    def paint_background(self, *args):
        """Paints the background."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(common.SEPARATOR)
        painter.drawRect(option.rect)
        rect = QtCore.QRect(option.rect)
        center = rect.center()
        rect.setHeight(rect.height() - common.ROW_SEPARATOR())
        rect.moveCenter(center)
        background = common.SECONDARY_BACKGROUND
        color = common.BACKGROUND_SELECTED if selected or hover else background
        painter.setBrush(color)
        painter.drawRect(rect)

    @delegate.paintmethod
    def paint_name(self, *args):
        """Paints the name and the number of files available for the given data-key."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        if not index.data(QtCore.Qt.DisplayRole):
            return

        if index.data(common.TodoCountRole):
            color = common.TEXT_SELECTED if hover else common.TEXT
        else:
            color = common.TEXT if hover else common.BACKGROUND_SELECTED
        color = common.TEXT_SELECTED if selected else color

        font = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())[0]

        o = common.MARGIN()
        rect = QtCore.QRect(option.rect)
        if selected:
            pixmap = images.ImageCache.get_rsc_pixmap(u'check', common.ADD, o)
            _rect = QtCore.QRect(0, 0, o, o)
            _rect.moveCenter(option.rect.center())
            _rect.moveLeft(
                option.rect.left() + ((o + common.INDICATOR_WIDTH()) * 0.5))
            painter.drawPixmap(_rect, pixmap, pixmap.rect())

            rect = rect.marginsRemoved(QtCore.QMargins(o * 2, 0, o, 0))
        else:
            rect = rect.marginsRemoved(QtCore.QMargins(o, 0, o, 0))

        text = index.data(QtCore.Qt.DisplayRole).upper()
        width = 0
        width = common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)
        rect.setLeft(rect.left() + width)

        items = []
        # Adding an indicator for the number of items in the folder
        if index.data(common.TodoCountRole):
            if index.data(common.TodoCountRole) >= 999:
                text = u'999+ items'
            else:
                text = u'{} items'.format(
                    index.data(common.TodoCountRole))
            color = common.TEXT_SELECTED if selected else common.FAVOURITE
            color = common.TEXT_SELECTED if hover else color
            items.append((text, color))
        else:
            color = common.TEXT if selected else common.BACKGROUND
            color = common.TEXT if hover else color
            items.append((u'n/a', color))

        if index.data(QtCore.Qt.ToolTipRole):
            color = common.TEXT_SELECTED if selected else common.TEXT
            color = common.TEXT_SELECTED if hover else color
            items.append((index.data(QtCore.Qt.ToolTipRole), color))

        for idx, val in enumerate(items):
            text, color = val
            if idx == 0:
                align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft
            else:
                align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight

            width = common.draw_aliased_text(
                painter, common.font_db.secondary_font(common.SMALL_FONT_SIZE())[0], rect, u'    |    ', align, common.SEPARATOR)
            rect.setLeft(rect.left() + width)

            width = common.draw_aliased_text(
                painter,
                common.font_db.primary_font(common.MEDIUM_FONT_SIZE())[0],
                rect,
                text,
                align,
                color
            )
            rect.setLeft(rect.left() + width)

    def sizeHint(self, option, index):
        """Returns the size of the TaskFolderWidgetDelegate items."""
        return index.data(QtCore.Qt.SizeHintRole)


class TaskFolderModel(base.BaseModel):
    """This model holds all the necessary data needed to display items to
    select for selecting the asset subfolders and/or bookmarks and assets.

    The model keeps track of the selections internally and is updated
    via the signals and slots."""
    queue_type = threads.TaskFolderInfoQueue
    taskFolderChangeRequested = QtCore.Signal()

    def __init__(self, parent=None):
        self._parent = parent
        self._monitor = None

        super(TaskFolderModel, self).__init__(parent=parent)

        self.init_monitor()
        self.modelDataResetRequested.connect(self.__resetdata__)

    @QtCore.Slot()
    def init_monitor(self):
        """We're using a QFileSystemWatcher to check keep track of any folder
        changes in the model's parent folder.

        If a new file/folder is added or changed we will trigger a model reset.

        """
        if not isinstance(self._monitor, QtCore.QFileSystemWatcher):
            self._monitor = QtCore.QFileSystemWatcher()
            self._monitor.fileChanged.connect(self.__resetdata__)
            self._monitor.directoryChanged.connect(self.__resetdata__)

    @QtCore.Slot()
    def reset_monitor(self):
        if self._monitor is None:
            self._monitor = QtCore.QFileSystemWatcher()
        for f in self._monitor.files():
            self._monitor.removePath(f)
        for f in self._monitor.directories():
            self._monitor.removePath(f)

    def init_threads(self):
        """Starts and connects the threads."""
        @QtCore.Slot(QtCore.QThread)
        def thread_started(thread):
            """Signals the model an item has been updated."""
            cnx = QtCore.Qt.QueuedConnection
            thread.updateRow.connect(
                self.updateRow, QtCore.Qt.DirectConnection)

            self.startCheckQueue.connect(
                lambda: log.debug('startCheckQueue -> worker.startCheckQueue', self))
            self.startCheckQueue.connect(
                thread.startCheckQueue, cnx)
            self.stopCheckQueue.connect(
                lambda: log.debug('stopCheckQueue -> worker.stopCheckQueue', self))
            self.stopCheckQueue.connect(
                thread.stopCheckQueue, cnx)
            self.startCheckQueue.emit()

        info_worker = threads.TaskFolderWorker(threads.TaskFolderInfoQueue)
        info_thread = threads.BaseThread(info_worker)
        self.threads[common.InfoThread].append(info_thread)
        info_thread.started.connect(partial(thread_started, info_thread))

        info_thread.start()

    def parent_path(self):
        """The model's parent folder path.

        Returns:
            tuple: A tuple of path segments.

        """
        return (
            settings.ACTIVE[settings.ServerKey],
            settings.ACTIVE[settings.JobKey],
            settings.ACTIVE[settings.RootKey],
            settings.ACTIVE[settings.AssetKey],
        )

    def data_type(self):
        return common.FileItem

    def sort_data(self):
        """This model is always alphabetical."""
        pass

    @base.initdata
    def __initdata__(self):
        """Bookmarks and assets are static. But files will be any number of """
        self.reset_monitor()

        self.INTERNAL_MODEL_DATA[0] = common.DataDict({
            common.FileItem: common.DataDict(),
            common.SequenceItem: common.DataDict()
        })

        flags = (
            QtCore.Qt.ItemIsSelectable |
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsDropEnabled |
            QtCore.Qt.ItemIsEditable
        )
        data = self.model_data()

        parent_path = self.parent_path()
        if not parent_path or not all(parent_path):
            return
        _parent_path = u'/'.join(parent_path)

        # Thumbnail image
        default_thumbnail = images.ImageCache.get_rsc_pixmap(
            u'folder_sm',
            common.SECONDARY_TEXT,
            self.row_size().height()
        )
        default_thumbnail = default_thumbnail.toImage()

        config = asset_config.get(*parent_path[0:3])

        # Add the parent path
        self._monitor.addPath(_parent_path)

        entries = sorted(
            ([f for f in _scandir.scandir(_parent_path)]), key=lambda x: x.name)

        for entry in entries:
            if entry.name.startswith(u'.'):
                continue
            if not entry.is_dir():
                continue

            idx = len(data)
            data[idx] = common.DataDict({
                QtCore.Qt.DisplayRole: entry.name,
                QtCore.Qt.EditRole: entry.name,
                QtCore.Qt.StatusTipRole: entry.path.replace(u'\\', u'/'),
                QtCore.Qt.ToolTipRole: u'',
                QtCore.Qt.ToolTipRole: config.get_description(entry.name),
                QtCore.Qt.SizeHintRole: self.row_size(),
                #
                common.FlagsRole: flags,
                common.ParentPathRole: parent_path,
                #
                common.FileInfoLoaded: False,
                common.ThumbnailLoaded: True,
                common.TodoCountRole: 0,
                #
                common.IdRole: idx,
            })
            thread = self.threads[common.InfoThread][0]
            thread.add_to_queue(weakref.ref(data[idx]))

    @QtCore.Slot()
    def check_task(self):
        """Slot used to verify the current task folder.

        """
        v = settings.ACTIVE[settings.TaskKey]
        if not v:
            self.taskFolderChangeRequested.emit()
            return

        parent_path = self.parent_path() + (v,)
        if not all(parent_path):
            self.taskFolderChangeRequested.emit()
            return

        if not QtCore.QFileInfo(u'/'.join(parent_path)).exists():
            self.taskFolderChangeRequested.emit()

    def default_row_size(self):
        return QtCore.QSize(1, common.ROW_HEIGHT() * 0.9)

    def local_settings_key(self):
        return settings.TaskKey


class TaskFolderWidget(QtWidgets.QListView):
    """The view responsonsible for displaying the available data-keys."""
    ContextMenu = TaskFolderContextMenu

    def __init__(self, parent=None, altparent=None):
        super(TaskFolderWidget, self).__init__(parent=parent)
        self.altparent = altparent
        self._context_menu_active = False

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.clicked.connect(self.activated)
        self.clicked.connect(self.hide)

        if self.altparent:
            self.clicked.connect(self.altparent.signal_dispatcher)

        if self.parent():
            @QtCore.Slot(QtCore.QRect)
            def set_width(rect):
                """Resizes the view to the size of the"""
                rect = browser_widget.stackedwidget.widget(
                    2).viewport().geometry()
                rect.setLeft(0)
                rect.setTop(0)
                self.setGeometry(rect)

            browser_widget = self.parent().parent().parent()
            browser_widget.stackedwidget.widget(2).resized.connect(set_width)

        model = TaskFolderModel()
        model.view = self
        self.setModel(model)
        self.setItemDelegate(TaskFolderWidgetDelegate(parent=self))
        self.installEventFilter(self)

    def sizeHint(self):
        """The default size of the widget."""
        if self.parent():
            return QtCore.QSize(self.parent().width(), self.parent().height())
        else:
            return QtCore.QSize(common.WIDTH() * 0.6, common.HEIGHT() * 0.6)

    @QtCore.Slot(QtCore.QModelIndex)
    def activate(self, index):
        """Exists only for compatibility/consistency."""
        if not index.isValid():
            return
        self.activated.emit(index)

    def inline_icons_count(self):
        return 0

    def hideEvent(self, event):
        """TaskFolderWidget hide event."""
        if self.parent():
            self.parent().verticalScrollBar().setHidden(False)
            self.parent().removeEventFilter(self)
            self.altparent.files_button.update()

    def showEvent(self, event):
        """TaskFolderWidget show event."""
        if self.parent():
            self.parent().verticalScrollBar().setHidden(True)
            self.parent().installEventFilter(self)

    def eventFilter(self, widget, event):
        """We're stopping events propagating back to the parent."""
        if widget == self.parent():
            return True
        if widget is not self:
            return False

        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.SEPARATOR)
            painter.setOpacity(0.75)
            painter.drawRect(self.rect())
            painter.end()
            return True
        return False

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.hide()
        elif (event.key() == QtCore.Qt.Key_Return) or (event.key() == QtCore.Qt.Key_Enter):
            self.hide()
            return
        super(TaskFolderWidget, self).keyPressEvent(event)

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if self._context_menu_active:
            return
        if event.lostFocus():
            self.hide()

    def contextMenuEvent(self, event):
        """Custom context menu event."""
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
        width = self.viewport().geometry().width()

        widget = self.ContextMenu(index, parent=self)
        rect = self.visualRect(index)
        offset = self.visualRect(index).height() - common.INDICATOR_WIDTH()
        widget.move(
            self.viewport().mapToGlobal(rect.bottomLeft()).x() + offset,
            self.viewport().mapToGlobal(rect.bottomLeft()).y() + 1,
        )

        widget.setFixedWidth(width - offset)
        common.move_widget_to_available_geo(widget)

        self._context_menu_active = True
        widget.exec_()
        self._context_menu_active = False

    def mousePressEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        index = self.indexAt(event.pos())
        if not index.isValid():
            self.hide()
            return
        super(TaskFolderWidget, self).mousePressEvent(event)
