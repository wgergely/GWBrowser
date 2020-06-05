# -*- coding: utf-8 -*-
"""File save dialog.

Initiate ``AddFileWidget`` with a file **extension** and use the
``AddFileWidget.get_file_path()`` to get the destination path.

Example:

    .. code-block:: python

          w = AddFileWidget(u'ma')
          if w.exec_() == QtWidgets.QDialog.Accepted:
              file_path = w.get_file_path()

          w = AddFileWidget(None, file='C:/myfiletoincrement_v0001.ma')
          if w.exec_() == QtWidgets.QDialog.Accepted:
              # Incremented version number to v0002 > C:/myfiletoincrement_v0002.ma
              file_path = w.get_file_path()


The widget will generate a valid filepath based on bookmark, asset and folder
selections. The resulting file path, if contains any version numbers, will
automatically be incremented to be the hightest in the destination folder.

The path is generated using the tokens set in ``FILE_NAME_PATTERN``. The
destination folder will also depend on the task the file is associated with.
These task, or modes, are defined in ``SCENE_FOLDERS`` and ``EXPORT_FOLDERS``.

"""
import functools
import uuid
from PySide2 import QtCore, QtWidgets, QtGui

import bookmarks.log as log
import bookmarks.common as common
import bookmarks.bookmark_db as bookmark_db
import bookmarks.settings as settings
import _scandir as _scandir
import bookmarks.common_ui as common_ui
import bookmarks.delegate as delegate
import bookmarks.baselist as baselist
import bookmarks.basecontextmenu as basecontextmenu
import bookmarks.images as images
import bookmarks.defaultpaths as defaultpaths

from bookmarks.bookmarkswidget import BookmarksModel
from bookmarks.assetswidget import AssetModel


class SelectButton(QtWidgets.QLabel):
    """A clickable text with a pop-up list widget.

    Used to pick the bookmark, asset and destination folder.

    Args:
        label (unicode): The default text to show.
        view (QWidget): The view widget associated wit the button.

    """
    clicked = QtCore.Signal()
    widgetMoved = QtCore.Signal(QtCore.QRect)

    ContextMenu = None

    def __init__(self, label, view, parent=None):
        super(SelectButton, self).__init__(parent=parent)
        self._view = view
        self._label = label
        self.update_timer = QtCore.QTimer(parent=self)
        self.update_timer.setSingleShot(False)
        self.update_timer.setInterval(200)

        self.setFixedHeight(common.ROW_HEIGHT())
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setText(self._label)
        self.setFocusProxy(self.view())
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

        self._connect_signals()

    def _connect_signals(self):
        self.clicked.connect(self.show_view)
        self.widgetMoved.connect(self.move_view)
        if hasattr(self.view().model(), u'sourceModel'):
            # We will temporarily block the selection model's signals whilst
            # the source model is loading. This is to prevent it from emiting
            # changed signals as the model is being populated.
            self.view().model().sourceModel().modelAboutToBeReset.connect(
                functools.partial(self.view().blockSignals, True))
            self.view().model().sourceModel().modelReset.connect(
                functools.partial(self.view().blockSignals, False))
            self.view().model().sourceModel().modelReset.connect(self.select_active)

        self.update_timer.timeout.connect(self.update_text)

    @QtCore.Slot()
    def update_text(self):
        """Slot responsible for keeping the button's text in sync with the
        current view selection.

        """
        if not self.view().selectionModel().hasSelection():
            self.setText(self._label)
            self.update()
            return
        index = self.view().selectionModel().currentIndex()
        if not index.isValid():
            self.setText(self._label)
            self.update()
            return
        if isinstance(index.model(), SelectFolderModel):
            if index.column() != 0:
                index = index.sibling(index.row(), 0)
            file_path = self.view().model().filePath(index)
            root_path = self.view().model().rootPath()
            if root_path not in file_path:
                self.view().selectionModel().setCurrentIndex(
                    QtCore.QModelIndex(), QtCore.QItemSelectionModel.Clear)
                self.setText(self._label)
                self.update()
                return
            text = file_path.lower().replace(root_path.lower(), u'').strip('/')
        else:
            text = index.data(QtCore.Qt.DisplayRole)
        self.setText(text)
        self.update()

    @QtCore.Slot()
    def select_active(self):
        """If there's an active index, we will select it and emit the change."""
        active_index = self.view().model().sourceModel().active_index()
        if not active_index.isValid():
            return

        proxy_index = self.view().model().mapFromSource(active_index)
        self.view().scrollTo(proxy_index, QtWidgets.QAbstractItemView.PositionAtCenter)
        self.view().selectionModel().setCurrentIndex(
            proxy_index, QtCore.QItemSelectionModel.ClearAndSelect)

        self.view().clicked.emit(proxy_index)
        self.update()

    def has_selection(self):
        return self.view().selectionModel().hasSelection()

    def view(self):
        """The view associated with this custom button."""
        return self._view

    def set_view(self, widget):
        """Sets the view associated with this custom button."""
        self._view = widget
        widget.setParent(self)

    @QtCore.Slot()
    def move_view(self):
        """Moves the view associated with the button in place."""
        self.view().setGeometry(self.window().geometry())
        pos = self.window().geometry().bottomLeft()
        # pos = self.window().mapToGlobal(pos)
        self.view().move(pos)

    @QtCore.Slot()
    def show_view(self):
        """Slot connected to the ``clicked`` signal of the button.
        Shows the view associated with this custom button.

        """
        if not self.view():
            return
        if self.view().isVisible():
            self.view().hide()
            return

        self.view().setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Window)

        self.move_view()

        if self.view().selectionModel().hasSelection():
            self.view().scrollTo(self.view().selectionModel().currentIndex(),
                                 QtWidgets.QAbstractItemView.PositionAtCenter)

        self.view().show()
        self.view().setFocus()

    @QtCore.Slot(unicode)
    def setText(self, text):
        super(SelectButton, self).setText(text)
        font, metrics = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())
        width = metrics.width(self.text().upper())
        self.setFixedWidth(width + common.MARGIN())
        self.update()

    def paintEvent(self, event):  # pylint: disable=W0613
        """``SelectButton``'s custom paint event to show the current view
        selection.

        """
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        color = common.FAVOURITE if hover else common.TEXT
        color = common.ADD if self.has_selection() else color

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        font, metrics = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())
        common.draw_aliased_text(
            painter, font, self.rect(),
            self.text().upper(), QtCore.Qt.AlignCenter, color)

        if not hover:
            return
        rect = QtCore.QRect(self.rect())
        rect.setTop(rect.bottom() - (common.ROW_SEPARATOR() * 2))
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(color)
        painter.drawRect(rect)
        painter.end()

    def contextMenuEvent(self, event):  # pylint: disable=W0613
        if not self.ContextMenu:
            return

        w = self.ContextMenu(parent=self)  # pylint: disable=E1102
        pos = self.rect().bottomLeft()
        pos = self.mapToGlobal(pos)
        w.move(pos)

        common.move_widget_to_available_geo(w)
        w.exec_()

    def enterEvent(self, event):  # pylint: disable=W0613
        self.update()

    def leaveEvent(self, event):  # pylint: disable=W0613
        self.update()

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.button() == QtCore.Qt.LeftButton:
            pos = common.cursor.pos()
            pos = self.mapFromGlobal(pos)
            if self.rect().contains(pos):
                self.clicked.emit()

    def hideEvent(self, event):  # pylint: disable=W0613
        self.view().hide()
        if self.update_timer.isActive():
            self.update_timer.stop()

    def showEvent(self, event):  # pylint: disable=W0613
        self.view().hide()
        if not self.update_timer.isActive():
            self.update_timer.start()

    def resizeEvent(self, event):  # pylint: disable=W0613
        self.widgetMoved.emit(self.rect())

    def moveEvent(self, event):  # pylint: disable=W0613
        self.widgetMoved.emit(self.rect())


