# -*- coding: utf-8 -*-
"""Module defines a ListWidget used to represent the assets found in the root
of the `server/job/assets` folder.

The asset collector expects a asset to contain an identifier file,
in the case of the default implementation, a ``*.mel`` file in the root of the asset folder.
If the identifier file is not found the folder will be ignored!

Assets are based on maya's project structure and ``Browser`` expects a
a ``renders``, ``textures``, ``exports`` and a ``scenes`` folder to be present.

The actual name of these folders can be customized in the ``common.py`` module.

"""
# pylint: disable=E1101, C0103, R0913, I1101

import re
import functools
import collections
from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common
from mayabrowser.baselistwidget import BaseContextMenu
from mayabrowser.baselistwidget import BaseInlineIconWidget
from mayabrowser.baselistwidget import BaseModel
from mayabrowser.settings import local_settings, path_monitor
from mayabrowser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite
from mayabrowser.delegate import BookmarksWidgetDelegate
from mayabrowser.delegate import BaseDelegate


class BookmarkInfo(QtCore.QFileInfo):
    """QFileInfo for bookmarks."""

    def __init__(self, bookmark, parent=None):
        self.server = bookmark['server']
        self.job = bookmark['job']
        self.root = bookmark['root']

        path = '{}/{}/{}'.format(self.server, self.job, self.root)
        super(BookmarkInfo, self).__init__(path, parent=parent)

        self.size = functools.partial(common.count_assets, path)


class BookmarksWidgetContextMenu(BaseContextMenu):
    """Context menu associated with the BookmarksWidget.

    Methods:
        refresh: Refreshes the collector and repopulates the widget.

    """

    def __init__(self, index, parent=None):
        super(BookmarksWidgetContextMenu, self).__init__(index, parent=parent)
        # Adding persistent actions
        self.add_sort_menu()
        self.add_display_toggles_menu()
        if index.isValid():
            self.add_reveal_folder_menu()
            self.add_copy_menu()
            self.add_mode_toggles_menu()
        self.add_add_bookmark_menu()
        self.add_refresh_menu()


class BookmarksModel(BaseModel):
    def __init__(self, parent=None):
        super(BookmarksModel, self).__init__(parent=parent)

    def __initdata__(self):
        """Collects the data needed to populate the bookmark views."""
        self.internal_data = {}  # reset
        active_paths = path_monitor.get_active_paths()

        items = local_settings.value(
            'bookmarks') if local_settings.value('bookmarks') else []
        items = [BookmarkInfo(items[k]) for k in items]

        for idx, file_info in enumerate(items):
            flags = (
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsEditable
            )

            # Active
            if (
                file_info.server == active_paths['server'] and
                file_info.job == active_paths['job'] and
                file_info.root == active_paths['root']
            ):
                flags = flags | MarkedAsActive

            favourites = local_settings.value('favourites')
            favourites = favourites if favourites else []
            if file_info.filePath() in favourites:
                flags = flags | MarkedAsFavourite

            if not file_info.exists():
                flags = QtCore.Qt.ItemIsSelectable | MarkedAsArchived

            self.internal_data[idx] = {
                QtCore.Qt.DisplayRole: file_info.job,
                QtCore.Qt.EditRole: file_info.job,
                QtCore.Qt.StatusTipRole: file_info.filePath(),
                QtCore.Qt.ToolTipRole: file_info.filePath(),
                QtCore.Qt.SizeHintRole: QtCore.QSize(common.WIDTH, common.ROW_HEIGHT),
                common.FlagsRole: flags,
                common.ParentRole: (file_info.server, file_info.job, file_info.root),
                common.DescriptionRole: u'Bookmark:  {}'.format(file_info.filePath()),
                common.TodoCountRole: common.count_assets(file_info.filePath()),
                common.FileDetailsRole: file_info.size(),
            }


