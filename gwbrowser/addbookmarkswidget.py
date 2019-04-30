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
import os
import functools

from PySide2 import QtWidgets, QtGui, QtCore, QtNetwork

from gwbrowser.imagecache import ImageCache
import gwbrowser.common as common
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.baselistwidget import BaseModel
from gwbrowser.delegate import BaseDelegate
from gwbrowser.delegate import paintmethod
from gwbrowser.settings import local_settings, Active, active_monitor



class ComboBoxItemDelegate(BaseDelegate):
    """Delegate used to render simple list items."""

    def __init__(self, parent=None):
        super(ComboBoxItemDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        """The main paint method."""
        args = self._get_paint_args(painter, option, index)
        self.paint_background(*args)
        self.paint_name(*args)

    @paintmethod
    def paint_background(self, *args):
        painter, option, index, selected, _, _, _, _ = args
        rect = QtCore.QRect(option.rect)
        if selected:
            painter.setBrush(common.BACKGROUND_SELECTED)
        else:
            painter.setBrush(common.BACKGROUND)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(rect)

    @paintmethod
    def paint_name(self, *args):
        """Paints the DisplayRole of the items."""
        painter, option, index, selected, _, _, _, _ = args
        disabled = (index.flags() == QtCore.Qt.NoItemFlags)

        font = QtGui.QFont(common.PrimaryFont)
        painter.setFont(font)

        rect = QtCore.QRect(option.rect)
        rect.setLeft(common.MARGIN)
        rect.setRight(option.rect.right())

        if disabled:
            color = self.get_state_color(option, index, common.TEXT_DISABLED)
        else:
            color = self.get_state_color(option, index, common.TEXT)

        text = index.data(QtCore.Qt.DisplayRole).upper()
        if disabled:
            text = u'{}  |  Unavailable'.format(
                index.data(QtCore.Qt.DisplayRole))
        common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)

    def sizeHint(self, option, index):
        return QtCore.QSize(self.parent().view().width(), common.ROW_HEIGHT * 0.66)


