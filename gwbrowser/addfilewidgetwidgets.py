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
import gwbrowser.editors as editors
from gwbrowser.common_ui import ClickableLabel, add_row
from gwbrowser.bookmarkswidget import BookmarksModel
from gwbrowser.assetswidget import AssetModel

from gwbrowser.delegate import BaseDelegate
from gwbrowser.delegate import paintmethod
from gwbrowser.delegate import AssetsWidgetDelegate
from gwbrowser.delegate import BookmarksWidgetDelegate

from gwbrowser.basecontextmenu import BaseContextMenu, contextmenu
from gwbrowser.baselistwidget import BaseInlineIconWidget

from gwbrowser.capture import ScreenGrabber
from gwbrowser.imagecache import ImageCache
from gwbrowser.imagecache import ImageCacheWorker


POPDOWN_HEIGHT = 480.0


class SelectButton(QtWidgets.QLabel):
    """A clickable text label with a view widget attached.
    Used to pick the bookmark, asset and subfolders when using the saver.

    Signals:
        activeChanged (QModelIndex): Notifies other components of a selection-change.

    """
    activeChanged = QtCore.Signal(QtCore.QModelIndex)
    clicked = QtCore.Signal()
    widgetMoved = QtCore.Signal(QtCore.QRect)

    Context_menu_cls = None

    def __init__(self, label, view, parent=None):
        super(SelectButton, self).__init__(parent=parent)
        self._view = view

        common.set_custom_stylesheet(self)
        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setText(label)
        self.setFocusProxy(self.view())

        self._connectSignals()

    def select_active(self):
        active_index = self.view().model().sourceModel().active_index()
        if not active_index.isValid():
            return

        proxy_index = self.view().model().mapFromSource(active_index)
        self.activated(proxy_index)
        self.view().scrollTo(proxy_index, QtWidgets.QAbstractItemView.PositionAtCenter)
        self.view().selectionModel().setCurrentIndex(proxy_index, QtCore.QItemSelectionModel.ClearAndSelect)
        self.repaint()

    def _connectSignals(self):
        self.clicked.connect(self.show_view)
        self.widgetMoved.connect(self.move_view)
        self.view().activated.connect(self.activated)

        if hasattr(self.view().model(), 'sourceModel'):
            self.view().activated.connect(
                lambda x: self.activeChanged.emit(self.view().model().mapToSource(x)))
            self.view().model().sourceModel().modelReset.connect(self.select_active)

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
            self.view().scrollTo(self.view().selectionModel().currentIndex(), QtWidgets.QAbstractItemView.PositionAtCenter)

        self.view().show()
        self.view().raise_()
        self.view().setFocus()

    @QtCore.Slot(QtCore.QModelIndex)
    def activated(self, index):
        if not index.isValid():
            return
        if index.flags() == QtCore.Qt.NoItemFlags:
            return

        self.setText(index.data(QtCore.Qt.DisplayRole))
        self.repaint()

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
        width = metrics.width(self.text())
        self.setFixedWidth(width + (common.MARGIN * 2))
        self.repaint()

    def paintEvent(self, event):
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
            self.text(), QtCore.Qt.AlignCenter, color)

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

    def showEvent(self, event):
        self.view().hide()

    def resizeEvent(self, event):
        self.widgetMoved.emit(self.rect())

    def moveEvent(self, event):
        self.widgetMoved.emit(self.rect())


class SelectBookmarkDelegate(BookmarksWidgetDelegate):
    """The delegate used to paint the bookmark items."""

    def paint(self, painter, option, index):
        """Defines how the BookmarksWidgetItems should be painted."""
        args = self._get_paint_args(painter, option, index)
        self.paint_background(*args)
        #
        self.paint_thumbnail(*args)
        self.paint_archived(*args)
        #
        self.paint_name(*args)
        #
        self.paint_count_icon(*args)
        #
        self.paint_selection_indicator(*args)

    def sizeHint(self, option, index):
        return QtCore.QSize(common.WIDTH, common.BOOKMARK_ROW_HEIGHT)


class SelectAssetDelegate(AssetsWidgetDelegate):
    """Delegate used by the ``AssetsWidget`` to display the collecteds assets."""

    def paint(self, painter, option, index):
        """Defines how the ``AssetsWidget``'s' items should be painted."""
        args = self._get_paint_args(painter, option, index)
        self.paint_background(*args)
        #
        self.paint_thumbnail(*args)
        self.paint_archived(*args)
        #
        self.paint_thumbnail_shadow(*args)
        self.paint_name(*args)
        #
        self.paint_description(*args)
        #
        self.paint_selection_indicator(*args)

    def sizeHint(self, option, index):
        return QtCore.QSize(common.WIDTH, common.ASSET_ROW_HEIGHT)


