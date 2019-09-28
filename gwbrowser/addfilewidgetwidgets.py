# -*- coding: utf-8 -*-
"""This modules contains all the elements needed to select a folder from inside
the current task folder.

"""

import re
import uuid
import functools
from PySide2 import QtCore, QtWidgets, QtGui

from gwbrowser.settings import local_settings
import gwbrowser.common as common
import gwbrowser.gwscandir as gwscandir
import gwbrowser.editors as editors
from gwbrowser.common_ui import ClickableLabel, add_row, PaintedButton, PaintedLabel
from gwbrowser.bookmarkswidget import BookmarksModel
from gwbrowser.assetswidget import AssetModel

from gwbrowser.delegate import AssetsWidgetDelegate
from gwbrowser.delegate import BookmarksWidgetDelegate

from gwbrowser.basecontextmenu import BaseContextMenu, contextmenu
from gwbrowser.baselistwidget import BaseInlineIconWidget

from gwbrowser.capture import ScreenGrabber
from gwbrowser.imagecache import ImageCache
from gwbrowser.imagecache import ImageCacheWorker


POPDOWN_HEIGHT = 480.0
SCENE_FILE_MODES = {
    u'anim': {
        'path': u'scenes/animation',
        'description': u'Animation scene files'
    },
    u'fx': {
        'path': u'scenes/fx',
        'description': u'Effect and simulation, eg. Houdini scene files'
    },
    u'ifds': {
        'path': u'scenes/ifds',
        'description': u''
    },
    u'layout': {
        'path': u'scenes/layout',
        'description': u'Animation layout, animatic and blocking scene files'
    },
    u'light': {
        'path': u'scenes/lighting',
        'description': u'Lighting scenes'
    },
    u'track': {
        'path': u'scenes/tracking',
        'description': u'Motion tracking scenes'
    },
    u'lookdev': {
        'path': u'scenes/look_dev',
        'description': u'Visual development scenes'
    },
    u'model': {
        'path': u'scenes/model',
        'description': u'Scenes for unrigged models and meshes'
    },
    u'rd': {
        'path': u'scenes/r_d',
        'description': u'Research and development scenes'
    },
    u'rig': {
        'path': u'scenes/rig',
        'description': u'Animation rig files'
    },
    u'render': {
        'path': u'scenes/rig',
        'description': u'Render files'
    },
    u'sculpt': {
        'path': u'scenes/sculpt',
        'description': u'Animation layout, animatic and blocking scene files'
    },
}

EXPORT_FILE_MODES = {
    u'abc': {
        'path': u'export/abc',
        'description': u'Animation layout, animatic and blocking scene files'
    },
    u'obj': {
        'path': u'export/obj',
        'description': u'Animation layout, animatic and blocking scene files'
    },
    u'fbx': {
        'path': u'export/fbx',
        'description': u'Animation layout, animatic and blocking scene files'
    },
}

FILE_NAME_PATTERN = u'{folder}/{prefix}_{asset}_{mode}_{user}_{version}.{ext}'

user_and_version_regex = re.compile(r'(.*)\_([a-zA-Z0-9]+)\_v([0-9]{1,4})\..+$')


def get_user_and_version(path):
    match = user_and_version_regex.search(path)
    if not match:
        return
    return match.groups()


