# -*- coding: utf-8 -*-
"""**addbookmarkswidget.py** defines ``AddBookmarksWidget`` and the supplemetary
widgets needed to select a **server**, **job** and **root** folder.

These three choices together (saved as a tuple) make up a **bookmark**. The
final path will, unsurprisingly, be a composite of the above, like so:
*server/job/root*. Eg.: **//network_server/my_job/shots.**

The actual bookmarks are stored, on Windows, in the *Registry* and are unique to
each users.

"""

from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser.gwscandir as gwscandir
import gwbrowser.common as common
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.delegate import BaseDelegate
from gwbrowser.delegate import paintmethod
from gwbrowser.settings import local_settings
from gwbrowser.common_ui import PaintedButton, PaintedLabel, ClickableIconButton, add_row


custom_string = u'Select a custom bookmark folder...'


class ComboboxContextMenu(BaseContextMenu):
    """Small context menu to reveal the current choice in the explorer."""

    def __init__(self, index, parent=None):
        super(ComboboxContextMenu, self).__init__(index, parent=parent)
        self.add_reveal_item_menu()  # pylint: disable=E1120


class ComboboxButton(QtWidgets.QPushButton):
    """Custom button uised for selecting a server, job or root folder."""

    def __init__(self, itemtype, description=u'', parent=None):
        super(ComboboxButton, self).__init__(parent=parent)
        self.type = itemtype
        self.context_menu_cls = ComboboxContextMenu
        self._view = ListWidget(parent=self)

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setStatusTip(description)
        self.setToolTip(description)
        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT * 0.8)

        self.pressed.connect(self.show_view)

    @QtCore.Slot()
    def show_view(self):
        """Shows the list view."""
        if not self._view.model().rowCount():
            return
        x = self.parent().rect().topLeft()
        x = self.parent().mapToGlobal(x)

        pos = self.rect().bottomLeft()
        pos = self.mapToGlobal(pos)

        self._view.move(pos)
        self._view.setFixedWidth(self.width())
        self._view.setFocus(QtCore.Qt.PopupFocusReason)
        self._view.show()

        model = self._view.selectionModel()
        index = model.currentIndex()
        if not index.isValid():
            return
        self._view.scrollTo(
            index, QtWidgets.QAbstractItemView.PositionAtCenter)

    def view(self):
        """The view associated with the widget."""
        return self._view

    def contextMenuEvent(self, event):
        """Custom context menu event for the combobox widget."""
        index = self.view().item(self.view().currentRow())
        if not index:
            return
        if index.data(QtCore.Qt.DisplayRole) == custom_string:
            return

        widget = self.context_menu_cls(index, parent=self)

        rect = self.rect()
        widget.move(
            self.mapToGlobal(rect.bottomLeft()).x(),
            self.mapToGlobal(rect.bottomLeft()).y(),
        )

        common.move_widget_to_available_geo(widget)
        widget.exec_()

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()

    def paintEvent(self, event):
        """The ``ComboboxButton``'s paint event."""
        if event.rect() != self.rect():
            return

        # Disabled
        disabled = False
        if self.type == u'job':
            m = self.parent().parent().pick_server_widget.view().selectionModel()
            if not m.hasSelection():
                disabled = True
        if self.type == u'bookmark':
            m = self.parent().parent().pick_job_widget.view().selectionModel()
            if not m.hasSelection():
                disabled = True

        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        index = self.view().selectionModel().currentIndex()
        if not self.view().selectionModel().hasSelection():
            text = u'Select a {}...'.format(self.type)
            color = common.TEXT
        else:
            text = index.data(QtCore.Qt.DisplayRole)
            text = text.upper() if text else u'Select {}'.format(self.type)
            color = common.TEXT_SELECTED
        color = common.SECONDARY_TEXT if disabled else color

        if text.lower() == custom_string.lower():
            text = custom_string

        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(255, 255, 255, 10))
        painter.drawRoundedRect(self.rect(), 3, 3)

        rect = QtCore.QRect(self.rect())
        if hover and not disabled or self.view().isVisible():
            color = common.TEXT_SELECTED
            if self.view().isVisible():
                painter.setBrush(common.SECONDARY_BACKGROUND)
            else:
                painter.setBrush(QtGui.QColor(255, 255, 255, 30))

            painter.setPen(QtCore.Qt.NoPen)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            painter.drawRoundedRect(self.rect(), 3, 3)

        center = rect.center()
        rect.setWidth(rect.width() - common.MARGIN)
        rect.moveCenter(center)

        if self.view().isVisible():
            text = u'...'
        common.draw_aliased_text(
            painter,
            common.PrimaryFont,
            rect,
            text,
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            color
        )

        painter.end()

    @QtCore.Slot(int)
    def pick_custom(self, index):
        """Method to select a the root folder of the assets. Called by the Assets push button."""
        if not index.isValid():
            return
        if not index.row() == 0:
            return

        parent = self.parent().parent()
        index = parent.pick_server_widget.view().selectionModel().currentIndex()
        server = index.data(QtCore.Qt.StatusTipRole)

        m = parent.pick_job_widget.view().selectionModel()
        index = parent.pick_job_widget.view().selectionModel().currentIndex()
        if not m.hasSelection():
            return
        if not index.isValid():
            return
        job = index.data(QtCore.Qt.DisplayRole)

        if not all((server, job)):
            return

        path = u'{}/{}'.format(server, job)
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            return

        dialog = QtWidgets.QFileDialog()
        dialog.setViewMode(QtWidgets.QFileDialog.Detail)
        res = dialog.getExistingDirectory(
            self,
            u'Pick a folder to bookmark',
            file_info.filePath(),
            QtWidgets.QFileDialog.ShowDirsOnly |
            QtWidgets.QFileDialog.DontResolveSymlinks |
            QtWidgets.QFileDialog.DontUseCustomDirectoryIcons |
            QtWidgets.QFileDialog.HideNameFilterDetails |
            QtWidgets.QFileDialog.ReadOnly
        )

        # Didn't make a valid selection
        if not res:
            return

        if path.lower() not in res.lower():
            return

        index = self.view().model().index(0, 0)

        root = res.lower().replace(path.lower(), u'').strip(u'/')
        self.view().model().setData(
            index,
            root,
            role=QtCore.Qt.DisplayRole)

        self.view().model().setData(
            index,
            res,
            role=QtCore.Qt.StatusTipRole)

        parent.validate()