class PickRootCombobox(QtWidgets.QComboBox):
    """Button responsible for picking a subfolder inside the job to bookmark."""
    # clicked = QtCore.Signal()

    def __init__(self, text, parent=None):
        super(PickRootCombobox, self).__init__(parent=parent)
        self._text = text

        view = QtWidgets.QListWidget()  # Setting a custom view here
        self.setModel(view.model())
        self.setView(view)
        self.setDuplicatesEnabled(False)
        self.setItemDelegate(ComboBoxItemDelegate(self))
        self.setMouseTracking(True)

    def setText(self, text):
        self._text = text

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        common.draw_aliased_text(
            painter, common.PrimaryFont, self.rect(), self._text.upper(), QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, common.TEXT)
        painter.end()

    @QtCore.Slot()
    def pick_custom(self):
        """Method to select a the root folder of the assets. Called by the Assets push button."""
        parent = self.window()
        server = parent.pick_server_widget.currentData(QtCore.Qt.StatusTipRole)
        job = parent.pick_job_widget.currentData(QtCore.Qt.DisplayRole)
        if not all((server, job)):
            return
        file_info = QtCore.QFileInfo(u'{}/{}'.format(server, job))
        if not file_info.exists():
            return parent.warning(u'Could not find job-folder', u'An error occured, the job folder could not be found.')

        dialog = QtWidgets.QFileDialog()
        dialog.setViewMode(QtWidgets.QFileDialog.Detail)
        res = dialog.getExistingDirectory(
            self,
            u'Pick the location of the assets folder',
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

        file_info = QtCore.QFileInfo(res)
        if not file_info.exists():
            return parent.warning(u'Internal error occured.', u'Could not load the selected folder.')

        #
        # self._item = QtWidgets.QListWidgetItem()
        # self._item.setData(QtCore.Qt.DisplayRole, file_info.fileName())
        # self._item.setData(QtCore.Qt.StatusTipRole, file_info.filePath())
        # self._item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
        #         common.WIDTH, common.ROW_BUTTONS_HEIGHT))


class AddBookmarksWidget(QtWidgets.QWidget):
    """Defines a widget used add a new ``Bookmark``.
    The final Bookmark path is made up of ``AddBookmarksWidget.server``,
    ``AddBookmarksWidget.job`` and ``AddBookmarksWidget.root``

    Attributes:
        server (str):   The path to the server. `None` if invalid.
        job (str):      The name of the job folder. `None` if invalid.
        root (str):     A relative path to the folder where the assets are located. `None` if invalid.

    """

    def __init__(self, parent=None):
        super(AddBookmarksWidget, self).__init__(parent=parent)
        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_widget_pos = None

        self.setWindowTitle(u'GWBrowser: Add bookmark')
        self.setMouseTracking(True)
        self.installEventFilter(self)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Window)

        self._createUI()
        self._connectSignals()
        self.initialize()

    def initialize(self):
        self.add_servers_from_config()
        self.select_saved_server()
        self.add_jobs_from_server_folder(self.pick_server_widget.currentIndex())
        self.select_saved_job(self.pick_server_widget.currentIndex())

        self.add_root_folders(self.pick_job_widget.currentIndex())
        self.update_root_text(self.pick_job_widget.currentIndex())

    def _createUI(self):
        """Creates the AddBookmarksWidget's ui and layout."""
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(
            common.MARGIN,
            common.MARGIN,
            common.MARGIN,
            common.MARGIN
        )

        # top label
        label = QtWidgets.QLabel()

        text = u'<p style="font-size: {s}pt; color: rgba({},{},{},{}); font-family: "{f}"">Add bookmark</p>'
        text = text.format(
            *common.TEXT.getRgb(),
            s=common.psize(common.LARGE_FONT_SIZE),
            f=common.PrimaryFont.family()
        )
        label.setText(text)

        label.setAlignment(QtCore.Qt.AlignJustify)
        label.setWordWrap(True)
        self.layout().addWidget(label, 0)

        self.pathsettings = QtWidgets.QWidget(parent=self)
        self.pathsettings.setObjectName('GWBrowserPathsettingsWidget')
        self.pathsettings.setMinimumWidth(300)
        QtWidgets.QVBoxLayout(self.pathsettings)
        self.pathsettings.layout().setContentsMargins(0, 0, 0, 0)
        self.pathsettings.layout().setSpacing(common.INDICATOR_WIDTH)
        self.pathsettings.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.pathsettings.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        # Server
        self.pick_server_widget = QtWidgets.QComboBox(parent=self)
        view = QtWidgets.QListWidget()  # Setting a custom view here
        self.pick_server_widget.setModel(view.model())
        self.pick_server_widget.setView(view)
        self.pick_server_widget.setDuplicatesEnabled(False)
        self.pick_server_widget.setItemDelegate(
            ComboBoxItemDelegate(self.pick_server_widget))

        self.pick_job_widget = QtWidgets.QComboBox(parent=self)
        view = QtWidgets.QListWidget()  # Setting a custom view here
        self.pick_job_widget.setModel(view.model())
        self.pick_job_widget.setView(view)
        self.pick_job_widget.setDuplicatesEnabled(False)
        self.pick_job_widget.setItemDelegate(
            ComboBoxItemDelegate(self.pick_job_widget))

        self.pick_root_widget = PickRootCombobox(u'Pick bookmark folder', parent=self)

        row = QtWidgets.QWidget(parent=self)
        row.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        row.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        QtWidgets.QHBoxLayout(row)

        self.ok_button = QtWidgets.QPushButton(u'Add bookmark')
        self.ok_button.setDisabled(True)
        self.cancel_button = QtWidgets.QPushButton(u'Cancel')

        row.layout().addWidget(self.ok_button, 1)
        row.layout().addWidget(self.cancel_button, 1)

        # Adding it all together
        main_widget = QtWidgets.QWidget()
        main_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        main_widget.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        QtWidgets.QHBoxLayout(main_widget)

        self.label = QtWidgets.QLabel()
        label.setAlignment(QtCore.Qt.AlignJustify)
        label.setWordWrap(True)

        pixmap = ImageCache.get_rsc_pixmap(
            u'bookmark', common.SECONDARY_TEXT, 128)
        self.label.setPixmap(pixmap)
        main_widget.layout().addWidget(self.label)
        main_widget.layout().addSpacing(common.MARGIN)
        main_widget.layout().addWidget(self.pathsettings, 1)
        self.layout().addWidget(main_widget)

        # Server Header
        self.layout().addWidget(row)
        text = u'<p style="font-size: {s}pt; color: rgba({},{},{},{}); font-family: "{f}"">Server</p>'
        text = text.format(
            *common.TEXT.getRgb(),
            s=common.psize(common.MEDIUM_FONT_SIZE),
            f=common.PrimaryFont.family()
        )
        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignJustify)
        label.setWordWrap(True)
        self.pathsettings.layout().addWidget(label)

        # Server description
        text = u'<p style="font-size: {s}pt; color: rgba({},{},{},{}); font-family: "{f}"">Select the server the bookmark is located at:</p>'
        text = text.format(
            *common.BACKGROUND.getRgb(),
            s=common.psize(common.SMALL_FONT_SIZE),
            f=common.SecondaryFont.family()
        )
        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignJustify)
        label.setWordWrap(True)
        self.pathsettings.layout().addWidget(label)

        self.pathsettings.layout().addWidget(self.pick_server_widget)
        self.pathsettings.layout().addSpacing(common.INDICATOR_WIDTH * 2)

        # Job header
        text = u'<p style="font-size: {s}pt; color: rgba({},{},{},{}); font-family: "{f}"">Job</p>'
        text = text.format(
            *common.TEXT.getRgb(),
            s=common.psize(common.MEDIUM_FONT_SIZE),
            f=common.PrimaryFont.family()
        )
        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignJustify)
        self.pathsettings.layout().addWidget(label)

        # Job description
        text = u'<p style="font-size: {s}pt; color: rgba({},{},{},{}); font-family: "{f}"">Select the name of the job:</p>'
        text = text.format(
            *common.BACKGROUND.getRgb(),
            s=common.psize(common.SMALL_FONT_SIZE),
            f=common.SecondaryFont.family()
        )
        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignJustify)

        self.pathsettings.layout().addWidget(label)
        self.pathsettings.layout().addWidget(self.pick_job_widget)
        self.pathsettings.layout().addSpacing(common.INDICATOR_WIDTH * 2)

        # Bookmarks header
        text = u'<p style="font-size: {s}pt; color: rgba({},{},{},{}); font-family: "{f}"">Bookmark folder</span>'
        text = text.format(
            *common.TEXT.getRgb(),
            s=common.psize(common.MEDIUM_FONT_SIZE),
            f=common.PrimaryFont.family()
        )
        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignJustify)
        self.pathsettings.layout().addWidget(label)

        # Bookmarks description

        text = u'<p style="font-size: {s}pt; color: rgba({},{},{},{}); font-family: "{f}"">Select the folder inside the job to be bookmarked.<br/><br/>'
        text += 'Any folder inside the job can be bookmarked but only folders containing <span style="color: silver;">assets</span> are considered valid:</p>'
        text = text.format(
            *common.BACKGROUND.getRgb(),
            s=common.psize(common.SMALL_FONT_SIZE),
            f=common.SecondaryFont.family()
        )
        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignJustify)

        self.pathsettings.layout().addWidget(label)
        self.pathsettings.layout().addWidget(self.pick_root_widget)

    def _connectSignals(self):
        self.pick_server_widget.activated.connect(self.add_jobs_from_server_folder)
        self.pick_server_widget.activated.connect(self.select_saved_job)
        self.pick_server_widget.activated.connect(self.update_root_text)

        self.pick_job_widget.activated.connect(self.update_root_text)
        self.pick_job_widget.activated.connect(self.add_root_folders)

        self.pick_root_widget.activated.connect(self.enable_ok)
        self.pick_root_widget.activated.connect(self.update_root_text)

        self.cancel_button.pressed.connect(self.close)
        self.ok_button.pressed.connect(self.action)

    @QtCore.Slot(int)
    def select_saved_job(self, index):
        """Sets the currently active job as the selected item."""
        local_paths = Active.paths()
        if local_paths[u'job']:
            self.pick_job_widget.setCurrentText(local_paths[u'job'])
            if self.pick_job_widget.currentIndex > -1:
                return
        self.pick_job_widget.setCurrentIndex(0)

    @QtCore.Slot(int)
    def add_root_folders(self, index):
        """Adds the found root folders to the `pick_root_widget`."""
        self.pick_root_widget.view().clear()
        self.pick_root_widget.clear()

        if index < 0:
             return

        path = self.pick_job_widget.currentData(QtCore.Qt.StatusTipRole)
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            return

        arr = []
        self.get_root_folder_items(path, arr=arr)
        for file_info in arr:
            item = QtWidgets.QListWidgetItem()
            name = file_info.filePath().replace(path, u'').strip(u'/')
            item.setData(QtCore.Qt.DisplayRole, name)
            item.setData(QtCore.Qt.StatusTipRole, file_info.filePath())
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                common.WIDTH, common.ROW_BUTTONS_HEIGHT))
            self.pick_root_widget.view().addItem(item)

    def get_root_folder_items(self, path, depth=4, count=0, arr=[]):
        """Scans the given path recursively and returns all root-folder candidates.

        Args:
            depth (int): The number of subfolders to scan.

        Returns:
            A list of QFileInfo items

        """
        if depth == count:
            return arr

        if [f for f in arr if path in f.filePath()]:
            return arr

        ddir = QtCore.QDir(path)
        ddir.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
        for dentry in ddir.entryList():
            dpath = u'{}/{}'.format(ddir.path(), dentry)
            fdir = QtCore.QDir(dpath)
            fdir.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
            for fentry in fdir.entryList():
                fpath = u'{}/{}'.format(fdir.path(), fentry)
                if fentry.lower() == common.ASSET_IDENTIFIER.lower():
                    if not [f for f in arr if path in f.filePath()]:
                        item = QtCore.QFileInfo(path)
                        arr.append(item)
                    return arr
            self.get_root_folder_items(dpath, depth=depth, count=count + 1, arr=arr)
        return arr

    @QtCore.Slot(int)
    def enable_ok(self, index):
        """Enables the ok button if the selected path is valid and hs not been
        added already to the bookmarks widget.

        """
        if index < 0:
            self.ok_button.setText(u'Add bookmark')
            self.ok_button.setDisabled(True)
            return

        server = self.pick_server_widget.currentData(QtCore.Qt.StatusTipRole)
        job = self.pick_job_widget.currentData(QtCore.Qt.DisplayRole)
        root = self.pick_root_widget.currentData(QtCore.Qt.StatusTipRole)

        if not all((server, job, root)):
            self.ok_button.setText(u'Add bookmark')
            self.setDisabled(True)
            return

        # Check if the proposed bookmark is unique
        bookmarks = local_settings.value(u'bookmarks')
        self.ok_button.setDisabled(False)

        key = u'{}/{}/{}'.format(server, job, root)

    def get_bookmark(self):
        """Querries users choices and returns a the bookmarks, a `dict` object with
        `server`, `job`, `root` keys/values set.

        Returns:
            dict: A dictionary object containing the selected bookmark.

        """
        server = self.pick_server_widget.currentData(QtCore.Qt.StatusTipRole)
        job = self.pick_job_widget.currentData(QtCore.Qt.DisplayRole)
        root = self.pick_root_widget.currentData(QtCore.StatusTipRole)
        key = u'{}/{}/{}'.format(server, job, root)

        return {key: {u'server': server, u'job': job, u'root': root}}

    def warning(self, msg1, msg2):
        QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Warning,
            msg1,
            msg2,
            QtWidgets.QMessageBox.Ok,
            parent=self
        ).exec_()

    @QtCore.Slot()
    def action(self):
        """The action to execute when the `Ok` button has been pressed."""
        bookmark = self.get_bookmark()

        if not all(bookmark[k] for k in bookmark):
            return
        key = next((k for k in bookmark), None)

        # Let's double-check the integrity of the choice
        paths = []
        for v in (bookmark[key]['server'], bookmark[key]['job'], bookmark[key]['root']):
            paths.append(v)
            path = u'/'.join(paths)
            path = path.rstrip(u'/')
            file_info = QtCore.QFileInfo(path)

            if not file_info.exists():
                return self.warning(
                    u'Could not add bookmark',
                    u'Folder "{v}" could not be found.\n\nServer: {s}\nJob: {j}\n Root: {r}\nPath: {s}/{j}/{r}'.format(
                        v=v,
                        s=bookmark[key][u'server'],
                        j=bookmark[key][u'job'],
                        r=bookmark[key][u'root'])
                )

        bookmarks = local_settings.value(u'bookmarks')
        if not bookmarks:
            local_settings.setValue(u'bookmarks', bookmark)
        else:
            bookmarks[key] = bookmark[key]
            local_settings.setValue(u'bookmarks', bookmarks)
            sys.stdout.write('# GWBrowser: Bookmark saved. ({})\n'.format(path))

        if self.parent():
            self.parent().model().sourceModel().modelReset.connect(functool.partial(self.select_newly_added_bookmark, path))
            self.parent().model().sourceModel().modelReset.connect(self.close)
            self.parent().model().sourceModel().modelReset.connect(self.deleteLater)
            self.parent().model().sourceModel().beginResetModel()
            self.parent().model().sourceModel().__initdata__()

    @QtCore.Slot(unicode)
    def select_newly_added_bookmark(self, path):
        """Selects the newly added bookmark in the `BookmarksWidget`."""
        if not self.parent():
            return

        for n in xrange(self.parent().model().rowCount()):
            index = self.parent().model().index(n, 0)
            if index.data(QtCore.Qt.StatusTipRole) == path:
                self.parent().selectionModel().setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect
                )
                self.parent().scrollTo(index)
                return

    def add_servers_from_config(self):
        """Querries the `gwbrowser.common` module and populates the widget with
        the available servers.

        """
        self.pick_server_widget.view().clear()

        for server in common.SERVERS:
            file_info = QtCore.QFileInfo(server['path'])
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, server[u'nickname'])
            item.setData(QtCore.Qt.StatusTipRole, file_info.filePath())
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                common.WIDTH, common.ROW_BUTTONS_HEIGHT))

            # Disable the item if it isn't available
            if not file_info.exists():
                item.setFlags(QtCore.Qt.NoItemFlags)

            item.setData(common.FlagsRole, item.flags())
            self.pick_server_widget.view().addItem(item)

    @QtCore.Slot(int)
    def add_jobs_from_server_folder(self, index):
        """Querries the given folder and return all readable folder within.

        Args:
            qdir (type): Description of parameter `qdir`.

        Returns:
            type: Description of returned object.

        """
        self.pick_job_widget.view().clear()

        if index < 0:
            return

        path = self.pick_server_widget.itemData(index, role=QtCore.Qt.StatusTipRole)
        qdir = QtCore.QDir(path)
        qdir.setFilter(
            QtCore.QDir.NoDotAndDotDot |
            QtCore.QDir.Dirs |
            QtCore.QDir.NoSymLinks
        )

        for file_info in qdir.entryInfoList():
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, file_info.fileName())
            item.setData(QtCore.Qt.StatusTipRole, file_info.filePath())
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                common.WIDTH, common.ROW_BUTTONS_HEIGHT))

            if not file_info.isReadable():
                item.setFlags(QtCore.Qt.NoItemFlags)

            item.setData(common.FlagsRole, item.flags())
            self.pick_job_widget.view().addItem(item)

    @QtCore.Slot(int)
    def update_root_text(self, index):
        """Sets the style of the pick root button.
        Triggered when the pick_job_widget selection changes.

        """
        if self.pick_server_widget.currentIndex() < 0:
            stylesheet = u'color: rgba({},{},{},{});'.format(*common.SECONDARY_TEXT.getRgb())
            stylesheet += u'background-color: rgba({},{},{},{});'.format(
                *common.BACKGROUND.getRgb())
            self.pick_root_widget.setStyleSheet(stylesheet)
            self.pick_root_widget.setText(u'Server not selected')
            self.pick_root_widget.setDisabled(True)
            return

        if self.pick_job_widget.currentIndex() < 0:
            stylesheet = u'color: rgba({},{},{},{});'.format(*common.SECONDARY_TEXT.getRgb())
            stylesheet += u'background-color: rgba({},{},{},{});'.format(
                *common.BACKGROUND.getRgb())
            self.pick_root_widget.setStyleSheet(stylesheet)
            self.pick_root_widget.setText(u'Job not selected')
            self.pick_root_widget.setDisabled(True)
            return

        if self.pick_root_widget.currentIndex() < 0:
            stylesheet = u'color: rgba({},{},{},{});'.format(*common.TEXT.getRgb())
            stylesheet += u'background-color: rgba({},{},{},{});'.format(
                *common.SECONDARY_TEXT.getRgb())
            self.pick_root_widget.setStyleSheet(stylesheet)
            self.pick_root_widget.setText(u'Pick folder to bookmark...')
            self.pick_root_widget.setDisabled(False)
            return

        # All seems dandy, let's set the name of the selected root folder
        path = self.pick_root_widget.currentData(QtCore.Qt.StatusTipRole)
        name = self.pick_root_widget.currentData(QtCore.Qt.DisplayRole)

        from gwbrowser.bookmarkswidget import BookmarkInfo
        count = BookmarkInfo.count_assets(path)

        if count:
            text = u'{} ({} assets)'.format(name, count)
            stylesheet = u'color: rgba({},{},{},{});'.format(*common.TEXT.getRgb())
            stylesheet += u'background-color: "green";'
            self.pick_root_widget.setStyleSheet(stylesheet)
        else:
            text = u'{} (No assets found)'.format(name)
            stylesheet = u'color: rgba({},{},{},{});'.format(
                *common.TEXT.getRgb())
            self.pick_root_widget.setStyleSheet(stylesheet)
        self.pick_root_widget.setText(text)

    def select_saved_server(self):
        """Sets the initial values in the widget."""
        local_paths = Active.paths()
        if local_paths[u'server']:
            idx = self.pick_server_widget.findData(
                local_paths[u'server'],
                role=QtCore.Qt.StatusTipRole,
                flags=QtCore.Qt.MatchFixedString
            )
            self.pick_server_widget.setCurrentIndex(idx)
            return
        self.pick_server_widget.setCurrentIndex(0)

    def mousePressEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.move_in_progress = True
        self.move_start_event_pos = event.pos()
        self.move_start_widget_pos = self.mapToGlobal(self.rect().topLeft())

    def mouseMoveEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.buttons() == QtCore.Qt.NoButton:
            return
        if self.move_start_widget_pos:
            offset = (event.pos() - self.move_start_event_pos)
            self.move(self.mapToGlobal(self.rect().topLeft()) + offset)

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_widget_pos = None


def run():
    app = QtWidgets.QApplication([])
    w = AddBookmarksWidget()
    w.show()
    app.exec_()