class BaseListView(baselist.BaseInlineIconWidget):
    """The base class used to view the ``BookmarksModel`` and ``AssetModel``
    models. The class is a control icon-less version of the
    ``baselist.BaseInlineIconWidget`` widget.

    The ``activated`` signal will hide the view but the activated signal itself
    is **not** connected in this class.

    """
    SourceModel = None
    Delegate = None
    ContextMenu = None

    def __init__(self, parent=None):
        super(BaseListView, self).__init__(parent=parent)
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint
        )

        self.installEventFilter(self)
        self.activated.connect(self.hide)

    def eventFilter(self, widget, event):
        """Event filter with a custom paint event."""
        if widget != self:
            return False

        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            pen = QtGui.QPen(common.SEPARATOR)
            pen.setWidth(common.ROW_SEPARATOR())
            painter.setPen(pen)
            painter.setBrush(common.SECONDARY_BACKGROUND)
            o = common.INDICATOR_WIDTH() * 2
            painter.drawRoundedRect(self.rect(), o, o)
            painter.end()
            return True
        return False

    def showEvent(self, event):
        self.adjust_height()
        if self.selectionModel().hasSelection():
            index = self.selectionModel().currentIndex()
            self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)

    @QtCore.Slot()
    def adjust_height(self, *args, **kwargs):  # pylint: disable=W0613
        """Adjusts the height of the ``SelectListView`` to it's contents."""
        height = 0
        margins = self.viewportMargins().top() + self.viewportMargins().bottom()
        margins += self.getContentsMargins()[1] + self.getContentsMargins()[3]

        option = QtWidgets.QStyleOptionViewItem()
        option.initFrom(self)

        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0)
            if not index.isValid():
                break
            height += self.itemDelegate().sizeHint(option, index).height()
            if height > common.HEIGHT():
                break
        if height == 0:
            self.hide()
            return
        height += margins
        self.setFixedHeight(height)

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.hide()

    def buttons_hidden(self):
        return True

    def inline_icons_count(self):
        return 0


class ThreadlessBookmarksModel(BookmarksModel):
    def __init__(self, has_threads=False, parent=None):
        super(ThreadlessBookmarksModel, self).__init__(
            has_threads=False, parent=parent)


class BookmarksListView(BaseListView):
    SourceModel = ThreadlessBookmarksModel
    Delegate = delegate.BookmarksWidgetDelegate
    ContextMenu = None

    @QtCore.Slot()
    def reselect_previous(self):
        """This is to override the default behaviour and instead always
        select the active index."""
        index = self.model().sourceModel().active_index()

        if not index.isValid():
            super(BookmarksListView, self).reselect_previous()
            return

        index = self.model().mapFromSource(index)
        self.selectionModel().setCurrentIndex(
            index, QtCore.QItemSelectionModel.ClearAndSelect)
        self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)


class ThreadlessAssetModel(AssetModel):
    def __init__(self, has_threads=False, parent=None):
        super(ThreadlessAssetModel, self).__init__(
            has_threads=False, parent=parent)


class AssetsListView(BaseListView):
    SourceModel = ThreadlessAssetModel
    Delegate = delegate.AssetsWidgetDelegate
    ContextMenu = None

    @QtCore.Slot()
    def reselect_previous(self):
        """This is to override the default behaviour and instead always
        select the active index."""
        index = self.model().sourceModel().active_index()

        if not index.isValid():
            super(AssetsListView, self).reselect_previous()
            return

        index = self.model().mapFromSource(index)
        self.selectionModel().setCurrentIndex(
            index, QtCore.QItemSelectionModel.ClearAndSelect)
        self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)


class SelectFolderViewContextMenu(basecontextmenu.BaseContextMenu):
    """The context-menu associated with the BrowserButton."""

    def __init__(self, index, parent=None):
        super(SelectFolderViewContextMenu, self).__init__(
            index, parent=parent)

        if not self.index.isValid():
            return

        self.add_new_folder_menu()
        self.add_reveal_item_menu()
        self.add_separator()
        self.add_view_options()

    @basecontextmenu.contextmenu
    def add_view_options(self, menu_set):
        menu_set[u'expand_all'] = {
            u'text': u'Expand all',
            u'action': self.parent().expandAll,
        }
        menu_set[u'collapse_all'] = {
            u'text': u'Collapse all',
            u'action': self.parent().collapseAll,
        }
        return menu_set

    @basecontextmenu.contextmenu
    def add_new_folder_menu(self, menu_set):
        if not self.index.isValid():
            return menu_set

        if not self.parent().model().isDir(self.index):
            return menu_set

        def add_folder():
            if self.index.column() != 0:
                self.index = self.index.sibling(self.index.row(), 0)

            w = QtWidgets.QInputDialog(parent=self)
            w.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
            w.setLabelText(u'Enter the name of the folder:')

            if w.exec_():
                if not w.textValue():
                    return

                index = self.parent().model().mkdir(self.index, w.textValue())
                self.parent().scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
                self.parent().selectionModel().setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect
                )

        menu_set[u'Add folder'] = {
            u'text': u'New folder...',
            u'action': add_folder,
        }
        return menu_set

    @basecontextmenu.contextmenu
    def add_reveal_item_menu(self, menu_set):
        def reveal():
            file_path = self.parent().model().filePath(self.index)
            common.reveal(file_path)

        menu_set[u'reveal'] = {
            u'text': u'Reveal in file explorer...',
            u'action': reveal,
        }
        return menu_set


class SelectFolderModelIconProvider(QtWidgets.QFileIconProvider):
    """SelectFolderModel's custom icon provider."""

    def icon(self, file_info):
        if file_info.isDir():
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'folder', common.SEPARATOR, common.THUMBNAIL_IMAGE_SIZE * 0.5)
        else:
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'files', common.SEPARATOR, common.THUMBNAIL_IMAGE_SIZE * 0.5)

        return QtGui.QIcon(pixmap)


class SelectFolderModel(QtWidgets.QFileSystemModel):
    """A customised QFileSystemModel used to select a destination folder."""

    def __init__(self, parent=None):
        super(SelectFolderModel, self).__init__(parent=parent)
        self.setNameFilterDisables(True)
        self.setIconProvider(SelectFolderModelIconProvider(parent=self))

    def flags(self, index):
        """Non-folder items are disabled and unselectable."""
        if self.isDir(index):
            return super(SelectFolderModel, self).flags(index)
        return QtCore.Qt.NoItemFlags

    def columnCount(self, parent=QtCore.QModelIndex):  # pylint: disable=W0613
        """The extra column is used for folder descriptions."""
        return 6
        # c = super(SelectFolderModel, self).columnCount(parent=parent)
        # return c + 1

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """We're matching the folder-name with our description."""
        if index.column() == 4:
            if role == QtCore.Qt.DisplayRole:
                return u''
        if index.column() == 5:
            if role == QtCore.Qt.DisplayRole:
                if self.isDir(index):
                    sibling = index.sibling(index.row(), 0)
                    k = self.fileName(sibling).lower()
                    if k in defaultpaths.TASK_FOLDERS:
                        return defaultpaths.TASK_FOLDERS[k]
                return u''
        if role == QtCore.Qt.DisplayRole:
            data = super(SelectFolderModel, self).data(index, role=role)
            if data:
                if index.parent() == self.index(self.rootPath()):
                    return data.upper()

        if role == QtCore.Qt.SizeHintRole and index.column() == 0:
            return QtCore.QSize(1, common.ROW_HEIGHT() * 0.8)
        return super(SelectFolderModel, self).data(index, role=role)