class ListWidgetDelegate(BaseDelegate):
    """Delegate render the items of ``ListWidget`` instances."""

    def paint(self, painter, option, index):
        """The main paint method."""
        if index.data(QtCore.Qt.DisplayRole) != custom_string:
            self.paint_background(index, painter, option)
        self.paint_name(index, painter, option)

    @paintmethod
    def paint_background(self, index, painter, option):
        rect = QtCore.QRect(option.rect)
        selected = option.state & QtWidgets.QStyle.State_Selected

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.SECONDARY_BACKGROUND)
        painter.drawRect(option.rect)

        if selected:
            painter.setBrush(common.BACKGROUND_SELECTED)
        else:
            painter.setBrush(common.BACKGROUND)

        if index.flags() == QtCore.Qt.NoItemFlags:
            painter.setBrush(common.SEPARATOR)

        painter.drawRect(rect)

    @paintmethod
    def paint_name(self, index, painter, option):
        """Paints the DisplayRole of the items."""
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        disabled = index.flags() == QtCore.Qt.NoItemFlags

        rect = QtCore.QRect(option.rect)
        center = rect.center()
        rect.setWidth(rect.width() - common.MARGIN)
        rect.moveCenter(center)

        color = common.TEXT_SELECTED if hover else common.TEXT
        color = common.SECONDARY_TEXT if disabled else color

        text = index.data(QtCore.Qt.DisplayRole)
        if text == custom_string and self.parent().model().rowCount() > 1:
            _rect = QtCore.QRect(option.rect)
            _rect.setTop(_rect.bottom() - 1)
            painter.setBrush(common.SEPARATOR)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRect(_rect)

        if text != custom_string:
            text = text.upper()

        width = common.draw_aliased_text(
            painter,
            common.PrimaryFont,
            rect,
            text,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            color
        )
        if index.data(common.DescriptionRole):
            rect.setLeft(rect.left() + width + common.INDICATOR_WIDTH)
            width = common.draw_aliased_text(
                painter,
                common.SecondaryFont,
                rect,
                u': {}'.format(index.data(common.DescriptionRole)),
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
                common.SECONDARY_TEXT
            )

    def sizeHint(self, option, index):
        """Returns the size of the combobox items."""
        return QtCore.QSize(
            self.parent().width(), common.ROW_HEIGHT * 0.66)


