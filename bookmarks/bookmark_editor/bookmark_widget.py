# -*- coding: utf-8 -*-
"""Sub-editor widget used by the Bookmark Editor to add and toggle bookmarks.

"""
import functools
from PySide2 import QtCore, QtGui, QtWidgets

import _scandir

from .. import common
from .. import log
from .. import settings
from .. import images
from .. import contextmenu
from .. import common_ui
from .. import shortcuts
from .. import actions

from . import list_widget


class BookmarkContextMenu(contextmenu.BaseContextMenu):
    """Custom context menu used to control the list of saved servers.

    """
    def setup(self):
        self.add_menu()
        self.separator()
        if isinstance(self.index, QtWidgets.QListWidgetItem) and self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.bookmark_properties_menu()
            self.reveal_menu()
        self.separator()
        self.refresh_menu()

    def add_menu(self):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'add', common.ADD, common.MARGIN())

        self.menu[u'Add Bookmark...'] = {
            u'action': self.parent().add,
            u'icon': pixmap
        }

    def reveal_menu(self):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'reveal_folder', common.SECONDARY_TEXT, common.MARGIN())

        @QtCore.Slot()
        def reveal():
            actions.reveal(self.index.data(QtCore.Qt.UserRole) + '/.')

        self.menu[u'Reveal...'] = {
            u'action': reveal,
            u'icon': pixmap
        }

    def refresh_menu(self):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'refresh', common.SECONDARY_TEXT, common.MARGIN())
        self.menu[u'Refresh'] = {
            u'action': self.parent().init_data,
            u'icon': pixmap
        }

    def bookmark_properties_menu(self):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'settings', common.SECONDARY_TEXT, common.MARGIN())

        server = self.parent().server
        job = self.parent().job
        root = self.index.data(QtCore.Qt.DisplayRole)

        self.menu[u'Properties'] = {
            'text': u'Edit Properties...',
            u'action': functools.partial(actions.edit_bookmark, server, job, root),
            u'icon': pixmap
        }