class SelectListView(BaseInlineIconWidget):

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

        self._connectSignals()

    def _connectSignals(self):
        self.selectionModel().currentChanged.connect(self.hide)
        self.selectionModel().currentChanged.connect(self.activated)

    def showEvent(self, event):
        self.adjust_height()
        if self.selectionModel().hasSelection():
            self.scrollTo(self.selectionModel().currentIndex())

    @QtCore.Slot()
    def adjust_height(self, *args, **kwargs):
        """Adjusts the size of the view to fit the contents exactly."""
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


class SelectFolderModel(QtWidgets.QFileSystemModel):
    """"""

    def __init__(self, parent=None):
        super(SelectFolderModel, self).__init__(parent=parent)
        self.setNameFilterDisables(True)

    def flags(self, index):
        """The flag values are stored in the model as a separate role."""
        if self.isDir(index):
            return super(SelectFolderModel, self).flags(index)
        return QtCore.Qt.NoItemFlags


class SelectFolderView(QtWidgets.QTreeView):
    activeChanged = QtCore.Slot(tuple)

    def __init__(self, model, parent=None):
        super(SelectFolderView, self).__init__(parent=parent)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setModel(model)
        model.setParent(self)
        self._connectSignals()

    def _connectSignals(self):
        self.model().directoryLoaded.connect(self.restore_previous_selection)
        self.model().directoryLoaded.connect(self.resize_columns)
        self.model().directoryLoaded.connect(self.adjust_height)

        self.expanded.connect(self.resize_columns)
        self.expanded.connect(self.adjust_height)
        self.collapsed.connect(self.resize_columns)
        self.collapsed.connect(self.adjust_height)

        self.activated.connect(self.hide)
        self.activated.connect(self.active_changed)

    @QtCore.Slot(QtCore.QModelIndex)
    def active_changed(self, index):
        """The slot called when an active item has changed. It will save the
        selection to the local preferences for safe-keeping.

        The slot is connected to the view's ``activated`` signal.

        """
        if not index.isValid():
            return
        if index.flags() == QtCore.Qt.NoItemFlags:
            return

        folder_root_path = self.model().filePath(self.rootIndex())
        folder_filepath = self.model().filePath(index)
        folder_basepath = folder_filepath.replace(folder_root_path, u'').strip(u'/')

        local_settings.setValue(u'saver/folder_filepath', folder_filepath)
        local_settings.setValue(u'saver/folder_basepath', folder_basepath)
        local_settings.setValue(u'saver/folder_rootpath', folder_root_path)

        import sys
        sys.stderr.write('# Saved: {}\n'.format(folder_basepath))

    @QtCore.Slot()
    def restore_previous_selection(self):
        """After each root path change we will try to reapply the previous user
        selections.

        """
        if self._initialized:
            return

        # folder_filepath = local_settings.setValue(u'saver/folder_filepath')
        folder_basepath = local_settings.value(u'saver/folder_basepath')
        # folder_root_path = local_settings.setValue(u'saver/folder_rootpath')

        if not folder_basepath:
            self._initialized = True
            return

        # Check if path is part of the current selection
        path = u'{}/{}'.format(self.model().rootPath(), folder_basepath)
        index = self.model().index(path)
        if not index.isValid():
            self._initialized = True
            return

        self.selectionModel().setCurrentIndex(index, QtCore.QItemSelectionModel.ClearAndSelect)
        self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
        self.activated.emit(index)

        import sys
        sys.stderr.write(u'Restored: {}\n'.format(path))

        self._initalized = True

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
        """Adjusts the size of the QTreeView to fit the contents exactly."""
        height = 0

        option = QtWidgets.QStyleOptionViewItem()
        option.initFrom(self)

        index = self.rootIndex()
        while True:
            index = self.indexBelow(index)
            if not index.isValid():
                break
            height += self.itemDelegate().sizeHint(option, index).height()
            if height > POPDOWN_HEIGHT:
                break
        if height == 0:
            self.hide()
            return
        self.setFixedHeight(height)

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
        index = self.model().index(self.model().rootPath())
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
            index = index.siblingAtColumn(0)

        self.activated.emit(index)