class BookmarksWidget(BaseInlineIconWidget):
    """Widget to list all saved ``Bookmarks``."""

    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(BookmarksModel(), parent=parent)

        self.setWindowTitle('Bookmarks')
        self.setItemDelegate(BookmarksWidgetDelegate(parent=self))
        self._context_menu_cls = BookmarksWidgetContextMenu
        # Select the active item
        self.selectionModel().setCurrentIndex(
            self.active_index(),
            QtCore.QItemSelectionModel.ClearAndSelect
        )

    def inline_icons_count(self):
        return 3

    def activate_current_index(self):
        """Sets the current item as ``active_index``.

        Emits the ``activeBookmarkChanged``, ``activeAssetChanged`` and
        ``activeFileChanged`` signals.

        """
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return
        if not index.data(common.TodoCountRole):
            return
        if not super(BookmarksWidget, self).activate_current_index():
            return

        server, job, root = index.data(common.ParentRole)
        local_settings.setValue('activepath/server', server)
        local_settings.setValue('activepath/job', job)
        local_settings.setValue('activepath/root', root)

        path_monitor.get_active_paths() # Resetting invalid paths
        self.activeBookmarkChanged.emit(index.data(common.ParentRole))

    def toggle_archived(self, index=None, state=None):
        """Bookmarks cannot be archived but they're automatically removed from
        from the ``local_settings``."""
        res = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.NoIcon,
            'Remove bookmark?',
            'Are you sure you want to remove this bookmark?\nDon\'t worry, files won\'t be affected.',
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
            parent=self
        ).exec_()

        if res == QtWidgets.QMessageBox.Cancel:
            return

        if not index:
            index = self.selectionModel().currentIndex()
            index = self.model().mapToSource(index)
        if not index.isValid():
            return

        # Removing the bookmark
        k = index.data(QtCore.Qt.StatusTipRole)
        bookmarks = local_settings.value('bookmarks')
        bookmarks.pop(k, None)
        local_settings.setValue('bookmarks', bookmarks)

        self.refresh()

    def show_add_bookmark_widget(self):
        """Opens a dialog to add a new project to the list of saved locations."""
        widget = AddBookmarkWidget(parent=self)

        app = QtCore.QCoreApplication.instance()
        widget.show()

        pos = self.parent().rect().center()
        pos = self.parent().mapToGlobal(pos)
        widget.move(
            pos.x() - (widget.width() / 2.0),
            pos.y() - (widget.height() / 2.0),
        )

    def mouseDoubleClickEvent(self, event):
        """When the bookmark item is double-clicked the the item will be actiaved."""
        index = self.selectionModel().currentIndex()
        if index.flags() & MarkedAsArchived:
            return
        if index.flags() & MarkedAsActive:
            return
        self.activate_current_index()


class ComboBoxItemDelegate(BaseDelegate):
    """Delegate used to render simple list items."""

    def __init__(self, parent=None):
        super(ComboBoxItemDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        """The main paint method."""
        args = self._get_paint_args(painter, option, index)

        self.paint_background(*args)
        self.paint_selection_indicator(*args)
        self.paint_active_indicator(*args)

        self.paint_name(*args)

    def paint_name(self, *args):
        """Paints the DisplayRole of the items."""
        painter, option, index, selected, _, _, _, _ = args
        disabled = (index.flags() == QtCore.Qt.NoItemFlags)

        painter.save()

        font = QtGui.QFont('Roboto')
        font.setBold(True)
        font.setPointSize(8)
        painter.setFont(font)

        rect = QtCore.QRect(option.rect)
        rect.setLeft(common.MARGIN)
        rect.setRight(option.rect.right())

        if disabled:
            color = self.get_state_color(option, index, common.TEXT_DISABLED)
        else:
            color = self.get_state_color(option, index, common.TEXT)

        painter.setPen(QtGui.QPen(color))
        painter.setBrush(QtCore.Qt.NoBrush)

        metrics = QtGui.QFontMetrics(painter.font())
        text = index.data(QtCore.Qt.DisplayRole)

        # Stripping the Glassworks-specific number suffix
        text = re.sub(r'[\W\d\_]+', ' ', text.upper())
        text = metrics.elidedText(
            text,
            QtCore.Qt.ElideRight,
            rect.width()
        )
        if disabled:
            text = metrics.elidedText(
                '{}  |  Unavailable'.format(index.data(QtCore.Qt.DisplayRole)),
                QtCore.Qt.ElideRight,
                rect.width()
            )

        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft | QtCore.Qt.TextWordWrap,
            text
        )

        painter.restore()

    def sizeHint(self, option, index):
        return QtCore.QSize(self.parent().view().width(), common.ROW_HEIGHT * 0.66)