class SelectButton(QtWidgets.QLabel):
    """A clickable text label with a view widget attached.
    Used to pick the bookmark, asset and subfolders when using the saver.

    """
    clicked = QtCore.Signal()
    widgetMoved = QtCore.Signal(QtCore.QRect)

    Context_menu_cls = None

    def __init__(self, label, view, parent=None):
        super(SelectButton, self).__init__(parent=parent)
        self._view = view
        self._label = label
        self.update_timer = QtCore.QTimer(parent=self)
        self.update_timer.setSingleShot(False)
        self.update_timer.setInterval(200)

        common.set_custom_stylesheet(self)

        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setText(self._label)
        self.setFocusProxy(self.view())
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

        self._connectSignals()

    def _connectSignals(self):
        self.clicked.connect(self.show_view)
        self.widgetMoved.connect(self.move_view)
        if hasattr(self.view().model(), u'sourceModel'):
            # We will temporarily block the selection model's signals whilst
            # the source model is loading. This is to prevent it from emiting
            # changed signals as the model is being populated.
            self.view().model().sourceModel().modelAboutToBeReset.connect(
                lambda: self.view().blockSignals(True))
            self.view().model().sourceModel().modelReset.connect(
                lambda: self.view().blockSignals(False))
            self.view().model().sourceModel().modelReset.connect(self.select_active)

        self.update_timer.timeout.connect(self.update_text)

    @QtCore.Slot()
    def update_text(self):
        if not self.view().selectionModel().hasSelection():
            return
        text = self.view().selectionModel().currentIndex().data(QtCore.Qt.DisplayRole)
        self.setText(text)
        self.repaint()

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
        self.repaint()

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
        self.view().move(
            self.window().geometry().bottomLeft().x(),
            self.window().geometry().bottomLeft().y())

    def show_view(self):
        """Shows the view associated with this custom button."""
        if not self.view():
            return
        if self.view().isVisible():
            self.view().hide()
            return

        self.view().setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Window)

        self.move_view()
        self.view().setFixedWidth(self.window().geometry().width())

        if self.view().selectionModel().hasSelection():
            self.view().scrollTo(self.view().selectionModel().currentIndex(),
                                 QtWidgets.QAbstractItemView.PositionAtCenter)

        self.view().show()
        self.view().raise_()
        self.view().setFocus()

    @QtCore.Slot(QtCore.QModelIndex)
    def destinationChanged(self, index):
        if not index.isValid():
            self.setText(u'Select destination folder...')
            return

        data = self.view().model().fileName(index)
        self.setText(data.upper())

    @QtCore.Slot(unicode)
    def setText(self, text):
        super(SelectButton, self).setText(text)
        metrics = QtGui.QFontMetrics(common.PrimaryFont)
        width = metrics.width(self.text().upper())
        self.setFixedWidth(width + common.MARGIN)
        self.repaint()

    def paintEvent(self, event):
        """``SelectButton``'s custom paint event to show the current view
        selection.

        """
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        color = common.FAVOURITE if hover else common.TEXT

        if self.has_selection():
            color = QtGui.QColor(30, 200, 120)

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        common.draw_aliased_text(
            painter, common.PrimaryFont, self.rect(),
            self.text().upper(), QtCore.Qt.AlignCenter, color)

        rect = QtCore.QRect(self.rect())
        rect.setTop(rect.bottom() - 1)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 1, 1)
        painter.end()

    def contextMenuEvent(self, event):
        if not self.Context_menu_cls:
            return

        w = self.Context_menu_cls(parent=self)
        pos = self.rect().bottomLeft()
        pos = self.mapToGlobal(pos)
        w.move(pos)

        common.move_widget_to_available_geo(w)

        widget.exec_()

    def enterEvent(self, event):
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.button() == QtCore.Qt.LeftButton:
            pos = QtGui.QCursor().pos()
            pos = self.mapFromGlobal(pos)
            if self.rect().contains(pos):
                self.clicked.emit()

    def hideEvent(self, event):
        self.view().hide()
        self.update_timer.stop()

    def showEvent(self, event):
        self.view().hide()
        self.update_timer.start()

    def resizeEvent(self, event):
        self.widgetMoved.emit(self.rect())

    def moveEvent(self, event):
        self.widgetMoved.emit(self.rect())