class SelectFolderContextMenu(BaseContextMenu):
    """Context menu associated with the thumbnail."""

    def __init__(self, parent=None):
        super(SelectFolderContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_reveal_item_menu()

    @contextmenu
    def add_reveal_item_menu(self, menu_set):
        """Menu for thumbnail operations."""
        asset = self.parent().view().model().asset()
        if asset.isValid():
            asset_path = asset.data(common.ParentRole)
            asset_path = u'/'.join(asset_path)
            menu_set[u'Reveal asset'] = {
                u'action': functools.partial(common.reveal, asset_path)
            }
            destination = self.parent().view().model().destination()
            if destination:
                menu_set[u'Reveal destination'] = {
                    u'action': functools.partial(common.reveal, destination)
                }
        return menu_set


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
        super(ThumbnailButton, self).__init__(u'pick_thumbnail', common.FAVOURITE, size, description=description, parent=parent)
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
            u'pick_thumbnail', common.FAVOURITE, common.ROW_HEIGHT)
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
        self.name_asset_widget = None
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

    def _createUI(self):
        # Bookmarks
        bookmark_model = BookmarksModel()
        bookmark_delegate = SelectBookmarkDelegate()
        bookmark_view = SelectListView(bookmark_model, bookmark_delegate)
        self.bookmark_widget = SelectButton(u'Select bookmark...', bookmark_view)

        # Assets
        asset_model = AssetModel()
        asset_delegate = SelectAssetDelegate()
        asset_view = SelectListView(asset_model, asset_delegate)
        self.asset_widget = SelectButton(u'Select asset...', asset_view)

        folder_model = SelectFolderModel()
        folder_view = SelectFolderView(folder_model)
        self.folder_widget = SelectButton(u'Select folder...', folder_view)

        # Connecting the bookmarks model and asset models
        bookmark_view.selectionModel().currentChanged.connect(asset_model.set_active)
        bookmark_view.selectionModel().currentChanged.connect(asset_view.model().sourceModel().modelDataResetRequested)
        asset_view.selectionModel().currentChanged.connect(folder_view.set_active)

        o = common.MARGIN * 2
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(4)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedWidth(common.WIDTH * 1.5)

        row = add_row(u'', parent=self, height=common.ROW_HEIGHT, padding=0)

        self.thumbnail_widget = ThumbnailButton(common.ROW_HEIGHT, description=u'Add thumbnail...', parent=self)
        row.layout().addWidget(self.thumbnail_widget, 0)

        self.description_editor_widget = DescriptionEditor(parent=self)
        row.layout().addWidget(self.description_editor_widget, 1)

        row.layout().addWidget(self.bookmark_widget, 0)
        row.layout().addWidget(self.asset_widget, 0)
        row.layout().addWidget(self.folder_widget, 0)


        row = add_row(u'Edit file name:', parent=self, height=common.ROW_HEIGHT * 0.8, padding=0)
        self.name_prefix_widget = NamePrefixWidget(parent=self)
        self.name_asset_widget = NameAssetWidget(parent=self)
        self.name_mode_widget = NameModeWidget(parent=self)
        self.name_version_widget = NameVersionWidget(parent=self)
        self.name_user_widget = NameUserWidget(parent=self)

        row.layout().addStretch(1)
        row.layout().addWidget(self.name_prefix_widget)
        row.layout().addWidget(self.name_asset_widget)
        row.layout().addWidget(self.name_mode_widget)
        row.layout().addWidget(self.name_user_widget)
        row.layout().addWidget(self.name_version_widget)

        self.layout().addSpacing(common.ROW_HEIGHT)

        row = add_row(u'Filename:', parent=self, height=common.ROW_HEIGHT, padding=0)
        self.file_path_widget = FilePathWidget(parent=self)
        row.layout().addWidget(self.file_path_widget)

    def _connectSignals(self):
        self.initialize_timer.timeout.connect(self.bookmark_widget.view().model().sourceModel().modelDataResetRequested)

    def showEvent(self, event):
        pass
        # self.initialize_timer.start()


class NameBase(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super(NameBase, self).__init__(parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

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
        self.setPlaceholderText(u'Enter description...')
        self.set_transparent()
        self.setFixedHeight(36)


class NamePrefixWidget(NameBase):
    def __init__(self, parent=None):
        super(NamePrefixWidget, self).__init__(parent=parent)
        self.setPlaceholderText(u'Enter file prefix...')
        self.set_transparent()


class NameAssetWidget(NameBase):
    def __init__(self, parent=None):
        super(NameAssetWidget, self).__init__(parent=parent)
        self.setPlaceholderText(u'Asset')
        self.setReadOnly(True)
        self.set_transparent()


class NameModeWidget(QtWidgets.QComboBox):
    modes = (
        u'anim',
        u'fx',
        u'ifds',
        u'layout',
        u'light',
        u'track',
        u'lookdev',
        u'model',
        u'rd',
        u'rig',
        u'sculpt',
    )
    def __init__(self, parent=None):
        super(NameModeWidget, self).__init__(parent=parent)
        for s in sorted(self.modes):
            self.addItem(s.upper())
        self.set_transparent()
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
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


class NameVersionWidget(NameBase):
    def __init__(self, parent=None):
        super(NameVersionWidget, self).__init__(parent=parent)
        self.setPlaceholderText(u'Enter version number...')
        self.setReadOnly(True)
        self.setText(u'v0001')
        self.set_transparent()


class NameUserWidget(NameBase):
    def __init__(self, parent=None):
        super(NameUserWidget, self).__init__(parent=parent)
        self.setPlaceholderText(u'Enter user name...')
        self.set_transparent()


class FilePathWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(FilePathWidget, self).__init__(parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        font = common.PrimaryFont
        rect = self.rect()
        text = 'test'

        text = '{folder}/{prefix}_{asset}_{mode}_{user}_{version}.{ext}'
        align = QtCore.Qt.AlignRight
        color = common.TEXT
        common.draw_aliased_text(painter, font, rect, text, align, color)
        painter.end()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = AddFileWidget()
    widget.show()
    app.exec_()
