# -*- coding: utf-8 -*-
"""Module defines a the wiedget used to add a new bookmark to `GWBrowser`.

"""
# pylint: disable=E1101, C0103, R0913, I1101

import re
import os
import sys
import functools
from PySide2 import QtWidgets, QtGui, QtCore, QtNetwork

import gwbrowser.gwscandir as gwscandir
from gwbrowser.imagecache import ImageCache
import gwbrowser.common as common
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.baselistwidget import BaseModel
from gwbrowser.delegate import BaseDelegate
from gwbrowser.delegate import paintmethod
from gwbrowser.settings import local_settings, Active, active_monitor


custom_string = u'Select custom folder...'


class PaintedButton(QtWidgets.QPushButton):
    """Custom buttons used to paint the buttons of the ``AddBookmarksWidget``."""

    def __init__(self, text, parent=None):
        super(PaintedButton, self).__init__(text, parent=parent)

    def paintEvent(self, event):
        """Custom paint for smooth text display."""
        painter = QtGui.QPainter()
        painter.begin(self)

        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        color = common.TEXT if self.isEnabled() else common.SECONDARY_TEXT
        color = common.TEXT_SELECTED if hover else color

        bg_color = common.SECONDARY_TEXT if self.isEnabled() else QtGui.QColor(0, 0, 0, 20)
        painter.setBrush(bg_color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 2, 2)

        rect = QtCore.QRect(self.rect())
        rect.setLeft(rect.left() + common.INDICATOR_WIDTH)
        common.draw_aliased_text(
            painter, common.PrimaryFont, rect, self.text(), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)

        painter.end()


class PaintedLabel(QtWidgets.QLabel):
    """Custom label used to paint the elements of the ``AddBookmarksWidget``."""
    def __init__(self, text, size=common.MEDIUM_FONT_SIZE, parent=None):
        super(PaintedLabel, self).__init__(text, parent=parent)
        self._font = QtGui.QFont(common.PrimaryFont)
        self._font.setPointSize(size)
        metrics = QtGui.QFontMetrics(self._font)
        self.setFixedHeight(metrics.height())

    def paintEvent(self, event):
        """Custom paint event to use the aliased paint method."""
        painter = QtGui.QPainter()
        painter.begin(self)
        color = common.TEXT
        common.draw_aliased_text(
            painter, self._font, self.rect(), self.text(), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)
        painter.end()


class ComboboxContextMenu(BaseContextMenu):
    """Small context menu to reveal the current choice in the explorer."""

    def __init__(self, index, parent=None):
        super(ComboboxContextMenu, self).__init__(index, parent=parent)
        self.add_reveal_item_menu()


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

        if index.flags() == QtCore.Qt.NoItemFlags:
            return

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
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        disabled = index.flags() == QtCore.Qt.NoItemFlags

        rect = QtCore.QRect(option.rect)
        rect.setLeft(common.MARGIN)
        rect.setRight(option.rect.right())

        text = index.data(QtCore.Qt.DisplayRole)
        color = common.TEXT_SELECTED if hover else common.TEXT
        color = common.SECONDARY_TEXT if disabled else color

        if text == custom_string:
            _rect = QtCore.QRect(option.rect)
            _rect.setTop(_rect.bottom() - 1)
            painter.setBrush(common.SEPARATOR)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRect(_rect)
        else:
            text = text.upper()

        common.draw_aliased_text(
            painter, common.PrimaryFont, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)

    def sizeHint(self, option, index):
        return QtCore.QSize(self.parent().view().width(), common.ROW_HEIGHT * 0.66)


