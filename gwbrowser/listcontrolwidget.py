# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903, C0330

"""Widget reponsible controlling the displayed list and the filter-modes."""

import sys
import functools
import re
from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser.gwscandir as gwscandir
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

from gwbrowser.assetswidget import AssetModel
from gwbrowser.bookmarkswidget import BookmarksModel

from gwbrowser.settings import local_settings


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

        count = 0
        for _, _, fileentries in common.walk(index.data(QtCore.Qt.StatusTipRole)):
            for entry in fileentries:
                count += 1
                if count > 999:
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
            common.PrimaryFont.family(),
            common.psize(common.SMALL_FONT_SIZE - 1),
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
                text = match.expand(ur'\1')


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
    message = QtCore.Signal(unicode)

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
        self.setStatusTip(u'Opens GWBrowser')

    def set_size(self, size):
        self.setFixedWidth(int(size))
        self.setFixedHeight(int(size))
        pixmap = ImageCache.get_rsc_pixmap(
            u'custom_bw', common.SECONDARY_TEXT, int(size))
        self.setPixmap(pixmap)

    def enterEvent(self, event):
        self.message.emit(self.statusTip())
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def paintEvent(self, event):
        """Browser button's custom paint event."""
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
            lambda: QtGui.QDesktopServices.openUrl(ur'https://gwbcn.slack.com/'))
        self.setStatusTip(u'Open Slack!')


class ControlButton(ClickableLabel):
    """Baseclass used for controls buttons to control list display."""
    message = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(ControlButton, self).__init__(parent=parent)
        self._parent = None
        self.setFixedSize(
            common.INLINE_ICON_SIZE,
            common.INLINE_ICON_SIZE,
        )
        self.clicked.connect(self.action)
        self.setStatusTip(u'')

    def enterEvent(self, event):
        self.message.emit(self.statusTip())
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

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
        """ControlButton's custom paint event."""
        painter = QtGui.QPainter()
        painter.begin(self)

        option = QtWidgets.QStyleOptionButton()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        color = common.FAVOURITE if self.state() else QtGui.QColor(255,255,255,50)
        color = common.TEXT_SELECTED if hover else color
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
        assetswidget = self._parent.widget(1)
        index = assetswidget.model().sourceModel().active_index()
        index = assetswidget.model().mapFromSource(index)
        if not index.isValid():
            return
        assetswidget.show_todos(index)

    def repaint(self):
        super(TodoButton, self).repaint()
        if self._parent.currentIndex() in (2,):
            self.show()
        else:
            self.hide()


class FilterButton(ControlButton):
    """Button for showing the filter editor."""

    def __init__(self, parent=None):
        super(FilterButton, self).__init__(parent=parent)
        description = u'Edit search filter'
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
            filter_text = common.FilterTextRegex.sub(u' ', filter_text)
            filter_text = re.sub(r'\s', ' ', filter_text)
        editor = FilterEditor(filter_text, parent=self._parent)
        pos = self._parent.rect().topLeft()
        pos = self._parent.mapToGlobal(pos)

        editor.move(pos)
        editor.setFixedWidth(self._parent.rect().width())

        def func(filter_text):
            filter_text = common.FilterTextRegex.sub(' ', filter_text)
            filter_text = re.sub(r'\s\s*', u' ', filter_text)
            # filter_text = re.sub(r'([^\s])', r'\\\1', filter_text)
            filter_text = re.sub(r'\s', r'[\S\s]*', filter_text)
            self.current().model().filterTextChanged.emit(filter_text)

        editor.finished.connect(func)
        editor.finished.connect(self.repaint)
        editor.finished.connect(editor.deleteLater)

        editor.show()


class CollapseSequenceButton(ControlButton):
    """The buttons responsible for collapsing/expanding the sequences of the
    current list.

    """

    def __init__(self, parent=None):
        super(CollapseSequenceButton, self).__init__(parent=parent)
        description = u'Group sequences together'
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
        """Only lists containing sequences can be collapsed."""
        if self._parent.currentIndex() not in (2, 3):
            return

        datatype = self.current().model().sourceModel().data_type()
        if datatype == common.FileItem:
            self.current().model().sourceModel().dataTypeChanged.emit(common.SequenceItem)
        else:
            self.current().model().sourceModel().dataTypeChanged.emit(common.FileItem)

    def repaint(self):
        super(CollapseSequenceButton, self).repaint()
        if self._parent.currentIndex() in (2, 3):
            self.show()
        else:
            self.hide()