class SelectListView(BaseInlineIconWidget):
    """The base class used to view the ``BookmarksModel`` and ``AssetModel``
    models. The class is an control icon-less version of the
    ``BaseInlineIconWidget`` widget.

    The ``activated`` signal will hide the view but the activated signal itself
    is **not** connected in this class.

    """

    def __init__(self, model, delegate, parent=None):
        super(SelectListView, self).__init__(parent=parent)
        self.set_model(model)
        delegate.setParent(self)
        self.setItemDelegate(delegate)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, False)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground, False)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.removeEventFilter(self)

        self.activated.connect(self.hide)

    def showEvent(self, event):
        self.adjust_height()
        if self.selectionModel().hasSelection():
            self.scrollTo(self.selectionModel().currentIndex())

    @QtCore.Slot()
    def adjust_height(self, *args, **kwargs):
        """Adjusts the height of the ``SelectListView`` to it's contents."""
        height = 0

        option = QtWidgets.QStyleOptionViewItem()
        option.initFrom(self)

        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0)
            if not index.isValid():
                break
            height += self.itemDelegate().sizeHint(option, index).height()
            if height > POPDOWN_HEIGHT:
                break
        if height == 0:
            self.hide()
            return
        self.setFixedHeight(height)

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.hide()

    def mouseDoubleClickEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.activate(self.selectionModel().currentIndex())

    def inline_icons_count(self):
        return 0


class SelectFolderModelIconProvider(QtWidgets.QFileIconProvider):

    def icon(self, file_info):
        file_info.isDir()
        if file_info.isDir():
            pixmap = ImageCache.get_rsc_pixmap(
                u'folder', common.SEPARATOR, 256)
        else:
            pixmap = ImageCache.get_rsc_pixmap(u'files', common.SEPARATOR, 256)

        return QtGui.QIcon(pixmap)


class SelectFolderModel(QtWidgets.QFileSystemModel):
    """"""

    def __init__(self, parent=None):
        super(SelectFolderModel, self).__init__(parent=parent)
        self.setNameFilterDisables(True)
        self.setIconProvider(SelectFolderModelIconProvider(parent=self))

    def flags(self, index):
        """The flag values are stored in the model as a separate role."""
        if self.isDir(index):
            return super(SelectFolderModel, self).flags(index)
        return QtCore.Qt.NoItemFlags

    def columnCount(self, parent=QtCore.QModelIndex):
        """Adding an extra column to assign a description to the folder."""
        return 6

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """We're matching the folder-name with our description."""
        if index.column() == 5:
            if role == QtCore.Qt.DisplayRole:
                if self.isDir(index):
                    sibling = index.sibling(index.row(), 0)
                    k = self.fileName(sibling).lower()
                    if k in common.ASSET_FOLDERS:
                        return common.ASSET_FOLDERS[k]
        if role == QtCore.Qt.DisplayRole:
            data = super(SelectFolderModel, self).data(index, role=role)
            if data:
                if index.parent() == self.index(self.rootPath()):
                    return data.upper()
        return super(SelectFolderModel, self).data(index, role=role)