class ListWidget(QtWidgets.QListWidget):
    """The widget used to present a simple list of items to choose."""

    def __init__(self, parent=None):
        super(ListWidget, self).__init__(parent=parent)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)
        self.setItemDelegate(ListWidgetDelegate(self))
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setWindowFlags(
            QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.itemClicked.connect(self.hide)
        self.itemActivated.connect(self.hide)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            event.accept()
            self.hide()
            return
        super(ListWidget, self).keyPressEvent(event)

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.hide()

    def showEvent(self, event):
        sizehint = self.itemDelegate().sizeHint(
            self.viewOptions(), QtCore.QModelIndex())

        height = 0
        for n in xrange(self.model().rowCount()):
            if n > 10:
                break
            height += sizehint.height()
        self.setFixedHeight(height)

        self.parent().update()

    def hideEvent(self, event):
        self.parent().update()


class AddJobButton(ClickableIconButton):
    """The button responsible for showing the ``AddJobWidget``."""

    def __init__(self, parent=None):
        super(AddJobButton, self).__init__(
            u'add_folder',
            (common.TEXT, common.SECONDARY_TEXT),
            common.ROW_BUTTONS_HEIGHT * 0.66,
            description=u'Click to add a new job to the server',
        )

class RefreshButton(ClickableIconButton):
    """The button responsible for showing the ``AddJobWidget``."""

    def __init__(self, parent=None):
        super(RefreshButton, self).__init__(
            u'refresh',
            (common.TEXT, common.SECONDARY_TEXT),
            common.ROW_BUTTONS_HEIGHT * 0.66,
            description=u'Click to refresh',
        )

    def state(self):
        """The state of the button will disabled if no server has been selected."""
        return True

    @QtCore.Slot()
    def action(self):
        """Slot connected to the clicked signal."""
        self.parent().parent().initialize()


class AddBookmarksWidget(QtWidgets.QDialog):
    """Defines the widget used add a bookmark.

    A bookmark is made up of the *server*, *job* and *root* folders.
    All sub-widgets needed to make the choices are laid-out in this
    widget.

    """

    def __init__(self, parent=None):
        super(AddBookmarksWidget, self).__init__(parent=parent)
        self.new_key = None

        self.setWindowTitle(u'Add bookmark')
        self.installEventFilter(self)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Window)

        self._createUI()
        self._connectSignals()

    def initialize(self):
        """Populates the comboboxes and selects the currently active items (if there's any)."""
        self.pick_server_widget.view().selectionModel().blockSignals(True)
        self.pick_job_widget.view().selectionModel().blockSignals(True)
        self.pick_root_widget.view().selectionModel().blockSignals(True)

        self.pick_server_widget.view().selectionModel().setCurrentIndex(
            QtCore.QModelIndex(), QtCore.QItemSelectionModel.Clear)
        self.pick_job_widget.view().selectionModel().setCurrentIndex(
            QtCore.QModelIndex(), QtCore.QItemSelectionModel.Clear)
        self.pick_root_widget.view().selectionModel().setCurrentIndex(
            QtCore.QModelIndex(), QtCore.QItemSelectionModel.Clear)

        self.add_servers_from_config()

        # Restoring previous setting
        val = local_settings.value(u'widget/AddBookmarksWidget/server')
        if val:
            for idx in xrange(self.pick_server_widget.view().count()):
                item = self.pick_server_widget.view().item(idx)
                if item.data(QtCore.Qt.DisplayRole).lower() == val.lower():
                    self.pick_server_widget.view().setCurrentItem(item)
                    break

        self.add_jobs_from_server_folder(
            self.pick_server_widget.view().selectionModel().currentIndex())

        # Restoring previous setting
        val = local_settings.value(u'widget/AddBookmarksWidget/job')
        if val:
            for idx in xrange(self.pick_job_widget.view().count()):
                item = self.pick_job_widget.view().item(idx)
                if item.data(QtCore.Qt.DisplayRole).lower() == val.lower():
                    self.pick_job_widget.view().setCurrentItem(item)
                    break

        self.add_root_folders(
            self.pick_job_widget.view().selectionModel().currentIndex())

        self.pick_server_widget.view().selectionModel().blockSignals(False)
        self.pick_job_widget.view().selectionModel().blockSignals(False)
        self.pick_root_widget.view().selectionModel().blockSignals(False)

        self.validate()

    def _createUI(self):
        """Creates the AddBookmarksWidget's ui and layout."""
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(common.INDICATOR_WIDTH)

        label = PaintedLabel(u'Add new bookmark', size=common.LARGE_FONT_SIZE)
        self.layout().addWidget(label, 0)

        self.layout().addSpacing(common.MARGIN)

        # Server
        row = add_row(u'Select server', parent=self)
        description = u'Click to select the server your job is located on.\nThis should in most cases be the primary server ({}),\nhowever, it is possible to work locally on the local SSD drive by selecting "jobs-local".'.format(
            common.Server.primary())
        self.pick_server_widget = ComboboxButton(
            u'server', description=description, parent=self)
        row.layout().addWidget(self.pick_server_widget, 1)
        self.refresh_button = RefreshButton(parent=self)
        row.layout().addWidget(self.refresh_button, 0)

        # Job
        row = add_row(u'Select job', parent=self)
        description = u'Click to select the job.\nEach job contains multiple locations to keep files and folders, referred to as a "bookmark".\n\nEg. the "data/shots" and "data/assets" folders.'
        self.pick_job_widget = ComboboxButton(
            u'job', description=description, parent=self)
        row.layout().addWidget(self.pick_job_widget, 1)
        self.add_job_widget = AddJobButton(parent=self)
        row.layout().addWidget(self.add_job_widget, 0)

        # Bookmarks folder
        row = add_row(u'Select bookmark', parent=self)
        description = u'Select the bookmark folder.'
        self.pick_root_widget = ComboboxButton(
            u'bookmark', description=description, parent=self)
        row.layout().addWidget(self.pick_root_widget, 1)

        self.layout().addSpacing(common.MARGIN)
        self.layout().addStretch(1)

        row = add_row('', parent=self)

        self.ok_button = PaintedButton(u'Add bookmark')
        row.layout().addWidget(self.ok_button, 1)

    def _connectSignals(self):
        self.pick_server_widget.view().itemClicked.connect(
            self.add_jobs_from_server_folder)
        self.pick_server_widget.view().itemActivated.connect(
            self.add_jobs_from_server_folder)
        self.pick_server_widget.view().itemClicked.connect(
            self.pick_server_widget.update)
        self.pick_server_widget.view().itemActivated.connect(
            self.pick_server_widget.update)

        self.pick_server_widget.view().itemClicked.connect(
            self.add_jobs_from_server_folder)
        self.pick_server_widget.view().itemActivated.connect(
            self.add_jobs_from_server_folder)

        self.pick_server_widget.view().itemClicked.connect(
            lambda x: self.add_root_folders(
                self.pick_job_widget.view().selectionModel().currentIndex()))
        self.pick_server_widget.view().itemActivated.connect(
            lambda x: self.add_root_folders(
                self.pick_job_widget.view().selectionModel().currentIndex()))

        self.pick_job_widget.view().itemClicked.connect(
            lambda x: self.add_root_folders(
                self.pick_job_widget.view().selectionModel().currentIndex()))
        self.pick_job_widget.view().itemActivated.connect(
            lambda x: self.add_root_folders(
                self.pick_job_widget.view().selectionModel().currentIndex()))

        self.pick_server_widget.view().itemClicked.connect(self.validate)
        self.pick_server_widget.view().itemActivated.connect(self.validate)
        self.pick_job_widget.view().itemClicked.connect(self.validate)
        self.pick_job_widget.view().itemActivated.connect(self.validate)
        self.pick_root_widget.view().itemClicked.connect(self.validate)
        self.pick_root_widget.view().itemActivated.connect(self.validate)

        self.pick_root_widget.view().itemClicked.connect(
            lambda x: self.pick_root_widget.pick_custom(self.pick_root_widget.view().selectionModel().currentIndex()))
        self.pick_root_widget.view().itemActivated.connect(
            lambda x: self.pick_root_widget.pick_custom(self.pick_root_widget.view().selectionModel().currentIndex()))

        self.pick_server_widget.view().selectionModel().currentChanged.connect(
            lambda x: local_settings.setValue(
                u'widget/AddBookmarksWidget/server', x.data(QtCore.Qt.DisplayRole))
        )
        self.pick_job_widget.view().selectionModel().currentChanged.connect(
            lambda x: local_settings.setValue(
                u'widget/AddBookmarksWidget/job', x.data(QtCore.Qt.DisplayRole))
        )
        self.pick_root_widget.view().selectionModel().currentChanged.connect(
            lambda x: local_settings.setValue(
                u'widget/AddBookmarksWidget/root', x.data(QtCore.Qt.DisplayRole))
        )

        self.ok_button.pressed.connect(self.add_bookmark)

    def _updateGeometry(self, *args, **kwargs):
        pos = self.parent().mapToGlobal(self.parent().rect().topLeft())
        self.move(pos)
        self.resize(self.parent().rect().size())

    def get_root_folder_items(self, path, depth=4, count=0, arr=None):
        """Scans the given path recursively and returns all root-folder candidates.
        The recursion-depth is limited by the `depth` property.

        Args:
            depth (int): The number of subfolders to scan.

        Returns:
            A list of ``QFileInfo`` items.

        """
        path = path.replace(u'\\', u'/')
        if depth == count:
            return arr

        if [f for f in arr if path in f]:
            return arr
        try:
            for entry in gwscandir.scandir(path):
                if not entry.is_dir():
                    continue
                if entry.name.startswith(u'.'):
                    continue

                identifier_path = u'{}/{}'.format(
                    entry.path.replace(u'\\', u'/'),
                    common.ASSET_IDENTIFIER)

                if QtCore.QFileInfo(identifier_path).exists():
                    if not [f for f in arr if path in f]:
                        arr.append(path)
                    return arr
                self.get_root_folder_items(
                    entry.path, depth=depth, count=count + 1, arr=arr)
        except OSError as err:
            return arr
        return arr

    @QtCore.Slot(int)
    def validate(self):
        """Enables the ok button if the selected path is valid and has not been
        added already to the bookmarks widget.

        """
        if not self.pick_server_widget.view().selectionModel().hasSelection():
            self.ok_button.setText(u'Add bookmark')
            self.ok_button.setDisabled(True)
            self.ok_button.update()
            return

        if not self.pick_job_widget.view().selectionModel().hasSelection():
            self.ok_button.setText(u'Add bookmark')
            self.ok_button.setDisabled(True)
            self.ok_button.update()
            return

        if not self.pick_root_widget.view().selectionModel().hasSelection():
            self.ok_button.setText(u'Add bookmark')
            self.ok_button.setDisabled(True)
            self.ok_button.update()
            return

        index = self.pick_root_widget.view().selectionModel().currentIndex()
        if not index.data(QtCore.Qt.StatusTipRole):
            self.ok_button.setText(u'Add bookmark')
            self.ok_button.setDisabled(True)
            self.ok_button.update()
            return

        # Let's check if the path is valid
        server = self.pick_server_widget.view().selectionModel(
        ).currentIndex().data(QtCore.Qt.StatusTipRole)
        job = self.pick_job_widget.view().selectionModel(
        ).currentIndex().data(QtCore.Qt.DisplayRole)
        root = self.pick_root_widget.view().selectionModel(
        ).currentIndex().data(QtCore.Qt.DisplayRole)

        key = u'{}/{}/{}'.format(server, job, root)
        file_info = QtCore.QFileInfo(key)
        if not file_info.exists():
            self.ok_button.setText(u'Bookmark folder not set')
            self.ok_button.setDisabled(True)
            self.ok_button.update()
            return
        if not file_info.isReadable():
            self.ok_button.setText(u'Cannot read folder')
            self.ok_button.setDisabled(True)
            self.ok_button.update()
            return
        if not file_info.isWritable():
            self.ok_button.setText(u'Cannot write to folder')
            self.ok_button.setDisabled(True)
            self.ok_button.update()
            return
        if file_info.isHidden():
            self.ok_button.setText(u'Folder is hidden')
            self.ok_button.setDisabled(True)
            self.ok_button.update()
            return

        bookmarks = local_settings.value(u'bookmarks')
        bookmarks = bookmarks if bookmarks else {}

        if key in bookmarks:
            self.ok_button.setText(u'Bookmark added already')
            self.ok_button.setDisabled(True)
            self.ok_button.update()
            return

        self.ok_button.setText(u'Add bookmark')
        self.ok_button.setDisabled(False)
        self.ok_button.update()

    @QtCore.Slot()
    def add_bookmark(self):
        """The action to execute when the `Ok` button is pressed."""
        if not self.pick_server_widget.view().selectionModel().hasSelection():
            return
        index = self.pick_server_widget.view().selectionModel().currentIndex()
        server = index.data(QtCore.Qt.StatusTipRole)

        if not self.pick_job_widget.view().selectionModel().hasSelection():
            return
        index = self.pick_job_widget.view().selectionModel().currentIndex()
        job = index.data(QtCore.Qt.DisplayRole)

        if not self.pick_root_widget.view().selectionModel().hasSelection():
            return

        index = self.pick_root_widget.view().selectionModel().currentIndex()
        if not index.data(QtCore.Qt.StatusTipRole):
            return

        root = index.data(QtCore.Qt.DisplayRole)

        if not all((server, job, root)):
            return

        key = u'{}/{}/{}'.format(server, job, root)
        file_info = QtCore.QFileInfo(key)
        if not file_info.exists():
            return

        bookmark = {key: {u'server': server, u'job': job, u'root': root}}
        bookmarks = local_settings.value(u'bookmarks')

        if not bookmarks:
            local_settings.setValue(u'bookmarks', bookmark)
        else:
            bookmarks[key] = bookmark[key]
            local_settings.setValue(u'bookmarks', bookmarks)

        # We will set the newly added Bookmark as the active item
        self.new_key = key
        bookmarkswidget = self.parent().widget(0)
        bookmarkswidget.model().sourceModel().beginResetModel()
        bookmarkswidget.model().sourceModel().__initdata__()
        for idx in xrange(bookmarkswidget.model().rowCount()):
            index = bookmarkswidget.model().index(idx, 0)
            parent = index.data(common.ParentRole)
            if parent[0].lower() == server.lower() and parent[1].lower() == job.lower() and parent[2].lower() == root.lower():
                bookmarkswidget.selectionModel().setCurrentIndex(
                    index, QtCore.QItemSelectionModel.ClearAndSelect)
                bookmarkswidget.scrollTo(
                    index, QtWidgets.QAbstractItemView.PositionAtCenter)
                break

        # Resetting the folder selection
        self.add_root_folders(
            self.pick_job_widget.view().selectionModel().currentIndex())
        self.pick_root_widget.update()
        self.validate()

        mbox = QtWidgets.QMessageBox(parent=self)
        mbox.setWindowTitle(u'Bookmark added')
        mbox.setIcon(QtWidgets.QMessageBox.NoIcon)
        mbox.setStandardButtons(
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        mbox.setText(
            u'Bookmark added. Would you like to add another bookmark?')
        res = mbox.exec_()
        if res == QtWidgets.QMessageBox.No:
            self.parent().parent().listcontrolwidget.listChanged.emit(0)

    def activate_bookmark(self):
        """Selects and activates the newly added bookmark in the `BookmarksWidget`."""
        if not self.new_key:
            return

        for n in xrange(self.parent().model().rowCount()):
            index = self.parent().model().index(n, 0)
            if index.data(QtCore.Qt.StatusTipRole) == self.new_key:
                self.parent().selectionModel().setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect
                )
                self.parent().scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
                self.parent().activate(index)
                self.new_key = None
                return
        self.new_key = None

    def add_servers_from_config(self):
        """Querries the `gwbrowser.common` module and populates the widget with
        the available servers.

        """
        self.pick_server_widget.view().clear()

        for server in common.Server.servers():
            file_info = QtCore.QFileInfo(server[u'path'])

            name = server[u'path'].split(u'/').pop()

            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, name)
            item.setData(common.DescriptionRole, server[u'description'])
            item.setData(QtCore.Qt.StatusTipRole, file_info.filePath())
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                common.WIDTH, common.ROW_BUTTONS_HEIGHT))

            # Disable the item if it isn't available
            if not file_info.exists():
                item.setFlags(QtCore.Qt.NoItemFlags)

            item.setData(common.FlagsRole, item.flags())
            self.pick_server_widget.view().addItem(item)

    @QtCore.Slot(QtCore.QModelIndex)
    def add_jobs_from_server_folder(self, index):
        """Querries the given folder and return all readable folder within.

        Args:
            qdir (type): Description of parameter `qdir`.

        Returns:
            type: Description of returned object.

        """
        m = self.pick_server_widget.view().selectionModel()
        if not m.currentIndex().isValid():
            return

        self.pick_job_widget.view().clear()

        path = index.data(QtCore.Qt.StatusTipRole)
        if not QtCore.QFileInfo(path).exists():
            mbox = QtWidgets.QMessageBox()
            mbox.setWindowTitle(u'An error occuered')
            mbox.setText(u'The selected server could not be found.')
            mbox.setInformativeText(
                u'Check the server settings and make sure the set servers are p[ointing to valid network share.')
            return mbox.exec_()

        for entry in sorted([f for f in gwscandir.scandir(path)], key=lambda x: x.name):
            if entry.name.startswith(u'.'):
                continue
            if entry.is_symlink():
                continue
            if not entry.is_dir():
                continue
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, entry.name)
            item.setData(QtCore.Qt.StatusTipRole,
                         entry.path.replace(u'\\', u'/'))
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                common.WIDTH, common.ROW_BUTTONS_HEIGHT))

            item.setData(common.FlagsRole, item.flags())

            self.pick_job_widget.view().addItem(item)

    @QtCore.Slot(QtCore.QModelIndex)
    def add_root_folders(self, index):
        """Adds the found root folders to the `pick_root_widget`."""
        self.pick_root_widget.view().clear()
        if not index.isValid():
            return

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        if not file_info.exists():
            return

        arr = []
        self.get_root_folder_items(index.data(
            QtCore.Qt.StatusTipRole), arr=arr)

        bookmarks = local_settings.value(u'bookmarks')
        bookmarks = bookmarks if bookmarks else {}

        for entry in sorted(arr):
            entry = entry.replace(u'\\', u'/')
            item = QtWidgets.QListWidgetItem()
            name = entry.replace(index.data(
                QtCore.Qt.StatusTipRole), u'').strip(u'/')
            item.setData(QtCore.Qt.DisplayRole, name)
            item.setData(QtCore.Qt.StatusTipRole, entry)
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                common.WIDTH, common.ROW_BUTTONS_HEIGHT))

            # Disabling the item if it has already been added to the widget
            if entry.replace(u'\\', u'/') in bookmarks:
                item.setFlags(QtCore.Qt.NoItemFlags)
                item.setData(QtCore.Qt.DisplayRole,
                             u'{} (bookmark already added)'.format(name))

            self.pick_root_widget.view().addItem(item)

        # Adding a special custom button
        item = QtWidgets.QListWidgetItem()
        name = custom_string
        item.setData(QtCore.Qt.DisplayRole, name)
        item.setData(QtCore.Qt.StatusTipRole, None)
        item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
            common.WIDTH, common.ROW_BUTTONS_HEIGHT))
        self.pick_root_widget.view().insertItem(0, item)

    def showEvent(self, event):
        """Custom show event responsible for placing the widget inthe right place."""
        self.initialize()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = AddBookmarksWidget()
    w.exec_()
    # app.exec_()
