# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903, C0330

"""Widget reponsible controlling the displayed list and the filter-modes."""

import functools
import re
from PySide2 import QtWidgets, QtGui, QtCore

from gwbrowser.settings import Active
import gwbrowser.common as common
from gwbrowser.delegate import paintmethod
from gwbrowser.basecontextmenu import BaseContextMenu, contextmenu
from gwbrowser.baselistwidget import BaseModel

from gwbrowser.delegate import BaseDelegate

from gwbrowser.editors import FilterEditor
from gwbrowser.editors import ClickableLabel
import gwbrowser.settings as Settings

from gwbrowser.imagecache import ImageCache
from gwbrowser.imagecache import ImageCacheWorker
from gwbrowser.fileswidget import FileInfoWorker
from gwbrowser.fileswidget import FilesWidget

from gwbrowser.threads import BaseThread
from gwbrowser.threads import BaseWorker
from gwbrowser.threads import Unique

from gwbrowser.assetwidget import AssetModel
from gwbrowser.bookmarkswidget import BookmarksModel


class ListInfoWorker(BaseWorker):
    """Note: This thread worker is a duplicate implementation of the FileInfoWorker."""
    queue = Unique(999999)

    @QtCore.Slot(QtCore.QModelIndex)
    @classmethod
    def process_index(cls, index):
        """The actual processing happens here."""
        if not index.isValid():
            return

        if not index.data(QtCore.Qt.StatusTipRole):
            return

        # Iterator
        itdir = QtCore.QDir(index.data(QtCore.Qt.StatusTipRole))
        itdir.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        itdir.setSorting(QtCore.QDir.Unsorted)
        it = QtCore.QDirIterator(
            itdir, flags=QtCore.QDirIterator.Subdirectories)

        count = 0
        while it.hasNext():
            it.next()
            count += 1
            if count > 9999:
                break

        # The underlying data can change whilst the calculating
        try:
            data = index.model().model_data()
            data[index.row()][common.TodoCountRole] = count
            index.model().dataChanged.emit(index, index)
        except Exception:
            return


class ListInfoThread(BaseThread):
    Worker = ListInfoWorker



class Progresslabel(QtWidgets.QLabel):
    """The widget responsible displaying progress messages."""

    messageChanged = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(Progresslabel, self).__init__(parent=parent)

        self.progress_monitor = QtCore.QTimer()
        self.progress_monitor.setSingleShot(False)
        self.progress_monitor.setInterval(1000)
        self.progress_monitor.timeout.connect(self.check_progress)
        self.progress_monitor.start()

        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        self.setStyleSheet("""
            QLabel {{
                font-family: "{}";
                font-size: {}pt;
                color: rgba({});
                background-color: rgba(0,0,0,0);
            	border: 0px solid;
                padding: 0px;
                margin: 0px;
            }}
        """.format(
            common.psize(common.SMALL_FONT_SIZE),
            common.PrimaryFont.family(),
            u'{},{},{},{}'.format(*common.SECONDARY_TEXT.getRgb()))
        )

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        self.qre = re.compile(r'(.*)(\s\-\s[0-9]+\sleft)', flags=re.IGNORECASE)

        self.setText(u'')
        self.messageChanged.connect(self.setText, type=QtCore.Qt.DirectConnection)
        self.messageChanged.connect(
            lambda x: QtWidgets.QApplication.instance().processEvents,
            type=QtCore.Qt.DirectConnection)

    @QtCore.Slot()
    def check_progress(self):
        """Sets the Progresslabel's visibility."""
        qsize = ImageCacheWorker.queue.qsize() + FileInfoWorker.queue.qsize()
        text = self.text()
        match = self.qre.match(text)
        if match:
            if match.group(1) == u'Loading items' or match.group(1) == u'Processing thumbnails':
                text = ''
            else:
                text = match.expand(r'\1')


        if ImageCacheWorker.queue.qsize():
            text = u'{} - {} left'.format(text if text else u'Processing thumbnails', qsize)
        else:
            if FileInfoWorker.queue.qsize():
                text = u'{} - {} left'.format(text if text else u'Loading items', qsize)

        self.messageChanged.emit(text)
        # self.setText(text)