class BookmarkListWidget(list_widget.ListWidget):
    """Simple list widget used to add and remove servers to/from the local
    settings.

    """
    loaded = QtCore.Signal()
    bookmarkAdded = QtCore.Signal(unicode, unicode, unicode)
    bookmarkRemoved = QtCore.Signal(unicode, unicode, unicode)

    def __init__(self, parent=None):
        super(BookmarkListWidget, self).__init__(
            default_message=u'No bookmarks found.',
            parent=parent
        )

        self._interrupt_requested = False

        self.setWindowTitle(u'Bookmark Editor')
        self.setObjectName(u'BookmarkEditor')

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        self.setMinimumWidth(common.WIDTH() * 0.33)

        self._connect_signals()
        self.init_shortcuts()

    def init_shortcuts(self):
        shortcuts.add_shortcuts(self, shortcuts.BookmarkEditorShortcuts)
        connect = functools.partial(shortcuts.connect, shortcuts.BookmarkEditorShortcuts)
        connect(shortcuts.AddItem, self.add)

    def _connect_signals(self):
        super(BookmarkListWidget, self)._connect_signals()
        self.itemClicked.connect(self.toggle_checkbox)
        self.itemActivated.connect(self.toggle_checkbox)

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def toggle_checkbox(self, item):
        settings.local_settings.sync()
        bookmarks = settings.local_settings.get_bookmarks()

        if item.checkState() == QtCore.Qt.Checked:
            item.setCheckState(QtCore.Qt.Unchecked)
            if item.data(QtCore.Qt.UserRole) in [f for f in bookmarks]:
                del bookmarks[item.data(QtCore.Qt.UserRole)]
            self.bookmarkRemoved.emit(
                self.server, self.job, item.data(QtCore.Qt.DisplayRole))
        elif item.checkState() == QtCore.Qt.Unchecked:
            item.setCheckState(QtCore.Qt.Checked)
            bookmarks[item.data(QtCore.Qt.UserRole)] = {
                settings.ServerKey: self.server,
                settings.JobKey: self.job,
                settings.RootKey: item.data(QtCore.Qt.DisplayRole)
            }
            self.bookmarkAdded.emit(
                self.server, self.job, item.data(QtCore.Qt.DisplayRole))

        self.set_item_state(item)

    @common.debug
    @common.error
    @QtCore.Slot()
    def add(self, *args, **kwargs):
        if not self.server or not self.job:
            return

        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            u'Pick a new bookmark folder',
            self.server + u'/' + self.job,
            QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks
        )
        if not path:
            return
        if not QtCore.QDir(path).mkdir(common.BOOKMARK_ROOT_DIR):
            log.error(u'Failed to create bookmark.')

        name = path.split(self.job)[-1].strip(u'/').strip(u'\\')

        for n in xrange(self.count()):
            item = self.item(n)
            if item.data(QtCore.Qt.DisplayRole) == name:
                common_ui.MessageBox(
                    u'"{}" is already a bookmark.'.format(name),
                    u'The selected folder is already a bookmark, skipping.'
                ).open()
                return

        item = QtWidgets.QListWidgetItem()
        item.setFlags(
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsSelectable |
            QtCore.Qt.ItemIsUserCheckable
        )
        item.setCheckState(QtCore.Qt.Unchecked)
        item.setData(QtCore.Qt.DisplayRole, name)
        item.setData(QtCore.Qt.UserRole, path)
        size = QtCore.QSize(
            0,
            common.MARGIN() * 2
        )
        item.setSizeHint(size)
        self.insertItem(self.count(), item)
        self.set_item_state(item)
        self.setCurrentItem(item)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        menu = BookmarkContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def showEvent(self, event):
        super(BookmarkListWidget, self).showEvent(event)
        self.init_data()

    @QtCore.Slot(unicode)
    def job_changed(self, server, job):
        """This slot responds to any job changes."""
        if server is None or job is None:
            self.clear()
            return

        if server == self.server and job == self.job:
            return

        self.server = server
        self.job = job
        self.init_data()

    @QtCore.Slot()
    def init_data(self):
        """Loads a list of bookmarks found in the current job.

        """
        self.clear()

        if not self.server or not self.job:
            self.loaded.emit()
            return

        path = self.server + u'/' + self.job
        dirs = self.find_bookmark_dirs(path, -1, 4, [])
        self._interrupt_requested = False

        for d in dirs:
            item = QtWidgets.QListWidgetItem()
            item.setFlags(
                QtCore.Qt.ItemIsEnabled |
                # QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsUserCheckable
            )
            item.setCheckState(QtCore.Qt.Unchecked)
            name = d.split(self.job)[-1].strip(u'/').strip('\\')
            item.setData(QtCore.Qt.DisplayRole, name)
            item.setData(QtCore.Qt.UserRole, d)
            size = QtCore.QSize(
                0,
                common.MARGIN() * 2
            )
            item.setSizeHint(size)
            self.insertItem(self.count(), item)
            self.set_item_state(item)

        self.loaded.emit()

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def set_item_state(self, item):
        """Checks if the item is part of the current bookmark set and set the
        `checkState` and icon accordingly.

        Args:
            item(QtWidgets.QListWidgetItem):    The item to check.

        """
        bookmarks = settings.local_settings.get_bookmarks()

        from . import job_widget
        pixmap = job_widget.get_job_thumbnail(self.server + u'/' + self.job)

        if item.data(QtCore.Qt.UserRole) in [f for f in bookmarks]:
            item.setCheckState(QtCore.Qt.Checked)

            if pixmap.isNull():
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'check', common.ADD, common.ROW_HEIGHT() * 0.8)

        else:
            item.setCheckState(QtCore.Qt.Unchecked)

            if pixmap.isNull():
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'remove', common.SECONDARY_BACKGROUND, common.ROW_HEIGHT() * 0.8)

        icon = QtGui.QIcon()

        icon.addPixmap(pixmap, QtGui.QIcon.Normal)
        icon.addPixmap(pixmap, QtGui.QIcon.Selected)
        icon.addPixmap(pixmap, QtGui.QIcon.Active)
        icon.addPixmap(pixmap, QtGui.QIcon.Disabled)
        item.setData(QtCore.Qt.DecorationRole, icon)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self._interrupt_requested = True

    def find_bookmark_dirs(self, path, count, limit, arr, emit_progress=True):
        """Recursive scanning function for finding bookmark folders
        inside the given path.

        """
        if self._interrupt_requested:
            return arr

        count += 1
        if count > limit:
            return arr

        # We'll let unreadable paths fail silently
        try:
            it = _scandir.scandir(path)
        except:
            return arr

        if emit_progress:
            self.progressUpdate.emit(
                u'Scanning for bookmarks, please wait...\n{}'.format(path))

        for entry in it:
            if not entry.is_dir():
                continue
            path = entry.path.replace(u'\\', u'/')
            if [f for f in arr if f in path]:
                continue

            if entry.name == common.BOOKMARK_ROOT_DIR:
                arr.append(u'/'.join(path.split(u'/')[:-1]))

            self.find_bookmark_dirs(path, count, limit, arr)

        if emit_progress:
            self.progressUpdate.emit(u'')

        return sorted(arr)
