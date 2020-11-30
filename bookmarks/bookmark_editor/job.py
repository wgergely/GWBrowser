"""Widget used to view the list of jobs on a server.

"""
from PySide2 import QtCore, QtGui, QtWidgets
import _scandir

from .. import common
from .. import settings
from .. import images
from .. import contextmenu
from .. import templates


def get_job_thumbnail(path):
    """Checks the given job folder for the presence of a thumbnail image file.

    """
    file_info = QtCore.QFileInfo(path)
    if not file_info.exists():
        return QtGui.QPixmap()

    for entry in _scandir.scandir(file_info.absoluteFilePath()):
        if entry.is_dir():
            continue

        if u'thumbnail' not in entry.name.lower():
            continue

        pixmap = QtGui.QPixmap(entry.path)
        if pixmap.isNull():
            continue
        return pixmap

    return QtGui.QPixmap()


class JobContextMenu(contextmenu.BaseContextMenu):
    """Custom context menu used to control the list of saved servers.

    """

    def __init__(self, index, parent=None):
        super(JobContextMenu, self).__init__(index, parent=parent)
        self.add_add_menu()
        self.add_separator()
        if isinstance(index, QtWidgets.QListWidgetItem) and index.flags() & QtCore.Qt.ItemIsEnabled:
            self.add_reveal_menu()
        self.add_separator()
        self.add_refresh_menu()

    @contextmenu.contextmenu
    def add_add_menu(self, menu_set):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'add', common.ADD, common.MARGIN())

        menu_set[u'Add new job'] = {
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
            u'action': (self.parent().init_data, self.parent().restore_current),
            u'icon': pixmap
        }

        return menu_set


class JobListWidget(QtWidgets.QListWidget):
    """Simple list widget used to add and remove servers to/from the local
    settings.

    """
    jobChanged = QtCore.Signal(unicode, unicode)

    def __init__(self, parent=None):
        super(JobListWidget, self).__init__(parent=parent)
        self._server = None

        common.set_custom_stylesheet(self)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.setWindowTitle(u'Job Editor')
        self.setObjectName(u'JobEditor')

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

        self._connect_signals()

    def _connect_signals(self):
        self.selectionModel().selectionChanged.connect(self.save_current)
        self.selectionModel().selectionChanged.connect(self.emit_job_changed)

    @QtCore.Slot(QtCore.QItemSelection)
    @QtCore.Slot(QtCore.QItemSelection)
    def emit_job_changed(self, current, previous):
        index = next((f for f in current.indexes()), QtCore.QModelIndex())
        if not index.isValid():
            self.jobChanged.emit(None, None)
            return
        self.jobChanged.emit(
            self._server,
            index.data(QtCore.Qt.DisplayRole)
        )

    @QtCore.Slot()
    def add(self):
        if not self._server:
            return

        w = templates.TemplatesWidget(u'job', parent=self)
        w.set_path(self._server)

        w.templateCreated.connect(self.init_data)
        w.templateCreated.connect(lambda x: self.restore_current(name=x))
        w.templateCreated.connect(w.close)
        w.exec_()

    @QtCore.Slot()
    def save_current(self, current, previous):
        index = next((f for f in current.indexes()), QtCore.QModelIndex())
        if not index.isValid():
            return

        settings.local_settings.setValue(
            u'bookmark_editor/job',
            index.data(QtCore.Qt.DisplayRole)
        )

    @QtCore.Slot()
    def restore_current(self, name=None):
        if name:
            current = name
        else:
            current = settings.local_settings.value(u'bookmark_editor/job')

        if not current:
            return

        for n in xrange(self.count()):
            if not current == self.item(n).text():
                continue
            index = self.indexFromItem(self.item(n))
            self.selectionModel().select(
                index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            self.scrollToItem(
                self.item(n), QtWidgets.QAbstractItemView.EnsureVisible)
            return

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        menu = JobContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def showEvent(self, event):
        super(JobListWidget, self).showEvent(event)
        self.init_data()
        self.restore_current()

    @QtCore.Slot(unicode)
    def server_changed(self, server):
        if server is None:
            self.jobChanged.emit(None, None)
            return

        if server == self._server:
            return

        self._server = server
        self.init_data()
        self.restore_current()

    @QtCore.Slot()
    def init_data(self):
        self.jobChanged.emit(None, None)

        self.blockSignals(True)
        self.clear()

        if not self._server:
            self.blockSignals(False)
            return

        for entry in _scandir.scandir(self._server):
            if not entry.is_dir():
                continue
            file_info = QtCore.QFileInfo(entry.path)
            if file_info.isHidden():
                continue

            item = QtWidgets.QListWidgetItem()
            item.setData(
                QtCore.Qt.DisplayRole,
                entry.name
            )
            item.setData(
                QtCore.Qt.UserRole,
                QtCore.QFileInfo(entry.path).absoluteFilePath()
            )

            size = QtCore.QSize(
                0,
                common.MARGIN() * 2
            )
            item.setSizeHint(size)
            self.validate_item(item)
            self.insertItem(self.count(), item)

        self.blockSignals(False)

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def validate_item(self, item, emit=False):
        self.blockSignals(True)

        pixmap = get_job_thumbnail(item.data(QtCore.Qt.UserRole))
        if pixmap.isNull():
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'logo', common.SECONDARY_BACKGROUND, common.ROW_HEIGHT() * 0.8)
            pixmap_selected = images.ImageCache.get_rsc_pixmap(
                u'logo', common.TEXT_SELECTED, common.ROW_HEIGHT() * 0.8)
            pixmap_disabled = images.ImageCache.get_rsc_pixmap(
                u'remove', common.REMOVE, common.ROW_HEIGHT() * 0.8)
        else:
            pixmap_selected = pixmap
            pixmap_disabled = pixmap

        icon = QtGui.QIcon()

        # Let's explicitly check read access by trying to get the
        # files inside the folder
        is_valid = False
        try:
            next(_scandir.scandir(item.data(QtCore.Qt.UserRole)))
            is_valid = True
        except StopIteration:
            is_valid = True
        except OSError:
            is_valid = False

        file_info = QtCore.QFileInfo(item.data(QtCore.Qt.UserRole))
        if (
            file_info.exists() and
            file_info.isReadable() and
            file_info.isWritable() and
            is_valid
        ):
            icon.addPixmap(pixmap, QtGui.QIcon.Normal)
            icon.addPixmap(pixmap_selected, QtGui.QIcon.Selected)
            icon.addPixmap(pixmap_selected, QtGui.QIcon.Active)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Disabled)
            item.setFlags(
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable
            )
            r = True
        else:
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Normal)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Selected)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Active)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Disabled)
            item.setFlags(
                QtCore.Qt.NoItemFlags
            )
            r = False

        item.setData(QtCore.Qt.DecorationRole, icon)
        self.blockSignals(False)

        if emit and r:
            index = self.indexFromItem(item)
            self.selectionModel().emitSelectionChanged(
                QtCore.QItemSelection(index, index),
                QtCore.QItemSelection()
            )

        return r
