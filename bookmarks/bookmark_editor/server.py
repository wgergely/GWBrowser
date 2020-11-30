"""Widget used to save and edit the list of servers available for Bookmarks.

"""
import re
import os
import functools

from PySide2 import QtCore, QtGui, QtWidgets

from .. import common
from .. import settings
from .. import images
from .. import standalone
from .. import contextmenu


class ServerContextMenu(contextmenu.BaseContextMenu):
    """Custom context menu used to control the list of saved servers.

    """

    def __init__(self, index, parent=None):
        super(ServerContextMenu, self).__init__(index, parent=parent)
        self.add_add_menu()
        self.add_separator()
        if isinstance(index, QtWidgets.QListWidgetItem) and index.flags() & QtCore.Qt.ItemIsEnabled:
            self.add_edit_menu()
            self.add_reveal_menu()
            self.add_remove_menu()
        elif isinstance(index, QtWidgets.QListWidgetItem) and not index.flags() & QtCore.Qt.ItemIsEnabled:
            self.add_edit_menu()
            self.add_remove_menu()
        self.add_separator()
        self.add_refresh_menu()

    @contextmenu.contextmenu
    def add_add_menu(self, menu_set):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'add', common.ADD, common.MARGIN())

        menu_set[u'Add new server'] = {
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
            common.reveal(self.index.text() + '/.')

        menu_set[u'Reveal...'] = {
            u'action': reveal,
            u'icon': pixmap
        }
        return menu_set

    @contextmenu.contextmenu
    def add_edit_menu(self, menu_set):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'todo', common.SECONDARY_TEXT, common.MARGIN())

        def edit():
            self.parent().blockSignals(True)
            flags = self.index.flags()
            self.index.setFlags(
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEditable
            )
            self.parent().blockSignals(False)

            self.parent().selectionModel().blockSignals(True)
            self.parent().setCurrentRow(self.parent().row(self.index))
            self.parent().selectionModel().blockSignals(False)

            self.parent().editItem(self.index)

            self.parent().blockSignals(True)
            self.index.setFlags(flags)
            self.parent().blockSignals(False)

        menu_set[u'Edit'] = {
            u'action': edit,
            u'icon': pixmap
        }
        return menu_set

    @contextmenu.contextmenu
    def add_remove_menu(self, menu_set):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'remove', common.REMOVE, common.MARGIN())

        QtCore.Slot()

        def remove():
            widget = self.parent()
            item = widget.takeItem(widget.row(self.index))
            widget.save_data()
            del item

        menu_set[u'Remove'] = {
            u'action': remove,
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


class ServerDelegate(QtWidgets.QStyledItemDelegate):
    """Custom delegate used by the ServerWidget."""

    def createEditor(self, parent, option, index):
        return QtWidgets.QLineEdit(parent=parent)

    def setModelData(self, editor, model, index):
        text = editor.text()

        if not text:
            editor.setText(u'Server not set')
        else:
            if os.path.isdir(text):
                text = os.path.normpath(os.path.abspath(text))
            text = text.rstrip(u'/').rstrip(u'\\')
            text = re.sub(ur'\\', '/', text)
            editor.setText(text)

        super(ServerDelegate, self).setModelData(editor, model, index)


class ServerListWidget(QtWidgets.QListWidget):
    """Simple list widget used to add and remove servers to/from the local
    settings.

    """
    serverChanged = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(ServerListWidget, self).__init__(parent=parent)

        self._init_timer = QtCore.QTimer()
        self._init_timer.setSingleShot(True)
        self._init_timer.setInterval(333)

        common.set_custom_stylesheet(self)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setItemDelegate(ServerDelegate(parent=self))
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

        self.setWindowTitle(u'Server Editor')
        self.setObjectName(u'ServerEditor')
        self._connect_signals()

    @QtCore.Slot()
    def add(self):
        item = QtWidgets.QListWidgetItem()
        size = QtCore.QSize(
            0,
            common.MARGIN() * 2
        )
        item.setSizeHint(size)
        item.setFlags(
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsSelectable |
            QtCore.Qt.ItemIsEditable
        )

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'server', common.TEXT, common.ROW_HEIGHT() * 0.8)
        icon = QtGui.QIcon()
        icon.addPixmap(pixmap, QtGui.QIcon.Normal)
        item.setData(QtCore.Qt.DecorationRole, icon)

        self.insertItem(self.count(), item)
        self.setCurrentRow(self.row(item))
        self.editItem(item)

    def _connect_signals(self):
        self._init_timer.timeout.connect(self.init)
        self.itemChanged.connect(
            functools.partial(self.validate_item, emit_selection_change=True))
        self.itemChanged.connect(self.save_data)
        self.selectionModel().selectionChanged.connect(self.save_current)
        self.selectionModel().selectionChanged.connect(self.emit_server_changed)

    @QtCore.Slot(QtCore.QItemSelection)
    @QtCore.Slot(QtCore.QItemSelection)
    def emit_server_changed(self, current, previous):
        index = next((f for f in current.indexes()), QtCore.QModelIndex())
        if not index.isValid():
            self.serverChanged.emit(None)
            return
        self.serverChanged.emit(index.data(QtCore.Qt.DisplayRole))

    @QtCore.Slot(QtCore.QItemSelection)
    @QtCore.Slot(QtCore.QItemSelection)
    def save_current(self, current, previous):
        index = next((f for f in current.indexes()), QtCore.QModelIndex())
        if not index.isValid():
            settings.local_settings.setValue(
                u'bookmark_editor/server',
                None
            )
            return

        settings.local_settings.setValue(
            u'bookmark_editor/server',
            index.data(QtCore.Qt.DisplayRole)
        )

    @QtCore.Slot()
    def restore_current(self, emit_selection_change=False):
        current = settings.local_settings.value(u'bookmark_editor/server')
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
            self.scrollToItem(self.item(n), QtWidgets.QAbstractItemView.EnsureVisible)
            if emit_selection_change:
                self.selectionModel().emitSelectionChanged(
                    QtCore.QItemSelection(index, index),
                    QtCore.QItemSelection()
                )
            return

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        menu = ServerContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def showEvent(self, event):
        super(ServerListWidget, self).showEvent(event)
        self._init_timer.start()

    def init(self):
        self.init_data()
        self.restore_current(emit_selection_change=True)

    @QtCore.Slot()
    def init_data(self):
        self.blockSignals(True)
        self.selectionModel().blockSignals(True)

        self.clear()

        servers = settings.local_settings.load_saved_servers()

        for server in servers:
            item = QtWidgets.QListWidgetItem(server)
            size = QtCore.QSize(
                0,
                common.MARGIN() * 2
            )
            item.setSizeHint(size)
            self.validate_item(item)
            self.insertItem(self.count(), item)

        self.blockSignals(False)
        self.selectionModel().blockSignals(False)

    @QtCore.Slot()
    def save_data(self):
        servers = []
        for n in xrange(self.count()):
            servers.append(self.item(n).text())

        settings.local_settings.sync()
        servers = sorted(list(set(servers)))
        settings.local_settings.setValue(u'servers', servers)

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def validate_item(self, item, emit_selection_change=False):
        self.blockSignals(True)

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'server', common.TEXT, common.ROW_HEIGHT() * 0.8)
        pixmap_selected = images.ImageCache.get_rsc_pixmap(
            u'server', common.TEXT_SELECTED, common.ROW_HEIGHT() * 0.8)
        pixmap_disabled = images.ImageCache.get_rsc_pixmap(
            u'remove', common.REMOVE, common.ROW_HEIGHT() * 0.8)
        icon = QtGui.QIcon()

        file_info = QtCore.QFileInfo(item.text())
        if file_info.exists() and file_info.isReadable() and file_info.isWritable():
            icon.addPixmap(pixmap, QtGui.QIcon.Normal)
            icon.addPixmap(pixmap_selected, QtGui.QIcon.Selected)
            icon.addPixmap(pixmap_selected, QtGui.QIcon.Active)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Disabled)
            item.setFlags(
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEditable
            )
            r = True
        else:
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Normal)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Selected)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Active)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Disabled)
            item.setFlags(
                QtCore.Qt.ItemIsEditable
            )
            r = False

        item.setData(QtCore.Qt.DecorationRole, icon)
        self.blockSignals(False)

        if emit_selection_change and r:
            index = self.indexFromItem(item)
            self.selectionModel().emitSelectionChanged(
                QtCore.QItemSelection(index, index),
                QtCore.QItemSelection()
            )

        return r