class BrowserButtonContextMenu(BaseContextMenu):
    """The context-menu associated with the BrowserButton."""

    def __init__(self, parent=None):
        super(BrowserButtonContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_show_menu()
        self.add_toolbar_menu()

    @contextmenu
    def add_show_menu(self, menu_set):
        if not hasattr(self.parent(), 'clicked'):
            return menu_set
        menu_set[u'show'] = {
            u'icon': ImageCache.get_rsc_pixmap(u'custom', None, common.INLINE_ICON_SIZE),
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
                u'action': functools.partial(common.reveal, u'/'.join(bookmark))
            }
            if all(asset):
                menu_set[u'asset'] = {
                    u'icon': ImageCache.get_rsc_pixmap(u'assets', common.TEXT, common.INLINE_ICON_SIZE),
                    u'disabled': not all(asset),
                    u'text': u'Show active asset in the file manager...',
                    u'action': functools.partial(common.reveal, '/'.join(asset))
                }
                if all(location):
                    menu_set[u'location'] = {
                        u'icon': ImageCache.get_rsc_pixmap(u'location', common.TEXT, common.INLINE_ICON_SIZE),
                        u'disabled': not all(location),
                        u'text': u'Show active location in the file manager...',
                        u'action': functools.partial(common.reveal, '/'.join(location))
                    }

        return menu_set


class BrowserButton(ClickableLabel):
    """Small widget to embed into the context to toggle the BrowserWidget's visibility."""

    def __init__(self, height=common.ROW_HEIGHT, parent=None):
        super(BrowserButton, self).__init__(parent=parent)
        self.context_menu_cls = BrowserButtonContextMenu
        self.setFixedWidth(height)
        self.setFixedHeight(height)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setWindowFlags(
            QtCore.Qt.Widget
            | QtCore.Qt.FramelessWindowHint
        )
        pixmap = ImageCache.get_rsc_pixmap(
            u'custom_bw', common.SECONDARY_TEXT, height)
        self.setPixmap(pixmap)

    def set_size(self, size):
        self.setFixedWidth(int(size))
        self.setFixedHeight(int(size))
        pixmap = ImageCache.get_rsc_pixmap(
            u'custom_bw', common.SECONDARY_TEXT, int(size))
        self.setPixmap(pixmap)

    def enterEvent(self, event):
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.initFrom(self)

        painter = QtGui.QPainter()
        painter.begin(self)
        brush = self.pixmap().toImage()

        painter.setBrush(brush)
        painter.setPen(QtCore.Qt.NoPen)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        painter.setOpacity(0.8)
        if option.state & QtWidgets.QStyle.State_MouseOver:
            painter.setOpacity(1)

        painter.drawRoundedRect(self.rect(), 2, 2)
        painter.end()

    def contextMenuEvent(self, event):
        """Context menu event."""
        # Custom context menu
        shift_modifier = event.modifiers() & QtCore.Qt.ShiftModifier
        alt_modifier = event.modifiers() & QtCore.Qt.AltModifier
        control_modifier = event.modifiers() & QtCore.Qt.ControlModifier
        if shift_modifier or alt_modifier or control_modifier:
            self.customContextMenuRequested.emit()
            return

        widget = self.context_menu_cls(parent=self)
        widget.move(self.mapToGlobal(self.rect().bottomLeft()))
        widget.setFixedWidth(300)
        common.move_widget_to_available_geo(widget)
        widget.exec_()


class CustomButton(BrowserButton):
    def __init__(self, parent=None):
        self.context_menu_cls = BrowserButtonContextMenu
        super(CustomButton, self).__init__(
            height=common.INLINE_ICON_SIZE, parent=parent)
        self.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(r'https://gwbcn.slack.com/'))