class AddBookmarkCombobox(QtWidgets.QComboBox):
    """Combobox responsible for picking a bookmark segment."""

    def __init__(self, type, parent=None):
        super(AddBookmarkCombobox, self).__init__(parent=parent)
        self.type = type
        self.context_menu_cls = ComboboxContextMenu
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        view = QtWidgets.QListWidget()  # Setting a custom view here
        self.setModel(view.model())
        self.setView(view)
        self.setDuplicatesEnabled(False)
        self.setItemDelegate(ComboBoxItemDelegate(self))
        self.setMouseTracking(True)

    def contextMenuEvent(self, event):
        """Custom context menu event for the combobox widget."""
        index = self.view().item(self.view().currentRow())
        if not index:
            return
        if index.data(QtCore.Qt.DisplayRole) == custom_string:
            return

        widget = self.context_menu_cls(index, parent=self)

        rect = self.rect()
        pos = self.mapToGlobal(event.pos())
        widget.move(
            self.mapToGlobal(rect.bottomLeft()).x(),
            self.mapToGlobal(rect.bottomLeft()).y(),
        )

        common.move_widget_to_available_geo(widget)
        widget.exec_()

    def paintEvent(self, event):
        """The paint event responsible for drawing the current selection."""
        if event.rect() != self.rect():
            return

        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        if self.currentIndex() == -1:
            text = u'Click to select {}'.format(self.type)
            color = common.TEXT
        else:
            item = self.view().item(self.view().currentRow())
            if not item:
                text = u'Click to select {}'.format(self.type)
            else:
                text = item.data(QtCore.Qt.DisplayRole)
            text = text.upper() if text else u'Click to select {}'.format(self.type)
            color = common.TEXT_SELECTED
        if hover:
            color = common.TEXT_SELECTED

        painter = QtGui.QPainter()
        painter.begin(self)

        rect = QtCore.QRect(self.rect())
        if self.view().currentRow() != -1 and text.upper() != custom_string.upper():
            _rect = QtCore.QRect(rect)
            _rect.setWidth(_rect.height())
            pixmap = ImageCache.instance().get_rsc_pixmap(u'check', common.FAVOURITE, self.height())
            painter.drawPixmap(_rect, pixmap, pixmap.rect())
            rect.setLeft(rect.left() + rect.height() + common.INDICATOR_WIDTH)

        common.draw_aliased_text(
            painter, common.PrimaryFont, rect, text, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, color)
        painter.end()

    @QtCore.Slot(int)
    def pick_custom(self, idx):
        """Method to select a the root folder of the assets. Called by the Assets push button."""
        if idx != 0:
            return

        parent = self.window()
        server = parent.pick_server_widget.currentData(QtCore.Qt.StatusTipRole)
        job = parent.pick_job_widget.currentData(QtCore.Qt.DisplayRole)

        if not all((server, job)):
            return

        path = u'{}/{}'.format(server, job)
        file_info = QtCore.QFileInfo(path)
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

        if path not in res:
            parent.warning(u'Invalid folder selected', u'The bookmark folder has to be inside current job folder.')
            return

        file_info = QtCore.QFileInfo(res)
        if not file_info.exists():
            return parent.warning(u'Internal error occured.', u'Could not load the selected folder.')

        self.view().item(0).setData(QtCore.Qt.DisplayRole, file_info.filePath().replace(path, u'').strip(u'/'))
        self.view().item(0).setData(QtCore.Qt.StatusTipRole, file_info.filePath())
        self.view().item(0).setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                common.WIDTH, common.ROW_BUTTONS_HEIGHT))

        parent.validate()


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
        self.new_key = None

        self.setWindowTitle(u'Add bookmark')
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
        """Populates the comboboxes and selects the currently active items (if there's any)."""
        self.add_servers_from_config()
        self.select_saved_item(None, key='server', combobox=self.pick_server_widget)

        self.add_jobs_from_server_folder(self.pick_server_widget.currentIndex())
        self.select_saved_item(None, key='job', combobox=self.pick_job_widget)

        self.add_root_folders(self.pick_job_widget.currentIndex())
        self.select_saved_item(None, key='root', combobox=self.pick_root_widget)

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
        label = PaintedLabel(u'Add bookmark', size=common.LARGE_FONT_SIZE)
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
        self.pick_server_widget = AddBookmarkCombobox(u'server', parent=self)
        self.pick_job_widget = AddBookmarkCombobox(u'job', parent=self)
        self.pick_root_widget = AddBookmarkCombobox(u'bookmark folder', parent=self)

        row = QtWidgets.QWidget(parent=self)
        row.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        row.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        QtWidgets.QHBoxLayout(row)

        self.ok_button = PaintedButton(u'Add bookmark')
        self.close_button = PaintedButton(u'Close')

        row.layout().addWidget(self.ok_button, 1)
        row.layout().addWidget(self.close_button, 1)

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

        # Server
        self.layout().addWidget(row)
        label = PaintedLabel(u'Server')
        self.pathsettings.layout().addWidget(label)
        self.pathsettings.layout().addWidget(self.pick_server_widget)
        self.pathsettings.layout().addSpacing(common.INDICATOR_WIDTH * 2)

        # Job
        label = PaintedLabel(u'Job')
        self.pathsettings.layout().addWidget(label)
        self.pathsettings.layout().addWidget(self.pick_job_widget)
        self.pathsettings.layout().addSpacing(common.INDICATOR_WIDTH * 2)

        # Bookmarks folder
        label = PaintedLabel(u'Bookmark folder')
        self.pathsettings.layout().addWidget(label)
        self.pathsettings.layout().addWidget(self.pick_root_widget)

        # Bookmarks description
        text = u'<p style="font-size: {s}pt; color: rgba({},{},{},{}); font-family: "{f}"">'
        text += 'Folders containing assets are listed above. '
        text += 'To pick a custom folder use the "{c}" button.</p>'
        text = text.format(
            *common.TEXT.getRgb(),
            s=common.psize(common.SMALL_FONT_SIZE),
            f=common.SecondaryFont.family(),
            c=custom_string
        )
        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignJustify)
        self.pathsettings.layout().addWidget(label)

    def _connectSignals(self):
        self.pick_server_widget.activated.connect(self.add_jobs_from_server_folder)
        self.pick_server_widget.activated.connect(
            functools.partial(self.select_saved_item, key='job', combobox=self.pick_job_widget))
        self.pick_server_widget.activated.connect(self.add_root_folders)
        self.pick_server_widget.activated.connect(
        functools.partial(self.select_saved_item, key='root', combobox=self.pick_root_widget))

        self.pick_job_widget.activated.connect(self.add_root_folders)
        self.pick_job_widget.activated.connect(
            functools.partial(self.select_saved_item, key='root', combobox=self.pick_root_widget))

        self.pick_server_widget.currentIndexChanged.connect(self.validate)
        self.pick_job_widget.currentIndexChanged.connect(self.validate)
        self.pick_root_widget.currentIndexChanged.connect(self.validate)
        self.pick_root_widget.activated.connect(self.pick_root_widget.pick_custom)

        self.ok_button.pressed.connect(self.add_bookmark)
        self.close_button.pressed.connect(self.close)

        if self.parent():
            self.parent().model().sourceModel().modelReset.connect(self.post_event)
            # self.parent().model().sourceModel().modelReset.connect(self.hide)

    @QtCore.Slot()
    def post_event(self):
        """This slot fires after the new bookmark has been added to the bookmarks widget."""
        if not self.new_key:
            return
        self.activate_bookmark(self.new_key)
        self.new_key = None

    @QtCore.Slot(int)
    def select_saved_item(self, index, key=None, combobox=None):
        """Sets the currently active job as the selected item."""

        def first_valid():
            """Returns the first selectable item's row number."""
            if not combobox.count():
                return -1

            for idx in xrange(combobox.count()):
                if combobox.view().item(idx).flags() != QtCore.Qt.NoItemFlags:
                    return idx
            return -1

        local_paths = Active.paths()
        if local_paths[key] is None:
            combobox.setCurrentIndex(first_valid())
            combobox.view().setCurrentRow(first_valid())
            return
        if local_paths[key] == 'None':
            combobox.setCurrentIndex(first_valid())
            combobox.view().setCurrentRow(first_valid())
            return

        idx = combobox.findData(
            local_paths[key],
            role=QtCore.Qt.StatusTipRole,
            flags=QtCore.Qt.MatchEndsWith
        )

        if idx is None:
            combobox.setCurrentIndex(first_valid())
            combobox.view().setCurrentRow(first_valid())
            return
        if idx == -1:
            combobox.setCurrentIndex(first_valid())
            combobox.view().setCurrentRow(first_valid())
            return

        combobox.setCurrentIndex(idx)
        combobox.view().setCurrentRow(idx)
        return

    @QtCore.Slot(int)
    def add_root_folders(self, index):
        """Adds the found root folders to the `pick_root_widget`."""
        self.pick_root_widget.view().clear()
        self.pick_root_widget.clear()

        if index == -1:
             return

        path = self.pick_job_widget.currentData(QtCore.Qt.StatusTipRole)
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            return

        arr = []
        self.get_root_folder_items(path, arr=arr)
        bookmarks = local_settings.value(u'bookmarks')
        bookmarks = bookmarks if bookmarks else {}

        for entry in sorted(arr):
            entry = entry.replace('\\', '/')
            item = QtWidgets.QListWidgetItem()
            name = entry.replace(path, u'').strip(u'/')
            item.setData(QtCore.Qt.DisplayRole, name)
            item.setData(QtCore.Qt.StatusTipRole, entry)
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                common.WIDTH, common.ROW_BUTTONS_HEIGHT))

            # Disabling the item if it has already been added to the widget
            if entry.replace('\\', '/') in bookmarks:
                item.setFlags(QtCore.Qt.NoItemFlags)

            self.pick_root_widget.view().addItem(item)

        # Adding a special custom button
        item = QtWidgets.QListWidgetItem()
        name = custom_string
        item.setData(QtCore.Qt.DisplayRole, name)
        item.setData(QtCore.Qt.StatusTipRole, None)
        item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
            common.WIDTH, common.ROW_BUTTONS_HEIGHT))
        self.pick_root_widget.view().insertItem(0, item)

    def get_root_folder_items(self, path, depth=4, count=0, arr=[]):
        """Scans the given path recursively and returns all root-folder candidates.
        The recursion-depth is limited by the `depth`.

        Args:
            depth (int): The number of subfolders to scan.

        Returns:
            A list of QFileInfo items

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
                self.get_root_folder_items(entry.path, depth=depth, count=count + 1, arr=arr)
        except OSError as err:
            return arr
        return arr

    @QtCore.Slot(int)
    def validate(self):
        """Enables the ok button if the selected path is valid and has not been
        added already to the bookmarks widget.

        """
        if self.pick_server_widget.currentIndex() == -1:
            self.ok_button.setText(u'Server not set')
            self.ok_button.setDisabled(True)
            return

        if self.pick_job_widget.currentIndex() == -1:
            self.ok_button.setText(u'Job not set')
            self.ok_button.setDisabled(True)
            return

        if self.pick_root_widget.currentIndex() == -1:
            self.ok_button.setText(u'Bookmark folder not set')
            self.ok_button.setDisabled(True)
            return

        # Let's check if the path is valid
        # self.ok_button.setDisabled(False)
        server = self.pick_server_widget.currentData(QtCore.Qt.StatusTipRole)
        job = self.pick_job_widget.currentData(QtCore.Qt.DisplayRole)
        root = self.pick_root_widget.currentData(QtCore.Qt.DisplayRole)

        key = u'{}/{}/{}'.format(server, job , root)
        file_info = QtCore.QFileInfo(key)
        if not file_info.exists():
            self.ok_button.setText(u'Bookmark folder not set')
            self.ok_button.setDisabled(True)
            return
        if not file_info.isReadable():
            self.ok_button.setText(u'Cannot read folder')
            self.ok_button.setDisabled(True)
            return
        if not file_info.isWritable():
            self.ok_button.setText(u'Cannot write to folder')
            self.ok_button.setDisabled(True)
            return
        if file_info.isHidden():
            self.ok_button.setText(u'Folder is hidden')
            self.ok_button.setDisabled(True)
            return

        bookmarks = local_settings.value(u'bookmarks')
        bookmarks = bookmarks if bookmarks else {}

        if key in bookmarks:
            self.ok_button.setText(u'Bookmark added already')
            self.ok_button.setDisabled(True)
            return

        self.ok_button.setText(u'Add bookmark')
        self.ok_button.setDisabled(False)

    @QtCore.Slot()
    def add_bookmark(self):
        """The action to execute when the `Ok` button is pressed."""
        server = self.pick_server_widget.currentData(QtCore.Qt.StatusTipRole)
        job = self.pick_job_widget.currentData(QtCore.Qt.DisplayRole)
        root = self.pick_root_widget.currentData(QtCore.Qt.DisplayRole)

        if not all((server, job, root)):
            self.warning('An error occured', 'Unable to get the selected bookmark data.')
            return

        key = u'{}/{}/{}'.format(server, job , root)
        file_info = QtCore.QFileInfo(key)
        if not file_info.exists():
            self.warning('An error occured', 'Unable to find the selected bookmark folder.')
            return

        bookmark = {key: {u'server': server, u'job': job, u'root': root}}

        bookmarks = local_settings.value(u'bookmarks')
        if not bookmarks:
            local_settings.setValue(u'bookmarks', bookmark)
        else:
            bookmarks[key] = bookmark[key]
            local_settings.setValue(u'bookmarks', bookmarks)
            sys.stdout.write('# GWBrowser: Bookmark {} added\n'.format(key))

        if self.parent():
            self.new_key = key
            self.parent().unset_activated()
            self.parent().model().sourceModel().modelDataResetRequested.emit()
            self.add_root_folders(self.pick_job_widget.currentIndex())

    @QtCore.Slot(unicode)
    def activate_bookmark(self, path):
        """Selects and activates the newly added bookmark in the `BookmarksWidget`."""
        try:
            # This is needed - it is not possible to disconnect a partial object in PySide2, not that I know of at least...
            if not self.parent():
                return
        except RuntimeError:
            return

        for n in xrange(self.parent().model().rowCount()):
            index = self.parent().model().index(n, 0)
            if index.data(QtCore.Qt.StatusTipRole) == path:
                self.parent().selectionModel().setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect
                )
                self.parent().scrollTo(index)
                self.parent().activate(index)
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

        if index == -1:
            return

        path = self.pick_server_widget.itemData(index, role=QtCore.Qt.StatusTipRole)
        for entry in sorted([f for f in gwscandir.scandir(path)], key=lambda x: x.name):
            if entry.name.startswith(u'.'):
                continue
            if entry.is_symlink():
                continue
            if not entry.is_dir():
                continue
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, entry.name)
            item.setData(QtCore.Qt.StatusTipRole, entry.path.replace(u'\\', u'/'))
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                common.WIDTH, common.ROW_BUTTONS_HEIGHT))

            item.setData(common.FlagsRole, item.flags())

            self.pick_job_widget.view().addItem(item)


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