class SelectFolderView(QtWidgets.QTreeView):
    """A QTreeView widget to display our QFileSystemModel. The widget is used
    to select the destination folder of our new file.

    The folder selection will be saved to the local settings and reapplied,
    when the widget is shown.

    """

    def __init__(self, model, parent=None):
        super(SelectFolderView, self).__init__(parent=parent)
        self._initialized = False
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setUniformRowHeights(True)
        self.setModel(model)
        model.setParent(self)

        for n in xrange(4):
            self.hideColumn(n + 1)

        self._connectSignals()

    def _connectSignals(self):
        self.model().directoryLoaded.connect(self.restore_previous_selection)
        self.model().directoryLoaded.connect(self.resize_columns)
        self.model().directoryLoaded.connect(self.adjust_height)

        self.expanded.connect(self.resize_columns)
        self.expanded.connect(self.adjust_height)
        self.collapsed.connect(self.resize_columns)
        self.collapsed.connect(self.adjust_height)

        self.selectionModel().currentChanged.connect(self.active_changed)
        self.activated.connect(self.hide)

    @QtCore.Slot(QtCore.QModelIndex)
    def active_changed(self, index):
        """The slot called when the current item has changed. It will save the
        selection to the local preferences for safe-keeping.

        The slot is connected to the view.selectionModel's ``currentChanged`` signal.

        """
        if not index.isValid():
            return
        if index.flags() == QtCore.Qt.NoItemFlags:
            return

        folder_root_path = self.model().filePath(self.rootIndex())
        folder_filepath = self.model().filePath(index)
        folder_basepath = folder_filepath.replace(
            folder_root_path, u'').strip(u'/')

        local_settings.setValue(u'saver/folder_filepath', folder_filepath)
        local_settings.setValue(u'saver/folder_basepath', folder_basepath)
        local_settings.setValue(u'saver/folder_rootpath', folder_root_path)

    @QtCore.Slot()
    def restore_previous_selection(self):
        """After each root path change we will try to reapply the previous user
        selections.

        """
        if self._initialized:
            return

        folder_basepath = local_settings.value(u'saver/folder_basepath')

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

        import sys
        sys.stderr.write(u'Restored: {}\n'.format(path))

        self._initialized = True

    @QtCore.Slot(unicode)
    def resize_columns(self):
        for n in xrange(self.model().columnCount()):
            self.resizeColumnToContents(n)

    def showEvent(self, event):
        self.adjust_height()
        if self.selectionModel().hasSelection():
            self.scrollTo(self.selectionModel().currentIndex())

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
        if height > POPDOWN_HEIGHT:
            height = POPDOWN_HEIGHT
        self.setFixedHeight(height)

    @QtCore.Slot(QtCore.QModelIndex)
    def set_active(self, index):
        """Slot connected to the activeChanged signal."""
        if not index.isValid():
            self.model().setRootPath(u'.')
            self.setRootIndex(QtCore.QModelIndex())
            return

        if index.flags() == QtCore.Qt.NoItemFlags:
            self.model().setRootPath(u'.')
            self.setRootIndex(QtCore.QModelIndex())
            return

        path = index.data(QtCore.Qt.StatusTipRole)
        if not path:
            self.model().setRootPath(u'.')
            self.setRootIndex(QtCore.QModelIndex())
            return

        self.model().setRootPath(path)
        index = self.model().index(path)
        self.setRootIndex(index)

        self._initialized = False

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.hide()

    def mouseDoubleClickEvent(self, event):
        """Remapping the index to be always column one. Also, will ignore event
        for disabled items.

        """
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
        if index.flags() == QtCore.Qt.NoItemFlags:
            return
        if index.column() != 0:
            return
        super(SelectFolderView, self).mouseDoubleClickEvent(event)