class AddBookmarkWidget(QtWidgets.QWidget):
    """Defines a widget used add a new ``Bookmark``.
    The final Bookmark path is made up of ``AddBookmarkWidget.server``,
    ``AddBookmarkWidget.job`` and ``AddBookmarkWidget.root``

    Attributes:
        server (str):   The path to the server. `None` if invalid.
        job (str):      The name of the job folder. `None` if invalid.
        root (str):     A relative path to the folder where the assets are located. `None` if invalid.

    """

    def __init__(self, parent=None):
        super(AddBookmarkWidget, self).__init__(parent=parent)
        self._root = None  # The `root` folder

        self.setMouseTracking(True)
        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_widget_pos = None

        self._createUI()
        common.set_custom_stylesheet(self)
        self.setWindowTitle('Add bookmark')
        self.installEventFilter(self)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Window)

        self._connectSignals()
        self._set_initial_values()

    def get_bookmark(self):
        """Querries the selection and picks made in the widget and return a `dict` object.

        Returns:
            dict: A dictionary object containing the selected bookmark.

        """
        server = self.pick_server_widget.currentData(common.DescriptionRole)
        job = self.pick_job_widget.currentData(common.DescriptionRole)
        root = self._root
        key = '{}/{}/{}'.format(server, job, root)
        return {key: {'server': server, 'job': job, 'root': root}}

    def _createUI(self):
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(
            common.MARGIN,
            common.MARGIN,
            common.MARGIN,
            common.MARGIN
        )

        # top label
        label = QtWidgets.QLabel()
        label.setText('Add bookmarks')
        self.layout().addWidget(label, 0)
        label.setStyleSheet("""
            QLabel {
                font-family: "Roboto Black";
                font-size: 12pt;
            }
        """)

        self.pathsettings = QtWidgets.QWidget()
        QtWidgets.QVBoxLayout(self.pathsettings)
        self.pathsettings.layout().setContentsMargins(0, 0, 0, 0)
        self.pathsettings.layout().setSpacing(common.MARGIN * 0.33)

        # Server
        self.pick_server_widget = QtWidgets.QComboBox()
        view = QtWidgets.QListWidget()  # Setting a custom view here
        self.pick_server_widget.setModel(view.model())
        self.pick_server_widget.setView(view)
        self.pick_server_widget.setDuplicatesEnabled(False)
        self.pick_server_widget.setItemDelegate(
            ComboBoxItemDelegate(self.pick_server_widget))

        self.pick_job_widget = QtWidgets.QComboBox()
        view = QtWidgets.QListWidget()  # Setting a custom view here
        self.pick_job_widget.setModel(view.model())
        self.pick_job_widget.setView(view)
        self.pick_job_widget.setDuplicatesEnabled(False)
        self.pick_job_widget.setItemDelegate(
            ComboBoxItemDelegate(self.pick_job_widget))

        self.pick_root_widget = QtWidgets.QPushButton('Pick bookmark folder')

        row = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row)

        self.ok_button = QtWidgets.QPushButton('Add bookmark')
        self.ok_button.setDisabled(True)
        self.cancel_button = QtWidgets.QPushButton('Cancel')

        row.layout().addWidget(self.ok_button, 1)
        row.layout().addWidget(self.cancel_button, 1)

        # Adding it all together
        main_widget = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(main_widget)
        self.label = QtWidgets.QLabel()
        pixmap = common.get_rsc_pixmap('bookmark', common.SECONDARY_TEXT, 128)
        self.label.setPixmap(pixmap)
        main_widget.layout().addStretch(0.5)
        main_widget.layout().addWidget(self.label)
        main_widget.layout().addSpacing(common.MARGIN)
        main_widget.layout().addWidget(self.pathsettings)
        main_widget.layout().addStretch(0.5)
        self.layout().addWidget(main_widget, 1)
        self.layout().addWidget(row)

        self.pathsettings.layout().addStretch(10)
        self.pathsettings.layout().addWidget(QtWidgets.QLabel('Server'), 0.1)
        label = QtWidgets.QLabel(
            'Select the network path the job is located at:')
        label.setWordWrap(True)
        label.setDisabled(True)
        self.pathsettings.layout().addWidget(label, 0)
        self.pathsettings.layout().addWidget(self.pick_server_widget, 0.1)
        self.pathsettings.layout().addStretch(0.1)
        self.pathsettings.layout().addWidget(QtWidgets.QLabel('Job'), 0.1)
        label = QtWidgets.QLabel(
            'Select the job:')
        label.setWordWrap(True)
        label.setDisabled(True)
        self.pathsettings.layout().addWidget(label, 0)
        self.pathsettings.layout().addWidget(self.pick_job_widget, 0.1)
        self.pathsettings.layout().addStretch(0.1)
        self.pathsettings.layout().addWidget(QtWidgets.QLabel('Bookmark folder'), 0.1)
        label = QtWidgets.QLabel(
            'Select the folder inside the Job containing a list of shots and/or assets:')
        label.setWordWrap(True)
        label.setDisabled(True)
        self.pathsettings.layout().addWidget(label, 0)
        self.pathsettings.layout().addWidget(self.pick_root_widget, 0.1)
        self.pathsettings.layout().addStretch(3)

    def _connectSignals(self):
        self.pick_server_widget.currentIndexChanged.connect(self.serverChanged)
        self.pick_job_widget.currentIndexChanged.connect(self.jobChanged)
        self.pick_root_widget.pressed.connect(self._pick_root)

        self.cancel_button.pressed.connect(self.close)
        self.ok_button.pressed.connect(self.action)

    def action(self):
        """The action to execute when the `Ok` button has been pressed."""
        bookmark = self.get_bookmark()
        if not all(bookmark[k] for k in bookmark):
            return
        key = next((k for k in bookmark), None)

        # Let's double-check the integrity of the choice.
        path = ''
        sequence = (bookmark[key]['server'], bookmark[key]
                    ['job'], bookmark[key]['root'])
        for value in sequence:
            path += '{}/'.format(value)
            dir_ = QtCore.QDir(path)
            if dir_.exists():
                continue
            return QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Warning,
                'Could not add bookmark',
                'The selected folder could not be found:\n{}/{}/{}'.format(
                    bookmark[key]['server'],
                    bookmark[key]['job'],
                    bookmark[key]['root'],
                ),
                QtWidgets.QMessageBox.Ok,
                parent=self
            ).exec_()

        bookmarks = local_settings.value('bookmarks')
        if not bookmarks:
            local_settings.setValue('bookmarks', bookmark)
        else:
            bookmarks[key] = bookmark[key]
            local_settings.setValue('bookmarks', bookmarks)

        self.refresh(key)
        self.close()

    def refresh(self, path):
        """Refreshes the parent widget and activates the new bookmark.

        Args:
            key (str): The path/key to select.

        """
        if not self.parent():
            return

        self.parent().refresh()

        for n in xrange(self.parent().model().rowCount()):
            index = self.parent().model().index(n, 0, parent=QtCore.QModelIndex())
            if index.data(QtCore.Qt.StatusTipRole).lower() == path.lower():
                self.parent().selectionModel().setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect
                )
                break

    def _add_servers(self):
        self.pick_server_widget.clear()

        for server in common.SERVERS:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, server['nickname'])
            item.setData(QtCore.Qt.EditRole, server['nickname'])
            item.setData(QtCore.Qt.StatusTipRole,
                         QtCore.QFileInfo(server['path']).filePath())
            item.setData(QtCore.Qt.ToolTipRole,
                         '{}\n{}'.format(server['nickname'], server['path']))
            item.setData(common.DescriptionRole, server['path'])
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                200, common.ROW_BUTTONS_HEIGHT))

            self.pick_server_widget.view().addItem(item)

            file_info = QtCore.QFileInfo(item.data(QtCore.Qt.StatusTipRole))
            if not file_info.exists():
                item.setFlags(QtCore.Qt.NoItemFlags)

            item.setData(common.FlagsRole, item.flags())

    def add_jobs(self, qdir):
        """Querries the given folder and return all readable folder within.

        Args:
            qdir (type): Description of parameter `qdir`.

        Returns:
            type: Description of returned object.

        """

        qdir.setFilter(
            QtCore.QDir.NoDotAndDotDot |
            QtCore.QDir.Dirs |
            QtCore.QDir.NoSymLinks
        )

        self.pick_job_widget.clear()

        for file_info in qdir.entryInfoList():
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, file_info.fileName())
            item.setData(QtCore.Qt.EditRole, file_info.fileName())
            item.setData(QtCore.Qt.StatusTipRole, file_info.filePath())
            item.setData(QtCore.Qt.ToolTipRole, file_info.filePath())
            item.setData(common.DescriptionRole, file_info.fileName())
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                common.WIDTH, common.ROW_BUTTONS_HEIGHT))

            if not file_info.isReadable():
                item.setFlags(QtCore.Qt.NoItemFlags)
            item.setData(common.FlagsRole, item.flags())
            self.pick_job_widget.view().addItem(item)

    def _pick_root(self):
        """Method to select a the root folder of the assets. Called by the Assets push button."""
        self._root = None

        dialog = QtWidgets.QFileDialog()
        dialog.setViewMode(QtWidgets.QFileDialog.Detail)

        path = self.pick_job_widget.currentData(QtCore.Qt.StatusTipRole)
        file_info = QtCore.QFileInfo(path)

        path = dialog.getExistingDirectory(
            self,
            'Pick the location of the assets folder',
            file_info.filePath(),
            QtWidgets.QFileDialog.ShowDirsOnly |
            QtWidgets.QFileDialog.DontResolveSymlinks |
            QtWidgets.QFileDialog.DontUseCustomDirectoryIcons |
            QtWidgets.QFileDialog.HideNameFilterDetails |
            QtWidgets.QFileDialog.ReadOnly
        )
        if not path:
            self.ok_button.setDisabled(True)
            self.pick_root_widget.setText('Select folder')
            self._root = None
            return

        self.ok_button.setDisabled(False)
        count = common.count_assets(path)

        # Removing the server and job name from the selection
        path = path.replace(self.pick_job_widget.currentData(
            QtCore.Qt.StatusTipRole), '')
        path = path.lstrip('/').rstrip('/')

        # Setting the internal root variable
        self._root = path

        if count:
            self.pick_root_widget.setStyleSheet(
                'color: rgba({},{},{},{});'.format(*common.TEXT.getRgb()))
        else:
            stylesheet = 'color: rgba({},{},{},{});'.format(
                *common.TEXT.getRgb())
            stylesheet += 'background-color: rgba({},{},{},{});'.format(
                *common.FAVOURITE.getRgb())
            self.pick_root_widget.setStyleSheet(stylesheet)

        path = '{}:  {} assets'.format(path, count)
        self.pick_root_widget.setText(path)

    def jobChanged(self, idx):
        """Triggered when the pick_job_widget selection changes."""
        self._root = None
        stylesheet = 'color: rgba({},{},{},{});'.format(*common.TEXT.getRgb())
        stylesheet += 'background-color: rgba({},{},{},{});'.format(
            *common.FAVOURITE.getRgb())

        self.pick_root_widget.setStyleSheet(stylesheet)
        self.pick_root_widget.setText('Pick bookmark folder')

    def serverChanged(self, idx):
        """Triggered when the pick_server_widget selection changes."""
        if idx < 0:
            self.pick_job_widget.clear()
            return

        item = self.pick_server_widget.view().item(idx)
        qdir = QtCore.QDir(item.data(QtCore.Qt.StatusTipRole))
        self.add_jobs(qdir)

    def _set_initial_values(self):
        """Sets the initial values in the widget."""
        self._add_servers()

        local_paths = path_monitor.get_active_paths()

        # Select the currently active server
        if local_paths['server']:
            idx = self.pick_server_widget.findData(
                local_paths['server'],
                role=common.DescriptionRole,
                flags=QtCore.Qt.MatchFixedString
            )
            self.pick_server_widget.setCurrentIndex(idx)

        # Select the currently active server
        if local_paths['job']:
            idx = self.pick_job_widget.findData(
                local_paths['job'],
                role=common.DescriptionRole,
                flags=QtCore.Qt.MatchFixedString
            )
            self.pick_job_widget.setCurrentIndex(idx)

    def mousePressEvent(self, event):
        self.move_in_progress = True
        self.move_start_event_pos = event.pos()
        self.move_start_widget_pos = self.mapToGlobal(self.rect().topLeft())

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.NoButton:
            return
        if self.move_start_widget_pos:
            offset = (event.pos() - self.move_start_event_pos)
            self.move(self.mapToGlobal(self.rect().topLeft()) + offset)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    app.w = BookmarksWidget()
    # app.w = QtWidgets.QListView()
    # app.w.setModel(BookmarksModel())
    app.w.show()
    app.exec_()