class SelectFolderView(QtWidgets.QTreeView):
    """A QTreeView widget to display our QFileSystemModel. The widget is used
    to select the destination folder of our new file.

    The folder selection will be saved to the local settings and reapplied,
    when the widget is shown.

    """
    SourceModel = SelectFolderModel
    ContextMenu = SelectFolderViewContextMenu

    def __init__(self, parent=None):
        super(SelectFolderView, self).__init__(parent=parent)
        self._initialized = False
        self._context_menu_open = False

        self.setModel(self.SourceModel(parent=self))

        self.setAnimated(False)
        self.setHeaderHidden(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setUniformRowHeights(True)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self.header().setDefaultSectionSize(common.WIDTH() * 0.5)
        self.header().setDefaultSectionSize(common.WIDTH() * 0.5)

        self.header().setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self.header().setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self.header().setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        self.header().setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        self.header().setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)
        self.header().setSectionResizeMode(5, QtWidgets.QHeaderView.Fixed)

        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.installEventFilter(self)

        self.hideColumn(1)
        self.hideColumn(2)
        self.hideColumn(3)
        self.hideColumn(4)

        self._connect_signals()

    def eventFilter(self, widget, event):
        if widget != self:
            return False

        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            pen = QtGui.QPen(common.SEPARATOR)
            pen.setWidth(common.ROW_SEPARATOR())
            painter.setPen(pen)
            painter.setBrush(common.SECONDARY_BACKGROUND)
            o = common.INDICATOR_WIDTH() * 2
            painter.drawRoundedRect(self.rect(), o, o)
            painter.end()
            return True
        return False

    def _connect_signals(self):
        self.model().directoryLoaded.connect(self.restore_previous_selection)
        self.model().directoryLoaded.connect(self.adjust_height)

        self.expanded.connect(self.adjust_height)
        self.collapsed.connect(self.adjust_height)

        self.selectionModel().currentChanged.connect(self.active_changed)
        self.activated.connect(self.hide)

    @QtCore.Slot(unicode)
    def set_folder(self, path):
        """Slot to responds to mode changes.

        When a mode has specifically set we will select a the corresponding
        destination in the asset. If the folder doesn't exist we will prompt the
        user to create it.

        """
        folder_root_path = self.model().filePath(self.rootIndex())
        dir_path = u'{}/{}'.format(folder_root_path, path)

        index = self.model().index(dir_path)
        if not index.isValid():
            mbox = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Question,
                u'Destination does not exist',
                u'"{}" does not exist. Do you want to create it now?'.format(
                    path.upper()),
                buttons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
                parent=self
            )
            if mbox.exec_() == QtWidgets.QMessageBox.Yes:
                if not QtCore.QDir(folder_root_path).mkpath(path):
                    s = u'Error making folder'
                    log.error(s)
                    common_ui.ErrorBox(
                        s,
                        u'An unknown error occured',
                    ).open()
                    raise RuntimeError(s)

        index = self.model().index(dir_path)

        if not index.isValid():
            return

        self.setCurrentIndex(index)

    @QtCore.Slot(QtCore.QModelIndex)
    def active_changed(self, index):
        """The slot called when active item changes.

        Saves the selection to the local preferences for future use.
        The slot is connected to the view.selectionModel's ``currentChanged``
        signal.

        """
        if not index.isValid():
            return
        if index.flags() == QtCore.Qt.NoItemFlags:
            return

        folder_root_path = self.model().filePath(self.rootIndex())
        folder_filepath = self.model().filePath(index)
        folder_basepath = folder_filepath.replace(
            folder_root_path, u'').strip(u'/')

        settings.local_settings.setValue(
            u'saver/folder_filepath', folder_filepath)
        settings.local_settings.setValue(
            u'saver/folder_basepath', folder_basepath)
        settings.local_settings.setValue(
            u'saver/folder_rootpath', folder_root_path)

    @QtCore.Slot()
    def restore_previous_selection(self):
        """After each root path change we will try to reapply the previous user
        selections.

        """
        if self._initialized:
            return

        folder_basepath = settings.local_settings.value(
            u'saver/folder_basepath')

        if not folder_basepath:
            self._initialized = True
            return

        # Check if path is part of the current selection
        path = u'{}/{}'.format(self.model().rootPath(), folder_basepath)
        index = self.model().index(path)
        if not index.isValid():
            self._initialized = True
            return

        self.selectionModel().setCurrentIndex(
            index, QtCore.QItemSelectionModel.ClearAndSelect)
        self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
        self.activated.emit(index)

        self._initialized = True

    def showEvent(self, event):
        self.adjust_height()
        if self.selectionModel().hasSelection():
            self.scrollTo(self.selectionModel().currentIndex(),
                          QtWidgets.QAbstractItemView.PositionAtCenter)

    @QtCore.Slot()
    def adjust_height(self, *args, **kwargs):
        """Adjusts the size of the ``SelectFolderView`` to fit its contents exactly."""
        row_height = 0
        margins = self.viewportMargins().top() + self.viewportMargins().bottom()
        margins += self.getContentsMargins()[1] + self.getContentsMargins()[3]

        option = QtWidgets.QStyleOptionViewItem()
        option.initFrom(self)
        #
        index = self.rootIndex()
        while True:
            index = self.indexBelow(index)
            index.data(QtCore.Qt.DisplayRole)
            row_height += self.rowHeight(index)
            if not index.isValid():
                break
        height = row_height + margins
        if height > common.HEIGHT():
            height = common.HEIGHT()
        self.setFixedHeight(height)

    @QtCore.Slot()
    def reset_active(self):
        """Slot called when a source model is about to be reset.

        I'm clearing the selectionModel's current index and the model to make
        sure the selection doesn't persist once the model has been reset.

        """
        self.selectionModel().clearCurrentIndex()
        self.selectionModel().reset()
        self.model().setRootPath(u'.')
        self.setRootIndex(QtCore.QModelIndex())

    @QtCore.Slot(QtCore.QModelIndex)
    def set_active(self, index):
        """Slot connected to the activeChanged signal."""
        if not index.isValid():
            return

        if index.flags() == QtCore.Qt.NoItemFlags:
            return

        path = index.data(QtCore.Qt.StatusTipRole)
        if not path:
            return

        self.model().setRootPath(path)
        index = self.model().index(path)
        self.setRootIndex(index)

        self._initialized = False

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if self._context_menu_open:
            return
        if event.lostFocus():
            self.hide()

    @QtCore.Slot(QtCore.QModelIndex)
    def itemActivated(self, index):
        """Slot connected to the doubleClicked signal."""
        if not index.isValid():
            return
        if index.flags() == QtCore.Qt.NoItemFlags:
            return
        if index.column() != 0:
            return

        self.activated.emit(index)

    def contextMenuEvent(self, event):
        """Context menu event."""
        index = self.indexAt(event.pos())

        width = self.viewport().geometry().width()
        width = (width * 0.5) if width > (common.WIDTH() * 0.6) else width
        width = width - common.INDICATOR_WIDTH()

        widget = self.ContextMenu(  # pylint: disable=E1102
            index, parent=self)
        if index.isValid():
            rect = self.visualRect(index)
            gpos = self.viewport().mapToGlobal(event.pos())
            widget.move(
                gpos.x(),
                self.viewport().mapToGlobal(rect.bottomLeft()).y(),
            )
        else:
            widget.move(common.cursor.pos())

        widget.setFixedWidth(width)
        widget.move(widget.x() + common.INDICATOR_WIDTH(), widget.y())
        common.move_widget_to_available_geo(widget)

        self._context_menu_open = True
        widget.exec_()
        self._context_menu_open = False