class ControlButton(ClickableLabel):

    def __init__(self, parent=None):
        super(ControlButton, self).__init__(parent=parent)
        self._parent = None
        self.setFixedSize(
            common.INLINE_ICON_SIZE,
            common.INLINE_ICON_SIZE,
        )
        self.clicked.connect(self.action)

    def pixmap(self, c):
        return QtGui.QPixmap(common.INLINE_ICON_SIZE, common.INLINE_ICON_SIZE)

    def current(self):
        if not self._parent:
            return None
        return self._parent.currentWidget()

    def set_parent(self, widget):
        self._parent = widget

    def state(self):
        return False

    @QtCore.Slot()
    def action(self):
        pass

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        color = common.FAVOURITE if self.state() else QtGui.QColor(255,255,255,50)
        pixmap = self.pixmap(color)
        painter.drawPixmap(self.rect(), pixmap, pixmap.rect())
        painter.end()


class TodoButton(ControlButton):
    """The button for showing the todo editor."""

    def __init__(self, parent=None):
        super(TodoButton, self).__init__(parent=parent)
        description = u'Show the Todo & Note editor'
        self.setToolTip(description)
        self.setStatusTip(description)

    def pixmap(self, c):
        return ImageCache.get_rsc_pixmap(u'todo', c, common.INLINE_ICON_SIZE)

    def state(self):
        index = self._parent.widget(1).model().sourceModel().active_index()
        if not index.isValid():
            return
        if index.data(common.TodoCountRole):
            return True
        return False

    def action(self):
        assetwidget = self._parent.widget(1)
        index = assetwidget.model().sourceModel().active_index()
        index = assetwidget.model().mapFromSource(index)
        if not index.isValid():
            return
        assetwidget.show_todos(index)


class FilterButton(ControlButton):
    """Button for showing the filter editor."""

    def __init__(self, parent=None):
        super(FilterButton, self).__init__(parent=parent)
        description = u'Edit the current list filter'
        self.setToolTip(description)
        self.setStatusTip(description)

    def pixmap(self, c):
        return ImageCache.get_rsc_pixmap(u'filter', c, common.INLINE_ICON_SIZE)

    def state(self):
        filter_text = self.current().model().filterText()
        if not filter_text:
            return False
        if filter_text == u'/':
            return False
        return True

    def action(self):
        filter_text = self.current().model().filterText()
        if not filter_text:
            filter_text = u''
        else:
            filter_text = re.sub('\[\\\S\\\s\]\*', ' ', filter_text)
            filter_text = re.sub(r'[\\]+', '', filter_text)
            filter_text = common.FilterTextRegex.sub(' ', filter_text)
            filter_text = re.sub(r'\s', ' ', filter_text)
        editor = FilterEditor(filter_text, parent=self._parent)
        pos = self._parent.rect().topLeft()
        pos = self._parent.mapToGlobal(pos)

        editor.move(pos)
        editor.setFixedWidth(self._parent.rect().width())

        def func(filter_text):
            filter_text = common.FilterTextRegex.sub(' ', filter_text)
            filter_text = re.sub(r'\s\s*', ' ', filter_text)
            # filter_text = re.sub(r'([^\s])', r'\\\1', filter_text)
            filter_text = re.sub(r'\s', r'[\S\s]*', filter_text)
            self.current().model().filterTextChanged.emit(filter_text)

        editor.finished.connect(func)
        editor.finished.connect(self.repaint)
        editor.finished.connect(editor.deleteLater)

        editor.show()

class CollapseSequenceButton(ControlButton):

    def __init__(self, parent=None):
        super(CollapseSequenceButton, self).__init__(parent=parent)
        description = u'Toggle sequence display'
        self.setToolTip(description)
        self.setStatusTip(description)

    def pixmap(self, c):
        return ImageCache.get_rsc_pixmap(u'collapse', c, common.INLINE_ICON_SIZE)

    def state(self):
        datatype = self.current().model().sourceModel().data_type()
        if datatype == common.FileItem:
            return False
        return True

    @QtCore.Slot()
    def action(self):
        if self._parent.currentIndex() != 2:
            return

        datatype = self.current().model().sourceModel().data_type()
        if datatype == common.FileItem:
            self.current().model().sourceModel().dataTypeChanged.emit(common.SequenceItem)
        else:
            self.current().model().sourceModel().dataTypeChanged.emit(common.FileItem)