class ThumbnailContextMenu(BaseContextMenu):
    """Context menu associated with the thumbnail."""

    def __init__(self, parent=None):
        super(ThumbnailContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_thumbnail_menu()

    @contextmenu
    def add_thumbnail_menu(self, menu_set):
        """Menu for thumbnail operations."""
        capture_thumbnail_pixmap = ImageCache.get_rsc_pixmap(
            u'capture_thumbnail', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        pick_thumbnail_pixmap = ImageCache.get_rsc_pixmap(
            u'pick_thumbnail', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        remove_thumbnail_pixmap = ImageCache.get_rsc_pixmap(
            u'remove', common.FAVOURITE, common.INLINE_ICON_SIZE)

        menu_set[u'Capture thumbnail'] = {
            u'icon': capture_thumbnail_pixmap,
            u'action': self.parent().capture_thumbnail
        }
        menu_set['Add from library...'] = {
            u'text': 'Add from library...',
            u'icon': pick_thumbnail_pixmap,
            u'action': self.parent().show_thumbnail_picker
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


class ThumbnailButton(ClickableLabel):
    """Button used to select the thumbnail for this item."""

    def __init__(self, size, description=u'', parent=None):
        super(ThumbnailButton, self).__init__(u'pick_thumbnail',
                                              common.FAVOURITE, size, description=description, parent=parent)
        self.reset_thumbnail()
        self.image = QtGui.QImage()

    def contextMenuEvent(self, event):
        menu = ThumbnailContextMenu(parent=self)
        pos = self.rect().center()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def isEnabled(self):
        return True

    def reset_thumbnail(self):
        pixmap = ImageCache.get_rsc_pixmap(
            u'pick_thumbnail', common.FAVOURITE, self.height())
        self.setStyleSheet(
            u'background-color: rgba({});'.format(common.rgb(common.BACKGROUND)))

        self._pixmap = pixmap
        self.image = QtGui.QImage()

    def show_thumbnail_picker(self):
        """Shows the dialog used to select a thumbnail from the library."""

        @QtCore.Slot(unicode)
        def _add_thumbnail_from_library(path):
            image = QtGui.QImage()
            if not image.load(path):
                return

            self.image = image
            self.update_thumbnail_preview()

        rect = QtWidgets.QApplication.instance().desktop().screenGeometry(self)
        widget = editors.ThumbnailsWidget(parent=self.parent())
        widget.thumbnailSelected.connect(_add_thumbnail_from_library)
        widget.show()
        widget.setFocus(QtCore.Qt.PopupFocusReason)

        wpos = QtCore.QPoint(widget.width() / 2.0, widget.height() / 2.0)
        widget.move(rect.center() - wpos)
        common.move_widget_to_available_geo(widget)

    def pick_thumbnail(self):
        """Prompt to select an image file."""
        dialog = QtWidgets.QFileDialog(parent=self)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilter(common.get_oiio_namefilters())

        # Setting the dialog's root path
        dialog.setOption(
            QtWidgets.QFileDialog.DontUseCustomDirectoryIcons, True)

        if not dialog.exec_():
            return
        if not dialog.selectedFiles():
            return

        temp_path = u'{}/browser_temp_thumbnail_{}.png'.format(
            QtCore.QDir.tempPath(), uuid.uuid1())

        ImageCacheWorker.process_index(
            QtCore.QModelIndex(),
            source=next(f for f in dialog.selectedFiles()),
            dest=temp_path
        )

        image = QtGui.QImage()
        image.load(temp_path)
        if image.isNull():
            return

        self.image = image
        self.update_thumbnail_preview()

    def capture_thumbnail(self):
        """Captures a thumbnail."""
        pixmap = ScreenGrabber.capture()

        if not pixmap:
            return
        if pixmap.isNull():
            return

        image = ImageCache.resize_image(
            pixmap.toImage(), common.THUMBNAIL_IMAGE_SIZE)
        self.image = image
        self.update_thumbnail_preview()

    def update_thumbnail_preview(self):
        """Sets the label's pixmap to the currently set thumbnail image."""
        if not self.image:
            return
        if self.image.isNull():
            return

        # Resizing for display
        image = ImageCache.resize_image(
            self.image, self.height())

        pixmap = QtGui.QPixmap()
        pixmap.convertFromImage(image)
        background = ImageCache.get_color_average(image)

        self._pixmap = pixmap
        self.setStyleSheet(
            'QLabel {{background-color: rgba({});}}'.format(
                common.rgb(background)))


class AddFileWidget(QtWidgets.QDialog):
    """The dialog used to save a file. It contains the header and the saver widgets
    needed to select the desired path.

    When ``done()`` is called, the widget will emit the ``fileSaveRequested``,
    ``fileDescriptionAdded`` and ``fileThumbnailAdded`` signals.

    """

    # Signals
    fileSaveRequested = QtCore.Signal(basestring)
    fileDescriptionAdded = QtCore.Signal(tuple)
    fileThumbnailAdded = QtCore.Signal(tuple)

    def __init__(self, extension=u'txt', file=None, parent=None):
        super(AddFileWidget, self).__init__(parent=parent)
        self.initialize_timer = QtCore.QTimer(parent=self)
        self.initialize_timer.setSingleShot(True)
        self.initialize_timer.setInterval(500)

        self._file_extension = extension
        self._file_increment = file

        self.thumbnail_widget = None
        self.description_editor_widget = None
        self.bookmark_widget = None
        self.asset_widget = None
        self.folder_widget = None
        #
        self.name_prefix_widget = None
        self.name_mode_widget = None
        self.name_version_widget = None
        self.name_user_widget = None

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(
            QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self._createUI()
        self._connectSignals()

    @property
    def extension(self):
        return self._file_extension

    def file(self):
        return self._file_increment

    def get_file_path(self):
        """The main function to get the file path based on the current user
        selections.

        The file pattern is defined by ``FILE_NAME_PATTERN``. By default, it is
        **{folder}/{prefix}_{asset}_{mode}_{user}_{version}.{ext}**

        """
        folder = self.folder_widget.view().selectionModel().currentIndex()
        folder = folder.data(
            QtWidgets.QFileSystemModel.FilePathRole) if folder.isValid() else u''
        asset = self.asset_widget.view().selectionModel().currentIndex()
        asset = asset.data(QtCore.Qt.DisplayRole) if asset.isValid() else u''
        mode = self.name_mode_widget.currentIndex()
        mode = self.name_mode_widget.currentData(
            QtCore.Qt.DisplayRole).lower() if mode != -1 else u''
        _user = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.HomeLocation)
        _user = QtCore.QFileInfo(_user)
        _user = _user.baseName()
        user = self.name_user_widget.text()
        user = user if user else _user
        version = u'{}'.format(self.name_version_widget.text()).zfill(4)
        version = u'v{}'.format(version)

        file_path = unicode(FILE_NAME_PATTERN)
        file_path = file_path.format(
            folder=folder,
            prefix=self.name_prefix_widget.text().lower(),
            asset=asset,
            mode=mode,
            user=user,
            version=version,
            ext=self.extension.lower()
        )

        return file_path

    def _createUI(self):
        # Bookmarks
        bookmark_model = BookmarksModel()
        bookmark_delegate = BookmarksWidgetDelegate()
        bookmark_view = SelectListView(bookmark_model, bookmark_delegate)
        self.bookmark_widget = SelectButton(
            u'Select bookmark...', bookmark_view, parent=self)

        # Assets
        asset_model = AssetModel()
        asset_delegate = AssetsWidgetDelegate()
        asset_view = SelectListView(asset_model, asset_delegate)
        self.asset_widget = SelectButton(
            u'Select asset...', asset_view, parent=self)

        # Folder
        folder_model = SelectFolderModel()
        folder_view = SelectFolderView(folder_model)
        self.folder_widget = SelectButton(
            u'Select folder...', folder_view, parent=self)

        o = common.MARGIN * 1
        common.set_custom_stylesheet(self)
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedWidth(common.WIDTH * 1.5)

        self.thumbnail_widget = ThumbnailButton(
            100, description=u'Add thumbnail...', parent=self)
        self.layout().addWidget(self.thumbnail_widget)
        self.layout().addSpacing(o)

        mainrow = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(mainrow)
        mainrow.layout().setContentsMargins(0, 0, 0, 0)
        mainrow.layout().setSpacing(common.INDICATOR_WIDTH)
        self.layout().addWidget(mainrow)

        row = add_row(u'', parent=mainrow, height=common.ROW_HEIGHT,
                      padding=0, cls=None)

        row.layout().addWidget(self.bookmark_widget, 1)
        row.layout().addWidget(self.asset_widget, 1)
        row.layout().addWidget(self.folder_widget, 1)
        row.layout().addStretch(1)

        row = add_row(
            u'',
            parent=mainrow,
            height=common.ROW_HEIGHT * 0.8,
            padding=0
        )
        self.description_editor_widget = DescriptionEditor(parent=self)
        self.name_mode_widget = NameModeWidget(parent=self)
        self.name_prefix_widget = NamePrefixWidget(parent=self)
        self.name_prefix_widget.setFixedWidth(64)
        self.name_user_widget = NameUserWidget(parent=self)
        self.name_user_widget.setFixedWidth(64)
        self.name_version_widget = NameVersionWidget(parent=self)
        self.name_version_widget.setFixedWidth(48)
        self.save_button = PaintedButton(u'Save')
        self.save_button.setFixedWidth(86)
        self.cancel_button = PaintedButton(u'Cancel')
        self.cancel_button.setFixedWidth(86)

        row.layout().addWidget(self.description_editor_widget, 1)
        row.layout().addWidget(self.name_mode_widget)
        row.layout().addWidget(self.name_prefix_widget)
        row.layout().addWidget(self.name_user_widget)
        row.layout().addWidget(self.name_version_widget)
        row.layout().addSpacing(common.MARGIN)
        row.layout().addWidget(self.save_button)
        row.layout().addWidget(self.cancel_button)

        row = add_row(u'', parent=mainrow, height=common.ROW_BUTTONS_HEIGHT,
                      padding=0, cls=None)
        self.file_path_widget = FilePathWidget(parent=self)
        row.layout().addWidget(PaintedLabel(u'New file\'s path:', size=common.SMALL_FONT_SIZE, color=common.SECONDARY_TEXT))
        row.layout().addWidget(self.file_path_widget)

    def _connectSignals(self):
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
        self.asset_widget.view().model().sourceModel().modelAboutToBeReset.connect(
            lambda: self.folder_widget.view().set_active(QtCore.QModelIndex())
        )

        self.folder_widget.view().selectionModel().currentChanged.connect(
            self.name_mode_widget.folder_changed)

        # Version label
        self.folder_widget.view().model().directoryLoaded.connect(self.name_version_widget.check_version)

    def showEvent(self, event):
        """Custom show event."""
        self.initialize_timer.start()


class NameBase(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super(NameBase, self).__init__(parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        self.setAlignment(QtCore.Qt.AlignLeft)

    def set_transparent(self):
        self.setStyleSheet(
            """
QLineEdit{{
    background-color: rgba(0,0,0,0);
    font-family: "{font}";
    font-size: {fontSize}pt;
    border-bottom: 2px solid rgba(0,0,0,50);
    border-radius: 0px;
    color: white;
}}
QLineEdit:!read-only:focus{{
    border-bottom: 2px solid rgba({favourite});
}}
            """.format(
                font=common.PrimaryFont.family(),
                fontSize=common.psize(common.MEDIUM_FONT_SIZE),
                favourite=common.rgb(common.FAVOURITE)
            )
        )


class DescriptionEditor(NameBase):
    """Editor widget to input the description of the file."""

    def __init__(self, parent=None):
        super(DescriptionEditor, self).__init__(parent=parent)
        self.setPlaceholderText(u'Description...')
        self.set_transparent()


class NamePrefixWidget(NameBase):
    def __init__(self, parent=None):
        super(NamePrefixWidget, self).__init__(parent=parent)
        self.setPlaceholderText(u'Prefix...')
        self.set_transparent()
        self.textChanged.connect(self.save)

        regex = QtCore.QRegExp(ur'[a-zA-Z0-9]{25}')
        validator = QtGui.QRegExpValidator(regex, parent=self)
        self.setValidator(validator)

    @QtCore.Slot()
    def save(self):
        local_settings.setValue(u'saver/prefix', self.text())

    def showEvent(self, event):
        val = local_settings.value(u'saver/prefix')
        if not val:
            return
        self.setText(val)


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
        for k in sorted(SCENE_FILE_MODES.keys()):
            v = SCENE_FILE_MODES[k]
            self._append_row(k, v)
        self.insertSeparator(self.count())
        for k in sorted(EXPORT_FILE_MODES.keys()):
            v = EXPORT_FILE_MODES[k]
            self._append_row(k, v)

        self.set_transparent()
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
        item.setData(v[u'path'], QtCore.Qt.StatusTipRole)
        item.setData(QtCore.QSize(
            common.WIDTH, common.ROW_BUTTONS_HEIGHT * 0.8), QtCore.Qt.SizeHintRole)
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

            if base_path.lower() == data.lower():
                self.setCurrentIndex(n)
                return

    @QtCore.Slot()
    def save_selection(self, idx):
        """Slot responsible for saving the current selection."""
        item = self.view().model().item(idx)
        local_settings.setValue(
            u'saver/mode', item.data(QtCore.Qt.StatusTipRole))

    @QtCore.Slot()
    def restore_selection(self):
        """Slot responsible for restoring the saved selection."""
        val = local_settings.value(u'saver/mode')
        if not val:
            return
        idx = self.findData(val, role=QtCore.Qt.StatusTipRole)
        if idx == -1:
            return
        self.setCurrentIndex(idx)

    def set_transparent(self):
        self.setStyleSheet(
            """
QComboBox{{
    background-color: rgba(0,0,0,0);
    font-family: "{font}";
    font-size: {fontSize}pt;
    border-bottom: 2px solid rgba(0,0,0,50);
    border-radius: 0px;
    color: white;
}}
QComboBox:focus{{
    border-bottom: 2px solid rgba({favourite});
}}
            """.format(
                font=common.PrimaryFont.family(),
                fontSize=common.psize(common.MEDIUM_FONT_SIZE),
                favourite=common.rgb(common.FAVOURITE)
            )
        )

    def showEvent(self, event):
        self.restore_selection()


class NameVersionWidget(NameBase):
    """QLineEdit user to edit the file's version number."""

    def __init__(self, parent=None):
        super(NameVersionWidget, self).__init__(parent=parent)
        self.setPlaceholderText(u'Version...')
        self.setText(u'0001')
        self.set_transparent()

        regex = QtCore.QRegExp(ur'[0-9]{1,4}')
        validator = QtGui.QRegExpValidator(regex, parent=self)
        self.setValidator(validator)

    @QtCore.Slot()
    def check_version(self):
        """Checks the currently set version against the folders in the
        set destination folder. If our set version is lower than any of the
        existing files, """
        file_info = QtCore.QFileInfo(self.window().get_file_path())
        v = get_user_and_version(file_info.fileName())
        if not v:
            return
        prefix, _, version = v

        versions = []
        for entry in gwscandir.scandir(file_info.path()):
            path = entry.path.replace(u'\\', u'/')
            if prefix not in path:
                continue
            _v = get_user_and_version(path)
            if not _v:
                continue
            _, _, _version = _v
            versions.append(int(_version))

        if not versions:
            self.setText(u'0001')
            return

        max_version = max(versions)
        if int(version) <= max_version:
            self.setText(u'{}'.format(max_version + 1).zfill(4))





class NameUserWidget(NameBase):
    """Widget used to input the name of the user."""

    def __init__(self, parent=None):
        super(NameUserWidget, self).__init__(parent=parent)
        self.setPlaceholderText(u'User name...')
        self.set_transparent()

        regex = QtCore.QRegExp(ur'[a-zA-Z]{1,9}')
        validator = QtGui.QRegExpValidator(regex, parent=self)
        self.setValidator(validator)

        self.textChanged.connect(self.save)

    @QtCore.Slot()
    def save(self):
        local_settings.setValue(u'saver/username', self.text())

    def showEvent(self, event):
        val = local_settings.value(u'saver/username')
        if not val:
            return
        self.setText(val)


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
        self.display_timer.setInterval(300)
        self.display_timer.timeout.connect(self.repaint)

    def showEvent(self, event):
        self.display_timer.start()

    def hideEvent(self, event):
        self.display_timer.stop()

    def enterEvent(self, event):
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        color = QtGui.QColor(
            255, 255, 255, 50) if hover else QtGui.QColor(0, 0, 0, 20)

        painter = QtGui.QPainter()
        painter.begin(self)
        font = common.SecondaryFont

        rect = self.rect()
        center = self.rect().center()
        rect.setHeight(rect.height() - common.MARGIN)
        rect.setWidth(rect.width() - common.MARGIN)
        rect.moveCenter(center)

        root_path = self.window().folder_widget.view().model().rootPath()
        file_path = self.window().get_file_path()
        # file_path = file_path.replace(root_path, u'...')
        align = QtCore.Qt.AlignLeft
        color = common.TEXT_SELECTED if hover else common.TEXT
        common.draw_aliased_text(painter, font, rect, file_path, align, color)
        painter.end()

    def mousePressEvent(self, event):
        file_path = self.window().get_file_path()
        _dir = QtCore.QFileInfo(file_path)
        common.reveal(_dir.path())

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    # model = SelectFolderModel()
    widget = AddFileWidget()
    # widget = SelectFolderView(model)
    widget.show()
    app.exec_()
