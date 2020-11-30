"""Widget used to view the list of jobs on a server.

"""
from PySide2 import QtCore, QtGui, QtWidgets

import _scandir

from .. import common
from .. import log
from .. import settings
from .. import images
from .. import contextmenu
from .. import common_ui

from . import bookmark_properties
from . import job


class ProgressOverlayWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ProgressOverlayWidget, self).__init__(parent=parent)
        self._message = u''

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

    @QtCore.Slot(unicode)
    def set_message(self, message):
        if message == self._message:
            return

        self._message = message
        self.update()
        QtWidgets.QApplication.instance().processEvents(
            flags=QtCore.QEventLoop.AllEvents)

    def paintEvent(self, event):
        if not self._message and not self.parent().parent().count():
            message = u'No bookmarks'
        elif not self._message:
            return
        elif self._message:
            message = self._message

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(common.TEXT)

        o = common.MARGIN()
        rect = self.rect().adjusted(o, o, -o, -o)
        text = QtGui.QFontMetrics(self.font()).elidedText(
            message,
            QtCore.Qt.ElideMiddle,
            rect.width(),
        )

        painter.drawText(
            rect,
            QtCore.Qt.AlignCenter,
            text,
        )
        painter.end()


class BookmarkContextMenu(contextmenu.BaseContextMenu):
    """Custom context menu used to control the list of saved servers.

    """

    def __init__(self, index, parent=None):
        super(BookmarkContextMenu, self).__init__(index, parent=parent)
        self.add_add_menu()
        self.add_separator()
        if isinstance(index, QtWidgets.QListWidgetItem) and index.flags() & QtCore.Qt.ItemIsEnabled:
            self.add_bookmark_properties_menu()
            self.add_reveal_menu()
        self.add_separator()
        self.add_refresh_menu()

    @contextmenu.contextmenu
    def add_add_menu(self, menu_set):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'add', common.ADD, common.MARGIN())

        menu_set[u'Add bookmark'] = {
            u'action': self.parent().add,
            u'icon': pixmap
        }
        return menu_set

    @contextmenu.contextmenu
    def add_reveal_menu(self, menu_set):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'reveal_folder', common.SECONDARY_TEXT, common.MARGIN())

        @QtCore.Slot()
        def reveal():
            common.reveal(self.index.data(QtCore.Qt.UserRole) + '/.')

        menu_set[u'Reveal...'] = {
            u'action': reveal,
            u'icon': pixmap
        }
        return menu_set

    @contextmenu.contextmenu
    def add_refresh_menu(self, menu_set):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'refresh', common.SECONDARY_TEXT, common.MARGIN())
        menu_set[u'Refresh'] = {
            u'action': self.parent().init_data,
            u'icon': pixmap
        }

        return menu_set

    @contextmenu.contextmenu
    def add_bookmark_properties_menu(self, menu_set):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'settings', common.SECONDARY_TEXT, common.MARGIN())
        menu_set[u'Properties'] = {
            u'action': lambda: self.parent().edit_properties(self.index),
            u'icon': pixmap
        }
        return menu_set


class BookmarkListWidget(QtWidgets.QListWidget):
    """Simple list widget used to add and remove servers to/from the local
    settings.

    """
    loaded = QtCore.Signal()
    bookmarkAdded = QtCore.Signal(unicode, unicode, unicode)
    bookmarkRemoved = QtCore.Signal(unicode, unicode, unicode)

    progressUpdate = QtCore.Signal(unicode)
    resized = QtCore.Signal(QtCore.QSize)

    def __init__(self, parent=None):
        super(BookmarkListWidget, self).__init__(parent=parent)
        self._server = None
        self._job = None
        self._interrupt_requested = False

        common.set_custom_stylesheet(self)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.setWindowTitle(u'Bookmark Editor')
        self.setObjectName(u'BookmarkEditor')

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

        self.overlay = ProgressOverlayWidget(parent=self.viewport())
        self.overlay.show()

        self._connect_signals()

    def _connect_signals(self):
        self.resized.connect(self.overlay.resize)
        self.progressUpdate.connect(self.overlay.set_message)
        self.itemClicked.connect(self.toggle_checkbox)
        self.itemActivated.connect(self.toggle_checkbox)

    def resizeEvent(self, event):
        self.resized.emit(event.size())

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def toggle_checkbox(self, item):
        settings.local_settings.sync()
        bookmarks = settings.local_settings.bookmarks()

        if item.checkState() == QtCore.Qt.Checked:
            item.setCheckState(QtCore.Qt.Unchecked)
            if item.data(QtCore.Qt.UserRole) in [f for f in bookmarks]:
                del bookmarks[item.data(QtCore.Qt.UserRole)]
            self.bookmarkRemoved.emit(
                self._server, self._job, item.data(QtCore.Qt.DisplayRole))
        elif item.checkState() == QtCore.Qt.Unchecked:
            item.setCheckState(QtCore.Qt.Checked)
            bookmarks[item.data(QtCore.Qt.UserRole)] = {
                u'server': self._server,
                u'job': self._job,
                u'root': item.data(QtCore.Qt.DisplayRole)
            }
            self.bookmarkAdded.emit(
                self._server, self._job, item.data(QtCore.Qt.DisplayRole))

        self.verify_item(item)

    @QtCore.Slot()
    def edit_properties(self, item):
        widget = bookmark_properties.BookmarkPropertiesWidget(
            self._server,
            self._job,
            item.data(QtCore.Qt.DisplayRole)
        )
        widget.open()

    @QtCore.Slot()
    def add(self):
        if not self._server or not self._job:
            return

        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            u'Pick a new bookmark folder',
            self._server + u'/' + self._job,
            QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks
        )
        if not path:
            return
        if not QtCore.QDir(path).mkdir(common.BOOKMARK_INDICATOR):
            log.error(u'Failed to create bookmark.')

        name = path.split(self._job)[-1].strip(u'/').strip(u'\\')

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
            # QtCore.Qt.ItemIsSelectable |
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
        self.verify_item(item)
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

        if server == self._server and job == self._job:
            return

        self._server = server
        self._job = job
        self.init_data()

    @QtCore.Slot()
    def init_data(self):
        """Best course of action might be to cache the results to a config file
        and let the user search for bookmarks.

        """
        self.clear()

        if not self._server or not self._job:
            self.loaded.emit()
            return

        path = self._server + u'/' + self._job
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
            name = d.split(self._job)[-1].strip(u'/').strip('\\')
            item.setData(QtCore.Qt.DisplayRole, name)
            item.setData(QtCore.Qt.UserRole, d)
            size = QtCore.QSize(
                0,
                common.MARGIN() * 2
            )
            item.setSizeHint(size)
            self.insertItem(self.count(), item)
            self.verify_item(item)

        self.loaded.emit()

    def verify_item(self, item):
        bookmarks = settings.local_settings.bookmarks()

        pixmap = job.get_job_thumbnail(self._server + u'/' + self._job)

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
            return

        if emit_progress:
            self.progressUpdate.emit(
                u'Scanning for bookmarks, please wait...\n{}'.format(path))

        for entry in it:
            if not entry.is_dir():
                continue
            path = entry.path.replace(u'\\', u'/')
            if [f for f in arr if f in path]:
                continue

            if entry.name == common.BOOKMARK_INDICATOR:
                arr.append(u'/'.join(path.split(u'/')[:-1]))

            self.find_bookmark_dirs(path, count, limit, arr)

        if emit_progress:
            self.progressUpdate.emit(u'')

        return sorted(arr)