class ThumbnailContextMenu(basecontextmenu.BaseContextMenu):
    """Context menu associated with the thumbnail."""

    def __init__(self, parent=None):
        super(ThumbnailContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_thumbnail_menu()

    @basecontextmenu.contextmenu
    def add_thumbnail_menu(self, menu_set):
        """Menu for thumbnail operations."""
        capture_pixmap = images.ImageCache.get_rsc_pixmap(
            u'capture_thumbnail', common.SECONDARY_TEXT, common.MARGIN())
        pick_thumbnail_pixmap = images.ImageCache.get_rsc_pixmap(
            u'pick_thumbnail', common.SECONDARY_TEXT, common.MARGIN())
        remove_thumbnail_pixmap = images.ImageCache.get_rsc_pixmap(
            u'remove', common.FAVOURITE, common.MARGIN())

        menu_set[u'Capture thumbnail'] = {
            u'icon': capture_pixmap,
            u'action': self.parent().capture
        }
        menu_set[u'Pick thumbnail'] = {
            u'icon': pick_thumbnail_pixmap,
            u'action': self.parent().pick_thumbnail
        }
        menu_set[u'separator'] = {}
        menu_set[u'Reset thumbnail'] = {
            u'icon': remove_thumbnail_pixmap,
            u'action': self.parent().reset_thumbnail
        }
        return menu_set


class ThumbnailButton(common_ui.ClickableIconButton):
    """Button used to select the thumbnail."""

    def __init__(self, size, description=u'', parent=None):
        super(ThumbnailButton, self).__init__(
            u'pick_thumbnail',
            (common.FAVOURITE, common.SECONDARY_BACKGROUND),
            size,
            description=description,
            parent=parent
        )
        self.thumbnail = QtGui.QImage()

        tip = u'Right-click to add a thumbnail...'
        self.setToolTip(tip)
        self.setStatusTip(tip)

        self.doubleClicked.connect(self.pick_thumbnail)
        self.clicked.connect(self.capture)

    def contextMenuEvent(self, event):
        menu = ThumbnailContextMenu(parent=self)
        pos = self.rect().center()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def state(self):
        return True

    def reset_thumbnail(self):
        self.thumbnail = QtGui.QImage()
        self.update()

    def pixmap(self):
        if self.thumbnail.isNull():
            return images.ImageCache.get_rsc_pixmap('placeholder', None, self.rect().height(), opacity=0.2)
        pixmap = QtGui.QPixmap()
        pixmap.convertFromImage(self.thumbnail)
        if pixmap.isNull():
            return super(ThumbnailButton, self).pixmap()
        return pixmap

    @QtCore.Slot()
    def pick_thumbnail(self):
        """Prompt to select an image file."""

        @QtCore.Slot(unicode)
        def process_source(source):
            """Processes and saves the selected source."""
            destination = QtCore.QStandardPaths.writableLocation(
                QtCore.QStandardPaths.GenericDataLocation)
            destination = u'{}/{}/temp/{}.{}'.format(
                destination,
                common.PRODUCT,
                uuid.uuid1(),
                common.THUMBNAIL_FORMAT
            )
            f = QtCore.QFileInfo(destination)
            if not f.dir().exists():
                if not f.dir().mkpath(u'.'):
                    s = u'Could not create temp folder.'
                    log.error(s)
                    common_ui.ErrorBox(u'Capture failed', s).open()
                    raise RuntimeError(s)

            res = images.ImageCache.oiio_make_thumbnail(
                source,
                destination,
                common.THUMBNAIL_IMAGE_SIZE
            )

            s = u'Error converting the thumbnail.'
            if not res:
                log.error(s)
                common_ui.ErrorBox(s, u'').open()
                raise RuntimeError(s)
            image = images.ImageCache.get_image(
                destination,
                common.THUMBNAIL_IMAGE_SIZE,
                force=True
            )
            if not image:
                log.error(s)
                common_ui.ErrorBox(s, u'').open()
                raise RuntimeError(s)

            self.thumbnail = image
            self.update()

        dialog = QtWidgets.QFileDialog(parent=self)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilter(common.get_oiio_namefilters())
        dialog.setFilter(
            QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dialog.setLabelText(
            QtWidgets.QFileDialog.Accept, u'Pick thumbnail')

        dialog.fileSelected.connect(process_source)
        dialog.open()

    @QtCore.Slot()
    def capture(self):
        """Captures a thumbnail and save it as a QImage.

        The capture is kept as `self.thumbnail` and saved to disk then the user
        saves the new file.

        """
        @QtCore.Slot(unicode)
        def process_capture(source):
            images.ImageCache.flush(source)
            image = images.ImageCache.get_image(
                source,
                int(common.THUMBNAIL_IMAGE_SIZE)
            )
            if not image:
                s = u'Error saving capture'
                log.error(s)
                common_ui.ErrorBox(s, u'').open()
                raise RuntimeError(s)

            self.thumbnail = image
            self.update()

        try:
            widget = images.ScreenCapture()
            widget.captureFinished.connect(process_capture)
            widget.open()
        except:
            s = u'Error saving capture'
            log.error(s)
            common_ui.ErroBox(s, u'').open()
            raise

    def paintEvent(self, event):
        painter = QtGui.QPainter()

        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        if hover:
            pen = QtGui.QPen(common.ADD)
        else:
            pen = QtGui.QPen(common.SEPARATOR)

        o = common.INDICATOR_WIDTH()
        pen.setWidth(o * 0.5)
        painter.setPen(pen)
        painter.setBrush(common.SEPARATOR)

        if not hover:
            painter.setOpacity(0.95)

        pixmap = self.pixmap()
        rect = self.rect()

        rect_ = rect.marginsRemoved(QtCore.QMargins(
            o * 0.5, o * 0.5, o * 0.5, o * 0.5))
        painter.drawRoundedRect(rect_, o * 2, o * 2)

        s = float(rect_.height())
        longest_edge = float(max((pixmap.width(), pixmap.height())))
        ratio = s / longest_edge
        w = pixmap.width() * ratio
        h = pixmap.height() * ratio

        _rect = QtCore.QRect(0, 0, int(w), int(h))
        _rect.moveCenter(rect_.center())
        painter.drawPixmap(_rect, pixmap, pixmap.rect())
        painter.end()


class DescriptionEditor(common_ui.LineEdit):
    """Editor widget to input the description of the file."""

    def __init__(self, parent=None):
        super(DescriptionEditor, self).__init__(parent=parent)
        self.setPlaceholderText(u'Description...')

        tip = u'Describe your file here, eg. the changes and revisions of this version'
        self.setToolTip(tip)
        self.setStatusTip(tip)


class NamePrefixWidget(common_ui.LineEdit):
    def __init__(self, parent=None):
        super(NamePrefixWidget, self).__init__(parent=parent)
        self.setReadOnly(True)


class NameModeWidget(QtWidgets.QComboBox):
    """This dropdown menu lets the user select the current mode of the file to
    be saved.

    A mode can be, eg. 'animation' or 'layout', etc. Each mode is associated
    with a relative path. When the folder selection changes the mode will be
    updated automatically via the
    ``SelectFolderView.selectionModel.currentChanged`` signal.

    """

    def __init__(self, parent=None):
        super(NameModeWidget, self).__init__(parent=parent)
        for k in sorted(defaultpaths.SCENE_FOLDERS.keys()):
            v = defaultpaths.SCENE_FOLDERS[k]
            self._append_row(k, v)
        self.insertSeparator(self.count())
        for k in sorted(defaultpaths.EXPORT_FOLDERS.keys()):
            v = defaultpaths.EXPORT_FOLDERS[k]
            self._append_row(k, v)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        self.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.setFrame(False)
        self.setMaxVisibleItems(24)

        self.activated.connect(self.save_selection)

    def _append_row(self, k, v):
        """Appends a new row to the combobox."""
        item = QtGui.QStandardItem()
        item.setData(k.upper(), QtCore.Qt.DisplayRole)
        item.setData(v[u'description'], QtCore.Qt.ToolTipRole)
        item.setData(v[u'value'], QtCore.Qt.StatusTipRole)
        item.setData(QtCore.QSize(
            common.WIDTH(), common.ROW_HEIGHT() * 0.8), QtCore.Qt.SizeHintRole)
        self.view().model().appendRow(item)

    @QtCore.Slot(QtCore.QModelIndex)
    def folder_changed(self, index):
        """Slot called when the folder selection changes.

        The function will try to see if there's an associated mode with the
        selected folder and change the mode accordingly.

        """
        if not index.isValid():
            return

        root_path = index.model().rootPath()
        file_path = index.data(QtWidgets.QFileSystemModel.FilePathRole)
        base_path = file_path.replace(root_path, u'').strip(u'/')
        for n in xrange(self.count()):
            data = self.itemData(n, QtCore.Qt.StatusTipRole)
            if not data:
                continue

            if data.lower() in base_path.lower():
                self.setCurrentIndex(n)
                return

    @QtCore.Slot()
    def save_selection(self, idx):
        """Slot responsible for saving the current selection."""
        item = self.view().model().item(idx)
        settings.local_settings.setValue(
            u'saver/mode', item.data(QtCore.Qt.StatusTipRole))

    @QtCore.Slot()
    def restore_selection(self):
        """Slot responsible for restoring the saved selection."""
        val = settings.local_settings.value(u'saver/mode')
        if not val:
            return
        idx = self.findData(val, role=QtCore.Qt.StatusTipRole)
        if idx == -1:
            return
        self.setCurrentIndex(idx)

    def showEvent(self, event):
        self.restore_selection()


class NameVersionWidget(common_ui.LineEdit):
    """QLineEdit user to edit the file's version number."""

    def __init__(self, parent=None):
        super(NameVersionWidget, self).__init__(parent=parent)
        self.setPlaceholderText(u'Version...')
        self.setText(u'0001')

        regex = QtCore.QRegExp(ur'[0-9]{1,4}')
        validator = QtGui.QRegExpValidator(regex, parent=self)
        self.setValidator(validator)

    @QtCore.Slot()
    def check_version(self):
        """This method checks the files inside the directory returned by
        `get_file_path()` against the currently set version number. The method
        will automatically increment the current version number if needed, eg.
        if a file with a larger version number exists already in the folder.

        """
        file_info = QtCore.QFileInfo(self.window().get_file_path())
        match = common.is_valid_filename(file_info.fileName())
        if not match:
            return

        version = match.group(5).lower()
        prefix = match.group(1) + u'_' + match.group(2)
        prefix = prefix.lower()

        versions = []
        ext = self.window().extension.lower()
        name_prefix = self.window().name_prefix_widget.text().lower()

        for entry in _scandir.scandir(file_info.path()):
            path = entry.path.replace(u'\\', u'/').lower()
            basename = path.split(u'/').pop(-1).lower()

            if not basename.lower().startswith(name_prefix.lower()):
                continue

            # Let's skip the files with a different extension
            if not path.lower().endswith(ext.lower()):
                continue

            # Skipping files that are not versioned appropiately
            if prefix.lower() not in path.lower():
                continue

            _match = common.is_valid_filename(path.lower())
            if not _match:
                continue
            _version = _match.group(5).lower()
            versions.append(int(_version))

        if not versions:
            self.setText(u'0001')
            return

        max_version = max(versions)
        if int(version) <= max_version:
            self.setText(u'{}'.format(max_version + 1).zfill(4))


class NameUserWidget(common_ui.LineEdit):
    """Widget used to input the name of the user."""

    def __init__(self, parent=None):
        super(NameUserWidget, self).__init__(parent=parent)
        self.setPlaceholderText(u'User name...')
        tip = u'Enter your name, eg. "Fernando", or "FH"'
        self.setToolTip(tip)
        self.setStatusTip(tip)

        regex = QtCore.QRegExp(ur'[a-zA-Z]{1,9}')
        validator = QtGui.QRegExpValidator(regex, parent=self)
        self.setValidator(validator)

        self.textChanged.connect(self.save)

    @QtCore.Slot()
    def save(self):
        settings.local_settings.setValue(u'saver/username', self.text())

    def showEvent(self, event):  # pylint: disable=W0613
        val = settings.local_settings.value(u'saver/username')
        if not val:
            return
        self.setText(val)


class NameCustomWidget(common_ui.LineEdit):
    """Widget used to input the name of the user."""

    def __init__(self, parent=None):
        super(NameCustomWidget, self).__init__(parent=parent)
        self.setPlaceholderText(u'Custom filename...')
        tip = u'Enter a custom file-name without the extension, eg. "myCharacter_rig".'
        self.setToolTip(tip)
        self.setStatusTip(tip)

        regex = QtCore.QRegExp(ur'[a-zA-Z0-9_-]+')
        validator = QtGui.QRegExpValidator(regex, parent=self)
        self.setValidator(validator)

        self.textChanged.connect(self.save)

    @QtCore.Slot()
    def shown(self):
        self.setFocus()
        self.selectAll()

    @QtCore.Slot()
    def save(self):
        settings.local_settings.setValue(u'saver/customname', self.text())

    def showEvent(self, event):  # pylint: disable=W0613
        val = settings.local_settings.value(u'saver/customname')
        if not val:
            return
        self.setText(val)


class ToggleCustomNameWidget(QtWidgets.QCheckBox):
    """Simple box to toggle the visibility of the custom name field."""

    def __init__(self, parent=None):
        super(ToggleCustomNameWidget, self).__init__(
            u'Use custom name', parent=parent)
        tip = u'Toggles the custom name display.\nUse it to save files that are not part of the normal pipeline.'
        self.setStatusTip(tip)
        self.setToolTip(tip)

        self.stateChanged.connect(self.save)

    @QtCore.Slot()
    def save(self):
        settings.local_settings.setValue(
            u'saver/togglecustom', self.isChecked())

    def showEvent(self, event):  # pylint: disable=W0613
        val = settings.local_settings.value(u'saver/togglecustom')
        if not val:
            self.toggled.emit(self.isChecked())
            return
        self.setChecked(val)
        self.toggled.emit(self.isChecked())


class FilePathWidget(QtWidgets.QWidget):
    """The widget used to display the currently set file path."""

    def __init__(self, parent=None):
        super(FilePathWidget, self).__init__(parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        self.display_timer = QtCore.QTimer(parent=self)
        self.display_timer.setSingleShot(False)
        self.display_timer.setInterval(200)
        self.display_timer.timeout.connect(self.update_text)
        self._text = u''

        tip = u'Click to reveal the destination folder in the file explorer'
        self.setToolTip(tip)
        self.setStatusTip(tip)

    @QtCore.Slot()
    def update_text(self):
        s = self.window().get_file_path()
        if s != self._text:
            self._text = s
            self.repaint()

    def showEvent(self, event):  # pylint: disable=W0613
        if not self.display_timer.isActive():
            self.display_timer.start()

    def hideEvent(self, event):  # pylint: disable=W0613
        self.display_timer.stop()

    def enterEvent(self, event):  # pylint: disable=W0613
        self.update()

    def leaveEvent(self, event):  # pylint: disable=W0613
        self.update()

    def paintEvent(self, event):  # pylint: disable=W0613
        """FilePathWidget's custom paint event"""
        option = QtWidgets.QStyleOption()
        option.initFrom(self)

        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        file_path = self._text

        if not file_path:
            painter.end()
            return

        o = common.INDICATOR_WIDTH()
        pen = QtGui.QPen(common.ADD)
        pen.setWidth(o * 0.5)
        painter.setPen(pen)
        rect = self.rect().marginsRemoved(
            QtCore.QMargins(o * 0.5, o * 0.5, o * 0.5, o * 0.5))
        painter.drawRoundedRect(rect, o, o)

        rect = self.rect().marginsRemoved(
            QtCore.QMargins(o * 2, o * 2, o * 2, o * 2))
        font, metrics = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())
        file_path = metrics.elidedText(
            file_path.upper(),
            QtCore.Qt.ElideLeft,
            rect.width()
        )

        align = QtCore.Qt.AlignCenter
        color = common.TEXT if hover else common.ADD
        common.draw_aliased_text(painter, font, rect, file_path, align, color)

        painter.end()

    def mousePressEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        file_path = self.window().get_file_path()
        file_info = QtCore.QFileInfo(file_path)

        if file_info.exists():
            common.reveal(file_info.filePath())
            return

        common.reveal(file_info.path())


class AddFileWidget(QtWidgets.QDialog):
    """A modal widget used to save a file.

    Has to be initiated with an **extension** The widget will not perform io
    operations, this has to be implemented in the host DCC.

    Use ``AddFileWidget.get_file_path()`` to retrieve the final file path.

    Example:

        .. code-block:: python

          widget = AddFileWidget()
          if widget.exec_() == QtWidgets.QDialog.Accepted:
              widget.get_file_path()

    """
    widgetMoved = QtCore.Signal(QtCore.QPoint)

    def __init__(self, extension, file=None, parent=None):
        super(AddFileWidget, self).__init__(parent=parent)
        if file is None and not isinstance(extension, (str, unicode)):
            raise ValueError(
                u'Expected <type unicode()> got {}'.format(type(extension)))

        if file is None and not extension:
            raise ValueError(u'Must provide a valid extension')

        if not self.parent():
            common.set_custom_stylesheet(self)

        self.initialize_timer = QtCore.QTimer(parent=self)
        self.initialize_timer.setSingleShot(True)
        self.initialize_timer.setInterval(300)

        self.move_in_progress = False
        self.move_start_position = None
        self.move_start_widget_pos = None

        self._file_path = None
        self._file_to_increment = None
        if file:
            self._file_to_increment = QtCore.QFileInfo(file)
            self.increment_file()
            self._file_path = self._file_to_increment.filePath()
            self._file_extension = self._file_to_increment.suffix()
        else:
            self._file_extension = extension.strip(u'.')

        self.bookmark_widget = None
        self.asset_widget = None
        self.folder_widget = None
        #
        self.thumbnail_widget = None
        self.description_editor_widget = None
        #
        self.name_prefix_widget = None
        self.name_mode_widget = None
        self.name_version_widget = None
        self.name_user_widget = None
        self.name_custom_widget = None
        self.toggle_custom_name_widget = None

        self.setWindowFlags(
            QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self._create_UI()
        self._connect_signals()

    def _create_UI(self):
        self.thumbnail_widget = ThumbnailButton(
            common.ROW_HEIGHT() * 5.0,
            description=u'Add thumbnail...',
            parent=self
        )

        # Bookmarks
        bookmark_view = BookmarksListView(parent=self)
        self.bookmark_widget = SelectButton(
            u'Select bookmark...', bookmark_view, parent=self)

        asset_view = AssetsListView(parent=self)
        self.asset_widget = SelectButton(
            u'Select asset...', asset_view, parent=self)

        # Folder
        folder_view = SelectFolderView(parent=self)
        self.folder_widget = SelectButton(
            u'Select folder...', folder_view, parent=self)

        self.description_editor_widget = DescriptionEditor(parent=self)
        self.name_mode_widget = NameModeWidget(parent=self)
        self.name_prefix_widget = NamePrefixWidget(parent=self)
        self.name_prefix_widget.setFixedWidth(common.MARGIN() * 4.5)
        self.name_user_widget = NameUserWidget(parent=self)
        self.name_user_widget.setFixedWidth(common.MARGIN() * 4.5)
        self.name_version_widget = NameVersionWidget(parent=self)
        self.name_version_widget.setFixedWidth(common.MARGIN() * 2.5)
        self.name_custom_widget = NameCustomWidget(parent=self)
        self.toggle_custom_name_widget = ToggleCustomNameWidget(parent=self)

        self.file_path_widget = FilePathWidget(parent=self)
        self.file_path_widget.setFixedHeight(common.ROW_HEIGHT())

        self.save_button = common_ui.PaintedButton(u'Save', parent=self)
        self.save_button.setFixedWidth(common.MARGIN() * 4.5)
        self.cancel_button = common_ui.PaintedButton(u'Cancel', parent=self)
        self.cancel_button.setFixedWidth(common.MARGIN() * 4.5)

        o = common.MARGIN()
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o * 0.5)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedWidth(common.WIDTH() * 1.5)

        self.layout().addWidget(self.thumbnail_widget)
        self.layout().addSpacing(o)

        mainrow = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(mainrow)
        mainrow.layout().setContentsMargins(0, 0, 0, 0)
        mainrow.layout().setSpacing(o * 0.5)
        self.layout().addWidget(mainrow)

        row = common_ui.add_row(
            None,
            padding=None,
            height=None,
            parent=mainrow,
        )
        row.setAutoFillBackground(True)

        def paintEvent(self, event):  # pylint: disable=W0613
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setBrush(common.SEPARATOR)
            painter.setPen(QtCore.Qt.NoPen)
            rect = self.rect()
            rect.setTop(rect.bottom() - (common.ROW_SEPARATOR() * 2.0))
            painter.drawRect(rect)
            painter.end()

        row.paintEvent = functools.partial(paintEvent, row)
        row.layout().addWidget(self.bookmark_widget, 1)
        row.layout().addWidget(self.asset_widget, 1)
        row.layout().addWidget(self.folder_widget, 1)
        row.layout().addStretch(1)
        row.layout().addWidget(self.toggle_custom_name_widget, 0)

        # We're not going to make any informed decisions when saving a quick
        # increment, hence no need to expose these controls...
        if self._file_to_increment:
            self.thumbnail_widget.hide()
            row.hide()
            self.folder_widget.view().hide()

        row = common_ui.add_row(
            None,
            padding=None,
            height=None,
            parent=mainrow,
        )
        row.layout().addWidget(self.description_editor_widget, 1)
        row.layout().addWidget(self.name_mode_widget)
        row.layout().addWidget(self.name_prefix_widget)
        row.layout().addWidget(self.name_user_widget)
        row.layout().addWidget(self.name_version_widget)
        row.layout().addWidget(self.name_custom_widget, 1)

        # self.name_prefix_widget.setHidden(True)

        if self._file_to_increment:
            row.hide()

        mainrow.layout().addSpacing(o * 0.5)
        row = common_ui.add_row(
            None,
            padding=None,
            height=None,
            parent=mainrow,
        )
        mainrow.layout().addSpacing(o)

        row.layout().addWidget(self.file_path_widget, 1)

        row = common_ui.add_row(
            None,
            padding=None,
            height=None,
            parent=mainrow,
        )
        row.layout().addStretch(1)
        row.layout().addWidget(self.save_button, 0)
        row.layout().addWidget(self.cancel_button, 0)
        mainrow.layout().addSpacing(o)

    def _connect_signals(self):
        """Signals are connected together here."""
        self.bookmark_widget.view().clicked.connect(
            self.bookmark_widget.view().activated)
        self.asset_widget.view().clicked.connect(self.asset_widget.view().activated)

        self.folder_widget.view().doubleClicked.connect(
            self.folder_widget.view().activated)

        self.initialize_timer.timeout.connect(
            self.bookmark_widget.view().model().sourceModel().modelDataResetRequested)

        self.bookmark_widget.view().clicked.connect(
            self.asset_widget.view().model().sourceModel().set_active)
        self.bookmark_widget.view().clicked.connect(
            self.asset_widget.view().model().sourceModel().modelDataResetRequested)

        self.asset_widget.view().selectionModel().currentChanged.connect(
            self.folder_widget.view().set_active)

        # Folder model reset
        self.bookmark_widget.view().model().sourceModel().modelAboutToBeReset.connect(
            self.folder_widget.view().reset_active)
        self.asset_widget.view().model().sourceModel().modelAboutToBeReset.connect(
            self.folder_widget.view().reset_active)

        self.asset_widget.view().model().sourceModel().modelAboutToBeReset.connect(
            self.folder_widget.view().selectionModel().reset)

        self.folder_widget.view().selectionModel().currentChanged.connect(
            self.name_mode_widget.folder_changed)

        # Version label
        self.folder_widget.view().clicked.connect(
            self.name_version_widget.check_version)
        self.folder_widget.view().model().directoryLoaded.connect(
            self.name_version_widget.check_version)

        self.name_mode_widget.activated.connect(
            self.name_version_widget.check_version)
        self.name_mode_widget.activated.connect(
            lambda x: self.folder_widget.view().set_folder(
                self.name_mode_widget.itemData(x, role=QtCore.Qt.StatusTipRole)))

        self.name_prefix_widget.textChanged.connect(
            self.name_version_widget.check_version)
        self.name_user_widget.textChanged.connect(
            self.name_version_widget.check_version)

        # Buttons
        self.cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self.accept)

        t = self.toggle_custom_name_widget
        t.toggled.connect(self.name_mode_widget.setHidden)
        t.toggled.connect(self.name_version_widget.setHidden)
        t.toggled.connect(self.name_user_widget.setHidden)
        t.toggled.connect(lambda x: self.name_custom_widget.setHidden(not x))
        t.toggled.connect(self.name_custom_widget.shown)

        # self.bookmark_widget.view().model().sourceModel().modelReset.connect(
        #     self.set_prefix)

        self.bookmark_widget.view().selectionModel().currentChanged.connect(
            self.set_prefix)
        self.bookmark_widget.view().model().sourceModel().activeChanged.connect(
            self.set_prefix)

    @QtCore.Slot()
    def set_prefix(self, index):
        """Sets the file-prefix based on the given bookmark selection.

        """
        if not index.isValid():
            return
        db = bookmark_db.get_db(
            index.data(common.ParentPathRole)[0],
            index.data(common.ParentPathRole)[1],
            index.data(common.ParentPathRole)[2],
        )
        prefix = db.value(1, u'prefix', table='properties')
        self.name_prefix_widget.setText(prefix)

    def increment_file(self):
        """Increments the version number of the current file."""
        if not self._file_to_increment:
            return

        seq = common.get_sequence(self._file_to_increment.filePath())
        if not seq:
            idx = 1
            _file_info = QtCore.QFileInfo(self._file_to_increment)
            while True:
                path = u'{folder}/{name}_v{idx}.{ext}'.format(
                    folder=self._file_to_increment.path(),
                    name=self._file_to_increment.baseName(),
                    idx=u'{}'.format(idx).zfill(4),
                    ext=self._file_to_increment.suffix()
                )
                _file_info = QtCore.QFileInfo(path)
                if not _file_info.exists():
                    break
                idx += 1
            self._file_to_increment = _file_info
            return

        idx = int(seq.group(2))
        _file_info = QtCore.QFileInfo(self._file_to_increment.filePath())
        while True:
            path = u'{before}{idx}{after}.{ext}'.format(
                before=seq.group(1),
                idx=u'{}'.format(idx).zfill(len(seq.group(2))),
                after=seq.group(3),
                ext=self._file_to_increment.suffix()
            )
            _file_info = QtCore.QFileInfo(path)
            if not _file_info.exists():
                break
            idx += 1
        self._file_to_increment = _file_info

    def filePath(self):
        """The currently set file-path."""
        return self._file_path

    def task_folder(self):
        """The currently set task folder."""
        if self._file_to_increment:
            return None

        if not self.folder_widget.view().selectionModel().hasSelection():
            return None

        root_path = self.folder_widget.view().model().rootPath()
        base_path = self.folder_widget.view().model().filePath(
            self.folder_widget.view().selectionModel().currentIndex()
        )

        task_folder = base_path.replace(root_path, u'').strip(u'/')
        if not task_folder:
            return None

        # We're taking the first subfolder of the root path, this is our
        # task_folder
        task_folder = task_folder.split(u'/').pop(0)
        return task_folder

    @property
    def extension(self):
        return self._file_extension

    def get_file_path(self):
        """The main function to get the file path based on the current selections.

        The file pattern is defined by ``FILE_NAME_PATTERN``. By default, it is
        **{folder}/{prefix}_{asset}_{mode}_{user}_{version}.{ext}**

        """
        if self._file_to_increment:
            return self._file_to_increment.filePath()
        folder = self.folder_widget.view().selectionModel().currentIndex()
        folder = folder.data(
            QtWidgets.QFileSystemModel.FilePathRole) if folder.isValid() else u''

        if self.toggle_custom_name_widget.isChecked():
            self._file_path = u'{folder}/{customname}.{ext}'.format(
                folder=folder,
                customname=self.name_custom_widget.text(),
                ext=self.extension)
            return self._file_path

        asset = self.asset_widget.view().selectionModel().currentIndex()
        # The model might still be loading...
        if asset.data(common.ParentPathRole) is None:
            return None

        asset = asset.data(
            common.ParentPathRole)[-1] if asset.isValid() else u''
        _mode = self.name_mode_widget.currentIndex()
        _mode = self.name_mode_widget.currentData(
            QtCore.Qt.DisplayRole).lower() if _mode != -1 else u''
        _user = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.HomeLocation)
        _user = QtCore.QFileInfo(_user)
        _user = _user.baseName()
        user = self.name_user_widget.text()
        user = user if user else _user
        version = u'{}'.format(self.name_version_widget.text()).zfill(4)
        version = u'v{}'.format(version)

        self._file_path = unicode(defaultpaths.FILE_NAME_PATTERN)
        self._file_path = self._file_path.format(
            folder=folder,
            prefix=self.name_prefix_widget.text().lower(),
            asset=asset.lower(),
            mode=_mode.lower(),
            user=user.lower(),
            version=version.lower(),
            ext=self.extension.lower()
        )
        return self._file_path

    def showEvent(self, event):  # pylint: disable=W0613
        """Custom show event."""
        if not self._file_to_increment:
            self.initialize_timer.start()

    def paintEvent(self, event):  # pylint: disable=W0613
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        pen = QtGui.QPen(common.SEPARATOR)
        pen.setWidthF(common.ROW_SEPARATOR())
        painter.setPen(pen)
        painter.setBrush(common.BACKGROUND)
        rect = self.rect()
        painter.drawRoundedRect(
            rect,
            common.INDICATOR_WIDTH() * 2.0,
            common.INDICATOR_WIDTH() * 2.0
        )
        painter.end()

    def save_thumbnail_and_description(self):
        """Saves the set thumbnail and descriptions. We have verified the
        validity of the selections so there no need to do it again.

        """
        index = self.bookmark_widget.view().selectionModel().currentIndex()
        if not index.isValid():
            return

        file_path = self.get_file_path()
        if not file_path:
            return

        server, job, root = index.data(common.ParentPathRole)[0:3]
        destination = images.get_thumbnail_path(
            server,
            job,
            root,
            file_path
        )

        if not self.thumbnail_widget.thumbnail.isNull():
            res = self.thumbnail_widget.thumbnail.save(
                destination,
                format=u'png',
                quality=100
            )
            if not res:
                s = u'Error saving the thumbnail'
                log.error(s)
                common_ui.ErrorBox(s, u'').open()
                raise RuntimeError(s)

        # Saving the description
        description = self.description_editor_widget.text()
        if description:
            db = bookmark_db.get_db(server, job, root)
            db.setValue(file_path, u'description', description)

    @QtCore.Slot()
    def accept(self):
        """Slot is resposible to verify the user input and file validity.

        Before we can save a file we will try to make sure the file does not
        exist already. If it does, we will try to increment the version number
        and re-run the checks.

        """
        if self._file_to_increment:
            super(AddFileWidget, self).accept()
            return

        # A folder selection is a must
        if not self.asset_widget.view().selectionModel().hasSelection():
            common_ui.MessageBox(
                u'Asset not selected.',
                u'Select an asset from the dropdown menu and try again.',
            ).open()
            return
        # A folder selection is a must
        if not self.asset_widget.view().selectionModel().currentIndex():
            common_ui.MessageBox(
                u'Asset not selected.',
                u'Select an asset from the dropdown menu and try again.',
            ).open()
            return

        # A folder selection is a must
        if not self.folder_widget.view().selectionModel().hasSelection():
            common_ui.MessageBox(
                u'Destination folder not set.',
                u'Select a folder from the dropdown menu and try again.',
            ).open()
            return

        index = self.folder_widget.view().selectionModel().currentIndex()
        if not index.isValid():
            common_ui.MessageBox(
                u'Destination folder not selected.',
                u'Select a folder from the dropdown menu and try again.',
            ).open()
            return
        if index.column() != 0:
            index = index.sibling(index.row(), 0)

        # Let's check if the folder exists and is writable...
        path = self.folder_widget.view().model().filePath(index)
        file_info = QtCore.QFileInfo(path)
        _file_info = QtCore.QFileInfo(file_info.path())

        if not _file_info.exists():
            common_ui.MessageBox(
                u'The destination folder does not exist.',
                u'Select another folder from the dropdown menu and try again.',
            ).open()
            return

        if not _file_info.isWritable():
            common_ui.MessageBox(
                u'The destination folder is not writable.',
                u'Select another folder from the dropdown menu and try again.',
            ).open()
            return

        # Let's make sure we have filled all the required fields
        if self.toggle_custom_name_widget.isChecked():
            if not self.name_custom_widget.text():
                common_ui.MessageBox(
                    u'Enter a name and try again.',
                    u'',
                ).open()
                return

        if not self.toggle_custom_name_widget.isChecked():
            if not self.name_prefix_widget.text():
                # We need to have a valid bookmark prefix to save a filename
                # We can bring the editor up
                common_ui.MessageBox(
                    u'The bookmark\'s file prefix is not configured',
                    u'Enter a prefix and try again.',
                ).exec_()

                import bookmarks.bookmark_properties as bookmark_properties

                model = self.bookmark_widget.view().model().sourceModel()
                index = model.active_index()
                if not index.isValid():
                    return

                bookmark_properties.BookmarkPropertiesWidget(
                    index.data(common.ParentPathRole)[0],
                    index.data(common.ParentPathRole)[1],
                    index.data(common.ParentPathRole)[2],
                ).exec_()
                self.set_prefix(index)
                return

        # We should be good to go, but have to make sure we're not overwriting
        # an existing file first...
        file_path = self.get_file_path()
        file_info = QtCore.QFileInfo(file_path)

        if file_info.exists() and not self.toggle_custom_name_widget.isChecked():
            match = common.is_valid_filename(file_path)
            if not match:
                return
            version = match.group(5)

            # Warning the user here that there's a version conflict
            version = u'{}'.format(version).zfill(4)
            version = u'v{}'.format(version)

            mbox = QtWidgets.QMessageBox(parent=self)
            mbox.setWindowTitle(u'Couldn\'t save file')
            mbox.setIcon(QtWidgets.QMessageBox.Warning)
            mbox.setText(u'A file named "{}" exists already!'.format(
                file_info.fileName()))
            mbox.setInformativeText(
                u'Do you want to increment version "{}"?'.format(version))
            button = mbox.addButton(
                u'Increment and save', QtWidgets.QMessageBox.AcceptRole)
            mbox.addButton(u'Cancel', QtWidgets.QMessageBox.RejectRole)
            mbox.setDefaultButton(button)

            res = mbox.exec_()
            if res == QtWidgets.QMessageBox.RejectRole:
                return

            # Let's increment the number
            self.name_version_widget.check_version()

            # And notify the user of the changes
            # FOr this we have to querry the filename again...
            file_path = self.get_file_path()

            match = common.is_valid_filename(file_path)
            if not match:
                return
            new_version = u'v' + match.group(5)

            mbox = QtWidgets.QMessageBox(parent=self)
            mbox.setWindowTitle(u'Version changed')
            mbox.setIcon(QtWidgets.QMessageBox.Warning)
            mbox.setText(u'Version incremented from "{}" to "{}"'.format(
                version, new_version))
            mbox.open()
            self.accept()

        if file_info.exists() and self.toggle_custom_name_widget.isChecked():
            self.message_box(
                u'A file named "{}" exists already!'.format(file_info.fileName()))
            self.name_custom_widget.setFocus()
            self.name_custom_widget.selectAll()
            return

        self.save_thumbnail_and_description()

        super(AddFileWidget, self).accept()

    def mouseReleaseEvent(self, event):
        self.move_in_progress = False
        self.move_start_position = None
        self.move_start_widget_pos = None

    def mousePressEvent(self, event):
        """Custom ``movePressEvent``.
        We're setting the properties needed to moving the main window.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.move_in_progress = True
        self.move_start_position = common.cursor.pos()
        self.move_start_widget_pos = self.geometry().topLeft()

    def mouseMoveEvent(self, event):
        """Moves the the parent window when clicked.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.buttons() == QtCore.Qt.NoButton:
            return
        if not self.move_start_widget_pos:
            return

        pos = common.cursor.pos()
        offset = self.move_start_position - pos
        self.move(self.move_start_widget_pos - offset)
        self.widgetMoved.emit(self.geometry().topLeft())
