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
from collections import OrderedDict
from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common
from mayabrowser.listbase import BaseContextMenu
from mayabrowser.listbase import BaseListWidget
from mayabrowser.collector import BookmarksCollector
import mayabrowser.configparsers as configparser
from mayabrowser.configparsers import local_settings
from mayabrowser.delegate import BookmarksWidgetDelegate
from mayabrowser.delegate import BaseDelegate


class BookmarksWidgetContextMenu(BaseContextMenu):
    """Context menu associated with the BookmarksWidget.

    Methods:
        refresh: Refreshes the collector and repopulates the widget.

    """

    def __init__(self, index, parent=None):
        super(BookmarksWidgetContextMenu, self).__init__(index, parent=parent)
        if index.isValid():
            self.add_bookmark_menu()
        self.add_refresh_menu()

    def add_bookmark_menu(self):
        """Adds options pertinent to bookmark items."""
        _, job, root, _ = self.index.data(QtCore.Qt.UserRole)
        menu_set = OrderedDict()

        menu_set['separator'] = {}
        menu_set['header'] = {
            'text': '{}: {}'.format(job, root),
            'disabled': True,
            'visible': self.index.isValid()
        }

        self.create_menu(menu_set)


class BookmarksWidget(BaseListWidget):
    """Widget to display all added ``Bookmarks``.

    """

    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)
        self.setWindowTitle('Bookmarks')
        self.setItemDelegate(BookmarksWidgetDelegate(parent=self))
        self._context_menu_cls = BookmarksWidgetContextMenu

        # Select the active item
        self.setCurrentItem(self.active_item())

    def set_current_item_as_active(self):
        """Sets the current item as ``active_item``.

        Emits the ``activeBookmarkChanged``, ``activeAssetChanged`` and
        ``activeFileChanged`` signals.

        """
        item = self.currentItem()
        if not item.data(QtCore.Qt.UserRole):
            return

        server, job, root, _ = item.data(QtCore.Qt.UserRole)
        # Updating the local config file
        local_settings.setValue('activepath/server', server)
        local_settings.setValue('activepath/job', job)
        local_settings.setValue('activepath/root', root)
        local_settings.setValue('activepath/asset', None)
        local_settings.setValue('activepath/file', None)

        archived = item.flags() & configparser.MarkedAsArchived
        if archived:
            return

        # Set flags
        active_item = self.active_item()
        if active_item:
            active_item.setFlags(active_item.flags() & ~
                                 configparser.MarkedAsActive)
        item.setFlags(item.flags() | configparser.MarkedAsActive)

        # Emiting active changed signals
        self.activeBookmarkChanged.emit((server, job, root))
        self.activeAssetChanged.emit(None)
        self.activeFileChanged.emit(None)

    def toggle_archived(self, item=None, state=None):
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

        k = self.currentItem().data(common.PathRole)
        bookmarks = local_settings.value('bookmarks')

        k = bookmarks.pop(k, None)
        local_settings.setValue('bookmarks', bookmarks)
        self.refresh()

    def show_add_bookmark_widget(self):
        """Opens a dialog to add a new project to the list of saved locations."""
        widget = AddBookmarkWidget(parent=self)
        widget.show()

        # pos = self.viewport().mapToGlobal(self.viewport().rect().topLeft())
        # widget.move(pos.x() + common.MARGIN, pos.y() + common.MARGIN)

    def add_items(self):
        """Adds the bookmarks saved in the local_settings file to the widget."""
        self.clear()

        # Collecting items
        collector = BookmarksCollector()
        items = collector.get_items(
            key=self.sort_order(),
            reverse=self.is_reversed(),
            path_filter=self.filter()
        )

        for file_info in items:
            item = QtWidgets.QListWidgetItem(parent=self)

            item.setData(
                QtCore.Qt.DisplayRole, file_info.job)
            item.setData(QtCore.Qt.EditRole, item.data(QtCore.Qt.DisplayRole))
            item.setData(QtCore.Qt.StatusTipRole, file_info.filePath())
            item.setData(QtCore.Qt.ToolTipRole,
                         item.data(QtCore.Qt.StatusTipRole))
            item.setData(common.DescriptionRole,
                         u'{}/{}/{}'.format(
                             file_info.server,
                             file_info.job,
                             file_info.root))
            item.setData(QtCore.Qt.UserRole, (
                file_info.server,
                file_info.job,
                file_info.root,
                file_info.size()))
            item.setData(common.PathRole, file_info.filePath())
            item.setData(
                QtCore.Qt.SizeHintRole,
                QtCore.QSize(common.WIDTH, common.ROW_HEIGHT))

            # Active
            if (
                file_info.server == local_settings.value('activepath/server') and
                file_info.job == local_settings.value('activepath/job') and
                file_info.root == local_settings.value('activepath/root')
            ):
                item.setFlags(item.flags() | configparser.MarkedAsActive)

            # If the folder does not exist marking it archived
            if not file_info.exists():
                item.setFlags(item.flags() | configparser.MarkedAsArchived)

            # Flags
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)

            # Favourite
            favourites = local_settings.value('favourites')
            favourites = favourites if favourites else []
            if file_info.filePath() in favourites:
                item.setFlags(item.flags() | configparser.MarkedAsFavourite)

            self.addItem(item)

        # The 'Add location' button at the bottom of the list
        item = QtWidgets.QListWidgetItem()
        item.setFlags(QtCore.Qt.NoItemFlags)
        item.setData(
            QtCore.Qt.DisplayRole,
            'Add location'
        )
        item.setData(
            QtCore.Qt.EditRole,
            'Add location'
        )
        item.setData(
            QtCore.Qt.StatusTipRole,
            'Add a new bookmark'
        )
        item.setData(
            QtCore.Qt.ToolTipRole,
            'Add a new bookmark'
        )
        item.setData(
            common.PathRole,
            None
        )

        self.addItem(item)

    def mouseReleaseEvent(self, event):
        """Custom mouse event handling the add button click."""
        index = self.indexAt(event.pos())
        if index.isValid() and index.row() == (self.count() - 1):
            self.show_add_bookmark_widget()
            return
        super(BookmarksWidget, self).mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """When the bookmark item is double-clicked the the item will be actiaved.
        """
        if self.currentItem() is self.active_item():
            return
        self.set_current_item_as_active()