class ToggleArchivedButton(ControlButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(ToggleArchivedButton, self).__init__(parent=parent)
        description = u'Show archived items'
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

    def repaint(self):
        super(ToggleArchivedButton, self).repaint()
        if self._parent.currentIndex() < 3:
            self.show()
        else:
            self.hide()


class ToggleFavouriteButton(ControlButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(ToggleFavouriteButton, self).__init__(parent=parent)
        description = u'Show my favourites only'
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

    def repaint(self):
        super(ToggleFavouriteButton, self).repaint()
        if self._parent.currentIndex() < 3:
            self.show()
        else:
            self.hide()


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


        # This will open the Saver to save a new file
        if self._parent.currentIndex() == 2:
            import gwbrowser.saver as saver

            index = self._parent.currentWidget().selectionModel().currentIndex()
            if index.isValid():
                if not index.data(common.StatusRole):
                    return

            bookmark_model = BookmarksModel()
            asset_model = AssetModel()

            extension = u'ext' # This is a generic extension that can be overriden
            currentfile = None
            data_key = self.current().model().sourceModel().data_key()
            subfolder = data_key if data_key else u'/'

            if index.isValid():
                # When there is a file selected, we will check if it is a sequence
                # increment the version number if it is.
                iscollapsed = common.is_collapsed(index.data(QtCore.Qt.StatusTipRole))
                if iscollapsed:
                    # Replacing the frame-number with placeholder characters
                    currentfile = iscollapsed.expand(ur'\1{}\3')
                    currentfile = currentfile.format(u'#' * len(index.data(common.FramesRole)[-1]))
                else:
                    # Getting the last frame of the sequence
                    currentfile = common.get_sequence_endpath(index.data(QtCore.Qt.StatusTipRole))
                extension = currentfile.split(u'.').pop()

            # If both the currentfile and the data_key are valid we'll set
            # the default location to be the subfolder of the current file.
            if currentfile and data_key:
                # Removing the parentpath
                server, job, root, asset, _, _ = index.data(common.ParentRole)
                parentpath = u'/'.join((server, job, root, asset))
                subfolder = index.data(QtCore.Qt.StatusTipRole)
                subfolder = QtCore.QFileInfo(subfolder)
                subfolder = subfolder.dir().path()
                subfolder = subfolder.replace(parentpath, '')
            else:
                subfolder = '{}/{}'.format(data_key, subfolder)

            subfolder = subfolder.strip(u'/')
            sys.stdout.write(subfolder)

            widget = saver.SaverWidget(
                bookmark_model,
                asset_model,
                extension,
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

    def repaint(self):
        """The button is only visible when showing bookmarks or files."""
        super(AddButton, self).repaint()
        if self._parent.currentIndex() in (0, 2):
            self.show()
        else:
            self.hide()


class GenerateThumbnailsButton(ControlButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(GenerateThumbnailsButton, self).__init__(parent=parent)
        description = u'Turn auto thumbnail generation ON of OFF'
        self.setToolTip(description)
        self.setStatusTip(description)

    def pixmap(self, c):
        return ImageCache.get_rsc_pixmap(u'pick_thumbnail', c, common.INLINE_ICON_SIZE)

    def state(self):
        """The state of the auto-thumbnails"""
        if self._parent.currentIndex() < 2:
            return False
        model = self._parent.currentWidget().model().sourceModel()
        return model.generate_thumbnails

    @QtCore.Slot()
    def action(self):
        """Toggles thumbnail generation."""
        model = self._parent.currentWidget().model().sourceModel()
        val = model.generate_thumbnails

        cls = model.__class__.__name__
        local_settings.setValue(u'widget/{}/generate_thumbnails'.format(cls), not val)
        if not val == False:
            ImageCacheWorker.reset_queue()
        model.generate_thumbnails = not val


    def repaint(self):
        """Will only show for favourite and file items."""
        super(GenerateThumbnailsButton, self).repaint()
        if self._parent.currentIndex() >= 2:
            self.show()
        else:
            self.hide()


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
        background.setAlpha(200)
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
        color = common.TEXT_SELECTED if hover else common.TEXT
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
            if index.data(common.TodoCountRole) >= 999:
                text = u'   |   999+ files'
            else:
                text = u'   |   {} files'.format(index.data(common.TodoCountRole))
            color = common.TEXT_SELECTED if selected else common.FAVOURITE
            color = common.TEXT_SELECTED if hover else color
            width = common.draw_aliased_text(
                painter, common.SecondaryFont, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)
            rect.setLeft(rect.left() + width)

        text = '   |   {}'.format(index.data(QtCore.Qt.ToolTipRole))
        color = common.TEXT_SELECTED if selected else common.SECONDARY_TEXT
        color = common.TEXT_SELECTED if hover else color
        width = common.draw_aliased_text(
            painter, common.SecondaryFont, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)

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
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self.context_menu_cls = ListControlContextMenu
        self._context_menu_active = False
        self.clicked.connect(self.activated)
        self.clicked.connect(self.hide)
        self.clicked.connect(self.parent().signal_dispatcher)

        self.setModel(DataKeyModel())
        self.setItemDelegate(DataKeyViewDelegate(parent=self))

        # self.setWindowOpacity(0.0)
        self.effect = QtWidgets.QGraphicsOpacityEffect(self.viewport())
        self.effect.setOpacity(0.0)
        self.viewport().setGraphicsEffect(self.effect)

        self.animation = QtCore.QPropertyAnimation(self.effect, QtCore.QByteArray('opacity'))
        self.animation.setDuration(250)
        self.animation.setKeyValueAt(0, 0)
        self.animation.setKeyValueAt(0.5, 0.8)
        self.animation.setKeyValueAt(1, 1.0)

    def hideEvent(self, event):
        self.animation.stop()

    def showEvent(self, event):
        self.animation.start(QtCore.QAbstractAnimation.KeepWhenStopped)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.hide()
            return
        super(DataKeyView, self).keyPressEvent(event)

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
        for n in xrange(common.LTHREAD_COUNT):
            self.threads[n] = ListInfoThread()
            self.threads[n].start()

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
            u'folder_sm',
            common.SECONDARY_TEXT,
            (common.BOOKMARK_ROW_HEIGHT / 1.5) - 2)
        default_thumbnail = default_thumbnail.toImage()
        thumbnail = ImageCache.instance().get_rsc_pixmap(
            u'folder_sm',
            common.SECONDARY_TEXT,
            (common.BOOKMARK_ROW_HEIGHT / 1.5) - 2)
        thumbnail = thumbnail.toImage()

        parent_path = u'/'.join(self._parent_item)
        indexes = []
        entries = sorted(([f for f in gwscandir.scandir(parent_path)]), key=lambda x: x.name)

        for entry in entries:
            if entry.name in common.ASSET_FOLDERS:
                description = common.ASSET_FOLDERS[entry.name]
            else:
                description = common.ASSET_FOLDERS[u'misc']

            if entry.name.startswith(u'.'):
                continue
            if not entry.is_dir():
                continue

            idx = len(data)
            data[idx] = {
                QtCore.Qt.DisplayRole: entry.name,
                QtCore.Qt.EditRole: entry.name,
                QtCore.Qt.StatusTipRole: entry.path.replace('\\', '/'),
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
    """Baseclass for the list control buttons."""
    message = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(BaseControlButton, self).__init__(parent=parent)
        self._parent = None
        self.index = 0
        self.setMouseTracking(True)
        self.setStatusTip(u'')

    def set_parent(self, widget):
        self._parent = widget

    def set_text(self, text):
        if text is None:
            text = u'Files'
        if text == u'':
            text == u'File'
        self.setText(text.title())
        metrics = QtGui.QFontMetrics(common.PrimaryFont)
        width = metrics.width(self.text()) + common.INDICATOR_WIDTH
        self.setFixedWidth(width)

    def enterEvent(self, event):
        self.message.emit(self.statusTip())
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
        self.setStatusTip(u'Show the list of added bookmarks')


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
        """Shows the ``DataKeyView`` widget for browsing."""
        if self.view().model().rowCount() == 0:
            return

        def select_key(parent):
            """Selects the current data-key in the list."""
            key = parent.stackedwidget.currentWidget().model().sourceModel().data_key()
            if not key:
                return
            for n in xrange(self.view().model().rowCount()):
                index = self.view().model().index(n, 0)
                if key.lower() == index.data(QtCore.Qt.DisplayRole).lower():
                    self.view().selectionModel().setCurrentIndex(
                        index, QtCore.QItemSelectionModel.ClearAndSelect)
                    return

        if not self.view():
            return

        if not self.view().isHidden():
            self.view().hide()

        parent = self.view().parent().parent()
        if parent.stackedwidget.currentIndex() != 2:
            return # We're not showing the widget when files are not tyhe visible list

        geo = parent.stackedwidget.currentWidget().geometry()
        self.view().setGeometry(geo)
        # Align to top-left corner and sets the width
        topleft =parent.stackedwidget.currentWidget().mapToGlobal(
            parent.stackedwidget.currentWidget().rect().topLeft())
        self.view().move(topleft)

        self.view().show()
        self.view().raise_()

        common.move_widget_to_available_geo(self.view())
        self.view().setFocus(QtCore.Qt.PopupFocusReason)

        select_key(parent)

class FavouritesButton(BaseControlButton):
    """Drop-down widget to switch between the list"""

    def __init__(self, parent=None):
        super(FavouritesButton, self).__init__(parent=parent)
        self.index = 3
        self.set_text(u'My favourites')


class ListControlWidget(QtWidgets.QWidget):
    """The bar above the list to control the mode, filters and sorting."""

    textChanged = QtCore.Signal(unicode)
    listChanged = QtCore.Signal(int)
    dataKeyChanged = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(ListControlWidget, self).__init__(parent=parent)
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
        self._favouritesbutton = FavouritesButton(parent=self)

        self._progresslabel = Progresslabel(parent=self)
        self._addbutton = AddButton(parent=self)
        self._generatethumbnailsbutton = GenerateThumbnailsButton(parent=self)
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
        self.layout().addWidget(self._favouritesbutton)
        self.layout().addStretch()
        self.layout().addWidget(self._progresslabel, 1)
        self.layout().addWidget(self._addbutton)
        self.layout().addWidget(self._generatethumbnailsbutton)
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