class ToggleArchivedButton(ControlButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(ToggleArchivedButton, self).__init__(parent=parent)
        description = u'Show archived items in the list'
        self.setToolTip(description)
        self.setStatusTip(description)

    def pixmap(self, c):
        return ImageCache.get_rsc_pixmap(u'active', c, common.INLINE_ICON_SIZE)

    def state(self):
        val = self.current().model().filterFlag(Settings.MarkedAsArchived)
        return val

    @QtCore.Slot()
    def action(self):
        val = self.current().model().filterFlag(Settings.MarkedAsArchived)
        self.current().model().filterFlagChanged.emit(Settings.MarkedAsArchived, not val)


class ToggleFavouriteButton(ControlButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(ToggleFavouriteButton, self).__init__(parent=parent)
        description = u'Show only items marked as favourite'
        self.setToolTip(description)
        self.setStatusTip(description)

    def pixmap(self, c):
        return ImageCache.get_rsc_pixmap(u'favourite', c, common.INLINE_ICON_SIZE)

    def state(self):
        val = self.current().model().filterFlag(Settings.MarkedAsFavourite)
        return val

    @QtCore.Slot()
    def action(self):
        val = self.current().model().filterFlag(Settings.MarkedAsFavourite)
        self.current().model().filterFlagChanged.emit(Settings.MarkedAsFavourite, not val)


class CollapseSequenceMenu(BaseContextMenu):
    def __init__(self, parent=None):
        super(CollapseSequenceMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_collapse_sequence_menu()


class AddButton(ControlButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(AddButton, self).__init__(parent=parent)
        description = u'Adds a new item'
        self.setToolTip(description)
        self.setStatusTip(description)

    def __init__(self, parent=None):
        super(AddButton, self).__init__(parent=parent)

    def pixmap(self, c):
        return ImageCache.get_rsc_pixmap(u'todo_add', c, common.INLINE_ICON_SIZE)

    def state(self):
        if self._parent.currentIndex() == 0:
            return True
        if self._parent.currentIndex() == 2:
            return True
        return False

    @QtCore.Slot()
    def action(self):
        """Action to take when the plus icon is clicked.

        Note:
            Adding assets is not yet implemented. I'll work this out for a future
            release.

        """
        if self._parent.currentIndex() == 0:
            self.current().show_add_bookmark_widget()
            return
        if self._parent.currentIndex() == 1:
            return


        index = self._parent.currentWidget().selectionModel().currentIndex()

        # This will open the Saver to save a new file
        if self._parent.currentIndex() == 2:
            import gwbrowser.saver as saver

            # I'm deleting
            bookmark_model = BookmarksModel()
            asset_model = AssetModel()

            extension = u'ext' # This is a generic extension that can be overriden
            currentfile = None
            data_key = self.current().model().sourceModel().data_key()
            subfolder = u'/'

            if index.isValid():
                if not index.data(common.StatusRole):
                    return

            if index.isValid():
                # Incrementing the currently selected file if it is a sequence
                iscollapsed = common.is_collapsed(index.data(QtCore.Qt.StatusTipRole))
                if iscollapsed:
                    currentfile = iscollapsed.expand(r'\1{}\3')
                    currentfile = currentfile.format(u'#' * len(index.data(common.FramesRole)[-1]))
                else:
                    currentfile = common.get_sequence_endpath(index.data(QtCore.Qt.StatusTipRole))
                extension = currentfile.split(u'.').pop()

            # If both the currentfile and the data_key are valid we'll set
            # the default location to be the subfolder of the current file.
            # This is a
            if currentfile and data_key:
                subfolder = currentfile.split(data_key).pop()
                subfolder = subfolder.split(u'/')
                subfolder.pop()
                subfolder = u'/'.join(subfolder).strip(u'/')
            subfolder = '{}/{}'.format(data_key, subfolder).strip(u'/')
            #
            widget = saver.SaverWidget(
                bookmark_model,
                asset_model,
                extension,
                subfolder, # location is the subfolder
                currentfile=currentfile
            )

            widget.finished.connect(bookmark_model.deleteLater)
            widget.finished.connect(asset_model.deleteLater)
            widget.finished.connect(widget.deleteLater)

            @QtCore.Slot(unicode)
            def fileSaveRequested(path):
                f = QtCore.QFile(path)
                if not f.exists():
                    f.open(QtCore.QIODevice.ReadWrite)
                    f.close()

                path = QtCore.QDir.toNativeSeparators(path)
                QtGui.QClipboard().setText(path)
                common.reveal(path)

            @QtCore.Slot(tuple)
            def fileDescriptionAdded(args):
                """Slot responsible for saving the description"""
                server, job, root, filepath, description = args
                settings = Settings.AssetSettings(QtCore.QModelIndex(), args=(server, job, root, filepath))
                settings.setValue(u'config/description', description)

            @QtCore.Slot(tuple)
            def fileThumbnailAdded(args):
                server, job, root, filepath, image = args
                settings = Settings.AssetSettings(QtCore.QModelIndex(), args=(server, job, root, filepath))
                if not image.isNull():
                    image.save(settings.thumbnail_path())

                fileswidget = self.parent().parent().findChild(FilesWidget)
                sizehint = fileswidget.itemDelegate().sizeHint(None, None)
                height = sizehint.height() - 2
                ImageCache.get(settings.thumbnail_path(), height, overwrite=True)

                self.parent().parent().findChild(FilesWidget).model().sourceModel().modelDataResetRequested.emit()

            widget.fileSaveRequested.connect(fileSaveRequested)
            widget.fileDescriptionAdded.connect(fileDescriptionAdded)
            widget.fileThumbnailAdded.connect(fileThumbnailAdded)
            widget.exec_()



class DataKeyViewDelegate(BaseDelegate):
    """The delegate used to paint the available subfolders inside the asset folder."""

    def __init__(self, parent=None):
        super(DataKeyViewDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        """The main paint method."""
        args = self._get_paint_args(painter, option, index)
        self.paint_background(*args)
        self.paint_thumbnail(*args)
        self.paint_name(*args)

    @paintmethod
    def paint_background(self, *args):
        """Paints the background."""
        painter, option, index, selected, _, _, _, _ = args
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        rect = QtCore.QRect(option.rect)
        center = rect.center()
        rect.setHeight(rect.height() - 2)
        rect.moveCenter(center)

        background = QtGui.QColor(common.BACKGROUND)
        background.setAlpha(50)
        color = common.BACKGROUND_SELECTED if selected or hover else background
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 3, 3)

    @paintmethod
    def paint_name(self, *args):
        """Paints the name and the number of files available for the given data-key."""
        painter, option, index, selected, _, _, _, _ = args
        if not index.data(QtCore.Qt.DisplayRole):
            return

        hover = option.state & QtWidgets.QStyle.State_MouseOver
        color = common.TEXT_SELECTED if hover else common.SECONDARY_TEXT
        color = common.TEXT_SELECTED if selected else color

        font = QtGui.QFont(common.PrimaryFont)
        current_key = index.data(
            QtCore.Qt.DisplayRole) == self.parent().model()._datakey

        rect = QtCore.QRect(option.rect)
        rect.setLeft(
            common.INDICATOR_WIDTH
            + rect.height()
        )
        rect.setRight(rect.right() - common.MARGIN)

        text = index.data(QtCore.Qt.DisplayRole).upper()
        width = 0
        width = common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)
        rect.setLeft(rect.left() + width)

        if index.data(common.TodoCountRole):
            if index.data(common.TodoCountRole) >= 9999:
                text = u' (9999+ files)'
            else:
                text = u' ({} files)'.format(index.data(common.TodoCountRole))
            color = common.TEXT_SELECTED if selected else common.SECONDARY_TEXT
            color = common.TEXT_SELECTED if hover else color
            width = common.draw_aliased_text(
                painter, common.SecondaryFont, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)
            rect.setLeft(rect.left() + width)

        if hover or selected:
            text = u'  {}'.format(index.data(QtCore.Qt.ToolTipRole))
            color = common.TEXT_SELECTED if selected else common.SECONDARY_TEXT
            color = common.TEXT_SELECTED if hover else color
            width = common.draw_aliased_text(
                painter, common.SecondaryFont, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight, color)

    def sizeHint(self, option, index):
        return QtCore.QSize(common.WIDTH, int(common.BOOKMARK_ROW_HEIGHT / 1.5))


class ListControlContextMenu(BaseContextMenu):
    def __init__(self, index, parent=None):
        super(ListControlContextMenu, self).__init__(index, parent=parent)
        self.add_reveal_item_menu()


class DataKeyView(QtWidgets.QListView):
    """The view responsonsible for displaying the available data-keys."""

    def __init__(self, parent=None):
        super(DataKeyView, self).__init__(parent=parent)
        common.set_custom_stylesheet(self)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self.context_menu_cls = ListControlContextMenu
        self._context_menu_active = False
        self.clicked.connect(self.activated)
        self.clicked.connect(self.hide)
        self.clicked.connect(self.parent().signal_dispatcher)

        self.setModel(DataKeyModel())
        self.model().modelReset.connect(self.adjust_size)
        self.setItemDelegate(DataKeyViewDelegate(parent=self))

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.hide()
            return
        super(DataKeyView, self).keyPressEvent(event)

    @QtCore.Slot()
    def adjust_size(self):
        # Setting the height based on the conents
        height = 0
        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0)
            height += self.itemDelegate().sizeHint(None, None).height()
        self.setFixedHeight(height + 8) # hardcoded padding from stylesheet

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

        widget = self.context_menu_cls(index, parent=self)
        rect = self.visualRect(index)
        offset = self.visualRect(index).height() - common.INDICATOR_WIDTH
        widget.move(
            self.viewport().mapToGlobal(rect.bottomLeft()).x() + offset,
            self.viewport().mapToGlobal(rect.bottomLeft()).y() + 1,
        )

        widget.setFixedWidth(width - offset)
        common.move_widget_to_available_geo(widget)

        self._context_menu_active = True
        widget.exec_()
        self._context_menu_active = False
        # self.hide()


class DataKeyModel(BaseModel):
    """This model holds all the necessary data needed to display items to
    select for selecting the asset subfolders and/or bookmarks and assets.

    The model keeps track of the selections internally and is updated
    via the signals and slots."""

    def __init__(self, parent=None):
        super(DataKeyModel, self).__init__(parent=parent)
        self._bookmark = None

        # Note: the asset is stored as the `_active_item`
        self._datakey = None
        self.modelDataResetRequested.connect(self.__resetdata__)

        self.threads = {}

        self.threads[1] = ListInfoThread()
        self.threads[1].start()

    def data_key(self):
        return 'default'

    def data_type(self):
        return common.FileItem

    def __initdata__(self):
        """Bookmarks and assets are static. But files will be any number of """
        # Empties the thread's queue
        ListInfoWorker.reset_queue()

        self._data[self.data_key()] = {
            common.FileItem: {}, common.SequenceItem: {}}

        rowsize = QtCore.QSize(common.WIDTH, common.BOOKMARK_ROW_HEIGHT / 1.5)
        secondary_rowsize = QtCore.QSize(
            common.WIDTH, int(common.BOOKMARK_ROW_HEIGHT / 2))

        flags = (
            QtCore.Qt.ItemIsSelectable |
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsDropEnabled |
            QtCore.Qt.ItemIsEditable
        )
        data = self.model_data()

        if not self._parent_item:
            self.endResetModel()
            return

        # Thumbnail image
        default_thumbnail = ImageCache.instance().get_rsc_pixmap(
            u'assets_sm',
            common.SECONDARY_BACKGROUND,
            (common.BOOKMARK_ROW_HEIGHT / 1.5) - 2)
        default_thumbnail = default_thumbnail.toImage()
        thumbnail = ImageCache.instance().get_rsc_pixmap(
            u'assets_sm',
            common.SECONDARY_TEXT,
            (common.BOOKMARK_ROW_HEIGHT / 1.5) - 2)
        thumbnail = thumbnail.toImage()

        parent_path = u'/'.join(self._parent_item)
        dir_ = QtCore.QDir(parent_path)
        dir_.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
        indexes = []
        for file_info in sorted(dir_.entryInfoList(), key=lambda x: x.fileName()):
            description = u'Show files'
            if file_info.fileName() == common.ExportsFolder:
                description = u'Folder for data and cache files'
            if file_info.fileName() == common.ScenesFolder:
                description = u'Folder for storing project and scene files'
            if file_info.fileName() == common.RendersFolder:
                description = u'Folder for storing output images'
            if file_info.fileName() == common.TexturesFolder:
                description = u'Folder for storing texture-files used by scenes'

            idx = len(data)
            data[idx] = {
                QtCore.Qt.DisplayRole: file_info.fileName(),
                QtCore.Qt.EditRole: file_info.fileName(),
                QtCore.Qt.StatusTipRole: file_info.filePath(),
                QtCore.Qt.ToolTipRole: description,
                QtCore.Qt.SizeHintRole: secondary_rowsize,
                #
                common.DefaultThumbnailRole: thumbnail,
                common.DefaultThumbnailBackgroundRole: QtGui.QColor(0, 0, 0, 0),
                common.ThumbnailRole: thumbnail,
                common.ThumbnailBackgroundRole: QtGui.QColor(0, 0, 0, 0),
                #
                common.FlagsRole: flags,
                common.ParentRole: None,
                #
                common.StatusRole: False,
                common.TodoCountRole: 0,
            }
            indexes.append(idx)

        self.endResetModel()
        ListInfoWorker.add_to_queue([self.index(f, 0) for f in indexes])

    @QtCore.Slot(QtCore.QModelIndex)
    def set_bookmark(self, index):
        """Stores the currently active bookmark."""
        if not index.isValid():
            self._bookmark = None
            return

        self._bookmark = index.data(common.ParentRole)

    @QtCore.Slot(unicode)
    def set_data_key(self, key):
        """Stores the currently active data key."""
        self._datakey = key

    @QtCore.Slot(int)
    def set_data_type(self, datatype):
        """Stores the currently active data type."""
        self._datatype = datatype



class BaseControlButton(ClickableLabel):

    def __init__(self, parent=None):
        super(BaseControlButton, self).__init__(parent=parent)
        self._parent = None
        self.index = 0

        self.setMouseTracking(True)

    def set_parent(self, widget):
        self._parent = widget

    def set_text(self, text):
        self.setText(text.title())
        metrics = QtGui.QFontMetrics(common.PrimaryFont)
        width = metrics.width(self.text()) + common.INDICATOR_WIDTH
        self.setFixedWidth(width)

    def enterEvent(self, event):
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def paintEvent(self, event):
        if not self._parent:
            painter.end()

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        option = QtWidgets.QStyleOptionButton()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        if self._parent.currentIndex() == self.index:
            color = common.TEXT_SELECTED if hover else common.TEXT
        else:
            color = common.TEXT_SELECTED if hover else common.SECONDARY_TEXT

        common.draw_aliased_text(
            painter,
            common.PrimaryFont,
            self.rect(),
            self.text(),
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            color
        )


        if self._parent.currentIndex() == self.index:
            metrics = QtGui.QFontMetrics(common.PrimaryFont)
            rect = QtCore.QRect(self.rect())
            center = rect.center()
            rect.setHeight(3)
            rect.moveCenter(center)
            rect.moveTop(rect.top() + (metrics.height() / 2) + 3)
            rect.setWidth(metrics.width(self.text()))
            painter.setBrush(color)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRoundedRect(rect, 1, 1)


        painter.end()



class BookmarksButton(BaseControlButton):
    def __init__(self, parent=None):
        super(BookmarksButton, self).__init__(parent=parent)
        self.index = 0
        self.set_text(u'Bookmarks')


class AssetsButton(BaseControlButton):
    def __init__(self, parent=None):
        super(AssetsButton, self).__init__(parent=parent)
        self.index = 1
        self.set_text(u'Assets')



class FilesButton(BaseControlButton):
    """Drop-down widget to switch between the list"""

    def __init__(self, parent=None):
        self._view = None
        super(FilesButton, self).__init__(parent=parent)
        self.index = 2
        self.set_text(u'Files')

        self.clicked.connect(self.show_view)

    def view(self):
        return self._view

    def set_view(self, widget):
        self._view = widget

    @QtCore.Slot()
    def show_view(self):
        if not self.view():
            return

        s = self.view().parent().parent().stackedwidget
        if s.currentIndex() != 2:
            return
        key = s.currentWidget().model().sourceModel().data_key()
        if key:
            for n in xrange(self.view().model().rowCount()):
                index = self.view().model().index(n, 0)
                if key.lower() == index.data(QtCore.Qt.DisplayRole).lower():
                    self.view().selectionModel().setCurrentIndex(
                        index, QtCore.QItemSelectionModel.ClearAndSelect)

        pos = self.view().parent().mapToGlobal(self.view().parent().rect().bottomLeft())
        self.view().move(
            pos.x(),
            pos.y()
        )

        self.view().setFixedWidth(self.view().parent().rect().width())
        self.view().show()
        self.view().raise_()
        common.move_widget_to_available_geo(self.view())
        self.view().setFocus(QtCore.Qt.PopupFocusReason)



class ListControlWidget(QtWidgets.QWidget):
    """The bar above the list to control the mode, filters and sorting."""

    textChanged = QtCore.Signal(unicode)
    listChanged = QtCore.Signal(int)
    dataKeyChanged = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(ListControlWidget, self).__init__(parent=parent)
        self._controlview = None
        self._filesbutton = None

        self._createUI()
        self._connectSignals()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(common.INDICATOR_WIDTH * 3)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT)

        # Control view/model/button
        self._bookmarksbutton = BookmarksButton(parent=self)
        self._assetsbutton = AssetsButton(parent=self)
        self._filesbutton = FilesButton(parent=self)
        self._controlview = DataKeyView(parent=self)
        self._filesbutton.set_view(self._controlview)

        self._progresslabel = Progresslabel(parent=self)
        self._addbutton = AddButton(parent=self)
        self._todobutton = TodoButton(parent=self)
        self._filterbutton = FilterButton(parent=self)
        self._collapsebutton = CollapseSequenceButton(parent=self)
        self._archivedbutton = ToggleArchivedButton(parent=self)
        self._favouritebutton = ToggleFavouriteButton(parent=self)
        self._custombutton = CustomButton(parent=self)

        self.layout().addSpacing(common.INDICATOR_WIDTH * 2)
        self.layout().addWidget(self._bookmarksbutton)
        self.layout().addWidget(self._assetsbutton)
        self.layout().addWidget(self._filesbutton)
        self.layout().addStretch()
        self.layout().addWidget(self._progresslabel, 1)
        self.layout().addWidget(self._addbutton)
        self.layout().addWidget(self._todobutton)
        self.layout().addWidget(self._filterbutton)
        self.layout().addWidget(self._collapsebutton)
        self.layout().addWidget(self._archivedbutton)
        self.layout().addWidget(self._favouritebutton)
        self.layout().addWidget(self._custombutton)
        self.layout().addSpacing(common.INDICATOR_WIDTH * 2)

    @QtCore.Slot(QtCore.QModelIndex)
    def signal_dispatcher(self, index):
        self.listChanged.emit(2)
        self.dataKeyChanged.emit(index.data(QtCore.Qt.DisplayRole))
        self.textChanged.emit(index.data(QtCore.Qt.DisplayRole))

    def _connectSignals(self):
        pass

    def control_view(self):
        return self._controlview

    def control_button(self):
        return self.findChild(FilesButton)