class ComboBoxItemDelegate(BaseDelegate):
    """Delegate used to render simple list items."""

    def __init__(self, parent=None):
        super(ComboBoxItemDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        """The main paint method."""
        args = self._get_paint_args(painter, option, index)

        self.paint_background(*args)
        self.paint_separators(*args)
        self.paint_selection_indicator(*args)
        self.paint_active_indicator(*args)
        self.paint_focus(*args)

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
            QtCore.Qt.Window
        )
        pixmap = common.get_thumbnail_pixmap(common.CUSTOM_THUMBNAIL)
        self.setWindowIcon(QtGui.QIcon(pixmap))
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
        self.pathsettings.layout().addWidget(QtWidgets.QLabel('Assets'), 0.1)
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
        sequence = (bookmark[key]['server'], bookmark[key]['job'], bookmark[key]['root'])
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

        for n in xrange(self.parent().count()):
            if self.parent().item(n).isHidden():
                continue
            if not self.parent().item(n).data(common.PathRole):
                continue
            if self.parent().item(n).data(common.PathRole) == path:
                self.parent().setCurrentItem(self.parent().item(n))
                break

    def _add_servers(self):
        self.pick_server_widget.clear()

        for server in common.SERVERS:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, server['nickname'])
            item.setData(QtCore.Qt.EditRole, server['nickname'])
            item.setData(QtCore.Qt.StatusTipRole,
                         '{}\n{}'.format(server['nickname'], server['path']))
            item.setData(QtCore.Qt.ToolTipRole,
                         '{}\n{}'.format(server['nickname'], server['path']))
            item.setData(common.DescriptionRole, server['path'])
            item.setData(common.PathRole, QtCore.QFileInfo(server['path']))
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                200, common.ROW_BUTTONS_HEIGHT))

            self.pick_server_widget.view().addItem(item)

            if not item.data(common.PathRole).exists():
                item.setFlags(QtCore.Qt.NoItemFlags)

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
            item.setData(common.PathRole, file_info)
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                common.WIDTH, common.ROW_BUTTONS_HEIGHT))

            if not file_info.isReadable():
                item.setFlags(QtCore.Qt.NoItemFlags)

            self.pick_job_widget.view().addItem(item)

    def _pick_root(self):
        """Method to select a the root folder of the assets. Called by the Assets push button."""
        self._root = None

        dialog = QtWidgets.QFileDialog()
        dialog.setViewMode(QtWidgets.QFileDialog.Detail)
        file_info = self.pick_job_widget.currentData(common.PathRole)

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
            common.PathRole).filePath(), '')
        path = path.lstrip('/').rstrip('/')

        # Setting the internal root variable
        self._root = path

        if count:
            self.pick_root_widget.setStyleSheet(
                'color: rgba({},{},{},{});'.format(*common.TEXT.getRgb()))
        else:
            stylesheet = 'color: rgba({},{},{},{});'.format(*common.TEXT.getRgb())
            stylesheet += 'background-color: rgba({},{},{},{});'.format(*common.FAVOURITE.getRgb())
            self.pick_root_widget.setStyleSheet(stylesheet)

        path = '{}:  {} assets'.format(path, count)
        self.pick_root_widget.setText(path)

    def jobChanged(self, idx):
        """Triggered when the pick_job_widget selection changes."""
        self._root = None
        stylesheet = 'color: rgba({},{},{},{});'.format(*common.TEXT.getRgb())
        stylesheet += 'background-color: rgba({},{},{},{});'.format(*common.FAVOURITE.getRgb())

        self.pick_root_widget.setStyleSheet(stylesheet)
        self.pick_root_widget.setText('Pick bookmark folder')

    def serverChanged(self, idx):
        """Triggered when the pick_server_widget selection changes."""
        if idx < 0:
            self.pick_job_widget.clear()
            return

        item = self.pick_server_widget.view().item(idx)
        qdir = QtCore.QDir(item.data(common.PathRole).filePath())
        self.add_jobs(qdir)

    def _set_initial_values(self):
        """Sets the initial values in the widget."""
        self._add_servers()

        # Select the currently active server
        if local_settings.value('activepath/server'):
            idx = self.pick_server_widget.findData(
                local_settings.value('activepath/server'),
                role=common.DescriptionRole,
                flags=QtCore.Qt.MatchFixedString
            )
            self.pick_server_widget.setCurrentIndex(idx)

        # Select the currently active server
        if local_settings.value('activepath/job'):
            idx = self.pick_job_widget.findData(
                local_settings.value('activepath/job'),
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
    app.w.show()
    app.exec_()
